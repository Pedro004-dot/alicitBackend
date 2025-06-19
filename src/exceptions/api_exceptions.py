"""
Exceções personalizadas para substituir o tratamento de erro genérico do api.py
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAPIException(Exception):
    """Exceção base para todas as exceções da API"""
    
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter exceção para formato JSON"""
        return {
            'success': False,
            'error': self.error_code,
            'message': self.message,
            'details': self.details
        }
    
    @property
    def http_status(self) -> int:
        """Status HTTP padrão para a exceção"""
        return 500

class ValidationError(BaseAPIException):
    """Erro de validação de entrada"""
    
    @property
    def http_status(self) -> int:
        return 400

class NotFoundError(BaseAPIException):
    """Recurso não encontrado"""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} não encontrado: {resource_id}"
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id
    
    @property
    def http_status(self) -> int:
        return 404

class DatabaseError(BaseAPIException):
    """Erro de banco de dados"""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error
        logger.error(f"Database error: {message}", exc_info=original_error)

class ProcessingError(BaseAPIException):
    """Erro de processamento de tarefas assíncronas"""
    
    def __init__(self, task_name: str, message: str):
        super().__init__(f"Erro no processamento de {task_name}: {message}")
        self.task_name = task_name
    
    @property
    def http_status(self) -> int:
        return 422

class ConfigurationError(BaseAPIException):
    """Erro de configuração"""
    
    def __init__(self, config_name: str, message: str):
        super().__init__(f"Erro de configuração em {config_name}: {message}")
        self.config_name = config_name

class ExternalAPIError(BaseAPIException):
    """Erro ao chamar APIs externas"""
    
    def __init__(self, service_name: str, message: str, status_code: Optional[int] = None):
        super().__init__(f"Erro no serviço {service_name}: {message}")
        self.service_name = service_name
        self.status_code = status_code
    
    @property
    def http_status(self) -> int:
        return 502  # Bad Gateway

class AuthenticationError(BaseAPIException):
    """Erro de autenticação"""
    
    @property
    def http_status(self) -> int:
        return 401

class AuthorizationError(BaseAPIException):
    """Erro de autorização"""
    
    @property
    def http_status(self) -> int:
        return 403

class RateLimitError(BaseAPIException):
    """Erro de limite de taxa"""
    
    @property
    def http_status(self) -> int:
        return 429

class ConcurrencyError(BaseAPIException):
    """Erro de concorrência (processo já em execução)"""
    
    @property
    def http_status(self) -> int:
        return 409  # Conflict 