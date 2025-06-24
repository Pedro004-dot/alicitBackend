# src/services/embedding_cache_service.py
import hashlib
import pickle
import logging
import redis
from typing import List, Optional, Dict, Any
from datetime import datetime
from config.redis_config import RedisConfig

logger = logging.getLogger(__name__)

class EmbeddingCacheService:
    """Cache de embeddings usando APENAS Redis local (simplificado para matching)"""
    
    def __init__(self, db_manager=None, **kwargs):
        """
        Inicializa EmbeddingCacheService usando APENAS Redis local
        db_manager mantido para compatibilidade mas não usado para cache
        """
        self.db_manager = db_manager
        
        # 🔧 NOVA CONFIGURAÇÃO: Redis LOCAL prioritário
        logger.info("🔄 Inicializando Redis LOCAL para cache de embeddings...")
        self.redis_client = self._get_local_redis_client()
        self.redis_available = self.redis_client is not None
        
        if self.redis_available:
            logger.info("✅ Redis LOCAL ativo para matching")
            # Configurar TTL padrão para embeddings (24h)
            self.default_ttl = 86400
        else:
            logger.warning("⚠️ Redis LOCAL não disponível - matching sem cache")
            logger.warning("💡 Para ativar cache: docker run -d -p 6379:6379 redis:alpine")
    
    def _get_local_redis_client(self):
        """Conecta especificamente ao Redis local, ignorando Railway/produção"""
        try:
            # 🎯 PRIORIZAR Redis local para desenvolvimento/matching
            logger.info("🔗 Conectando ao Redis LOCAL: localhost:6379")
            
            client = redis.Redis(
                host='localhost',
                port=6379,
                password=None,  # Redis local sem senha
                db=0,
                decode_responses=False,  # Para pickle
                socket_connect_timeout=2,  # Timeout rápido
                socket_timeout=2,
                retry_on_timeout=False
            )
            
            # Testar conexão
            client.ping()
            logger.info("✅ Redis LOCAL conectado com sucesso!")
            
            # Mostrar estatísticas básicas
            info = client.info()
            memory_used = info.get('used_memory_human', 'N/A')
            total_keys = info.get('db0', {}).get('keys', 0)
            logger.info(f"📊 Redis Stats: {total_keys} keys, {memory_used} memory")
            
            return client
            
        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis LOCAL não conectou: {e}")
            logger.info("💡 Para usar cache, inicie Redis local:")
            logger.info("   🐳 Docker: docker run -d -p 6379:6379 redis:alpine")
            logger.info("   🍺 Homebrew: brew install redis && redis-server")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao conectar Redis LOCAL: {e}")
            return None
    
    def get_embedding_from_cache(self, text: str, model_name: str = "sentence-transformers") -> Optional[List[float]]:
        """Busca embedding no Redis LOCAL"""
        if not self.redis_available:
            return None
            
        try:
            text_hash = self._hash_text(text)
            redis_key = f"match:{model_name}:{text_hash}"
            
            cached = self.redis_client.get(redis_key)
            if cached:
                data = pickle.loads(cached)
                
                # Verificar integridade e atualizar estatísticas
                if data.get('text_hash') == text_hash:
                    # Incrementar contador de acesso
                    access_key = f"stats:{redis_key}"
                    self.redis_client.incr(access_key)
                    self.redis_client.expire(access_key, self.default_ttl)
                    
                    logger.debug("⚡ Embedding encontrado no Redis LOCAL")
                    return data['embedding']
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar embedding no Redis: {e}")
            return None
    
    def save_embedding_to_cache(self, text: str, embedding: List[float], model_name: str = "sentence-transformers") -> bool:
        """Salva embedding no Redis LOCAL"""
        if not self.redis_available:
            return False
            
        try:
            text_hash = self._hash_text(text)
            redis_key = f"match:{model_name}:{text_hash}"
            
            # Preparar dados para cache
            data = {
                'embedding': embedding,
                'text_hash': text_hash,
                'text_preview': text[:100] + "..." if len(text) > 100 else text,
                'model_name': model_name,
                'cached_at': datetime.now().isoformat(),
                'dimensions': len(embedding) if embedding else 0
            }
            
            # Salvar no Redis com TTL
            serialized = pickle.dumps(data)
            success = self.redis_client.setex(redis_key, self.default_ttl, serialized)
            
            if success:
                # Inicializar contador de acesso
                access_key = f"stats:{redis_key}"
                self.redis_client.setex(access_key, self.default_ttl, 1)
                
                logger.debug(f"💾 Embedding salvo no Redis LOCAL: {len(embedding)} dim")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar embedding no Redis: {e}")
            return False
    
    def batch_get_embeddings_from_cache(self, texts: List[str], model_name: str = "sentence-transformers") -> Dict[str, List[float]]:
        """Busca múltiplos embeddings em lote (otimizado para Redis)"""
        if not self.redis_available or not texts:
            return {}
        
        try:
            # Preparar chaves
            text_to_key = {}
            keys_to_fetch = []
            
            for text in texts:
                text_hash = self._hash_text(text)
                redis_key = f"match:{model_name}:{text_hash}"
                text_to_key[text] = redis_key
                keys_to_fetch.append(redis_key)
            
            # Buscar todos de uma vez usando pipeline
            pipe = self.redis_client.pipeline()
            for key in keys_to_fetch:
                pipe.get(key)
            
            results = pipe.execute()
            
            # Processar resultados
            cached_embeddings = {}
            for i, (text, key) in enumerate(text_to_key.items()):
                cached_data = results[i]
                if cached_data:
                    try:
                        data = pickle.loads(cached_data)
                        if data.get('text_hash') == self._hash_text(text):
                            cached_embeddings[text] = data['embedding']
                            
                            # Incrementar contador de acesso
                            access_key = f"stats:{key}"
                            self.redis_client.incr(access_key)
                            self.redis_client.expire(access_key, self.default_ttl)
                    except:
                        continue
            
            if cached_embeddings:
                logger.info(f"⚡ {len(cached_embeddings)}/{len(texts)} embeddings encontrados no cache Redis")
            
            return cached_embeddings
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar embeddings em lote: {e}")
            return {}
    
    def batch_save_embeddings_to_cache(self, texts_and_embeddings: List[tuple], model_name: str = "sentence-transformers") -> bool:
        """Salva múltiplos embeddings em lote (otimizado para Redis)"""
        if not self.redis_available or not texts_and_embeddings:
            return False
        
        try:
            # Usar pipeline para operações em lote
            pipe = self.redis_client.pipeline()
            saved_count = 0
            
            for text, embedding in texts_and_embeddings:
                if not embedding:
                    continue
                    
                text_hash = self._hash_text(text)
                redis_key = f"match:{model_name}:{text_hash}"
                
                # Preparar dados
                data = {
                    'embedding': embedding,
                    'text_hash': text_hash,
                    'text_preview': text[:100] + "..." if len(text) > 100 else text,
                    'model_name': model_name,
                    'cached_at': datetime.now().isoformat(),
                    'dimensions': len(embedding)
                }
                
                # Adicionar ao pipeline
                serialized = pickle.dumps(data)
                pipe.setex(redis_key, self.default_ttl, serialized)
                
                # Inicializar contador de acesso
                access_key = f"stats:{redis_key}"
                pipe.setex(access_key, self.default_ttl, 1)
                
                saved_count += 1
            
            # Executar pipeline
            pipe.execute()
            
            logger.info(f"💾 {saved_count} embeddings salvos no Redis LOCAL em lote")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar embeddings em lote: {e}")
            return False
    
    def clear_cache(self, pattern: str = "match:*") -> int:
        """Limpa cache por padrão"""
        if not self.redis_available:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🗑️ {deleted} chaves removidas do cache")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Estatísticas do cache Redis LOCAL"""
        if not self.redis_available:
            return {
                'status': 'disabled',
                'message': 'Redis LOCAL não disponível'
            }
        
        try:
            # Info básico do Redis
            info = self.redis_client.info()
            
            # Contar chaves por tipo
            match_keys = self.redis_client.keys("match:*")
            stats_keys = self.redis_client.keys("stats:*")
            
            # Calcular estatísticas de acesso
            total_accesses = 0
            if stats_keys:
                pipe = self.redis_client.pipeline()
                for key in stats_keys:
                    pipe.get(key)
                access_counts = pipe.execute()
                total_accesses = sum(int(count) if count else 0 for count in access_counts)
            
            # Análise por modelo
            models_stats = {}
            for key in match_keys:
                try:
                    key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                    parts = key_str.split(':')
                    if len(parts) >= 2:
                        model = parts[1]
                        if model not in models_stats:
                            models_stats[model] = 0
                        models_stats[model] += 1
                except:
                    continue
            
            return {
                'status': 'active',
                'redis_info': {
                    'version': info.get('redis_version', 'N/A'),
                    'memory_used': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_keys': info.get('db0', {}).get('keys', 0)
                },
                'cache_stats': {
                    'match_keys': len(match_keys),
                    'total_accesses': total_accesses,
                    'avg_accesses': round(total_accesses / len(match_keys), 2) if match_keys else 0,
                    'models': models_stats
                },
                'performance': {
                    'hit_rate_estimate': f"{min(95, (total_accesses / len(match_keys)) * 10) if match_keys else 0:.1f}%",
                    'cache_efficiency': 'High' if len(match_keys) > 100 else 'Medium' if len(match_keys) > 10 else 'Low'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter stats do cache: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _hash_text(self, text: str) -> str:
        """Gera hash SHA-256 do texto"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    # Métodos para compatibilidade com deduplicação (delegam para DB se necessário)
    def is_resource_processed(self, resource_type: str, resource_id: str, process_data: Dict[str, Any]) -> bool:
        """Verifica se recurso foi processado (mantém lógica DB para deduplicação)"""
        if not self.db_manager:
            return False
            
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
        """Marca recurso como processado (mantém lógica DB para deduplicação)"""
        if not self.db_manager:
            return False
            
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
    
    def _hash_process_data(self, data: Dict[str, Any]) -> str:
        """Gera hash dos dados de processamento"""
        sorted_data = {k: data[k] for k in sorted(data.keys())}
        data_str = str(sorted_data)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()