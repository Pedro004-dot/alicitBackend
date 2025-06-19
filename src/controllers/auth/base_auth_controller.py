"""
Base controller para operações de autenticação
Contém utilitários e tratamento de erros comuns
"""
import logging
from flask import request, jsonify
from middleware.auth_middleware import get_current_user
from exceptions.api_exceptions import ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)

class BaseAuthController:
    """Base controller com funcionalidades comuns de autenticação"""
    
    def _get_json_data(self, required_fields: list = None) -> dict:
        """Extrair e validar dados JSON da requisição"""
        data = request.get_json()
        
        if not data:
            raise ValidationError("Nenhum dado fornecido")
        
        if required_fields:
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                raise ValidationError(f'Campos obrigatórios faltando: {", ".join(missing_fields)}')
        
        return data
    
    def _get_device_info(self, data: dict = None) -> dict:
        """Extrair informações do dispositivo da requisição"""
        device_info = data.get('device_info', {}) if data else {}
        
        if not device_info:
            device_info = {
                'user_agent': request.headers.get('User-Agent', ''),
                'ip_address': request.remote_addr
            }
        
        return device_info
    
    def _get_current_user_safe(self) -> dict:
        """Obter usuário atual com tratamento de erro"""
        try:
            return get_current_user()
        except Exception as e:
            logger.error(f"Erro ao obter usuário atual: {e}")
            raise ValidationError("Token inválido")
    
    def _success_response(self, data: dict = None, message: str = None, status_code: int = 200) -> tuple:
        """Criar resposta de sucesso padronizada"""
        response = {'success': True}
        
        if data:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return jsonify(response), status_code
    
    def _error_response(self, error_type: str, message: str, status_code: int = 400) -> tuple:
        """Criar resposta de erro padronizada"""
        return jsonify({
            'success': False,
            'error': error_type,
            'message': message
        }), status_code
    
    def _handle_exceptions(self, func, *args, **kwargs):
        """Wrapper para tratamento padronizado de exceções"""
        try:
            return func(*args, **kwargs)
            
        except ValidationError as e:
            return self._error_response('Dados inválidos', str(e), 400)
            
        except NotFoundError as e:
            return self._error_response('Não encontrado', str(e), 404)
            
        except DatabaseError as e:
            logger.error(f"Erro de banco: {e}")
            return self._error_response('Erro interno do servidor', 'Falha na operação', 500)
            
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            return self._error_response('Erro interno', 'Erro inesperado no servidor', 500) 