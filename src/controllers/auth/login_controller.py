"""
Controller para operações de login (Clean Architecture)
Responsável apenas por requisições HTTP, delegando lógica para services
"""
import logging
from flask import request, jsonify
from datetime import datetime
from typing import Dict, Any, Tuple
from services.auth.login_service import LoginService
from validators.auth_validators import AuthValidationError
from exceptions.api_exceptions import ValidationError, AuthenticationError, DatabaseError
from .base_auth_controller import BaseAuthController

logger = logging.getLogger(__name__)

class LoginController(BaseAuthController):
    """Controller para endpoints de login"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.login_service = LoginService(db_manager)
    
    def login(self) -> Tuple[Dict[str, Any], int]:
        """POST /api/auth/login - Fazer login"""
        try:
            # 1. Extrair e validar dados da requisição
            data = self._get_json_data(['email', 'password'])
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            
            # 2. Extrair informações do dispositivo
            device_info = self._extract_device_info()
            ip_address = self._get_client_ip()
            
            # 3. Delegar para service
            result = self.login_service.login_user(
                email=email,
                password=password,
                device_info=device_info,
                ip_address=ip_address
            )
            
            # 4. Retornar resposta de sucesso
            return self._success_response(
                data=result,
                message="Login realizado com sucesso"
            )
            
        except AuthValidationError as e:
            return self._error_response('Dados inválidos', str(e), 400)
        except AuthenticationError as e:
            return self._error_response('Falha na autenticação', str(e), 401)
        except ValidationError as e:
            return self._error_response('Dados inválidos', str(e), 400)
        except DatabaseError as e:
            return self._error_response('Erro interno do servidor', str(e), 500)
        except Exception as e:
            logger.error(f"Erro inesperado no login: {e}")
            return self._error_response('Erro interno do servidor', "Erro inesperado", 500)
    
    def verify_token(self) -> Tuple[Dict[str, Any], int]:
        """POST /api/auth/verify-token - Verificar validade do token"""
        try:
            # 1. Extrair token
            data = self._get_json_data(['token'])
            token = data.get('token', '').strip()
            
            # 2. Verificar token
            payload = self.login_service.verify_token(token)
            
            if not payload:
                return self._error_response("Token inválido", "Token inválido ou expirado", 401)
            
            # 3. Retornar dados do token
            return self._success_response(
                data={
                    'user_id': payload.get('user_id'),
                    'email': payload.get('email'),
                    'expires_at': payload.get('exp'),
                    'issued_at': payload.get('iat')
                },
                message="Token válido"
            )
            
        except AuthValidationError as e:
            return self._error_response(str(e), 400)
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            return self._error_response("Erro interno do servidor", 500)
    
    def refresh_token(self) -> Tuple[Dict[str, Any], int]:
        """POST /api/auth/refresh-token - Renovar token"""
        try:
            # 1. Extrair token do header Authorization
            old_token = self._extract_auth_token()
            if not old_token:
                return self._error_response("Token não fornecido", "Token de autenticação necessário", 401)
            
            # 2. Verificar token atual para obter user_id
            payload = self.login_service.verify_token(old_token)
            if not payload:
                return self._error_response("Token inválido", "Token inválido ou expirado", 401)
            
            # 3. Extrair informações do dispositivo
            device_info = self._extract_device_info()
            ip_address = self._get_client_ip()
            
            # 4. Renovar token
            result = self.login_service.refresh_token(
                user_id=payload['user_id'],
                old_token=old_token,
                device_info=device_info,
                ip_address=ip_address
            )
            
            return self._success_response(
                data=result,
                message="Token renovado com sucesso"
            )
            
        except AuthenticationError as e:
            return self._error_response('Falha na autenticação', str(e), 401)
        except DatabaseError as e:
            return self._error_response('Erro interno do servidor', str(e), 500)
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            return self._error_response('Erro interno do servidor', "Erro inesperado", 500)
    
    def get_sessions(self) -> Tuple[Dict[str, Any], int]:
        """GET /api/auth/sessions - Listar sessões ativas"""
        def _get_sessions():
            # 1. Extrair user_id do token (assumindo middleware de autenticação)
            user_id = self._get_current_user_id()
            if not user_id:
                raise ValidationError("Usuário não autenticado")
            
            # 2. Buscar sessões
            sessions = self.login_service.get_active_sessions(user_id)
            
            return self._success_response(
                data={'sessions': sessions},
                message="Sessões listadas com sucesso"
            )
        
        return self._handle_exceptions(_get_sessions)
    
    def logout(self) -> Tuple[Dict[str, Any], int]:
        """POST /api/auth/logout - Logout da sessão atual"""
        def _logout():
            # 1. Extrair token
            token = self._extract_auth_token()
            if not token:
                raise ValidationError("Token não fornecido")
            
            # 2. Fazer logout
            success = self.login_service.logout_session(token)
            
            if success:
                return self._success_response(message="Logout realizado com sucesso")
            else:
                raise DatabaseError("Erro ao fazer logout")
        
        return self._handle_exceptions(_logout)
    
    def logout_all(self) -> Tuple[Dict[str, Any], int]:
        """POST /api/auth/logout-all - Logout de todas as sessões"""
        def _logout_all():
            # 1. Extrair user_id
            user_id = self._get_current_user_id()
            if not user_id:
                raise ValidationError("Usuário não autenticado")
            
            # 2. Fazer logout de todas as sessões
            sessions_count = self.login_service.logout_all_sessions(user_id)
            
            return self._success_response(
                data={'sessions_logged_out': sessions_count},
                message=f"Logout realizado em {sessions_count} sessões"
            )
        
        return self._handle_exceptions(_logout_all)
    
    # Métodos auxiliares específicos do controller
    
    def _extract_device_info(self) -> str:
        """Extrair informações do dispositivo da requisição"""
        user_agent = request.headers.get('User-Agent', 'Unknown')
        device_type = 'web'  # Pode ser expandido para detectar mobile/app
        
        # Informações básicas do dispositivo
        device_info = f"{device_type}|{user_agent[:100]}"
        
        return device_info
    
    def _get_client_ip(self) -> str:
        """Obter IP do cliente considerando proxies"""
        # Verificar headers de proxy
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.environ.get('REMOTE_ADDR', 'unknown')
    
    def _extract_auth_token(self) -> str:
        """Extrair token de autenticação do header Authorization"""
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer '
        
        return ''
    
    def _get_current_user_id(self) -> str:
        """Obter ID do usuário atual (assumindo middleware de auth)"""
        # Este método assumiria que existe um middleware que adiciona
        # user_id ao request após validar o token
        return getattr(request, 'user_id', None) 