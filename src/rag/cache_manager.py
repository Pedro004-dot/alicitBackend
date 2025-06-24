# Cache manager module 

import redis
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
import pickle
from datetime import datetime, timedelta
from config.redis_config import RedisConfig

logger = logging.getLogger(__name__)

class CacheManager:
    """Gerenciador de cache Redis para RAG com suporte ao Railway"""
    
    def __init__(self, default_ttl: int = 3600, **kwargs):
        """
        Inicializa CacheManager usando configuração unificada
        kwargs são mantidos para compatibilidade mas ignorados
        """
        self.default_ttl = default_ttl  # 1 hora padrão
        
        # 🔧 NOVA CONFIGURAÇÃO: Usar RedisConfig unificado
        logger.info("🔄 Inicializando Redis com configuração unificada...")
        self.redis_client = RedisConfig.get_redis_client()
        
        if self.redis_client:
            # Exibir informações da configuração
            redis_info = RedisConfig.get_redis_info()
            url_info = redis_info.get('url_safe', f"{redis_info['host']}:{redis_info['port']}")
            logger.info(f"📊 Redis configurado: {redis_info['type']} - {url_info}")
        else:
            logger.warning("⚠️ Redis não disponível - cache desabilitado")
    
    def _generate_key(self, prefix: str, identifier: str) -> str:
        """Gera chave padronizada para cache"""
        hash_id = hashlib.md5(identifier.encode()).hexdigest()
        return f"rag:{prefix}:{hash_id}"
    
    def cache_embeddings(self, text: str, embedding: List[float], ttl: Optional[int] = None) -> bool:
        """Cacheia embedding de um texto"""
        if not self.redis_client:
            return False
        
        try:
            key = self._generate_key("embedding", text)
            data = {
                'embedding': embedding,
                'cached_at': datetime.now().isoformat(),
                'text_hash': hashlib.sha256(text.encode()).hexdigest()
            }
            
            ttl = ttl or self.default_ttl * 24  # Embeddings duram mais
            serialized = pickle.dumps(data)
            
            return self.redis_client.setex(key, ttl, serialized)
            
        except Exception as e:
            logger.error(f"❌ Erro ao cachear embedding: {e}")
            return False
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Recupera embedding cacheado"""
        if not self.redis_client:
            return None
        
        try:
            key = self._generate_key("embedding", text)
            cached = self.redis_client.get(key)
            
            if cached:
                data = pickle.loads(cached)
                
                # Verificar integridade
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                if data.get('text_hash') == text_hash:
                    logger.debug("✅ Embedding encontrado no cache")
                    return data['embedding']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar embedding: {e}")
            return None
    
    def cache_query_result(self, query: str, licitacao_id: str, 
                          result: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cacheia resultado de consulta RAG"""
        if not self.redis_client:
            return False
        
        try:
            identifier = f"{query}:{licitacao_id}"
            key = self._generate_key("query", identifier)
            
            data = {
                'result': result,
                'query': query,
                'licitacao_id': licitacao_id,
                'cached_at': datetime.now().isoformat()
            }
            
            ttl = ttl or self.default_ttl
            serialized = pickle.dumps(data)
            
            return self.redis_client.setex(key, ttl, serialized)
            
        except Exception as e:
            logger.error(f"❌ Erro ao cachear consulta: {e}")
            return False
    
    def get_cached_query_result(self, query: str, licitacao_id: str) -> Optional[Dict[str, Any]]:
        """Recupera resultado de consulta cacheado"""
        if not self.redis_client:
            return None
        
        try:
            identifier = f"{query}:{licitacao_id}"
            key = self._generate_key("query", identifier)
            cached = self.redis_client.get(key)
            
            if cached:
                data = pickle.loads(cached)
                logger.debug("✅ Resultado de consulta encontrado no cache")
                return data['result']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar consulta: {e}")
            return None
    
    def invalidate_licitacao_cache(self, licitacao_id: str) -> int:
        """Invalida todos os caches de uma licitação"""
        if not self.redis_client:
            return 0
        
        try:
            pattern = f"rag:query:*{licitacao_id}*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🗑️ {deleted} entradas de cache invalidadas para licitação {licitacao_id}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao invalidar cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        if not self.redis_client:
            return {'status': 'disabled'}
        
        try:
            info = self.redis_client.info()
            
            # Contar chaves por tipo
            embedding_keys = len(self.redis_client.keys("rag:embedding:*"))
            query_keys = len(self.redis_client.keys("rag:query:*"))
            
            return {
                'status': 'active',
                'total_keys': info.get('db0', {}).get('keys', 0),
                'embedding_keys': embedding_keys,
                'query_keys': query_keys,
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats: {e}")
            return {'status': 'error', 'error': str(e)} 