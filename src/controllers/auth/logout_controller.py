"""
Controller para operações de logout e gestão de sessões
Sistema multi-tenant com controle de sessões por dispositivo
"""
import logging
from flask import request
from .base_auth_controller import BaseAuthController
from services.auth import LogoutService
from middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)

class LogoutController(BaseAuthController):
    """Controller para gerenciar logout e sessões de usuários"""
    
    def __init__(self):
        """Inicializar controller com service"""
        self.logout_service = LogoutService()
    
    @require_auth
    def logout(self):
        """POST /api/auth/logout - Logout (invalida token atual)"""
        def _logout():
            data = request.get_json() or {}
            current_user = self._get_current_user_safe()
            
            logout_all = data.get('logout_all_devices', False)
            
            if logout_all:
                result = self.logout_service.logout_all_sessions(current_user['user_id'])
                message = f'Logout realizado com sucesso! {result["sessions_revoked"]} dispositivos desconectados.'
            else:
                # Pegar JWT ID do token atual
                jti = current_user.get('jti')
                if not jti:
                    return self._error_response('Token inválido', 'Token não contém identificador de sessão', 400)
                
                self.logout_service.logout_session(jti)
                message = 'Logout realizado com sucesso!'
            
            return self._success_response(message=message)
        
        return self._handle_exceptions(_logout)
    
    @require_auth
    def logout_all(self):
        """POST /api/auth/logout-all - Logout de todos dispositivos"""
        def _logout_all():
            current_user = self._get_current_user_safe()
            result = self.logout_service.logout_all_sessions(current_user['user_id'])
            
            return self._success_response(
                message=f'Logout realizado em todos os dispositivos! {result["sessions_revoked"]} sessões encerradas.',
                data={'devices_count': result['sessions_revoked']}
            )
        
        return self._handle_exceptions(_logout_all)
    
    @require_auth
    def get_user_sessions(self):
        """GET /api/auth/sessions - Listar sessões ativas do usuário"""
        def _get_sessions():
            current_user = self._get_current_user_safe()
            sessions = self.logout_service.get_user_sessions(current_user['user_id'])
            current_jti = current_user.get('jti')
            
            return self._success_response(
                data={
                    'sessions': sessions,
                    'current_session': current_jti,
                    'total_sessions': len(sessions)
                }
            )
        
        return self._handle_exceptions(_get_sessions)
    
    @require_auth
    def revoke_session(self, session_id):
        """DELETE /api/auth/sessions/<session_id> - Revogar sessão específica"""
        def _revoke_session():
            current_user = self._get_current_user_safe()
            current_jti = current_user.get('jti')
            
            # Não permitir revogar a própria sessão
            if session_id == current_jti:
                return self._error_response(
                    'Operação inválida',
                    'Não é possível revogar a sessão atual. Use logout.',
                    400
                )
            
            revoked = self.logout_service.revoke_session(current_user['user_id'], session_id)
            
            if not revoked:
                return self._error_response(
                    'Sessão não encontrada',
                    'Sessão não encontrada ou já revogada',
                    404
                )
            
            return self._success_response(message='Sessão revogada com sucesso!')
        
        return self._handle_exceptions(_revoke_session) 