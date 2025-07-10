"""
Controller para Licitações (Bids)
Substitui os endpoints de licitação do api.py
"""
from flask import jsonify, request
import logging
from typing import Dict, Any, Tuple
from services.bid_service import BidService
from middleware.error_handler import log_endpoint_access
from exceptions.api_exceptions import ValidationError, NotFoundError, DatabaseError
from supabase import create_client, Client
import os
import re
from ._id_converter import convert_pncp_to_uuid

logger = logging.getLogger(__name__)

class BidController:
    """Controller para endpoints de licitações"""
    
    def __init__(self):
        self.bid_service = BidService()
    
    @log_endpoint_access
    def get_bids(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids
        Migração do endpoint get_bids() do api.py linha 77-101
        """
        try:
            # Obter parâmetro limit da query string
            limit = request.args.get('limit', type=int)
            
            # Se limit=0, passar None para buscar todas as licitações
            if limit == 0:
                limit = None
            
            bids, message = self.bid_service.get_all_bids(limit=limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitações: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar licitações do banco'
            }), 500

    def get_all_bids(self) -> Tuple[Dict[str, Any], int]:
        """Alias para get_bids() - compatibilidade com rotas"""
        return self.get_bids()
    
    @log_endpoint_access
    def get_bid_detail(self, pncp_id: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/<pncp_id>
        Migração do endpoint get_bid_detail() do api.py linha 1040-1100
        """
        try:
            bid, message = self.bid_service.get_bid_by_pncp_id(pncp_id, include_items=True)
            
            if not bid:
                return jsonify({
                    'success': False,
                    'message': message
                }), 404
            
            return jsonify({
                'success': True,
                'data': bid,
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitação {pncp_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar detalhes da licitação'
            }), 500
    
    @log_endpoint_access
    def get_bid_detail_by_query(self) -> Tuple[Dict[str, Any], int]:
        """GET /api/bids/detail?pncp_id=<id> - Obter detalhes de licitação específica por query parameter"""
        try:
            pncp_id = request.args.get('pncp_id')
            if not pncp_id:
                return jsonify({'success': False, 'message': 'pncp_id não fornecido'}), 400

            result = self.bid_service.get_bid_by_pncp_id(pncp_id)

            if result:
                return jsonify({'success': True, 'data': result}), 200
            else:
                return jsonify({'success': False, 'message': 'Licitação não encontrada'}), 404

        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes da licitação: {e}", exc_info=True)
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @log_endpoint_access
    def get_bid_items(self, pncp_id: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/<pncp_id>/items
        Migração do endpoint get_bid_items() do api.py linha 1164-1218
        """
        try:
            items, message = self.bid_service.get_bid_items(pncp_id)
            
            if 'não encontrada' in message:
                return jsonify({
                    'success': False,
                    'message': message
                }), 404
            
            return jsonify({
                'success': True,
                'data': items,
                'total': len(items),
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar itens da licitação {pncp_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar itens da licitação'
            }), 500
    
    @log_endpoint_access
    def get_bid_items_by_query(self) -> Tuple[Dict[str, Any], int]:
        """GET /api/bids/items?pncp_id=<id> - Buscar itens de licitação específica por query parameter"""
        try:
            licitacao_data = None
            # Para POST, os dados da licitação vêm no corpo
            if request.method == 'POST':
                licitacao_data = request.get_json()
                if not licitacao_data:
                    return jsonify({'success': False, 'message': 'Corpo da requisição POST está vazio.'}), 400
            
            # O pncp_id é sempre esperado na query string para identificar o recurso
            pncp_id = request.args.get('pncp_id')
            if not pncp_id:
                return jsonify({'success': False, 'message': 'Parâmetro pncp_id é obrigatório'}), 400
            
            logger.info(f"🔍 Buscando itens da licitação PNCP: {pncp_id} (Método: {request.method})")
            
            # Chamar o serviço, passando os dados da licitação se for um POST
            result = self.bid_service.get_bid_items(pncp_id, licitacao_data=licitacao_data)
            
            if not result.get('success'):
                return jsonify(result), 404
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens da licitação: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar itens da licitação'
            }), 500
    
    @log_endpoint_access
    def get_bids_detailed(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/detailed?page=<page>&limit=<limit>&uf=<uf>&modalidade_id=<id>&status=<status>
        Migração do endpoint get_bids_detailed() do api.py linha 1276-1355
        """
        try:
            # Obter parâmetros de query
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 50, type=int)
            uf = request.args.get('uf')
            modalidade_id = request.args.get('modalidade_id', type=int)
            status = request.args.get('status')
            
            # Montar filtros
            filters = {}
            if uf:
                filters['uf'] = uf
            if modalidade_id:
                filters['modalidade_id'] = modalidade_id
            if status:
                filters['status'] = status
            
            # Buscar licitações com filtros
            bids = self.bid_service.search_bids(filters, limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'page': page,
                'limit': limit,
                'message': f'{len(bids)} licitações encontradas'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitações detalhadas: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar licitações detalhadas'
            }), 500
    
    def get_detailed_bids(self) -> Tuple[Dict[str, Any], int]:
        """Alias para get_bids_detailed() - compatibilidade com rotas"""
        return self.get_bids_detailed()
    
    @log_endpoint_access
    def get_recent_bids(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/recent
        Migração do endpoint get_recent_bids() do api.py linha 982-1036
        """
        try:
            limit = request.args.get('limit', 20, type=int)
            bids, message = self.bid_service.get_recent_bids(limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitações recentes: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar licitações recentes'
            }), 500
    
    @log_endpoint_access
    def get_bids_by_status(self, status: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/status/<status>
        Buscar licitações por status específico
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            filters = {'status': status}
            bids = self.bid_service.search_bids(filters, limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': f'{len(bids)} licitações com status "{status}" encontradas'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitações por status {status}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar licitações com status {status}'
            }), 500

    @log_endpoint_access
    def get_active_bids(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/active - Buscar licitações ativas (ainda abertas para propostas)
        """
        try:
            from datetime import datetime
            
            # Obter parâmetros da query
            after_date = request.args.get('after')
            limit = request.args.get('limit', type=int)
            
            # Se limit=0, passar None para buscar todas
            if limit == 0:
                limit = None
            
            # Se não especificar data, usar hoje
            if not after_date:
                after_date = datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"🔍 Buscando licitações ativas após {after_date}, limite: {limit or 'sem limite'}")
            
            # Usar o service para buscar licitações ativas
            active_bids, message = self.bid_service.get_active_bids(after_date, limit)
            
            return jsonify({
                'success': True,
                'data': active_bids,
                'total': len(active_bids),
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar licitações ativas: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar licitações ativas'
            }), 500
    
    @log_endpoint_access
    def get_bids_by_uf(self, uf: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/uf/<uf>
        Buscar licitações por UF específica
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            bids = self.bid_service.get_bids_by_state(uf.upper(), limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': f'{len(bids)} licitações do estado {uf.upper()} encontradas'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar licitações do estado {uf}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar licitações do estado {uf}'
            }), 500
    
    @log_endpoint_access
    def get_bid_statistics(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/statistics
        Obter estatísticas das licitações
        """
        try:
            result = self.bid_service.get_bid_statistics()
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'data': result['data'],
                    'message': result.get('message', 'Estatísticas calculadas com sucesso')
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', 'Erro ao calcular estatísticas')
                }), 500
                
        except Exception as e:
            logger.error(f"Erro no controller ao calcular estatísticas: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao calcular estatísticas'
            }), 500

    # ===== NOVOS ENDPOINTS PARA FUNÇÕES DE NEGÓCIO =====
    
    @log_endpoint_access
    def get_srp_opportunities(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/srp-opportunities
        Buscar oportunidades de Sistema de Registro de Preços (SRP)
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            bids, message = self.bid_service.get_srp_opportunities(limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': message,
                'opportunity_type': 'SRP',
                'description': 'Oportunidades de Sistema de Registro de Preços - válidos por até 1 ano'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar oportunidades SRP: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar oportunidades SRP'
            }), 500
    
    @log_endpoint_access
    def get_active_proposals(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/active-proposals
        Buscar licitações com propostas ainda abertas (timing crítico)
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            bids, message = self.bid_service.get_active_proposals(limit)
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': message,
                'opportunity_type': 'active_proposals',
                'description': 'Licitações com propostas ainda abertas - ação urgente necessária'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar propostas ativas: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar propostas ativas'
            }), 500
    
    @log_endpoint_access
    def get_materials_opportunities(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/materials-opportunities
        Buscar itens de MATERIAL (não serviços) para empresas que fornecem produtos
        """
        try:
            limit = request.args.get('limit', 100, type=int)
            items, message = self.bid_service.get_materials_opportunities(limit)
            
            return jsonify({
                'success': True,
                'data': items,
                'total': len(items),
                'message': message,
                'opportunity_type': 'materials',
                'description': 'Oportunidades de fornecimento de materiais/produtos'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar oportunidades de materiais: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar oportunidades de materiais'
            }), 500
    
    @log_endpoint_access
    def get_services_opportunities(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/services-opportunities
        Buscar itens de SERVIÇO (não materiais) para empresas prestadoras de serviços
        """
        try:
            limit = request.args.get('limit', 100, type=int)
            items, message = self.bid_service.get_services_opportunities(limit)
            
            return jsonify({
                'success': True,
                'data': items,
                'total': len(items),
                'message': message,
                'opportunity_type': 'services',
                'description': 'Oportunidades de prestação de serviços'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar oportunidades de serviços: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar oportunidades de serviços'
            }), 500
    
    @log_endpoint_access
    def get_me_epp_opportunities(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/me-epp-opportunities
        Buscar itens exclusivos para Micro e Pequenas Empresas (ME/EPP)
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            items, message = self.bid_service.get_me_epp_opportunities(limit)
            
            return jsonify({
                'success': True,
                'data': items,
                'total': len(items),
                'message': message,
                'opportunity_type': 'me_epp_exclusive',
                'description': 'Oportunidades EXCLUSIVAS para Micro e Pequenas Empresas'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar oportunidades ME/EPP: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar oportunidades ME/EPP'
            }), 500
    
    @log_endpoint_access
    def search_by_ncm_code(self, ncm_code: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/search-by-ncm/<ncm_code>
        Buscar itens por código NCM específico - muito preciso para empresas especializadas
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            items, message = self.bid_service.search_by_ncm_code(ncm_code, limit)
            
            return jsonify({
                'success': True,
                'data': items,
                'total': len(items),
                'message': message,
                'opportunity_type': 'ncm_specific',
                'ncm_code': ncm_code,
                'description': f'Oportunidades específicas para NCM {ncm_code}'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar por NCM {ncm_code}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar por NCM {ncm_code}'
            }), 500
    
    @log_endpoint_access
    def get_bids_by_disputa_mode(self, mode_id: int) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/disputa-mode/<mode_id>
        Buscar licitações por modo de disputa específico
        """
        try:
            limit = request.args.get('limit', 50, type=int)
            bids, message = self.bid_service.get_bids_by_disputa_mode(mode_id, limit)
            
            mode_names = {
                1: "Aberto",
                2: "Fechado", 
                3: "Aberto-Fechado"
            }
            
            mode_name = mode_names.get(mode_id, f"Modo {mode_id}")
            
            return jsonify({
                'success': True,
                'data': bids,
                'total': len(bids),
                'message': message,
                'opportunity_type': 'disputa_mode',
                'mode_id': mode_id,
                'mode_name': mode_name,
                'description': f'Licitações em modo de disputa {mode_name}'
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar por modo de disputa {mode_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar por modo de disputa {mode_id}'
            }), 500
    
    @log_endpoint_access
    def get_enhanced_statistics(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/enhanced-statistics
        Estatísticas de negócio com análises estratégicas
        """
        try:
            stats, message = self.bid_service.get_enhanced_statistics()
            
            return jsonify({
                'success': True,
                'data': stats,
                'message': message,
                'insights': {
                    'description': 'Análises estratégicas para tomada de decisão',
                    'generated_at': stats.get('generated_at', None)
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Erro no controller ao buscar estatísticas estratégicas: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar estatísticas estratégicas'
            }), 500

    # ===== NOVOS ENDPOINTS PARA PREPARAÇÃO AUTOMÁTICA DE ANÁLISE =====
    
    @log_endpoint_access
    def prepare_analysis(self) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/bids/prepare-analysis - Iniciar preparação automática de análise
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'JSON payload obrigatório'}), 400
            
            licitacao_id = data.get('licitacao_id')
            pncp_id = data.get('pncp_id') # pncp_id é opcional, mas útil para o service
            
            if not licitacao_id:
                return jsonify({'success': False, 'error': 'Parâmetro licitacao_id é obrigatório'}), 400

            # >>> INÍCIO DA CORREÇÃO: LÓGICA DE CONVERSÃO DE ID <<<
            try:
                uuid_licitacao_id = convert_pncp_to_uuid(licitacao_id)
                if not uuid_licitacao_id:
                    return jsonify({'success': False, 'error': f'Licitação não encontrada para o ID fornecido: {licitacao_id}'}), 404
                
                # Usar o UUID convertido daqui em diante
                licitacao_id = uuid_licitacao_id
            except Exception as e:
                 return jsonify({'success': False, 'error': f'Erro ao processar ID: {str(e)}'}), 500
            # >>> FIM DA CORREÇÃO <<<
            
            logger.info(f"🚀 Controller: Iniciando preparação para licitacao_id (UUID): {licitacao_id}")
            
            result, message = self.bid_service.start_document_preparation(licitacao_id, pncp_id)
            
            if result.get('status') == 'error':
                return jsonify({
                    'success': False,
                    'error': result.get('error'),
                    'message': message
                }), 500
            
            return jsonify({
                'success': True,
                'data': result,
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no controller prepare_analysis: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    @log_endpoint_access  
    def get_preparation_status(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/preparation-status?licitacao_id=<id> - Verificar status de preparação
        """
        try:
            licitacao_id = request.args.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'Parâmetro licitacao_id é obrigatório'
                }), 400
            
            # >>> INÍCIO DA CORREÇÃO: LÓGICA DE CONVERSÃO DE ID <<<
            try:
                uuid_licitacao_id = convert_pncp_to_uuid(licitacao_id)
                if not uuid_licitacao_id:
                    return jsonify({'success': False, 'error': f'Licitação não encontrada para o ID fornecido: {licitacao_id}'}), 404
                
                # Usar o UUID convertido daqui em diante
                licitacao_id = uuid_licitacao_id
            except Exception as e:
                 return jsonify({'success': False, 'error': f'Erro ao processar ID: {str(e)}'}), 500
            # >>> FIM DA CORREÇÃO <<<
            
            logger.info(f"📊 Controller: Verificando status para licitacao_id (UUID): {licitacao_id}")
            
            result, message = self.bid_service.get_preparation_status(licitacao_id)
            
            if result.get('status') == 'error':
                return jsonify({
                    'success': False,
                    'error': result.get('error'),
                    'message': message
                }), 500
            
            return jsonify({
                'success': True,
                'data': result,
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no controller get_preparation_status: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    @log_endpoint_access
    def cleanup_preparation(self) -> Tuple[Dict[str, Any], int]:
        """
        DELETE /api/bids/cleanup-preparation?licitacao_id=<id> - Limpar preparação falhada
        """
        try:
            licitacao_id = request.args.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'Parâmetro licitacao_id é obrigatório'
                }), 400
            
            logger.info(f"🧹 Controller: Limpando preparação para {licitacao_id}")
            
            result, message = self.bid_service.cleanup_failed_preparation(licitacao_id)
            
            if result.get('cleanup_status') == 'error':
                return jsonify({
                    'success': False,
                    'error': result.get('error'),
                    'message': message
                }), 500
            
            return jsonify({
                'success': True,
                'data': result,
                'message': message
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no controller cleanup_preparation: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    @log_endpoint_access
    def get_bid_documents(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/bids/documents?licitacao_id=<id>
        Lista os documentos de uma licitação, buscando-os no Supabase Storage.
        """
        try:
            licitacao_id_param = request.args.get('licitacao_id')
            if not licitacao_id_param:
                return jsonify({'success': False, 'error': 'Parâmetro licitacao_id é obrigatório'}), 400

            logger.info(f"🔍 Buscando documentos da licitação: {licitacao_id_param}")

            # >>> INÍCIO DA CORREÇÃO: Converter pncp_id para UUID <<<
            try:
                uuid_licitacao_id = convert_pncp_to_uuid(licitacao_id_param)
            except ValueError as e:
                logger.error(f"❌ Erro ao converter ID '{licitacao_id_param}' para UUID: {e}")
                return jsonify({'success': False, 'error': str(e)}), 404
            # >>> FIM DA CORREÇÃO <<<

            # Inicializar cliente Supabase (a lógica pode variar, ajustar conforme necessário)
            if not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_KEY'):
                logger.error("❌ Variáveis de ambiente SUPABASE não configuradas.")
                return self._return_mock_documents(uuid_licitacao_id, "Supabase não configurado")

            supabase: Client = create_client(
                os.environ.get("SUPABASE_URL"), 
                os.environ.get("SUPABASE_SERVICE_KEY")
            )
            bucket_name = "licitacao-documents"
            logger.info(f"✅ Cliente Supabase criado, acessando bucket: {bucket_name}")

            # Montar o caminho usando o UUID convertido
            path = f"licitacoes/{uuid_licitacao_id}"
            
            # Listar arquivos no caminho especificado
            response = supabase.storage.from_(bucket_name).list(path)

            if not response:
                 logger.info(f"📁 Nenhum arquivo encontrado em {path}")
                 return jsonify({'success': True, 'data': [], 'total': 0, 'message': 'Nenhum documento encontrado'}), 200

            documentos = []
            for doc in response:
                public_url_response = supabase.storage.from_(bucket_name).get_public_url(f"{path}/{doc['name']}")
                
                # Tratamento de erro se a URL pública não for obtida
                if not public_url_response:
                    public_url = None
                    logger.warning(f"⚠️ Não foi possível obter a URL pública para {doc['name']}")
                else:
                    public_url = public_url_response

                documentos.append({
                    'name': doc.get('name'),
                    'id': doc.get('id'),
                    'updated_at': doc.get('updated_at'),
                    'created_at': doc.get('created_at'),
                    'last_accessed_at': doc.get('last_accessed_at'),
                    'metadata': doc.get('metadata'),
                    'public_url': public_url
                })
            
            logger.info(f"✅ {len(documentos)} documentos encontrados para {uuid_licitacao_id}")

            return jsonify({
                'success': True,
                'data': documentos,
                'total': len(documentos),
                'message': f'{len(documentos)} documentos encontrados'
            }), 200

        except Exception as e:
            logger.error(f"❌ Erro ao buscar documentos: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500
    
    def _get_local_documents(self, licitacao_id: str) -> Tuple[Dict[str, Any], int] | None:
        """Busca documentos no sistema de arquivos local como fallback"""
        try:
            import os
            from pathlib import Path
            
            # Verificar pasta local storage/licitacoes/{licitacao_id}
            local_storage_path = Path("storage") / "licitacoes" / licitacao_id
            
            if not local_storage_path.exists():
                logger.info(f"📁 Pasta local não encontrada: {local_storage_path}")
                return None
            
            documents = []
            for file_path in local_storage_path.iterdir():
                if file_path.is_file():
                    # Determinar tipo do arquivo
                    file_extension = file_path.suffix.lower().lstrip('.')
                    file_type = 'pdf' if file_extension == 'pdf' else file_extension
                    
                    # Gerar URL local (servir via Flask)
                    file_url = f"http://localhost:5002/storage/licitacoes/{licitacao_id}/{file_path.name}"
                    
                    # Obter informações do arquivo
                    file_stats = file_path.stat()
                    
                    documents.append({
                        'name': file_path.name,
                        'url': file_url,
                        'type': file_type,
                        'size': file_stats.st_size,
                        'created_at': None,  # Poderia usar file_stats.st_ctime se necessário
                        'updated_at': None   # Poderia usar file_stats.st_mtime se necessário
                    })
            
            if documents:
                logger.info(f"✅ {len(documents)} documentos encontrados localmente para licitação {licitacao_id}")
                return jsonify({
                    'success': True,
                    'data': documents,
                    'message': f'{len(documents)} documentos encontrados (armazenamento local)',
                    'total': len(documents),
                    'source': 'local'
                }), 200
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar documentos locais: {e}")
            return None
    
    def _return_mock_documents(self, licitacao_id: str, reason: str) -> Tuple[Dict[str, Any], int]:
        """Retorna documentos mockados quando há problemas com o Supabase Storage"""
        logger.warning(f"⚠️ Retornando dados mockados devido a: {reason}")
        logger.info(f"🎭 Retornando documentos mockados para licitação: {licitacao_id}")
        
        mock_documents = [
            {
                'name': 'edital_completo.pdf',
                'url': 'https://via.placeholder.com/800x600/FF6B35/FFFFFF?text=Edital+Completo+PDF',
                'type': 'pdf',
                'size': 2048576,
                'created_at': '2024-01-15T10:30:00Z',
                'updated_at': '2024-01-15T10:30:00Z'
            },
            {
                'name': 'anexo_i_especificacoes.pdf',
                'url': 'https://via.placeholder.com/800x600/FF6B35/FFFFFF?text=Anexo+I+Especificacoes',
                'type': 'pdf',
                'size': 1024768,
                'created_at': '2024-01-15T10:35:00Z',
                'updated_at': '2024-01-15T10:35:00Z'
            },
            {
                'name': 'anexo_ii_planilha_orcamentaria.pdf',
                'url': 'https://via.placeholder.com/800x600/FF6B35/FFFFFF?text=Anexo+II+Planilha+Orcamentaria',
                'type': 'pdf',
                'size': 512384,
                'created_at': '2024-01-15T10:40:00Z',
                'updated_at': '2024-01-15T10:40:00Z'
            },
            {
                'name': 'minuta_contrato.pdf',
                'url': 'https://via.placeholder.com/800x600/FF6B35/FFFFFF?text=Minuta+do+Contrato',
                'type': 'pdf',
                'size': 768192,
                'created_at': '2024-01-15T10:45:00Z',
                'updated_at': '2024-01-15T10:45:00Z'
            }
        ]
        
        return jsonify({
            'success': True,
            'data': mock_documents,
            'message': f'{len(mock_documents)} documentos mockados para demonstração (licitação {licitacao_id})',
            'total': len(mock_documents),
            'mock': True
        }), 200
    
    @log_endpoint_access
    def test_supabase_connection(self) -> Tuple[Dict[str, Any], int]:
        """GET /api/bids/test-storage - Testar conectividade com Supabase Storage"""
        try:
            from supabase import create_client, Client
            import os
            
            logger.info("🧪 Testando conectividade com Supabase Storage")
            
            # Configuração do Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                return jsonify({
                    'success': False,
                    'message': 'Credenciais do Supabase não encontradas'
                }), 500
            
            logger.info(f"🔧 URL: {supabase_url}")
            logger.info(f"🔑 Key: {supabase_key[:20]}...")
            
            # Criar cliente
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Testar acesso ao bucket específico (sem listar todos os buckets)
            try:
                bucket_name = "licitacao-documents"
                
                # Tentar listar uma pasta qualquer para testar conectividade
                test_files = supabase.storage.from_(bucket_name).list("test")
                
                logger.info(f"✅ Conectividade com bucket '{bucket_name}' funcionando")
                
                return jsonify({
                    'success': True,
                    'data': {
                        'bucket_name': bucket_name,
                        'connection_status': 'OK'
                    },
                    'message': f'Conectividade OK com bucket {bucket_name}'
                }), 200
                
            except Exception as storage_error:
                logger.error(f"❌ Erro ao acessar bucket: {storage_error}")
                return jsonify({
                    'success': False,
                    'error': str(storage_error),
                    'message': 'Erro ao acessar Supabase Storage'
                }), 500
            
        except Exception as e:
            logger.error(f"❌ Erro geral no teste: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao testar conectividade'
            }), 500 

    @log_endpoint_access
    def get_bid_items_by_pncp_id(self, pncp_id: str) -> Tuple[Dict[str, Any], int]:
        """GET /api/bids/<pncp_id>/items - Legacy endpoint (DEPRECATED)"""
        try:
            logger.info(f"🔍 [DEPRECATED] Buscando itens da licitação PNCP (legacy): {pncp_id}")
            
            result = self.bid_service.get_bid_items(pncp_id)
            
            if not result.get('success'):
                return jsonify(result), 404
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens da licitação (legacy): {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Erro ao buscar itens da licitação'
            }), 500

    @log_endpoint_access
    def get_bid_items_by_provider(self, provider: str, external_id: str) -> Tuple[Dict[str, Any], int]:
        """GET /api/bids/<provider>/<external_id>/items - Buscar itens por provider específico"""
        try:
            logger.info(f"🔍 Buscando itens da licitação: Provider={provider}, ID={external_id}")
            
            # Validar provider suportado
            supported_providers = ['pncp', 'comprasnet']
            if provider.lower() not in supported_providers:
                return jsonify({
                    'success': False,
                    'error': 'Provider não suportado',
                    'supported_providers': supported_providers,
                    'message': f'Provider "{provider}" não é suportado. Use: {", ".join(supported_providers)}'
                }), 400
            
            # Chamar método específico baseado no provider
            if provider.lower() == 'pncp':
                # Para PNCP, usar o método existente
                result = self.bid_service.get_bid_items(external_id)
            elif provider.lower() == 'comprasnet':
                # Para ComprasNet, usar adapter específico
                result = self._get_comprasnet_items(external_id)
            else:
                return jsonify({
                    'success': False,
                    'error': 'Provider não implementado',
                    'message': f'Suporte para provider "{provider}" ainda não implementado'
                }), 501
            
            if not result.get('success'):
                return jsonify(result), 404
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens por provider {provider}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar itens do provider {provider}'
            }), 500

    def _get_comprasnet_items(self, external_id: str) -> Dict[str, Any]:
        """
        🔍 BUSCAR ITENS DO COMPRASNET usando adapter específico
        Método interno para buscar itens de licitações do ComprasNet
        """
        try:
            logger.info(f"🔍 Iniciando busca de itens ComprasNet para: {external_id}")
            
            # Importar e usar o ComprasNetAdapter diretamente
            from src.adapters.comprasnet_adapter import ComprasNetAdapter
            adapter = ComprasNetAdapter()
            
            # Buscar itens usando o adapter
            items = adapter.get_opportunity_items(external_id)
            
            if not items:
                logger.warning(f"⚠️ Nenhum item encontrado para {external_id}")
                return {
                    'success': False,
                    'message': f'Nenhum item encontrado para a licitação {external_id}',
                    'items': [],
                    'provider': 'comprasnet'
                }
            
            # Formatar resultado similar ao serviço PNCP
            result = {
                'success': True,
                'items': items,
                'total_items': len(items),
                'external_id': external_id,
                'provider': 'comprasnet',
                'message': f'{len(items)} itens encontrados'
            }
            
            logger.info(f"✅ ComprasNet: {len(items)} itens encontrados para {external_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens ComprasNet: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Erro ao buscar itens do ComprasNet para {external_id}',
                'items': [],
                'provider': 'comprasnet'
            } 

    def buscar_itens_multi_provider(self):
        """
        Endpoint para buscar itens de múltiplas licitações de diferentes providers.
        Espera receber uma lista de licitações (ou external_ids) no corpo da requisição.
        Retorna lista de dicts: {'licitacao': ..., 'itens': [...]}
        """
        from flask import request, jsonify
        try:
            data = request.get_json()
            licitacoes = data.get('licitacoes') if data else None
            if not licitacoes or not isinstance(licitacoes, list):
                return jsonify({'success': False, 'message': 'Corpo da requisição deve conter uma lista de licitacoes'}), 400

            from services.licitacao_service import LicitacaoService
            service = LicitacaoService()
            resultados = service.buscar_itens_para_licitacoes(licitacoes)
            return jsonify({'success': True, 'data': resultados, 'message': f'{len(resultados)} licitações processadas'}), 200
        except Exception as e:
            logger.error(f"Erro ao buscar itens multi-provider: {e}")
            return jsonify({'success': False, 'message': f'Erro ao buscar itens: {str(e)}'}), 500 