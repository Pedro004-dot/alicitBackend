"""
Unified Search Routes - Phase 3 Service Layer Abstraction

This module provides REST API endpoints for the unified multi-source search functionality
while maintaining backward compatibility with existing PNCP-specific endpoints.
"""

import asyncio
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, Optional

from services.bid_service import BidService
from services.unified_search_service import UnifiedSearchService

logger = logging.getLogger(__name__)

# Create blueprint for unified search routes
unified_search_bp = Blueprint('unified_search', __name__, url_prefix='/api/search')

# Initialize services
bid_service = BidService()
unified_search_service = UnifiedSearchService()


@unified_search_bp.route('/unified', methods=['GET'])
def search_unified_opportunities():
    """
    Search opportunities across all active providers using unified search
    
    Query Parameters:
        - keywords: Search keywords (optional)
        - region_code: State/region code like 'MG', 'SP' (optional)
        - min_value: Minimum estimated value (optional)
        - max_value: Maximum estimated value (optional)
        - publication_date_from: Publication date from (YYYY-MM-DD) (optional)
        - publication_date_to: Publication date to (YYYY-MM-DD) (optional)
        - submission_deadline_from: Submission deadline from (YYYY-MM-DD) (optional)
        - submission_deadline_to: Submission deadline to (YYYY-MM-DD) (optional)
        - page: Page number (default: 1)
        - page_size: Results per page (default: 20)
        - sort_by: Sort field (publication_date, estimated_value) (optional)
        - sort_order: Sort order (asc, desc) (optional)
    
    Returns:
        JSON response with opportunities from all providers
    """
    try:
        logger.info(f"🔍 Unified search request from {request.remote_addr}")
        
        # Extract query parameters
        filters = {
            'keywords': request.args.get('keywords'),
            'region_code': request.args.get('region_code'),
            'min_value': _parse_float(request.args.get('min_value')),
            'max_value': _parse_float(request.args.get('max_value')),
            'publication_date_from': request.args.get('publication_date_from'),
            'publication_date_to': request.args.get('publication_date_to'),
            'submission_deadline_from': request.args.get('submission_deadline_from'),
            'submission_deadline_to': request.args.get('submission_deadline_to'),
            'page': _parse_int(request.args.get('page', 1)),
            'page_size': _parse_int(request.args.get('page_size', 20)),
            'sort_by': request.args.get('sort_by'),
            'sort_order': request.args.get('sort_order', 'desc')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        logger.info(f"🔍 Search filters: {filters}")
        
        # Perform unified search through BidService (using asyncio.run for async method)
        opportunities, message = asyncio.run(bid_service.search_unified(filters))
        
        # Build response
        response_data = {
            'success': True,
            'data': {
                'opportunities': opportunities,
                'total': len(opportunities),
                'page': filters.get('page', 1),
                'page_size': filters.get('page_size', 20),
                'filters_applied': filters
            },
            'message': message,
            'source': 'unified_search'
        }
        
        logger.info(f"✅ Unified search completed: {len(opportunities)} opportunities returned")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in unified search endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error performing unified search'
        }), 500


@unified_search_bp.route('/providers', methods=['GET'])
def get_provider_stats():
    """
    Get statistics and health information for all search providers
    
    Returns:
        JSON response with provider statistics and health status
    """
    try:
        logger.info(f"📊 Provider stats request from {request.remote_addr}")
        
        # Get provider statistics through BidService (using asyncio.run for async method)
        stats, message = asyncio.run(bid_service.get_unified_provider_stats())
        
        # Build response
        response_data = {
            'success': True,
            'data': stats,
            'message': message,
            'source': 'unified_search_service'
        }
        
        logger.info(f"✅ Provider stats retrieved successfully")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in provider stats endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error retrieving provider statistics'
        }), 500


@unified_search_bp.route('/providers/<provider_name>', methods=['GET'])
def search_by_provider(provider_name: str):
    """
    Search opportunities from a specific provider
    
    Path Parameters:
        - provider_name: Name of the provider (e.g., 'pncp')
    
    Query Parameters:
        Same as /unified endpoint
    
    Returns:
        JSON response with opportunities from the specified provider
    """
    try:
        logger.info(f"🔍 Provider-specific search request: {provider_name}")
        
        # Extract query parameters (same as unified search)
        filters = {
            'keywords': request.args.get('keywords'),
            'region_code': request.args.get('region_code'),
            'min_value': _parse_float(request.args.get('min_value')),
            'max_value': _parse_float(request.args.get('max_value')),
            'publication_date_from': request.args.get('publication_date_from'),
            'publication_date_to': request.args.get('publication_date_to'),
            'submission_deadline_from': request.args.get('submission_deadline_from'),
            'submission_deadline_to': request.args.get('submission_deadline_to'),
            'page': _parse_int(request.args.get('page', 1)),
            'page_size': _parse_int(request.args.get('page_size', 20)),
            'sort_by': request.args.get('sort_by'),
            'sort_order': request.args.get('sort_order', 'desc')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        logger.info(f"🔍 Provider search filters: {filters}")
        
        # Search specific provider through BidService (using asyncio.run for async method)
        opportunities, message = asyncio.run(bid_service.search_by_provider(provider_name, filters))
        
        # Build response
        response_data = {
            'success': True,
            'data': {
                'opportunities': opportunities,
                'total': len(opportunities),
                'provider': provider_name,
                'page': filters.get('page', 1),
                'page_size': filters.get('page_size', 20),
                'filters_applied': filters
            },
            'message': message,
            'source': f'provider_{provider_name}'
        }
        
        logger.info(f"✅ Provider search completed: {len(opportunities)} opportunities from {provider_name}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in provider search endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Error searching provider {provider_name}'
        }), 500


@unified_search_bp.route('/providers/<provider_name>/health', methods=['GET'])
def validate_provider_health(provider_name: str):
    """
    Validate health/connectivity of a specific provider
    
    Path Parameters:
        - provider_name: Name of the provider to validate
    
    Returns:
        JSON response with provider health status
    """
    try:
        logger.info(f"🔍 Provider health check: {provider_name}")
        
        # Validate provider health through BidService (using asyncio.run for async method)
        health_status, message = asyncio.run(bid_service.validate_provider_health(provider_name))
        
        # Build response
        response_data = {
            'success': True,
            'data': {
                'provider': provider_name,
                'health_status': health_status,
                'is_connected': health_status.get(provider_name, False)
            },
            'message': message,
            'source': 'provider_validation'
        }
        
        logger.info(f"✅ Provider health check completed: {provider_name}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in provider health endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Error validating provider {provider_name}'
        }), 500


@unified_search_bp.route('/filters/template', methods=['GET'])
def get_search_filters_template():
    """
    Get a template showing all available search filter options
    
    Returns:
        JSON response with filter template and examples
    """
    try:
        logger.info(f"📋 Search filters template request")
        
        # Get filter template from UnifiedSearchService
        template = unified_search_service.get_search_filters_template()
        
        # Add examples and additional documentation
        response_data = {
            'success': True,
            'data': {
                'filters': template,
                'examples': {
                    'basic_search': {
                        'keywords': 'equipamentos médicos',
                        'region_code': 'MG',
                        'page_size': 10
                    },
                    'value_range_search': {
                        'min_value': 10000,
                        'max_value': 100000,
                        'region_code': 'SP'
                    },
                    'date_range_search': {
                        'publication_date_from': '2025-01-01',
                        'publication_date_to': '2025-12-31',
                        'keywords': 'software'
                    }
                },
                'supported_providers': unified_search_service.factory.get_available_providers()
            },
            'message': 'Search filters template retrieved successfully',
            'source': 'unified_search_service'
        }
        
        logger.info(f"✅ Search filters template provided")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in filters template endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error retrieving search filters template'
        }), 500


@unified_search_bp.route('/test', methods=['GET'])
def test_unified_search():
    """
    Test endpoint to verify unified search functionality
    
    Returns:
        JSON response with system status and basic functionality test
    """
    try:
        logger.info(f"🧪 Unified search test endpoint called")
        
        # Perform basic functionality tests
        test_results = {
            'unified_search_service': False,
            'bid_service_integration': False,
            'available_providers': [],
            'active_providers': []
        }
        
        # Test UnifiedSearchService initialization
        try:
            test_service = UnifiedSearchService()
            test_results['unified_search_service'] = True
            test_results['available_providers'] = test_service.factory.get_available_providers()
            test_results['active_providers'] = test_service.factory.get_active_providers()
        except Exception as e:
            logger.error(f"UnifiedSearchService test failed: {e}")
        
        # Test BidService integration
        try:
            test_bid_service = BidService()
            if test_bid_service.unified_search_service:
                test_results['bid_service_integration'] = True
        except Exception as e:
            logger.error(f"BidService integration test failed: {e}")
        
        # Determine overall status
        overall_status = (
            test_results['unified_search_service'] and 
            test_results['bid_service_integration'] and
            len(test_results['active_providers']) > 0
        )
        
        response_data = {
            'success': True,
            'data': {
                'overall_status': 'healthy' if overall_status else 'degraded',
                'test_results': test_results,
                'recommendations': _get_health_recommendations(test_results)
            },
            'message': 'Unified search test completed',
            'source': 'test_endpoint'
        }
        
        logger.info(f"✅ Unified search test completed: {'healthy' if overall_status else 'degraded'}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in test endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error testing unified search functionality'
        }), 500


@unified_search_bp.route('/providers/<provider_name>/no-cache', methods=['GET'])
def search_by_provider_no_cache(provider_name: str):
    """
    Search opportunities from a specific provider with cache disabled (for testing)
    
    Path Parameters:
        - provider_name: Name of the provider (e.g., 'pncp')
    
    Query Parameters:
        Same as /providers/<provider_name> endpoint
    
    Returns:
        JSON response with opportunities from the specified provider (no cache)
    """
    try:
        logger.info(f"🔍 Provider-specific search request (NO CACHE): {provider_name}")
        
        # Extract query parameters (same as unified search)
        filters = {
            'keywords': request.args.get('keywords'),
            'region_code': request.args.get('region_code'),
            'min_value': _parse_float(request.args.get('min_value')),
            'max_value': _parse_float(request.args.get('max_value')),
            'publication_date_from': request.args.get('publication_date_from'),
            'publication_date_to': request.args.get('publication_date_to'),
            'submission_deadline_from': request.args.get('submission_deadline_from'),
            'submission_deadline_to': request.args.get('submission_deadline_to'),
            'page': _parse_int(request.args.get('page', 1)),
            'page_size': _parse_int(request.args.get('page_size', 20)),
            'sort_by': request.args.get('sort_by'),
            'sort_order': request.args.get('sort_order', 'desc')
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}
        
        logger.info(f"🔍 Provider search filters (NO CACHE): {filters}")
        
        # Search provider with cache disabled (using asyncio.run for async method)
        opportunities, message = asyncio.run(bid_service.search_by_provider_no_cache(provider_name, filters))
        
        # Build response
        response_data = {
            'success': True,
            'data': {
                'opportunities': opportunities,
                'total': len(opportunities),
                'provider': provider_name,
                'page': filters.get('page', 1),
                'page_size': filters.get('page_size', 20),
                'filters_applied': filters,
                'cache_disabled': True
            },
            'message': message,
            'source': f'provider_{provider_name}_no_cache'
        }
        
        logger.info(f"✅ Provider search (NO CACHE) completed: {len(opportunities)} opportunities from {provider_name}")
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error in provider search (no cache) endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Error searching provider {provider_name} without cache'
        }), 500


# Helper functions

def _parse_int(value: str) -> int:
    """Parse string to integer, return None if invalid"""
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


def _parse_float(value: str) -> float:
    """Parse string to float, return None if invalid"""
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None


def _get_health_recommendations(test_results: Dict[str, Any]) -> list:
    """Get health recommendations based on test results"""
    recommendations = []
    
    if not test_results['unified_search_service']:
        recommendations.append("UnifiedSearchService initialization failed - check dependencies")
    
    if not test_results['bid_service_integration']:
        recommendations.append("BidService integration not working - check imports")
    
    if len(test_results['active_providers']) == 0:
        recommendations.append("No active providers found - check configuration")
    
    if len(test_results['available_providers']) == 0:
        recommendations.append("No providers registered - check factory setup")
    
    if not recommendations:
        recommendations.append("All systems healthy - unified search ready for use")
    
    return recommendations


# Error handlers for the blueprint

@unified_search_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    return jsonify({
        'success': False,
        'error': 'Bad Request',
        'message': 'Invalid request parameters'
    }), 400


@unified_search_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': 'Endpoint not found'
    }), 404


@unified_search_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500