"""
Unified Search Service - Phase 3 Service Layer Abstraction

This service provides a unified interface for searching across multiple procurement
data sources while maintaining backward compatibility with existing PNCP workflows.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from factories.data_source_factory import DataSourceFactory
from interfaces.procurement_data_source import SearchFilters, OpportunityData
from config.data_source_config import DataSourceConfig
from utils.search.synonym_service import generate_synonyms, expand_search_terms

logger = logging.getLogger(__name__)


class UnifiedSearchService:
    """
    Unified Search Service for multi-source procurement data
    
    This service wraps the DataSourceFactory to provide application-level
    search functionality while maintaining backward compatibility.
    """
    
    # Class-level factory instance (singleton pattern)
    _factory_instance = None
    _config_instance = None
    
    def __init__(self, config: DataSourceConfig = None):
        """Initialize the unified search service with singleton factory"""
        
        # Use singleton pattern for factory to avoid multiple Redis connections
        if UnifiedSearchService._factory_instance is None or config is not None:
            self.config = config or DataSourceConfig()
            UnifiedSearchService._config_instance = self.config
            UnifiedSearchService._factory_instance = DataSourceFactory(self.config)
            logger.info("✅ UnifiedSearchService initialized with NEW DataSourceFactory")
        else:
            # Reuse existing factory
            self.config = UnifiedSearchService._config_instance
            logger.info("✅ UnifiedSearchService initialized with EXISTING DataSourceFactory (singleton)")
    
        self.factory = UnifiedSearchService._factory_instance
        
        logger.info("✅ UnifiedSearchService initialized with synonym expansion")
    
    async def search_opportunities(self, filters: SearchFilters) -> Dict[str, List[OpportunityData]]:
        """
        Search opportunities across all active providers
        
        Returns a dictionary mapping provider names to their opportunity lists.
        This allows the caller to see results from each provider separately.
        
        Args:
            filters: SearchFilters object with search criteria
            
        Returns:
            Dict mapping provider names to lists of OpportunityData
        """
        try:
            logger.info(f"🔍 Searching opportunities across all active providers")
            
            # Expand keywords with synonyms before searching
            enhanced_filters = self._enhance_filters_with_synonyms(filters)
            
            # Get all active provider instances
            providers = self.factory.create_all_active()
            
            if not providers:
                logger.warning("No active providers found")
                return {}
            
            results = {}
            
            # Search each provider
            for provider_name, provider in providers.items():
                try:
                    logger.info(f"🔍 Searching {provider_name} provider")
                    
                    # Search opportunities from this provider
                    opportunities = await provider.search_opportunities(enhanced_filters)
                    results[provider_name] = opportunities
                    
                    logger.info(f"✅ {provider_name}: {len(opportunities)} opportunities found")
                    
                except Exception as e:
                    logger.error(f"❌ Error searching {provider_name}: {e}")
                    results[provider_name] = []  # Continue with other providers
            
            total_opportunities = sum(len(opps) for opps in results.values())
            logger.info(f"✅ Total search completed: {total_opportunities} opportunities from {len(results)} providers")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error in unified search: {e}")
            return {}
    
    async def search_combined(self, filters: SearchFilters) -> List[Dict[str, Any]]:
        """
        Search opportunities and return combined, sorted results
        
        This method merges results from all providers into a single list,
        sorted by relevance/publication date, with provider information included.
        
        Args:
            filters: SearchFilters object with search criteria
            
        Returns:
            List of dictionaries with opportunity data and provider metadata
        """
        try:
            logger.info(f"🔍 Searching combined opportunities across all providers")
            
            # Get separate results from each provider
            provider_results = await self.search_opportunities(filters)
            
            if not provider_results:
                return []
            
            # Combine all results into a single list
            combined_results = []
            
            for provider_name, opportunities in provider_results.items():
                for opportunity in opportunities:
                    # Convert OpportunityData to dictionary and add provider info
                    opportunity_dict = self._opportunity_to_dict(opportunity)
                    opportunity_dict['provider_name'] = provider_name
                    opportunity_dict['provider_metadata'] = self._get_provider_metadata(provider_name)
                    
                    combined_results.append(opportunity_dict)
            
            # Sort by publication date (newest first) and estimated value (highest first)
            combined_results.sort(key=lambda x: (
                x.get('publication_date', ''),
                x.get('estimated_value', 0)
            ), reverse=True)
            
            logger.info(f"✅ Combined search completed: {len(combined_results)} total opportunities")
            
            return combined_results
            
        except Exception as e:
            logger.error(f"❌ Error in combined search: {e}")
            return []
    
    def _enhance_filters_with_synonyms(self, filters: SearchFilters) -> SearchFilters:
        """
        Enhance search filters by expanding keywords with synonyms
        
        This method takes the original keywords and expands them with related terms
        to improve search recall across all providers.
        
        Args:
            filters: Original SearchFilters object
            
        Returns:
            Enhanced SearchFilters with expanded keywords
        """
        try:
            # If no keywords, return original filters
            if not filters.keywords or not filters.keywords.strip():
                return filters
            
            original_keywords = filters.keywords.strip()
            logger.info(f"🔤 Expanding keywords: '{original_keywords}'")
            
            # Generate expanded search terms using synonym service
            expanded_terms = generate_synonyms(original_keywords, max_synonyms=5)
            
            # Join expanded terms for the search
            enhanced_keywords = ' OR '.join([f'"{term}"' for term in expanded_terms])
            
            # Create new SearchFilters with enhanced keywords
            enhanced_filters = SearchFilters(
                keywords=enhanced_keywords,
                region_code=filters.region_code,
                country_code=filters.country_code,
                min_value=filters.min_value,
                max_value=filters.max_value,
                currency_code=filters.currency_code,
                publication_date_from=filters.publication_date_from,
                publication_date_to=filters.publication_date_to,
                submission_deadline_from=filters.submission_deadline_from,
                submission_deadline_to=filters.submission_deadline_to,
                page=filters.page,
                page_size=filters.page_size,
                sort_by=filters.sort_by,
                sort_order=filters.sort_order
            )
            
            logger.info(f"✅ Keywords expanded from '{original_keywords}' to: {expanded_terms}")
            
            return enhanced_filters
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to expand keywords, using original: {e}")
            return filters
    
    async def get_provider_stats(self) -> Dict[str, Any]:
        """
        Get statistics and health information for all providers
        
        Returns:
            Dictionary with provider statistics and health status
        """
        try:
            logger.info("📊 Getting provider statistics")
            
            # Get available and active providers
            available_providers = self.factory.get_available_providers()
            active_providers = self.factory.get_active_providers()
            
            # Get provider information and validation results
            provider_info = self.factory.get_provider_info()
            validation_results = self.factory.validate_all_providers()
            
            # Build comprehensive stats
            stats = {
                'summary': {
                    'total_providers': len(available_providers),
                    'active_providers': len(active_providers),
                    'connected_providers': sum(1 for connected in validation_results.values() if connected),
                    'last_updated': datetime.now().isoformat()
                },
                'providers': {}
            }
            
            # Add detailed information for each provider
            for provider_name in available_providers:
                provider_data = provider_info.get(provider_name, {})
                is_connected = validation_results.get(provider_name, False)
                
                stats['providers'][provider_name] = {
                    'name': provider_name,
                    'enabled': provider_data.get('enabled', False),
                    'connected': is_connected,
                    'status': 'healthy' if is_connected else 'disconnected',
                    'config': provider_data.get('config', {}),
                    'metadata': provider_data.get('metadata', {}),
                    'last_validated': datetime.now().isoformat()
                }
            
            logger.info(f"✅ Provider stats completed: {len(available_providers)} providers analyzed")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting provider stats: {e}")
            return {
                'summary': {
                    'total_providers': 0,
                    'active_providers': 0,
                    'connected_providers': 0,
                    'error': str(e)
                },
                'providers': {}
            }
    
    async def search_by_provider(self, provider_name: str, filters: SearchFilters) -> List[OpportunityData]:
        """
        Search opportunities from a specific provider
        
        Args:
            provider_name: Name of the provider to search
            filters: SearchFilters object with search criteria
            
        Returns:
            List of OpportunityData from the specified provider
        """
        try:
            logger.info(f"🔍 Searching {provider_name} provider specifically")
            
            # Expand keywords with synonyms before searching
            enhanced_filters = self._enhance_filters_with_synonyms(filters)
            
            # Create provider instance
            provider = self.factory.create(provider_name)
            
            # Search opportunities
            opportunities = await provider.search_opportunities(enhanced_filters)
            
            logger.info(f"✅ {provider_name} search completed: {len(opportunities)} opportunities")
            
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error searching {provider_name}: {e}")
            return []
    
    async def validate_provider_connection(self, provider_name: str) -> bool:
        """
        Validate connection to a specific provider
        
        Args:
            provider_name: Name of the provider to validate
            
        Returns:
            True if provider is connected and working, False otherwise
        """
        try:
            logger.info(f"🔍 Validating {provider_name} connection")
            
            # Create provider instance
            provider = self.factory.create(provider_name)
            
            # Validate connection
            is_connected = await provider.validate_connection()
            
            logger.info(f"✅ {provider_name} validation: {'Connected' if is_connected else 'Disconnected'}")
            
            return is_connected
            
        except Exception as e:
            logger.error(f"❌ Error validating {provider_name}: {e}")
            return False
    
    async def get_opportunity_details(self, provider_name: str, external_id: str) -> Optional[OpportunityData]:
        """
        Get detailed information about a specific opportunity
        
        Args:
            provider_name: Name of the provider
            external_id: External ID of the opportunity
            
        Returns:
            OpportunityData with detailed information, or None if not found
        """
        try:
            logger.info(f"🔍 Getting opportunity details: {provider_name}/{external_id}")
            
            # Create provider instance
            provider = self.factory.create(provider_name)
            
            # Get opportunity details
            opportunity = await provider.get_opportunity_details(external_id)
            
            if opportunity:
                logger.info(f"✅ Opportunity details found: {opportunity.title}")
            else:
                logger.warning(f"❌ Opportunity not found: {external_id}")
            
            return opportunity
            
        except Exception as e:
            logger.error(f"❌ Error getting opportunity details: {e}")
            return None
    
    def _opportunity_to_dict(self, opportunity: OpportunityData) -> Dict[str, Any]:
        """
        Convert OpportunityData to dictionary for API responses
        
        Args:
            opportunity: OpportunityData object
            
        Returns:
            Dictionary representation of the opportunity
        """
        return {
            'external_id': opportunity.external_id,
            'title': opportunity.title,
            'description': opportunity.description,
            'estimated_value': opportunity.estimated_value,
            'currency_code': opportunity.currency_code,
            'country_code': opportunity.country_code,
            'region_code': opportunity.region_code,
            'municipality': opportunity.municipality,
            'publication_date': opportunity.publication_date,
            'submission_deadline': opportunity.submission_deadline,
            'procuring_entity_id': opportunity.procuring_entity_id,
            'procuring_entity_name': opportunity.procuring_entity_name,
            'provider_specific_data': opportunity.provider_specific_data
        }
    
    def _get_provider_metadata(self, provider_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Dictionary with provider metadata
        """
        try:
            provider = self.factory.create(provider_name)
            return provider.get_provider_metadata()
        except Exception as e:
            logger.warning(f"Could not get metadata for {provider_name}: {e}")
            return {'name': provider_name, 'error': str(e)}
    
    def get_search_filters_template(self) -> Dict[str, Any]:
        """
        Get a template for SearchFilters with all available options
        
        Returns:
            Dictionary showing all available search filter options
        """
        return {
            'keywords': 'Optional search keywords',
            'region_code': 'Optional region/state code (e.g., "MG", "SP")',
            'country_code': 'Optional country code (e.g., "BR")',
            'min_value': 'Optional minimum estimated value',
            'max_value': 'Optional maximum estimated value',
            'currency_code': 'Optional currency code (e.g., "BRL")',
            'publication_date_from': 'Optional publication date from (YYYY-MM-DD)',
            'publication_date_to': 'Optional publication date to (YYYY-MM-DD)',
            'submission_deadline_from': 'Optional submission deadline from (YYYY-MM-DD)',
            'submission_deadline_to': 'Optional submission deadline to (YYYY-MM-DD)',
            'page': 'Optional page number (default: 1)',
            'page_size': 'Optional page size (default: 20)',
            'sort_by': 'Optional sort field (publication_date, estimated_value)',
            'sort_order': 'Optional sort order (asc, desc)'
        }