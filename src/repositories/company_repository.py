"""
Repository específico para empresas
Operações CRUD e consultas específicas para a tabela 'empresas'
"""
from typing import List, Dict, Any, Optional
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class CompanyRepository(BaseRepository):
    """Repository para operações com a tabela empresas"""
    
    @property
    def table_name(self) -> str:
        return "empresas"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_user_id(self, user_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar todas as empresas de um usuário específico"""
        return self.find_by_filters({'user_id': user_id}, limit=limit)
    
    def find_by_id_and_user(self, company_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar empresa por ID apenas se pertencer ao usuário"""
        companies = self.find_by_filters({'id': company_id, 'user_id': user_id}, limit=1)
        return companies[0] if companies else None
    
    def find_by_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Buscar empresa por CNPJ"""
        companies = self.find_by_filters({'cnpj': cnpj}, limit=1)
        return companies[0] if companies else None
    
    def find_by_cnpj_and_user(self, cnpj: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar empresa por CNPJ apenas se pertencer ao usuário"""
        companies = self.find_by_filters({'cnpj': cnpj, 'user_id': user_id}, limit=1)
        return companies[0] if companies else None
    
    def search_by_name(self, search_term: str, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar empresas por nome fantasia ou razão social"""
        base_query = """
            SELECT * FROM empresas 
            WHERE nome_fantasia ILIKE %s 
               OR razao_social ILIKE %s
        """
        
        params = [f"%{search_term}%", f"%{search_term}%"]
        
        # Adicionar filtro de usuário se fornecido
        if user_id:
            base_query += " AND user_id = %s"
            params.append(user_id)
        
        query = base_query + " ORDER BY nome_fantasia LIMIT %s"
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def search_by_products(self, products: List[str], limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar empresas por produtos/serviços"""
        if not products:
            return []
        
        # Construir condições para cada produto/serviço
        product_conditions = []
        params = []
        
        for product in products:
            product_pattern = f"%{product}%"
            product_conditions.append("""
                (descricao_servicos_produtos ILIKE %s 
                 OR produtos::text ILIKE %s
                 OR setor_atuacao ILIKE %s)
            """)
            params.extend([product_pattern, product_pattern, product_pattern])
        
        base_query = f"""
            SELECT *, 
                   (CASE 
                    WHEN nome_fantasia ILIKE ANY(ARRAY[{','.join(['%s'] * len(products))}]) THEN 3
                    WHEN descricao_servicos_produtos ILIKE ANY(ARRAY[{','.join(['%s'] * len(products))}]) THEN 2
                    ELSE 1
                   END) as relevance_score
            FROM empresas 
            WHERE {' OR '.join(product_conditions)}
        """
        
        # Adicionar produtos para os ARRAY[]
        product_patterns = [f"%{prod}%" for prod in products]
        all_params = product_patterns + product_patterns + params
        
        # Adicionar filtro de usuário se fornecido
        if user_id:
            base_query += " AND user_id = %s"
            all_params.append(user_id)
        
        query = base_query + " ORDER BY relevance_score DESC, nome_fantasia LIMIT %s"
        all_params.append(limit)
        
        return self.execute_custom_query(query, tuple(all_params))
    
    def get_companies_by_sector(self, sector: str, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar empresas por setor de atuação"""
        filters = {'setor_atuacao': sector}
        if user_id:
            filters['user_id'] = user_id
        return self.find_by_filters(filters, limit=limit)
    
    def get_companies_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Obter estatísticas das empresas"""
        base_query = """
            SELECT 
                COUNT(*) as total_empresas,
                COUNT(DISTINCT setor_atuacao) as total_setores,
                COUNT(CASE WHEN cnpj IS NOT NULL THEN 1 END) as empresas_com_cnpj,
                MAX(created_at) as ultima_empresa_criada,
                MIN(created_at) as primeira_empresa_criada
            FROM empresas
        """
        
        params = []
        if user_id:
            base_query += " WHERE user_id = %s"
            params.append(user_id)
        
        result = self.execute_custom_query(base_query, tuple(params))
        if result:
            stats = result[0]
            
            # Buscar setores mais comuns
            sectors_base_query = """
                SELECT setor_atuacao, COUNT(*) as quantidade
                FROM empresas 
                WHERE setor_atuacao IS NOT NULL
            """
            
            sectors_params = []
            if user_id:
                sectors_base_query += " AND user_id = %s"
                sectors_params.append(user_id)
                
            sectors_query = sectors_base_query + """
                GROUP BY setor_atuacao
                ORDER BY quantidade DESC
                LIMIT 10
            """
            
            stats['setores_principais'] = self.execute_custom_query(sectors_query, tuple(sectors_params))
            return stats
        
        return {
            'total_empresas': 0,
            'total_setores': 0,
            'empresas_com_cnpj': 0,
            'setores_principais': []
        }
    
    def get_companies_with_products_count(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obter empresas com quantidade de produtos/serviços"""
        base_query = """
            SELECT id, nome_fantasia, razao_social,
                   CASE 
                       WHEN produtos IS NULL THEN 0
                       ELSE jsonb_array_length(produtos)
                   END as total_products
            FROM empresas
        """
        
        params = []
        if user_id:
            base_query += " WHERE user_id = %s"
            params.append(user_id)
            
        query = base_query + " ORDER BY total_products DESC, nome_fantasia"
        
        return self.execute_custom_query(query, tuple(params))
    
    def update_products(self, company_id: str, products: List[str]) -> Optional[Dict[str, Any]]:
        """Atualizar produtos/serviços de uma empresa"""
        import json
        return self.update(company_id, {'produtos': json.dumps(products)})
    
    def bulk_create(self, companies_data: List[Dict[str, Any]]) -> List[str]:
        """Criar múltiplas empresas em uma transação"""
        created_ids = []
        
        with self.db_manager.get_transaction() as conn:
            with conn.cursor() as cursor:
                for company_data in companies_data:
                    # Adicionar timestamps
                    from datetime import datetime
                    if 'created_at' not in company_data:
                        company_data['created_at'] = datetime.now()
                    if 'updated_at' not in company_data:
                        company_data['updated_at'] = datetime.now()
                    
                    # Construir INSERT
                    columns = list(company_data.keys())
                    placeholders = ['%s'] * len(columns)
                    values = list(company_data.values())
                    
                    query = f"""
                        INSERT INTO empresas ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        RETURNING id
                    """
                    
                    cursor.execute(query, values)
                    created_ids.append(cursor.fetchone()[0])
        
        logger.info(f"Criadas {len(created_ids)} empresas em lote")
        return created_ids 