"""
Controller para Análise de Dados e Debugging de Licitações
Endpoints para identificar e resolver inconsistências
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
from repositories.licitacao_repository_enhanced import LicitacaoPNCPRepositoryEnhanced

# Configurar logger
logger = logging.getLogger(__name__)

class DataAnalysisController:
    """
    Controller dedicado à análise de dados e debugging de licitações
    """
    
    def __init__(self):
        self.enhanced_repo = LicitacaoPNCPRepositoryEnhanced()
    
    def test_licitacao_data_consistency(self) -> Dict[str, Any]:
        """
        Testa a consistência de dados de uma licitação específica
        """
        try:
            # Obter PNCP ID dos parâmetros
            pncp_id = request.args.get('pncp_id')
            if not pncp_id:
                return {
                    'success': False,
                    'error': 'Parâmetro pncp_id é obrigatório'
                }, 400
            
            logger.info(f"🧪 Iniciando teste de consistência para licitação {pncp_id}")
            
            # Executar teste
            resultado = self.enhanced_repo.test_data_consistency(pncp_id)
            
            if resultado['success']:
                logger.info(f"✅ Teste concluído com sucesso para {pncp_id}")
                return {
                    'success': True,
                    'data': resultado,
                    'message': f'Análise de consistência concluída para {pncp_id}'
                }
            else:
                logger.warning(f"⚠️ Teste falhou para {pncp_id}: {resultado.get('error')}")
                return {
                    'success': False,
                    'error': resultado.get('error'),
                    'pncp_id': pncp_id
                }, 404
                
        except Exception as e:
            logger.error(f"❌ Erro no teste de consistência: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500
    
    def analyze_batch_consistency(self) -> Dict[str, Any]:
        """
        Analisa consistência de um lote de licitações
        """
        try:
            # Obter lista de PNCP IDs
            data = request.get_json()
            if not data or 'pncp_ids' not in data:
                return {
                    'success': False,
                    'error': 'Lista de pncp_ids é obrigatória no body'
                }, 400
            
            pncp_ids = data['pncp_ids']
            if not isinstance(pncp_ids, list) or not pncp_ids:
                return {
                    'success': False,
                    'error': 'pncp_ids deve ser uma lista não vazia'
                }, 400
            
            logger.info(f"🔍 Analisando consistência de {len(pncp_ids)} licitações")
            
            resultados = []
            for pncp_id in pncp_ids:
                resultado = self.enhanced_repo.test_data_consistency(pncp_id)
                resultados.append(resultado)
            
            # Gerar relatório consolidado
            relatorio_consolidado = self.enhanced_repo.generate_data_consistency_report()
            
            sucessos = sum(1 for r in resultados if r['success'])
            falhas = len(resultados) - sucessos
            
            logger.info(f"📊 Análise de lote concluída: {sucessos} sucessos, {falhas} falhas")
            
            return {
                'success': True,
                'batch_results': resultados,
                'consolidated_report': relatorio_consolidado,
                'summary': {
                    'total_analyzed': len(pncp_ids),
                    'successful': sucessos,
                    'failed': falhas,
                    'success_rate': sucessos / len(pncp_ids) if pncp_ids else 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de lote: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500
    
    def enrich_licitacao_with_details(self) -> Dict[str, Any]:
        """
        Enriquece uma licitação com dados detalhados da API
        """
        try:
            # Obter dados da licitação do body
            data = request.get_json()
            if not data or 'licitacao' not in data:
                return {
                    'success': False,
                    'error': 'Dados da licitação são obrigatórios no body'
                }, 400
            
            licitacao_busca = data['licitacao']
            pncp_id = licitacao_busca.get('numeroControlePNCP')
            
            if not pncp_id:
                return {
                    'success': False,
                    'error': 'numeroControlePNCP é obrigatório na licitação'
                }, 400
            
            logger.info(f"🔄 Enriquecendo licitação {pncp_id} com dados detalhados")
            
            # Enriquecer licitação
            licitacao_enriquecida = self.enhanced_repo.enrich_licitacao_with_details(licitacao_busca)
            
            # Gerar relatório de consistência
            relatorio = self.enhanced_repo.generate_data_consistency_report()
            
            logger.info(f"✅ Licitação {pncp_id} enriquecida com sucesso")
            
            return {
                'success': True,
                'original_data': licitacao_busca,
                'enriched_data': licitacao_enriquecida,
                'consistency_report': relatorio,
                'enhancement_summary': {
                    'original_fields': len(licitacao_busca),
                    'enriched_fields': len(licitacao_enriquecida),
                    'new_fields_added': len(licitacao_enriquecida) - len(licitacao_busca)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no enriquecimento: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500
    
    def get_data_consistency_report(self) -> Dict[str, Any]:
        """
        Retorna relatório de consistência atual
        """
        try:
            logger.info("📋 Gerando relatório de consistência de dados")
            
            relatorio = self.enhanced_repo.generate_data_consistency_report()
            
            return {
                'success': True,
                'report': relatorio,
                'timestamp': relatorio.get('timestamp'),
                'message': 'Relatório de consistência gerado com sucesso'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar relatório: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500
    
    def debug_api_responses(self) -> Dict[str, Any]:
        """
        Endpoint para debug detalhado das respostas da API
        """
        try:
            # Configurar logging mais detalhado temporariamente
            data_logger = logging.getLogger('data_consistency')
            original_level = data_logger.level
            data_logger.setLevel(logging.DEBUG)
            
            try:
                # Obter parâmetros
                pncp_id = request.args.get('pncp_id')
                if not pncp_id:
                    return {
                        'success': False,
                        'error': 'Parâmetro pncp_id é obrigatório'
                    }, 400
                
                logger.info(f"🐞 Iniciando debug detalhado para {pncp_id}")
                
                # Executar com logging detalhado
                resultado = self.enhanced_repo.test_data_consistency(pncp_id)
                
                return {
                    'success': True,
                    'debug_data': resultado,
                    'message': f'Debug concluído para {pncp_id}. Verifique os logs para detalhes.'
                }
                
            finally:
                # Restaurar nível de logging original
                data_logger.setLevel(original_level)
                
        except Exception as e:
            logger.error(f"❌ Erro no debug: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500
    
    def compare_search_vs_details(self) -> Dict[str, Any]:
        """
        Compara dados de busca vs detalhes para identificar inconsistências
        """
        try:
            data = request.get_json()
            if not data or 'search_data' not in data or 'detail_data' not in data:
                return {
                    'success': False,
                    'error': 'search_data e detail_data são obrigatórios no body'
                }, 400
            
            search_data = data['search_data']
            detail_data = data['detail_data']
            
            pncp_id = search_data.get('numeroControlePNCP', 'UNKNOWN')
            
            logger.info(f"🔍 Comparando dados de busca vs detalhes para {pncp_id}")
            
            # Detectar inconsistências
            self.enhanced_repo.detect_data_inconsistencies(search_data, detail_data)
            
            # Gerar relatório
            relatorio = self.enhanced_repo.generate_data_consistency_report()
            
            return {
                'success': True,
                'pncp_id': pncp_id,
                'comparison_completed': True,
                'consistency_report': relatorio,
                'message': f'Comparação concluída para {pncp_id}'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na comparação: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, 500 