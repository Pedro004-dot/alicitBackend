#!/usr/bin/env python3
"""
🧹 Script para limpar cache PNCP do Redis
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def clear_pncp_cache():
    """Limpa todas as chaves PNCP do Redis"""
    
    try:
        from config.redis_config import RedisConfig
        
        print("🔗 Conectando ao Redis...")
        redis_client = RedisConfig.get_redis_client()
        
        if not redis_client:
            print("❌ Não foi possível conectar ao Redis")
            return False
            
        print("✅ Conectado ao Redis")
        
        # Listar chaves PNCP antes da limpeza
        pncp_keys = list(redis_client.scan_iter(match='pncp*'))
        print(f"🔍 Encontradas {len(pncp_keys)} chaves PNCP no cache")
        
        if pncp_keys:
            print("📋 Chaves encontradas:")
            for key in pncp_keys[:10]:  # Mostrar até 10 chaves
                key_str = key.decode() if isinstance(key, bytes) else key
                print(f"   - {key_str}")
            if len(pncp_keys) > 10:
                print(f"   ... e mais {len(pncp_keys) - 10} chaves")
        
        # Limpar todas as chaves PNCP
        if pncp_keys:
            deleted_count = 0
            for key in pncp_keys:
                redis_client.delete(key)
                deleted_count += 1
            
            print(f"🧹 Cache limpo: {deleted_count} chaves PNCP removidas")
        else:
            print("📭 Nenhuma chave PNCP encontrada no cache")
        
        # Verificar se limpeza foi bem-sucedida
        remaining_keys = list(redis_client.scan_iter(match='pncp*'))
        if remaining_keys:
            print(f"⚠️ Ainda restam {len(remaining_keys)} chaves PNCP")
            return False
        else:
            print("✅ Cache PNCP completamente limpo!")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao limpar cache: {e}")
        return False

if __name__ == "__main__":
    print("🧹 LIMPEZA DE CACHE PNCP")
    print("=" * 40)
    
    success = clear_pncp_cache()
    
    if success:
        print("\n🎉 Cache limpo com sucesso!")
        print("Agora você pode executar testes sem interferência de cache.")
    else:
        print("\n❌ Falha na limpeza do cache.") 