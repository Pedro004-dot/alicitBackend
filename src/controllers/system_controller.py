"""
Controller para Operações de Sistema
Substitui os endpoints de sistema/background jobs do api.py
"""
from flask import jsonify, request
import logging
from typing import Dict, Any, Tuple
from services.system_service import SystemService
from middleware.error_handler import log_endpoint_access
from config.database import db_manager

logger = logging.getLogger(__name__)

class SystemController:
    """Controller para endpoints de sistema e background jobs"""
    
    def __init__(self):
        self.system_service = SystemService()
    
    @log_endpoint_access
    def health_check(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/health
        Health check completo do sistema
        """
        try:
            # Obter status do banco Supabase
            db_status = db_manager.get_health_status()
            
            # Obter status geral do sistema
            system_status = self.system_service.get_system_health()
            
            # Combinar informações
            health_info = {
                'status': 'healthy',
                'timestamp': system_status.get('timestamp'),
                'system': {
                    'version': '2.0.0-refactored',
                    'architecture': 'modular',
                    'endpoints_migrated': 32
                },
                'database': db_status,
                'services': {
                    'companies': 'active',
                    'bids': 'active', 
                    'matches': 'active',
                    'analysis': 'active',
                    'system': 'active'
                },
                'background_jobs': system_status.get('background_jobs', {}),
                'notes': [
                    '🚀 Nova arquitetura modular ativa',
                    '📊 Conectado ao Supabase PostgreSQL',
                    '🔄 32 endpoints migrados do monólito'
                ]
            }
            
            # Determinar status geral
            if db_status['overall'] == 'error':
                health_info['status'] = 'degraded'
                health_info['notes'].append('⚠️  Modo mock ativo - banco indisponível')
            
            return {
                'status': 'success',
                'data': health_info
            }, 200
            
        except Exception as e:
            logger.error(f"Erro no health check: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro interno no health check',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def get_system_status(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/status
        Status geral do sistema
        """
        try:
            status = self.system_service.get_system_status()
            return {
                'status': 'success',
                'data': status
            }, 200
        except Exception as e:
            logger.error(f"Erro ao obter status do sistema: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao obter status',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def get_daily_bids_status(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/status/daily-bids
        Status da busca diária
        """
        try:
            status = self.system_service.get_daily_bids_status()
            return {
                'status': 'success',
                'data': status
            }, 200
        except Exception as e:
            logger.error(f"Erro ao obter status de busca diária: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao obter status de busca diária',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def get_reevaluate_status(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/status/reevaluate
        Status da reavaliação
        """
        try:
            status = self.system_service.get_reevaluate_status()
            return {
                'status': 'success',
                'data': status
            }, 200
        except Exception as e:
            logger.error(f"Erro ao obter status de reavaliação: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao obter status de reavaliação',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def get_config_options(self) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/config/options
        Opções de configuração
        """
        try:
            options = self.system_service.get_config_options()
            return {
                'status': 'success',
                'data': options
            }, 200
        except Exception as e:
            logger.error(f"Erro ao obter opções de configuração: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao obter configurações',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def search_new_bids(self) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/search-new-bids
        Iniciar busca de novas licitações usando ENGINE REAL
        """
        try:
            result = self.system_service.start_daily_search()
            return {
                'status': 'success',
                'data': result
            }, 200 if result['success'] else 409
        except Exception as e:
            logger.error(f"Erro ao iniciar busca: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao iniciar busca de licitações',
                'details': str(e)
            }, 500
    
    @log_endpoint_access
    def reevaluate_bids(self) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/reevaluate-bids
        Iniciar reavaliação de licitações usando ENGINE REAL
        """
        try:
            result = self.system_service.start_reevaluation()
            return {
                'status': 'success',
                'data': result
            }, 200 if result['success'] else 409
        except Exception as e:
            logger.error(f"Erro ao iniciar reavaliação: {str(e)}")
            return {
                'status': 'error',
                'message': 'Erro ao iniciar reavaliação',
                'details': str(e)
            }, 500 