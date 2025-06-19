"""
Repository para operações com subscriptions
Responsável por acesso a dados das tabelas subscription_plans e user_subscriptions
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class SubscriptionRepository(BaseRepository):
    """Repository para gerenciar subscriptions"""
    
    @property
    def table_name(self) -> str:
        return "user_subscriptions"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def get_all_plans(self) -> List[Dict[str, Any]]:
        """Buscar todos os planos disponíveis"""
        query = "SELECT * FROM subscription_plans WHERE is_active = true ORDER BY price ASC"
        return self.execute_custom_query(query)
    
    def get_plan_by_name(self, plan_name: str) -> Optional[Dict[str, Any]]:
        """Buscar plano por nome"""
        query = "SELECT * FROM subscription_plans WHERE name = %s AND is_active = true"
        results = self.execute_custom_query(query, (plan_name,))
        return results[0] if results else None
    
    def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar subscription atual do usuário"""
        query = """
            SELECT us.*, sp.name as plan_name, sp.max_empresas, 
                   sp.max_monthly_matches, sp.max_monthly_rag_queries, sp.price
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
            WHERE us.user_id = %s
            ORDER BY us.created_at DESC
            LIMIT 1
        """
        results = self.execute_custom_query(query, (user_id,))
        return results[0] if results else None
    
    def create_user_subscription(self, user_id: str, plan_id: str, 
                               status: str = 'trial', trial_days: int = 7) -> Dict[str, Any]:
        """Criar nova subscription para usuário"""
        trial_end = datetime.utcnow() + timedelta(days=trial_days)
        
        subscription_data = {
            'user_id': user_id,
            'subscription_plan_id': plan_id,
            'status': status,
            'trial_ends_at': trial_end,
            'current_period_start': datetime.utcnow(),
            'current_period_end': trial_end,
            'created_at': datetime.utcnow()
        }
        return self.create(subscription_data)
    
    def update_subscription_status(self, user_id: str, status: str) -> bool:
        """Atualizar status da subscription"""
        subscription = self.get_user_subscription(user_id)
        if subscription:
            data = {'status': status}
            result = self.update(subscription['id'], data)
            return result is not None
        return False
    
    def extend_trial(self, user_id: str, days: int) -> bool:
        """Estender período de trial"""
        subscription = self.get_user_subscription(user_id)
        if subscription and subscription['status'] == 'trial':
            new_trial_end = subscription['trial_ends_at'] + timedelta(days=days)
            data = {
                'trial_ends_at': new_trial_end,
                'current_period_end': new_trial_end
            }
            result = self.update(subscription['id'], data)
            return result is not None
        return False
    
    def activate_paid_subscription(self, user_id: str, plan_id: str, 
                                 current_period_end: datetime) -> bool:
        """Ativar subscription paga"""
        subscription = self.get_user_subscription(user_id)
        if subscription:
            data = {
                'subscription_plan_id': plan_id,
                'status': 'active',
                'current_period_start': datetime.utcnow(),
                'current_period_end': current_period_end
            }
            result = self.update(subscription['id'], data)
            return result is not None
        return False
    
    def cancel_subscription(self, user_id: str) -> bool:
        """Cancelar subscription (marca para cancelamento no final do período)"""
        subscription = self.get_user_subscription(user_id)
        if subscription:
            data = {
                'status': 'cancelled',
                'cancelled_at': datetime.utcnow()
            }
            result = self.update(subscription['id'], data)
            return result is not None
        return False
    
    def get_expired_trials(self) -> List[Dict[str, Any]]:
        """Buscar trials expirados"""
        query = """
            SELECT us.user_id, us.id as subscription_id
            FROM user_subscriptions us
            WHERE us.status = 'trial' AND us.trial_ends_at < %s
        """
        return self.execute_custom_query(query, (datetime.utcnow(),))
    
    def get_expired_subscriptions(self) -> List[Dict[str, Any]]:
        """Buscar subscriptions expiradas"""
        query = """
            SELECT us.user_id, us.id as subscription_id
            FROM user_subscriptions us
            WHERE us.status = 'active' AND us.current_period_end < %s
        """
        return self.execute_custom_query(query, (datetime.utcnow(),))
    
    def is_subscription_active(self, user_id: str) -> bool:
        """Verificar se usuário tem subscription ativa"""
        subscription = self.get_user_subscription(user_id)
        if not subscription:
            return False
        
        now = datetime.utcnow()
        
        # Trial ativo
        if subscription['status'] == 'trial':
            return subscription['trial_ends_at'] > now
        
        # Subscription paga ativa
        if subscription['status'] == 'active':
            return subscription['current_period_end'] > now
        
        return False
    
    def get_subscription_limits(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar limites da subscription do usuário"""
        subscription = self.get_user_subscription(user_id)
        if subscription:
            return {
                'max_empresas': subscription['max_empresas'],
                'max_monthly_matches': subscription['max_monthly_matches'],
                'max_monthly_rag_queries': subscription['max_monthly_rag_queries'],
                'plan_name': subscription['plan_name']
            }
        return None 