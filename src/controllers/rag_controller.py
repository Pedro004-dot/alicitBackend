from flask import request, jsonify
import logging
from typing import Dict, Any
import re

logger = logging.getLogger(__name__)

class RAGController:
    """Controller para endpoints RAG"""
    
    def __init__(self, rag_service):
        self.rag_service = rag_service
    
    def analisar_documentos(self) -> Dict[str, Any]:
        """Endpoint principal para análise de documentos"""
        try:
            # Validar request
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            print(f"licitacao_id: {licitacao_id}")
            query = data.get('query', 'Faça um resumo geral dos documentos desta licitação.')
            print(f"query: {query}")
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            # 🎯 NOVA VALIDAÇÃO: Detectar se recebeu pncp_id em vez de licitacao_id
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
            pncp_pattern = re.compile(r'^\d+.*-.*\d+/\d{4}$')  # Formato típico de PNCP ID
            
            if not uuid_pattern.match(licitacao_id):
                if pncp_pattern.match(licitacao_id):
                    logger.warning(f"⚠️ Recebido pncp_id '{licitacao_id}' em vez de licitacao_id UUID")
                    
                    # Tentar converter pncp_id para licitacao_id
                    try:
                        from db.database_manager import DatabaseManager
                        db_manager = DatabaseManager()
                        
                        with db_manager.get_connection() as conn:
                            with conn.cursor() as cursor:
                                cursor.execute("""
                                    SELECT id FROM licitacoes WHERE pncp_id = %s
                                """, (licitacao_id,))
                                result = cursor.fetchone()
                                
                                if result:
                                    uuid_licitacao_id = result[0]
                                    logger.info(f"✅ Convertido pncp_id '{licitacao_id}' para UUID: {uuid_licitacao_id}")
                                    licitacao_id = uuid_licitacao_id
                                else:
                                    logger.error(f"❌ Licitação não encontrada para pncp_id: {licitacao_id}")
                                    return jsonify({
                                        'success': False,
                                        'error': f'Licitação não encontrada para pncp_id: {licitacao_id}'
                                    }), 404
                    except Exception as e:
                        logger.error(f"❌ Erro ao converter pncp_id para UUID: {e}")
                        return jsonify({
                            'success': False,
                            'error': f'Erro ao processar pncp_id: {str(e)}'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Formato inválido para licitacao_id. Esperado UUID ou pncp_id válido, recebido: {licitacao_id}'
                    }), 400
            
            print(f"licitacao_id final (UUID): {licitacao_id}")
            
            # Processar com RAG
            result = self.rag_service.process_or_query(licitacao_id, query)
            print(f"result: {result}")
            # Determinar status code
            status_code = 200 if result['success'] else 400
            
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"❌ Erro no controller: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def query_licitacao(self) -> Dict[str, Any]:
        """Endpoint para fazer perguntas sobre uma licitação específica"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            query = data.get('query')
            
            if not licitacao_id or not query:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id e query são obrigatórios'
                }), 400
            
            # Processar query
            result = self.rag_service._answer_query(query, licitacao_id)
            
            status_code = 200 if result['success'] else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"❌ Erro no query controller: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def status_licitacao(self) -> Dict[str, Any]:
        """Endpoint para verificar status de processamento"""
        try:
            licitacao_id = request.args.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            stats = self.rag_service.get_licitacao_stats(licitacao_id)
            
            return jsonify({
                'success': True,
                'data': stats
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no status controller: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def invalidar_cache(self) -> Dict[str, Any]:
        """Endpoint para invalidar cache de uma licitação"""
        try:
            data = request.get_json()
            licitacao_id = data.get('licitacao_id') if data else None
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            deleted_count = self.rag_service.cache_manager.invalidate_licitacao_cache(licitacao_id)
            
            return jsonify({
                'success': True,
                'message': f'{deleted_count} entradas de cache removidas',
                'deleted_count': deleted_count
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao invalidar cache: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def reprocessar_documentos(self) -> Dict[str, Any]:
        """Endpoint para forçar reprocessamento de documentos com extração recursiva"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            forcar_reprocessamento = data.get('forcar_reprocessamento', True)
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            # Limpar documentos existentes se forçando
            if forcar_reprocessamento:
                logger.info(f"🗑️ Limpando documentos existentes para: {licitacao_id}")
                try:
                    self.rag_service.unified_processor._limpar_documentos_licitacao(licitacao_id)
                    # Também limpar do vector store (se método existir)
                    if hasattr(self.rag_service.vector_store, 'clear_licitacao_vectors'):
                        self.rag_service.vector_store.clear_licitacao_vectors(licitacao_id)
                    # Invalidar cache
                    self.rag_service.cache_manager.invalidate_licitacao_cache(licitacao_id)
                except Exception as clean_error:
                    logger.warning(f"⚠️ Erro na limpeza: {clean_error}")
            
            # Forçar reprocessamento
            result = self.rag_service._ensure_documents_processed(licitacao_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Reprocessamento iniciado com sucesso',
                    'data': result
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Erro no reprocessamento')
                }), 500
                
        except Exception as e:
            logger.error(f"❌ Erro no reprocessamento: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    # 🆕 NOVO MÉTODO: Endpoint de vetorização para preparação automática
    def vectorize_documents(self) -> Dict[str, Any]:
        """Endpoint para vetorização de documentos (usado na preparação automática)"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON payload obrigatório'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            logger.info(f"🔄 Iniciando vetorização para licitacao_id: {licitacao_id}")
            
            # Chamar o método de vetorização do RAG service
            result = self.rag_service._vectorize_licitacao(licitacao_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Vetorização concluída com sucesso',
                    'data': {
                        'licitacao_id': licitacao_id,
                        'processed_documents': result.get('processed_documents', 0),
                        'total_chunks': result.get('total_chunks', 0),
                        'embedding_cache_hits': result.get('embedding_cache_hits', 0),
                        'already_vectorized': result.get('already_vectorized', False)
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Erro na vetorização'),
                    'details': result.get('processing_details')
                }), 500
                
        except Exception as e:
            logger.error(f"❌ Erro na vetorização: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
