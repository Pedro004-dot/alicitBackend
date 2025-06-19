"""
Controller para operações de perfil de usuários
Sistema multi-tenant com dados de subscription e empresas
"""
import logging
from .base_auth_controller import BaseAuthController
from services.auth import ProfileService
from middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

class ProfileController(BaseAuthController):
    """Controller para gerenciar perfil e dados do usuário"""
    
    def __init__(self):
        """Inicializar controller com service"""
        self.profile_service = ProfileService()
    
    @require_auth
    def get_profile(self):
        """GET /api/auth/me - Dados do usuário logado"""
        def _get_profile():
            current_user = self._get_current_user_safe()
            profile = self.profile_service.get_user_profile(current_user['user_id'])
            
            return self._success_response(data=profile)
        
        return self._handle_exceptions(_get_profile)
    
    @require_auth
    def update_profile(self):
        """PUT /api/auth/me - Atualizar dados do usuário"""
        def _update_profile():
            data = self._get_json_data()
            current_user = self._get_current_user_safe()
            
            updated_user = self.profile_service.update_user_profile(current_user['user_id'], data)
            
            return self._success_response(
                data={'user': updated_user},
                message='Perfil atualizado com sucesso!'
            )
        
        return self._handle_exceptions(_update_profile)
    
    @require_auth
    def get_subscription_details(self):
        """GET /api/auth/subscription - Detalhes da subscription do usuário"""
        def _get_subscription():
            current_user = self._get_current_user_safe()
            subscription = self.profile_service.get_user_subscription_details(current_user['user_id'])
            
            return self._success_response(data=subscription)
        
        return self._handle_exceptions(_get_subscription) 