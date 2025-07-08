from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class FonteBusca(ABC):
    """Interface base para todas as fontes de busca de licitações"""
    
    @abstractmethod
    def buscar(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """
        Realiza a busca de licitações na fonte específica
        
        Args:
            filtros: Dicionário com os filtros a serem aplicados
            
        Returns:
            Lista de licitações no formato padronizado
        """
        pass
    
    @abstractmethod
    def normalizar_licitacao(self, licitacao: Dict) -> Dict:
        """
        Converte o formato específico da fonte para o formato padronizado
        
        Args:
            licitacao: Licitação no formato original da fonte
            
        Returns:
            Licitação no formato padronizado do sistema
        """
        pass 