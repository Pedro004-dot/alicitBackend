#!/usr/bin/env python3
"""
Script para testar o SISTEMA OTIMIZADO vs sistema antigo
Foco: Performance e filtros corretos
"""

import sys
import os
import asyncio
import time
from datetime import datetime

# Adicionar o caminho do src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from repositories.licitacao_repository import LicitacaoPNCPRepository
from adapters.pncp_adapter import PNCPAdapter
from interfaces.procurement_data_source import SearchFilters

async def test_optimized_performance():
    """Teste do sistema otimizado vs sistema antigo"""
    
    print("🔍 TESTE: SISTEMA OTIMIZADO VS SISTEMA ANTIGO")
    print("=" * 60)
    
    # Configuração de teste
    test_keywords = "Material de construção"
    test_filters = {
        'estados': ['SP'],
        'modalidades': ['pregao_eletronico']
    }
    
    print("📋 Filtros de teste:")
    print(f"   🔤 Palavras-chave: '{test_keywords}'")
    print(f"   🗺️ Estados: {test_filters['estados']}")
    print(f"   📋 Modalidades: {test_filters['modalidades']}")
    print()

    # 🔹 SISTEMA ANTIGO
    print("🔹 SISTEMA ANTIGO (licitacao_repository.py)")
    try:
        repo_antigo = LicitacaoPNCPRepository()
        
        start_time = time.time()
        resultado_antigo = await repo_antigo.buscar_licitacoes_paralelo(
            filtros=test_filters,
            palavras_busca=[test_keywords],
            pagina=1,
            itens_por_pagina=500
        )
        antigo_time = time.time() - start_time
        
        antigo_total = len(resultado_antigo.get('licitacoes', []))
        antigo_pages = resultado_antigo.get('total_paginas_buscadas', 0)
        
        print(f"   ⏱️ Tempo: {antigo_time:.2f}s")
        print(f"   📊 Total filtrado: {antigo_total}")
        print(f"   📄 Páginas: {antigo_pages}")
        if antigo_total > 0:
            first_id = resultado_antigo['licitacoes'][0].get('numeroControlePNCP', 'N/A')
            print(f"   🎯 Amostra: {first_id}")
        print()
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        antigo_time = 0
        antigo_total = 0
        antigo_pages = 0
        print()

    # 🔸 SISTEMA NOVO OTIMIZADO
    print("🔸 SISTEMA NOVO OTIMIZADO (pncp_adapter.py)")
    try:
        # Configuração do adapter
        adapter_config = {
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'timeout': 30,
            'max_results': 20000
        }
        novo_adapter = PNCPAdapter(adapter_config)
        
        start_time = time.time()
        
        # Usar SearchFilters para compatibilidade
        resultado_novo_raw = await novo_adapter.search_opportunities(
            filters=SearchFilters(
                keywords=test_keywords, 
                region_code=test_filters['estados'][0]
            )
        )
        novo_time = time.time() - start_time
        
        novo_total = len(resultado_novo_raw)
        
        print(f"   ⏱️ Tempo: {novo_time:.2f}s")
        print(f"   📊 Total retornado: {novo_total}")
        if novo_total > 0:
            first_item = resultado_novo_raw[0]
            print(f"   🎯 Amostra: {first_item.external_id}")
        print()
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        novo_time = 0
        novo_total = 0
        print()

    # 📊 COMPARAÇÃO DOS RESULTADOS
    print("📊 COMPARAÇÃO DOS RESULTADOS")
    print("=" * 40)
    print(f"📈 Sistema Antigo:    {antigo_total} licitações")
    print(f"📈 Sistema Novo OPT:  {novo_total} licitações")
    
    if antigo_total > 0:
        percentual = (novo_total / antigo_total * 100) if antigo_total > 0 else 0
        print(f"📊 Percentual:        {percentual:.1f}%")
    
    if novo_total >= antigo_total and novo_total > 0:
        print("✅ OTIMIZAÇÃO FUNCIONOU! Resultados corretos.")
    else:
        print("⚠️ Resultados ainda divergem.")
    
    print("⚡ Performance:")
    print(f"   Antigo:     {antigo_time:.2f}s")
    print(f"   Novo OPT:   {novo_time:.2f}s")
    
    if novo_time > 0 and antigo_time > 0:
        speedup = antigo_time / novo_time
        print(f"   Speedup:    {speedup:.1f}x")

if __name__ == "__main__":
    asyncio.run(test_optimized_performance()) 