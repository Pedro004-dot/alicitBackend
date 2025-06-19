"""
Service para operações de registro de usuários
Sistema multi-tenant com verificação de email e trial automático
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from .base_auth_service import BaseAuthService
from services.email_service import EmailService
from exceptions.api_exceptions import ValidationError, DatabaseError
import random

logger = logging.getLogger(__name__)

class RegisterService(BaseAuthService):
    """Service para gerenciar registro e verificação de usuários"""
    
    def __init__(self):
        """Inicializar service com dependências"""
        super().__init__()
        self.email_service = EmailService()
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Registrar novo usuário"""
        
        try:
            logger.info(f"🔄 Iniciando registro para email: {user_data.get('email', 'N/A')}")
            
            # Validar dados
            logger.info("📝 Validando dados do usuário...")
            self._validate_user_registration(user_data)
            logger.info("✅ Dados validados com sucesso")
            
            # Hash da senha
            password_hash = self._hash_password(user_data['password'])
            
            # Gerar código de verificação (6 dígitos)
            verification_code = ''.join(random.choices('0123456789', k=6))
            verification_expires = datetime.utcnow() + timedelta(minutes=10)  # Código expira em 10 minutos
            
            # Verificar se email já existe ANTES de iniciar transação
            logger.info("🔍 Verificando se email já existe...")
            if self._check_user_exists(user_data['email']):
                logger.warning(f"❌ Email já existe: {user_data['email']}")
                raise ValidationError("Email já está em uso")
            logger.info("✅ Email disponível")
            
            user_id = str(uuid.uuid4())
            
            # Primeiro: Criar usuário
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO users (id, email, password_hash, name, 
                                         verification_code, verification_code_expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (user_id, user_data['email'], password_hash, user_data['name'],
                          verification_code, verification_expires))
                    conn.commit()
            
            # Segundo: Criar subscription (após usuário estar commitado)
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar plano Free Trial e criar subscription
                    trial_plan = self._get_trial_plan()
                    trial_ends_at = self._create_trial_subscription(user_id, trial_plan[0])
                    conn.commit()
            
            # Enviar email com código de verificação
            try:
                self.email_service.send_verification_code(
                    user_data['email'], 
                    user_data['name'], 
                    verification_code
                )
            except Exception as e:
                logger.warning(f"Erro ao enviar email de verificação: {e}")
                # Não falhar o registro por problemas de email
            
            return {
                'user_id': user_id,
                'trial_ends_at': trial_ends_at.isoformat()
            }
            
        except ValidationError as e:
            logger.warning(f"❌ Erro de validação no registro: {e}")
            raise
        except Exception as e:
            logger.error(f"💥 Erro inesperado ao registrar usuário: {e}", exc_info=True)
            raise DatabaseError("Erro interno ao registrar usuário")
    
    def verify_email(self, code: str, email: str) -> Dict[str, Any]:
        """Verificar email do usuário com código"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar usuário pelo email e código
                    cur.execute("""
                        SELECT id, email, name, email_verified, verification_code_expires_at
                        FROM users 
                        WHERE email = %s AND verification_code = %s AND is_active = true
                    """, (email, code))
                    
                    user = cur.fetchone()
                    if not user:
                        raise ValidationError("Código de verificação inválido")
                    
                    # Verificar se já foi verificado
                    if user[3]:  # email_verified
                        raise ValidationError("Email já foi verificado")
                    
                    # Verificar se código não expirou
                    if user[4] < datetime.utcnow():  # verification_code_expires_at
                        raise ValidationError("Código de verificação expirado")
                    
                    # Marcar email como verificado
                    cur.execute("""
                        UPDATE users 
                        SET email_verified = true, 
                            verification_code = NULL,
                            verification_code_expires_at = NULL,
                            email_verified_at = NOW()
                        WHERE id = %s
                    """, (user[0],))
                    
                    conn.commit()
            
            # Enviar email de boas-vindas
            try:
                self.email_service.send_welcome_email(user[1], user[2])
            except Exception as e:
                logger.warning(f"Erro ao enviar email de boas-vindas: {e}")
            
            return {
                'user_id': user[0],
                'email': user[1],
                'name': user[2]
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao verificar email: {e}")
            raise DatabaseError("Erro interno ao verificar email")
    
    def resend_verification_code(self, email: str) -> None:
        """Reenviar código de verificação"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar usuário
                    cur.execute("""
                        SELECT id, name, email_verified, is_active
                        FROM users 
                        WHERE LOWER(email) = LOWER(%s)
                    """, (email,))
                    
                    user = cur.fetchone()
                    if not user:
                        raise ValidationError("Email não encontrado")
                    
                    if not user[3]:  # is_active
                        raise ValidationError("Conta desativada")
                    
                    if user[2]:  # email_verified
                        raise ValidationError("Email já foi verificado")
                    
                    # Gerar novo código
                    verification_code = ''.join(random.choices('0123456789', k=6))
                    verification_expires = datetime.utcnow() + timedelta(minutes=10)
                    
                    # Atualizar código no banco
                    cur.execute("""
                        UPDATE users 
                        SET verification_code = %s,
                            verification_code_expires_at = %s
                        WHERE id = %s
                    """, (verification_code, verification_expires, user[0]))
                    
                    conn.commit()
            
            # Enviar email
            self.email_service.send_verification_code(email, user[1], verification_code)
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao reenviar verificação: {e}")
            raise DatabaseError("Erro interno ao reenviar verificação") 