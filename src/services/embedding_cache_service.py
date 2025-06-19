# src/services/embedding_cache_service.py
import hashlib
import pickle
import logging
import redis
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.config.database import db_manager


logger = logging.getLogger(__name__)


#criar uma classe para o cache de embeddings

class EmbeddingCacheService:
    """Cache inteligente para embeddings com PostgreSQL + Redis"""
    
    def __init__(self, db_manager, redis_host: str = "localhost"):
        self.db_manager = db_manager
        
        # Redis para cache rápido (opcional)
        try:
            self.redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=False)
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis cache ativo")
        except:
            self.redis_available = False
            logger.warning("⚠️ Redis não disponível, usando apenas PostgreSQL")
        
        self._create_cache_tables()
    
    def _create_cache_tables(self):
        """Criar tabelas de cache se não existirem"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Tabela para cache de embeddings
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS embedding_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        text_hash VARCHAR(64) UNIQUE NOT NULL,
                        text_preview TEXT,
                        embedding VECTOR(768), -- NeralMind BERT português (768 dimensões)
                        model_name VARCHAR(100),
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        accessed_at TIMESTAMPTZ DEFAULT NOW(),
                        access_count INTEGER DEFAULT 1
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash 
                    ON embedding_cache (text_hash);
                    
                    CREATE INDEX IF NOT EXISTS idx_embedding_cache_model 
                    ON embedding_cache (model_name);
                """)
                
                # Tabela para controle de processamento
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processamento_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        resource_type VARCHAR(50) NOT NULL, -- 'licitacao', 'documento'
                        resource_id VARCHAR(255) NOT NULL,
                        process_hash VARCHAR(64) NOT NULL,
                        status VARCHAR(20) DEFAULT 'completed',
                        metadata JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        
                        UNIQUE(resource_type, resource_id, process_hash)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_processamento_cache_resource 
                    ON processamento_cache (resource_type, resource_id);
                """)
                
                conn.commit()
                logger.info("✅ Tabelas de cache criadas/verificadas")
    
    def get_embedding_from_cache(self, text: str, model_name: str = "sentence-transformers") -> Optional[List[float]]:
        """Busca embedding no cache (PostgreSQL + Redis)"""
        text_hash = self._hash_text(text)
        
        # 1. Tentar Redis primeiro (mais rápido)
        if self.redis_available:
            try:
                redis_key = f"emb:{model_name}:{text_hash}"
                cached = self.redis_client.get(redis_key)
                if cached:
                    embedding = pickle.loads(cached)
                    logger.debug("⚡ Embedding encontrado no Redis")
                    return embedding
            except Exception as e:
                logger.warning(f"Erro no Redis: {e}")
        
        # 2. Buscar no PostgreSQL
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT embedding FROM embedding_cache 
                        WHERE text_hash = %s AND model_name = %s
                    """, (text_hash, model_name))
                    
                    result = cursor.fetchone()
                    if result:
                        embedding = result[0]  # PostgreSQL retorna lista diretamente
                        
                        # Atualizar estatísticas de acesso
                        cursor.execute("""
                            UPDATE embedding_cache 
                            SET accessed_at = NOW(), access_count = access_count + 1
                            WHERE text_hash = %s AND model_name = %s
                        """, (text_hash, model_name))
                        conn.commit()
                        
                        # Cache no Redis para próximas consultas
                        if self.redis_available:
                            try:
                                redis_key = f"emb:{model_name}:{text_hash}"
                                self.redis_client.setex(redis_key, 86400, pickle.dumps(embedding))  # 24h
                            except:
                                pass
                        
                        logger.debug("✅ Embedding encontrado no PostgreSQL")
                        return embedding
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar embedding: {e}")
            return None
    
    def save_embedding_to_cache(self, text: str, embedding: List[float], model_name: str = "sentence-transformers") -> bool:
        """Salva embedding no cache"""
        try:
            text_hash = self._hash_text(text)
            text_preview = text[:100] + "..." if len(text) > 100 else text
            
            # Salvar no PostgreSQL
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO embedding_cache (text_hash, text_preview, embedding, model_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (text_hash) DO UPDATE SET
                            accessed_at = NOW(),
                            access_count = embedding_cache.access_count + 1
                    """, (text_hash, text_preview, embedding, model_name))
                    conn.commit()
            
            # Cache no Redis
            if self.redis_available:
                try:
                    redis_key = f"emb:{model_name}:{text_hash}"
                    self.redis_client.setex(redis_key, 86400, pickle.dumps(embedding))
                except:
                    pass
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar embedding: {e}")
            return False
    
    def is_resource_processed(self, resource_type: str, resource_id: str, process_data: Dict[str, Any]) -> bool:
        """Verifica se recurso já foi processado com estes parâmetros"""
        try:
            process_hash = self._hash_process_data(process_data)
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS(
                            SELECT 1 FROM processamento_cache 
                            WHERE resource_type = %s AND resource_id = %s AND process_hash = %s
                        )
                    """, (resource_type, resource_id, process_hash))
                    
                    return cursor.fetchone()[0]
                    
        except Exception as e:
            logger.error(f"❌ Erro ao verificar processamento: {e}")
            return False
    
    def mark_resource_processed(self, resource_type: str, resource_id: str, process_data: Dict[str, Any]) -> bool:
        """Marca recurso como processado"""
        try:
            import json
            process_hash = self._hash_process_data(process_data)
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO processamento_cache (resource_type, resource_id, process_hash, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (resource_type, resource_id, process_hash) DO NOTHING
                    """, (resource_type, resource_id, process_hash, json.dumps(process_data)))
                    conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao marcar processamento: {e}")
            return False
    
    def _hash_text(self, text: str) -> str:
        """Gera hash SHA-256 do texto"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _hash_process_data(self, data: Dict[str, Any]) -> str:
        """Gera hash dos dados de processamento"""
        # Ordenar chaves para hash consistente
        sorted_data = {k: data[k] for k in sorted(data.keys())}
        data_str = str(sorted_data)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Estatísticas do cache"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Stats embeddings
                    cursor.execute("""
                        SELECT 
                            model_name,
                            COUNT(*) as total_embeddings,
                            SUM(access_count) as total_accesses,
                            AVG(access_count) as avg_accesses
                        FROM embedding_cache 
                        GROUP BY model_name
                    """)
                    embedding_stats = cursor.fetchall()
                    
                    # Stats processamento
                    cursor.execute("""
                        SELECT 
                            resource_type,
                            COUNT(*) as total_processed
                        FROM processamento_cache 
                        GROUP BY resource_type
                    """)
                    processing_stats = cursor.fetchall()
                    
                    return {
                        'embedding_stats': {
                            row[0]: {
                                'total_embeddings': row[1],
                                'total_accesses': row[2],
                                'avg_accesses': float(row[3])
                            } for row in embedding_stats
                        },
                        'processing_stats': {row[0]: row[1] for row in processing_stats},
                        'redis_available': self.redis_available
                    }
                    
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats: {e}")
            return {'error': str(e)}