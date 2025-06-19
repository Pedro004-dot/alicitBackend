"""
Routes para autenticação - endpoints HTTP
Sistema multi-tenant com JWT, verificação de email e free trial automático
"""
from flask import Blueprint
from controllers.auth_controller import AuthController

# Criar blueprint com url_prefix correto
auth_routes = Blueprint('auth', __name__, url_prefix='/api/auth')

# Instanciar controller
auth_controller = AuthController()

# ====== ROTAS DE AUTENTICAÇÃO ======

@auth_routes.route('/register', methods=['POST'], strict_slashes=False)
def register():
    """
    POST /api/auth/register - Registro de novo usuário
    
    DESCRIÇÃO:
    - Registra novo usuário no sistema multi-tenant
    - Cria user_subscription com plano "Free Trial" automático (7 dias)
    - Envia email de verificação obrigatório
    - Usuário só pode fazer login após verificar email
    
    PARÂMETROS (Body JSON):
    - email: Email único válido (obrigatório)
    - password: Senha mínimo 8 caracteres (obrigatório)  
    - name: Nome completo do usuário (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Instrução para verificar email
    - user_id: ID do usuário criado (para debug)
    - trial_ends_at: Data de expiração do trial gratuito
    """
    return auth_controller.register()

@auth_routes.route('/verify-email', methods=['POST'], strict_slashes=False)
def verify_email():
    """
    POST /api/auth/verify-email - Verificar email com token
    
    DESCRIÇÃO:
    - Verifica email do usuário usando token enviado por email
    - Ativa a conta para permitir login
    - Token tem validade de 24 horas
    
    PARÂMETROS (Body JSON):
    - token: Token de verificação recebido por email (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de ativação
    - redirect_to: URL do frontend para login
    """
    return auth_controller.verify_email()

@auth_routes.route('/resend-verification', methods=['POST'], strict_slashes=False)
def resend_verification():
    """
    POST /api/auth/resend-verification - Reenviar email de verificação
    
    DESCRIÇÃO:
    - Reenvia email de verificação para usuário não verificado
    - Gera novo token com validade de 24 horas
    - Útil se o email anterior expirou ou foi perdido
    
    PARÂMETROS (Body JSON):
    - email: Email do usuário (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de reenvio
    """
    return auth_controller.resend_verification()

@auth_routes.route('/login', methods=['POST'], strict_slashes=False)
def login():
    """
    POST /api/auth/login - Login com JWT
    
    DESCRIÇÃO:
    - Autentica usuário com email/senha
    - Retorna JWT token com validade de 7 dias
    - Verifica se email foi verificado
    - Registra session para controle de múltiplos dispositivos
    
    PARÂMETROS (Body JSON):
    - email: Email do usuário (obrigatório)
    - password: Senha do usuário (obrigatório)
    - device_info: Informações do dispositivo (opcional)
    
    RETORNA:
    - success: true/false
    - access_token: JWT token para autenticação
    - user: Dados básicos do usuário
    - subscription: Dados da assinatura atual
    - expires_at: Data de expiração do token
    """
    return auth_controller.login()

@auth_routes.route('/logout', methods=['POST'], strict_slashes=False)
def logout():
    """
    POST /api/auth/logout - Logout (invalida token atual)
    
    DESCRIÇÃO:
    - Invalida o token JWT atual
    - Remove session específica do banco
    - Não afeta outros dispositivos por padrão
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    PARÂMETROS (Body JSON):
    - logout_all_devices: true para invalidar todos tokens (opcional)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de logout
    """
    return auth_controller.logout()

@auth_routes.route('/logout-all', methods=['POST'], strict_slashes=False)
def logout_all():
    """
    POST /api/auth/logout-all - Logout de todos dispositivos
    
    DESCRIÇÃO:
    - Invalida TODOS os tokens do usuário
    - Remove todas as sessions ativas
    - Força re-login em todos dispositivos
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de logout global
    - devices_count: Quantidade de dispositivos desconectados
    """
    return auth_controller.logout_all()

@auth_routes.route('/forgot-password', methods=['POST'], strict_slashes=False)
def forgot_password():
    """
    POST /api/auth/forgot-password - Solicitar reset de senha
    
    DESCRIÇÃO:
    - Envia email com token para reset de senha
    - Token válido por 1 hora
    - Funciona apenas para contas verificadas
    
    PARÂMETROS (Body JSON):
    - email: Email do usuário (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de envio
    """
    return auth_controller.forgot_password()

@auth_routes.route('/verify-password-code', methods=['POST'], strict_slashes=False)
def verify_password_code():
    """
    POST /api/auth/verify-password-code - Verificar código de reset de senha
    
    DESCRIÇÃO:
    - Verifica se o código de 6 dígitos enviado ao email é válido e não expirou.
    - Não redefine a senha, apenas valida o código.
    
    PARÂMETROS (Body JSON):
    - email: Email do usuário (obrigatório)
    - code: Código de 6 dígitos recebido por email (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de validade do código
    - data: {'verified': true}
    """
    return auth_controller.verify_password_code()

@auth_routes.route('/reset-password', methods=['POST'], strict_slashes=False)
def reset_password():
    """
    POST /api/auth/reset-password - Redefinir senha com token
    
    DESCRIÇÃO:
    - Redefine senha usando token recebido por email
    - Invalida TODOS os tokens existentes (logout forçado)
    - Token consumido após uso
    
    PARÂMETROS (Body JSON):
    - token: Token de reset recebido por email (obrigatório)
    - new_password: Nova senha mínimo 8 caracteres (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de alteração
    - redirect_to: URL do frontend para novo login
    """
    return auth_controller.reset_password()

# ====== ROTAS DE USUÁRIO AUTENTICADO ======

@auth_routes.route('/me', methods=['GET'], strict_slashes=False)
def get_profile():
    """
    GET /api/auth/me - Dados do usuário logado
    
    DESCRIÇÃO:
    - Retorna dados completos do usuário autenticado
    - Inclui informações da assinatura e limites
    - Usado para popular perfil e verificar permissões
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    RETORNA:
    - user: Dados do usuário (sem senha)
    - subscription: Plano atual e limites
    - usage: Uso atual do mês (empresas, matches, queries RAG)
    - companies: Lista de empresas do usuário
    """
    return auth_controller.get_profile()

@auth_routes.route('/me', methods=['PUT'], strict_slashes=False)
def update_profile():
    """
    PUT /api/auth/me - Atualizar dados do usuário
    
    DESCRIÇÃO:
    - Atualiza nome e outras informações básicas
    - Email não pode ser alterado (seria necessário re-verificação)
    - Senha é alterada via endpoint específico
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    PARÂMETROS (Body JSON):
    - name: Novo nome do usuário (opcional)
    
    RETORNA:
    - success: true/false
    - user: Dados atualizados do usuário
    """
    return auth_controller.update_profile()

@auth_routes.route('/change-password', methods=['POST'], strict_slashes=False)
def change_password():
    """
    POST /api/auth/change-password - Alterar senha logado
    
    DESCRIÇÃO:
    - Altera senha do usuário logado
    - Requer senha atual para confirmação
    - Invalida TODOS os outros tokens (mantém o atual)
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    PARÂMETROS (Body JSON):
    - current_password: Senha atual (obrigatório)
    - new_password: Nova senha mínimo 8 caracteres (obrigatório)
    
    RETORNA:
    - success: true/false
    - message: Confirmação de alteração
    """
    return auth_controller.change_password()

# ====== ROTAS DE VERIFICAÇÃO ======

@auth_routes.route('/verify-token', methods=['POST'], strict_slashes=False)
def verify_token():
    """
    POST /api/auth/verify-token - Verificar validade do token
    
    DESCRIÇÃO:
    - Verifica se token JWT é válido e não revogado
    - Usado pelo frontend para verificar autenticação
    - Atualiza last_used_at da session
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    RETORNA:
    - valid: true/false
    - user_id: ID do usuário do token
    - expires_at: Data de expiração do token
    """
    return auth_controller.verify_token()

@auth_routes.route('/refresh-token', methods=['POST'], strict_slashes=False)
def refresh_token():
    """
    POST /api/auth/refresh-token - Renovar token JWT
    
    DESCRIÇÃO:
    - Gera novo token JWT com validade estendida
    - Invalida o token anterior
    - Usado para manter usuário logado sem re-login
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    RETORNA:
    - success: true/false
    - access_token: Novo JWT token
    - expires_at: Nova data de expiração
    """
    return auth_controller.refresh_token()

# ====== ROTAS ADMINISTRATIVAS ======

@auth_routes.route('/sessions', methods=['GET'], strict_slashes=False)
def get_user_sessions():
    """
    GET /api/auth/sessions - Listar sessões ativas do usuário
    
    DESCRIÇÃO:
    - Lista todas as sessões ativas do usuário
    - Mostra dispositivos, IPs e última atividade
    - Usado para gerenciar segurança da conta
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    RETORNA:
    - sessions: Lista de sessões ativas
    - current_session: ID da sessão atual
    - total_sessions: Quantidade total de sessões
    """
    return auth_controller.get_user_sessions()

@auth_routes.route('/sessions/<session_id>', methods=['DELETE'], strict_slashes=False)
def revoke_session(session_id):
    """
    DELETE /api/auth/sessions/<session_id> - Revogar sessão específica
    
    DESCRIÇÃO:
    - Revoga uma sessão específica (logout remoto)
    - Usado para desconectar dispositivo perdido/roubado
    - Não pode revogar a própria sessão atual
    
    HEADERS:
    - Authorization: Bearer <token> (obrigatório)
    
    PARÂMETROS:
    - session_id: ID da sessão a ser revogada
    
    RETORNA:
    - success: true/false
    - message: Confirmação de revogação
    """
    return auth_controller.revoke_session(session_id) 