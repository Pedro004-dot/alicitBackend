"""
Repository específico para análises
Operações CRUD e consultas específicas para análises de editais
"""
from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class AnalysisRepository(BaseRepository):
    """Repository para operações com análises de editais"""
    
    @property
    def table_name(self) -> str:
        return "analises_editais"  # ou "analysis" dependendo do schema
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_licitacao_id(self, licitacao_id: str) -> Optional[Dict[str, Any]]:
        """Buscar análise por ID da licitação"""
        analyses = self.find_by_filters({'licitacao_id': licitacao_id}, limit=1)
        return analyses[0] if analyses else None
    
    def find_documents_by_licitacao_id(self, licitacao_id: str) -> List[Dict[str, Any]]:
        """Buscar documentos processados de uma licitação"""
        query = """
            SELECT * FROM documentos_editais 
            WHERE licitacao_id = %s
            ORDER BY created_at DESC
        """
        return self.execute_custom_query(query, (licitacao_id,))
    
    def create_checklist_processing(self, licitacao_id: str, checklist_id: str) -> Dict[str, Any]:
        """Criar registro de processamento de checklist"""
        data = {
            'id': checklist_id,
            'licitacao_id': licitacao_id,
            'status_geracao': 'processando',
            'created_at': self.db_manager.get_connection().__enter__().cursor().execute("SELECT NOW()").fetchone()[0]
        }
        return self.create(data)
    
    def update_checklist_error(self, licitacao_id: str, error_message: str) -> Optional[Dict[str, Any]]:
        """Marcar checklist como erro"""
        analysis = self.find_by_licitacao_id(licitacao_id)
        if analysis:
            return self.update(analysis['id'], {
                'status_geracao': 'erro',
                'erro_detalhes': error_message
            })
        return None
    
    def find_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar análises por status"""
        return self.find_by_filters({'status_geracao': status}, limit=limit)
    
    def find_processing_analyses(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar análises em processamento"""
        return self.find_by_status('processando', limit=limit)
    
    def find_completed_analyses(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar análises concluídas"""
        return self.find_by_status('concluido', limit=limit)
    
    def find_failed_analyses(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar análises com erro"""
        return self.find_by_status('erro', limit=limit)
    
    def find_high_score_analyses(self, min_score: float = 0.8, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar análises com score alto"""
        query = """
            SELECT * FROM analises_editais 
            WHERE score_qualidade >= %s
            ORDER BY score_qualidade DESC, created_at DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (min_score, limit))
    
    def find_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar análises mais recentes"""
        query = """
            SELECT * FROM analises_editais 
            ORDER BY created_at DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))
    
    def get_document_count_by_licitacao(self, licitacao_id: str) -> int:
        """Contar documentos de uma licitação"""
        query = """
            SELECT COUNT(*) FROM documentos_editais 
            WHERE licitacao_id = %s
        """
        result = self.execute_custom_query(query, (licitacao_id,))
        return result[0]['count'] if result else 0
    
    def cleanup_old_processing(self, hours_old: int = 24) -> int:
        """Limpar processamentos antigos"""
        command = """
            UPDATE analises_editais 
            SET status_geracao = 'erro', erro_detalhes = 'Timeout - processamento abandonado'
            WHERE status_geracao = 'processando' 
            AND created_at < NOW() - INTERVAL '%s hours'
        """
        return self.execute_custom_command(command, (hours_old,))
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas das análises"""
        stats_query = """
            SELECT 
                COUNT(*) as total_analises,
                COUNT(CASE WHEN status_geracao = 'concluido' THEN 1 END) as concluidas,
                COUNT(CASE WHEN status_geracao = 'processando' THEN 1 END) as processando,
                COUNT(CASE WHEN status_geracao = 'erro' THEN 1 END) as com_erro,
                AVG(CASE WHEN score_qualidade IS NOT NULL THEN score_qualidade ELSE NULL END) as score_medio,
                MAX(created_at) as ultima_analise,
                MIN(created_at) as primeira_analise
            FROM analises_editais
        """
        
        result = self.execute_custom_query(stats_query)
        if result:
            return result[0]
        
        return {
            'total_analises': 0,
            'concluidas': 0,
            'processando': 0,
            'com_erro': 0,
            'score_medio': 0,
            'ultima_analise': None,
            'primeira_analise': None
        } 