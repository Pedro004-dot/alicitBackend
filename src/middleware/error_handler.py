"""
Middleware Global de Tratamento de Erros
Substitui os try/catch repetitivos e inconsistentes do api.py
"""
from flask import jsonify, request
import logging
import time
from typing import Dict, Any, Tuple

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

def register_error_handlers(app):
    """Registrar handlers de erro globais na aplicação Flask"""
    
    @app.errorhandler(BaseAPIException)
    def handle_api_exception(error: BaseAPIException) -> Tuple[Dict[str, Any], int]:
        """Handler para exceções personalizadas da API"""
        logger.error(f"API Exception: {error.message}", extra={
            'error_code': error.error_code,
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url,
            'details': error.details
        })
        
        return jsonify(error.to_dict()), error.http_status
    
    @app.errorhandler(404)
    def handle_not_found(error) -> Tuple[Dict[str, Any], int]:
        """Handler para 404 - Endpoint não encontrado"""
        return jsonify({
            'success': False,
            'error': 'EndpointNotFound',
            'message': f'Endpoint não encontrado: {request.method} {request.path}',
            'details': {
                'available_endpoints': _get_available_endpoints(app)
            }
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error) -> Tuple[Dict[str, Any], int]:
        """Handler para 405 - Método não permitido"""
        return jsonify({
            'success': False,
            'error': 'MethodNotAllowed',
            'message': f'Método {request.method} não permitido para {request.path}',
            'details': {
                'allowed_methods': error.description if hasattr(error, 'description') else []
            }
        }), 405
    
    @app.errorhandler(400)
    def handle_bad_request(error) -> Tuple[Dict[str, Any], int]:
        """Handler para 400 - Requisição inválida"""
        return jsonify({
            'success': False,
            'error': 'BadRequest',
            'message': 'Requisição inválida',
            'details': {
                'description': str(error.description) if hasattr(error, 'description') else 'Dados de entrada inválidos'
            }
        }), 400
    
    @app.errorhandler(500)
    def handle_internal_error(error) -> Tuple[Dict[str, Any], int]:
        """Handler para 500 - Erro interno do servidor"""
        logger.error(f"Internal Server Error: {str(error)}", extra={
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url
        }, exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'InternalServerError',
            'message': 'Erro interno do servidor',
            'details': {
                'error_id': _generate_error_id(),
                'contact': 'Entre em contato com o suporte técnico'
            }
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> Tuple[Dict[str, Any], int]:
        """Handler para exceções não tratadas"""
        logger.error(f"Unexpected Error: {str(error)}", extra={
            'error_type': type(error).__name__,
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url
        }, exc_info=True)
        
        return jsonify({
            'success': False,
            'error': 'UnexpectedError',
            'message': 'Erro inesperado no servidor',
            'details': {
                'error_type': type(error).__name__,
                'error_id': _generate_error_id()
            }
        }), 500

def _get_available_endpoints(app) -> list:
    """Listar endpoints disponíveis para ajudar no debug"""
    endpoints = []
    for rule in app.url_map.iter_rules():
        endpoints.append({
            'path': rule.rule,
            'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
        })
    return sorted(endpoints, key=lambda x: x['path'])

def _generate_error_id() -> str:
    """Gerar ID único para rastreamento de erros"""
    import uuid
    import datetime
    
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    return f"ERR_{timestamp}_{unique_id}"

# Decorator para adicionar logging automático aos endpoints
def log_endpoint_access(func):
    """Decorator para logging automático de acesso a endpoints"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        logger.info(f"🚀 {request.method} {request.path}", extra={
            'endpoint': func.__name__,
            'method': request.method,
            'url': request.url,
            'user_agent': request.headers.get('User-Agent'),
            'ip': request.remote_addr
        })
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(f"✅ {request.method} {request.path} - {duration:.3f}s", extra={
                'endpoint': func.__name__,
                'duration': duration,
                'status': 'success'
            })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            logger.error(f"❌ {request.method} {request.path} - {duration:.3f}s - {str(e)}", extra={
                'endpoint': func.__name__,
                'duration': duration,
                'status': 'error',
                'error': str(e)
            })
            
            raise
    
    return wrapper 