"""
Repository Base para padronizar operações CRUD com PostgreSQL
Elimina repetições de conexão/cursor e padroniza acesso a dados
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Tuple
from psycopg2.extras import DictCursor
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseRepository(ABC):
    """Repository base com operações CRUD padronizadas usando pool PostgreSQL"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    @property
    @abstractmethod
    def table_name(self) -> str:
        """Nome da tabela principal"""
        pass
    
    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Nome da chave primária"""
        pass
    
    def find_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar todos os registros com paginação opcional"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = f"SELECT * FROM {self.table_name}"
                params = []
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def find_by_id(self, record_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Buscar registro por ID"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = %s"
                cursor.execute(query, (record_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def find_by_filters(self, filters: Dict[str, Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar registros por filtros dinâmicos"""
        if not filters:
            return self.find_all(limit=limit)
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Construir WHERE dinamicamente
                where_clauses = []
                params = []
                
                for key, value in filters.items():
                    if value is None:
                        where_clauses.append(f"{key} IS NULL")
                    else:
                        where_clauses.append(f"{key} = %s")
                        params.append(value)
                
                query = f"SELECT * FROM {self.table_name} WHERE {' AND '.join(where_clauses)}"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Criar novo registro"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Adicionar timestamps se não existirem
                if 'created_at' not in data:
                    data['created_at'] = datetime.now()
                if 'updated_at' not in data:
                    data['updated_at'] = datetime.now()
                
                # Construir INSERT dinamicamente
                columns = list(data.keys())
                placeholders = ['%s'] * len(columns)
                values = list(data.values())
                
                query = f"""
                    INSERT INTO {self.table_name} ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    RETURNING *
                """
                
                cursor.execute(query, values)
                return dict(cursor.fetchone())
    
    def update(self, record_id: Union[str, int], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualizar registro existente"""
        if not data:
            return self.find_by_id(record_id)
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Adicionar timestamp de atualização
                data['updated_at'] = datetime.now()
                
                # Construir UPDATE dinamicamente
                set_clauses = []
                params = []
                
                for key, value in data.items():
                    set_clauses.append(f"{key} = %s")
                    params.append(value)
                
                params.append(record_id)
                
                query = f"""
                    UPDATE {self.table_name}
                    SET {', '.join(set_clauses)}
                    WHERE {self.primary_key} = %s
                    RETURNING *
                """
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                return dict(row) if row else None
    
    def delete(self, record_id: Union[str, int]) -> bool:
        """Deletar registro por ID"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = %s"
                cursor.execute(query, (record_id,))
                return cursor.rowcount > 0
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Contar registros com filtros opcionais"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                if not filters:
                    query = f"SELECT COUNT(*) FROM {self.table_name}"
                    cursor.execute(query)
                else:
                    where_clauses = []
                    params = []
                    
                    for key, value in filters.items():
                        if value is None:
                            where_clauses.append(f"{key} IS NULL")
                        else:
                            where_clauses.append(f"{key} = %s")
                            params.append(value)
                    
                    query = f"SELECT COUNT(*) FROM {self.table_name} WHERE {' AND '.join(where_clauses)}"
                    cursor.execute(query, params)
                
                return cursor.fetchone()[0]
    
    def exists(self, record_id: Union[str, int]) -> bool:
        """Verificar se registro existe"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = f"SELECT 1 FROM {self.table_name} WHERE {self.primary_key} = %s LIMIT 1"
                cursor.execute(query, (record_id,))
                return cursor.fetchone() is not None
    
    def execute_custom_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Executar query personalizada (SELECT)"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
    
    def execute_custom_command(self, command: str, params: Tuple = ()) -> int:
        """Executar comando personalizado (INSERT/UPDATE/DELETE)"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(command, params)
                return cursor.rowcount
    
    def find_with_pagination(self, page: int = 1, per_page: int = 20, 
                           where_clause: str = "", params: List[Any] = None,
                           order_by: str = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Buscar com paginação e metadados"""
        offset = (page - 1) * per_page
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Contar total
                count_query = f"SELECT COUNT(*) FROM {self.table_name}"
                if where_clause:
                    count_query += f" WHERE {where_clause}"
                
                cursor.execute(count_query, params or [])
                total_count = cursor.fetchone()[0]
                
                # Buscar dados
                query = f"SELECT * FROM {self.table_name}"
                if where_clause:
                    query += f" WHERE {where_clause}"
                
                if order_by:
                    query += f" ORDER BY {order_by}"
                
                query += " LIMIT %s OFFSET %s"
                
                execute_params = (params or []) + [per_page, offset]
                cursor.execute(query, execute_params)
                
                records = [dict(row) for row in cursor.fetchall()]
                
                # Metadados de paginação
                total_pages = (total_count + per_page - 1) // per_page
                pagination_meta = {
                    'current_page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
                
                return records, pagination_meta
    
    def _has_timestamps(self) -> bool:
        """Verificar se a tabela tem colunas de timestamp"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = %s AND column_name IN ('created_at', 'updated_at')
                """, (self.table_name,))
                
                timestamp_columns = [row[0] for row in cursor.fetchall()]
                return 'created_at' in timestamp_columns and 'updated_at' in timestamp_columns
    
    def _decimal_to_float(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Converter campos Decimal para float para serialização JSON"""
        result = {}
        for key, value in data.items():
            if hasattr(value, '__float__'):  # Decimal types
                result[key] = float(value)
            else:
                result[key] = value
        return result
    
    def _format_for_json(self, records: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Formatar registros para JSON (convert Decimal, etc)"""
        if isinstance(records, list):
            return [self._decimal_to_float(record) for record in records]
        else:
            return self._decimal_to_float(records) 