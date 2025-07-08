#!/usr/bin/env python3
"""
Test script to verify PNCP URL fix
This will test both the old (broken) and new (fixed) URLs
"""

import sys
import os
import requests
from datetime import datetime, timedelta

# Add src to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_urls():
    """Test both old and new PNCP URLs"""
    
    # Calculate same date range as adapter
    hoje = datetime.now()
    data_inicial = (hoje - timedelta(days=90)).strftime('%Y%m%d')
    data_final = (hoje + timedelta(days=120)).strftime('%Y%m%d')
    
    # Test parameters
    params = {
        'dataInicial': data_inicial,
        'dataFinal': data_final,
        'pagina': 1,
        'tamanhoPagina': 5,  # Small size for test
        'codigoModalidadeContratacao': 8
    }
    
    # Test URLs
    urls_to_test = [
        ('❌ BROKEN (old)', 'https://pncp.gov.br/api/contratacoes/proposta'),
        ('✅ FIXED (new)', 'https://pncp.gov.br/api/consulta/v1/contratacoes/proposta')
    ]
    
    print("🧪 TESTING PNCP API URLs")
    print("=" * 50)
    print(f"📅 Date range: {data_inicial} to {data_final}")
    print(f"🔧 Parameters: {params}")
    print()
    
    for label, url in urls_to_test:
        print(f"{label}: {url}")
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                result_count = len(data.get('data', []))
                print(f"   ✅ SUCCESS: HTTP {response.status_code} - {result_count} results")
                
                # Show first result if available
                if result_count > 0:
                    first_result = data['data'][0]
                    pncp_id = first_result.get('numeroControlePNCP', 'N/A')
                    titulo = first_result.get('objetoContratacao', 'N/A')[:50]
                    print(f"   📋 First result: {pncp_id} - {titulo}...")
                    
            else:
                print(f"   ❌ ERROR: HTTP {response.status_code}")
                print(f"   📄 Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ REQUEST ERROR: {e}")
        
        print()

def test_adapter_config():
    """Test the adapter configuration"""
    print("🔧 TESTING ADAPTER CONFIGURATION")
    print("=" * 50)
    
    try:
        from config.data_source_config import DataSourceConfig
        from adapters.pncp_adapter import PNCPAdapter
        
        # Test config
        config_manager = DataSourceConfig()
        pncp_config = config_manager.get_provider_config('pncp')
        
        print(f"📋 PNCP Config: {pncp_config}")
        print(f"🔗 API Base URL: {pncp_config.get('api_base_url')}")
        
        # Test adapter creation
        adapter = PNCPAdapter(pncp_config)
        print(f"✅ Adapter created successfully")
        print(f"🔗 Adapter Base URL: {adapter.api_base_url}")
        
        # Test URL construction
        test_url = f"{adapter.api_base_url}/contratacoes/proposta"
        print(f"🌐 Complete URL would be: {test_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 PNCP URL FIX VERIFICATION")
    print("=" * 60)
    print()
    
    # Test URLs directly
    test_urls()
    
    print()
    
    # Test adapter configuration
    test_adapter_config()
    
    print()
    print("✅ URL fix verification complete!") 