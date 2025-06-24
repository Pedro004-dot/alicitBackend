"""
Pacote de matching de licitações com API do PNCP
"""

from .vectorizers import (
    BaseTextVectorizer,
    BrazilianTextVectorizer,
    OpenAITextVectorizer,
    VoyageAITextVectorizer, 
    HybridTextVectorizer,
    MockTextVectorizer,
    calculate_cosine_similarity,
    calculate_enhanced_similarity
)

from .pncp_api import (
    get_db_connection,
    get_all_companies_from_db,
    get_processed_bid_ids,
    fetch_bids_from_pncp,
    fetch_bid_items_from_pncp,
    save_bid_to_db,
    save_bid_items_to_db,
    save_match_to_db,
    update_bid_status,
    get_existing_bids_from_db,
    get_bid_items_from_db,
    clear_existing_matches,
    ESTADOS_BRASIL
)

from .matching_engine import (
    process_daily_bids,
    reevaluate_existing_bids
)

__all__ = [
    # Vectorizers
    'BaseTextVectorizer',
    'BrazilianTextVectorizer',
    'OpenAITextVectorizer',
    'VoyageAITextVectorizer', 
    'HybridTextVectorizer',
    'MockTextVectorizer',
    'calculate_cosine_similarity',
    'calculate_enhanced_similarity',
    
    # PNCP API
    'get_db_connection',
    'get_all_companies_from_db',
    'get_processed_bid_ids',
    'fetch_bids_from_pncp',
    'fetch_bid_items_from_pncp',
    'save_bid_to_db',
    'save_bid_items_to_db',
    'save_match_to_db',
    'update_bid_status',
    'get_existing_bids_from_db',
    'get_bid_items_from_db',
    'clear_existing_matches',
    'ESTADOS_BRASIL',
    
    # Main functions
    'process_daily_bids',
    'reevaluate_existing_bids'
] 