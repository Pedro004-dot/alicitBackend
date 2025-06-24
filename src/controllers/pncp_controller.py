"""
PNCP Controller
Controller para endpoints essenciais de integração com PNCP
Mantém apenas rotas utilizadas pelo sistema
"""
from flask import jsonify, request
import logging
from typing import Dict, Any, Tuple
from services.pncp_search_service import PNCPSearchService
from repositories.licitacao_repository import LicitacaoRepository
from repositories.bid_repository import BidRepository
from config.database import db_manager
from middleware.error_handler import log_endpoint_access

logger = logging.getLogger(__name__)

class PNCPController:
    """Controller para endpoints essenciais do PNCP"""
    
    def __init__(self):
        self.pncp_service = PNCPSearchService()
        self.licitacao_repo = LicitacaoRepository(db_manager)
        self.bid_repo = BidRepository(db_manager)

    @log_endpoint_access
    def search_by_keywords_advanced(self) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/pncp/search/advanced - Busca avançada PNCP (uso interno)
        
        DESCRIÇÃO:
        - Busca na API oficial do PNCP com filtros avançados
        - Usada internamente pela busca unificada (/api/search/unified)
        - Sistema de score de relevância baseado em palavras-chave
        
        Body JSON:
        {
            "keywords": "computadores notebooks",
            "filtros": {
                "uf": "SP",
                "modalidades": ["pregao_eletronico"],
                "valor_min": "1000",
                "valor_max": "50000"
            },
            "data_inicio": "20240101",
            "data_fim": "20240630",
            "max_pages": 5,
            "include_items": true,
            "save_results": false,
            "apenas_abertas": false
        }
        """
        try:
            # Validar dados de entrada
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Dados JSON são obrigatórios'
                }), 400
            
            keywords = data.get('keywords', '').strip()
            if not keywords:
                return jsonify({
                    'success': False,
                    'message': 'Palavras-chave são obrigatórias'
                }), 400
            
            # Parâmetros da busca avançada
            filtros = data.get('filtros', {})
            data_inicio = data.get('data_inicio')
            data_fim = data.get('data_fim')
            max_pages = data.get('max_pages', 5)
            include_items = data.get('include_items', True)
            save_results = data.get('save_results', False)
            apenas_abertas = data.get('apenas_abertas', False)
            
            # Validar max_pages
            if max_pages > 10:
                return jsonify({
                    'success': False,
                    'message': 'Máximo de 10 páginas permitido para evitar sobrecarga'
                }), 400
            
            logger.info(f"🔍 Iniciando busca PNCP avançada: '{keywords}' com {len(filtros)} filtros")
            
            # Executar busca avançada na API do PNCP
            results, metadata = self.pncp_service.search_by_keywords_advanced(
                keywords=keywords,
                filtros=filtros,
                data_inicio=data_inicio,
                data_fim=data_fim,
                max_pages=max_pages,
                include_items=include_items,
                save_results=save_results,
                apenas_abertas=apenas_abertas
            )
            
            # Verificar se houve erro na busca
            if 'error' in metadata:
                return jsonify({
                    'success': False,
                    'message': f'Erro na busca avançada: {metadata["error"]}',
                    'metadata': metadata
                }), 500
            
            # Preparar resposta
            response_data = {
                'success': True,
                'data': results,
                'metadata': metadata,
                'message': f"Busca avançada: {len(results)} licitações encontradas"
            }
            
            logger.info(f"✅ Busca avançada concluída: {len(results)} resultados")
            
            return jsonify(response_data), 200
            
        except ValueError as e:
            logger.warning(f"⚠️ Erro de validação: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except Exception as e:
            logger.error(f"❌ Erro na busca PNCP avançada: {e}")
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor',
                'error': str(e)
            }), 500

    @log_endpoint_access
    def get_licitacao_items(self, pncp_id: str) -> Tuple[Dict[str, Any], int]:
        """
        GET /api/pncp/licitacao/{pncp_id}/itens - Busca itens de licitação específica
        
        DESCRIÇÃO:
        - Busca itens detalhados de uma licitação pelo número de controle PNCP
        - Primeiro verifica se os itens estão salvos no banco de dados
        - Se não encontrar, busca na API oficial do PNCP e salva automaticamente
        """
        try:
            logger.info(f"📦 Buscando itens da licitação PNCP ID: {pncp_id}")
            
            # 1. Verificar se a licitação existe no banco
            licitacao = self.bid_repo.get_by_pncp_id(pncp_id)
            if not licitacao:
                return jsonify({
                    'success': False,
                    'message': f'Licitação com PNCP ID {pncp_id} não encontrada no banco de dados'
                }), 404
            
            # 2. Buscar itens já salvos no banco
            itens_banco = self.bid_repo.get_bid_items(pncp_id)
            
            if itens_banco:
                logger.info(f"✅ {len(itens_banco)} itens encontrados no banco")
                return jsonify({
                    'success': True,
                    'data': {
                        'licitacao': licitacao,
                        'itens': itens_banco,
                        'fonte': 'banco_dados',
                        'total_itens': len(itens_banco)
                    },
                    'message': f"{len(itens_banco)} itens carregados do banco de dados"
                }), 200
            
            # 3. Se não tem itens no banco, buscar na API PNCP
            logger.info(f"🌐 Itens não encontrados no banco, buscando na API PNCP...")
            
            itens_api = self.pncp_service.get_licitacao_items(pncp_id)
            
            if not itens_api:
                return jsonify({
                    'success': False,
                    'message': f'Nenhum item encontrado para a licitação {pncp_id}'
                }), 404
            
            # 4. Salvar itens no banco para consultas futuras
            try:
                licitacao_id = licitacao['id']
                self.bid_repo.save_bid_items(licitacao_id, itens_api)
                logger.info(f"💾 {len(itens_api)} itens salvos no banco")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar itens no banco: {e}")
            
            return jsonify({
                'success': True,
                'data': {
                    'licitacao': licitacao,
                    'itens': itens_api,
                    'fonte': 'api_pncp',
                    'total_itens': len(itens_api)
                },
                'message': f"{len(itens_api)} itens carregados da API PNCP e salvos no banco"
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens da licitação {pncp_id}: {e}")
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor',
                'error': str(e)
            }), 500

    @log_endpoint_access 
    def refresh_licitacao_items(self, pncp_id: str) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/pncp/licitacao/{pncp_id}/itens/refresh - Força atualização dos itens
        
        DESCRIÇÃO:
        - Força busca dos itens diretamente da API do PNCP
        - Ignora dados salvos no banco e busca versão mais recente
        - Atualiza os dados salvos no banco com as informações mais recentes
        """
        try:
            logger.info(f"🔄 Forçando atualização dos itens da licitação PNCP ID: {pncp_id}")
            
            # 1. Verificar se a licitação existe no banco
            licitacao = self.bid_repo.get_by_pncp_id(pncp_id)
            if not licitacao:
                return jsonify({
                    'success': False,
                    'message': f'Licitação com PNCP ID {pncp_id} não encontrada no banco de dados'
                }), 404
            
            # 2. Buscar itens diretamente da API PNCP (ignorando cache)
            logger.info(f"🌐 Buscando itens atualizados da API PNCP...")
            
            itens_api = self.pncp_service.get_licitacao_items(pncp_id)
            
            if not itens_api:
                return jsonify({
                    'success': False,
                    'message': f'Nenhum item encontrado na API PNCP para a licitação {pncp_id}'
                }), 404
            
            # 3. Atualizar itens no banco (substituir dados existentes)
            try:
                licitacao_id = licitacao['id']
                
                # Primeiro, remover itens existentes
                self.bid_repo.delete_bid_items(licitacao_id)
                
                # Depois, salvar novos itens
                self.bid_repo.save_bid_items(licitacao_id, itens_api)
                
                logger.info(f"💾 {len(itens_api)} itens atualizados no banco")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao atualizar itens no banco: {e}")
            
            return jsonify({
                'success': True,
                'data': {
                    'licitacao': licitacao,
                    'itens': itens_api,
                    'fonte': 'api_pncp_refresh',
                    'total_itens': len(itens_api)
                },
                'message': f"{len(itens_api)} itens atualizados da API PNCP"
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar itens da licitação {pncp_id}: {e}")
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor',
                'error': str(e)
            }), 500

    @log_endpoint_access
    def search_and_save_postgres(self) -> Tuple[Dict[str, Any], int]:
        """
        POST /api/pncp/search/save-postgres - Busca e salva no PostgreSQL diretamente
        
        DESCRIÇÃO:
        - Busca licitações na API PNCP e salva usando BidRepository 
        - Garante compatibilidade total com pncp_api.py
        - Salva todos os campos, incluindo datas de abertura e encerramento
        - Usa o mesmo método de salvamento que o pncp_api.py funcionante
        
        Body JSON:
        {
            "keywords": "computadores notebooks",
            "filtros": {
                "uf": "SP",
                "modalidades": ["pregao_eletronico"],
                "valor_min": "1000",
                "valor_max": "50000"
            },
            "data_inicio": "20240101",
            "data_fim": "20240630",
            "max_pages": 5,
            "include_items": true
        }
        """
        try:
            # Validar dados de entrada
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Dados JSON são obrigatórios'
                }), 400
            
            keywords = data.get('keywords', '').strip()
            if not keywords:
                return jsonify({
                    'success': False,
                    'message': 'Palavras-chave são obrigatórias'
                }), 400
            
            # Parâmetros da busca
            filtros = data.get('filtros', {})
            data_inicio = data.get('data_inicio')
            data_fim = data.get('data_fim')
            max_pages = data.get('max_pages', 5)
            include_items = data.get('include_items', True)
            
            # Validar max_pages
            if max_pages > 10:
                return jsonify({
                    'success': False,
                    'message': 'Máximo de 10 páginas permitido'
                }), 400
            
            logger.info(f"🔍 Busca + PostgreSQL: '{keywords}' com {len(filtros)} filtros")
            
            # 1. Executar busca avançada (SEM salvar automaticamente)
            results, metadata = self.pncp_service.search_by_keywords_advanced(
                keywords=keywords,
                filtros=filtros,
                data_inicio=data_inicio,
                data_fim=data_fim,
                max_pages=max_pages,
                include_items=include_items,
                save_results=False  # NÃO usar persistence service
            )
            
            # Verificar se houve erro na busca
            if 'error' in metadata:
                return jsonify({
                    'success': False,
                    'message': f'Erro na busca: {metadata["error"]}',
                    'metadata': metadata
                }), 500
            
            if not results:
                return jsonify({
                    'success': True,
                    'message': 'Nenhuma licitação encontrada com os critérios especificados',
                    'data': {
                        'licitacoes': [],
                        'stats': {
                            'licitacoes_salvas': 0,
                            'licitacoes_atualizadas': 0,
                            'itens_salvos': 0,
                            'erros': []
                        }
                    },
                    'metadata': metadata
                }), 200
            
            # 2. Salvar usando BidRepository para compatibilidade total
            logger.info(f"💾 Salvando {len(results)} licitações no PostgreSQL...")
            save_stats = self.pncp_service.save_results_to_postgres(
                results, 
                include_items=include_items
            )
            
            # 3. Preparar resposta consolidada
            response_data = {
                'success': True,
                'message': f"Busca e salvamento concluídos: {len(results)} licitações processadas",
                'data': {
                    'licitacoes': results,
                    'stats': save_stats
                },
                'metadata': {
                    **metadata,
                    'save_method': 'postgres_direct',
                    'save_stats': save_stats
                }
            }
            
            # Log final
            logger.info(f"✅ Busca + PostgreSQL concluída:")
            logger.info(f"   📊 {save_stats['licitacoes_salvas']} novas")
            logger.info(f"   🔄 {save_stats['licitacoes_atualizadas']} atualizadas") 
            logger.info(f"   📦 {save_stats['itens_salvos']} itens salvos")
            logger.info(f"   ❌ {len(save_stats['erros'])} erros")
            
            return jsonify(response_data), 200
            
        except ValueError as e:
            logger.warning(f"⚠️ Erro de validação: {e}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
            
        except Exception as e:
            logger.error(f"❌ Erro na busca + PostgreSQL: {e}")
            return jsonify({
                'success': False,
                'message': 'Erro interno do servidor',
                'error': str(e)
            }), 500 