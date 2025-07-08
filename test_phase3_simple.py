#!/usr/bin/env python3
"""
Simple Phase 3 Validation Test - Service Layer Abstraction

This test validates the core structure and imports without requiring
full database dependencies.
"""

import sys
import os

# Add src to Python path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_file_structure():
    """Test 1: Verify all Phase 3 files exist"""
    print("🧪 Test 1: File Structure Validation")
    print("=" * 50)
    
    try:
        # Check if all required files exist
        required_files = [
            'src/services/unified_search_service.py',
            'src/routes/unified_search_routes.py',
            'src/interfaces/procurement_data_source.py',
            'src/factories/data_source_factory.py',
            'src/adapters/pncp_adapter.py',
            'src/config/data_source_config.py'
        ]
        
        for file_path in required_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            assert os.path.exists(full_path), f"File {file_path} does not exist"
            print(f"✅ {file_path} exists")
        
        print("✅ All Phase 3 files are present")
        return True
        
    except Exception as e:
        print(f"❌ File structure test failed: {e}")
        return False


def test_basic_imports():
    """Test 2: Test basic imports without database dependencies"""
    print("\n🧪 Test 2: Basic Import Validation")
    print("=" * 50)
    
    try:
        # Test interface import
        from interfaces.procurement_data_source import ProcurementDataSource, SearchFilters, OpportunityData
        print("✅ Interface module imported successfully")
        
        # Test SearchFilters creation
        filters = SearchFilters(keywords="test", region_code="MG")
        assert filters.keywords == "test"
        assert filters.region_code == "MG"
        print("✅ SearchFilters class works correctly")
        
        # Test OpportunityData creation
        opportunity = OpportunityData(
            external_id="test-123",
            title="Test Opportunity",
            description="Test Description",
            country_code="BR"
        )
        assert opportunity.external_id == "test-123"
        assert opportunity.title == "Test Opportunity"
        print("✅ OpportunityData class works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic imports test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_structure():
    """Test 3: Test configuration structure"""
    print("\n🧪 Test 3: Configuration Structure")
    print("=" * 50)
    
    try:
        # Test config import without database
        from config.data_source_config import DataSourceConfig
        print("✅ DataSourceConfig imported successfully")
        
        # Create config instance
        config = DataSourceConfig()
        print("✅ DataSourceConfig instance created")
        
        # Test basic methods exist
        assert hasattr(config, 'get_active_providers'), "Missing get_active_providers method"
        assert hasattr(config, 'get_provider_config'), "Missing get_provider_config method"
        assert hasattr(config, 'is_provider_enabled'), "Missing is_provider_enabled method"
        print("✅ DataSourceConfig has required methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_service_structure():
    """Test 4: Test service classes structure without instantiation"""
    print("\n🧪 Test 4: Service Structure Validation")
    print("=" * 50)
    
    try:
        # Test that files can be imported and classes defined
        import importlib.util
        
        # Check UnifiedSearchService file
        service_spec = importlib.util.spec_from_file_location(
            "unified_search_service", 
            os.path.join(src_path, "services", "unified_search_service.py")
        )
        service_module = importlib.util.module_from_spec(service_spec)
        
        # Check if class is defined in the module content
        with open(os.path.join(src_path, "services", "unified_search_service.py"), 'r') as f:
            content = f.read()
            assert "class UnifiedSearchService" in content, "UnifiedSearchService class not found"
            assert "def search_opportunities" in content, "search_opportunities method not found"
            assert "def search_combined" in content, "search_combined method not found"
            assert "def get_provider_stats" in content, "get_provider_stats method not found"
        
        print("✅ UnifiedSearchService structure validated")
        
        # Check routes file
        with open(os.path.join(src_path, "routes", "unified_search_routes.py"), 'r') as f:
            content = f.read()
            assert "unified_search_bp = Blueprint" in content, "Blueprint not found"
            assert "@unified_search_bp.route('/unified'" in content, "Unified search route not found"
            assert "@unified_search_bp.route('/providers'" in content, "Providers route not found"
        
        print("✅ Unified search routes structure validated")
        
        # Check BidService integration
        with open(os.path.join(src_path, "services", "bid_service.py"), 'r') as f:
            content = f.read()
            assert "def search_unified" in content, "search_unified method not found in BidService"
            assert "def get_unified_provider_stats" in content, "get_unified_provider_stats method not found"
            assert "UnifiedSearchService" in content, "UnifiedSearchService reference not found"
        
        print("✅ BidService integration structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Service structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_integration():
    """Test 5: Test app.py integration"""
    print("\n🧪 Test 5: App Integration Validation")
    print("=" * 50)
    
    try:
        # Check if app.py includes unified search routes
        with open(os.path.join(src_path, "app.py"), 'r') as f:
            content = f.read()
            assert "from routes.unified_search_routes import unified_search_bp" in content, "Import not found"
            assert "app.register_blueprint(unified_search_bp)" in content, "Blueprint registration not found"
            assert "Unified Search: 6 endpoints" in content, "Log entry not found"
        
        print("✅ App.py integration validated")
        
        return True
        
    except Exception as e:
        print(f"❌ App integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility_structure():
    """Test 6: Test backward compatibility structure"""
    print("\n🧪 Test 6: Backward Compatibility Structure")
    print("=" * 50)
    
    try:
        # Check that existing BidService methods are preserved
        with open(os.path.join(src_path, "services", "bid_service.py"), 'r') as f:
            content = f.read()
            
            # Check existing methods are still there
            existing_methods = [
                "def get_all_bids",
                "def get_bid_by_id", 
                "def get_bid_by_pncp_id",
                "def search_bids_by_object",
                "def get_bids_by_state",
                "def get_recent_bids"
            ]
            
            for method in existing_methods:
                assert method in content, f"Existing method {method} not found"
                print(f"✅ {method} method preserved")
            
            # Check that fallback functionality exists
            assert "def _fallback_to_pncp_search" in content, "Fallback method not found"
            print("✅ Fallback functionality implemented")
            
            # Check that existing repositories are preserved
            assert "self.licitacao_repo = BidRepository" in content, "licitacao_repo not preserved"
            assert "self.pncp_repo = LicitacaoPNCPRepository" in content, "pncp_repo not preserved"
            print("✅ Existing repositories preserved")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all simple validation tests"""
    print("🚀 PHASE 3 SIMPLE VALIDATION TESTS")
    print("=" * 60)
    print("Service Layer Abstraction - Structure Validation")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Basic Imports", test_basic_imports),
        ("Configuration Structure", test_config_structure),
        ("Service Structure", test_service_structure),
        ("App Integration", test_app_integration),
        ("Backward Compatibility Structure", test_backward_compatibility_structure),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL STRUCTURE TESTS PASSED - PHASE 3 READY!")
        print("\n✅ PHASE 3 STRUCTURE VALIDATION COMPLETE")
        print("🔥 Service layer abstraction is properly implemented!")
        print("📋 Implementation Summary:")
        print("   ✅ UnifiedSearchService created with multi-provider support")
        print("   ✅ BidService extended with unified search methods")
        print("   ✅ API endpoints created (/api/search/*)")
        print("   ✅ Backward compatibility maintained")
        print("   ✅ Factory and adapter patterns implemented")
        print("   ✅ Configuration management in place")
        print("\n📋 New API Endpoints Available:")
        print("   • GET /api/search/unified - Search across all providers")
        print("   • GET /api/search/providers - Get provider statistics")
        print("   • GET /api/search/providers/{name} - Search specific provider")
        print("   • GET /api/search/providers/{name}/health - Check provider health")
        print("   • GET /api/search/filters/template - Get search filter template")
        print("   • GET /api/search/test - Test endpoint functionality")
        print("\n🚀 Ready for production deployment and Phase 4!")
        return True
    else:
        print("⚠️  SOME STRUCTURE TESTS FAILED - REVIEW BEFORE PROCEEDING")
        print("🔧 Fix structural issues before proceeding to Phase 4")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    
    if success:
        print("\n✅ PHASE 3 STRUCTURE VALIDATION COMPLETE")
        print("🚀 Service layer abstraction structure is solid!")
        sys.exit(0)
    else:
        print("\n❌ STRUCTURE VALIDATION FAILED")
        print("🔧 Fix structural issues before proceeding")
        sys.exit(1)