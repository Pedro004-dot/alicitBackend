"""
Routes para matches - endpoints HTTP
Sistema multi-tenant: rotas autenticadas para usuários e públicas para admin
"""
from flask import Blueprint
from controllers.match_controller import MatchController

# Criar blueprint com url_prefix correto
match_routes = Blueprint('matches', __name__, url_prefix='/api/matches')

# Instanciar controller
match_controller = MatchController()

# ====== ROTAS AUTENTICADAS (MULTI-TENANT) ======

@match_routes.route('/', methods=['GET'])
def get_user_matches():
    """
    GET /api/matches - Listar matches das empresas do usuário logado
    
    DESCRIÇÃO:
    - Lista apenas os matches das empresas que pertencem ao usuário autenticado
    - Implementa isolamento de dados por usuário (multi-tenancy)
    - Usado pelo frontend para popular a tabela de matches do usuário
    
    PARÂMETROS (Query):
    - limit: Itens por página (opcional, padrão: 50)
    
    AUTENTICAÇÃO: Bearer Token obrigatório
    
    RETORNA:
    - Array de matches apenas das empresas do usuário
    - Score de compatibilidade (0.0 a 1.0)
    - Dados completos da empresa e licitação
    """
    return match_controller.get_user_matches()

@match_routes.route('/<match_id>', methods=['GET'])
def get_match_by_id(match_id):
    """
    GET /api/matches/{id} - Buscar match específico do usuário
    
    DESCRIÇÃO:
    - Busca um match específico apenas se a empresa pertencer ao usuário
    - Garante isolamento de dados por usuário
    
    AUTENTICAÇÃO: Bearer Token obrigatório
    
    RETORNA:
    - Dados completos do match se pertencer ao usuário
    - 404 se não encontrado ou não pertencer ao usuário
    """
    return match_controller.get_match_by_id(match_id)

@match_routes.route('/by-company', methods=['GET'])
def get_user_matches_by_company():
    """
    GET /api/matches/by-company - Matches agrupados por empresa do usuário
    
    DESCRIÇÃO:
    - Agrupa matches apenas das empresas do usuário autenticado
    - Usado pelo frontend para estatísticas de empresas do usuário
    
    AUTENTICAÇÃO: Bearer Token obrigatório
    
    RETORNA:
    - Array de empresas do usuário com seus matches agregados
    - Estatísticas: total de matches, score médio, melhor match
    """
    return match_controller.get_matches_by_company()

@match_routes.route('/company/<company_id>', methods=['GET'])
def get_matches_by_company_id(company_id):
    """
    GET /api/matches/company/{company_id} - Matches de empresa específica
    
    DESCRIÇÃO:
    - Lista matches de uma empresa específica do usuário
    - Valida se a empresa pertence ao usuário autenticado
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 20)
    
    AUTENTICAÇÃO: Bearer Token obrigatório
    
    RETORNA:
    - Array de matches da empresa se pertencer ao usuário
    - 404 se empresa não encontrada ou não pertencer ao usuário
    """
    return match_controller.get_matches_by_company_id(company_id)

# ====== ROTAS PÚBLICAS/ADMINISTRATIVAS ======

@match_routes.route('/all', methods=['GET'])
def get_all_matches():
    """
    GET /api/matches/all - Listar todos os matches (admin/público)
    
    DESCRIÇÃO:
    - Lista todos os matches do sistema sem filtro de usuário
    - Usado para administração e relatórios globais
    
    PARÂMETROS (Query):
    - limit: Itens por página (opcional, padrão: 50)
    
    RETORNA:
    - Array de todos os matches do sistema
    """
    return match_controller.get_all_matches()

@match_routes.route('/recent', methods=['GET', 'POST'])
def get_recent_matches():
    """
    GET /api/matches/recent - Matches recentes com validação LLM opcional (público)
    
    DESCRIÇÃO:
    - Lista matches recentes com opção de reavaliação LLM
    - Permite especificar período de busca customizável
    - Validação LLM reavaliar e/ou atualizar matches existentes
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 10)
    - days_back: Quantos dias atrás buscar matches (opcional, padrão: 7)
    - enable_llm: Ativar validação LLM ('true'/'false', padrão: 'false')
    - update_existing: Atualizar scores dos matches com LLM ('true'/'false', padrão: 'false')
    
    EXEMPLOS DE USO:
    - GET /api/matches/recent?limit=20&days_back=30
      (busca 20 matches dos últimos 30 dias sem LLM)
    
    - GET /api/matches/recent?days_back=14&enable_llm=true
      (reavalia matches dos últimos 14 dias com LLM, sem atualizar)
    
    - GET /api/matches/recent?enable_llm=true&update_existing=true
      (reavalia e atualiza matches dos últimos 7 dias com LLM)
    
    RETORNA:
    - Array de matches com dados completos
    - Estatísticas de validação LLM (se ativada)
    - Informações sobre matches atualizados (se update_existing=true)
    
    RESPOSTA COM LLM:
    {
        "success": true,
        "data": [...matches com llm_validation...],
        "total": 15,
        "llm_validation": {
            "enabled": true,
            "validated": 15,
            "approved": 12,
            "rejected": 3,
            "updated": 8
        },
        "filters": {...}
    }
    
    RESPOSTA SEM LLM:
    {
        "success": true,
        "data": [...matches normais...],
        "total": 15,
        "llm_validation": {
            "enabled": false,
            "message": "Use enable_llm=true para ativar validação LLM"
        },
        "filters": {...}
    }
    """
    return match_controller.get_recent_matches()

@match_routes.route('/statistics', methods=['GET'])
def get_matches_statistics():
    """
    GET /api/matches/statistics - Estatísticas gerais de matches (público)
    
    DESCRIÇÃO:
    - Calcula métricas abrangentes sobre todos os matches
    - Usado para dashboards administrativos e relatórios globais
    
    RETORNA:
    - Total de matches e distribuição por score
    - Empresas mais ativas e licitações mais procuradas
    - Performance do algoritmo de matching
    """
    return match_controller.get_matches_statistics()

@match_routes.route('/grouped', methods=['GET'])
def get_matches_grouped():
    """
    GET /api/matches/grouped - Correspondências agrupadas (público)
    
    DESCRIÇÃO:
    - Retorna matches organizados em diferentes agrupamentos
    - Usado para análises administrativas e relatórios
    
    RETORNA:
    - Objeto com matches organizados por critério
    - Estatísticas agregadas por grupo
    """
    return match_controller.get_matches_grouped()

# ====== ROTAS ESPECÍFICAS (MANTIDAS PARA COMPATIBILIDADE) ======

@match_routes.route('/bid/<bid_id>', methods=['GET'])
def get_matches_by_bid_id(bid_id):
    """
    GET /api/matches/bid/{bid_id} - Matches de uma licitação específica
    
    DESCRIÇÃO:
    - Lista todos os matches de uma licitação específica
    - Rota pública para análise de competitividade
    
    RETORNA:
    - Array de matches da licitação específica
    """
    return match_controller.get_matches_by_bid_id(bid_id)

@match_routes.route('/score', methods=['GET'])
def get_matches_by_score_range():
    """
    GET /api/matches/score - Matches por faixa de score
    
    DESCRIÇÃO:
    - Busca matches dentro de uma faixa específica de score
    
    PARÂMETROS (Query):
    - min_score: Score mínimo (padrão: 0.5)
    - max_score: Score máximo (padrão: 1.0)
    
    RETORNA:
    - Array de matches na faixa de score especificada
    """
    return match_controller.get_matches_by_score_range()

@match_routes.route('/high-quality', methods=['GET'])
def get_high_quality_matches():
    """
    GET /api/matches/high-quality - Matches de alta qualidade
    
    DESCRIÇÃO:
    - Busca matches com score alto (>= 0.8 por padrão)
    
    PARÂMETROS (Query):
    - min_score: Score mínimo (padrão: 0.8)
    
    RETORNA:
    - Array de matches de alta qualidade
    """
    return match_controller.get_high_quality_matches()

@match_routes.route('/reevaluate-bids', methods=['POST'])
def reevaluate_bids_by_date():
    """
    POST /api/matches/reevaluate-bids - Reavaliar licitações de uma data específica
    
    DESCRIÇÃO:
    - Reavaliar todas as licitações de uma data específica contra empresas cadastradas
    - Executa o processo completo de matching com validação LLM
    - Salva novos matches aprovados pelo LLM no banco de dados
    
    BODY (JSON):
    - data: Data no formato YYYY-MM-DD (obrigatório)
    - enable_llm: Ativar validação LLM (opcional, padrão: true)
    - limit: Limite de licitações para processar (opcional, padrão: 50)
    
    EXEMPLO DE BODY:
    {
        "data": "2025-06-25",
        "enable_llm": true,
        "limit": 30
    }
    
    RETORNA:
    - Array de novos matches encontrados e salvos
    - Estatísticas do processamento (licitações encontradas, processadas)
    - Informações de validação LLM (aprovados, rejeitados)
    - Detalhes completos das licitações e empresas matched
    
    RESPOSTA:
    {
        "success": true,
        "data": [...matches...],
        "total_matches": 15,
        "processing_info": {
            "target_date": "2025-06-25",
            "total_bids_found": 14,
            "total_bids_processed": 14,
            "enable_llm": true
        },
        "llm_validation": {
            "enabled": true,
            "validated": 45,
            "approved": 15,
            "rejected": 30
        },
        "message": "Processadas 14 licitações da data 2025-06-25"
    }
    """
    return match_controller.reevaluate_bids_by_date()

 