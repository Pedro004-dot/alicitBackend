from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchFilters:
    """Provider-specific search filters for procurement data sources
    
    Each provider can interpret these filters according to their own capabilities.
    No global filtering logic - filters are passed directly to providers.
    """
    # Basic search criteria
    keywords: Optional[str] = None
    
    # Geographic filters
    country_code: Optional[str] = None
    region_code: Optional[str] = None
    municipality: Optional[str] = None
    
    # Value filters
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    currency_code: Optional[str] = None
    
    # Date filters
    publication_date_from: Optional[str] = None
    publication_date_to: Optional[str] = None
    submission_deadline_from: Optional[str] = None
    submission_deadline_to: Optional[str] = None
    
    # Procurement type and status
    procurement_type: Optional[str] = None
    status: Optional[str] = None
    
    # Pagination and sorting (handled by each provider)
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    
    # Provider-specific filters (flexible)
    provider_specific_filters: Optional[Dict[str, Any]] = None


@dataclass
class OpportunityData:
    """Standardized opportunity data structure"""
    external_id: str
    title: str
    description: Optional[str] = None
    estimated_value: Optional[float] = None
    currency_code: str = 'BRL'
    country_code: str = 'BR'
    region_code: Optional[str] = None
    municipality: Optional[str] = None
    publication_date: Optional[str] = None
    submission_deadline: Optional[str] = None
    opening_date: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    provider_name: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    documents: Optional[List[Dict[str, Any]]] = None
    additional_info: Optional[Dict[str, Any]] = None
    procuring_entity_id: Optional[str] = None
    procuring_entity_name: Optional[str] = None
    contracting_authority: Optional[str] = None
    provider_specific_data: Optional[Dict[str, Any]] = None


class ProcurementDataSource(ABC):
    """Abstract interface for procurement data sources
    
    Each provider implements its own filtering logic without global filter constraints.
    """
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name (e.g., 'pncp', 'eu_ted')"""
        pass
    
    @abstractmethod
    def search_opportunities(self, filters: SearchFilters) -> List[OpportunityData]:
        """Search for procurement opportunities using provider-specific filtering"""
        pass
    
    @abstractmethod
    def get_opportunity_details(self, external_id: str) -> Optional[OpportunityData]:
        """Get detailed information for a specific opportunity"""
        pass
    
    @abstractmethod
    def get_opportunity_items(self, external_id: str) -> List[Dict[str, Any]]:
        """Get items/lots for a specific opportunity"""
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """Test if the data source is accessible"""
        pass
    
    @abstractmethod
    def get_provider_metadata(self) -> Dict[str, Any]:
        """Get metadata about the provider (rate limits, capabilities, supported filters, etc.)"""
        pass
    
    def get_supported_filters(self) -> List[str]:
        """Get list of filter names supported by this provider
        
        Override in provider implementations to specify which filters they support.
        Default implementation returns common filters.
        """
        return [
            'keywords', 'region_code', 'min_value', 'max_value',
            'publication_date_from', 'publication_date_to',
            'page', 'page_size'
        ]