#!/usr/bin/env python3
"""
Test script para verificar a paginação eficiente do PNCP
"""

import sys
import os
import logging

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from adapters.pncp_adapter import PNCPAdapter
from interfaces.procurement_data_source import SearchFilters

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_efficient_pagination():
    """Testar a paginação eficiente"""
    print("\n" + "="*80)
    print("TESTE DA PAGINAÇÃO EFICIENTE PNCP")
    print("="*80)
    
    # Configurar adapter
    config = {
        'enabled': True,
        'api_base_url': 'https://pncp.gov.br/api',
        'timeout': 30,
        'rate_limit': 100,
        'disable_cache': True  # Desabilitar cache para ver resultados reais
    }
    
    adapter = PNCPAdapter(config)
    
    print(f"📊 Configuração:")
    print(f"   - Target results: {adapter.target_total_results}")
    print(f"   - Pages per target: {adapter.max_pages_to_fetch}")
    print(f"   - Page size: {adapter.api_page_size}")
    print(f"   - Cache disabled: {config.get('disable_cache', False)}")
    
    # Teste 1: Busca específica por UF
    print(f"\n{'='*50}")
    print("TESTE 1: BUSCA ESPECÍFICA POR UF (SP)")
    print("="*50)
    
    filters_sp = SearchFilters(
        keywords="equipamento",
        region_code="SP",
        page=1,
        page_size=50
    )
    
    print(f"🔍 Iniciando busca em SP...")
    results_sp = adapter.search_opportunities(filters_sp)
    print(f"✅ SP Results: {len(results_sp)} licitações encontradas")
    
    # Teste 2: Busca nacional (limitada para não sobrecarregar)
    print(f"\n{'='*50}")
    print("TESTE 2: BUSCA NACIONAL (PRIMEIROS 3 ESTADOS)")
    print("="*50)
    
    # Modificar temporariamente para testar só alguns estados
    original_ufs = None
    
    def limited_national_search():
        # Sobrescrever o método temporariamente para limitar UFs
        original_method = adapter._fetch_with_efficient_pagination
        
        def limited_fetch(filtros):
            # Força busca em apenas 3 estados para teste
            filtros['test_mode'] = True
            return original_method(filtros)
        
        adapter._fetch_with_efficient_pagination = limited_fetch
        
        filters_national = SearchFilters(
            keywords="serviço",
            page=1,
            page_size=100
        )
        
        print(f"🌍 Iniciando busca nacional limitada...")
        results_national = adapter.search_opportunities(filters_national)
        print(f"✅ National Results: {len(results_national)} licitações encontradas")
        
        # Restaurar método original
        adapter._fetch_with_efficient_pagination = original_method
        return results_national
    
    results_national = limited_national_search()
    
    # Resumo
    print(f"\n{'='*50}")
    print("RESUMO DOS TESTES")
    print("="*50)
    print(f"🎯 SP (específico): {len(results_sp)} resultados")
    print(f"🌍 Nacional (limitado): {len(results_national)} resultados")
    print(f"📊 Total testado: {len(results_sp) + len(results_national)} licitações")
    
    # Verificar se temos resultados significativos
    if len(results_sp) > 50:
        print(f"✅ SP search: SUCESSO - mais de 50 resultados!")
    else:
        print(f"⚠️ SP search: apenas {len(results_sp)} resultados")
    
    if len(results_national) > 100:
        print(f"✅ National search: SUCESSO - mais de 100 resultados!")
    else:
        print(f"⚠️ National search: apenas {len(results_national)} resultados")
    
    print(f"\n🎉 Teste da paginação eficiente concluído!")

def test_api_direct():
    """Teste direto da API para verificar se está funcionando"""
    print(f"\n{'='*50}")
    print("TESTE DIRETO DA API PNCP")
    print("="*50)
    
    from matching.pncp_api import fetch_bids_from_pncp
    from datetime import datetime, timedelta
    
    # Parâmetros de teste - CORRIGIR DATAS PARA PASSADO
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    # Para ter certeza que funcionará, usar datas específicas recentes
    end_date = "2025-01-07"  # Data recente passada
    start_date = "2024-12-07"  # 1 mês antes
    
    uf = "SP"
    page = 1
    
    print(f"🔍 Testando API direta:")
    print(f"   - UF: {uf}")
    print(f"   - Data: {start_date} a {end_date}")
    print(f"   - Página: {page}")
    
    try:
        results, has_more = fetch_bids_from_pncp(start_date, end_date, uf, page)
        print(f"✅ API Results: {len(results)} licitações na página {page}")
        print(f"📄 Has more pages: {has_more}")
        
        if results:
            first_result = results[0]
            print(f"📋 Primeira licitação: {first_result.get('numeroControlePNCP', 'N/A')} - {first_result.get('objetoCompra', 'N/A')[:50]}...")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Erro na API: {e}")
        return False

if __name__ == "__main__":
    try:
        # Teste API primeiro
        api_works = test_api_direct()
        
        if api_works:
            print(f"\n✅ API funcionando - continuando com teste de paginação")
            test_efficient_pagination()
        else:
            print(f"\n❌ API não está funcionando - verifique conectividade")
            
    except Exception as e:
        print(f"\n💥 Erro durante teste: {e}")
        import traceback
        traceback.print_exc() 