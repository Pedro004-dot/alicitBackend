"""
Repository para operações com usuários
Responsável apenas por acesso a dados da tabela users
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class UserRepository(BaseRepository):
    """Repository para gerenciar dados de usuários"""
    
    @property
    def table_name(self) -> str:
        return "users"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Buscar usuário por email"""
        return self.find_by_filters({'email': email.lower()}, limit=1)
    
    def find_by_email_with_subscription(self, email: str) -> Optional[Dict[str, Any]]:
        """Buscar usuário por email com dados de subscription"""
        query = """
            SELECT u.id, u.email, u.name, u.password_hash, u.email_verified, 
                   u.is_active, u.login_attempts, u.locked_until,
                   us.status as subscription_status, sp.name as plan_name,
                   sp.max_empresas, sp.max_monthly_matches, sp.max_monthly_rag_queries,
                   us.trial_ends_at, us.current_period_end
            FROM users u
            LEFT JOIN user_subscriptions us ON u.id = us.user_id
            LEFT JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
            WHERE LOWER(u.email) = LOWER(%s)
        """
        results = self.execute_custom_query(query, (email,))
        return results[0] if results else None
    
    def find_by_verification_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Buscar usuário por token de verificação"""
        results = self.find_by_filters({
            'email_verification_token': token,
            'is_active': True
        }, limit=1)
        return results[0] if results else None
    
    def find_by_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Buscar usuário por token de reset de senha"""
        results = self.find_by_filters({
            'password_reset_token': token,
            'is_active': True
        }, limit=1)
        return results[0] if results else None
    
    def update_login_attempts(self, user_id: str, attempts: int, locked_until: Optional[datetime] = None) -> bool:
        """Atualizar tentativas de login"""
        data = {
            'login_attempts': attempts,
            'locked_until': locked_until
        }
        result = self.update(user_id, data)
        return result is not None
    
    def reset_login_attempts(self, user_id: str) -> bool:
        """Reset tentativas de login e atualizar último login"""
        data = {
            'login_attempts': 0,
            'locked_until': None,
            'last_login_at': datetime.utcnow()
        }
        result = self.update(user_id, data)
        return result is not None
    
    def verify_email(self, user_id: str) -> bool:
        """Marcar email como verificado"""
        data = {
            'email_verified': True,
            'email_verification_token': None,
            'email_verification_expires_at': None,
            'email_verified_at': datetime.utcnow()
        }
        result = self.update(user_id, data)
        return result is not None
    
    def update_verification_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        """Atualizar token de verificação"""
        data = {
            'email_verification_token': token,
            'email_verification_expires_at': expires_at
        }
        result = self.update(user_id, data)
        return result is not None
    
    def update_reset_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        """Atualizar token de reset de senha"""
        data = {
            'password_reset_token': token,
            'password_reset_expires_at': expires_at
        }
        result = self.update(user_id, data)
        return result is not None
    
    def update_password(self, user_id: str, password_hash: str) -> bool:
        """Atualizar senha do usuário"""
        data = {
            'password_hash': password_hash,
            'password_changed_at': datetime.utcnow()
        }
        result = self.update(user_id, data)
        return result is not None
    
    def clear_reset_token(self, user_id: str) -> bool:
        """Limpar token de reset após uso"""
        data = {
            'password_reset_token': None,
            'password_reset_expires_at': None
        }
        result = self.update(user_id, data)
        return result is not None
    
    def get_profile_with_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Buscar perfil completo com subscription"""
        query = """
            SELECT u.id, u.email, u.name, u.created_at, u.last_login_at,
                   us.status as subscription_status, sp.name as plan_name,
                   sp.max_empresas, sp.max_monthly_matches, sp.max_monthly_rag_queries,
                   us.trial_ends_at, us.current_period_end
            FROM users u
            LEFT JOIN user_subscriptions us ON u.id = us.user_id
            LEFT JOIN subscription_plans sp ON us.subscription_plan_id = sp.id
            WHERE u.id = %s AND u.is_active = true
        """
        results = self.execute_custom_query(query, (user_id,))
        return results[0] if results else None 