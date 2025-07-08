#!/usr/bin/env python3
"""
Test script for corrected PNCPAdapter

This script tests the fixes applied to resolve the method naming issues
and ensure the adapter works with the actual repository implementation.
"""

import os
import sys
import logging

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pncp_adapter():
    """Test PNCPAdapter with simple search"""
    try:
        from interfaces.procurement_data_source import SearchFilters
        from adapters.pncp_adapter import PNCPAdapter
        
        logger.info("🧪 Testing PNCPAdapter...")
        
        # Create test configuration
        config = {
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'rate_limit': 50,
            'redis_host': 'localhost',
            'redis_port': 6379
        }
        
        # Initialize adapter
        adapter = PNCPAdapter(config)
        logger.info("✅ PNCPAdapter initialized successfully")
        
        # Test simple search
        filters = SearchFilters(
            keywords="medicamentos",
            min_value=10000.0
        )
        
        logger.info("🔍 Testing search with simple filters...")
        opportunities = adapter.search_opportunities(filters)
        
        logger.info(f"✅ Search completed: {len(opportunities)} opportunities found")
        
        # Test metadata
        metadata = adapter.get_provider_metadata()
        logger.info(f"✅ Provider metadata: {metadata['name']}")
        
        # Test supported filters
        supported = adapter.get_supported_filters()
        logger.info(f"✅ Supported filters: {list(supported.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pncp_adapter()
    if success:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("💥 Tests failed!")
        sys.exit(1) 