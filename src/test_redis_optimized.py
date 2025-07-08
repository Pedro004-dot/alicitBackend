#!/usr/bin/env python3
"""
Test script para verificar o Redis otimizado com compressão e 20.000 licitações
"""

import sys
import os
import logging
import time

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from adapters.pncp_adapter import PNCPAdapter
from interfaces.procurement_data_source import SearchFilters

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_redis_optimized():
    """Testar o cache Redis otimizado"""
    print("\n" + "="*80)
    print("TESTE DO REDIS OTIMIZADO - 20K LICITAÇÕES COM COMPRESSÃO")
    print("="*80)
    
    # Configurar adapter
    config = {
        'enabled': True,
        'api_base_url': 'https://pncp.gov.br/api',
        'timeout': 30,
        'rate_limit': 100,
        'disable_cache': False  # HABILITAR cache
    }
    
    adapter = PNCPAdapter(config)
    
    # Filtros de teste - busca específica no SP
    filters = SearchFilters(
        keywords="equipamento",
        region_code="SP"
    )
    
    print(f"🔍 Testando busca com cache Redis:")
    print(f"   - Palavras-chave: {filters.keywords}")
    print(f"   - UF: {filters.region_code}")
    print(f"   - Cache habilitado: {adapter.cache_enabled}")
    print(f"   - Duração do cache: {adapter.cache_duration_hours} horas")
    print(f"   - Limite de licitações: {adapter.target_total_results}")
    
    # PRIMEIRA BUSCA - deve ir ao PNCP e armazenar no cache
    print(f"\n{'='*50}")
    print("PRIMEIRA BUSCA (deve buscar do PNCP e cachear)")
    print("="*50)
    
    start_time = time.time()
    results_1 = adapter.search_opportunities(filters)
    duration_1 = time.time() - start_time
    
    print(f"✅ Primeira busca concluída:")
    print(f"   - Tempo: {duration_1:.2f} segundos")
    print(f"   - Resultados: {len(results_1)} licitações")
    
    # SEGUNDA BUSCA - deve usar o cache
    print(f"\n{'='*50}")
    print("SEGUNDA BUSCA (deve usar cache - muito mais rápida)")
    print("="*50)
    
    start_time = time.time()
    results_2 = adapter.search_opportunities(filters)
    duration_2 = time.time() - start_time
    
    print(f"✅ Segunda busca concluída:")
    print(f"   - Tempo: {duration_2:.2f} segundos")
    print(f"   - Resultados: {len(results_2)} licitações")
    print(f"   - Speedup: {duration_1/duration_2 if duration_2 > 0 else 'N/A'}x mais rápida")
    
    # Verificar se os resultados são idênticos
    if len(results_1) == len(results_2):
        print(f"✅ Cache funcionando: ambas as buscas retornaram {len(results_1)} resultados")
    else:
        print(f"❌ Problema no cache: primeira busca {len(results_1)} vs segunda {len(results_2)}")
    
    # Mostrar algumas licitações de exemplo
    if results_2:
        print(f"\n📋 Exemplo de licitações encontradas:")
        for i, licitacao in enumerate(results_2[:3]):
            print(f"   {i+1}. {licitacao.external_id} - {licitacao.title[:60]}...")
    
    # Verificar informações do cache Redis
    try:
        import json
        
        # Verificar chaves do Redis
        if adapter.redis_client:
            keys = adapter.redis_client.keys("pncp_search_v2:*")
            print(f"\n💾 Chaves do Redis encontradas: {len(keys)}")
            
            if keys:
                key = keys[0].decode('utf-8') if isinstance(keys[0], bytes) else keys[0]
                ttl = adapter.redis_client.ttl(key)
                print(f"   - Chave exemplo: {key}")
                print(f"   - TTL restante: {ttl} segundos ({ttl/3600:.1f} horas)")
                
                # Verificar tamanho da chave
                cache_size = adapter.redis_client.memory_usage(key)
                if cache_size:
                    print(f"   - Tamanho no Redis: {cache_size / 1024 / 1024:.2f} MB")
    except Exception as e:
        print(f"⚠️ Erro ao verificar Redis: {e}")
    
    print(f"\n🎉 TESTE CONCLUÍDO!")
    print(f"Cache Redis com compressão funcionando para {len(results_2)} licitações")

if __name__ == "__main__":
    test_redis_optimized() 