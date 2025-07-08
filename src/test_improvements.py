#!/usr/bin/env python3
"""
Test script for Phase 3 improvements:
1. Synonym service integration
2. External pagination for 5000+ results
3. Provider-specific filters (no global filters)
"""

import os
import sys
import logging
from typing import Dict, Any

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from interfaces.procurement_data_source import SearchFilters
from utils.search.synonym_service import generate_synonyms, synonym_service
from services.unified_search_service import UnifiedSearchService
from adapters.pncp_adapter import PNCPAdapter
from config.data_source_config import DataSourceConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_synonym_service():
    """Test the new synonym service functionality"""
    print("\n" + "="*60)
    print("TEST 1: SYNONYM SERVICE")
    print("="*60)
    
    try:
        # Test if synonym service is available
        print(f"🔤 Synonym service available: {synonym_service.is_available()}")
        
        # Test synonym generation
        test_keywords = ["software", "computador", "licitação"]
        
        for keyword in test_keywords:
            synonyms = generate_synonyms(keyword, max_synonyms=5)
            print(f"🔤 '{keyword}' → {synonyms}")
        
        print("✅ Synonym service test completed")
        return True
        
    except Exception as e:
        print(f"❌ Synonym service test failed: {e}")
        return False


def test_unified_search_with_synonyms():
    """Test UnifiedSearchService with synonym integration"""
    print("\n" + "="*60)
    print("TEST 2: UNIFIED SEARCH WITH SYNONYMS")
    print("="*60)
    
    try:
        # Initialize unified search service
        unified_service = UnifiedSearchService()
        
        # Test search with keywords that should be expanded
        test_filters = SearchFilters(
            keywords="software",
            region_code="MG",
            page=1,
            page_size=10
        )
        
        print(f"🔍 Testing search with filters: {test_filters}")
        
        # Test combined search (this should expand keywords internally)
        results = unified_service.search_combined(test_filters)
        
        print(f"✅ Combined search returned {len(results)} results")
        
        # Test provider-specific search
        pncp_results = unified_service.search_by_provider("pncp", test_filters)
        print(f"✅ PNCP-specific search returned {len(pncp_results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Unified search test failed: {e}")
        return False


def test_pncp_pagination():
    """Test PNCP external pagination for 5000+ results"""
    print("\n" + "="*60)
    print("TEST 3: PNCP EXTERNAL PAGINATION")
    print("="*60)
    
    try:
        # Initialize PNCP adapter with config
        config = {
            'enabled': True,
            'api_base_url': 'https://pncp.gov.br/api',
            'timeout': 30,
            'rate_limit': 100
        }
        
        pncp_adapter = PNCPAdapter(config)
        
        print(f"📄 PNCP Adapter initialized:")
        print(f"   - Target results: {pncp_adapter.target_total_results}")
        print(f"   - API page size: {pncp_adapter.api_page_size}")
        print(f"   - Max pages: {pncp_adapter.max_pages_to_fetch}")
        
        # Test search with pagination
        test_filters = SearchFilters(
            keywords="equipamento",
            region_code="SP",
            page=1,
            page_size=50  # Request 50 results from our paginated data
        )
        
        print(f"🔍 Testing PNCP search with external pagination...")
        
        # This should trigger external pagination to fetch 5000+ results
        # then return the requested page
        results = pncp_adapter.search_opportunities(test_filters)
        
        print(f"✅ PNCP pagination test returned {len(results)} results for requested page")
        
        # Test supported filters
        supported_filters = pncp_adapter.get_supported_filters()
        print(f"📋 PNCP supported filters: {supported_filters}")
        
        return True
        
    except Exception as e:
        print(f"❌ PNCP pagination test failed: {e}")
        return False


def test_provider_specific_filters():
    """Test provider-specific filter support"""
    print("\n" + "="*60)
    print("TEST 4: PROVIDER-SPECIFIC FILTERS")
    print("="*60)
    
    try:
        # Test PNCP provider filters
        config = {'enabled': True}
        pncp_adapter = PNCPAdapter(config)
        
        # Get provider metadata including supported filters
        metadata = pncp_adapter.get_provider_metadata()
        
        print(f"🏢 Provider: {metadata['name']}")
        print(f"📋 Supported filters: {metadata['supported_filters']}")
        print(f"🌍 Data coverage: {metadata['data_coverage']}")
        print(f"💱 Default currency: {metadata['default_currency']}")
        
        # Test filters with provider-specific data
        test_filters = SearchFilters(
            keywords="material",
            region_code="RJ",
            min_value=10000.0,
            currency_code="BRL",
            page_size=20,
            provider_specific_filters={
                'modalidade': 'pregao_eletronico',
                'orgao': 'ministerio_saude'
            }
        )
        
        print(f"🔧 Testing with provider-specific filters: {test_filters.provider_specific_filters}")
        
        # This should work with PNCP-specific filters
        results = pncp_adapter.search_opportunities(test_filters)
        
        print(f"✅ Provider-specific filters test completed - {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Provider-specific filters test failed: {e}")
        return False


def main():
    """Run all improvement tests"""
    print("🚀 Testing Phase 3 Improvements")
    print("=" * 60)
    
    tests = [
        ("Synonym Service", test_synonym_service),
        ("Unified Search with Synonyms", test_unified_search_with_synonyms),
        ("PNCP External Pagination", test_pncp_pagination),
        ("Provider-Specific Filters", test_provider_specific_filters)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASSED" if passed_test else "❌ FAILED"
        print(f"{status} - {test_name}")
        if passed_test:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All improvements working correctly!")
        return 0
    else:
        print("⚠️ Some improvements need attention")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 