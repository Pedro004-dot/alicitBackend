#!/usr/bin/env python3
"""
🚀 Test script to validate PARALLEL SEARCH performance
This compares sequential vs parallel performance and validates identical results
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_parallel_vs_sequential():
    """Test both parallel and sequential search methods"""
    
    print("🚀 TESTING PARALLEL VS SEQUENTIAL SEARCH")
    print("=" * 60)
    
    try:
        # Import required classes
        from config.data_source_config import DataSourceConfig
        from adapters.pncp_adapter import PNCPAdapter
        from interfaces.procurement_data_source import SearchFilters
        
        # Initialize adapter with cache DISABLED for fair comparison
        config = DataSourceConfig()
        pncp_config = config.get_provider_config('pncp')
        pncp_config['cache_ttl'] = 0  # 🚫 DISABLE CACHE completely
        adapter = PNCPAdapter(pncp_config)
        
        # Test filters (using keywords to make search meaningful)
        test_filters = SearchFilters(
            keywords="Medicamentos OR Equipamentos",
            region_code="SP"  # Focus on São Paulo for faster test
        )
        
        # 🔄 TEST 1: Force Sequential Search
        print("\n🔄 TEST 1: SEQUENTIAL SEARCH")
        print("-" * 40)
        
        # Disable parallel for this test
        os.environ['ENABLE_PARALLEL_SEARCH'] = 'false'
        
        start_time = time.time()
        sequential_results = adapter.search_opportunities(test_filters)
        sequential_time = time.time() - start_time
        
        print(f"⏱️ Sequential Time: {sequential_time:.2f}s")
        print(f"📊 Sequential Results: {len(sequential_results)}")
        
        # Get unique IDs from sequential results for comparison
        sequential_ids = {r.external_id for r in sequential_results if r.external_id}
        
        # 🚀 TEST 2: Force Parallel Search  
        print("\n🚀 TEST 2: PARALLEL SEARCH")
        print("-" * 40)
        
        # Enable parallel for this test
        os.environ['ENABLE_PARALLEL_SEARCH'] = 'true'
        
        # Clear cache to ensure fair comparison
        try:
            if adapter.redis_client:
                # Clear PNCP cache
                for key in adapter.redis_client.scan_iter(match="pncp*"):
                    adapter.redis_client.delete(key)
                print("🧹 Cache cleared for fair comparison")
        except Exception as e:
            print(f"⚠️ Cache clear warning: {e}")
        
        start_time = time.time()
        parallel_results = adapter.search_opportunities(test_filters)
        parallel_time = time.time() - start_time
        
        print(f"⏱️ Parallel Time: {parallel_time:.2f}s")
        print(f"📊 Parallel Results: {len(parallel_results)}")
        
        # Get unique IDs from parallel results for comparison
        parallel_ids = {r.external_id for r in parallel_results if r.external_id}
        
        # 📊 PERFORMANCE COMPARISON
        print("\n📊 PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        if sequential_time > 0 and parallel_time > 0:
            speedup = sequential_time / parallel_time
            print(f"🚀 Speedup: {speedup:.1f}x faster")
            print(f"⚡ Time Saved: {sequential_time - parallel_time:.2f}s ({((sequential_time - parallel_time) / sequential_time * 100):.1f}%)")
        
        # 🔍 RESULT VALIDATION
        print("\n🔍 RESULT VALIDATION")
        print("-" * 40)
        
        # Compare unique IDs
        common_ids = sequential_ids.intersection(parallel_ids)
        only_sequential = sequential_ids - parallel_ids
        only_parallel = parallel_ids - sequential_ids
        
        print(f"🎯 Common Results: {len(common_ids)}")
        print(f"📋 Sequential Only: {len(only_sequential)}")
        print(f"📋 Parallel Only: {len(only_parallel)}")
        
        if len(only_sequential) > 0:
            print(f"⚠️ Missing in parallel: {list(only_sequential)[:3]}{'...' if len(only_sequential) > 3 else ''}")
        
        if len(only_parallel) > 0:
            print(f"✅ Extra in parallel: {list(only_parallel)[:3]}{'...' if len(only_parallel) > 3 else ''}")
        
        # 🎉 SUCCESS METRICS
        if len(common_ids) > 0:
            overlap_percentage = (len(common_ids) / max(len(sequential_ids), len(parallel_ids))) * 100
            print(f"🎯 Result Overlap: {overlap_percentage:.1f}%")
            
            if overlap_percentage >= 90:
                print("✅ HIGH RESULT CONSISTENCY (≥90%)")
            elif overlap_percentage >= 75:
                print("⚠️ MODERATE RESULT CONSISTENCY (75-90%)")
            else:
                print("❌ LOW RESULT CONSISTENCY (<75%)")
        
        # 📈 RECOMMENDATIONS
        print("\n📈 RECOMMENDATIONS")
        print("-" * 40)
        
        if parallel_time > 0 and sequential_time > 0:
            if parallel_time < sequential_time * 0.5:  # 50% faster
                print("✅ PARALLEL SEARCH RECOMMENDED: Significant performance gain")
            elif parallel_time < sequential_time * 0.8:  # 20% faster
                print("✅ PARALLEL SEARCH BENEFICIAL: Moderate performance gain")
            else:
                print("⚠️ PARALLEL SEARCH MARGINAL: Consider sequential for simplicity")
        
        # Save detailed results for analysis
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'sequential': {
                'time': sequential_time,
                'results_count': len(sequential_results),
                'sample_ids': list(sequential_ids)[:10]
            },
            'parallel': {
                'time': parallel_time,
                'results_count': len(parallel_results),
                'sample_ids': list(parallel_ids)[:10]
            },
            'comparison': {
                'speedup': speedup if sequential_time > 0 and parallel_time > 0 else 0,
                'common_results': len(common_ids),
                'overlap_percentage': overlap_percentage if len(common_ids) > 0 else 0
            }
        }
        
        # Save to file
        with open('parallel_test_results.json', 'w') as f:
            json.dump(test_results, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: parallel_test_results.json")
        
        return test_results
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_quick_validation():
    """Quick test to ensure parallel search is working"""
    
    print("\n🔍 QUICK VALIDATION TEST")
    print("=" * 40)
    
    try:
        from config.data_source_config import DataSourceConfig
        from adapters.pncp_adapter import PNCPAdapter
        from interfaces.procurement_data_source import SearchFilters
        
        # Enable parallel
        os.environ['ENABLE_PARALLEL_SEARCH'] = 'true'
        
        config = DataSourceConfig()
        pncp_config = config.get_provider_config('pncp')
        adapter = PNCPAdapter(pncp_config)
        
        # Simple test
        test_filters = SearchFilters(keywords="teste")
        
        start_time = time.time()
        results = adapter.search_opportunities(test_filters)
        elapsed = time.time() - start_time
        
        print(f"⏱️ Time: {elapsed:.2f}s")
        print(f"📊 Results: {len(results)}")
        
        if len(results) > 0:
            print("✅ Parallel search is working!")
            sample = results[0]
            print(f"📋 Sample result: {sample.title[:50]}...")
        else:
            print("⚠️ No results found (may be normal depending on data)")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 PARALLEL SEARCH PERFORMANCE TEST")
    print("=" * 60)
    
    # Quick validation first
    if test_quick_validation():
        print("\n" + "=" * 60)
        # Full comparison test
        test_parallel_vs_sequential()
    else:
        print("\n❌ Quick validation failed - skipping full test") 