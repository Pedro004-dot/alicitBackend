import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DataSourceConfig:
    """Configuration manager for multi-source data providers"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or 'config/data_sources.yaml'
        self.sources = self._load_config()
        logger.info(f"✅ Data source configuration loaded with {len(self.sources)} providers")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables and defaults"""
        # Start with defaults - only PNCP for Phase 1
        default_config = {
            'pncp': {
                'enabled': True,
                'priority': 1,
                'api_base_url': 'https://pncp.gov.br/api/consulta/v1',  # ✅ CORRIGIDO: URL completa com /consulta/v1
                'timeout': 30,
                'rate_limit': 100,
                'cache_ttl': 3600
            }
        }
        
        # Override with environment variables if they exist
        if os.getenv('PNCP_ENABLED'):
            default_config['pncp']['enabled'] = os.getenv('PNCP_ENABLED').lower() == 'true'
        
        if os.getenv('PNCP_API_URL'):
            default_config['pncp']['api_base_url'] = os.getenv('PNCP_API_URL')
        
        if os.getenv('PNCP_TIMEOUT'):
            try:
                default_config['pncp']['timeout'] = int(os.getenv('PNCP_TIMEOUT'))
            except ValueError:
                logger.warning("Invalid PNCP_TIMEOUT value, using default")
        
        # Future providers can be added here via environment variables
        # For now, we only support PNCP to maintain backward compatibility
        
        return default_config
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider"""
        config = self.sources.get(provider, {})
        if not config:
            logger.warning(f"No configuration found for provider: {provider}")
        return config
    
    def is_provider_enabled(self, provider: str) -> bool:
        """Check if a provider is enabled"""
        return self.sources.get(provider, {}).get('enabled', False)
    
    def get_active_providers(self) -> List[str]:
        """Get list of currently enabled providers"""
        active = [name for name, config in self.sources.items() 
                 if config.get('enabled', False)]
        logger.debug(f"Active providers: {active}")
        return active
    
    def add_provider_runtime(self, name: str, config: Dict[str, Any]):
        """Add new provider without redeployment (for future use)"""
        self.sources[name] = config
        self._validate_provider_config(name, config)
        logger.info(f"✅ Provider '{name}' added to runtime configuration")
    
    def _validate_provider_config(self, name: str, config: Dict[str, Any]):
        """Validate provider configuration"""
        required_fields = ['enabled', 'api_base_url', 'timeout']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Provider '{name}' missing required field: {field}")
        
        if not isinstance(config['enabled'], bool):
            raise ValueError(f"Provider '{name}' 'enabled' must be boolean")
        
        if not isinstance(config['timeout'], (int, float)) or config['timeout'] <= 0:
            raise ValueError(f"Provider '{name}' 'timeout' must be positive number")