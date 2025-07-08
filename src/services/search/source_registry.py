from typing import Dict, Type
from .base_source import FonteBusca

class RegistroFontes:
    """Registro central de todas as fontes de busca disponíveis"""
    
    _fontes: Dict[str, Type[FonteBusca]] = {}
    
    @classmethod
    def registrar(cls, nome: str, fonte: Type[FonteBusca]):
        """
        Registra uma nova fonte de busca
        
        Args:
            nome: Identificador único da fonte
            fonte: Classe da fonte que implementa FonteBusca
        """
        cls._fontes[nome] = fonte
    
    @classmethod
    def obter_fonte(cls, nome: str) -> Type[FonteBusca]:
        """
        Retorna uma fonte de busca pelo nome
        
        Args:
            nome: Identificador da fonte
            
        Returns:
            Classe da fonte solicitada
            
        Raises:
            KeyError: Se a fonte não estiver registrada
        """
        if nome not in cls._fontes:
            raise KeyError(f"Fonte de busca '{nome}' não encontrada")
        return cls._fontes[nome]
    
    @classmethod
    def listar_fontes(cls) -> Dict[str, Type[FonteBusca]]:
        """Retorna todas as fontes registradas"""
        return cls._fontes.copy() 