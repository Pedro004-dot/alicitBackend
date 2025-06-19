"""
Service para operações de perfil de usuários
Sistema multi-tenant com dados de subscription e empresas
"""
import logging
from typing import Dict, Any
from .base_auth_service import BaseAuthService
from exceptions.api_exceptions import ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

class ProfileService(BaseAuthService):
    """Service para gerenciar perfil e dados do usuário"""
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Buscar perfil completo do usuário"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar dados do usuário e subscription
                    cur.execute("""
                        SELECT u.id, u.email, u.name, u.created_at, u.last_login_at,
                               us.status as subscription_status, sp.name as plan_name,
                               sp.max_empresas, sp.max_monthly_matches, sp.max_monthly_rag_queries,
                               us.trial_ends_at, us.current_period_end
                        FROM users u
                        LEFT JOIN user_subscriptions us ON u.id = us.user_id
                        LEFT JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
                        WHERE u.id = %s AND u.is_active = true
                    """, (user_id,))
                    
                    user = cur.fetchone()
                    if not user:
                        raise NotFoundError("Usuário não encontrado")
                    
                    # Buscar empresas do usuário se a tabela empresas tem user_id
                    empresas = []
                    try:
                        cur.execute("""
                            SELECT id, nome_fantasia, cnpj, is_primary, is_active, created_at
                            FROM empresas 
                            WHERE user_id = %s
                            ORDER BY is_primary DESC, created_at ASC
                        """, (user_id,))
                        
                        empresas = [
                            {
                                'id': row[0],
                                'nome_fantasia': row[1],
                                'cnpj': row[2],
                                'is_primary': row[3] if len(row) > 3 else False,
                                'is_active': row[4] if len(row) > 4 else True,
                                'created_at': row[5].isoformat() if len(row) > 5 and row[5] else None
                            }
                            for row in cur.fetchall()
                        ]
                    except Exception as e:
                        logger.warning(f"Erro ao buscar empresas: {e}")
                        # Continuar sem empresas se a coluna user_id não existir ainda
                    
                    # Buscar contadores de uso (se tabela user_usage_logs existir)
                    matches_count = 0
                    rag_queries_count = 0
                    try:
                        # Contar uso no mês atual
                        cur.execute("""
                            SELECT 
                                COUNT(CASE WHEN action_type = 'match' THEN 1 END) as matches,
                                COUNT(CASE WHEN action_type = 'rag_query' THEN 1 END) as rag_queries
                            FROM user_usage_logs 
                            WHERE user_id = %s 
                            AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
                        """, (user_id,))
                        
                        usage = cur.fetchone()
                        if usage:
                            matches_count = usage[0] or 0
                            rag_queries_count = usage[1] or 0
                    except Exception as e:
                        logger.warning(f"Erro ao buscar dados de uso: {e}")
                    
                    # Contadores básicos
                    empresas_count = len(empresas)
            
            return {
                'user': {
                    'id': user[0],
                    'email': user[1],
                    'name': user[2],
                    'created_at': user[3].isoformat() if user[3] else None,
                    'last_login_at': user[4].isoformat() if user[4] else None
                },
                'subscription': {
                    'status': user[5],
                    'plan_name': user[6],
                    'max_empresas': user[7],
                    'max_monthly_matches': user[8],
                    'max_monthly_rag_queries': user[9],
                    'trial_ends_at': user[10].isoformat() if user[10] else None,
                    'current_period_end': user[11].isoformat() if user[11] else None
                },
                'usage': {
                    'empresas_count': empresas_count,
                    'matches_this_month': matches_count,
                    'rag_queries_this_month': rag_queries_count
                },
                'companies': empresas
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar perfil do usuário: {e}")
            raise DatabaseError("Erro interno ao buscar perfil")
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualizar dados do perfil do usuário"""
        try:
            # Campos permitidos para atualização
            allowed_fields = ['name']
            update_fields = []
            update_values = []
            
            # Validar e preparar campos para atualização
            for field in allowed_fields:
                if field in update_data:
                    value = update_data[field]
                    
                    if field == 'name':
                        if not value or len(value.strip()) < 2:
                            raise ValidationError("Nome deve ter pelo menos 2 caracteres")
                        value = value.strip()
                    
                    update_fields.append(f"{field} = %s")
                    update_values.append(value)
            
            if not update_fields:
                raise ValidationError("Nenhum campo válido fornecido para atualização")
            
            # Atualizar no banco
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Verificar se usuário existe
                    user = self._get_user_by_id(user_id)
                    if not user:
                        raise NotFoundError("Usuário não encontrado")
                    
                    # Executar atualização
                    query = f"""
                        UPDATE users 
                        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """
                    update_values.append(user_id)
                    
                    cur.execute(query, update_values)
                    conn.commit()
                    
                    # Buscar dados atualizados
                    updated_user = self._get_user_by_id(user_id)
            
            return {
                'id': updated_user[0],
                'email': updated_user[1],
                'name': updated_user[2]
            }
            
        except (ValidationError, NotFoundError):
            raise
        except Exception as e:
            logger.error(f"Erro ao atualizar perfil: {e}")
            raise DatabaseError("Erro interno ao atualizar perfil")
    
    def get_user_subscription_details(self, user_id: str) -> Dict[str, Any]:
        """Buscar detalhes específicos da subscription do usuário"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT us.id, us.status, us.trial_ends_at, us.current_period_start,
                               us.current_period_end, us.canceled_at, us.created_at,
                               sp.id as plan_id, sp.name as plan_name, sp.price_monthly,
                               sp.max_empresas, sp.max_monthly_matches, sp.max_monthly_rag_queries,
                               sp.is_trial_plan
                        FROM user_subscriptions us
                        JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
                        WHERE us.user_id = %s
                        ORDER BY us.created_at DESC
                        LIMIT 1
                    """, (user_id,))
                    
                    subscription = cur.fetchone()
                    if not subscription:
                        raise NotFoundError("Subscription não encontrada")
            
            return {
                'id': subscription[0],
                'status': subscription[1],
                'trial_ends_at': subscription[2].isoformat() if subscription[2] else None,
                'current_period_start': subscription[3].isoformat() if subscription[3] else None,
                'current_period_end': subscription[4].isoformat() if subscription[4] else None,
                'canceled_at': subscription[5].isoformat() if subscription[5] else None,
                'created_at': subscription[6].isoformat() if subscription[6] else None,
                'plan': {
                    'id': subscription[7],
                    'name': subscription[8],
                    'price_monthly': float(subscription[9]) if subscription[9] else 0,
                    'max_empresas': subscription[10],
                    'max_monthly_matches': subscription[11],
                    'max_monthly_rag_queries': subscription[12],
                    'is_trial_plan': subscription[13]
                }
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes da subscription: {e}")
            raise DatabaseError("Erro interno ao buscar subscription") 