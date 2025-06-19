# Vector store module - Otimizado para VoyageAI

import logging
import psycopg2
from typing import List, Dict, Any, Optional
import numpy as np
import json

logger = logging.getLogger(__name__)

class VectorStore:
    """Armazenamento vetorial usando PostgreSQL + pgvector - Otimizado para VoyageAI"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.embedding_dim = 1024  # VoyageAI voyage-3-large dimensões
        
        logger.info("✅ VectorStore inicializado para VoyageAI (1024 dimensões)")
    
    def save_chunks_with_embeddings(self, documento_id: str, licitacao_id: str, 
                                   chunks: List[Dict], embeddings: List[List[float]]) -> bool:
        """Salva chunks com embeddings no banco"""
        try:
            if len(chunks) != len(embeddings):
                logger.error(f"❌ Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")
                return False
            
            # Validar dimensões dos embeddings
            for i, embedding in enumerate(embeddings):
                if len(embedding) != self.embedding_dim:
                    logger.error(f"❌ Embedding {i} tem {len(embedding)} dimensões, esperado {self.embedding_dim}")
                    return False
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Inserir chunks com embeddings
                    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                        cursor.execute("""
                            INSERT INTO documentos_chunks (
                                documento_id, licitacao_id, chunk_index, chunk_text,
                                chunk_type, page_number, section_title, token_count,
                                char_count, embedding, metadata_chunk
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            documento_id, licitacao_id, i, chunk['text'],
                            chunk.get('chunk_type', 'paragraph'),
                            chunk.get('page_number'),
                            chunk.get('section_title'),
                            chunk.get('token_count'),
                            chunk.get('char_count'),
                            embedding,  # PostgreSQL aceita lista Python diretamente
                            json.dumps(chunk.get('metadata', {}))
                        ))
                    
                    # Atualizar status do documento
                    cursor.execute("""
                        UPDATE documentos_licitacao 
                        SET vetorizado = true, 
                            chunks_count = %s,
                            status_processamento = 'concluido',
                            updated_at = NOW()
                        WHERE id = %s
                    """, (len(chunks), documento_id))
                    
                    conn.commit()
                    
            logger.info(f"✅ {len(chunks)} chunks salvos com embeddings VoyageAI")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar chunks: {e}")
            return False
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], 
                     licitacao_id: str, limit: int = 12) -> List[Dict]:
        """Busca híbrida usando função PostgreSQL otimizada"""
        try:
            logger.info(f"🔍 Busca híbrida para: {query_text[:50]}...")
            logger.info(f"🎯 Licitação ID: {licitacao_id}")
            logger.info(f"📊 Embedding size: {len(query_embedding)}")
            
            # Validar dimensão do embedding
            if len(query_embedding) != self.embedding_dim:
                logger.error(f"❌ Query embedding tem {len(query_embedding)} dimensões, esperado {self.embedding_dim}")
                return []
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Verificar se temos chunks para esta licitação
                    cursor.execute("""
                        SELECT COUNT(*) FROM documentos_chunks 
                        WHERE licitacao_id = %s
                    """, (licitacao_id,))
                    
                    total_chunks = cursor.fetchone()[0]
                    logger.info(f"📋 Total de chunks disponíveis para esta licitação: {total_chunks}")
                    
                    if total_chunks == 0:
                        logger.warning("⚠️ Nenhum chunk encontrado para esta licitação")
                        return []
                    
                    # Verificar se a função hybrid_search existe
                    cursor.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM pg_proc p 
                            JOIN pg_namespace n ON p.pronamespace = n.oid 
                            WHERE n.nspname = 'public' AND p.proname = 'hybrid_search'
                        )
                    """)
                    
                    function_exists = cursor.fetchone()[0]
                    if function_exists:
                        logger.info("✅ Função hybrid_search encontrada no banco")
                    else:
                        logger.error("❌ Função hybrid_search não encontrada")
                        return []
                    
                    # Executar busca híbrida com casting explícito
                    try:
                        cursor.execute("""
                            SELECT * FROM hybrid_search(%s::vector(1024), %s::text, %s::uuid, %s::integer, %s::double precision, %s::double precision)
                        """, (
                            query_embedding,
                            query_text,
                            licitacao_id,
                            limit,
                            0.7,  # peso semântico
                            0.3   # peso textual
                        ))
                        
                        results = cursor.fetchall()
                        
                        # Converter resultados
                        chunks = []
                        for row in results:
                            chunk = {
                                'id': str(row[0]),
                                'text': row[1],
                                'metadata': row[2] or {},
                                'similarity_score': float(row[3]),
                                'text_score': float(row[4]),
                                'hybrid_score': float(row[5]),
                                'final_score': float(row[5])  # Para compatibilidade
                            }
                            chunks.append(chunk)
                        
                        logger.info(f"✅ Busca híbrida retornou {len(chunks)} chunks")
                        return chunks
                        
                    except Exception as search_error:
                        logger.error(f"❌ Erro na função hybrid_search: {search_error}")
                        
                        # Fallback: busca semântica simples
                        logger.info("🔄 Tentando busca semântica simples como fallback...")
                        return self._semantic_search_fallback(cursor, query_embedding, licitacao_id, limit)
                        
        except Exception as e:
            logger.error(f"❌ Erro na busca híbrida: {e}")
            return []
    
    def _semantic_search_fallback(self, cursor, query_embedding: List[float], 
                                 licitacao_id: str, limit: int) -> List[Dict]:
        """Busca semântica simples como fallback"""
        try:
            cursor.execute("""
                SELECT 
                    id, chunk_text, metadata_chunk,
                    1 - (embedding <=> %s) as similarity_score
                FROM documentos_chunks
                WHERE licitacao_id = %s 
                AND embedding IS NOT NULL
                ORDER BY embedding <=> %s
                LIMIT %s
            """, (query_embedding, licitacao_id, query_embedding, limit))
            
            results = cursor.fetchall()
            
            chunks = []
            for row in results:
                chunk = {
                    'id': str(row[0]),
                    'text': row[1],
                    'metadata': row[2] or {},
                    'similarity_score': float(row[3]),
                    'text_score': 0.0,
                    'hybrid_score': float(row[3]),
                    'final_score': float(row[3])
                }
                chunks.append(chunk)
            
            logger.info(f"✅ Busca semântica fallback retornou {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Erro na busca semântica: {e}")
            return []
    
    def check_vectorization_status(self, licitacao_id: str) -> Dict[str, Any]:
        """Verifica status de vetorização de uma licitação"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_documentos,
                            COUNT(*) FILTER (WHERE vetorizado = true) as documentos_vetorizados,
                            SUM(chunks_count) as total_chunks
                        FROM documentos_licitacao 
                        WHERE licitacao_id = %s
                    """, (licitacao_id,))
                    
                    result = cursor.fetchone()
                    
                    return {
                        'total_documentos': result[0],
                        'documentos_vetorizados': result[1],
                        'total_chunks': result[2] or 0,
                        'vetorizado_completo': result[0] > 0 and result[0] == result[1],
                        'embedding_dimensions': self.embedding_dim
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            return {'error': str(e)}
    
    def count_document_chunks(self, documento_id: str) -> int:
        """Conta chunks de um documento específico"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(*) FROM documentos_chunks 
                        WHERE documento_id = %s
                    """, (documento_id,))
                    
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            logger.error(f"❌ Erro ao contar chunks: {e}")
            return 0