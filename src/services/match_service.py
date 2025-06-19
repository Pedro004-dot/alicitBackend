"""
Match Service
Lógica de negócio para operações com matches
Usa repository padronizado para acesso a dados
"""
import logging
from typing import List, Dict, Any, Optional
from repositories.match_repository import MatchRepository
from config.database import db_manager

logger = logging.getLogger(__name__)

class MatchService:
    """
    Service para lógica de negócio de matches
    PADRONIZADO: Usa MatchRepository para acesso a dados
    """
    
    def __init__(self):
        self.match_repo = MatchRepository(db_manager)
    
    def get_all_matches(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obter todos os matches com formatação para frontend
        Se user_id for fornecido, filtra apenas matches das empresas do usuário
        """
        try:
            if user_id:
                matches = self.match_repo.find_matches_with_details(limit=limit, user_id=user_id)
            else:
                matches = self.match_repo.find_matches_with_details(limit=limit)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches: {e}")
            return []
    
    def get_match_by_id(self, match_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Buscar match por ID com formatação, validando propriedade se user_id fornecido"""
        try:
            if user_id:
                match = self.match_repo.find_by_id_and_user(match_id, user_id)
            else:
                match = self.match_repo.find_by_id(match_id)
                
            if match:
                return self._format_match_for_frontend(match)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar match {match_id}: {e}")
            return None
    
    def get_matches_by_company(self, company_id: str, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obter matches de uma empresa específica com detalhes
        Se user_id fornecido, valida se a empresa pertence ao usuário
        """
        try:
            matches = self.match_repo.find_matches_by_company_with_details(company_id, limit, user_id=user_id)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches da empresa {company_id}: {e}")
            return []
    
    def get_matches_by_licitacao(self, licitacao_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obter matches de uma licitação específica com detalhes
        """
        try:
            matches = self.match_repo.find_matches_by_licitacao_with_details(licitacao_id, limit)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches da licitação {licitacao_id}: {e}")
            return []
    
    def get_high_score_matches(self, min_score: float = 0.8, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Buscar matches com score alto
        Se user_id fornecido, filtra apenas matches das empresas do usuário
        """
        try:
            matches = self.match_repo.find_high_score_matches(min_score, limit, user_id=user_id)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches com score alto: {e}")
            return []
    
    def create_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Criar novo match com validação de negócio
        """
        try:
            # Validações de negócio
            self._validate_match_data(match_data)
            
            # Verificar se match já existe
            existing = self.match_repo.find_potential_matches(
                match_data['empresa_id'], 
                match_data['licitacao_id']
            )
            
            if existing:
                return {
                    'success': False,
                    'message': 'Match já existe entre esta empresa e licitação',
                    'data': None
                }
            
            # Criar match
            created_match = self.match_repo.create(match_data)
            
            logger.info(f"Match criado: {created_match['id']}")
            
            return {
                'success': True,
                'message': 'Match criado com sucesso',
                'data': self._format_match_for_frontend(created_match)
            }
            
        except ValueError as e:
            logger.warning(f"Erro de validação ao criar match: {e}")
            return {
                'success': False,
                'message': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Erro ao criar match: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def update_match(self, match_id: str, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualizar match existente com validação
        """
        try:
            # Verificar se match existe
            if not self.match_repo.exists(match_id):
                return {
                    'success': False,
                    'message': 'Match não encontrado',
                    'data': None
                }
            
            # Validar score se fornecido
            if 'score_similaridade' in match_data:
                score = match_data['score_similaridade']
                if not isinstance(score, (int, float)) or score < 0 or score > 1:
                    return {
                        'success': False,
                        'message': 'Score deve ser um número entre 0 e 1',
                        'data': None
                    }
            
            # Atualizar match
            updated_match = self.match_repo.update(match_id, match_data)
            
            if updated_match:
                logger.info(f"Match atualizado: {match_id}")
                return {
                    'success': True,
                    'message': 'Match atualizado com sucesso',
                    'data': self._format_match_for_frontend(updated_match)
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao atualizar match',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao atualizar match {match_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def delete_match(self, match_id: str) -> Dict[str, Any]:
        """
        Deletar match
        """
        try:
            # Verificar se match existe
            match = self.match_repo.find_by_id(match_id)
            if not match:
                return {
                    'success': False,
                    'message': 'Match não encontrado',
                    'data': None
                }
            
            # Deletar match
            success = self.match_repo.delete(match_id)
            
            if success:
                logger.info(f"Match deletado: {match_id}")
                return {
                    'success': True,
                    'message': 'Match deletado com sucesso',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao deletar match',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao deletar match {match_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def get_matches_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas completas dos matches"""
        try:
            return self.match_repo.get_matches_statistics()
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de matches: {e}")
            return {}
    
    def get_companies_with_matches_summary(self) -> List[Dict[str, Any]]:
        """Buscar empresas com resumo de matches"""
        try:
            return self.match_repo.get_companies_with_matches_summary()
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de empresas com matches: {e}")
            return []
    
    def find_duplicate_matches(self) -> List[Dict[str, Any]]:
        """Identificar matches duplicados"""
        try:
            return self.match_repo.find_duplicate_matches()
        except Exception as e:
            logger.error(f"Erro ao buscar matches duplicados: {e}")
            return []
    
    def bulk_create_matches(self, matches_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Criar múltiplos matches em lote com validação
        """
        try:
            # Validar todos os matches antes de inserir
            validated_matches = []
            errors = []
            
            for i, match_data in enumerate(matches_data):
                try:
                    self._validate_match_data(match_data)
                    validated_matches.append(match_data)
                except Exception as e:
                    errors.append(f"Match {i+1}: {str(e)}")
            
            if errors:
                return {
                    'success': False,
                    'message': 'Erros de validação encontrados',
                    'data': {'errors': errors}
                }
            
            # Inserir matches em lote
            created_ids = self.match_repo.bulk_create_matches(validated_matches)
            
            logger.info(f"Importação em lote: {len(created_ids)} matches criados")
            
            return {
                'success': True,
                'message': f'{len(created_ids)} matches criados com sucesso',
                'data': {
                    'total_created': len(created_ids),
                    'match_ids': created_ids
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na criação em lote de matches: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def search_matches(self, search_filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar matches com filtros avançados
        """
        try:
            # Processar filtros de score
            if 'min_score' in search_filters and 'max_score' in search_filters:
                matches = self.match_repo.find_by_score_range(
                    search_filters['min_score'],
                    search_filters['max_score'],
                    limit
                )
            elif 'min_score' in search_filters:
                matches = self.match_repo.find_high_score_matches(
                    search_filters['min_score'],
                    limit
                )
            else:
                # Usar filtros simples
                matches = self.match_repo.find_by_filters(search_filters, limit)
            
            return self._format_matches_for_frontend(matches)
            
        except Exception as e:
            logger.error(f"Erro ao buscar matches com filtros: {e}")
            return []
    
    def _validate_match_data(self, data: Dict[str, Any]):
        """Validações de negócio para dados de match"""
        required_fields = ['empresa_id', 'licitacao_id', 'score_similaridade']
        
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'Campo obrigatório ausente: {field}')
        
        # Validar score
        score = data.get('score_similaridade')
        if not isinstance(score, (int, float)) or score < 0 or score > 1:
            raise ValueError('Score de similaridade deve ser um número entre 0 e 1')
    
    def _format_match_for_frontend(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Formatar match individual para frontend"""
        return {
            'id': str(match['id']),
            'empresa_id': str(match['empresa_id']),
            'licitacao_id': str(match['licitacao_id']),
            'score_similaridade': float(match.get('score_similaridade', 0)),
            'criterios_match': match.get('criterios_match', {}),
            'keywords_match': match.get('keywords_match', []),
            'created_at': match.get('created_at').isoformat() if match.get('created_at') else None,
            'updated_at': match.get('updated_at').isoformat() if match.get('updated_at') else None,
            # Campos extras se vierem do join
            'empresa_nome': match.get('nome_fantasia'),
            'empresa_cnpj': match.get('cnpj'),
            'licitacao_objeto': match.get('objeto_compra'),
            'licitacao_valor': float(match.get('valor_total_estimado', 0)) if match.get('valor_total_estimado') else None,
            'licitacao_uf': match.get('uf'),
            'licitacao_modalidade': match.get('modalidade_nome')
        }
    
    def _format_matches_for_frontend(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formatar lista de matches para frontend"""
        return [self._format_match_for_frontend(match) for match in matches] 