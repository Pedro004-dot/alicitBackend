"""
Service para operações de login e autenticação (Clean Architecture)
Responsável apenas pela lógica de negócio, delegando validação e acesso a dados
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import jwt
from repositories.auth import UserRepository, UserSessionRepository, SubscriptionRepository
from validators.auth_validators import AuthValidator, AuthValidationError
from .base_auth_service import BaseAuthService
from exceptions.api_exceptions import ValidationError, DatabaseError, AuthenticationError

logger = logging.getLogger(__name__)

class LoginService:
    """Service para gerenciar login e verificação de tokens"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.user_repository = UserRepository(db_manager)
        self.session_repository = UserSessionRepository(db_manager)
        self.subscription_repository = SubscriptionRepository(db_manager)
        self.validator = AuthValidator()
        self.base_service = BaseAuthService()
    
    def login_user(self, email: str, password: str, device_info: str, ip_address: str) -> Dict[str, Any]:
        """Fazer login do usuário"""
        try:
            # 1. Validar dados de entrada
            self._validate_login_data(email, password)
            
            # 2. Buscar usuário com dados de subscription
            user = self.user_repository.find_by_email_with_subscription(email.lower())
            if not user:
                raise AuthenticationError("Email ou senha inválidos")
            
            # 3. Validar regras de segurança
            self._validate_login_security(user)
            
            # 4. Verificar senha
            if not self.base_service._verify_password(password, user['password_hash']):
                self._handle_failed_login(user['id'], user.get('login_attempts', 0))
                raise AuthenticationError("Email ou senha inválidos")
            
            # 5. Reset tentativas e criar sessão
            self.user_repository.reset_login_attempts(user['id'])
            session_data = self._create_user_session(user, device_info, ip_address)
            
            # 6. Retornar dados estruturados
            return self._build_login_response(user, session_data)
            
        except (AuthenticationError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Erro ao fazer login: {e}")
            raise DatabaseError("Erro interno ao fazer login")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verificar se token JWT é válido"""
        try:
            # 1. Validar formato do token
            self.validator.validate_jwt_token(token)
            
            # 2. Decodificar token JWT
            payload = self._decode_jwt_token(token)
            if not payload:
                return None
            
            # 3. Verificar se sessão está ativa
            session = self.session_repository.find_by_token(token)
            if not session or not self._is_session_valid(session):
                return None
            
            # 4. Atualizar última atividade
            self.session_repository.update_last_activity(token)
            
            return payload
            
        except AuthValidationError:
            return None
        except Exception as e:
            logger.error(f"Erro ao verificar token: {e}")
            return None
    
    def refresh_token(self, user_id: str, old_token: str, device_info: str, ip_address: str) -> Dict[str, Any]:
        """Renovar token JWT invalidando o anterior"""
        try:
            # 1. Buscar usuário por ID (não por email)
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT u.id, u.email, u.name, u.email_verified, u.is_active,
                               us.status as subscription_status, sp.name as plan_name,
                               sp.max_empresas, sp.max_monthly_matches, sp.max_monthly_rag_queries,
                               us.trial_ends_at, us.current_period_end
                        FROM users u
                        LEFT JOIN user_subscriptions us ON u.id = us.user_id
                        LEFT JOIN subscription_plans sp ON us.plan_id = sp.id
                        WHERE u.id = %s AND u.is_active = true
                    """, (user_id,))
                    
                    user_data = cur.fetchone()
                    if not user_data:
                        raise AuthenticationError("Usuário inválido")
                    
                    user = {
                        'id': user_data[0],
                        'email': user_data[1],
                        'name': user_data[2],
                        'email_verified': user_data[3],
                        'is_active': user_data[4],
                        'subscription_status': user_data[5],
                        'plan_name': user_data[6],
                        'max_empresas': user_data[7],
                        'max_monthly_matches': user_data[8],
                        'max_monthly_rag_queries': user_data[9],
                        'trial_ends_at': user_data[10],
                        'current_period_end': user_data[11]
                    }
            
            if not user.get('email_verified'):
                raise AuthenticationError("Email não verificado")
            
            # 2. Invalidar token antigo
            self.session_repository.deactivate_session_by_token(old_token)
            
            # 3. Gerar novo token e sessão
            session_data = self._create_user_session(user, device_info, ip_address)
            
            return {
                'access_token': session_data['token'],
                'expires_at': session_data['expires_at'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao renovar token: {e}")
            raise DatabaseError("Erro interno ao renovar token")
    
    def get_active_sessions(self, user_id: str) -> list:
        """Buscar sessões ativas do usuário"""
        try:
            return self.session_repository.get_session_details(user_id)
        except Exception as e:
            logger.error(f"Erro ao buscar sessões: {e}")
            raise DatabaseError("Erro ao buscar sessões")
    
    def logout_session(self, token: str) -> bool:
        """Logout de sessão específica"""
        try:
            return self.session_repository.deactivate_session_by_token(token)
        except Exception as e:
            logger.error(f"Erro ao fazer logout: {e}")
            return False
    
    def logout_all_sessions(self, user_id: str) -> int:
        """Logout de todas as sessões do usuário"""
        try:
            return self.session_repository.deactivate_all_user_sessions(user_id)
        except Exception as e:
            logger.error(f"Erro ao fazer logout de todas sessões: {e}")
            return 0
    
    # Métodos privados para lógica interna
    
    def _validate_login_data(self, email: str, password: str) -> None:
        """Validar dados de login"""
        data = {'email': email, 'password': password}
        self.validator.validate_login_data(data)
    
    def _validate_login_security(self, user: Dict[str, Any]) -> None:
        """Validar regras de segurança do login"""
        # Verificar se conta está ativa
        if not user.get('is_active'):
            raise AuthenticationError("Conta desativada")
        
        # Verificar se email foi verificado
        if not user.get('email_verified'):
            raise AuthenticationError("Email não verificado. Verifique sua caixa de entrada.")
        
        # Verificar se conta está bloqueada
        locked_until = user.get('locked_until')
        if locked_until and locked_until > datetime.utcnow():
            raise AuthenticationError("Conta temporariamente bloqueada. Tente novamente mais tarde.")
    
    def _handle_failed_login(self, user_id: str, current_attempts: int) -> None:
        """Gerenciar tentativas de login falhadas"""
        attempts = (current_attempts or 0) + 1
        locked_until = None
        
        # Bloquear após 5 tentativas por 30 minutos
        if attempts >= 5:
            locked_until = datetime.utcnow() + timedelta(minutes=30)
        
        self.user_repository.update_login_attempts(user_id, attempts, locked_until)
    
    def _create_user_session(self, user: Dict[str, Any], device_info: str, ip_address: str) -> Dict[str, Any]:
        """Criar nova sessão para o usuário"""
        # Gerar token JWT
        jti = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        token = self._generate_jwt_token(user['id'], user['email'], jti, expires_at)
        
        # Criar sessão no banco
        session = self.session_repository.create_session(
            user_id=user['id'],
            token=token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
            jti=jti
        )
        
        return {
            'token': token,
            'expires_at': expires_at,
            'session_id': session['id']
        }
    
    def _generate_jwt_token(self, user_id: str, email: str, jti: str, expires_at: datetime) -> str:
        """Gerar token JWT"""
        from flask import current_app
        
        payload = {
            'user_id': user_id,
            'email': email,
            'jti': jti,
            'iat': datetime.utcnow(),
            'exp': expires_at
        }
        
        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    def _decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decodificar token JWT"""
        try:
            from flask import current_app
            
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token expirado")
            return None
        except jwt.InvalidTokenError:
            logger.debug("Token inválido")
            return None
    
    def _is_session_valid(self, session: Dict[str, Any]) -> bool:
        """Verificar se sessão é válida"""
        # Verificar se não foi revogada
        if session.get('revoked_at') is not None:
            return False
        
        # Verificar se não expirou
        expires_at = session.get('expires_at')
        if expires_at and expires_at < datetime.utcnow():
            return False
        
        return True
    
    def _build_login_response(self, user: Dict[str, Any], session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Construir resposta estruturada do login"""
        return {
            'access_token': session_data['token'],
            'user': {
                'id': user['id'],
                'email': user['email'],
                'name': user['name']
            },
            'subscription': {
                'status': user.get('subscription_status'),
                'plan_name': user.get('plan_name'),
                'max_empresas': user.get('max_empresas'),
                'max_monthly_matches': user.get('max_monthly_matches'),
                'max_monthly_rag_queries': user.get('max_monthly_rag_queries'),
                'trial_ends_at': user.get('trial_ends_at').isoformat() if user.get('trial_ends_at') else None,
                'current_period_end': user.get('current_period_end').isoformat() if user.get('current_period_end') else None
            },
            'expires_at': session_data['expires_at'].isoformat()
        } 