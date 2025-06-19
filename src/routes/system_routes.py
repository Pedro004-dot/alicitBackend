"""
Rotas para operações de sistema
"""
from flask import Blueprint
from controllers.system_controller import SystemController

# Criar blueprint para sistema
system_routes = Blueprint('system', __name__)

# Instanciar controller
controller = SystemController()

# ====== ROTAS DE SISTEMA ======

@system_routes.route('/api/health', methods=['GET'])
def health_check():
    """
    GET /api/health - Health check do sistema
    
    DESCRIÇÃO:
    - Verificação geral de saúde de toda a aplicação
    - Testa conectividade com banco de dados, APIs externas
    - Usado para monitoramento automático e alertas
    
    RETORNA:
    - Status geral do sistema (healthy/degraded/unhealthy)
    - Detalhes de cada componente (database, supabase, etc.)
    - Timestamp da verificação e tempo de resposta
    - Versão da aplicação e informações do ambiente
    """
    return controller.health_check()

@system_routes.route('/api/status', methods=['GET'])
def get_system_status():
    """
    GET /api/status - Status geral do sistema
    
    DESCRIÇÃO:
    - Informações detalhadas sobre o estado atual do sistema
    - Inclui estatísticas de uso, performance e recursos
    - Usado para dashboards administrativos
    
    RETORNA:
    - Estatísticas de uso da aplicação
    - Informações sobre processos em execução
    - Métricas de performance e memória
    - Status dos serviços dependentes
    """
    return controller.get_system_status()

@system_routes.route('/api/status/daily-bids', methods=['GET'])
def get_daily_bids_status():
    """
    GET /api/status/daily-bids - Status da busca diária
    
    DESCRIÇÃO:
    - Monitora o processo automático de busca diária de licitações
    - Usado pelo frontend para mostrar status em tempo real
    - Inclui informações sobre última execução e próxima
    
    RETORNA:
    - Status atual do processo (running/idle/error)
    - Timestamp da última execução bem-sucedida
    - Quantidade de licitações encontradas na última busca
    - Próxima execução programada
    """
    return controller.get_daily_bids_status()

@system_routes.route('/api/status/reevaluate', methods=['GET'])
def get_reevaluate_status():
    """
    GET /api/status/reevaluate - Status da reavaliação
    
    DESCRIÇÃO:
    - Monitora o processo de reavaliação de matches existentes
    - Usado pelo frontend para acompanhar progresso em tempo real
    - Mostra estatísticas de reprocessamento de dados
    
    RETORNA:
    - Status atual da reavaliação (running/idle/error)
    - Progresso atual (% concluído, registros processados)
    - Timestamp de início e estimativa de conclusão
    - Estatísticas de matches atualizados
    """
    return controller.get_reevaluate_status()

@system_routes.route('/api/config/options', methods=['GET'])
def get_config_options():
    """
    GET /api/config/options - Opções de configuração do sistema
    
    DESCRIÇÃO:
    - Lista todas as configurações disponíveis do sistema
    - Usado para interface administrativa de configuração
    - Inclui valores atuais e opções disponíveis
    
    RETORNA:
    - Configurações de busca automática (frequência, filtros)
    - Parâmetros do algoritmo de matching
    - Configurações de notificações e alertas
    - Limites de API e timeouts
    """
    return controller.get_config_options()

@system_routes.route('/api/search-new-bids', methods=['POST'], strict_slashes=False)
def search_new_bids():
    """
    POST /api/search-new-bids - Iniciar busca de novas licitações
    
    DESCRIÇÃO:
    - Inicia manualmente o processo de busca de novas licitações
    - Usado pelo frontend no botão "Buscar Novas Licitações"
    - Processo assíncrono que roda em background
    
    PARÂMETROS (Body JSON):
    - force: Forçar nova busca mesmo se já executada hoje
    - filters: Filtros específicos para a busca (opcional)
    - limit: Limite de registros a buscar (opcional)
    
    RETORNA:
    - Confirmação de início do processo
    - ID do processo para acompanhamento
    - Estimativa de tempo de execução
    """
    return controller.search_new_bids()

@system_routes.route('/api/reevaluate-bids', methods=['POST'], strict_slashes=False)
def reevaluate_bids():
    """
    POST /api/reevaluate-bids - Reavaliação de licitações existentes
    
    DESCRIÇÃO:
    - Inicia processo de reavaliação de matches existentes
    - Usado pelo frontend no botão "Reavaliar Matches"
    - Recalcula scores de compatibilidade com novos critérios
    
    PARÂMETROS (Body JSON):
    - company_ids: IDs específicos de empresas (opcional)
    - bid_ids: IDs específicos de licitações (opcional)
    - recalculate_all: Reprocessar todos os matches
    
    RETORNA:
    - Confirmação de início da reavaliação
    - ID do processo para monitoramento
    - Quantidade estimada de registros a processar
    """
    return controller.reevaluate_bids()

# Blueprint para exposição
def register_system_routes(app):
    """
    FUNÇÃO: register_system_routes - Registrar rotas de sistema no app Flask
    
    DESCRIÇÃO:
    - Função utilitária para registrar todas as rotas de sistema
    - Inclui logging detalhado dos endpoints registrados
    - Usado durante a inicialização da aplicação
    
    PARÂMETROS:
    - app: Instância do Flask para registrar as rotas
    
    FUNCIONALIDADE:
    - Registra o blueprint system_routes
    - Gera logs informativos sobre os endpoints
    - Confirma sucesso do registro
    """
    app.register_blueprint(system_routes)
    
    # Log dos endpoints registrados
    import logging
    logger = logging.getLogger(__name__)
    logger.info("✅ Sistema: 7 endpoints registrados")
    logger.info("  - GET /api/health (health check)")
    logger.info("  - GET /api/status (status geral)")
    logger.info("  - GET /api/status/daily-bids (status busca)")
    logger.info("  - GET /api/status/reevaluate (status reavaliação)")
    logger.info("  - GET /api/config/options (opções config)")
    logger.info("  - POST /api/search-new-bids (buscar licitações)")
    logger.info("  - POST /api/reevaluate-bids (reavaliar licitações)") 