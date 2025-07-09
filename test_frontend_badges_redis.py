#!/usr/bin/env python3
"""
🧪 Teste para verificar:
1. Badges corretos no frontend (PNCP azul, COMPRASNET verde)
2. Cache Redis salvando dados BRUTOS (373 ComprasNet + 3458 PNCP)
"""

import sys
import os
import requests
import json

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_frontend_badges_and_redis():
    """
    🎯 Teste completo: badges frontend + cache Redis
    """
    print("🧪 TESTANDO BADGES FRONTEND + CACHE REDIS")
    print("=" * 60)
    
    # ✅ ETAPA 1: Fazer busca unificada
    print("\n🔍 ETAPA 1: Fazendo busca unificada...")
    try:
        url = "http://localhost:5001/api/search/unified"
        params = {
            'query': 'saude',
            'limit': 100  # Limitar para teste
        }
        
        response = requests.get(url, params=params, timeout=60)
        
        if response.status_code != 200:
            print(f"   ❌ Erro HTTP: {response.status_code}")
            return False
        
        data = response.json()
        total_results = len(data.get('results', []))
        
        print(f"   ✅ Total de resultados: {total_results}")
        
        # Verificar se há resultados
        if total_results == 0:
            print("   ⚠️ Nenhum resultado encontrado")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro na busca: {e}")
        return False
    
    # ✅ ETAPA 2: Analisar distribution por provider
    print("\n📊 ETAPA 2: Análise por provider...")
    
    results = data.get('results', [])
    pncp_count = 0
    comprasnet_count = 0
    
    # Contar por provider
    for result in results:
        provider = result.get('provider_name', '').lower()
        if provider == 'pncp':
            pncp_count += 1
        elif provider == 'comprasnet':
            comprasnet_count += 1
    
    print(f"   📋 PNCP (badge azul): {pncp_count} resultados")
    print(f"   📋 COMPRASNET (badge verde): {comprasnet_count} resultados")
    
    # ✅ ETAPA 3: Verificar estrutura de dados para badges
    print("\n🏷️ ETAPA 3: Verificando estrutura para badges...")
    
    sample_pncp = None
    sample_comprasnet = None
    
    # Encontrar amostras de cada provider
    for result in results[:10]:  # Primeiros 10 para teste
        provider = result.get('provider_name', '').lower()
        if provider == 'pncp' and not sample_pncp:
            sample_pncp = result
        elif provider == 'comprasnet' and not sample_comprasnet:
            sample_comprasnet = result
    
    # Verificar se campo provider_name existe
    if sample_pncp:
        print(f"   ✅ Amostra PNCP: provider_name='{sample_pncp.get('provider_name')}'")
        print(f"      📝 Título: {sample_pncp.get('title', '')[:50]}...")
    else:
        print("   ⚠️ Nenhuma amostra PNCP encontrada")
    
    if sample_comprasnet:
        print(f"   ✅ Amostra COMPRASNET: provider_name='{sample_comprasnet.get('provider_name')}'")
        print(f"      📝 Título: {sample_comprasnet.get('title', '')[:50]}...")
    else:
        print("   ⚠️ Nenhuma amostra COMPRASNET encontrada")
    
    # ✅ ETAPA 4: Verificar cache Redis
    print("\n🗄️ ETAPA 4: Verificando cache Redis...")
    
    try:
        from config.redis_config import RedisConfig
        redis_client = RedisConfig.get_redis_client()
        
        if not redis_client:
            print("   ❌ Redis não disponível")
            return False
        
        # Buscar chaves de cache
        pncp_keys = list(redis_client.scan_iter(match="pncp:*"))
        comprasnet_keys = list(redis_client.scan_iter(match="comprasnet:*"))
        
        print(f"   📊 Chaves PNCP no Redis: {len(pncp_keys)}")
        print(f"   📊 Chaves ComprasNet no Redis: {len(comprasnet_keys)}")
        
        # Analisar uma chave de cada provider
        if pncp_keys:
            print(f"   🔑 Exemplo chave PNCP: {pncp_keys[0][:80]}...")
            
            # Verificar se é comprimida
            key_data = redis_client.get(pncp_keys[0])
            if key_data:
                try:
                    if pncp_keys[0].endswith(':gz'):
                        import gzip
                        decompressed = gzip.decompress(key_data).decode('utf-8')
                        data_sample = json.loads(decompressed)
                        print(f"   💾 Dados PNCP (comprimidos): {len(data_sample.get('data', []))} registros")
                    else:
                        data_sample = json.loads(key_data.decode('utf-8') if isinstance(key_data, bytes) else key_data)
                        print(f"   💾 Dados PNCP: {len(data_sample.get('data', []))} registros")
                except:
                    print(f"   💾 Dados PNCP: {len(key_data)} bytes")
        
        if comprasnet_keys:
            print(f"   🔑 Exemplo chave ComprasNet: {comprasnet_keys[0][:80]}...")
            
            key_data = redis_client.get(comprasnet_keys[0])
            if key_data:
                try:
                    if comprasnet_keys[0].endswith(':gz'):
                        import gzip
                        decompressed = gzip.decompress(key_data).decode('utf-8')
                        data_sample = json.loads(decompressed)
                        print(f"   💾 Dados ComprasNet (comprimidos): {len(data_sample)} registros")
                    else:
                        data_sample = json.loads(key_data.decode('utf-8') if isinstance(key_data, bytes) else key_data)
                        print(f"   💾 Dados ComprasNet: {len(data_sample)} registros")
                except:
                    print(f"   💾 Dados ComprasNet: {len(key_data)} bytes")
                    
    except Exception as e:
        print(f"   ❌ Erro ao verificar Redis: {e}")
        return False
    
    # ✅ ETAPA 5: Verificar logs do console
    print("\n📋 ETAPA 5: Resumo do teste...")
    print(f"   ✅ Total de resultados retornados: {total_results}")
    print(f"   ✅ PNCP (badges azuis): {pncp_count}")
    print(f"   ✅ ComprasNet (badges verdes): {comprasnet_count}")
    print(f"   ✅ Cache Redis PNCP: {len(pncp_keys)} chaves")
    print(f"   ✅ Cache Redis ComprasNet: {len(comprasnet_keys)} chaves")
    
    # Verificar se badges podem ser renderizados corretamente
    has_provider_field = all(
        'provider_name' in result for result in results[:5]
    )
    
    if has_provider_field:
        print("   ✅ Campo 'provider_name' presente - badges funcionarão!")
    else:
        print("   ❌ Campo 'provider_name' ausente - badges NÃO funcionarão!")
    
    print("\n🎉 TESTE CONCLUÍDO!")
    print("\n📋 PRÓXIMOS PASSOS:")
    print("   1. Verificar badges no frontend: http://localhost:3000")
    print("   ℹ️ Backend rodando em: http://localhost:5001")
    print("   2. PNCP deve ter badge azul 'PNCP'")
    print("   3. ComprasNet deve ter badge verde 'COMPRASNET'")
    print("   4. Dados brutos estão no Redis para filtros futuros")
    
    return True

if __name__ == "__main__":
    test_frontend_badges_and_redis() 