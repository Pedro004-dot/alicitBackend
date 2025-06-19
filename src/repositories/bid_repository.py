"""
Repository para Licitações (Bids)
Migração das operações de licitação do api.py para camada de dados dedicada
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from psycopg2.extras import DictCursor
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

class BidRepository(BaseRepository):
    """Repository para operações com licitações"""
    
    @property
    def table_name(self) -> str:
        return "licitacoes"
    
    @property 
    def primary_key(self) -> str:
        return "id"
    
    def find_all_formatted(self) -> List[Dict[str, Any]]:
        """
        Buscar todas as licitações formatadas para o frontend
        Migração do endpoint GET /api/bids do api.py linha 77-101
        """
        bids = self.find_all()
        
        formatted_bids = []
        for bid in bids:
            formatted_bids.append({
                'id': bid['id'],
                'pncp_id': bid['pncp_id'],
                'objeto_compra': bid['objeto_compra'],
                'valor_total_estimado': float(bid.get('valor_total_estimado', 0)) if bid.get('valor_total_estimado') else 0,
                'uf': bid.get('uf', ''),
                'status': bid.get('status', ''),
                'data_publicacao': bid.get('data_publicacao', ''),
                'modalidade_compra': 'Pregão Eletrônico'  # Valor padrão pois não está no BD
            })
        
        return formatted_bids
    
    def find_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar licitação por pncp_id
        Migração dos endpoints de busca específica do api.py
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM licitacoes WHERE pncp_id = %s",
                    (pncp_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Converter para dict e formatar dados
                bid_dict = dict(row)
                return self._format_for_json(bid_dict)
    
    def find_by_pncp_id_with_items(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar licitação com seus itens incluídos
        Migração do endpoint GET /api/bids/<pncp_id> do api.py linha 1040-1100
        """
        bid = self.find_by_pncp_id(pncp_id)
        
        if not bid:
            return None
        
        # Buscar itens da licitação
        items = self.find_items_by_bid_id(bid['id'])
        bid['itens'] = items
        bid['possui_itens'] = len(items) > 0
        
        return bid
    
    def find_items_by_pncp_id(self, pncp_id: str) -> List[Dict[str, Any]]:
        """
        Buscar itens de uma licitação pelo pncp_id
        Migração dos endpoints GET /api/bids/<pncp_id>/items e /api/bids/items
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Primeiro, buscar o ID da licitação pelo pncp_id
                cursor.execute("SELECT id FROM licitacoes WHERE pncp_id = %s", (pncp_id,))
                bid = cursor.fetchone()
                
                if not bid:
                    return []
                
                return self.find_items_by_bid_id(bid['id'])
    
    def find_items_by_bid_id(self, bid_id: str) -> List[Dict[str, Any]]:
        """
        Buscar itens de uma licitação pelo ID interno
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM licitacao_itens 
                    WHERE licitacao_id = %s 
                    ORDER BY numero_item
                """, (bid_id,))
                
                items = cursor.fetchall()
                items_list = []
                
                # Converter e formatar dados
                for item in items:
                    item_dict = dict(item)
                    items_list.append(self._format_for_json(item_dict))
                
                return items_list
    
    def find_detailed_with_pagination(self, page: int = 1, per_page: int = 20, 
                                    filters: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Buscar licitações com informações detalhadas e paginação
        Migração do endpoint GET /api/bids/detailed do api.py linha 1276-1355
        """
        # Construir filtros
        where_conditions = []
        params = []
        
        if filters:
            if filters.get('uf'):
                where_conditions.append("uf = %s")
                params.append(filters['uf'])
            
            if filters.get('modalidade_id'):
                where_conditions.append("modalidade_id = %s")
                params.append(int(filters['modalidade_id']))
            
            if filters.get('status'):
                where_conditions.append("status = %s")
                params.append(filters['status'])
        
        where_clause = ""
        if where_conditions:
            where_clause = " AND ".join(where_conditions)
        
        # Usar método de paginação da classe base
        order_by = "data_publicacao DESC, created_at DESC"
        records, pagination_meta = self.find_with_pagination(
            page=page,
            per_page=per_page,
            where_clause=where_clause,
            params=params,
            order_by=order_by
        )
        
        # Formatar registros para JSON
        formatted_records = [self._format_for_json(record) for record in records]
        
        return formatted_records, pagination_meta
    
    def count_all(self) -> int:
        """Contar total de licitações"""
        return self.count()
    
    def find_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar licitações mais recentes"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM licitacoes 
                    ORDER BY data_publicacao DESC, created_at DESC
                    LIMIT %s
                """, (limit,))
                
                bids = cursor.fetchall()
                return [self._format_for_json(dict(bid)) for bid in bids]
    
    def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Buscar licitações por status"""
        bids = self.find_by_field('status', status)
        return [self._format_for_json(bid) for bid in bids]
    
    def find_by_uf(self, uf: str) -> List[Dict[str, Any]]:
        """Buscar licitações por UF"""
        bids = self.find_by_field('uf', uf)
        return [self._format_for_json(bid) for bid in bids] 