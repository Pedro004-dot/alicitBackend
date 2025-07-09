"""
Serviço de Persistência Escalável
Implementa Strategy Pattern para suportar múltiplos providers sem modificação
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import asdict
from datetime import datetime

from interfaces.data_mapper import data_mapper_registry, BaseDataMapper, DatabaseOpportunity
from interfaces.procurement_data_source import OpportunityData
from config.database import get_db_manager


class PersistenceService:
    """
    Serviço de persistência escalável usando Strategy Pattern
    
    Princípios SOLID aplicados:
    - Open/Closed: Aberto para extensão (novos providers), fechado para modificação
    - Single Responsibility: Apenas gerencia persistência de oportunidades
    - Dependency Inversion: Depende de abstrações (DataMapper), não implementações
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_manager = get_db_manager()
        
    def save_opportunity(self, opportunity: OpportunityData) -> bool:
        """
        Salva uma oportunidade no banco usando o mapper apropriado
        
        Args:
            opportunity: Dados da oportunidade a serem salvos
            
        Returns:
            bool: True se salvou com sucesso, False caso contrário
        """
        try:
            # Validar provider_name
            if not opportunity.provider_name:
                self.logger.error("Opportunity missing provider_name")
                return False
            
            # Obter mapper para o provider
            mapper = data_mapper_registry.get_mapper(opportunity.provider_name)
            if not mapper:
                self.logger.error(f"No mapper found for provider: {opportunity.provider_name}")
                return False
            
            # Validar dados usando mapper específico
            if not mapper.validate_data(opportunity):
                self.logger.error(f"Data validation failed for {opportunity.provider_name} opportunity {opportunity.external_id}")
                return False
            
            # Converter para formato do banco
            db_opportunity = mapper.opportunity_to_database(opportunity)
            
            # Verificar se já existe (upsert)
            existing = self._get_existing_opportunity(
                db_opportunity.provider_name, 
                db_opportunity.external_id
            )
            
            if existing:
                result = self._update_opportunity(db_opportunity, existing['id'])
                action = "updated"
            else:
                result = self._insert_opportunity(db_opportunity)
                action = "inserted"
            
            if result:
                self.logger.info(f"Successfully {action} {opportunity.provider_name} opportunity {opportunity.external_id}")
                return True
            else:
                self.logger.error(f"Failed to {action.replace('ed', '')} {opportunity.provider_name} opportunity {opportunity.external_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error saving opportunity: {e}")
            return False
    
    def save_opportunities_batch(self, opportunities: List[OpportunityData]) -> Dict[str, int]:
        """
        Salva múltiplas oportunidades em lote para melhor performance
        
        Args:
            opportunities: Lista de oportunidades
            
        Returns:
            Dict com estatísticas: {'success': int, 'failed': int, 'skipped': int}
        """
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        
        try:
            # Agrupar por provider para otimização
            by_provider = {}
            for opp in opportunities:
                if opp.provider_name:
                    if opp.provider_name not in by_provider:
                        by_provider[opp.provider_name] = []
                    by_provider[opp.provider_name].append(opp)
                else:
                    stats['skipped'] += 1
            
            # Processar cada provider
            for provider_name, provider_opportunities in by_provider.items():
                mapper = data_mapper_registry.get_mapper(provider_name)
                if not mapper:
                    self.logger.error(f"No mapper for provider {provider_name}, skipping {len(provider_opportunities)} opportunities")
                    stats['skipped'] += len(provider_opportunities)
                    continue
                
                # Processar oportunidades do provider
                for opportunity in provider_opportunities:
                    if self.save_opportunity(opportunity):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
            
            self.logger.info(f"Batch save completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error in batch save: {e}")
            return stats
    
    def get_opportunity(self, provider_name: str, external_id: str) -> Optional[OpportunityData]:
        """
        Recupera uma oportunidade do banco e converte para OpportunityData
        
        Args:
            provider_name: Nome do provider
            external_id: ID externo da oportunidade
            
        Returns:
            OpportunityData ou None se não encontrado
        """
        try:
            # Obter mapper
            mapper = data_mapper_registry.get_mapper(provider_name)
            if not mapper:
                self.logger.error(f"No mapper found for provider: {provider_name}")
                return None
            
            # Buscar no banco
            db_data = self._get_existing_opportunity(provider_name, external_id)
            if not db_data:
                return None
            
            # Converter para OpportunityData
            opportunity = mapper.database_to_opportunity(db_data)
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Error retrieving opportunity {provider_name}:{external_id}: {e}")
            return None
    
    def search_opportunities(
        self, 
        provider_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[OpportunityData]:
        """
        Busca oportunidades no banco com filtros
        
        Args:
            provider_name: Filtrar por provider (opcional)
            filters: Filtros adicionais
            limit: Limite de resultados
            offset: Offset para paginação
            
        Returns:
            Lista de OpportunityData
        """
        try:
            opportunities = []
            
            # Buscar dados no banco
            db_results = self._search_in_database(provider_name, filters, limit, offset)
            
            # Converter cada resultado usando o mapper apropriado
            for db_data in db_results:
                result_provider = db_data.get('provider_name')
                if not result_provider:
                    continue
                
                mapper = data_mapper_registry.get_mapper(result_provider)
                if not mapper:
                    self.logger.warning(f"No mapper for provider {result_provider}, skipping opportunity")
                    continue
                
                try:
                    opportunity = mapper.database_to_opportunity(db_data)
                    opportunities.append(opportunity)
                except Exception as e:
                    self.logger.error(f"Error converting opportunity {db_data.get('external_id')}: {e}")
                    continue
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Error searching opportunities: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de oportunidades por provider
        
        Returns:
            Dict com estatísticas
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Contar por provider
                    cursor.execute("""
                        SELECT 
                            provider_name,
                            COUNT(*) as total,
                            COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                            COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed,
                            AVG(estimated_value) as avg_value,
                            MAX(created_at) as last_updated
                        FROM licitacoes 
                        GROUP BY provider_name
                        ORDER BY total DESC
                    """)
                    
                    results = cursor.fetchall()
                    
                    stats = {
                        'total_opportunities': sum(row[1] for row in results),
                        'providers': [],
                        'supported_providers': data_mapper_registry.list_providers()
                    }
                    
                    for row in results:
                        provider_stats = {
                            'name': row[0],
                            'total': row[1],
                            'active': row[2],
                            'closed': row[3],
                            'avg_value': float(row[4]) if row[4] else 0,
                            'last_updated': row[5].isoformat() if row[5] else None,
                            'mapper_available': data_mapper_registry.is_provider_supported(row[0])
                        }
                        stats['providers'].append(provider_stats)
                    
                    return stats
                    
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {'error': str(e)}
    
    def _get_existing_opportunity(self, provider_name: str, external_id: str) -> Optional[Dict[str, Any]]:
        """Busca oportunidade existente no banco"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM licitacoes 
                        WHERE provider_name = %s AND external_id = %s
                        LIMIT 1
                    """, (provider_name, external_id))
                    
                    result = cursor.fetchone()
                    if result:
                        columns = [desc[0] for desc in cursor.description]
                        return dict(zip(columns, result))
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error checking existing opportunity: {e}")
            return None
    
    def _insert_opportunity(self, db_opportunity: DatabaseOpportunity) -> bool:
        """Insere nova oportunidade no banco"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Converter dataclass para dict
                    data = asdict(db_opportunity)
                    
                    # Preparar campos e valores
                    fields = list(data.keys())
                    values = [data[field] for field in fields]
                    placeholders = ', '.join(['%s'] * len(fields))
                    
                    query = f"""
                        INSERT INTO licitacoes ({', '.join(fields)})
                        VALUES ({placeholders})
                    """
                    
                    cursor.execute(query, values)
                    conn.commit()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error inserting opportunity: {e}")
            return False
    
    def _update_opportunity(self, db_opportunity: DatabaseOpportunity, existing_id: int) -> bool:
        """Atualiza oportunidade existente no banco"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Converter dataclass para dict
                    data = asdict(db_opportunity)
                    
                    # Atualizar updated_at
                    data['updated_at'] = datetime.now().isoformat()
                    
                    # Preparar campos para update (excluir created_at)
                    data.pop('created_at', None)
                    
                    fields = list(data.keys())
                    values = [data[field] for field in fields]
                    set_clause = ', '.join([f"{field} = %s" for field in fields])
                    
                    query = f"""
                        UPDATE licitacoes 
                        SET {set_clause}
                        WHERE id = %s
                    """
                    
                    cursor.execute(query, values + [existing_id])
                    conn.commit()
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error updating opportunity: {e}")
            return False
    
    def _search_in_database(
        self, 
        provider_name: Optional[str],
        filters: Optional[Dict[str, Any]],
        limit: int,
        offset: int
    ) -> List[Dict[str, Any]]:
        """Busca oportunidades no banco com filtros"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Base query
                    query = "SELECT * FROM licitacoes WHERE 1=1"
                    params = []
                    
                    # Filtro por provider
                    if provider_name:
                        query += " AND provider_name = %s"
                        params.append(provider_name)
                    
                    # Filtros adicionais
                    if filters:
                        for key, value in filters.items():
                            if key in ['status', 'region_code', 'category']:
                                query += f" AND {key} = %s"
                                params.append(value)
                    
                    # Ordenação e paginação
                    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                    params.extend([limit, offset])
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    # Converter para dicts
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in results]
                    
        except Exception as e:
            self.logger.error(f"Error searching in database: {e}")
            return []


# Instância global singleton
_persistence_service = None

def get_persistence_service() -> PersistenceService:
    """
    Obtém instância singleton do PersistenceService
    Garante que os mappers sejam inicializados automaticamente
    
    Returns:
        PersistenceService: Instância do serviço
    """
    global _persistence_service
    if _persistence_service is None:
        # 🏗️ GARANTIR QUE MAPPERS SEJAM INICIALIZADOS
        try:
            import adapters.mappers
            logging.getLogger(__name__).info("✅ DataMappers inicializados automaticamente via PersistenceService")
        except Exception as e:
            logging.getLogger(__name__).warning(f"⚠️ Erro na inicialização automática de mappers: {e}")
        
        _persistence_service = PersistenceService()
    return _persistence_service 