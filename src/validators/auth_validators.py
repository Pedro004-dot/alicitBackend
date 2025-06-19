"""
Validadores para operações de autenticação
Responsáveis apenas por validação de dados de entrada
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AuthValidationError(Exception):
    """Exceção customizada para erros de validação"""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)

class EmailValidator:
    """Validador específico para emails"""
    
    @staticmethod
    def validate(email: str) -> Tuple[bool, str]:
        """Validar formato de email"""
        if not email:
            return False, "Email é obrigatório"
        
        if len(email) > 255:
            return False, "Email muito longo (máximo 255 caracteres)"
        
        # Regex simples para email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Formato de email inválido"
        
        return True, ""

class PasswordValidator:
    """Validador específico para senhas"""
    
    @staticmethod
    def validate(password: str) -> Tuple[bool, str]:
        """Validar força da senha"""
        if not password:
            return False, "Senha é obrigatória"
        
        if len(password) < 8:
            return False, "Senha deve ter pelo menos 8 caracteres"
        
        if len(password) > 128:
            return False, "Senha muito longa (máximo 128 caracteres)"
        
        # Verificar se tem pelo menos uma letra maiúscula
        if not re.search(r'[A-Z]', password):
            return False, "Senha deve conter pelo menos uma letra maiúscula"
        
        # Verificar se tem pelo menos uma letra minúscula
        if not re.search(r'[a-z]', password):
            return False, "Senha deve conter pelo menos uma letra minúscula"
        
        # Verificar se tem pelo menos um número
        if not re.search(r'[0-9]', password):
            return False, "Senha deve conter pelo menos um número"
        
        # Verificar se tem pelo menos um caractere especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Senha deve conter pelo menos um caractere especial"
        
        return True, ""

class NameValidator:
    """Validador específico para nomes"""
    
    @staticmethod
    def validate(name: str) -> Tuple[bool, str]:
        """Validar nome do usuário"""
        if not name:
            return False, "Nome é obrigatório"
        
        name = name.strip()
        
        if len(name) < 2:
            return False, "Nome deve ter pelo menos 2 caracteres"
        
        if len(name) > 100:
            return False, "Nome muito longo (máximo 100 caracteres)"
        
        # Verificar se contém apenas letras, espaços e alguns caracteres especiais
        if not re.match(r'^[a-zA-ZÀ-ÿ\s\'-]+$', name):
            return False, "Nome contém caracteres inválidos"
        
        return True, ""

class RegisterDataValidator:
    """Validador para dados de registro"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar dados completos de registro"""
        errors = []
        
        # Validar email
        email = data.get('email', '').strip().lower()
        valid_email, email_error = EmailValidator.validate(email)
        if not valid_email:
            errors.append(email_error)
        
        # Validar senha
        password = data.get('password', '')
        valid_password, password_error = PasswordValidator.validate(password)
        if not valid_password:
            errors.append(password_error)
        
        # Validar nome
        name = data.get('name', '').strip()
        valid_name, name_error = NameValidator.validate(name)
        if not valid_name:
            errors.append(name_error)
        
        return len(errors) == 0, errors

class LoginDataValidator:
    """Validador para dados de login"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar dados de login"""
        errors = []
        
        # Validar email
        email = data.get('email', '').strip().lower()
        if not email:
            errors.append("Email é obrigatório")
        
        # Validar senha (menos rigoroso no login)
        password = data.get('password', '')
        if not password:
            errors.append("Senha é obrigatória")
        
        return len(errors) == 0, errors

class PasswordResetValidator:
    """Validador para reset de senha"""
    
    @staticmethod
    def validate_reset_request(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar solicitação de reset"""
        errors = []
        
        # Validar email
        email = data.get('email', '').strip().lower()
        valid_email, email_error = EmailValidator.validate(email)
        if not valid_email:
            errors.append(email_error)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_reset_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar dados de reset (token + nova senha)"""
        errors = []
        
        # Validar token
        token = data.get('token', '').strip()
        if not token:
            errors.append("Token de reset é obrigatório")
        
        # Validar nova senha
        password = data.get('new_password', '')
        valid_password, password_error = PasswordValidator.validate(password)
        if not valid_password:
            errors.append(password_error)
        
        return len(errors) == 0, errors

class ProfileUpdateValidator:
    """Validador para atualização de perfil"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar dados de atualização de perfil"""
        errors = []
        
        # Validar nome se fornecido
        if 'name' in data:
            name = data.get('name', '').strip()
            valid_name, name_error = NameValidator.validate(name)
            if not valid_name:
                errors.append(name_error)
        
        # Email não pode ser alterado via perfil (por questões de segurança)
        if 'email' in data:
            errors.append("Email não pode ser alterado via perfil")
        
        return len(errors) == 0, errors

class PasswordChangeValidator:
    """Validador para mudança de senha"""
    
    @staticmethod
    def validate(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validar dados de mudança de senha"""
        errors = []
        
        # Validar senha atual
        current_password = data.get('current_password', '')
        if not current_password:
            errors.append("Senha atual é obrigatória")
        
        # Validar nova senha
        new_password = data.get('new_password', '')
        valid_password, password_error = PasswordValidator.validate(new_password)
        if not valid_password:
            errors.append(password_error)
        
        # Verificar se senhas são diferentes
        if current_password and new_password and current_password == new_password:
            errors.append("Nova senha deve ser diferente da atual")
        
        return len(errors) == 0, errors

class TokenValidator:
    """Validador para tokens"""
    
    @staticmethod
    def validate_jwt_format(token: str) -> Tuple[bool, str]:
        """Validar formato básico de JWT"""
        if not token:
            return False, "Token é obrigatório"
        
        # JWT tem 3 partes separadas por pontos
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Formato de token inválido"
        
        return True, ""

# Classe principal que agrega todos os validadores
class AuthValidator:
    """Validador principal para operações de autenticação"""
    
    def __init__(self):
        self.email_validator = EmailValidator()
        self.password_validator = PasswordValidator()
        self.name_validator = NameValidator()
        self.register_validator = RegisterDataValidator()
        self.login_validator = LoginDataValidator()
        self.password_reset_validator = PasswordResetValidator()
        self.profile_validator = ProfileUpdateValidator()
        self.password_change_validator = PasswordChangeValidator()
        self.token_validator = TokenValidator()
    
    def validate_register_data(self, data: Dict[str, Any]) -> None:
        """Validar dados de registro - lança exceção se inválido"""
        valid, errors = self.register_validator.validate(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_login_data(self, data: Dict[str, Any]) -> None:
        """Validar dados de login - lança exceção se inválido"""
        valid, errors = self.login_validator.validate(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_password_reset_request(self, data: Dict[str, Any]) -> None:
        """Validar solicitação de reset - lança exceção se inválido"""
        valid, errors = self.password_reset_validator.validate_reset_request(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_password_reset(self, data: Dict[str, Any]) -> None:
        """Validar dados de reset - lança exceção se inválido"""
        valid, errors = self.password_reset_validator.validate_reset_data(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_profile_update(self, data: Dict[str, Any]) -> None:
        """Validar atualização de perfil - lança exceção se inválido"""
        valid, errors = self.profile_validator.validate(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_password_change(self, data: Dict[str, Any]) -> None:
        """Validar mudança de senha - lança exceção se inválido"""
        valid, errors = self.password_change_validator.validate(data)
        if not valid:
            raise AuthValidationError("; ".join(errors))
    
    def validate_jwt_token(self, token: str) -> None:
        """Validar formato de JWT - lança exceção se inválido"""
        valid, error = self.token_validator.validate_jwt_format(token)
        if not valid:
            raise AuthValidationError(error) 