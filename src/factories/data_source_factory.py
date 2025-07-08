from typing import Dict, Type, Any, List
import logging

from interfaces.procurement_data_source import ProcurementDataSource
from adapters.pncp_adapter import PNCPAdapter
from config.data_source_config import DataSourceConfig

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """Factory for creating procurement data source instances
    
    This factory implements the Factory pattern to manage different
    procurement data sources in a centralized way.
    """
    
    # Registry of available provider classes
    _providers: Dict[str, Type[ProcurementDataSource]] = {
        'pncp': PNCPAdapter,
        # Future providers will be added here:
        # 'eu_ted': EUTEDAdapter,
        # 'comprasnet': ComprasNetAdapter,
    }
    
    def __init__(self, config: DataSourceConfig = None):
        self.config = config or DataSourceConfig()
        # Cache for provider instances to avoid creating duplicates
        self._instance_cache = {}
        logger.info(f"✅ DataSourceFactory initialized with {len(self._providers)} registered providers")
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[ProcurementDataSource]):
        """Register a new provider class
        
        This allows adding new providers without modifying the factory code.
        """
        if not issubclass(provider_class, ProcurementDataSource):
            raise ValueError(f"Provider {name} must implement ProcurementDataSource interface")
        
        cls._providers[name] = provider_class
        logger.info(f"✅ Provider '{name}' registered in factory")
    
    def create(self, provider_name: str, config_override: Dict[str, Any] = None) -> ProcurementDataSource:
        """Create a data source instance with caching
        
        Args:
            provider_name: Name of the provider ('pncp', 'eu_ted', etc.)
            config_override: Optional configuration overrides
            
        Returns:
            Configured provider instance (cached if possible)
            
        Raises:
            ValueError: If provider is unknown or disabled
        """
        if provider_name not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Unknown provider: {provider_name}. Available: {available}")
        
        if not self.config.is_provider_enabled(provider_name):
            raise ValueError(f"Provider {provider_name} is not enabled in configuration")
        
        # Create cache key based on provider name and config
        cache_key = f"{provider_name}_{hash(str(config_override or {}))}"
        
        # Return cached instance if available
        if cache_key in self._instance_cache:
            logger.info(f"✅ Returning CACHED {provider_name} provider instance")
            return self._instance_cache[cache_key]
        
        # Get provider configuration
        provider_config = self.config.get_provider_config(provider_name).copy()
        
        # Apply any configuration overrides
        if config_override:
            provider_config.update(config_override)
        
        # Create new provider instance
        provider_class = self._providers[provider_name]
        instance = provider_class(provider_config)
        
        # Cache the instance
        self._instance_cache[cache_key] = instance
        
        logger.info(f"✅ Created NEW {provider_name} provider instance (cached for reuse)")
        return instance
    
    def create_all_active(self) -> Dict[str, ProcurementDataSource]:
        """Create instances for all active providers
        
        Returns:
            Dictionary mapping provider names to instances
        """
        active_providers = self.config.get_active_providers()
        instances = {}
        
        for provider_name in active_providers:
            try:
                instance = self.create(provider_name)
                instances[provider_name] = instance
            except Exception as e:
                logger.error(f"Failed to create provider {provider_name}: {e}")
                # Continue with other providers - graceful degradation
                continue
        
        logger.info(f"✅ Created {len(instances)} active provider instances")
        return instances
    
    def get_available_providers(self) -> List[str]:
        """Get list of all registered providers"""
        return list(self._providers.keys())
    
    def get_active_providers(self) -> List[str]:
        """Get list of currently enabled providers"""
        return self.config.get_active_providers()
    
    def validate_all_providers(self) -> Dict[str, bool]:
        """Validate connection for all active providers
        
        Returns:
            Dictionary mapping provider names to connection status
        """
        active_providers = self.get_active_providers()
        validation_results = {}
        
        for provider_name in active_providers:
            try:
                provider = self.create(provider_name)
                is_connected = provider.validate_connection()
                validation_results[provider_name] = is_connected
                
                status = "✅ Connected" if is_connected else "❌ Disconnected"
                logger.info(f"{provider_name}: {status}")
                
            except Exception as e:
                validation_results[provider_name] = False
                logger.error(f"{provider_name}: ❌ Failed to validate - {e}")
        
        return validation_results
    
    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers
        
        Returns:
            Dictionary with provider metadata and status
        """
        provider_info = {}
        
        for provider_name in self.get_available_providers():
            try:
                is_enabled = self.config.is_provider_enabled(provider_name)
                config = self.config.get_provider_config(provider_name)
                
                info = {
                    'enabled': is_enabled,
                    'config': config,
                    'connected': False,
                    'metadata': {}
                }
                
                # Get additional metadata if provider is enabled
                if is_enabled:
                    try:
                        provider = self.create(provider_name)
                        info['connected'] = provider.validate_connection()
                        info['metadata'] = provider.get_provider_metadata()
                    except Exception as e:
                        logger.warning(f"Could not get metadata for {provider_name}: {e}")
                
                provider_info[provider_name] = info
                
            except Exception as e:
                logger.error(f"Error getting info for {provider_name}: {e}")
                provider_info[provider_name] = {
                    'enabled': False,
                    'error': str(e)
                }
        
        return provider_info