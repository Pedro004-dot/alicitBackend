"""
Middleware para autenticação JWT
Verifica tokens em todas as rotas protegidas
"""
import logging
from functools import wraps
from flask import request, jsonify, g, current_app
from services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Instância global do service de autenticação
auth_service = None

def get_auth_service():
    """Obter instância do service de autenticação com lazy loading"""
    global auth_service
    if auth_service is None:
        auth_service = AuthService()
    return auth_service

def require_auth(f):
    """
    Decorator para rotas que requerem autenticação JWT
    
    Usage:
        @require_auth
        def protected_route():
            user = get_current_user()
            return jsonify({'user_id': user['user_id']})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extrair token do header Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({
                    'success': False,
                    'error': 'Token de autenticação obrigatório',
                    'message': 'Header Authorization não fornecido'
                }), 401
            
            # Verificar formato "Bearer <token>"
            try:
                scheme, token = auth_header.split(' ', 1)
                if scheme.lower() != 'bearer':
                    raise ValueError("Esquema inválido")
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Formato de token inválido',
                    'message': 'Use: Authorization: Bearer <token>'
                }), 401
            
            # Verificar token
            auth_svc = get_auth_service()
            payload = auth_svc.verify_token(token)
            
            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'Token inválido',
                    'message': 'Token expirado, revogado ou inválido'
                }), 401
            
            # Armazenar dados do usuário no contexto da requisição
            g.current_user = payload
            
            # Chamar função original
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Erro no middleware de autenticação: {e}")
            return jsonify({
                'success': False,
                'error': 'Erro interno',
                'message': 'Erro inesperado na autenticação'
            }), 500
    
    return decorated_function

def get_current_user():
    """
    Obter dados do usuário atual da requisição
    
    Returns:
        Dict com dados do token JWT ou None se não autenticado
    """
    return getattr(g, 'current_user', None)

def require_subscription_active(f):
    """
    Decorator para rotas que requerem subscription ativa
    Deve ser usado junto com @require_auth
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            current_user = get_current_user()
            if not current_user:
                return jsonify({
                    'success': False,
                    'error': 'Autenticação obrigatória',
                    'message': 'Use @require_auth antes de @require_subscription_active'
                }), 401
            
            # Buscar dados de subscription do usuário
            auth_svc = get_auth_service()
            profile = auth_svc.get_user_profile(current_user['user_id'])
            
            subscription = profile.get('subscription', {})
            status = subscription.get('status')
            
            # Verificar se subscription está ativa
            if status not in ['trial', 'active']:
                return jsonify({
                    'success': False,
                    'error': 'Subscription inativa',
                    'message': 'Sua assinatura expirou ou foi cancelada',
                    'subscription_status': status
                }), 402  # Payment Required
            
            # Verificar se trial não expirou
            if status == 'trial':
                trial_ends_at = subscription.get('trial_ends_at')
                if trial_ends_at:
                    from datetime import datetime
                    trial_end = datetime.fromisoformat(trial_ends_at.replace('Z', '+00:00'))
                    if trial_end < datetime.utcnow():
                        return jsonify({
                            'success': False,
                            'error': 'Trial expirado',
                            'message': 'Seu período de trial gratuito expirou',
                            'trial_ends_at': trial_ends_at
                        }), 402
            
            # Armazenar dados de subscription no contexto
            g.current_subscription = subscription
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Erro no middleware de subscription: {e}")
            return jsonify({
                'success': False,
                'error': 'Erro interno',
                'message': 'Erro inesperado na verificação de subscription'
            }), 500
    
    return decorated_function

def get_current_subscription():
    """
    Obter dados da subscription atual da requisição
    
    Returns:
        Dict com dados da subscription ou None
    """
    return getattr(g, 'current_subscription', None)

def check_usage_limit(usage_type: str, limit_field: str):
    """
    Decorator factory para verificar limites de uso
    
    Args:
        usage_type: Tipo de uso ('empresa', 'match', 'rag_query')
        limit_field: Campo do plano com o limite ('max_empresas', 'max_monthly_matches', etc.)
    
    Usage:
        @check_usage_limit('empresa', 'max_empresas')
        def create_empresa():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                current_user = get_current_user()
                if not current_user:
                    return jsonify({
                        'success': False,
                        'error': 'Autenticação obrigatória'
                    }), 401
                
                subscription = get_current_subscription()
                if not subscription:
                    # Buscar subscription se não estiver no contexto
                    auth_svc = get_auth_service()
                    profile = auth_svc.get_user_profile(current_user['user_id'])
                    subscription = profile.get('subscription', {})
                
                # Verificar limite
                limit = subscription.get(limit_field)
                if limit is not None:  # None = ilimitado
                    # Buscar uso atual
                    # TODO: Implementar lógica específica para cada tipo de uso
                    # Por agora, permitir tudo
                    pass
                
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Erro na verificação de limite de uso: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Erro interno',
                    'message': 'Erro inesperado na verificação de limite'
                }), 500
        
        return decorated_function
    return decorator

def optional_auth(f):
    """
    Decorator para rotas que podem funcionar com ou sem autenticação
    Se token fornecido, valida e armazena dados do usuário
    Se não fornecido, continua sem dados do usuário
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Tentar extrair token do header Authorization
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    scheme, token = auth_header.split(' ', 1)
                    if scheme.lower() == 'bearer':
                        # Verificar token se fornecido
                        auth_svc = get_auth_service()
                        payload = auth_svc.verify_token(token)
                        if payload:
                            g.current_user = payload
                except:
                    # Ignorar erros de token em rotas opcionais
                    pass
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Erro no middleware de autenticação opcional: {e}")
            # Em rotas opcionais, continuar mesmo com erros
            return f(*args, **kwargs)
    
    return decorated_function 