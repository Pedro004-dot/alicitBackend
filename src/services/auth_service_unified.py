"""
Service unificado para operações de autenticação
Agrega todos os serviços específicos mantendo compatibilidade com código existente
"""
import logging
from typing import Dict, List, Optional, Any

from services.auth import (
    RegisterService,
    LoginService, 
    LogoutService,
    PasswordService,
    ProfileService
)

logger = logging.getLogger(__name__)

class AuthService:
    """Service principal que agrega todos os serviços de autenticação"""
    
    def __init__(self):
        """Inicializar todos os serviços específicos"""
        from config.database import get_db_manager
        
        # Obter db_manager para services que precisam (clean architecture)
        db_manager = get_db_manager()
        
        self.register_service = RegisterService()
        self.login_service = LoginService(db_manager)
        self.logout_service = LogoutService()
        self.password_service = PasswordService()
        self.profile_service = ProfileService()
    
    # =========================
    # MÉTODOS DE REGISTRO
    # =========================
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Registrar novo usuário no sistema"""
        return self.register_service.register_user(user_data)
    
    def verify_email(self, token: str) -> Dict[str, Any]:
        """Verificar email do usuário com token"""
        return self.register_service.verify_email(token)
    
    def resend_verification_email(self, email: str) -> None:
        """Reenviar email de verificação"""
        return self.register_service.resend_verification_email(email)
    
    # =========================
    # MÉTODOS DE LOGIN
    # =========================
    
    def login_user(self, email: str, password: str, device_info: Dict, ip_address: str) -> Dict[str, Any]:
        """Fazer login do usuário"""
        return self.login_service.login_user(email, password, device_info, ip_address)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar se token JWT é válido e não revogado"""
        return self.login_service.verify_token(token)
    
    def refresh_token(self, user_id: str, old_jti: str, device_info: Dict, ip_address: str) -> Dict[str, Any]:
        """Renovar token JWT invalidando o anterior"""
        return self.login_service.refresh_token(user_id, old_jti, device_info, ip_address)
    
    # =========================
    # MÉTODOS DE LOGOUT
    # =========================
    
    def logout_session(self, jti: str) -> None:
        """Fazer logout de uma sessão específica"""
        return self.logout_service.logout_session(jti)
    
    def logout_all_sessions(self, user_id: str) -> Dict[str, int]:
        """Fazer logout de todas as sessões do usuário"""
        return self.logout_service.logout_all_sessions(user_id)
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Listar sessões ativas do usuário"""
        return self.logout_service.get_user_sessions(user_id)
    
    def revoke_session(self, user_id: str, jti: str) -> bool:
        """Revogar sessão específica (diferente da atual)"""
        return self.logout_service.revoke_session(user_id, jti)
    
    def cleanup_expired_sessions(self) -> Dict[str, int]:
        """Limpar sessões expiradas"""
        return self.logout_service.cleanup_expired_sessions()
    
    # =========================
    # MÉTODOS DE SENHA
    # =========================
    
    def request_password_reset(self, email: str) -> None:
        """Solicitar reset de senha por email"""
        return self.password_service.request_password_reset(email)
    
    def reset_password(self, token: str, new_password: str) -> None:
        """Redefinir senha com token de reset"""
        return self.password_service.reset_password(token, new_password)
    
    def change_password(self, user_id: str, current_password: str, new_password: str, current_jti: str = None) -> None:
        """Alterar senha do usuário logado"""
        return self.password_service.change_password(user_id, current_password, new_password, current_jti)
    
    # =========================
    # MÉTODOS DE PERFIL
    # =========================
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Buscar perfil completo do usuário"""
        return self.profile_service.get_user_profile(user_id)
    
    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualizar dados do perfil do usuário"""
        return self.profile_service.update_user_profile(user_id, update_data)
    
    def get_user_subscription_details(self, user_id: str) -> Dict[str, Any]:
        """Buscar detalhes específicos da subscription do usuário"""
        return self.profile_service.get_user_subscription_details(user_id) 