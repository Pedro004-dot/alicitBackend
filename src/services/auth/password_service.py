"""
Service para operações de recuperação e alteração de senhas
Sistema com códigos seguros e validações
"""
import logging
import random
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from .base_auth_service import BaseAuthService
from .logout_service import LogoutService
from services.email_service import EmailService
from exceptions.api_exceptions import ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

class PasswordService(BaseAuthService):
    """Service para gerenciar recuperação e alteração de senhas"""
    
    def __init__(self):
        """Inicializar service com dependências"""
        super().__init__()
        self.email_service = EmailService()
        self.logout_service = LogoutService()
    
    def _generate_numeric_code(self, length: int = 6) -> str:
        """Gera um código numérico de comprimento específico."""
        return "".join([str(random.randint(0, 9)) for _ in range(length)])
    
    def request_password_reset(self, email: str) -> None:
        """Solicitar reset de senha por email"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar usuário (não revelar se existe ou não)
                    cur.execute("""
                        SELECT id, name, email_verified, is_active
                        FROM users 
                        WHERE LOWER(email) = LOWER(%s)
                    """, (email,))
                    
                    user = cur.fetchone()
                    
                    # Se usuário existe e está ativo e verificado
                    if user and user[3] and user[2]:  # is_active and email_verified
                        # Gerar código de reset
                        reset_code = self._generate_numeric_code(6)
                        hashed_code = self._hash_password(reset_code) # Reutiliza a função de hash de senha
                        reset_expires = datetime.now(timezone.utc) + timedelta(minutes=10) # 10 minutos para reset
                        
                        # Salvar código no banco
                        cur.execute("""
                            UPDATE users 
                            SET reset_password_code = %s,
                                reset_password_expires_at = %s
                            WHERE id = %s
                        """, (hashed_code, reset_expires, user[0]))
                        
                        conn.commit()
                        
                        # Enviar email com o código
                        try:
                            self.email_service.send_password_reset_code_email(
                                email, user[1], reset_code
                            )
                        except Exception as e:
                            logger.warning(f"Erro ao enviar email de código de reset: {e}")
                    else:
                        # Log para depuração do motivo de não enviar o email
                        if not user:
                            logger.info(f"Solicitação de reset para email não cadastrado: {email}")
                        elif not user[2]: # email_verified
                            logger.info(f"Solicitação de reset para email não verificado: {email}")
                        elif not user[3]: # is_active
                            logger.info(f"Solicitação de reset para usuário inativo: {email}")
            
            # Sempre retornar sucesso por segurança (não revelar se email existe)
                            
        except Exception as e:
            logger.error(f"Erro ao solicitar reset de senha: {e}")
            # Não propagar erro para não revelar informações
    
    def verify_password_reset_code(self, email: str, code: str) -> bool:
        """Verifica se o código de reset de senha é válido, sem alterar a senha."""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, reset_password_code, reset_password_expires_at
                        FROM users 
                        WHERE LOWER(email) = LOWER(%s) AND is_active = true
                    """, (email,))
                    
                    user = cur.fetchone()
                    if not user or not user[1]: # reset_password_code
                        raise ValidationError("Código de reset inválido ou não solicitado.")
                    
                    if user[2] < datetime.now(timezone.utc):  # reset_password_expires_at
                        cur.execute("""
                            UPDATE users SET reset_password_code = NULL, reset_password_expires_at = NULL WHERE id = %s
                        """, (user[0],))
                        conn.commit()
                        raise ValidationError("Código de reset expirado. Por favor, solicite um novo.")

                    if not self._verify_password(code, user[1]): # reset_password_code
                        raise ValidationError("Código de reset incorreto.")
                    
                    # Código é válido
                    return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao verificar código de reset de senha: {e}")
            raise DatabaseError("Erro interno ao verificar código de reset")
    
    def reset_password(self, email: str, code: str, new_password: str) -> None:
        """Redefinir senha com código de reset"""
        try:
            # Validar nova senha
            self._validate_password_strength(new_password)
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar usuário pelo email
                    cur.execute("""
                        SELECT id, reset_password_code, reset_password_expires_at
                        FROM users 
                        WHERE LOWER(email) = LOWER(%s) AND is_active = true
                    """, (email,))
                    
                    user = cur.fetchone()
                    if not user or not user[1]: # reset_password_code
                        raise ValidationError("Código de reset inválido ou não solicitado.")
                    
                    # Verificar se código não expirou
                    if user[2] < datetime.now(timezone.utc):  # reset_password_expires_at
                        # Limpar código expirado
                        cur.execute("""
                            UPDATE users SET reset_password_code = NULL, reset_password_expires_at = NULL WHERE id = %s
                        """, (user[0],))
                        conn.commit()
                        raise ValidationError("Código de reset expirado. Por favor, solicite um novo.")
                    
                    # Verificar se o código bate com o hash
                    if not self._verify_password(code, user[1]): # reset_password_code
                        raise ValidationError("Código de reset incorreto.")

                    # Hash da nova senha
                    password_hash = self._hash_password(new_password)
                    
                    # Atualizar senha e limpar código
                    cur.execute("""
                        UPDATE users 
                        SET password_hash = %s,
                            reset_password_code = NULL,
                            reset_password_expires_at = NULL,
                            password_changed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (password_hash, user[0]))
                    
                    conn.commit()
            
            # Invalidar todas as sessões do usuário por segurança
            try:
                self.logout_service.logout_all_sessions(user[0])
            except Exception as e:
                logger.warning(f"Erro ao invalidar sessões após reset: {e}")
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao redefinir senha: {e}")
            raise DatabaseError("Erro interno ao redefinir senha")
    
    def change_password(self, user_id: str, current_password: str, new_password: str, current_jti: str = None) -> None:
        """Alterar senha do usuário logado"""
        try:
            # Validar nova senha
            self._validate_password_strength(new_password)
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Buscar usuário atual
                    user = self._get_user_by_id(user_id)
                    if not user:
                        raise ValidationError("Usuário não encontrado")
                    
                    # Verificar senha atual
                    if not self._verify_password(current_password, user[3]):  # password_hash
                        raise ValidationError("Senha atual incorreta")
                    
                    # Hash da nova senha
                    password_hash = self._hash_password(new_password)
                    
                    # Atualizar senha
                    cur.execute("""
                        UPDATE users 
                        SET password_hash = %s,
                            password_changed_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (password_hash, user_id))
                    
                    conn.commit()
            
            # Invalidar todas as outras sessões (exceto a atual se especificada)
            try:
                if current_jti:
                    # Invalidar todas exceto a atual
                    with self.db_manager.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                UPDATE user_sessions 
                                SET revoked_at = CURRENT_TIMESTAMP
                                WHERE user_id = %s AND jti != %s AND revoked_at IS NULL
                            """, (user_id, current_jti))
                            conn.commit()
                else:
                    # Invalidar todas as sessões
                    self.logout_service.logout_all_sessions(user_id)
            except Exception as e:
                logger.warning(f"Erro ao invalidar sessões após mudança de senha: {e}")
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro ao alterar senha: {e}")
            raise DatabaseError("Erro interno ao alterar senha") 