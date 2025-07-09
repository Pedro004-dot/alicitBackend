"""
Interface base para mapeamento de dados entre providers e banco de dados
Implementa Strategy Pattern para escalabilidade seguindo SOLID principles
🚫 SALVAMENTO AUTOMÁTICO CONTROLADO - Cada mapper decide quando salvar
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from interfaces.procurement_data_source import OpportunityData


@dataclass
class DatabaseOpportunity:
    """Estrutura padronizada para persistência no banco de dados"""
    # Identificação
    external_id: str
    provider_name: str
    title: str
    description: Optional[str] = None
    
    # Valores financeiros
    estimated_value: Optional[float] = None
    currency_code: str = 'BRL'
    
    # Localização
    country_code: str = 'BR'
    region_code: Optional[str] = None
    municipality: Optional[str] = None
    
    # Temporal
    publication_date: Optional[str] = None
    submission_deadline: Optional[str] = None
    opening_date: Optional[str] = None
    
    # Classificação
    category: Optional[str] = None
    subcategory: Optional[str] = None
    procurement_method: Optional[str] = None
    
    # Status e organização
    status: str = 'active'
    contracting_authority: Optional[str] = None
    procuring_entity_id: Optional[str] = None
    procuring_entity_name: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    
    # Metadados
    source_url: Optional[str] = None
    documents: Optional[List[Dict[str, Any]]] = None
    additional_info: Optional[Dict[str, Any]] = None
    
    # Campos de auditoria
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class BaseDataMapper(ABC):
    """
    Interface base para mapeamento de dados específicos de cada provider
    
    Implementa Strategy Pattern para permitir diferentes estratégias de conversão
    sem modificar o código principal (Open/Closed Principle)
    
    🚫 CONTROLE DE SALVAMENTO AUTOMÁTICO
    Cada mapper pode decidir se deve salvar automaticamente ou só sob demanda
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Nome do provider que este mapper gerencia"""
        pass
    
    def should_auto_save(self) -> bool:
        """
        🚫 Controla se este mapper deve salvar automaticamente
        
        Returns:
            bool: True para salvar automaticamente, False para salvamento sob demanda
        """
        # Padrão: DESATIVADO para evitar inflação do banco
        # Providers específicos podem sobrescrever se necessário
        return False
    
    @abstractmethod
    def opportunity_to_database(self, opportunity: OpportunityData) -> DatabaseOpportunity:
        """
        Converte OpportunityData para formato do banco de dados
        
        Args:
            opportunity: Dados padronizados do provider
            
        Returns:
            DatabaseOpportunity: Estrutura pronta para persistência
        """
        pass
    
    @abstractmethod
    def database_to_opportunity(self, db_data: Dict[str, Any]) -> OpportunityData:
        """
        Converte dados do banco para OpportunityData
        
        Args:
            db_data: Dicionário com dados do banco
            
        Returns:
            OpportunityData: Estrutura padronizada do provider
        """
        pass
    
    @abstractmethod
    def validate_data(self, opportunity: OpportunityData) -> bool:
        """
        Valida se os dados estão no formato correto para o provider
        
        Args:
            opportunity: Dados a serem validados
            
        Returns:
            bool: True se válidos, False caso contrário
        """
        pass
    
    def get_unique_key(self, opportunity: OpportunityData) -> str:
        """
        Gera chave única para deduplicação
        
        Args:
            opportunity: Dados da oportunidade
            
        Returns:
            str: Chave única combinando provider e external_id
        """
        return f"{self.provider_name}:{opportunity.external_id}"
    
    def prepare_additional_info(self, opportunity: OpportunityData) -> Dict[str, Any]:
        """
        Prepara informações adicionais específicas do provider
        
        Args:
            opportunity: Dados da oportunidade
            
        Returns:
            Dict: Informações adicionais formatadas
        """
        return {
            'provider_name': self.provider_name,
            'source_url': opportunity.source_url,
            'raw_data_keys': list(opportunity.additional_info.keys()) if opportunity.additional_info else [],
            'auto_save_enabled': self.should_auto_save(),
            'save_policy': 'automatic' if self.should_auto_save() else 'on_demand'
        }


class DataMapperRegistry:
    """
    Registry para gerenciar mappers de diferentes providers
    
    Implementa Factory Pattern para criação dinâmica de mappers
    """
    
    def __init__(self):
        self._mappers: Dict[str, BaseDataMapper] = {}
    
    def register_mapper(self, provider_name: str, mapper: BaseDataMapper) -> None:
        """
        Registra um novo mapper
        
        Args:
            provider_name: Nome do provider
            mapper: Instância do mapper a ser registrado
        """
        self._mappers[provider_name] = mapper
    
    def get_mapper(self, provider_name: str) -> Optional[BaseDataMapper]:
        """
        Obtém mapper para um provider específico
        
        Args:
            provider_name: Nome do provider
            
        Returns:
            BaseDataMapper: Mapper correspondente ou None
        """
        return self._mappers.get(provider_name)
    
    def list_providers(self) -> List[str]:
        """
        Lista todos os providers registrados
        
        Returns:
            List[str]: Lista de nomes dos providers
        """
        return list(self._mappers.keys())
    
    def is_provider_supported(self, provider_name: str) -> bool:
        """
        Verifica se um provider é suportado
        
        Args:
            provider_name: Nome do provider
            
        Returns:
            bool: True se suportado
        """
        return provider_name in self._mappers
    
    def has_mapper(self, provider_name: str) -> bool:
        """
        Alias para is_provider_supported para compatibilidade
        
        Args:
            provider_name: Nome do provider
            
        Returns:
            bool: True se suportado
        """
        return self.is_provider_supported(provider_name)
    
    def get_auto_save_mappers(self) -> List[str]:
        """
        🚫 Lista mappers que têm salvamento automático habilitado
        
        Returns:
            List[str]: Lista de providers com auto-save ativo
        """
        auto_save_providers = []
        for provider_name, mapper in self._mappers.items():
            if mapper.should_auto_save():
                auto_save_providers.append(provider_name)
        return auto_save_providers
    
    def get_on_demand_mappers(self) -> List[str]:
        """
        📋 Lista mappers que usam salvamento sob demanda
        
        Returns:
            List[str]: Lista de providers com salvamento sob demanda
        """
        on_demand_providers = []
        for provider_name, mapper in self._mappers.items():
            if not mapper.should_auto_save():
                on_demand_providers.append(provider_name)
        return on_demand_providers


# Instância global do registry
data_mapper_registry = DataMapperRegistry() 