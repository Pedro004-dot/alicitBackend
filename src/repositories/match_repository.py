"""
Repository específico para matches
Operações CRUD e consultas específicas para a tabela 'matches'
Sistema multi-tenant: filtra matches por user_id via empresas
"""
from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class MatchRepository(BaseRepository):
    """Repository para operações com a tabela matches"""
    
    @property
    def table_name(self) -> str:
        return "matches"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_user_id(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar todos os matches de empresas de um usuário específico"""
        query = """
            SELECT m.* FROM matches m
            JOIN empresas e ON m.empresa_id = e.id
            WHERE e.user_id = %s
            ORDER BY m.score_similaridade DESC, m.created_at DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (user_id, limit))
    
    def find_by_id_and_user(self, match_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar match por ID apenas se a empresa pertencer ao usuário"""
        query = """
            SELECT m.* FROM matches m
            JOIN empresas e ON m.empresa_id = e.id
            WHERE m.id = %s AND e.user_id = %s
            LIMIT 1
        """
        results = self.execute_custom_query(query, (match_id, user_id))
        return results[0] if results else None
    
    def find_by_company_id(self, empresa_id: str, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar matches por ID da empresa, opcionalmente filtrado por usuário"""
        if user_id:
            # Verificar se a empresa pertence ao usuário
            query = """
                SELECT m.* FROM matches m
                JOIN empresas e ON m.empresa_id = e.id
                WHERE m.empresa_id = %s AND e.user_id = %s
                ORDER BY m.score_similaridade DESC, m.created_at DESC
                LIMIT %s
            """
            return self.execute_custom_query(query, (empresa_id, user_id, limit))
        else:
            return self.find_by_filters({'empresa_id': empresa_id}, limit=limit)
    
    def find_by_licitacao_id(self, licitacao_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar matches por ID da licitação"""
        return self.find_by_filters({'licitacao_id': licitacao_id}, limit=limit)
    
    def find_high_score_matches(self, min_score: float = 0.8, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar matches com score alto, opcionalmente filtrado por usuário"""
        base_query = """
            SELECT m.* FROM matches m
        """
        
        params = [min_score]
        
        if user_id:
            base_query += """
                JOIN empresas e ON m.empresa_id = e.id
                WHERE m.score_similaridade >= %s AND e.user_id = %s
            """
            params.append(user_id)
        else:
            base_query += """
                WHERE m.score_similaridade >= %s
            """
        
        query = base_query + """
            ORDER BY m.score_similaridade DESC, m.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def find_matches_with_details(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar matches com detalhes de empresa e licitação, opcionalmente filtrado por usuário"""
        base_query = """
            SELECT 
                m.*,
                e.nome_fantasia as empresa_nome,
                e.razao_social as empresa_razao_social,
                e.cnpj as empresa_cnpj,
                l.objeto_compra as licitacao_objeto,
                l.valor_total_estimado as licitacao_valor,
                l.data_publicacao as licitacao_data_publicacao,
                l.uf as licitacao_uf,
                l.modalidade_nome as licitacao_modalidade
            FROM matches m
            JOIN empresas e ON m.empresa_id = e.id
            JOIN licitacoes l ON m.licitacao_id = l.id
        """
        
        params = []
        
        if user_id:
            base_query += " WHERE e.user_id = %s"
            params.append(user_id)
        
        query = base_query + """
            ORDER BY m.score_similaridade DESC, m.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def find_matches_by_company_with_details(self, empresa_id: str, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar matches de uma empresa com detalhes da licitação, validando propriedade se user_id fornecido"""
        base_query = """
            SELECT 
                m.*,
                l.objeto_compra,
                l.valor_total_estimado,
                l.data_publicacao,
                l.uf,
                l.modalidade_nome,
                l.status as licitacao_status
            FROM matches m
            JOIN licitacoes l ON m.licitacao_id = l.id
        """
        
        params = [empresa_id]
        
        if user_id:
            base_query += """
                JOIN empresas e ON m.empresa_id = e.id
                WHERE m.empresa_id = %s AND e.user_id = %s
            """
            params.append(user_id)
        else:
            base_query += " WHERE m.empresa_id = %s"
        
        query = base_query + """
            ORDER BY m.score_similaridade DESC, m.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def find_matches_by_licitacao_with_details(self, licitacao_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar matches de uma licitação com detalhes da empresa"""
        query = """
            SELECT 
                m.*,
                e.nome_fantasia,
                e.razao_social,
                e.cnpj,
                e.setor_atuacao,
                e.descricao_servicos_produtos
            FROM matches m
            JOIN empresas e ON m.empresa_id = e.id
            WHERE m.licitacao_id = %s
            ORDER BY m.score_similaridade DESC, m.created_at DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (licitacao_id, limit))
    
    def get_matches_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas dos matches"""
        stats_query = """
            SELECT 
                COUNT(*) as total_matches,
                AVG(score_similaridade) as score_medio,
                MAX(score_similaridade) as melhor_score,
                MIN(score_similaridade) as pior_score,
                COUNT(CASE WHEN score_similaridade >= 0.9 THEN 1 END) as matches_excelentes,
                COUNT(CASE WHEN score_similaridade >= 0.8 THEN 1 END) as matches_bons,
                COUNT(CASE WHEN score_similaridade >= 0.7 THEN 1 END) as matches_regulares,
                COUNT(DISTINCT empresa_id) as empresas_com_matches,
                COUNT(DISTINCT licitacao_id) as licitacoes_com_matches,
                MAX(created_at) as ultimo_match_criado,
                MIN(created_at) as primeiro_match_criado
            FROM matches
        """
        
        result = self.execute_custom_query(stats_query)
        if result:
            stats = result[0]
            
            # Buscar empresas com mais matches
            top_empresas_query = """
                SELECT 
                    e.nome_fantasia,
                    e.razao_social,
                    COUNT(m.id) as total_matches,
                    AVG(m.score_similaridade) as score_medio
                FROM matches m
                JOIN empresas e ON m.empresa_id = e.id
                GROUP BY e.id, e.nome_fantasia, e.razao_social
                ORDER BY COUNT(m.id) DESC, AVG(m.score_similaridade) DESC
                LIMIT 10
            """
            
            # Buscar score distribution
            score_distribution_query = """
                SELECT 
                    CASE 
                        WHEN score_similaridade >= 0.9 THEN '0.9-1.0'
                        WHEN score_similaridade >= 0.8 THEN '0.8-0.9'
                        WHEN score_similaridade >= 0.7 THEN '0.7-0.8'
                        WHEN score_similaridade >= 0.6 THEN '0.6-0.7'
                        WHEN score_similaridade >= 0.5 THEN '0.5-0.6'
                        ELSE '0.0-0.5'
                    END as faixa_score,
                    COUNT(*) as quantidade
                FROM matches
                GROUP BY 
                    CASE 
                        WHEN score_similaridade >= 0.9 THEN '0.9-1.0'
                        WHEN score_similaridade >= 0.8 THEN '0.8-0.9'
                        WHEN score_similaridade >= 0.7 THEN '0.7-0.8'
                        WHEN score_similaridade >= 0.6 THEN '0.6-0.7'
                        WHEN score_similaridade >= 0.5 THEN '0.5-0.6'
                        ELSE '0.0-0.5'
                    END
                ORDER BY faixa_score DESC
            """
            
            stats['top_empresas'] = self.execute_custom_query(top_empresas_query)
            stats['distribuicao_scores'] = self.execute_custom_query(score_distribution_query)
            
            return stats
        
        return {
            'total_matches': 0,
            'score_medio': 0,
            'melhor_score': 0,
            'pior_score': 0,
            'matches_excelentes': 0,
            'matches_bons': 0,
            'matches_regulares': 0,
            'empresas_com_matches': 0,
            'licitacoes_com_matches': 0,
            'top_empresas': [],
            'distribuicao_scores': []
        }
    
    def find_by_score_range(self, min_score: float, max_score: float, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar matches por faixa de score"""
        query = """
            SELECT * FROM matches 
            WHERE score_similaridade BETWEEN %s AND %s
            ORDER BY score_similaridade DESC, created_at DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (min_score, max_score, limit))
    
    def get_companies_with_matches_summary(self) -> List[Dict[str, Any]]:
        """Buscar empresas com resumo de matches (equivalente ao endpoint antigo)"""
        query = """
            SELECT 
                e.id as empresa_id,
                e.nome_fantasia as empresa_nome,
                e.razao_social,
                e.cnpj,
                e.setor_atuacao,
                COUNT(m.id) as total_matches,
                AVG(m.score_similaridade) as score_medio,
                MAX(m.score_similaridade) as melhor_score,
                MIN(m.score_similaridade) as pior_score
            FROM empresas e
            JOIN matches m ON e.id = m.empresa_id
            GROUP BY e.id, e.nome_fantasia, e.razao_social, e.cnpj, e.setor_atuacao
            HAVING COUNT(m.id) > 0
            ORDER BY COUNT(m.id) DESC, AVG(m.score_similaridade) DESC
        """
        return self.execute_custom_query(query)
    
    def find_duplicate_matches(self) -> List[Dict[str, Any]]:
        """Identificar possíveis matches duplicados"""
        query = """
            SELECT 
                empresa_id,
                licitacao_id,
                COUNT(*) as duplicatas,
                MIN(id) as primeiro_id,
                MAX(id) as ultimo_id,
                MIN(created_at) as primeira_data,
                MAX(created_at) as ultima_data
            FROM matches
            GROUP BY empresa_id, licitacao_id
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, empresa_id, licitacao_id
        """
        return self.execute_custom_query(query)
    
    def delete_by_company_id(self, empresa_id: str) -> int:
        """Deletar todos os matches de uma empresa"""
        command = "DELETE FROM matches WHERE empresa_id = %s"
        return self.execute_custom_command(command, (empresa_id,))
    
    def delete_by_licitacao_id(self, licitacao_id: str) -> int:
        """Deletar todos os matches de uma licitação"""
        command = "DELETE FROM matches WHERE licitacao_id = %s"
        return self.execute_custom_command(command, (licitacao_id,))
    
    def update_score(self, match_id: str, new_score: float) -> Optional[Dict[str, Any]]:
        """Atualizar score de um match"""
        return self.update(match_id, {'score_similaridade': new_score})
    
    def bulk_create_matches(self, matches_data: List[Dict[str, Any]]) -> List[str]:
        """Criar múltiplos matches em uma transação"""
        created_ids = []
        
        with self.db_manager.get_transaction() as conn:
            with conn.cursor() as cursor:
                for match_data in matches_data:
                    # Adicionar timestamps
                    from datetime import datetime
                    if 'created_at' not in match_data:
                        match_data['created_at'] = datetime.now()
                    if 'updated_at' not in match_data:
                        match_data['updated_at'] = datetime.now()
                    
                    # Construir INSERT
                    columns = list(match_data.keys())
                    placeholders = ['%s'] * len(columns)
                    values = list(match_data.values())
                    
                    query = f"""
                        INSERT INTO matches ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING id
                    """
                    
                    cursor.execute(query, values)
                    created_ids.append(cursor.fetchone()[0])
        
        logger.info(f"Criados {len(created_ids)} matches em lote")
        return created_ids
    
    def find_potential_matches(self, empresa_id: str, licitacao_id: str) -> List[Dict[str, Any]]:
        """Verificar se já existe match entre empresa e licitação"""
        return self.find_by_filters({
            'empresa_id': empresa_id,
            'licitacao_id': licitacao_id
        }, limit=1)
    
    def find_all_with_details(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar todos os matches com detalhes (alias para find_matches_with_details)"""
        return self.find_matches_with_details(limit=limit)

    def find_recent_matches(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Buscar matches mais recentes com dados completos de empresa e licitação"""
        query = """
            SELECT 
                m.id as match_id,
                m.score_similaridade,
                m.match_type as tipo_match,
                m.data_match as match_timestamp,
                -- Dados da empresa
                e.id as empresa_id,
                e.nome_fantasia as empresa_nome,
                e.razao_social as empresa_razao_social,
                e.cnpj as empresa_cnpj,
                -- Dados da licitação
                l.id as licitacao_id,
                l.pncp_id as licitacao_pncp_id,
                l.objeto_compra as licitacao_objeto,
                l.valor_total_estimado as licitacao_valor,
                l.uf as licitacao_uf,
                l.data_publicacao as licitacao_data_publicacao,
                l.data_encerramento_proposta as licitacao_data_encerramento
            FROM matches m
            JOIN empresas e ON m.empresa_id = e.id
            JOIN licitacoes l ON m.licitacao_id = l.id
            ORDER BY m.data_match DESC
            LIMIT %s
        """
        
        try:
            results = self.execute_custom_query(query, (limit,))
            
            # Formatar resultados para o frontend
            formatted_matches = []
            for match in results:
                formatted_match = {
                    'id': match.get('match_id'),
                    'score': float(match.get('score_similaridade', 0)),  # Já está em formato 0-1
                    'tipo_match': match.get('tipo_match'),
                    'timestamp': match.get('match_timestamp'),
                    'empresa': {
                        'id': match.get('empresa_id'),
                        'nome': match.get('empresa_nome'),
                        'razao_social': match.get('empresa_razao_social'),
                        'cnpj': match.get('empresa_cnpj')
                    },
                    'licitacao': {
                        'id': match.get('licitacao_id'),
                        'pncp_id': match.get('licitacao_pncp_id'),
                        'objeto_compra': match.get('licitacao_objeto'),
                        'valor_total_estimado': match.get('licitacao_valor'),
                        'uf': match.get('licitacao_uf'),
                        'data_publicacao': match.get('licitacao_data_publicacao'),
                        'data_encerramento_proposta': match.get('licitacao_data_encerramento')
                    }
                }
                formatted_matches.append(formatted_match)
                
            return formatted_matches
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar matches recentes: {e}")
            return []
    
    def find_grouped_by_company(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar matches agrupados por empresa, opcionalmente filtrado por usuário"""
        base_query = """
            SELECT 
                e.id as empresa_id,
                e.nome_fantasia as empresa_nome,
                e.razao_social,
                e.cnpj,
                e.setor_atuacao,
                COUNT(m.id) as total_matches,
                AVG(m.score_similaridade) as score_medio,
                MAX(m.score_similaridade) as melhor_score,
                MIN(m.score_similaridade) as pior_score
            FROM empresas e
            JOIN matches m ON e.id = m.empresa_id
        """
        
        params = []
        
        if user_id:
            base_query += " WHERE e.user_id = %s"
            params.append(user_id)
        
        query = base_query + """
            GROUP BY e.id, e.nome_fantasia, e.razao_social, e.cnpj, e.setor_atuacao
            HAVING COUNT(m.id) > 0
            ORDER BY COUNT(m.id) DESC, AVG(m.score_similaridade) DESC
        """
        
        return self.execute_custom_query(query, tuple(params) if params else ()) 