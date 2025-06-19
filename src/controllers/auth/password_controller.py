"""
Controller para operações de recuperação e alteração de senhas
Sistema com tokens seguros e validações
"""
import logging
from .base_auth_controller import BaseAuthController
from services.auth import PasswordService
from middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

class PasswordController(BaseAuthController):
    """Controller para gerenciar recuperação e alteração de senhas"""
    
    def __init__(self):
        """Inicializar controller com service"""
        self.password_service = PasswordService()
    
    def forgot_password(self):
        """POST /api/auth/forgot-password - Solicitar reset de senha"""
        def _forgot_password():
            data = self._get_json_data(['email'])
            self.password_service.request_password_reset(data['email'])
            
            # Sempre retornar sucesso por segurança (não expor se email existe)
            return self._success_response(
                message='Se o email estiver cadastrado, você receberá as instruções para redefinir sua senha.'
            )
        
        return self._handle_exceptions(_forgot_password)
    
    def verify_password_code(self):
        """POST /api/auth/verify-password-code - Verifica o código de reset"""
        def _verify_code():
            data = self._get_json_data(['email', 'code'])
            self.password_service.verify_password_reset_code(data['email'], data['code'])
            
            # Se não houver exceção, o código é válido
            return self._success_response(
                message='Código verificado com sucesso!',
                data={'verified': True}
            )

        return self._handle_exceptions(_verify_code)
    
    def reset_password(self):
        """POST /api/auth/reset-password - Redefinir senha com código"""
        def _reset_password():
            data = self._get_json_data(['email', 'code', 'new_password'])
            self.password_service.reset_password(
                data['email'], data['code'], data['new_password']
            )
            
            return self._success_response(
                message='Senha redefinida com sucesso! Faça login com sua nova senha.',
                data={'redirect_to': '/login'}
            )
        
        return self._handle_exceptions(_reset_password)
    
    @require_auth
    def change_password(self):
        """POST /api/auth/change-password - Alterar senha logado"""
        def _change_password():
            data = self._get_json_data(['current_password', 'new_password'])
            current_user = self._get_current_user_safe()
            
            self.password_service.change_password(
                user_id=current_user['user_id'],
                current_password=data['current_password'],
                new_password=data['new_password'],
                current_jti=current_user.get('jti')
            )
            
            return self._success_response(
                message='Senha alterada com sucesso! Outros dispositivos foram desconectados.'
            )
        
        return self._handle_exceptions(_change_password) 