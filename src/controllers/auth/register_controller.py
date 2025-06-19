"""
Controller para operações de registro de usuários
Sistema multi-tenant com verificação de email
"""
import logging
from .base_auth_controller import BaseAuthController
from services.auth import RegisterService

logger = logging.getLogger(__name__)

class RegisterController(BaseAuthController):
    """Controller para gerenciar registro e verificação de usuários"""
    
    def __init__(self):
        """Inicializar controller com service"""
        self.register_service = RegisterService()
    
    def register(self):
        """POST /api/auth/register - Registro de novo usuário"""
        def _register():
            data = self._get_json_data(['email', 'password', 'name'])
            result = self.register_service.register_user(data)
            
            return self._success_response(
                data={
                    'user_id': result['user_id'],
                    'trial_ends_at': result['trial_ends_at']
                },
                message='Usuário registrado com sucesso! Verifique seu email para obter o código de verificação.',
                status_code=201
            )
        
        return self._handle_exceptions(_register)
    
    def verify_email(self):
        """POST /api/auth/verify-email - Verificar email com código"""
        def _verify_email():
            data = self._get_json_data(['code', 'email'])
            result = self.register_service.verify_email(data['code'], data['email'])
            
            return self._success_response(
                message='Email verificado com sucesso! Agora você pode fazer login.',
                data={'redirect_to': '/login'}
            )
        
        return self._handle_exceptions(_verify_email)
    
    def resend_verification(self):
        """POST /api/auth/resend-verification - Reenviar código de verificação"""
        def _resend_verification():
            data = self._get_json_data(['email'])
            self.register_service.resend_verification_code(data['email'])
            
            return self._success_response(
                message='Novo código de verificação enviado! Verifique sua caixa de entrada.'
            )
        
        return self._handle_exceptions(_resend_verification) 