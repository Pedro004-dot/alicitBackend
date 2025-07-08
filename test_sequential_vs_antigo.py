#!/usr/bin/env python3
"""
Script para testar o NOVO método sequencial nacional vs sistema antigo
Foco: Comparar estratégia nacional sequencial (novo) vs estratégia que funciona (antigo)
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

async def test_sequential_nacional():
    """Teste do método sequencial nacional vs sistema antigo"""
    
    print("🔍 TESTE: SEQUENCIAL NACIONAL VS SISTEMA ANTIGO")
    print("=" * 60)
    
    # Configuração de teste
    test_keywords = "limpeza"
    test_filters = {
        'estados': ['SP'],  # São Paulo
        'modalidades': ['pregao_eletronico']
    }
    
    print(f"📋 Filtros de teste:")
    print(f"   🔤 Palavras-chave: '{test_keywords}'")
    print(f"   🗺️ Estados: {test_filters['estados']}")
    print(f"   📋 Modalidades: {test_filters['modalidades']}")
    print()
    
    # ========== TESTE SISTEMA ANTIGO ==========
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
        time_antigo = time.time() - start_time
        
        data_antigo = resultado_antigo.get('data', [])
        metadados_antigo = resultado_antigo.get('metadados', {})
        
        print(f"   ⏱️ Tempo: {time_antigo:.2f}s")
        print(f"   📊 Total bruto: {metadados_antigo.get('totalBruto', 0)}")
        print(f"   📊 Total filtrado: {len(data_antigo)}")
        print(f"   📄 Páginas: {metadados_antigo.get('paginasConsultadas', 0)}")
        
        if data_antigo:
            primeira = data_antigo[0]
            print(f"   🎯 Amostra: {primeira.get('numeroControlePNCP', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return
    
    print()
    
    # ========== TESTE SISTEMA NOVO SEQUENCIAL ==========
    print("🔸 SISTEMA NOVO SEQUENCIAL NACIONAL (pncp_adapter.py)")
    
    # GARANTIR que busca paralela está DESABILITADA
    os.environ['ENABLE_PARALLEL_SEARCH'] = 'false'
    
    try:
        adapter_config = {
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'timeout': 30,
            'max_results': 20000
        }
        novo_adapter = PNCPAdapter(adapter_config)
        
        filters_novo = SearchFilters(
            keywords=test_keywords,
            region_code=test_filters['estados'][0]
        )
        
        start_time = time.time()
        resultado_novo = await novo_adapter.search_opportunities(filters_novo)
        time_novo = time.time() - start_time
        
        print(f"   ⏱️ Tempo: {time_novo:.2f}s")
        print(f"   📊 Total retornado: {len(resultado_novo)}")
        
        if resultado_novo:
            primeira = resultado_novo[0]
            print(f"   🎯 Amostra: {primeira.external_id}")
        
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # ========== COMPARAÇÃO ==========
    print("📊 COMPARAÇÃO DOS RESULTADOS")
    print("=" * 40)
    
    total_antigo = len(data_antigo)
    total_novo = len(resultado_novo)
    
    print(f"📈 Sistema Antigo:    {total_antigo} licitações")
    print(f"📈 Sistema Novo SEQ:  {total_novo} licitações")
    
    if total_antigo > 0:
        percentual = (total_novo / total_antigo) * 100
        print(f"📊 Percentual:        {percentual:.1f}%")
        
        if percentual >= 90:
            print("✅ SEQUENCIAL FUNCIONOU! Resultados equivalentes.")
        elif percentual >= 70:
            print("⚠️ Melhorou mas ainda há diferenças.")
        else:
            print("❌ Ainda há problemas significativos.")
    
    print(f"⚡ Performance:")
    print(f"   Antigo:     {time_antigo:.2f}s")
    print(f"   Novo SEQ:   {time_novo:.2f}s")
    if time_antigo > 0:
        speedup = time_antigo / time_novo
        print(f"   Speedup:    {speedup:.1f}x")
    
    # ========== ANÁLISE DE IDs ==========
    if data_antigo and resultado_novo:
        print()
        print("🔍 ANÁLISE DE IDs (primeiros 5)")
        
        ids_antigo = {item.get('numeroControlePNCP') for item in data_antigo[:5]}
        ids_novo = {item.external_id for item in resultado_novo[:5]}
        
        ids_comuns = ids_antigo.intersection(ids_novo)
        
        print(f"   🤝 IDs em comum: {len(ids_comuns)}/{min(5, len(data_antigo), len(resultado_novo))}")
        
        if ids_comuns:
            print(f"   ✅ Exemplos comuns: {list(ids_comuns)[:3]}")

if __name__ == "__main__":
    asyncio.run(test_sequential_nacional()) 