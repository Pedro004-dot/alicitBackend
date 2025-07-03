import redis
import pickle
import logging
from typing import Optional, Any, Dict

from config.redis_config import RedisConfig

logger = logging.getLogger(__name__)

class CacheService:
    """Serviço para gerenciar o cache de dados da aplicação em Redis."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Inicializa o CacheService.

        Args:
            ttl_seconds (int): Tempo de vida padrão para as chaves de cache em segundos.
                               Default é 3600 (1 hora).
        """
        self.redis_client = RedisConfig.get_redis_client()
        self.default_ttl = ttl_seconds
        if self.redis_client:
            logger.info(f"✅ CacheService inicializado com TTL padrão de {self.default_ttl}s")
        else:
            logger.warning("⚠️ CacheService inicializado, mas Redis não está disponível. O cache estará desativado.")

    def get(self, key: str) -> Optional[Any]:
        """
        Busca um valor no cache pela chave.

        Args:
            key (str): A chave a ser buscada.

        Returns:
            Optional[Any]: O valor desserializado se a chave existir, senão None.
        """
        if not self.redis_client:
            return None
        
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                logger.info(f"🎯 CACHE HIT: Chave '{key}' encontrada.")
                return pickle.loads(cached_data)
        except (redis.RedisError, pickle.UnpicklingError) as e:
            logger.warning(f"⚠️ Erro ao ler do cache para a chave '{key}': {e}")
        
        logger.info(f"📥 CACHE MISS: Chave '{key}' não encontrada.")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Define um valor no cache com um tempo de vida (TTL).

        Args:
            key (str): A chave para salvar o valor.
            value (Any): O valor (objeto Python) a ser salvo.
            ttl (Optional[int]): TTL customizado em segundos. Se None, usa o TTL padrão.
        """
        if not self.redis_client:
            return

        try:
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            serialized_value = pickle.dumps(value)
            self.redis_client.setex(key, ttl_to_use, serialized_value)
            logger.info(f"💾 CACHE SET: Chave '{key}' salva com TTL de {ttl_to_use}s.")
        except (redis.RedisError, pickle.PicklingError) as e:
            logger.error(f"❌ Erro ao salvar no cache para a chave '{key}': {e}")
            
    def delete(self, key: str) -> bool:
        """
        Remove uma chave do cache.

        Args:
            key (str): A chave a ser removida.
            
        Returns:
            bool: True se a chave foi removida, False caso contrário.
        """
        if not self.redis_client:
            return False
        
        try:
            result = self.redis_client.delete(key)
            if result > 0:
                logger.info(f"🗑️ CACHE DELETE: Chave '{key}' removida.")
                return True
            return False
        except redis.RedisError as e:
            logger.error(f"❌ Erro ao deletar chave '{key}' do cache: {e}")
            return False

    def clear_prefix(self, prefix: str) -> int:
        """
        Limpa todas as chaves que começam com um determinado prefixo.

        Args:
            prefix (str): O prefixo das chaves a serem removidas (ex: "licitacoes:*").

        Returns:
            int: O número de chaves removidas.
        """
        if not self.redis_client:
            return 0
        
        keys_to_delete = []
        try:
            # Usar `scan_iter` é mais seguro para produção do que `keys()`
            for key in self.redis_client.scan_iter(f"{prefix}*"):
                keys_to_delete.append(key)
            
            if keys_to_delete:
                self.redis_client.delete(*keys_to_delete)
                logger.info(f"🗑️ CACHE CLEAR: {len(keys_to_delete)} chaves com prefixo '{prefix}' removidas.")
                return len(keys_to_delete)
            
            logger.info(f"ℹ️ Nenhuma chave encontrada com o prefixo '{prefix}' para limpar.")
            return 0
        except redis.RedisError as e:
            logger.error(f"❌ Erro ao limpar cache com prefixo '{prefix}': {e}")
            return 0

    def get_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o status do cliente Redis.
        """
        if not self.redis_client:
            return {"status": "indisponivel"}
            
        try:
            info = self.redis_client.info()
            return {
                "status": "conectado",
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "total_keys": info.get("db0", {}).get("keys", "N/A"),
            }
        except redis.RedisError as e:
            return {"status": "erro", "message": str(e)} 