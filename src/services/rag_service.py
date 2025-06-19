import logging
from typing import Dict, Any, Optional, List
import time
from datetime import datetime

# Importar componentes RAG
from rag.document_processor import DocumentProcessor
from rag.embedding_service import EmbeddingService
from rag.vector_store import VectorStore
from rag.cache_manager import CacheManager
from rag.retrieval_engine import RetrievalEngine

# 🆕 NOVO: Importar serviços de cache e deduplicação
from services.embedding_cache_service import EmbeddingCacheService
from services.deduplication_service import DeduplicationService

logger = logging.getLogger(__name__)

class RAGService:
    """Serviço principal de RAG com cache inteligente"""
    
    def __init__(self, db_manager, unified_processor, openai_api_key: str, 
                 redis_host: str = "localhost"):
        self.db_manager = db_manager
        self.unified_processor = unified_processor
        
        # 🆕 NOVO: Inicializar cache e deduplicação
        self.cache_service = EmbeddingCacheService(db_manager, redis_host)
        self.dedup_service = DeduplicationService(db_manager, self.cache_service)
        
        # Componentes RAG existentes
        self.document_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()  # Manter VoyageAI como fallback
        self.vector_store = VectorStore(db_manager)
        self.cache_manager = CacheManager(redis_host=redis_host)
        self.retrieval_engine = RetrievalEngine(openai_api_key)
        
        logger.info("✅ RAGService inicializado com cache inteligente")
    
    def process_or_query(self, licitacao_id: str, query: str) -> Dict[str, Any]:
        """Função principal: processa documentos se necessário e responde query"""
        try:
            logger.info(f"🚀 Iniciando RAG para licitação: {licitacao_id}")
            
            # 1. Verificar cache primeiro
            cached_result = self.cache_manager.get_cached_query_result(query, licitacao_id)
            if cached_result:
                logger.info("⚡ Resultado encontrado no cache")
                return {
                    'success': True,
                    'cached': True,
                    **cached_result
                }
            
            # 2. Verificar se documentos estão vetorizados
            status = self.vector_store.check_vectorization_status(licitacao_id)
                         
            if not status.get('vetorizado_completo', False):
                # 3. Processar documentos se necessário (inclui extração recursiva de ZIPs)
                logger.info("📝 Documentos não vetorizados, iniciando processamento completo...")
                print("📝 Documentos não vetorizados, iniciando processamento completo...")
                vectorization_result = self._vectorize_licitacao(licitacao_id)
                print(f"vectorization_result: {vectorization_result}")
                
                if not vectorization_result['success']:
                    # Incluir detalhes de diagnóstico no resultado
                    error_response = {
                        'success': False,
                        'error': vectorization_result.get('error'),
                        'processing_details': {
                            'action': vectorization_result.get('action', 'unknown'),
                            'suggestion': vectorization_result.get('suggestion'),
                            'licitacao_info': vectorization_result.get('licitacao_info')
                        }
                    }
                    return error_response
            
            # 4. Responder query
            response_result = self._answer_query(query, licitacao_id)
            
            # 5. Cachear resultado
            if response_result['success']:
                self.cache_manager.cache_query_result(
                    query, licitacao_id, response_result, ttl=3600
                )
                
                # Adicionar informações de processamento se documentos foram processados nesta sessão
                if not status.get('vetorizado_completo', False):
                    response_result['processing_info'] = {
                        'documents_processed_this_session': True,
                        'processing_method': 'recursive_zip_extraction',
                        'vectorization_completed': True
                    }
            
            return response_result
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento RAG: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }
    
    def _vectorize_licitacao(self, licitacao_id: str) -> Dict[str, Any]:
        """VERSÃO ATUALIZADA: Vetoriza documentos evitando reprocessamento"""
        try:
            # 1. Verificar e processar documentos automaticamente se necessário
            documentos_result = self._ensure_documents_processed(licitacao_id)
            if not documentos_result['success']:
                return documentos_result
            
            # 2. Obter documentos do banco
            documentos = self.unified_processor.obter_documentos_licitacao(licitacao_id)
            
            if not documentos:
                return {
                    'success': False,
                    'error': 'Nenhum documento encontrado para vetorização'
                }
            
            # 3. 🆕 NOVO: Verificar quais documentos já foram processados
            documentos_para_processar = []
            documentos_ja_processados = 0
            
            for documento in documentos:
                documento_data = {
                    'arquivo_url': documento.get('arquivo_nuvem_url', ''),
                    'tamanho_arquivo': documento.get('tamanho_arquivo', 0),
                    'hash_arquivo': documento.get('hash_arquivo', '')
                }
                
                # Verificar se já tem chunks vetorizados OU se já foi processado antes
                existing_chunks = self.vector_store.count_document_chunks(documento['id'])
                already_processed = self.dedup_service.should_process_rag_document(documento['id'], documento_data)
                
                if existing_chunks > 0 or not already_processed:
                    documentos_ja_processados += 1
                    logger.info(f"⏭️ Documento já processado: {documento['titulo']} ({existing_chunks} chunks)")
                else:
                    documentos_para_processar.append(documento)
            
            if documentos_ja_processados > 0:
                logger.info(f"📊 Documentos: {documentos_ja_processados} já processados, {len(documentos_para_processar)} para processar")
            
            # Se todos já processados, retornar sucesso
            if not documentos_para_processar:
                total_chunks = sum(self.vector_store.count_document_chunks(doc['id']) for doc in documentos)
                return {
                    'success': True,
                    'message': 'Todos os documentos já estavam vetorizados',
                    'processed_documents': len(documentos),
                    'total_chunks': total_chunks,
                    'already_vectorized': True
                }
            
            # 4. 🆕 NOVO: Processar apenas documentos necessários
            total_chunks = 0
            processed_docs = 0
            embedding_cache_hits = 0
            
            logger.info(f"📋 Processando {len(documentos_para_processar)} documentos para vetorização...")
            
            for idx, documento in enumerate(documentos_para_processar, 1):
                logger.info(f"📄 Processando documento {idx}/{len(documentos_para_processar)}: {documento['titulo']}")
                
                # Marcar como processando
                self._update_document_status(documento['id'], 'processando')
                
                try:
                    # Extrair texto (SEM MUDANÇA)
                    texto_completo = self.document_processor.extract_text_from_url(
                        documento['arquivo_nuvem_url']
                    )
                    
                    if not texto_completo:
                        self._update_document_status(documento['id'], 'erro')
                        continue
                    
                    # Salvar texto extraído
                    self._save_extracted_text(documento['id'], texto_completo)
                    
                    # Criar chunks inteligentes (SEM MUDANÇA)
                    chunks = self.document_processor.create_intelligent_chunks(
                        texto_completo, documento['id']
                    )
                    
                    if not chunks:
                        self._update_document_status(documento['id'], 'erro')
                        continue
                    
                    # 🆕 NOVO: Gerar embeddings com cache
                    chunk_texts = [chunk.text for chunk in chunks]
                    embeddings = []
                    
                    # Verificar cache para cada chunk
                    for chunk_text in chunk_texts:
                        cached_embedding = self.cache_service.get_embedding_from_cache(
                            chunk_text, "sentence-transformers"
                        )
                        
                        if cached_embedding:
                            embeddings.append(cached_embedding)
                            embedding_cache_hits += 1
                        else:
                            # Gerar novo embedding (usar sentence-transformers primeiro)
                            new_embedding = self._generate_embedding_with_fallback(chunk_text)
                            embeddings.append(new_embedding)
                            
                            if new_embedding:
                                self.cache_service.save_embedding_to_cache(
                                    chunk_text, new_embedding, "sentence-transformers"
                                )
                    
                    # Verificar se todos embeddings foram gerados
                    valid_embeddings = [emb for emb in embeddings if emb]
                    
                    if len(valid_embeddings) != len(chunks):
                        logger.error(f"❌ Embeddings incompletos para {documento['titulo']}")
                        logger.error(f"📊 Esperado: {len(chunks)} embeddings, Gerado: {len(valid_embeddings)}")
                        self._update_document_status(documento['id'], 'erro_embedding')
                        continue
                    
                    # Salvar no vector store (SEM MUDANÇA)
                    chunk_dicts = [self._chunk_to_dict(chunk) for chunk in chunks]
                    success = self.vector_store.save_chunks_with_embeddings(
                        documento['id'], licitacao_id, chunk_dicts, valid_embeddings
                    )
                    
                    if success:
                        total_chunks += len(chunks)
                        processed_docs += 1
                        
                        # 🆕 NOVO: Marcar documento como processado
                        documento_data = {
                            'arquivo_url': documento.get('arquivo_nuvem_url', ''),
                            'tamanho_arquivo': documento.get('tamanho_arquivo', 0),
                            'hash_arquivo': documento.get('hash_arquivo', '')
                        }
                        self.dedup_service.mark_rag_document_processed(documento['id'], documento_data)
                        
                        logger.info(f"✅ Documento vetorizado: {documento['titulo']} ({len(chunks)} chunks)")
                    else:
                        self._update_document_status(documento['id'], 'erro')
                
                except Exception as e:
                    logger.error(f"❌ Erro ao vetorizar {documento['título']}: {e}")
                    self._update_document_status(documento['id'], 'erro')
                    continue
            
            logger.info(f"📊 Cache hits de embeddings: {embedding_cache_hits}")
            
            if processed_docs > 0 or documentos_ja_processados > 0:
                total_existing_chunks = sum(self.vector_store.count_document_chunks(doc['id']) for doc in documentos)
                return {
                    'success': True,
                    'message': 'Vetorização concluída com cache',
                    'processed_documents': processed_docs,
                    'already_processed_documents': documentos_ja_processados,
                    'total_chunks': total_chunks + total_existing_chunks,
                    'embedding_cache_hits': embedding_cache_hits
                }
            else:
                return {
                    'success': False,
                    'error': 'Nenhum documento foi vetorizado com sucesso'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro na vetorização: {e}")
            return {
                'success': False,
                'error': f'Erro na vetorização: {str(e)}'
            }
    
    def _generate_embedding_with_fallback(self, text: str) -> List[float]:
        """🆕 NOVO: Gera embedding com fallback sentence-transformers -> voyage -> openai"""
        
        # 1. Tentar sentence-transformers primeiro (se disponível)
        try:
            from services.sentence_transformer_service import SentenceTransformerService
            st_service = SentenceTransformerService()
            embedding = st_service.generate_single_embedding(text)
            if embedding:
                return embedding
        except Exception as e:
            logger.warning(f"⚠️ SentenceTransformers falhou: {e}")
        
        # 2. Fallback para VoyageAI
        try:
            embedding = self.embedding_service.generate_single_embedding(text)
            if embedding:
                return embedding
        except Exception as e:
            logger.warning(f"⚠️ VoyageAI falhou: {e}")
        
        # 3. Último recurso: usar vectorizer do matching
        try:
            from matching.vectorizers import OpenAITextVectorizer
            openai_vectorizer = OpenAITextVectorizer()
            embedding = openai_vectorizer.vectorize(text)
            if embedding:
                return embedding
        except Exception as e:
            logger.warning(f"⚠️ OpenAI fallback falhou: {e}")
        
        logger.warning("🔄 Todos os métodos de embedding falharam")
        return []
    
    def _chunk_to_dict(self, chunk) -> Dict[str, Any]:
        """Converte chunk para dicionário"""
        return {
            'text': chunk.text,
            'chunk_type': chunk.chunk_type,
            'page_number': chunk.page_number,
            'section_title': chunk.section_title,
            'token_count': chunk.token_count,
            'char_count': chunk.char_count,
            'metadata': chunk.metadata or {}
        }
    
    def _answer_query(self, query: str, licitacao_id: str) -> Dict[str, Any]:
        """Responde uma query usando RAG"""
        try:
            start_time = time.time()
            
            # 1. Gerar embedding da query
            query_embedding = self.embedding_service.generate_single_embedding(query)
            
            if not query_embedding:
                return {
                    'success': False,
                    'error': 'Erro ao gerar embedding da consulta'
                }
            
            # 2. Buscar chunks relevantes (híbrida)
            chunks = self.vector_store.hybrid_search(
                query, query_embedding, licitacao_id, limit=12  # Buscar mais para reranking
            )
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'Nenhum conteúdo relevante encontrado nos documentos'
                }
            
            # 3. Aplicar reranking
            top_chunks = self.retrieval_engine.rerank_chunks(query, chunks, top_k=8)
            
            # 4. Obter informações da licitação
            licitacao_info = self.unified_processor.extrair_info_licitacao(licitacao_id)
            
            # 5. Gerar resposta
            response_result = self.retrieval_engine.generate_response(
                query, top_chunks, licitacao_info
            )
            
            if response_result.get('error'):
                return {
                    'success': False,
                    'error': response_result['answer']
                }
            
            processing_time = time.time() - start_time
            
            # 6. Montar resultado final
            result = {
                'success': True,
                'answer': response_result['answer'],
                'query': query,
                'licitacao_id': licitacao_id,
                'chunks_used': response_result['chunks_used'],
                'sources': response_result['sources'],
                'processing_time': round(processing_time, 2),
                'model_response_time': response_result.get('response_time'),
                'cost_usd': response_result.get('cost_usd'),
                'model': response_result.get('model'),
                'cached': False
            }
            
            logger.info(f"✅ Query respondida em {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao responder query: {e}")
            return {
                'success': False,
                'error': f'Erro ao processar consulta: {str(e)}'
            }
    
    def _ensure_documents_processed(self, licitacao_id: str) -> Dict[str, Any]:
        """
        🚀 NOVA FUNÇÃO: Garante que documentos estão processados usando UnifiedDocumentProcessor recursivo
        Integração completa do processamento recursivo de ZIPs no fluxo RAG
        """
        try:
            logger.info(f"🔍 Verificando documentos para licitação: {licitacao_id}")
            
            # 1. Verificar se documentos já existem
            documentos_existem = self.unified_processor.verificar_documentos_existem(licitacao_id)
            
            if documentos_existem:
                # Verificar se documentos são válidos (não corrompidos/vazios)
                documentos = self.unified_processor.obter_documentos_licitacao(licitacao_id)
                
                # Validar se temos documentos úteis
                documentos_validos = []
                for doc in documentos:
                    # Verificar se é arquivo útil (PDF, DOC, etc) e não está corrompido
                    if (doc.get('tipo_arquivo') in ['application/pdf', 'application/msword'] and 
                        doc.get('tamanho_arquivo', 0) > 1000):  # Arquivos > 1KB
                        documentos_validos.append(doc)
                
                if documentos_validos:
                    logger.info(f"✅ {len(documentos_validos)} documentos válidos já processados")
                    return {
                        'success': True,
                        'message': 'Documentos já processados',
                        'documentos_count': len(documentos_validos),
                        'action': 'documents_already_exist'
                    }
                else:
                    logger.warning(f"⚠️ Documentos existem mas são inválidos, reprocessando...")
                    # Limpar documentos inválidos
                    self.unified_processor._limpar_documentos_licitacao(licitacao_id)
            
            # 2. Processar documentos usando nossa lógica recursiva aprimorada
            logger.info("📥 Iniciando processamento recursivo de documentos...")
            
            # Primeiro, validar se a licitação existe
            licitacao_info = self.unified_processor.extrair_info_licitacao(licitacao_id)
            if not licitacao_info:
                return {
                    'success': False,
                    'error': f'Licitação {licitacao_id} não encontrada no banco de dados',
                    'action': 'licitacao_not_found'
                }
            
            # Tentar processar documentos (método assíncrono)
            import asyncio
            result = asyncio.run(self.unified_processor.processar_documentos_licitacao(licitacao_id))
            
            if result['success']:
                logger.info(f"🎉 Processamento recursivo concluído: {result.get('documentos_processados', 0)} documentos")
                return {
                    'success': True,
                    'message': 'Documentos processados com sucesso usando extração recursiva',
                    'documentos_processados': result.get('documentos_processados', 0),
                    'storage_provider': result.get('storage_provider', 'supabase'),
                    'pasta_nuvem': result.get('pasta_nuvem'),
                    'action': 'documents_processed_recursive'
                }
            else:
                # Se falhou, tentar diagnosticar o problema
                error_detail = result.get('error', 'Erro desconhecido')
                logger.error(f"❌ Falha no processamento: {error_detail}")
                
                # Verificar se é problema da API PNCP
                if 'API PNCP' in error_detail or 'HTTP' in error_detail:
                    return {
                        'success': False,
                        'error': f'Erro na API PNCP: {error_detail}',
                        'suggestion': 'Verifique se a licitação possui documentos disponíveis na API',
                        'action': 'api_error'
                    }
                
                # Outros erros
                return {
                    'success': False,
                    'error': f'Erro no processamento de documentos: {error_detail}',
                    'licitacao_info': {
                        'objeto': licitacao_info.get('objeto_compra', 'N/A')[:100] + '...',
                        'orgao': licitacao_info.get('orgao_entidade', 'N/A'),
                        'uf': licitacao_info.get('uf', 'N/A')
                    },
                    'action': 'processing_error'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro crítico ao garantir documentos processados: {e}")
            return {
                'success': False,
                'error': f'Erro crítico no processamento: {str(e)}',
                'action': 'critical_error'
            }
    
    def _update_document_status(self, documento_id: str, status: str):
        """Atualiza status de processamento do documento"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE documentos_licitacao 
                        SET status_processamento = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (status, documento_id))
                    conn.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar status: {e}")
    
    def _save_extracted_text(self, documento_id: str, texto: str):
        """Salva texto extraído no banco"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE documentos_licitacao 
                        SET texto_extraido = %s, updated_at = NOW()
                        WHERE id = %s
                    """, (texto, documento_id))
                    conn.commit()
        except Exception as e:
            logger.error(f"❌ Erro ao salvar texto: {e}")
    
    def get_licitacao_stats(self, licitacao_id: str) -> Dict[str, Any]:
        """Retorna estatísticas de uma licitação"""
        try:
            status = self.vector_store.check_vectorization_status(licitacao_id)
            cache_stats = self.cache_manager.get_cache_stats()
            
            return {
                'licitacao_id': licitacao_id,
                'vectorization_status': status,
                'cache_stats': cache_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats: {e}")
            return {'error': str(e)}
