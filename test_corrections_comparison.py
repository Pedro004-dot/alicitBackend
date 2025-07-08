#!/usr/bin/env python3
"""
Script para testar as correções aplicadas no pncp_adapter.py
Compara resultados do sistema antigo vs novo após correções
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

async def test_corrections():
    """Teste das correções aplicadas"""
    
    print("🔍 TESTE DE CORREÇÕES - SISTEMA ANTIGO VS NOVO")
    print("=" * 60)
    
    # Configuração de teste
    test_keywords = "limpeza"
    test_filters = {
        'estados': ['SP'],  # São Paulo para ter muitos resultados
        'modalidades': ['pregao_eletronico']
    }
    
    print(f"📋 Filtros de teste:")
    print(f"   🔤 Palavras-chave: '{test_keywords}'")
    print(f"   🗺️ Estados: {test_filters['estados']}")
    print(f"   📋 Modalidades: {test_filters['modalidades']}")
    print()
    
    # ========== TESTE SISTEMA ANTIGO ==========
    print("🔹 TESTANDO SISTEMA ANTIGO (licitacao_repository.py)")
    try:
        repo_antigo = LicitacaoPNCPRepository()
        
        start_time = time.time()
        # CORREÇÃO: Chamar a função assíncrona diretamente com await
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
        print(f"   📄 Páginas consultadas: {metadados_antigo.get('paginasConsultadas', 0)}")
        
        # Amostras
        if data_antigo:
            print(f"   🎯 Primeira licitação:")
            primeira = data_antigo[0]
            print(f"      ID: {primeira.get('numeroControlePNCP', 'N/A')}")
            print(f"      Objeto: {primeira.get('objetoCompra', 'N/A')[:100]}...")
            print(f"      UF: {primeira.get('unidadeOrgao', {}).get('ufSigla', 'N/A')}")
            print(f"      Valor: R$ {primeira.get('valorTotalEstimado', 0):,.2f}")
        
    except Exception as e:
        print(f"   ❌ Erro no sistema antigo: {e}")
        return
    
    print()
    
    # ========== TESTE SISTEMA NOVO ==========
    print("\n\n🔸 TESTANDO SISTEMA NOVO CORRIGIDO (pncp_adapter.py)")
    try:
        # Configurar adapter
        adapter_config = {
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'timeout': 30,
            'max_results': 20000
        }
        novo_adapter = PNCPAdapter(adapter_config)
        
        # Criar filtros do novo sistema
        filters_novo = SearchFilters(
            keywords=test_keywords,
            region_code=test_filters['estados'][0]
        )
        
        start_time = time.time()
        # CORREÇÃO: Usar await para a função agora assíncrona
        resultado_novo_raw = await novo_adapter.search_opportunities(
            filters=filters_novo
        )
        time_novo = time.time() - start_time
        
        print(f"   ⏱️ Tempo: {time_novo:.2f}s")
        print(f"   📊 Total retornado: {len(resultado_novo_raw)}")
        
        # Amostras
        if resultado_novo_raw:
            print(f"   🎯 Primeira licitação:")
            primeira = resultado_novo_raw[0]
            print(f"      ID: {primeira.external_id}")
            print(f"      Título: {primeira.title[:100]}...")
            print(f"      UF: {primeira.region_code}")
            print(f"      Valor: R$ {primeira.estimated_value:,.2f}" if primeira.estimated_value else "N/A")
        
    except Exception as e:
        print(f"   ❌ Erro no sistema novo: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    
    # ========== COMPARAÇÃO DOS RESULTADOS ==========
    print("📊 COMPARAÇÃO DOS RESULTADOS")
    print("=" * 40)
    
    total_antigo = len(data_antigo)
    total_novo = len(resultado_novo_raw)
    
    print(f"📈 Sistema Antigo: {total_antigo} licitações")
    print(f"📈 Sistema Novo:   {total_novo} licitações")
    
    if total_antigo > 0:
        percentual = (total_novo / total_antigo) * 100
        print(f"📊 Percentual:     {percentual:.1f}%")
        
        if percentual >= 90:
            print("✅ CORREÇÕES FUNCIONARAM! Resultados similares.")
        elif percentual >= 70:
            print("⚠️ Correções parciais. Ainda há diferenças.")
        else:
            print("❌ Correções insuficientes. Grande diferença persiste.")
    
    print(f"⚡ Performance:")
    print(f"   Antigo: {time_antigo:.2f}s")
    print(f"   Novo:   {time_novo:.2f}s")
    if time_antigo > 0:
        speedup = time_antigo / time_novo
        print(f"   Speedup: {speedup:.1f}x")
    
    # ========== ANÁLISE DE IDs ==========
    if data_antigo and resultado_novo_raw:
        print()
        print("🔍 ANÁLISE DE IDs (primeiros 10)")
        
        ids_antigo = {item.get('numeroControlePNCP') for item in data_antigo[:10]}
        ids_novo = {item.external_id for item in resultado_novo_raw[:10]}
        
        ids_comuns = ids_antigo.intersection(ids_novo)
        ids_apenas_antigo = ids_antigo - ids_novo
        ids_apenas_novo = ids_novo - ids_antigo
        
        print(f"   🤝 IDs em comum: {len(ids_comuns)}")
        print(f"   🔹 Apenas no antigo: {len(ids_apenas_antigo)}")
        print(f"   🔸 Apenas no novo: {len(ids_apenas_novo)}")
        
        if ids_apenas_antigo:
            print(f"   📋 Exemplo apenas antigo: {list(ids_apenas_antigo)[:3]}")
        if ids_apenas_novo:
            print(f"   📋 Exemplo apenas novo: {list(ids_apenas_novo)[:3]}")

if __name__ == "__main__":
    asyncio.run(test_corrections()) 