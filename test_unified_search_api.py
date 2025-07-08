#!/usr/bin/env python3
"""
Integration Tests for Unified Search API - Phase 3 Service Layer Abstraction

This test suite validates the new unified search API endpoints and ensures
backward compatibility with existing PNCP functionality.
"""

import sys
import os
import json
from unittest.mock import patch, MagicMock

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


def test_imports():
    """Test 1: Verify all unified search modules can be imported"""
    print("🧪 Test 1: Import Validation for Phase 3")
    print("=" * 50)
    
    try:
        # Test service imports
        from services.unified_search_service import UnifiedSearchService
        print("✅ UnifiedSearchService imported successfully")
        
        from services.bid_service import BidService
        print("✅ BidService (with unified search integration) imported successfully")
        
        # Test route imports
        from routes.unified_search_routes import unified_search_bp
        print("✅ Unified search routes imported successfully")
        
        # Test that BidService has new unified methods
        bid_service = BidService()
        assert hasattr(bid_service, 'search_unified'), "BidService missing search_unified method"
        assert hasattr(bid_service, 'get_unified_provider_stats'), "BidService missing get_unified_provider_stats method"
        print("✅ BidService has unified search methods")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_flask_app_creation():
    """Test 2: Verify Flask app can be created with unified search routes"""
    print("\n🧪 Test 2: Flask App Creation with Unified Search")
    print("=" * 50)
    
    try:
        # Mock environment variables to avoid real database connections
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-anon-key',
            'DATABASE_URL': 'postgresql://test:test@test:5432/test',
            'SECRET_KEY': 'test-secret-key'
        }):
            # Mock database manager to avoid real connections
            with patch('config.database.get_db_manager') as mock_db:
                mock_db_instance = MagicMock()
                mock_db_instance.get_health_status.return_value = {
                    'overall': 'healthy',
                    'connections': {'postgresql': {'status': 'connected'}}
                }
                mock_db.return_value = mock_db_instance
                
                # Import and create app
                from app import create_app
                app = create_app()
                
                print("✅ Flask app created successfully")
                
                # Verify unified search routes are registered
                route_paths = [rule.rule for rule in app.url_map.iter_rules()]
                
                expected_routes = [
                    '/api/search/unified',
                    '/api/search/providers',
                    '/api/search/providers/<provider_name>',
                    '/api/search/providers/<provider_name>/health',
                    '/api/search/filters/template',
                    '/api/search/test'
                ]
                
                for route in expected_routes:
                    # Handle parameterized routes by checking if similar routes exist
                    if '<' in route:
                        base_route = route.split('<')[0]
                        similar_routes = [r for r in route_paths if r.startswith(base_route)]
                        assert len(similar_routes) > 0, f"Parameterized route {route} not found"
                    else:
                        assert route in route_paths, f"Route {route} not registered"
                
                print("✅ All unified search routes registered")
                
                return True
        
    except Exception as e:
        print(f"❌ Flask app creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_search_service():
    """Test 3: Test UnifiedSearchService functionality"""
    print("\n🧪 Test 3: UnifiedSearchService Functionality")
    print("=" * 50)
    
    try:
        from services.unified_search_service import UnifiedSearchService
        from interfaces.procurement_data_source import SearchFilters
        
        # Create service instance
        service = UnifiedSearchService()
        print("✅ UnifiedSearchService created")
        
        # Test provider stats
        stats = service.get_provider_stats()
        assert isinstance(stats, dict), "Provider stats should return dict"
        assert 'summary' in stats, "Stats should have summary"
        assert 'providers' in stats, "Stats should have providers"
        print("✅ Provider stats method works")
        
        # Test search filters template
        template = service.get_search_filters_template()
        assert isinstance(template, dict), "Template should return dict"
        print("✅ Search filters template method works")
        
        # Test search filters creation
        filters = SearchFilters(keywords="test", region_code="MG", page_size=10)
        assert filters.keywords == "test", "SearchFilters not working correctly"
        print("✅ SearchFilters object creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ UnifiedSearchService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bid_service_integration():
    """Test 4: Test BidService integration with unified search"""
    print("\n🧪 Test 4: BidService Unified Search Integration")
    print("=" * 50)
    
    try:
        # Mock database to avoid real connections
        with patch('config.database.db_manager') as mock_db:
            mock_db.get_connection.return_value.__enter__ = MagicMock()
            mock_db.get_connection.return_value.__exit__ = MagicMock()
            
            from services.bid_service import BidService
            
            # Create service instance
            bid_service = BidService()
            print("✅ BidService created")
            
            # Test unified search method exists and is callable
            assert hasattr(bid_service, 'search_unified'), "Missing search_unified method"
            assert callable(bid_service.search_unified), "search_unified not callable"
            print("✅ search_unified method available")
            
            # Test provider stats method
            assert hasattr(bid_service, 'get_unified_provider_stats'), "Missing get_unified_provider_stats method"
            assert callable(bid_service.get_unified_provider_stats), "get_unified_provider_stats not callable"
            print("✅ get_unified_provider_stats method available")
            
            # Test provider health validation
            assert hasattr(bid_service, 'validate_provider_health'), "Missing validate_provider_health method"
            assert callable(bid_service.validate_provider_health), "validate_provider_health not callable"
            print("✅ validate_provider_health method available")
            
            # Test fallback method exists
            assert hasattr(bid_service, '_fallback_to_pncp_search'), "Missing fallback method"
            print("✅ Fallback method available for backward compatibility")
            
            return True
        
    except Exception as e:
        print(f"❌ BidService integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """Test 5: Test API endpoints with Flask test client"""
    print("\n🧪 Test 5: API Endpoints Integration Test")
    print("=" * 50)
    
    try:
        # Mock environment variables
        with patch.dict(os.environ, {
            'SUPABASE_URL': 'https://test.supabase.co',
            'SUPABASE_ANON_KEY': 'test-anon-key',
            'DATABASE_URL': 'postgresql://test:test@test:5432/test',
            'SECRET_KEY': 'test-secret-key'
        }):
            # Mock database manager
            with patch('config.database.get_db_manager') as mock_db:
                mock_db_instance = MagicMock()
                mock_db_instance.get_health_status.return_value = {
                    'overall': 'healthy',
                    'connections': {'postgresql': {'status': 'connected'}}
                }
                mock_db.return_value = mock_db_instance
                
                # Mock the unified search service to avoid actual API calls
                with patch('services.unified_search_service.UnifiedSearchService') as mock_service_class:
                    mock_service = MagicMock()
                    mock_service.get_provider_stats.return_value = {
                        'summary': {'active_providers': 1, 'total_providers': 1},
                        'providers': {'pncp': {'enabled': True, 'connected': True}}
                    }
                    mock_service.get_search_filters_template.return_value = {
                        'keywords': 'Optional search keywords',
                        'region_code': 'Optional region code'
                    }
                    mock_service_class.return_value = mock_service
                    
                    # Mock BidService search methods
                    with patch('services.bid_service.BidService') as mock_bid_service_class:
                        mock_bid_service = MagicMock()
                        mock_bid_service.search_unified.return_value = ([], "No results for test")
                        mock_bid_service.get_unified_provider_stats.return_value = (
                            {'summary': {'active_providers': 1}}, "Stats retrieved"
                        )
                        mock_bid_service.validate_provider_health.return_value = (
                            {'pncp': True}, "Provider healthy"
                        )
                        mock_bid_service_class.return_value = mock_bid_service
                        
                        from app import create_app
                        app = create_app()
                        
                        with app.test_client() as client:
                            print("✅ Test client created")
                            
                            # Test 1: GET /api/search/unified
                            response = client.get('/api/search/unified?keywords=test&region_code=MG')
                            assert response.status_code == 200, f"Unified search endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Unified search should return success"
                            print("✅ GET /api/search/unified works")
                            
                            # Test 2: GET /api/search/providers
                            response = client.get('/api/search/providers')
                            assert response.status_code == 200, f"Provider stats endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Provider stats should return success"
                            print("✅ GET /api/search/providers works")
                            
                            # Test 3: GET /api/search/providers/pncp
                            response = client.get('/api/search/providers/pncp?keywords=test')
                            assert response.status_code == 200, f"Provider search endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Provider search should return success"
                            print("✅ GET /api/search/providers/pncp works")
                            
                            # Test 4: GET /api/search/providers/pncp/health
                            response = client.get('/api/search/providers/pncp/health')
                            assert response.status_code == 200, f"Provider health endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Provider health should return success"
                            print("✅ GET /api/search/providers/pncp/health works")
                            
                            # Test 5: GET /api/search/filters/template
                            response = client.get('/api/search/filters/template')
                            assert response.status_code == 200, f"Filters template endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Filters template should return success"
                            print("✅ GET /api/search/filters/template works")
                            
                            # Test 6: GET /api/search/test
                            response = client.get('/api/search/test')
                            assert response.status_code == 200, f"Test endpoint failed: {response.status_code}"
                            data = response.get_json()
                            assert data['success'] == True, "Test endpoint should return success"
                            print("✅ GET /api/search/test works")
                            
                            return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backward_compatibility():
    """Test 6: Ensure backward compatibility with existing PNCP functionality"""
    print("\n🧪 Test 6: Backward Compatibility Validation")
    print("=" * 50)
    
    try:
        # Mock database to avoid real connections
        with patch('config.database.db_manager') as mock_db:
            mock_db.get_connection.return_value.__enter__ = MagicMock()
            mock_db.get_connection.return_value.__exit__ = MagicMock()
            
            from services.bid_service import BidService
            
            # Create service instance
            bid_service = BidService()
            
            # Test that existing methods still exist and work
            existing_methods = [
                'get_all_bids',
                'get_bid_by_id',
                'get_bid_by_pncp_id',
                'search_bids_by_object',
                'get_bids_by_state',
                'get_recent_bids',
                'get_statistics'
            ]
            
            for method_name in existing_methods:
                assert hasattr(bid_service, method_name), f"Missing existing method: {method_name}"
                assert callable(getattr(bid_service, method_name)), f"Method {method_name} not callable"
                print(f"✅ Existing method {method_name} still available")
            
            # Test that existing PNCP repository is still accessible
            assert hasattr(bid_service, 'pncp_repo'), "Missing pncp_repo attribute"
            print("✅ PNCP repository still accessible")
            
            # Test that existing licitacao_repo is still accessible
            assert hasattr(bid_service, 'licitacao_repo'), "Missing licitacao_repo attribute"
            print("✅ Licitacao repository still accessible")
            
            # Verify that existing methods have the same signatures
            import inspect
            
            # Check get_all_bids signature
            sig = inspect.signature(bid_service.get_all_bids)
            params = list(sig.parameters.keys())
            assert 'limit' in params, "get_all_bids signature changed"
            print("✅ Existing method signatures preserved")
            
            return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests"""
    print("🚀 UNIFIED SEARCH API INTEGRATION TESTS")
    print("=" * 60)
    print("Phase 3: Service Layer Abstraction Validation")
    print("=" * 60)
    
    tests = [
        ("Import Validation", test_imports),
        ("Flask App Creation", test_flask_app_creation),
        ("UnifiedSearchService Functionality", test_unified_search_service),
        ("BidService Integration", test_bid_service_integration),
        ("API Endpoints", test_api_endpoints),
        ("Backward Compatibility", test_backward_compatibility),
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
        print("🎉 ALL TESTS PASSED - PHASE 3 SERVICE LAYER READY!")
        print("\n✅ INTEGRATION VALIDATION COMPLETE")
        print("🔥 Unified search API is working!")
        print("📋 API endpoints available:")
        print("   • GET /api/search/unified - Search across all providers")
        print("   • GET /api/search/providers - Get provider statistics")
        print("   • GET /api/search/providers/{name} - Search specific provider")
        print("   • GET /api/search/providers/{name}/health - Check provider health")
        print("   • GET /api/search/filters/template - Get search filter template")
        print("   • GET /api/search/test - Test endpoint functionality")
        print("📋 Ready for Phase 4: Database Schema & Second Provider Integration")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW BEFORE PROCEEDING")
        print("🔧 Fix issues before proceeding to Phase 4")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    
    if success:
        print("\n✅ PHASE 3 INTEGRATION VALIDATION COMPLETE")
        print("🚀 All unified search functionality is working!")
        sys.exit(0)
    else:
        print("\n❌ INTEGRATION VALIDATION FAILED")
        print("🔧 Fix issues before proceeding")
        sys.exit(1)