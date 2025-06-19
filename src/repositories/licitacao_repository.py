"""
Repository específico para licitações
Operações CRUD e consultas específicas para a tabela 'licitacoes'
"""
from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class LicitacaoRepository(BaseRepository):
    """Repository para operações com a tabela licitacoes"""
    
    @property
    def table_name(self) -> str:
        return "licitacoes"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Buscar licitação por ID"""
        query = """
            SELECT * FROM licitacoes WHERE id = %s
        """
        results = self.execute_custom_query(query, (id,))
        return results[0] if results else None
    
    def find_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """Buscar licitação por ID do PNCP com todos os campos novos"""
        query = """
            SELECT 
                id, pncp_id, orgao_cnpj, ano_compra, sequencial_compra,
                objeto_compra, link_sistema_origem, data_publicacao,
                valor_total_estimado, uf, status, created_at, updated_at,
                -- Novos campos da API 1
                numero_controle_pncp, numero_compra, processo,
                valor_total_homologado, data_abertura_proposta, data_encerramento_proposta,
                modo_disputa_id, modo_disputa_nome, srp,
                link_processo_eletronico, justificativa_presencial, razao_social,
                -- Novos campos da unidadeOrgao
                uf_nome, nome_unidade, municipio_nome, codigo_ibge, codigo_unidade
            FROM licitacoes 
            WHERE pncp_id = %s
            LIMIT 1
        """
        results = self.execute_custom_query(query, (pncp_id,))
        return results[0] if results else None
    
    def find_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por status"""
        return self.find_by_filters({'status': status}, limit=limit)
    
    def find_pending_for_processing(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações pendentes para processamento"""
        return self.find_by_status('coletada', limit=limit)
    
    def search_by_object(self, search_term: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por objeto"""
        query = """
            SELECT * FROM licitacoes 
            WHERE objeto_compra ILIKE %s
            ORDER BY data_publicacao DESC, valor_total_estimado DESC
            LIMIT %s
        """
        search_pattern = f"%{search_term}%"
        return self.execute_custom_query(query, (search_pattern, limit))
    
    def find_by_value_range(self, min_value: Optional[float] = None, 
                           max_value: Optional[float] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por faixa de valor"""
        where_clauses = []
        params = []
        
        if min_value is not None:
            where_clauses.append("valor_total_estimado >= %s")
            params.append(min_value)
        
        if max_value is not None:
            where_clauses.append("valor_total_estimado <= %s")
            params.append(max_value)
        
        if not where_clauses:
            return self.find_all(limit=limit)
        
        query = f"""
            SELECT * FROM licitacoes 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY valor_total_estimado DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def find_by_uf(self, uf: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por UF"""
        return self.find_by_filters({'uf': uf}, limit=limit)
    
    def find_by_date_range(self, start_date: str, end_date: str, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por período de publicação"""
        query = """
            SELECT * FROM licitacoes 
            WHERE data_publicacao BETWEEN %s AND %s
            ORDER BY data_publicacao DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (start_date, end_date, limit))
    
    def find_by_modalidade(self, modalidade_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por modalidade"""
        return self.find_by_filters({'modalidade_id': modalidade_id}, limit=limit)
    
    def get_licitacoes_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas das licitações"""
        stats_query = """
            SELECT 
                COUNT(*) as total_licitacoes,
                COUNT(DISTINCT uf) as total_ufs,
                COUNT(DISTINCT modalidade_id) as total_modalidades,
                SUM(CASE WHEN valor_total_estimado IS NOT NULL THEN valor_total_estimado ELSE 0 END) as valor_total_estimado,
                AVG(CASE WHEN valor_total_estimado IS NOT NULL THEN valor_total_estimado ELSE NULL END) as valor_medio,
                COUNT(CASE WHEN status = 'coletada' THEN 1 END) as coletadas,
                COUNT(CASE WHEN status = 'processada' THEN 1 END) as processadas,
                COUNT(CASE WHEN status = 'matched' THEN 1 END) as com_matches,
                MAX(data_publicacao) as ultima_publicacao,
                MIN(data_publicacao) as primeira_publicacao
            FROM licitacoes
        """
        
        result = self.execute_custom_query(stats_query)
        if result:
            stats = result[0]
            
            # Buscar modalidades mais comuns
            modalidades_query = """
                SELECT modalidade_nome, modalidade_id, COUNT(*) as quantidade
                FROM licitacoes 
                WHERE modalidade_nome IS NOT NULL
                GROUP BY modalidade_nome, modalidade_id
                ORDER BY quantidade DESC
                LIMIT 10
            """
            
            # Buscar UFs mais ativas
            ufs_query = """
                SELECT uf, COUNT(*) as quantidade
                FROM licitacoes 
                WHERE uf IS NOT NULL
                GROUP BY uf
                ORDER BY quantidade DESC
                LIMIT 10
            """
            
            stats['modalidades_principais'] = self.execute_custom_query(modalidades_query)
            stats['ufs_mais_ativas'] = self.execute_custom_query(ufs_query)
            
            return stats
        
        return {
            'total_licitacoes': 0,
            'total_ufs': 0,
            'total_modalidades': 0,
            'valor_total_estimado': 0,
            'valor_medio': 0,
            'coletadas': 0,
            'processadas': 0,
            'com_matches': 0,
            'modalidades_principais': [],
            'ufs_mais_ativas': []
        }
    
    def update_status(self, licitacao_id: str, new_status: str) -> Optional[Dict[str, Any]]:
        """Atualizar status de uma licitação"""
        return self.update(licitacao_id, {'status': new_status})
    
    def mark_as_processed(self, licitacao_id: str) -> Optional[Dict[str, Any]]:
        """Marcar licitação como processada"""
        return self.update_status(licitacao_id, 'processada')
    
    def mark_as_matched(self, licitacao_id: str) -> Optional[Dict[str, Any]]:
        """Marcar licitação como tendo matches"""
        return self.update_status(licitacao_id, 'matched')
    
    def find_with_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações que possuem itens"""
        return self.find_by_filters({'possui_itens': True}, limit=limit)
    
    def search_advanced(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """Busca avançada com múltiplos filtros"""
        where_clauses = []
        params = []
        
        # Filtro por objeto (ILIKE)
        if filters.get('objeto'):
            where_clauses.append("objeto_compra ILIKE %s")
            params.append(f"%{filters['objeto']}%")
        
        # Filtro por UF
        if filters.get('uf'):
            where_clauses.append("uf = %s")
            params.append(filters['uf'])
        
        # Filtro por status
        if filters.get('status'):
            where_clauses.append("status = %s")
            params.append(filters['status'])
        
        # Filtro por modalidade
        if filters.get('modalidade_id'):
            where_clauses.append("modalidade_id = %s")
            params.append(filters['modalidade_id'])
        
        # Filtro por valor mínimo
        if filters.get('valor_min'):
            where_clauses.append("valor_total_estimado >= %s")
            params.append(filters['valor_min'])
        
        # Filtro por valor máximo
        if filters.get('valor_max'):
            where_clauses.append("valor_total_estimado <= %s")
            params.append(filters['valor_max'])
        
        # Filtro por data de publicação (início)
        if filters.get('data_inicio'):
            where_clauses.append("data_publicacao >= %s")
            params.append(filters['data_inicio'])
        
        # Filtro por data de publicação (fim)
        if filters.get('data_fim'):
            where_clauses.append("data_publicacao <= %s")
            params.append(filters['data_fim'])
        
        if not where_clauses:
            return self.find_all(limit=limit)
        
        query = f"""
            SELECT * FROM licitacoes 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY data_publicacao DESC, valor_total_estimado DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def bulk_update_status(self, licitacao_ids: List[str], new_status: str) -> int:
        """Atualizar status de múltiplas licitações"""
        if not licitacao_ids:
            return 0
        
        placeholders = ','.join(['%s'] * len(licitacao_ids))
        params = [new_status] + licitacao_ids
        
        command = f"""
            UPDATE licitacoes 
            SET status = %s, updated_at = NOW()
            WHERE id IN ({placeholders})
        """
        
        return self.execute_custom_command(command, tuple(params))
    
    def find_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar licitações mais recentes baseado na data de publicação"""
        query = """
            SELECT * FROM licitacoes 
            ORDER BY 
                CASE 
                    WHEN data_publicacao IS NOT NULL THEN data_publicacao
                    ELSE created_at
                END DESC 
            LIMIT %s
        """
        
        return self.execute_custom_query(query, (limit,))
    
    def find_items_by_licitacao_id(self, licitacao_id: str) -> List[Dict[str, Any]]:
        """Buscar itens de uma licitação específica pelo ID interno com todos os campos novos"""
        query = """
            SELECT 
                id, licitacao_id, numero_item, descricao, quantidade,
                unidade_medida, valor_unitario_estimado, created_at, updated_at,
                -- Novos campos da API 2
                material_ou_servico, ncm_nbs_codigo,
                criterio_julgamento_id, criterio_julgamento_nome,
                tipo_beneficio_id, tipo_beneficio_nome,
                situacao_item_id, situacao_item_nome,
                aplicabilidade_margem_preferencia, percentual_margem_preferencia,
                tem_resultado
            FROM licitacao_itens 
            WHERE licitacao_id = %s 
            ORDER BY numero_item
        """
        
        return self.execute_custom_query(query, (licitacao_id,))
    
    def find_active_bids(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações ativas (ainda em prazo)"""
        query = """
            SELECT * FROM licitacoes 
            WHERE 
                (data_abertura IS NULL OR data_abertura >= CURRENT_DATE)
                AND status != 'cancelada'
            ORDER BY data_publicacao DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))

    def find_active_bids_after_date(self, after_date: str = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar licitações ativas (data_encerramento_proposta > data especificada)"""
        if after_date:
            if limit is not None:
                query = """
                    SELECT * FROM licitacoes 
                    WHERE 
                        data_encerramento_proposta > %s
                        AND status != 'cancelada'
                    ORDER BY data_encerramento_proposta ASC
                    LIMIT %s
                """
                return self.execute_custom_query(query, (after_date, limit))
            else:
                query = """
                    SELECT * FROM licitacoes 
                    WHERE 
                        data_encerramento_proposta > %s
                        AND status != 'cancelada'
                    ORDER BY data_encerramento_proposta ASC
                """
                return self.execute_custom_query(query, (after_date,))
        else:
            # Se não especificar data, usar hoje
            if limit is not None:
                query = """
                    SELECT * FROM licitacoes 
                    WHERE 
                        data_encerramento_proposta > CURRENT_DATE
                        AND status != 'cancelada'
                    ORDER BY data_encerramento_proposta ASC
                    LIMIT %s
                """
                return self.execute_custom_query(query, (limit,))
            else:
                query = """
                    SELECT * FROM licitacoes 
                    WHERE 
                        data_encerramento_proposta > CURRENT_DATE
                        AND status != 'cancelada'
                    ORDER BY data_encerramento_proposta ASC
                """
                return self.execute_custom_query(query, ())
    
    def find_high_value_bids(self, min_value: float = 1000000, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações de alto valor"""
        query = """
            SELECT * FROM licitacoes 
            WHERE valor_total_estimado >= %s
            ORDER BY valor_total_estimado DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (min_value, limit))
    
    def find_by_state(self, uf: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações por estado (alias para find_by_uf)"""
        return self.find_by_uf(uf, limit)
    
    def find_by_modality(self, modalidade: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações por modalidade (nome)"""
        query = """
            SELECT * FROM licitacoes 
            WHERE modalidade_nome ILIKE %s
            ORDER BY data_publicacao DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (f"%{modalidade}%", limit))
    
    # ===== NOVAS FUNÇÕES APROVEITANDO OS CAMPOS DAS APIs =====
    
    def find_srp_licitacoes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações com Sistema de Registro de Preços (SRP)"""
        query = """
            SELECT 
                id, pncp_id, objeto_compra, orgao_cnpj, uf,
                valor_total_estimado, data_abertura_proposta, data_encerramento_proposta,
                srp, numero_controle_pncp, link_sistema_origem
            FROM licitacoes 
            WHERE srp = true
            ORDER BY data_abertura_proposta DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))
    
    def find_active_proposals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações com prazo de propostas ainda aberto"""
        query = """
            SELECT 
                id, pncp_id, objeto_compra, orgao_cnpj, uf,
                valor_total_estimado, data_abertura_proposta, data_encerramento_proposta,
                numero_controle_pncp, link_sistema_origem, srp
            FROM licitacoes 
            WHERE data_encerramento_proposta > NOW()
            ORDER BY data_encerramento_proposta ASC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))
    
    def find_by_modo_disputa(self, modo_disputa_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações por modo de disputa (aberto, fechado, etc.)"""
        query = """
            SELECT * FROM licitacoes 
            WHERE modo_disputa_id = %s
            ORDER BY data_publicacao DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (modo_disputa_id, limit))
    
    def find_items_by_material_servico(self, tipo: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar itens por tipo: 'M' (Material) ou 'S' (Serviço)"""
        query = """
            SELECT 
                li.*, l.pncp_id, l.objeto_compra, l.orgao_cnpj
            FROM licitacao_itens li
            JOIN licitacoes l ON li.licitacao_id = l.id
            WHERE li.material_ou_servico = %s
            ORDER BY li.valor_unitario_estimado DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (tipo, limit))
    
    def find_items_by_ncm(self, ncm_codigo: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar itens por código NCM/NBS"""
        query = """
            SELECT 
                li.*, l.pncp_id, l.objeto_compra, l.orgao_cnpj, l.uf
            FROM licitacao_itens li
            JOIN licitacoes l ON li.licitacao_id = l.id
            WHERE li.ncm_nbs_codigo = %s
            ORDER BY li.valor_unitario_estimado DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (ncm_codigo, limit))
    
    def find_items_me_epp_only(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar itens com participação exclusiva para ME/EPP"""
        query = """
            SELECT 
                li.*, l.pncp_id, l.objeto_compra, l.orgao_cnpj, l.uf
            FROM licitacao_itens li
            JOIN licitacoes l ON li.licitacao_id = l.id
            WHERE li.tipo_beneficio_nome ILIKE '%exclusiv%ME%EPP%'
               OR li.tipo_beneficio_nome ILIKE '%micro%pequen%'
            ORDER BY li.valor_unitario_estimado DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Estatísticas aprimoradas com os novos campos"""
        stats = self.get_licitacoes_statistics()
        
        # Estatísticas SRP
        srp_query = """
            SELECT 
                COUNT(*) as total_srp,
                AVG(valor_total_estimado) as valor_medio_srp,
                COUNT(CASE WHEN data_encerramento_proposta > NOW() THEN 1 END) as srp_abertas
            FROM licitacoes 
            WHERE srp = true
        """
        srp_stats = self.execute_custom_query(srp_query)
        if srp_stats:
            stats.update(srp_stats[0])
        
        # Estatísticas de itens por tipo
        items_type_query = """
            SELECT 
                material_ou_servico,
                COUNT(*) as quantidade,
                AVG(valor_unitario_estimado) as valor_medio,
                SUM(valor_unitario_estimado * quantidade) as valor_total
            FROM licitacao_itens 
            WHERE material_ou_servico IS NOT NULL
            GROUP BY material_ou_servico
        """
        stats['tipos_item'] = self.execute_custom_query(items_type_query)
        
        # Estatísticas de modo de disputa
        modo_disputa_query = """
            SELECT 
                modo_disputa_nome,
                COUNT(*) as quantidade,
                AVG(valor_total_estimado) as valor_medio
            FROM licitacoes 
            WHERE modo_disputa_nome IS NOT NULL
            GROUP BY modo_disputa_nome
            ORDER BY quantidade DESC
        """
        stats['modos_disputa'] = self.execute_custom_query(modo_disputa_query)
        
        return stats 