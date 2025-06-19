#!/usr/bin/env python3
"""
Script para limpar embeddings de dimensões incorretas do Redis
"""
import redis
import pickle
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_redis_embeddings():
    """Limpar embeddings de 384 dimensões do Redis"""
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
        redis_client.ping()
        logger.info("✅ Redis conectado")
        
        # Buscar todas as chaves de embeddings
        embedding_keys = redis_client.keys("emb:*")
        logger.info(f"📊 Total de chaves encontradas: {len(embedding_keys)}")
        
        removed_count = 0
        kept_count = 0
        error_count = 0
        
        for key in embedding_keys:
            try:
                # Recuperar embedding
                cached_data = redis_client.get(key)
                if cached_data:
                    embedding = pickle.loads(cached_data)
                    
                    # Verificar dimensões
                    if isinstance(embedding, list) and len(embedding) == 384:
                        # Remover embedding de 384 dimensões
                        redis_client.delete(key)
                        removed_count += 1
                        if removed_count <= 5:  # Log apenas os primeiros 5
                            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                            logger.info(f"🗑️ Removido: {key_str} (384 dim)")
                    elif isinstance(embedding, list) and len(embedding) == 768:
                        # Manter embedding de 768 dimensões
                        kept_count += 1
                    else:
                        # Embedding com dimensões estranhas
                        logger.warning(f"⚠️ Embedding com {len(embedding) if isinstance(embedding, list) else 'N/A'} dimensões: {key}")
                        
            except Exception as e:
                error_count += 1
                if error_count <= 3:  # Log apenas os primeiros 3 erros
                    logger.error(f"❌ Erro ao processar chave {key}: {e}")
        
        logger.info(f"\n📊 RESULTADO:")
        logger.info(f"   🗑️ Removidos (384 dim): {removed_count}")
        logger.info(f"   ✅ Mantidos (768 dim): {kept_count}")
        logger.info(f"   ❌ Erros: {error_count}")
        
        # Verificar resultado final
        remaining_keys = redis_client.keys("emb:*")
        logger.info(f"   📋 Chaves restantes: {len(remaining_keys)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar no Redis: {e}")
        return False

if __name__ == "__main__":
    print("🔧 LIMPEZA DE EMBEDDINGS REDIS")
    print("=" * 50)
    
    success = fix_redis_embeddings()
    
    if success:
        print("\n✅ Limpeza concluída com sucesso!")
        print("🚀 Sistema pronto para usar apenas embeddings de 768 dimensões")
    else:
        print("\n❌ Falha na limpeza do Redis") 