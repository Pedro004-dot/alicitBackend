#!/usr/bin/env python3

"""
Test script to verify PNCP search without cache
This will test if we can get more than 186 results with cache disabled
"""

import os
import sys
import logging

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pncp_no_cache():
    """Test PNCPAdapter with cache disabled"""
    try:
        from interfaces.procurement_data_source import SearchFilters
        from adapters.pncp_adapter import PNCPAdapter
        
        logger.info("🧪 Testing PNCPAdapter without cache...")
        
        # Create test configuration with cache disabled
        config = {
            'name': 'pncp',
            'disable_cache': True,  # Force disable cache
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'rate_limit': 50
        }
        
        # Initialize adapter
        adapter = PNCPAdapter(config)
        
        # Create search filters
        filters = SearchFilters(
            keywords='software',  # Different keyword to avoid any cache
            min_value=5000.0,
            country_code='BR'
        )
        
        logger.info(f"🔍 Searching with filters: {filters}")
        
        # Perform search
        results = adapter.search_opportunities(filters)
        
        logger.info(f"✅ Search completed - Found {len(results)} opportunities")
        
        if len(results) > 186:
            logger.info("🎉 SUCCESS: Found more than 186 results (cache was the issue)")
        else:
            logger.warning(f"⚠️ Still getting {len(results)} results - may need further investigation")
        
        # Show first few results
        for i, result in enumerate(results[:3]):
            logger.info(f"  {i+1}. {result.external_id}: {result.title[:60]}...")
        
        return len(results)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    test_pncp_no_cache() 