"""
Base service para operações de autenticação
Contém validações, hash de senhas e utilitários comuns
"""
import logging
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import bcrypt
import jwt
from config.database import get_db_manager
from exceptions.api_exceptions import ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

class BaseAuthService:
    """Base service com funcionalidades comuns de autenticação"""
    
    def __init__(self):
        """Inicializar service com dependências"""
        self.db_manager = get_db_manager()
    
    def _validate_user_registration(self, data: Dict[str, Any]) -> None:
        """Validar dados de registro do usuário"""
        logger.info(f"🔍 Validando dados: {data}")
        
        # Validar email
        email = data.get('email', '').strip().lower()
        logger.info(f"📧 Email recebido: '{email}'")
        if not email or '@' not in email or len(email) < 5:
            logger.warning(f"❌ Email inválido: '{email}'")
            raise ValidationError("Email inválido")
        
        # Validar senha
        password = data.get('password', '')
        logger.info(f"🔒 Senha recebida: {'***' if password else 'VAZIA'} (len={len(password)})")
        if not password or len(password) < 8:
            logger.warning(f"❌ Senha inválida: len={len(password)}")
            raise ValidationError("Senha deve ter pelo menos 8 caracteres")
        
        # Validar nome
        name = data.get('name', '').strip()
        logger.info(f"👤 Nome recebido: '{name}' (len={len(name)})")
        if not name or len(name) < 2:
            logger.warning(f"❌ Nome inválido: '{name}' (len={len(name)})")
            raise ValidationError("Nome deve ter pelo menos 2 caracteres")
        
        # Atualizar dados limpos
        data['email'] = email
        data['name'] = name
        logger.info("✅ Todos os dados validados com sucesso")
    
    def _validate_password_strength(self, password: str) -> None:
        """Validar força da senha"""
        if not password or len(password) < 8:
            raise ValidationError("Senha deve ter pelo menos 8 caracteres")
        
        # Adicionar mais validações se necessário
        # has_upper = any(c.isupper() for c in password)
        # has_lower = any(c.islower() for c in password)
        # has_digit = any(c.isdigit() for c in password)
        
    def _hash_password(self, password: str) -> str:
        """Gerar hash da senha usando bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verificar senha contra hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _generate_token(self, length: int = 32) -> str:
        """Gerar token seguro"""
        return secrets.token_urlsafe(length)
    
    def _generate_jwt_token(self, user_id: str, email: str, jti: str, expires_in_days: int = 7) -> tuple:
        """Gerar JWT token com payload"""
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        token_payload = {
            'user_id': user_id,
            'email': email,
            'jti': jti,
            'iat': datetime.utcnow(),
            'exp': expires_at
        }
        
        # Usar secret key do Flask
        from flask import current_app
        access_token = jwt.encode(
            token_payload, 
            current_app.config['SECRET_KEY'], 
            algorithm='HS256'
        )
        
        return access_token, expires_at
    
    def _get_token_hash(self, token: str) -> str:
        """Gerar hash do token para armazenamento seguro"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _check_user_exists(self, email: str) -> Optional[tuple]:
        """Verificar se usuário existe por email"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
                return cur.fetchone()
    
    def _get_user_by_id(self, user_id: str) -> Optional[tuple]:
        """Buscar usuário por ID"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, name, password_hash, email_verified, 
                           is_active, login_attempts, locked_until, created_at, last_login_at
                    FROM users 
                    WHERE id = %s
                """, (user_id,))
                return cur.fetchone()
    
    def _get_user_by_email(self, email: str) -> Optional[tuple]:
        """Buscar usuário por email"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, name, password_hash, email_verified, 
                           is_active, login_attempts, locked_until, created_at, last_login_at
                    FROM users 
                    WHERE LOWER(email) = LOWER(%s)
                """, (email,))
                return cur.fetchone()
    
    def _update_login_attempts(self, user_id: str, attempts: int, locked_until: Optional[datetime] = None) -> None:
        """Atualizar tentativas de login e bloqueio"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET login_attempts = %s, locked_until = %s
                    WHERE id = %s
                """, (attempts, locked_until, user_id))
                conn.commit()
    
    def _reset_login_attempts(self, user_id: str) -> None:
        """Reset tentativas de login e atualizar último login"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET login_attempts = 0, locked_until = NULL, last_login_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (user_id,))
                conn.commit()
    
    def _get_trial_plan(self) -> tuple:
        """Buscar plano de trial ativo"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM subscription_plans WHERE is_trial_plan = true AND is_active = true")
                trial_plan = cur.fetchone()
                if not trial_plan:
                    raise DatabaseError("Plano de trial não encontrado")
                return trial_plan
    
    def _create_trial_subscription(self, user_id: str, trial_plan_id: str) -> datetime:
        """Criar subscription de trial automática"""
        trial_ends_at = datetime.utcnow() + timedelta(days=7)
        
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_subscriptions (id, user_id, subscription_plan_id, 
                                                   status, trial_ends_at, current_period_end)
                    VALUES (%s, %s, %s, 'trial', %s, %s)
                """, (str(uuid.uuid4()), user_id, trial_plan_id, trial_ends_at, trial_ends_at))
                conn.commit()
        
        return trial_ends_at 