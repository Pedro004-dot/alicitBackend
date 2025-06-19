"""
Repositories Module
Camada de acesso a dados padronizada usando PostgreSQL direto
"""

from .base_repository import BaseRepository
from .company_repository import CompanyRepository
from .licitacao_repository import LicitacaoRepository
from .match_repository import MatchRepository

__all__ = [
    'BaseRepository',
    'CompanyRepository', 
    'LicitacaoRepository',
    'MatchRepository'
] 