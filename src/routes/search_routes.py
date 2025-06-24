"""
Rotas unificadas de busca - Combina busca local e PNCP
REFATORADO: Agora segue padrão clean code com controller
"""
from flask import Blueprint
from controllers.search_controller import SearchController

# Criar blueprint para busca unificada
search_routes = Blueprint('search', __name__, url_prefix='/api/search')

# Instanciar controller
controller = SearchController()

@search_routes.route('/unified', methods=['POST'])
def unified_search():
    """
    POST /api/search/unified - Busca unificada (Local + PNCP)
    
    DESCRIÇÃO:
    - Busca inteligente que combina resultados do banco local e API PNCP
    - Primeiro busca no banco local (mais rápido)
    - Opcionalmente busca no PNCP para mais resultados
    - Retorna resultados combinados com indicador de origem
    
    BODY JSON:
    {
        "keywords": "computadores notebooks",           // obrigatório
        "search_pncp": true,                           // opcional - se deve buscar também no PNCP
        "filters": {                                   // filtros opcionais
            "uf": "MG",
            "valor_min": 10000,
            "valor_max": 500000,
            "status": "ativa",
            "modalidades": ["pregao_eletronico"]
        },
        "pncp_options": {                             // opções específicas para busca PNCP
            "max_pages": 3,
            "include_items": true,
            "save_results": true
        }
    }
    
    RETORNA:
    {
        "success": true,
        "data": {
            "local_results": [...],        // resultados do banco local
            "pncp_results": [...],         // resultados do PNCP (se solicitado)
            "combined_results": [...],     // todos os resultados combinados
            "summary": {
                "total_local": 15,
                "total_pncp": 8,
                "total_combined": 23,
                "search_time_ms": 1250
            }
        }
    }
    """
    return controller.unified_search()

@search_routes.route('/suggestions', methods=['GET'])
def get_search_suggestions():
    """
    GET /api/search/suggestions - Sugestões de busca
    
    DESCRIÇÃO:
    - Retorna sugestões de palavras-chave baseadas em buscas populares
    - Análise de objetos de licitação mais comuns
    
    PARÂMETROS (Query):
    - Nenhum parâmetro necessário
    
    RETORNA:
    - Sugestões categorizadas por tipo
    - Palavras-chave populares, tecnologia, serviços, materiais
    """
    return controller.get_search_suggestions() 