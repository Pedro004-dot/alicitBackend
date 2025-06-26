from flask import request, jsonify
import logging
from typing import Dict, Any
import re
from ._id_converter import convert_pncp_to_uuid

logger = logging.getLogger(__name__)

class RAGController:
    """Controller para endpoints RAG"""
    
    def __init__(self, rag_service):
        self.rag_service = rag_service
    
    def analisar_documentos(self) -> Dict[str, Any]:
        """Endpoint principal para análise de documentos"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'JSON inválido'}), 400
            
            licitacao_id = data.get('licitacao_id')
            query = data.get('query', 'Faça um resumo geral dos documentos desta licitação.')
            
            if not licitacao_id:
                return jsonify({'success': False, 'error': 'licitacao_id é obrigatório'}), 400
            
            try:
                uuid_licitacao_id = convert_pncp_to_uuid(licitacao_id)
            except ValueError as e:
                logger.error(f"❌ Erro de conversão de ID: {e}")
                return jsonify({'success': False, 'error': str(e)}), 404

            result = self.rag_service.process_or_query(uuid_licitacao_id, query)
            status_code = 200 if result.get('success', False) else 500
            
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"❌ Erro no controller RAG/analisar: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500
    
    def query_licitacao(self) -> Dict[str, Any]:
        """Endpoint para fazer perguntas sobre uma licitação específica"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            query = data.get('query')
            
            if not licitacao_id or not query:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id e query são obrigatórios'
                }), 400
            
            # Processar query
            result = self.rag_service._answer_query(query, licitacao_id)
            
            status_code = 200 if result['success'] else 400
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"❌ Erro no query controller: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def status_licitacao(self) -> Dict[str, Any]:
        """Endpoint para verificar status de processamento"""
        try:
            licitacao_id = request.args.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            stats = self.rag_service.get_licitacao_stats(licitacao_id)
            
            return jsonify({
                'success': True,
                'data': stats
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no status controller: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def invalidar_cache(self) -> Dict[str, Any]:
        """Endpoint para invalidar cache de uma licitação"""
        try:
            data = request.get_json()
            licitacao_id = data.get('licitacao_id') if data else None
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            deleted_count = self.rag_service.cache_manager.invalidate_licitacao_cache(licitacao_id)
            
            return jsonify({
                'success': True,
                'message': f'{deleted_count} entradas de cache removidas',
                'deleted_count': deleted_count
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao invalidar cache: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def reprocessar_documentos(self) -> Dict[str, Any]:
        """Endpoint para forçar reprocessamento de documentos com extração recursiva"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON inválido'
                }), 400
            
            licitacao_id = data.get('licitacao_id')
            forcar_reprocessamento = data.get('forcar_reprocessamento', True)
            
            if not licitacao_id:
                return jsonify({
                    'success': False,
                    'error': 'licitacao_id é obrigatório'
                }), 400
            
            # Limpar documentos existentes se forçando
            if forcar_reprocessamento:
                logger.info(f"🗑️ Limpando documentos existentes para: {licitacao_id}")
                try:
                    self.rag_service.unified_processor._limpar_documentos_licitacao(licitacao_id)
                    # Também limpar do vector store (se método existir)
                    if hasattr(self.rag_service.vector_store, 'clear_licitacao_vectors'):
                        self.rag_service.vector_store.clear_licitacao_vectors(licitacao_id)
                    # Invalidar cache
                    self.rag_service.cache_manager.invalidate_licitacao_cache(licitacao_id)
                except Exception as clean_error:
                    logger.warning(f"⚠️ Erro na limpeza: {clean_error}")
            
            # Forçar reprocessamento
            result = self.rag_service._ensure_documents_processed(licitacao_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Reprocessamento iniciado com sucesso',
                    'data': result
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Erro no reprocessamento')
                }), 500
                
        except Exception as e:
            logger.error(f"❌ Erro no reprocessamento: {e}")
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500
    
    def vectorize_documents(self) -> Dict[str, Any]:
        """Endpoint para vetorização de documentos (usado na preparação automática)"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'JSON payload obrigatório'}), 400
            
            licitacao_id = data.get('licitacao_id')
            
            if not licitacao_id:
                return jsonify({'success': False, 'error': 'licitacao_id é obrigatório'}), 400

            try:
                uuid_licitacao_id = convert_pncp_to_uuid(licitacao_id)
            except ValueError as e:
                logger.error(f"❌ Erro de conversão de ID para vetorização: {e}")
                return jsonify({'success': False, 'error': str(e)}), 404

            # Chama o novo método público no serviço com o ID correto
            result = self.rag_service.vectorize_documents(uuid_licitacao_id)
            status_code = 200 if result.get('success', False) else 500
            
            return jsonify(result), status_code

        except Exception as e:
            logger.error(f"❌ Erro ao vetorizar documentos: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Erro interno: {str(e)}'}), 500
