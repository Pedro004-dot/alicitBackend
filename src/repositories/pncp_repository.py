"""
PNCP Repository
Repository para operações de banco de dados relacionadas às buscas no PNCP
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class PNCPRepository(BaseRepository):
    """Repository para operações relacionadas ao PNCP"""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.results_table = 'pncp_search_results'
    
    @property
    def table_name(self) -> str:
        """Nome da tabela principal"""
        return 'pncp_searches'
    
    @property
    def primary_key(self) -> str:
        """Nome da chave primária"""
        return 'id'
    
    def save_search(self, search_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Salva uma busca realizada no PNCP para histórico
        
        Args:
            search_data: Dados da busca (keywords, datas, metadados, etc.)
            
        Returns:
            Dados da busca salva com ID gerado
        """
        try:
            # Preparar dados para inserção
            insert_data = {
                'keywords': search_data.get('keywords', ''),
                'data_inicio': search_data.get('data_inicio'),
                'data_fim': search_data.get('data_fim'),
                'modalidade': search_data.get('modalidade', 'pregao_eletronico'),
                'max_pages': search_data.get('max_pages', 5),
                'total_api_results': search_data.get('total_api_results', 0),
                'total_filtered_results': search_data.get('total_filtered_results', 0),
                'search_metadata': json.dumps(search_data.get('search_metadata', {})),
                'created_at': datetime.now().isoformat(),
                'user_id': search_data.get('user_id'),  # Se houver autenticação
                'status': 'completed'
            }
            
            # Inserir no banco
            query = f"""
                INSERT INTO {self.table_name} 
                (keywords, data_inicio, data_fim, modalidade, max_pages, 
                 total_api_results, total_filtered_results, search_metadata, 
                 created_at, user_id, status)
                VALUES (%(keywords)s, %(data_inicio)s, %(data_fim)s, %(modalidade)s, 
                        %(max_pages)s, %(total_api_results)s, %(total_filtered_results)s, 
                        %(search_metadata)s, %(created_at)s, %(user_id)s, %(status)s)
                RETURNING *
            """
            
            result = self.db_manager.execute_query(query, insert_data, fetch_one=True)
            
            if result:
                logger.info(f"✅ Busca PNCP salva: ID {result['id']}")
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar busca PNCP: {e}")
            return None
    
    def save_search_results(self, search_id: int, results: List[Dict[str, Any]]) -> bool:
        """
        Salva os resultados de uma busca PNCP
        
        Args:
            search_id: ID da busca no banco
            results: Lista de licitações encontradas
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            if not results:
                logger.info("📝 Nenhum resultado para salvar")
                return True
            
            # Preparar dados para inserção em lote
            insert_values = []
            
            for result in results:
                insert_data = {
                    'search_id': search_id,
                    'pncp_id': result.get('pncp_id', ''),
                    'objeto_compra': result.get('objeto_compra', ''),
                    'modalidade_nome': result.get('modalidade_nome', ''),
                    'codigo_modalidade': result.get('codigo_modalidade'),
                    'unidade_compra': result.get('unidade_compra', ''),
                    'data_inicio_lances': result.get('data_inicio_lances'),
                    'data_encerramento_proposta': result.get('data_encerramento_proposta'),
                    'valor_total_estimado': result.get('valor_total_estimado', 0),
                    'uf': result.get('uf', ''),
                    'municipio': result.get('municipio', ''),
                    'situacao': result.get('situacao', ''),
                    'srp': result.get('srp', False),
                    'fonte_dados': result.get('fonte_dados', 'PNCP_API'),
                    'api_data': json.dumps(result.get('api_data', {})),
                    'data_importacao': result.get('data_importacao', datetime.now().isoformat()),
                    'created_at': datetime.now().isoformat()
                }
                insert_values.append(insert_data)
            
            # Inserir em lote para melhor performance
            success_count = 0
            
            for data in insert_values:
                query = f"""
                    INSERT INTO {self.results_table}
                    (search_id, pncp_id, objeto_compra, modalidade_nome, codigo_modalidade,
                     unidade_compra, data_inicio_lances, data_encerramento_proposta,
                     valor_total_estimado, uf, municipio, situacao, srp, fonte_dados,
                     api_data, data_importacao, created_at)
                    VALUES (%(search_id)s, %(pncp_id)s, %(objeto_compra)s, %(modalidade_nome)s,
                            %(codigo_modalidade)s, %(unidade_compra)s, %(data_inicio_lances)s,
                            %(data_encerramento_proposta)s, %(valor_total_estimado)s, %(uf)s,
                            %(municipio)s, %(situacao)s, %(srp)s, %(fonte_dados)s, %(api_data)s,
                            %(data_importacao)s, %(created_at)s)
                    ON CONFLICT (pncp_id) DO UPDATE SET
                        objeto_compra = EXCLUDED.objeto_compra,
                        modalidade_nome = EXCLUDED.modalidade_nome,
                        data_importacao = EXCLUDED.data_importacao,
                        updated_at = NOW()
                """
                
                try:
                    self.db_manager.execute_query(query, data)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao salvar resultado individual: {e}")
                    continue
            
            logger.info(f"✅ Salvos {success_count}/{len(insert_values)} resultados da busca {search_id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar resultados da busca: {e}")
            return False
    
    def get_search_history(self, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca histórico de pesquisas realizadas
        
        Args:
            limit: Número máximo de registros
            user_id: ID do usuário (opcional, para filtrar por usuário)
            
        Returns:
            Lista de buscas realizadas
        """
        try:
            base_query = f"""
                SELECT 
                    id, keywords, data_inicio, data_fim, modalidade,
                    total_api_results, total_filtered_results, 
                    created_at, status
                FROM {self.table_name}
            """
            
            if user_id:
                query = f"{base_query} WHERE user_id = %(user_id)s"
                params = {'user_id': user_id, 'limit': limit}
            else:
                query = base_query
                params = {'limit': limit}
            
            query += " ORDER BY created_at DESC LIMIT %(limit)s"
            
            results = self.db_manager.execute_query(query, params, fetch_all=True)
            
            return results or []
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico: {e}")
            return []
    
    def get_search_results(self, search_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca resultados de uma pesquisa específica
        
        Args:
            search_id: ID da busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de licitações encontradas na busca
        """
        try:
            query = f"""
                SELECT 
                    pncp_id, objeto_compra, modalidade_nome, codigo_modalidade,
                    unidade_compra, data_inicio_lances, data_encerramento_proposta,
                    valor_total_estimado, uf, municipio, situacao, srp,
                    fonte_dados, api_data, data_importacao, created_at
                FROM {self.results_table}
                WHERE search_id = %(search_id)s
                ORDER BY valor_total_estimado DESC, created_at DESC
                LIMIT %(limit)s
            """
            
            results = self.db_manager.execute_query(
                query, 
                {'search_id': search_id, 'limit': limit}, 
                fetch_all=True
            )
            
            return results or []
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar resultados da pesquisa {search_id}: {e}")
            return []
    
    def get_search_by_id(self, search_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca informações de uma pesquisa específica por ID
        
        Args:
            search_id: ID da busca
            
        Returns:
            Dados da busca ou None se não encontrada
        """
        try:
            query = f"""
                SELECT * FROM {self.table_name}
                WHERE id = %(search_id)s
            """
            
            result = self.db_manager.execute_query(
                query, 
                {'search_id': search_id}, 
                fetch_one=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar pesquisa {search_id}: {e}")
            return None
    
    def delete_search(self, search_id: int) -> bool:
        """
        Remove uma busca e seus resultados
        
        Args:
            search_id: ID da busca para remover
            
        Returns:
            True se removeu com sucesso
        """
        try:
            # Primeiro, remover resultados
            delete_results_query = f"DELETE FROM {self.results_table} WHERE search_id = %(search_id)s"
            self.db_manager.execute_query(delete_results_query, {'search_id': search_id})
            
            # Depois, remover a busca
            delete_search_query = f"DELETE FROM {self.table_name} WHERE id = %(search_id)s"
            self.db_manager.execute_query(delete_search_query, {'search_id': search_id})
            
            logger.info(f"✅ Busca {search_id} e resultados removidos")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao remover busca {search_id}: {e}")
            return False
    
    def get_popular_keywords(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Busca palavras-chave mais utilizadas nas pesquisas
        
        Args:
            limit: Número máximo de palavras-chave
            
        Returns:
            Lista de palavras-chave ordenadas por frequência
        """
        try:
            query = f"""
                SELECT 
                    keywords,
                    COUNT(*) as frequency,
                    AVG(total_filtered_results) as avg_results,
                    MAX(created_at) as last_used
                FROM {self.table_name}
                WHERE keywords IS NOT NULL AND keywords != ''
                GROUP BY keywords
                ORDER BY frequency DESC, avg_results DESC
                LIMIT %(limit)s
            """
            
            results = self.db_manager.execute_query(
                query, 
                {'limit': limit}, 
                fetch_all=True
            )
            
            return results or []
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar palavras-chave populares: {e}")
            return []
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Busca estatísticas gerais das pesquisas PNCP
        
        Returns:
            Dicionário com estatísticas das buscas
        """
        try:
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_searches,
                    SUM(total_api_results) as total_api_results,
                    SUM(total_filtered_results) as total_filtered_results,
                    AVG(total_filtered_results) as avg_results_per_search,
                    COUNT(DISTINCT modalidade) as unique_modalities,
                    MIN(created_at) as first_search,
                    MAX(created_at) as last_search
                FROM {self.table_name}
            """
            
            result = self.db_manager.execute_query(stats_query, {}, fetch_one=True)
            
            if not result:
                return {
                    'total_searches': 0,
                    'total_api_results': 0,
                    'total_filtered_results': 0,
                    'avg_results_per_search': 0,
                    'unique_modalities': 0,
                    'first_search': None,
                    'last_search': None
                }
            
            return {
                'total_searches': result.get('total_searches', 0),
                'total_api_results': result.get('total_api_results', 0),
                'total_filtered_results': result.get('total_filtered_results', 0),
                'avg_results_per_search': float(result.get('avg_results_per_search', 0) or 0),
                'unique_modalities': result.get('unique_modalities', 0),
                'first_search': result.get('first_search'),
                'last_search': result.get('last_search')
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar estatísticas: {e}")
            return {} 