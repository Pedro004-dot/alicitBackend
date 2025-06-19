"""
Chat Controller
Coordena operações de chat e análise RAG
Segue padrão: Controller -> Service -> Repository
"""
import logging
from flask import request, jsonify
from typing import Dict, Any, Optional
from services.rag_integration_service import RAGIntegrationService

logger = logging.getLogger(__name__)

class ChatController:
    """
    Controller para operações de chat e análise RAG
    PADRONIZADO: Segue padrão Controller -> Service
    """
    
    def __init__(self):
        self.rag_service = RAGIntegrationService()
    
    def iniciar_sessao_chat(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Iniciar sessão de análise com checklist automático
        POST /api/licitacoes/<id>/iniciar-sessao
        """
        try:
            logger.info(f"Iniciando sessão de chat para licitação: {licitacao_id}")
            
            # Preparar documento e gerar checklist
            resultado = self.rag_service.iniciar_sessao_analise(licitacao_id)
            
            if resultado['success']:
                return jsonify({
                    'success': True,
                    'data': resultado['data']
                }), 200
            else:
                status_code = 202 if resultado.get('status') == 'processing' else 400
                return jsonify({
                    'success': False,
                    'message': resultado['message'],
                    'status': resultado.get('status', 'error')
                }), status_code
                
        except Exception as e:
            logger.error(f"Erro ao iniciar sessão de chat: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def responder_pergunta(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Responder pergunta sobre licitação usando RAG
        POST /api/licitacoes/<id>/chat
        """
        try:
            # Validar dados da requisição
            data = request.get_json()
            if not data or 'pergunta' not in data:
                return jsonify({
                    'success': False,
                    'message': 'Pergunta é obrigatória'
                }), 400
            
            pergunta = data['pergunta'].strip()
            if not pergunta:
                return jsonify({
                    'success': False,
                    'message': 'Pergunta não pode estar vazia'
                }), 400
            
            session_id = data.get('session_id')
            historico = data.get('historico', [])
            
            logger.info(f"Processando pergunta para licitação {licitacao_id}: {pergunta[:100]}...")
            
            # Processar pergunta
            resultado = self.rag_service.processar_pergunta(
                licitacao_id=licitacao_id,
                pergunta=pergunta,
                session_id=session_id,
                historico=historico
            )
            
            if resultado['success']:
                return jsonify({
                    'success': True,
                    'data': resultado['data']
                }), 200
            else:
                status_code = 400 if resultado.get('error_type') == 'document_not_ready' else 500
                return jsonify({
                    'success': False,
                    'message': resultado['message'],
                    'error_type': resultado.get('error_type')
                }), status_code
                
        except Exception as e:
            logger.error(f"Erro ao processar pergunta: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def verificar_status_documento(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Verificar status da vetorização do documento
        GET /api/licitacoes/<id>/status-documento
        """
        try:
            status = self.rag_service.verificar_status_documento(licitacao_id)
            
            return jsonify({
                'success': True,
                'data': status
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao verificar status do documento: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def obter_checklist_atualizado(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Obter checklist mais recente da licitação
        GET /api/licitacoes/<id>/checklist-atualizado
        """
        try:
            # Parâmetros da query
            force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
            sections = request.args.get('sections', '').split(',') if request.args.get('sections') else None
            
            logger.info(f"Obtendo checklist atualizado para licitação: {licitacao_id}")
            
            checklist = self.rag_service.obter_checklist_atualizado(
                licitacao_id=licitacao_id,
                force_refresh=force_refresh,
                sections_especificas=sections
            )
            
            if checklist['success']:
                return jsonify({
                    'success': True,
                    'data': checklist['data']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': checklist['message']
                }), 400
                
        except Exception as e:
            logger.error(f"Erro ao obter checklist atualizado: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def obter_historico_chat(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Obter histórico de conversas da licitação
        GET /api/licitacoes/<id>/historico-chat
        """
        try:
            # Parâmetros da query
            session_id = request.args.get('session_id')
            limit = int(request.args.get('limit', 50))
            
            historico = self.rag_service.obter_historico_conversa(
                licitacao_id=licitacao_id,
                session_id=session_id,
                limit=limit
            )
            
            return jsonify({
                'success': True,
                'data': historico
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao obter histórico de chat: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def exportar_analise_completa(self, licitacao_id: str) -> tuple[Dict[str, Any], int]:
        """
        Exportar análise completa da licitação
        GET /api/licitacoes/<id>/export-analise
        """
        try:
            # Parâmetros da query
            formato = request.args.get('formato', 'json')
            incluir_chat = request.args.get('incluir_chat', 'true').lower() == 'true'
            incluir_fontes = request.args.get('incluir_fontes', 'true').lower() == 'true'
            
            if formato not in ['json', 'pdf', 'markdown']:
                return jsonify({
                    'success': False,
                    'message': 'Formato deve ser: json, pdf ou markdown'
                }), 400
            
            resultado = self.rag_service.exportar_analise_completa(
                licitacao_id=licitacao_id,
                formato=formato,
                incluir_chat=incluir_chat,
                incluir_fontes=incluir_fontes
            )
            
            if resultado['success']:
                return jsonify({
                    'success': True,
                    'data': resultado['data']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'message': resultado['message']
                }), 400
                
        except Exception as e:
            logger.error(f"Erro ao exportar análise: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def limpar_cache_vetores(self) -> tuple[Dict[str, Any], int]:
        """
        Limpar cache de vetores antigos (admin)
        POST /api/admin/limpeza-cache-vetores
        """
        try:
            data = request.get_json() or {}
            dias_antigos = data.get('dias_antigos', 30)
            force = data.get('force', False)
            
            resultado = self.rag_service.limpar_cache_vetores(
                dias_antigos=dias_antigos,
                force=force
            )
            
            return jsonify({
                'success': True,
                'data': resultado
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache de vetores: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500
    
    def obter_estatisticas_rag(self) -> tuple[Dict[str, Any], int]:
        """
        Obter estatísticas do sistema RAG (admin)
        GET /api/admin/estatisticas-rag
        """
        try:
            estatisticas = self.rag_service.obter_estatisticas_sistema()
            
            return jsonify({
                'success': True,
                'data': estatisticas
            }), 200
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas RAG: {e}")
            return jsonify({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }), 500 