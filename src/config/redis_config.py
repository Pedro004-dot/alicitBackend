import os
import redis
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class RedisConfig:
    """Configuração unificada do Redis que suporta URL completa e Railway"""
    
    @staticmethod
    def get_redis_client():
        """
        Cria cliente Redis baseado na configuração do ambiente
        Suporta tanto URL completa quanto host/port separados
        """
        try:
            # 1. PRIORIDADE: REDIS_URL (padrão Railway)
            redis_url = os.getenv('REDIS_URL')
            
            # 2. FALLBACK: REDIS_HOST (se for URL completa)
            if not redis_url:
                redis_url = os.getenv('REDIS_HOST')
            
            if redis_url and redis_url.startswith('redis://'):
                parsed = urlparse(redis_url)
                
                logger.info(f"🔗 Tentando conectar via URL Redis: {redis_url.split('@')[0]}@[HIDDEN]")
                
                # 🎯 SEMPRE tentar conectar primeiro, independente do hostname
                # Se falhar, aí sim fazer fallback
                
                client = redis.Redis(
                    host=parsed.hostname,
                    port=parsed.port or 6379,
                    password=parsed.password,
                    db=int(os.getenv('REDIS_DB', '0')),
                    decode_responses=False,  # Para pickle
                    socket_connect_timeout=5,  # Timeout menor para falhar mais rápido
                    socket_timeout=5,
                    retry_on_timeout=False  # Não retry se é desenvolvimento
                )
                
                # Testar conexão
                client.ping()
                logger.info("✅ Redis conectado via URL com sucesso")
                return client
                
            else:
                # 2. Fallback para host/port separados (desenvolvimento local)
                host = os.getenv('REDIS_HOST', 'localhost')
                port = int(os.getenv('REDIS_PORT', '6379'))
                password = os.getenv('REDIS_PASSWORD')
                db = int(os.getenv('REDIS_DB', '0'))
                
                # 🎯 Tentar conectar independente do hostname
                
                logger.info(f"🔗 Conectando via host/port local: {host}:{port}")
                
                client = redis.Redis(
                    host=host,
                    port=port,
                    password=password if password else None,
                    db=db,
                    decode_responses=False,
                    socket_connect_timeout=3,  # Timeout ainda menor para desenvolvimento
                    socket_timeout=3,
                    retry_on_timeout=False
                )
                
                # Testar conexão
                client.ping()
                logger.info("✅ Redis local conectado com sucesso")
                return client
        
        except redis.ConnectionError as e:
            # 🔄 Se falhou com URL Railway, tentar localhost como fallback
            redis_url = os.getenv('REDIS_URL', '')
            if 'railway.internal' in redis_url:
                logger.warning(f"⚠️ Redis Railway não acessível: {e}")
                logger.info("🔄 Tentando fallback para Redis local...")
                
                # Tentar localhost sem senha
                try:
                    logger.info("🔗 Tentando Redis local: localhost:6379")
                    local_client = redis.Redis(
                        host='localhost',
                        port=6379,
                        password=None,  # Sem senha para Redis local
                        db=0,
                        decode_responses=False,
                        socket_connect_timeout=3,
                        socket_timeout=3,
                        retry_on_timeout=False
                    )
                    local_client.ping()
                    logger.info("✅ Redis local conectado com sucesso!")
                    return local_client
                except Exception as local_e:
                    logger.info(f"🏠 Redis local também não disponível: {local_e}")
                    logger.info("✅ Sistema funcionará sem cache (normal em desenvolvimento)")
            else:
                logger.warning(f"⚠️ Redis não disponível: {e}")
                logger.info("💡 Sistema continuará funcionando sem cache")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao configurar Redis: {e}")
            return None
    
    @staticmethod
    def get_redis_info():
        """Retorna informações da configuração Redis"""
        redis_url = os.getenv('REDIS_URL') or os.getenv('REDIS_HOST', 'localhost')
        
        if redis_url.startswith('redis://'):
            parsed = urlparse(redis_url)
            return {
                'type': 'url',
                'host': parsed.hostname,
                'port': parsed.port or 6379,
                'has_password': bool(parsed.password),
                'db': int(os.getenv('REDIS_DB', '0')),
                'url_safe': f"redis://[USER]:[PASS]@{parsed.hostname}:{parsed.port or 6379}"
            }
        else:
            return {
                'type': 'host_port',
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', '6379')),
                'has_password': bool(os.getenv('REDIS_PASSWORD')),
                'db': int(os.getenv('REDIS_DB', '0'))
            } 