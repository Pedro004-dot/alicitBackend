"""
Controller unificado para operações de autenticação
Agrega todos os controllers específicos mantendo compatibilidade com código existente
"""
import logging
from config.database import get_db_manager
from controllers.auth import (
    RegisterController,
    LoginController,
    LogoutController,
    PasswordController,
    ProfileController
)

logger = logging.getLogger(__name__)

class AuthController:
    """Controller principal que agrega todos os controllers de autenticação"""
    
    def __init__(self):
        """Inicializar todos os controllers específicos"""
        # Obter db_manager para controllers que usam clean architecture
        db_manager = get_db_manager()
        
        # Instanciar controllers (alguns precisam de db_manager, outros não)
        self.register_controller = RegisterController()
        self.login_controller = LoginController(db_manager)  # Clean Architecture
        self.logout_controller = LogoutController()
        self.password_controller = PasswordController()
        self.profile_controller = ProfileController()
    
    # =========================
    # MÉTODOS DE REGISTRO
    # =========================
    
    def register(self):
        """POST /api/auth/register - Registro de novo usuário"""
        return self.register_controller.register()
    
    def verify_email(self):
        """POST /api/auth/verify-email - Verificar email com token"""
        return self.register_controller.verify_email()
    
    def resend_verification(self):
        """POST /api/auth/resend-verification - Reenviar email de verificação"""
        return self.register_controller.resend_verification()
    
    # =========================
    # MÉTODOS DE LOGIN
    # =========================
    
    def login(self):
        """POST /api/auth/login - Login com JWT"""
        return self.login_controller.login()
    
    def verify_token(self):
        """POST /api/auth/verify-token - Verificar validade do token"""
        return self.login_controller.verify_token()
    
    def refresh_token(self):
        """POST /api/auth/refresh-token - Renovar token JWT"""
        return self.login_controller.refresh_token()
    
    # =========================
    # MÉTODOS DE LOGOUT
    # =========================
    
    def logout(self):
        """POST /api/auth/logout - Logout (invalida token atual)"""
        return self.logout_controller.logout()
    
    def logout_all(self):
        """POST /api/auth/logout-all - Logout de todos dispositivos"""
        return self.logout_controller.logout_all()
    
    def get_user_sessions(self):
        """GET /api/auth/sessions - Listar sessões ativas do usuário"""
        return self.logout_controller.get_user_sessions()
    
    def revoke_session(self, session_id):
        """DELETE /api/auth/sessions/<session_id> - Revogar sessão específica"""
        return self.logout_controller.revoke_session(session_id)
    
    # =========================
    # MÉTODOS DE SENHA
    # =========================
    
    def forgot_password(self):
        """POST /api/auth/forgot-password - Solicitar reset de senha"""
        return self.password_controller.forgot_password()
    
    def verify_password_code(self):
        """POST /api/auth/verify-password-code - Verifica o código de reset"""
        return self.password_controller.verify_password_code()
    
    def reset_password(self):
        """POST /api/auth/reset-password - Redefinir senha com token"""
        return self.password_controller.reset_password()
    
    def change_password(self):
        """POST /api/auth/change-password - Alterar senha logado"""
        return self.password_controller.change_password()
    
    # =========================
    # MÉTODOS DE PERFIL
    # =========================
    
    def get_profile(self):
        """GET /api/auth/me - Dados do usuário logado"""
        return self.profile_controller.get_profile()
    
    def update_profile(self):
        """PUT /api/auth/me - Atualizar dados do usuário"""
        return self.profile_controller.update_profile()
    
    def get_subscription_details(self):
        """GET /api/auth/subscription - Detalhes da subscription do usuário"""
        return self.profile_controller.get_subscription_details() 