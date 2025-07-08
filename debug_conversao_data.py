#!/usr/bin/env python3

"""
🔍 Debug específico para conversão de dados no PNCPAdapter

Verifica se a data de abertura está sendo extraída corretamente
na função _convert_to_opportunity_data.
"""

import os
import sys
import logging

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from adapters.pncp_adapter import PNCPAdapter

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_conversao_data():
    """🔍 Debug específico para conversão de dados"""
    
    print("🔍 DEBUG: CONVERSÃO DE DADOS NO PNCP ADAPTER")
    print("=" * 50)
    
    # Criar instância do adapter
    config = {'timeout': 30}
    adapter = PNCPAdapter(config)
    
    # ID da licitação que sabemos que existe
    test_pncp_id = "04892707000100-1-000246/2024"
    
    print(f"🎯 Testando com: {test_pncp_id}")
    print()
    
    # Buscar dados via get_opportunity_details
    print("🔍 1. TESTANDO get_opportunity_details")
    print("-" * 40)
    
    opportunity_data = adapter.get_opportunity_details(test_pncp_id)
    
    if opportunity_data:
        print(f"✅ OpportunityData criado com sucesso")
        print(f"   📋 External ID: {opportunity_data.external_id}")
        print(f"   📝 Title: {opportunity_data.title[:100]}...")
        print(f"   📅 Publication Date: {opportunity_data.publication_date}")
        print(f"   📅 Submission Deadline: {opportunity_data.submission_deadline}")
        print(f"   🎯 Provider Specific Data keys: {list(opportunity_data.provider_specific_data.keys())}")
        
        # Verificar dados específicos
        provider_data = opportunity_data.provider_specific_data
        print()
        print("🔍 DADOS ESPECÍFICOS DE DATA:")
        print("-" * 30)
        print(f"   📅 data_abertura_proposta: {provider_data.get('data_abertura_proposta')}")
        print(f"   📅 data_encerramento_proposta: {provider_data.get('data_encerramento_proposta')}")
        print(f"   📅 data_publicacao_pncp: {provider_data.get('data_publicacao_pncp')}")
        
        # Verificar dados brutos
        raw_data = provider_data.get('raw_data', {})
        if raw_data:
            print()
            print("🔍 DADOS BRUTOS DA API:")
            print("-" * 25)
            print(f"   📅 dataAberturaProposta: {raw_data.get('dataAberturaProposta')}")
            print(f"   📅 dataEncerramentoProposta: {raw_data.get('dataEncerramentoProposta')}")
            print(f"   📅 dataPublicacaoPncp: {raw_data.get('dataPublicacaoPncp')}")
        
        print()
        print("🔍 2. TESTANDO CONVERSÃO MANUAL")
        print("-" * 35)
        
        # Testar o parse das datas específicas
        if raw_data:
            data_abertura_str = raw_data.get('dataAberturaProposta')
            if data_abertura_str:
                parsed_date = adapter._parse_pncp_date(data_abertura_str)
                print(f"   📅 String original: {data_abertura_str}")
                print(f"   📅 Data parseada: {parsed_date}")
            else:
                print("   ❌ dataAberturaProposta não encontrada nos dados brutos")
        
    else:
        print("❌ Falha ao buscar opportunity_data")

if __name__ == "__main__":
    debug_conversao_data() 