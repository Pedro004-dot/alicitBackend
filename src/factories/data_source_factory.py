"""
🏭 Factory para Data Sources
Implementa Factory Pattern + Singleton para gerenciar providers de dados
"""

import logging
from typing import Dict, Optional

from interfaces.procurement_data_source import ProcurementDataSource

logger = logging.getLogger(__name__)

class DataSourceFactory:
    """
    Factory para criação de Data Sources
    Implementa Singleton Pattern para evitar múltiplas instâncias
    """
    
    _instance: Optional['DataSourceFactory'] = None
    _data_sources: Dict[str, ProcurementDataSource] = {}
    
    def __new__(cls) -> 'DataSourceFactory':
        """Implementação do Singleton Pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("🏭 DataSourceFactory singleton criada")
        return cls._instance
    
    def get_data_source(self, provider_name: str) -> Optional[ProcurementDataSource]:
        """
        Obtém instância de um data source específico
        
        Args:
            provider_name: Nome do provider (ex: 'pncp', 'comprasnet')
            
        Returns:
            Instância do data source ou None se não suportado
        """
        if provider_name in self._data_sources:
            return self._data_sources[provider_name]
        
        try:
            if provider_name.lower() == 'pncp':
                from adapters.pncp_adapter import PNCPAdapter
                
                # 🔧 CORREÇÃO: Fornecer configuração padrão para PNCPAdapter
                default_config = {
                    'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
                    'timeout': 30,
                    'max_results': 1000,  # Limitar para busca unificada
                    'cache_ttl': 3600
                }
                
                instance = PNCPAdapter(default_config)
                self._data_sources[provider_name] = instance
                logger.info(f"✅ {provider_name} adapter criado e cacheado")
                return instance
                
            elif provider_name.lower() == 'comprasnet':
                from adapters.comprasnet_adapter import ComprasNetAdapter
                instance = ComprasNetAdapter()
                self._data_sources[provider_name] = instance
                logger.info(f"✅ {provider_name} adapter criado e cacheado")
                return instance
            
            else:
                logger.warning(f"⚠️ Provider não suportado: {provider_name}")
                return None
                
        except ImportError as e:
            logger.error(f"❌ Erro ao importar {provider_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao criar {provider_name}: {e}")
            return None
    
    def list_available_providers(self) -> list:
        """
        Lista todos os providers disponíveis
        
        Returns:
            Lista de nomes dos providers disponíveis
        """
        return ['pncp', 'comprasnet']
    
    def is_provider_supported(self, provider_name: str) -> bool:
        """
        Verifica se um provider é suportado
        
        Args:
            provider_name: Nome do provider
            
        Returns:
            True se suportado
        """
        return provider_name.lower() in ['pncp', 'comprasnet']
    
    def get_cached_providers(self) -> list:
        """
        Lista providers que já foram instanciados e estão em cache
        
        Returns:
            Lista de nomes dos providers em cache
        """
        return list(self._data_sources.keys())
    
    def clear_cache(self) -> None:
        """Limpa o cache de data sources"""
        self._data_sources.clear()
        logger.info("🧹 Cache de data sources limpo")


def get_data_source_factory() -> DataSourceFactory:
    """
    Função auxiliar para obter instância singleton da factory
    
    Returns:
        Instância singleton da DataSourceFactory
    """
    return DataSourceFactory()