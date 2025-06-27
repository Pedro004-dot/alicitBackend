"""
Rotas para Debugging e Análise de Dados de Licitações
Endpoints dedicados para identificar inconsistências e problemas
"""
from flask import Blueprint, jsonify
from controllers.data_analysis_controller import DataAnalysisController

# Criar blueprint para rotas de debug
debug_bp = Blueprint('debug', __name__, url_prefix='/api/debug')

# Instanciar controller
data_analysis_controller = DataAnalysisController()

@debug_bp.route('/test-consistency', methods=['GET'])
def test_licitacao_consistency():
    """
    Testa consistência de dados de uma licitação específica
    
    Query Params:
    - pncp_id: ID da licitação no PNCP
    
    Exemplo: GET /api/debug/test-consistency?pncp_id=08584229000122-1-000013/2025
    """
    result = data_analysis_controller.test_licitacao_data_consistency()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/batch-consistency', methods=['POST'])
def analyze_batch_consistency():
    """
    Analisa consistência de um lote de licitações
    
    Body JSON:
    {
        "pncp_ids": ["08584229000122-1-000013/2025", "outro-id/2025"]
    }
    """
    result = data_analysis_controller.analyze_batch_consistency()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/enrich-licitacao', methods=['POST'])
def enrich_licitacao():
    """
    Enriquece uma licitação com dados detalhados da API
    
    Body JSON:
    {
        "licitacao": {
            "numeroControlePNCP": "08584229000122-1-000013/2025",
            "objetoCompra": "...",
            // outros campos da licitação
        }
    }
    """
    result = data_analysis_controller.enrich_licitacao_with_details()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/consistency-report', methods=['GET'])
def get_consistency_report():
    """
    Retorna relatório de consistência atual
    
    Exemplo: GET /api/debug/consistency-report
    """
    result = data_analysis_controller.get_data_consistency_report()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/api-responses', methods=['GET'])
def debug_api_responses():
    """
    Debug detalhado das respostas da API do PNCP
    
    Query Params:
    - pncp_id: ID da licitação no PNCP
    
    Exemplo: GET /api/debug/api-responses?pncp_id=08584229000122-1-000013/2025
    """
    result = data_analysis_controller.debug_api_responses()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/compare-data', methods=['POST'])
def compare_search_vs_details():
    """
    Compara dados de busca vs detalhes para identificar inconsistências
    
    Body JSON:
    {
        "search_data": {
            "numeroControlePNCP": "...",
            "objetoCompra": "...",
            // dados vindos da API de busca
        },
        "detail_data": {
            "numeroControlePNCP": "...",
            "objetoCompra": "...",
            // dados vindos da API de detalhes
        }
    }
    """
    result = data_analysis_controller.compare_search_vs_details()
    
    if isinstance(result, tuple):
        return jsonify(result[0]), result[1]
    return jsonify(result)

@debug_bp.route('/health', methods=['GET'])
def debug_health():
    """
    Health check para as funcionalidades de debug
    """
    try:
        return jsonify({
            'success': True,
            'message': 'Sistema de debug funcionando corretamente',
            'available_endpoints': [
                'GET /api/debug/test-consistency?pncp_id=...',
                'POST /api/debug/batch-consistency',
                'POST /api/debug/enrich-licitacao',
                'GET /api/debug/consistency-report',
                'GET /api/debug/api-responses?pncp_id=...',
                'POST /api/debug/compare-data',
                'GET /api/debug/health'
            ]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro no sistema de debug: {str(e)}'
        }), 500 