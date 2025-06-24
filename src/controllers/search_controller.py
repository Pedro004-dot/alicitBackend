"""
Search Controller
Controller para busca unificada (Local + PNCP)
Segue padrão: Controller -> Service -> Repository
"""
import logging
from flask import request, jsonify
from typing import Dict, Any, Tuple
from services.search_service import SearchService
from middleware.error_handler import log_endpoint_access

logger = logging.getLogger(__name__)

class SearchController:
    """
    Controller para busca unificada
    PADRONIZADO: Segue padrão Controller -> Service
    """
    
    def __init__(self):
        self.search_service = SearchService()
    
    @log_endpoint_access
    def unified_search(self) -> Tuple[Dict[str, Any], int]:
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
        """
        try:
            data = request.get_json()
            
            if not data or not data.get('keywords'):
                return jsonify({
                    'success': False,
                    'message': 'Palavras-chave são obrigatórias'
                }), 400
            
            # Extrair parâmetros
            keywords = data['keywords']
            search_pncp = data.get('search_pncp', True)
            filters = data.get('filters', {})
            pncp_options = data.get('pncp_options', {})
            
            logger.info(f"🔍 Iniciando busca unificada para: {keywords}")
            
            # Delegar para service
            result = self.search_service.perform_unified_search(
                keywords=keywords,
                search_pncp=search_pncp,
                filters=filters,
                pncp_options=pncp_options
            )
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result['data'],
                    'message': f"Busca realizada: {result['data']['summary']['total_combined']} resultados"
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400
                
        except Exception as e:
            logger.error(f"Erro no controller de busca: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    @log_endpoint_access
    def get_search_suggestions(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/search/suggestions - Sugestões de busca
        
        DESCRIÇÃO:
        - Retorna sugestões de palavras-chave baseadas em buscas populares
        - Análise de objetos de licitação mais comuns
        """
        try:
            suggestions = self.search_service.get_search_suggestions()
            
            return jsonify({
                'success': True,
                'data': suggestions,
                'message': 'Sugestões carregadas com sucesso'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao buscar sugestões: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro ao carregar sugestões: {str(e)}'
            }), 500 