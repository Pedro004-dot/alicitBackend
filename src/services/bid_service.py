"""
Bid Service (Licitação Service)
Lógica de negócio para operações com licitações
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from repositories.bid_repository import BidRepository
from repositories.licitacao_repository import LicitacaoPNCPRepository
from config.database import db_manager
import requests
import os
import asyncio
import uuid
import json

logger = logging.getLogger(__name__)

class BidService:
    """Service para regras de negócio de licitações"""
    
    def __init__(self):
        # Repositório para operações no banco de dados local
        self.licitacao_repo = BidRepository(db_manager)
        # Repositório para busca na API do PNCP
        self.pncp_repo = LicitacaoPNCPRepository()
        # Unified search service (lazy initialization)
        self._unified_search_service = None
        # 🆕 NEW: PNCPAdapter para busca de detalhes e itens  
        self._pncp_adapter = None
    
    @property
    def unified_search_service(self):
        """Lazy initialization of UnifiedSearchService"""
        if self._unified_search_service is None:
            try:
                from services.unified_search_service import UnifiedSearchService
                self._unified_search_service = UnifiedSearchService()
                logger.info("✅ UnifiedSearchService initialized in BidService")
            except Exception as e:
                logger.error(f"❌ Failed to initialize UnifiedSearchService: {e}")
                self._unified_search_service = None
        return self._unified_search_service
    
    @property
    def pncp_adapter(self):
        """🆕 NEW: Lazy loading do PNCPAdapter com configuração adequada"""
        if not hasattr(self, '_pncp_adapter') or self._pncp_adapter is None:
            try:
                from adapters.pncp_adapter import PNCPAdapter
                
                # 🔧 Configuração necessária para o PNCPAdapter
                config = {
                    'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
                    'timeout': 30,
                    'max_results': 20000,
                    'max_pages': 400
                }
                
                self._pncp_adapter = PNCPAdapter(config)
                logger.info("✅ PNCPAdapter inicializado com sucesso")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize PNCPAdapter: {e}")
                self._pncp_adapter = None
                
        return self._pncp_adapter
    
    def get_all_bids(self, limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar todas as licitações com formatação para frontend
        """
        try:
            bids = self.licitacao_repo.find_all(limit=limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            message = f'{len(formatted_bids)} licitações encontradas'
            return formatted_bids, message
        except Exception as e:
            logger.error(f"Erro ao buscar licitações: {e}")
            return [], f"Erro ao buscar licitações: {str(e)}"
    
    def get_bid_by_id(self, bid_id: str) -> Optional[Dict[str, Any]]:
        """Buscar licitação por ID com formatação"""
        try:
            bid = self.licitacao_repo.find_by_id(bid_id)
            if bid:
                return self._format_bid_for_frontend(bid)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar licitação {bid_id}: {e}")
            return None
    
    def get_bid_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """🔄 UPDATED: Buscar licitação por PNCP ID usando novo PNCPAdapter"""
        try:
            # 1. Tenta buscar no banco de dados local primeiro
            bid = self.licitacao_repo.find_by_pncp_id(pncp_id)
            if bid:
                logger.info(f"Licitação {pncp_id} encontrada no banco de dados local.")
                return self._format_bid_for_frontend(bid)

            # 2. 🆕 NEW: Se não encontrou, usa o novo PNCPAdapter
            logger.info(f"Licitação {pncp_id} não encontrada localmente. Usando PNCPAdapter...")
            
            if self.pncp_adapter is None:
                logger.warning("❌ PNCPAdapter não disponível, usando fallback para API antiga")
                return self._fallback_to_old_api(pncp_id)
            
            # Buscar detalhes via novo adapter
            opportunity_data = self.pncp_adapter.get_opportunity_details(pncp_id)
            
            if opportunity_data:
                logger.info(f"✅ Detalhes da licitação {pncp_id} encontrados via PNCPAdapter.")
                # Converter OpportunityData para formato frontend
                converted_bid = self._convert_opportunity_data_to_bid(opportunity_data, pncp_id)
                return self._format_bid_for_frontend(converted_bid)

            logger.warning(f"Licitação {pncp_id} não encontrada via PNCPAdapter, tentando fallback...")
            return self._fallback_to_old_api(pncp_id)

        except Exception as e:
            logger.error(f"Erro ao buscar licitação por PNCP {pncp_id}: {e}", exc_info=True)
            # Tentar fallback em caso de erro
            return self._fallback_to_old_api(pncp_id)
    
    def _fallback_to_old_api(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """🔄 Fallback para a API antiga quando PNCPAdapter falha"""
        try:
            logger.info(f"🔄 Fallback: Usando API antiga para {pncp_id}")
            
            # 🔧 FIX: Usar await corretamente ou create_task quando já em um event loop
            try:
                # Tentar usar o loop existente se estivermos em um
                import asyncio
                loop = asyncio.get_running_loop()
                
                # Se há um loop rodando, criar uma task
                async def fetch_data():
                    return self.pncp_repo.buscar_licitacao_detalhada(pncp_id)
                
                # Criar uma task para executar no loop existente
                task = loop.create_task(fetch_data())
                # Aguardar usando loop.run_until_complete() NÃO funciona em loop existente
                # Então vamos tentar uma abordagem síncrona
                
                logger.warning("⚠️ Event loop já rodando, tentando abordagem alternativa")
                return None
                
            except RuntimeError:
                # Não há loop rodando, podemos usar asyncio.run()
                raw_data = asyncio.run(self.pncp_repo.buscar_licitacao_detalhada(pncp_id))
                
                if raw_data:
                    return self._convert_api_bid_data(raw_data, pncp_id)
                    
        except Exception as e:
            logger.error(f"❌ Erro também no fallback para {pncp_id}: {e}")
            
        return None
    
    def _convert_opportunity_data_to_bid(self, opportunity_data, pncp_id: str) -> Dict[str, Any]:
        """🆕 NEW: Converte OpportunityData do PNCPAdapter para formato bid"""
        from datetime import datetime
        import uuid
        
        try:
            # ✅ FIX: Garantir que sempre temos um ID
            bid_id = str(uuid.uuid4())
            
            # 🔧 CORREÇÃO CRÍTICA: Extrair CNPJ corretamente
            orgao_cnpj = (
                opportunity_data.procuring_entity_id or  # Campo principal
                (opportunity_data.provider_specific_data.get('orgao_cnpj') if opportunity_data.provider_specific_data else None) or
                self._extract_cnpj_from_pncp_id(pncp_id)  # Fallback
            )
            
            # 🔧 CORREÇÃO: Mapear dados do provider_specific_data corretamente
            provider_data = opportunity_data.provider_specific_data or {}
            
            return {
                'id': bid_id,  # ✅ Campo obrigatório para _format_bid_for_frontend
                'pncp_id': pncp_id,
                'numero_controle_pncp': pncp_id,
                'objeto_compra': opportunity_data.title,
                'orgao_cnpj': orgao_cnpj,  # ✅ CORRIGIDO: usar o CNPJ extraído
                'razao_social': opportunity_data.procuring_entity_name or provider_data.get('orgao_nome'),
                'uf': opportunity_data.region_code,
                'uf_nome': provider_data.get('ufNome'),
                'nome_unidade': provider_data.get('unidade_nome'),
                'municipio_nome': opportunity_data.municipality,
                'codigo_ibge': provider_data.get('codigoIbge'),
                'codigo_unidade': provider_data.get('codigoUnidade'),
                'status': provider_data.get('situacao_nome') or provider_data.get('status'),
                'link_sistema_origem': provider_data.get('link_sistema_origem'),
                'data_publicacao': opportunity_data.publication_date,
                'valor_total_estimado': opportunity_data.estimated_value,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'numero_compra': provider_data.get('numero_compra'),
                'processo': provider_data.get('processo'),
                'valor_total_homologado': provider_data.get('valor_total_homologado'),
                'data_abertura_proposta': provider_data.get('data_abertura_proposta'),
                'data_encerramento_proposta': opportunity_data.submission_deadline,
                'modo_disputa_id': provider_data.get('modoDisputaId'),
                'modo_disputa_nome': provider_data.get('modo_disputa'),
                'srp': provider_data.get('srp'),
                'link_processo_eletronico': provider_data.get('linkProcessoEletronico'),
                'modalidade_nome': provider_data.get('modalidade_nome'),
                'ano_compra': provider_data.get('ano_compra') or self._extract_year_from_pncp_id(pncp_id),
                'sequencial_compra': provider_data.get('sequencial_compra') or self._extract_sequential_from_pncp_id(pncp_id),
                'informacao_complementar': opportunity_data.description
            }
        except Exception as e:
            logger.error(f"❌ Erro ao converter OpportunityData: {e}")
            raise

    def _extract_cnpj_from_pncp_id(self, pncp_id: str) -> Optional[str]:
        """Extrai o CNPJ do PNCP ID como fallback"""
        try:
            # Parse do formato: CNPJ-TIPO-SEQUENCIAL/ANO
            if '-' in pncp_id and '/' in pncp_id:
                parts = pncp_id.split('-')
                if len(parts) >= 1:
                    cnpj = parts[0]
                    if len(cnpj) == 14 and cnpj.isdigit():
                        return cnpj
        except Exception:
            pass
        return None

    def _convert_api_bid_data(self, raw_data: Dict[str, Any], fallback_pncp_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Converte dados da API de detalhes para um formato similar ao do banco de dados."""
        from datetime import datetime
        import uuid
        
        # Extrair informações do órgão e unidade (nome na API pode variar)
        orgao_info = (
            raw_data.get('orgaoEntidade')
            or raw_data.get('orgao')
            or {}
        )
        unidade_info = raw_data.get('unidadeOrgao', {})
        
        # Extrair o PNCP ID (algumas variações de campo foram observadas na API)
        pncp_id = (
            raw_data.get('numeroControlePNCP')
            or raw_data.get('numeroControlePncp')  # variação camelCase
            or raw_data.get('numeroControle')      # fallback observado em alguns endpoints
            or fallback_pncp_id                    # último recurso: usar o PNCP ID recebido como parâmetro externo
        )

        if not pncp_id:
            logger.error("❌ PNCP ID não encontrado nos dados da API, mesmo após tentativas de fallback")
            return None
        
        # Fallback para CNPJ usando PNCP-ID
        cnpj_fallback = None
        try:
            parsed_aux = self.pncp_repo._parse_pncp_id(pncp_id)
            if parsed_aux:
                cnpj_fallback = parsed_aux.get('cnpj')
        except Exception:
            pass
        
        # ✅ FIX: Garantir que sempre temos um ID
        bid_id = str(uuid.uuid4())
        
        # Construir o dicionário com os dados convertidos
        return {
            'id': bid_id,  # ✅ Campo obrigatório para _format_bid_for_frontend
            'pncp_id': pncp_id,  # Campo principal para identificação
            'numero_controle_pncp': pncp_id,  # Campo duplicado para compatibilidade
            'objeto_compra': raw_data.get('objetoCompra') or raw_data.get('objeto_compra'),
            'orgao_cnpj': orgao_info.get('cnpj') or cnpj_fallback,
            'razao_social': orgao_info.get('razaoSocial'),
            'uf': unidade_info.get('ufSigla'),
            'uf_nome': unidade_info.get('ufNome'),
            'nome_unidade': unidade_info.get('nomeUnidade'),
            'municipio_nome': unidade_info.get('municipioNome'),
            'codigo_ibge': unidade_info.get('codigoIbge'),
            'codigo_unidade': unidade_info.get('codigo'),
            'status': raw_data.get('situacaoCompraNome'),
            'link_sistema_origem': raw_data.get('linkSistemaOrigem'),
            'data_publicacao': raw_data.get('dataPublicacaoPncp'),
            'valor_total_estimado': raw_data.get('valorTotalEstimado'),
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'numero_compra': raw_data.get('numero'),
            'processo': raw_data.get('numeroProcesso'),
            'valor_total_homologado': raw_data.get('valorTotalHomologado'),
            'data_abertura_proposta': raw_data.get('dataAberturaProposta'),
            'data_encerramento_proposta': raw_data.get('dataEncerramentoProposta'),
            'modo_disputa_id': raw_data.get('modoDisputa', {}).get('id'),
            'modo_disputa_nome': raw_data.get('modoDisputa', {}).get('nome'),
            'srp': raw_data.get('srp'),
            'link_processo_eletronico': raw_data.get('uriSistemaOrigem'),
            'modalidade_nome': raw_data.get('modalidadeNome'),
            'ano_compra': self._extract_year_from_pncp_id(pncp_id),
            'sequencial_compra': self._extract_sequential_from_pncp_id(pncp_id)
        }

    def search_bids_by_object(self, search_term: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações por objeto/descrição
        """
        try:
            bids = self.licitacao_repo.search_by_object(search_term, limit)
            return self._format_bids_for_frontend(bids)
        except Exception as e:
            logger.error(f"Erro ao buscar licitações por objeto '{search_term}': {e}")
            return []
    
    def get_bids_by_state(self, uf: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações por estado
        """
        try:
            bids = self.licitacao_repo.find_by_state(uf, limit)
            return self._format_bids_for_frontend(bids)
        except Exception as e:
            logger.error(f"Erro ao buscar licitações do estado {uf}: {e}")
            return []
    
    def get_bids_by_modality(self, modalidade: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações por modalidade
        """
        try:
            bids = self.licitacao_repo.find_by_modality(modalidade, limit)
            return self._format_bids_for_frontend(bids)
        except Exception as e:
            logger.error(f"Erro ao buscar licitações da modalidade {modalidade}: {e}")
            return []
    
    def get_bids_by_value_range(self, min_value: float, max_value: float, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações por faixa de valor
        """
        try:
            bids = self.licitacao_repo.find_by_value_range(min_value, max_value, limit)
            return self._format_bids_for_frontend(bids)
        except Exception as e:
            logger.error(f"Erro ao buscar licitações por valor ({min_value}-{max_value}): {e}")
            return []
    
    def get_recent_bids(self, limit: int = 10) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar licitações mais recentes
        """
        try:
            bids = self.licitacao_repo.find_recent(limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            message = f"{len(formatted_bids)} licitações recentes encontradas"
            return formatted_bids, message
        except Exception as e:
            logger.error(f"Erro ao buscar licitações recentes: {e}")
            return [], f"Erro ao buscar licitações recentes: {str(e)}"
    
    def get_active_bids(self, after_date: str = None, limit: Optional[int] = None) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar licitações ativas (com prazo aberto após uma data específica)
        
        Args:
            after_date: Data mínima no formato YYYY-MM-DD (opcional)
            limit: Número máximo de resultados (None = sem limite)
            
        Returns:
            Tupla com lista de licitações ativas e mensagem de status
        """
        try:
            bids = self.licitacao_repo.find_active_bids_after_date(after_date, limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            
            message = f"{len(formatted_bids)} licitações ativas encontradas"
            if after_date:
                message += f" após {after_date}"
                
            return formatted_bids, message
        except Exception as e:
            logger.error(f"Erro ao buscar licitações ativas: {e}")
            return [], f"Erro ao buscar licitações ativas: {str(e)}"
    
    def get_high_value_bids(self, min_value: float = 1000000, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações de alto valor
        """
        try:
            bids = self.licitacao_repo.find_high_value_bids(min_value, limit)
            return self._format_bids_for_frontend(bids)
        except Exception as e:
            logger.error(f"Erro ao buscar licitações de alto valor: {e}")
            return []
    
    def create_bid(self, bid_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Criar nova licitação com validação de negócio
        """
        try:
            # Validações de negócio
            self._validate_bid_data(bid_data)
            
            # Verificar se licitação já existe por PNCP ID
            if bid_data.get('pncp_id'):
                existing = self.licitacao_repo.find_by_pncp_id(bid_data['pncp_id'])
                if existing:
                    return {
                        'success': False,
                        'message': 'Licitação já existe com este PNCP ID',
                        'data': None
                    }
            
            # Criar licitação
            created_bid = self.licitacao_repo.create(bid_data)
            
            logger.info(f"Licitação criada: {created_bid['id']}")
            
            return {
                'success': True,
                'message': 'Licitação criada com sucesso',
                'data': self._format_bid_for_frontend(created_bid)
            }
            
        except ValueError as e:
            logger.warning(f"Erro de validação ao criar licitação: {e}")
            return {
                'success': False,
                'message': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Erro ao criar licitação: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def update_bid(self, bid_id: str, bid_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualizar licitação existente com validação
        """
        try:
            # Verificar se licitação existe
            if not self.licitacao_repo.exists(bid_id):
                return {
                    'success': False,
                    'message': 'Licitação não encontrada',
                    'data': None
                }
            
            # Validar dados se necessário
            if 'valor_total_estimado' in bid_data:
                value = bid_data['valor_total_estimado']
                if not isinstance(value, (int, float)) or value < 0:
                    return {
                        'success': False,
                        'message': 'Valor deve ser um número positivo',
                        'data': None
                    }
            
            # Atualizar licitação
            updated_bid = self.licitacao_repo.update(bid_id, bid_data)
            
            if updated_bid:
                logger.info(f"Licitação atualizada: {bid_id}")
                return {
                    'success': True,
                    'message': 'Licitação atualizada com sucesso',
                    'data': self._format_bid_for_frontend(updated_bid)
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao atualizar licitação',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao atualizar licitação {bid_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def delete_bid(self, bid_id: str) -> Dict[str, Any]:
        """
        Deletar licitação
        """
        try:
            # Verificar se licitação existe
            bid = self.licitacao_repo.find_by_id(bid_id)
            if not bid:
                return {
                    'success': False,
                    'message': 'Licitação não encontrada',
                    'data': None
                }
            
            # Deletar licitação
            success = self.licitacao_repo.delete(bid_id)
            
            if success:
                logger.info(f"Licitação deletada: {bid_id}")
                return {
                    'success': True,
                    'message': 'Licitação deletada com sucesso',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao deletar licitação',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao deletar licitação {bid_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def get_bid_statistics(self) -> Dict[str, Any]:
        """
        Obter estatísticas gerais de licitações
        """
        try:
            # Usar o método get_statistics que já implementamos
            stats, message = self.get_statistics()
            return {
                'success': True,
                'data': stats,
                'message': message
            }
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas de licitações: {e}")
            return {
                'success': False,
                'message': f'Erro ao calcular estatísticas: {str(e)}'
            }
    
    def get_statistics(self) -> Tuple[Dict[str, Any], str]:
        """
        Obter estatísticas das licitações - método para BidController
        """
        try:
            # Buscar todas as licitações para calcular estatísticas
            all_bids = self.licitacao_repo.find_all(limit=None)
            
            if not all_bids:
                stats = {
                    'total_licitacoes': 0,
                    'message': 'Nenhuma licitação encontrada'
                }
                return stats, 'Nenhuma licitação para calcular estatísticas'
            
            total_licitacoes = len(all_bids)
            
            # Calcular estatísticas básicas
            stats = {
                'total_licitacoes': total_licitacoes,
                'valor_total_estimado': 0,
                'modalidades': {},
                'estados': {},
                'status_distribution': {},
                'recentes_30_dias': 0,
                'valor_medio': 0,
                'valor_maximo': 0,
                'valor_minimo': 0,
                'licitacoes_com_valor': 0,
                'last_updated': '2025-06-08T21:46:00Z'
            }
            
            # Análise detalhada
            valores = []
            for bid in all_bids:
                # Modalidades
                modalidade = bid.get('modalidade', 'Não especificada')
                stats['modalidades'][modalidade] = stats['modalidades'].get(modalidade, 0) + 1
                
                # Estados
                uf = bid.get('uf', 'Não especificado')
                stats['estados'][uf] = stats['estados'].get(uf, 0) + 1
                
                # Valores - garantir que não seja None
                valor_raw = bid.get('valor_total_estimado')
                if valor_raw is not None:
                    try:
                        valor = float(valor_raw)
                        if valor > 0:
                            valores.append(valor)
                            stats['valor_total_estimado'] += valor
                            stats['valor_maximo'] = max(stats['valor_maximo'], valor)
                            if stats['valor_minimo'] == 0:  # Primeira vez
                                stats['valor_minimo'] = valor
                            else:
                                stats['valor_minimo'] = min(stats['valor_minimo'], valor)
                    except (ValueError, TypeError):
                        # Ignorar valores inválidos
                        pass
            
            # Estatísticas de valores
            if valores:
                stats['valor_medio'] = stats['valor_total_estimado'] / len(valores)
                stats['licitacoes_com_valor'] = len(valores)
            else:
                stats['valor_minimo'] = 0
                stats['licitacoes_com_valor'] = 0
            
            # Ordenar por quantidade (top 10)
            stats['modalidades'] = dict(sorted(stats['modalidades'].items(), key=lambda x: x[1], reverse=True)[:10])
            stats['estados'] = dict(sorted(stats['estados'].items(), key=lambda x: x[1], reverse=True)[:10])
            
            message = f'Estatísticas de {total_licitacoes} licitações calculadas'
            return stats, message
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas de licitações: {e}")
            return {}, f"Erro ao calcular estatísticas: {str(e)}"
    
    def get_modalities_summary(self) -> List[Dict[str, Any]]:
        """Buscar resumo por modalidades"""
        try:
            return self.licitacao_repo.get_modalities_summary()
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de modalidades: {e}")
            return []
    
    def get_states_summary(self) -> List[Dict[str, Any]]:
        """Buscar resumo por estados"""
        try:
            return self.licitacao_repo.get_states_summary()
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de estados: {e}")
            return []
    
    def bulk_create_bids(self, bids_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Criar múltiplas licitações em lote com validação
        """
        try:
            # Validar todas as licitações antes de inserir
            validated_bids = []
            errors = []
            
            for i, bid_data in enumerate(bids_data):
                try:
                    self._validate_bid_data(bid_data)
                    validated_bids.append(bid_data)
                except Exception as e:
                    errors.append(f"Licitação {i+1}: {str(e)}")
            
            if errors:
                return {
                    'success': False,
                    'message': 'Erros de validação encontrados',
                    'data': {'errors': errors}
                }
            
            # Inserir licitações em lote
            created_ids = self.licitacao_repo.bulk_create_bids(validated_bids)
            
            logger.info(f"Importação em lote: {len(created_ids)} licitações criadas")
            
            return {
                'success': True,
                'message': f'{len(created_ids)} licitações criadas com sucesso',
                'data': {
                    'total_created': len(created_ids),
                    'bid_ids': created_ids
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na criação em lote de licitações: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def search_bids(self, search_filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar licitações com filtros avançados
        """
        try:
            # Processar filtros de valor
            if 'min_value' in search_filters and 'max_value' in search_filters:
                bids = self.licitacao_repo.find_by_value_range(
                    search_filters['min_value'],
                    search_filters['max_value'],
                    limit
                )
            elif 'min_value' in search_filters:
                bids = self.licitacao_repo.find_high_value_bids(
                    search_filters['min_value'],
                    limit
                )
            elif 'search_term' in search_filters:
                bids = self.licitacao_repo.search_by_object(
                    search_filters['search_term'],
                    limit
                )
            else:
                # Usar filtros simples
                bids = self.licitacao_repo.find_by_filters(search_filters, limit)
            
            return self._format_bids_for_frontend(bids)
            
        except Exception as e:
            logger.error(f"Erro ao buscar licitações com filtros: {e}")
            return []
    
    def _validate_bid_data(self, data: Dict[str, Any]):
        """Validações de negócio para dados de licitação"""
        required_fields = ['objeto_compra', 'orgao_nome']
        
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'Campo obrigatório ausente: {field}')
        
        # Validar valor se fornecido
        if 'valor_total_estimado' in data:
            value = data.get('valor_total_estimado')
            if value is not None and (not isinstance(value, (int, float)) or value < 0):
                raise ValueError('Valor total estimado deve ser um número positivo')
    
    def _format_bid_for_frontend(self, bid: Dict[str, Any]) -> Dict[str, Any]:
        """Formatar licitação individual para frontend com cálculo de status robusto"""
        from datetime import datetime, timezone, timedelta
        
        # Formatação de datas auxiliar
        def format_date(date_value):
            if date_value and hasattr(date_value, 'isoformat'):
                return date_value.isoformat()
            return date_value
        
        # Formatação de valores monetários
        def format_currency(value):
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return None
            return None
        
        # Cálculo de status baseado na data de encerramento
        def calculate_status(data_encerramento):
            """Calcular status: Ativa ou Fechada baseado na data de encerramento"""
            if not data_encerramento:
                return 'Indefinido'
            
            try:
                # Converter data de encerramento para datetime
                if isinstance(data_encerramento, str):
                    # Tentar diferentes formatos de data
                    try:
                        if 'T' in data_encerramento:
                            data_encerramento_dt = datetime.fromisoformat(data_encerramento.replace('Z', '+00:00'))
                        else:
                            data_encerramento_dt = datetime.fromisoformat(data_encerramento)
                        # Remover timezone para comparação simples
                        data_encerramento_dt = data_encerramento_dt.replace(tzinfo=None)
                    except:
                        # Fallback: tentar parse manual
                        data_clean = data_encerramento.replace('+00:00', '').replace('Z', '').replace('T', ' ')
                        data_encerramento_dt = datetime.fromisoformat(data_clean)
                else:
                    data_encerramento_dt = data_encerramento
                    if hasattr(data_encerramento_dt, 'replace'):
                        data_encerramento_dt = data_encerramento_dt.replace(tzinfo=None)
                    
                # Data atual (sem timezone para comparação simples)
                hoje = datetime.now()
                
                # Um dia antes da data de encerramento
                um_dia_antes = data_encerramento_dt - timedelta(days=1)
                
                # Se hoje é depois de um dia antes = Fechada, senão Ativa
                if hoje > um_dia_antes:
                    return 'Fechada'
                else:
                    return 'Ativa'
            except Exception as e:
                logger.warning(f"Erro ao calcular status para data {data_encerramento}: {e}")
                return 'Indefinido'
        
        # Formatação de valor para exibição 
        def format_valor_display(valor):
            """Retorna 'Sigiloso' se valor for 0 ou null, senão formata em BRL"""
            if valor is None or valor == 0:
                return 'Sigiloso'
            try:
                valor_float = float(valor)
                if valor_float <= 0:
                    return 'Sigiloso'
                return valor_float  # Retorna o número para o frontend formatar
            except:
                return 'Sigiloso'
        
        # Garantir que UF tenha valor ou seja uma string vazia
        def format_uf(uf_value):
            """Garantir que UF seja uma string válida"""
            if uf_value is None:
                return ''
            return str(uf_value).strip().upper()
        
        return {
            # ===== CAMPOS BÁSICOS =====
            'id': str(bid['id']),
            'pncp_id': bid.get('pncp_id'),
            'objeto_compra': bid.get('objeto_compra'),
            'orgao_cnpj': bid.get('orgao_cnpj'),
            'razao_social': bid.get('razao_social'),  # Nova razão social do órgão licitante
            'uf': format_uf(bid.get('uf')),  # UF formatado garantindo string válida
            # Novos campos da unidadeOrga
            'uf_nome': bid.get('uf_nome'),  # Nome completo do estado (ex: Minas Gerais)
            'nome_unidade': bid.get('nome_unidade'),  # Nome da unidade do órgão (ex: MUNICIPIO DE FRONTEIRA- MG)
            'municipio_nome': bid.get('municipio_nome'),  # Nome do município (ex: Fronteira)
            'codigo_ibge': bid.get('codigo_ibge'),  # Código IBGE do município
            'codigo_unidade': bid.get('codigo_unidade'),  # Código da unidade organizacional
            'status': bid.get('status'),
            'link_sistema_origem': bid.get('link_sistema_origem'),
            'data_publicacao': format_date(bid.get('data_publicacao')),
            'valor_total_estimado': format_currency(bid.get('valor_total_estimado')),
            'created_at': format_date(bid.get('created_at')),
            'updated_at': format_date(bid.get('updated_at')),
            
            # ===== CAMPOS CALCULADOS PARA FRONTEND =====
            'status_calculado': calculate_status(bid.get('data_encerramento_proposta')),
            'valor_display': format_valor_display(bid.get('valor_total_estimado')),
            
            # ===== NOVOS CAMPOS DA API 1 (LICITAÇÃO) =====
            'numero_controle_pncp': bid.get('numero_controle_pncp'),
            'numero_compra': bid.get('numero_compra'),
            'processo': bid.get('processo'),
            'valor_total_homologado': format_currency(bid.get('valor_total_homologado')),
            'data_abertura_proposta': format_date(bid.get('data_abertura_proposta')),
            'data_encerramento_proposta': format_date(bid.get('data_encerramento_proposta')),
            'modo_disputa_id': bid.get('modo_disputa_id'),
            'modo_disputa_nome': bid.get('modo_disputa_nome'),
            'srp': bid.get('srp'),  # Sistema de Registro de Preços
            'link_processo_eletronico': bid.get('link_processo_eletronico'),
            'justificativa_presencial': bid.get('justificativa_presencial'),
            
            # ===== CAMPOS CALCULADOS/INTELIGÊNCIA =====
            'is_srp': bid.get('srp', False),  # Alias mais claro
            'is_proposal_open': self._is_proposal_open(bid.get('data_encerramento_proposta')),
            'days_until_deadline': self._calculate_days_until_deadline(bid.get('data_encerramento_proposta')),
            'has_homologated_value': bid.get('valor_total_homologado') is not None,
            'disputa_mode_friendly': self._get_friendly_disputa_mode(bid.get('modo_disputa_nome')),
            
            # ===== CAMPOS EXTRAS (DE JOINS SE EXISTIREM) =====
            'tem_matches': bid.get('tem_matches', False),
            'total_matches': bid.get('total_matches', 0),
            'tem_itens': bid.get('tem_itens', False),
            'total_itens': bid.get('total_itens', 0)
        }
    
    def _format_bids_for_frontend(self, bids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formatar lista de licitações para frontend"""
        return [self._format_bid_for_frontend(bid) for bid in bids]
    
    # ===== FUNÇÕES AUXILIARES PARA CAMPOS CALCULADOS =====
    
    def _is_proposal_open(self, data_encerramento) -> bool:
        """Verificar se o prazo de propostas ainda está aberto"""
        if not data_encerramento:
            return False
        
        try:
            from datetime import datetime
            if isinstance(data_encerramento, str):
                from dateutil import parser
                data_encerramento = parser.parse(data_encerramento)
            
            return datetime.now() < data_encerramento.replace(tzinfo=None)
        except:
            return False
    
    def _calculate_days_until_deadline(self, data_encerramento) -> Optional[int]:
        """Calcular quantos dias faltam para o prazo final"""
        if not data_encerramento or not self._is_proposal_open(data_encerramento):
            return None
        
        try:
            from datetime import datetime
            if isinstance(data_encerramento, str):
                from dateutil import parser
                data_encerramento = parser.parse(data_encerramento)
            
            delta = data_encerramento.replace(tzinfo=None) - datetime.now()
            return max(0, delta.days)
        except:
            return None
    
    def _get_friendly_disputa_mode(self, modo_disputa_nome) -> str:
        """Converter modo de disputa para texto amigável"""
        if not modo_disputa_nome:
            return "Não especificado"
        
        friendly_names = {
            "Aberto": "🔓 Aberto - Preços visíveis durante disputa",
            "Fechado": "🔒 Fechado - Preços ocultos até final",
            "Aberto-Fechado": "🔓🔒 Misto - Inicia aberto, finaliza fechado"
        }
        
        return friendly_names.get(modo_disputa_nome, modo_disputa_nome)
    
    # ===== NOVOS MÉTODOS DE NEGÓCIO APROVEITANDO AS APIs =====
    
    def get_srp_opportunities(self, limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar oportunidades de Sistema de Registro de Preços (SRP)
        SRP permite fornecimento por até 1 ano - alta prioridade para empresas
        """
        try:
            bids = self.licitacao_repo.find_srp_licitacoes(limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            
            # Adicionar informações estratégicas
            for bid in formatted_bids:
                bid['strategic_note'] = "🏷️ SRP - Cadastro válido por até 1 ano"
                bid['opportunity_type'] = "high_value_recurring"
            
            message = f"{len(formatted_bids)} oportunidades SRP encontradas"
            logger.info(f"SRP opportunities requested: {len(formatted_bids)} found")
            return formatted_bids, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar oportunidades SRP: {e}")
            return [], f"Erro ao buscar oportunidades SRP: {str(e)}"
    
    def get_active_proposals(self, limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar licitações com propostas ainda abertas (timing crítico)
        """
        try:
            bids = self.licitacao_repo.find_active_proposals(limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            
            # Ordenar por urgência (prazo mais próximo primeiro)
            formatted_bids.sort(key=lambda x: x.get('days_until_deadline') or 999)
            
            # Adicionar alertas de urgência
            for bid in formatted_bids:
                days = bid.get('days_until_deadline', 0)
                if days <= 1:
                    bid['urgency_alert'] = "🚨 CRÍTICO - Menos de 24h!"
                    bid['urgency_level'] = "critical"
                elif days <= 3:
                    bid['urgency_alert'] = "⚠️ URGENTE - Poucos dias restantes"
                    bid['urgency_level'] = "high"
                elif days <= 7:
                    bid['urgency_alert'] = "📅 Prazo próximo"
                    bid['urgency_level'] = "medium"
                else:
                    bid['urgency_level'] = "low"
            
            message = f"{len(formatted_bids)} propostas abertas encontradas"
            return formatted_bids, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar propostas ativas: {e}")
            return [], f"Erro ao buscar propostas ativas: {str(e)}"
    
    def get_bids_by_disputa_mode(self, modo_disputa_id: int, limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar licitações por modo de disputa específico
        """
        try:
            bids = self.licitacao_repo.find_by_modo_disputa(modo_disputa_id, limit)
            formatted_bids = self._format_bids_for_frontend(bids)
            
            mode_names = {
                1: "Aberto",
                2: "Fechado", 
                3: "Aberto-Fechado"
            }
            
            mode_name = mode_names.get(modo_disputa_id, f"Modo {modo_disputa_id}")
            message = f"{len(formatted_bids)} licitações em modo {mode_name}"
            
            return formatted_bids, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar por modo de disputa {modo_disputa_id}: {e}")
            return [], f"Erro ao buscar por modo de disputa: {str(e)}"
    
    def get_materials_opportunities(self, limit: int = 100) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar itens de MATERIAL (não serviços) para empresas que fornecem produtos
        """
        try:
            items = self.licitacao_repo.find_items_by_material_servico('M', limit)
            formatted_items = self._format_items_for_frontend(items)
            
            message = f"{len(formatted_items)} oportunidades de MATERIAIS encontradas"
            return formatted_items, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar oportunidades de materiais: {e}")
            return [], f"Erro ao buscar oportunidades de materiais: {str(e)}"
    
    def get_services_opportunities(self, limit: int = 100) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar itens de SERVIÇO (não materiais) para empresas prestadoras de serviços
        """
        try:
            items = self.licitacao_repo.find_items_by_material_servico('S', limit)
            formatted_items = self._format_items_for_frontend(items)
            
            message = f"{len(formatted_items)} oportunidades de SERVIÇOS encontradas"
            return formatted_items, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar oportunidades de serviços: {e}")
            return [], f"Erro ao buscar oportunidades de serviços: {str(e)}"
    
    def get_me_epp_opportunities(self, limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar itens exclusivos para Micro e Pequenas Empresas (ME/EPP)
        """
        try:
            items = self.licitacao_repo.find_items_me_epp_only(limit)
            formatted_items = self._format_items_for_frontend(items)
            
            # Adicionar destaque para exclusividade
            for item in formatted_items:
                item['exclusive_highlight'] = "👥 EXCLUSIVO ME/EPP - Sem concorrência de grandes empresas"
                item['competitive_advantage'] = "high"
            
            message = f"{len(formatted_items)} oportunidades EXCLUSIVAS ME/EPP encontradas"
            return formatted_items, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar oportunidades ME/EPP: {e}")
            return [], f"Erro ao buscar oportunidades ME/EPP: {str(e)}"
    
    def search_by_ncm_code(self, ncm_codigo: str, limit: int = 50) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar itens por código NCM específico - muito preciso para empresas especializadas
        """
        try:
            items = self.licitacao_repo.find_items_by_ncm(ncm_codigo, limit)
            formatted_items = self._format_items_for_frontend(items)
            
            message = f"{len(formatted_items)} itens encontrados para NCM {ncm_codigo}"
            return formatted_items, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar por NCM {ncm_codigo}: {e}")
            return [], f"Erro ao buscar por NCM: {str(e)}"
    
    def get_enhanced_statistics(self) -> Tuple[Dict[str, Any], str]:
        """
        Estatísticas aprimoradas usando os novos campos das APIs
        """
        try:
            stats = self.licitacao_repo.get_enhanced_statistics()
            
            # Adicionar insights estratégicos
            insights = []
            
            if stats.get('total_srp', 0) > 0:
                srp_percentage = (stats['total_srp'] / stats.get('total_licitacoes', 1)) * 100
                insights.append(f"🏷️ {srp_percentage:.1f}% das licitações são SRP (oportunidades recorrentes)")
            
            if stats.get('tipos_item'):
                for tipo in stats['tipos_item']:
                    tipo_name = "Materiais" if tipo['material_ou_servico'] == 'M' else "Serviços"
                    insights.append(f"📊 {tipo['quantidade']} itens de {tipo_name} disponíveis")
            
            stats['business_insights'] = insights
            stats['last_analysis'] = '2025-06-08T21:46:00Z'
            
            message = "Estatísticas aprimoradas calculadas com sucesso"
            return stats, message
            
        except Exception as e:
            logger.error(f"Erro ao calcular estatísticas aprimoradas: {e}")
            return {}, f"Erro ao calcular estatísticas: {str(e)}"
    
    def get_bid_items(self, pncp_id: str, licitacao_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """🔄 UPDATED: Buscar itens usando novo PNCPAdapter"""
        try:
            if not pncp_id:
                return {'success': False, 'message': 'PNCP ID não fornecido'}

            # 1. Verificar se a licitação já existe no banco
            licitacao_local = self.licitacao_repo.find_by_pncp_id(pncp_id)

            # 2. Se não existir, criar a partir dos dados do POST ou da API
            if not licitacao_local:
                logger.info(f"Licitação {pncp_id} não encontrada localmente. Tentando salvar...")
                converted_bid = None

                if licitacao_data:
                    logger.info(f"Usando dados da licitação providos pelo frontend para {pncp_id}")
                    converted_bid = self._convert_frontend_bid_data(licitacao_data)
                else:
                    # 🆕 NEW: Usar PNCPAdapter para buscar detalhes
                    logger.info(f"Buscando detalhes via PNCPAdapter para {pncp_id}")
                    if self.pncp_adapter:
                        opportunity_data = self.pncp_adapter.get_opportunity_details(pncp_id)
                        if opportunity_data:
                            converted_bid = self._convert_opportunity_data_to_bid(opportunity_data, pncp_id)
                        else:
                            # Fallback para API antiga
                            detailed_bid = self.pncp_repo.buscar_licitacao_detalhada(pncp_id)
                            if detailed_bid:
                                converted_bid = self._convert_api_bid_data(detailed_bid, pncp_id)
                    else:
                        # Fallback direto para API antiga
                        detailed_bid = self.pncp_repo.buscar_licitacao_detalhada(pncp_id)
                        if detailed_bid:
                            converted_bid = self._convert_api_bid_data(detailed_bid, pncp_id)

                if not converted_bid:
                    msg = "Dados da licitação não puderam ser obtidos ou convertidos."
                    logger.error(f"❌ {msg} para PNCP ID: {pncp_id}")
                    return {'success': False, 'message': msg}

                try:
                    # Usar create_or_update para evitar duplicação
                    licitacao_local = self.licitacao_repo.create_or_update(converted_bid, 'numero_controle_pncp')
                    logger.info(f"✅ Licitação {pncp_id} salva/atualizada com sucesso. ID local: {licitacao_local.get('id')}")
                except Exception as e:
                    logger.error(f"❌ Falha ao salvar licitação {pncp_id}: {e}", exc_info=True)
                    return {'success': False, 'message': f"Erro ao salvar licitação: {e}"}

            licitacao_db_id = licitacao_local.get('id')
            if not licitacao_db_id:
                return {'success': False, 'message': 'Não foi possível obter o ID da licitação no banco de dados.'}

            # 3. 🆕 NEW: Buscar itens via PNCPAdapter
            api_items = self._fetch_items_via_adapter(pncp_id)

            if not api_items:
                logger.info(f"Nenhum item encontrado para {pncp_id}")
                return {
                    'success': True,
                    'data': {'itens': [], 'licitacao': self._format_bid_for_frontend(licitacao_local)},
                    'message': 'Licitação encontrada, mas sem itens disponíveis.'
                }

            logger.info(f"✅ {len(api_items)} itens encontrados para {pncp_id}. Tentando salvar...")

            try:
                db_items = [
                    {
                        'licitacao_id': licitacao_db_id,
                        'numero_item': item.get('numeroItem'),  # 🔧 FIX: Usar 'numeroItem' da API v1 PNCP
                        'descricao': item.get('descricao'),
                        'quantidade': item.get('quantidade'),
                        'unidade_medida': item.get('unidadeMedida'),
                        'valor_unitario_estimado': item.get('valorUnitarioEstimado'),
                        'valor_total': item.get('valorTotal'),
                        'material_ou_servico': item.get('materialOuServico'),
                        'criterio_julgamento_nome': item.get('criterioJulgamentoNome'),
                        'situacao_item': item.get('situacaoCompraItemNome'),
                        'especificacao_tecnica': item.get('informacaoComplementar'),
                        # 🆕 NOVOS CAMPOS DA API v1
                        'criterio_julgamento_id': item.get('criterioJulgamentoId'),
                        'situacao_item_id': item.get('situacaoCompraItem'),
                        'codigo_produto_servico': item.get('catalogoCodigoItem'),
                        'ncm_nbs_codigo': item.get('ncmNbsCodigo'),
                        'tipo_beneficio_id': item.get('tipoBeneficio'),
                        'tipo_beneficio_nome': item.get('tipoBeneficioNome'),
                        'beneficio_micro_epp': item.get('tipoBeneficio') == 1 if item.get('tipoBeneficio') else False,
                        'tem_resultado': item.get('temResultado', False),
                        'dados_api_completos': json.dumps(item)  # 🔧 FIX: Converter dict para JSON string
                    } for item in api_items]
                
                # Salvar itens no banco (se repositório suportar)
                try:
                    num_saved = self.licitacao_repo.create_or_update_bulk_items(db_items, ['licitacao_id', 'numero_item'])
                    logger.info(f"✅ {num_saved} itens salvos/atualizados para a licitação ID {licitacao_db_id}")
                except AttributeError:
                    logger.warning("⚠️ Método create_or_update_bulk_items não disponível no repositório")
                except Exception as e:
                    logger.error(f"⚠️ Falha ao salvar itens: {e}")
            except Exception as e:
                logger.error(f"⚠️ Erro ao processar itens para salvamento: {e}")

            return {
                'success': True,
                'data': {'itens': api_items, 'licitacao': self._format_bid_for_frontend(licitacao_local)},
                'message': f"{len(api_items)} itens encontrados e processados."
            }

        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens da licitação {pncp_id}: {e}", exc_info=True)
            return {'success': False, 'message': f"Erro ao buscar itens: {str(e)}"}
    
    def _fetch_items_via_adapter(self, pncp_id: str) -> List[Dict[str, Any]]:
        """🆕 NEW: Buscar itens via PNCPAdapter com fallback para API antiga"""
        try:
            # Tentar usar PNCPAdapter primeiro
            if self.pncp_adapter:
                logger.info(f"🔍 Buscando itens via PNCPAdapter para {pncp_id}")
                items_data = self.pncp_adapter.get_opportunity_items(pncp_id)
                
                if items_data and isinstance(items_data, list):
                    logger.info(f"✅ {len(items_data)} itens encontrados via PNCPAdapter")
                    return items_data
                else:
                    logger.info("⚠️ PNCPAdapter não retornou itens, tentando fallback")
            
            # Fallback para método antigo
            logger.info(f"🔄 Fallback: Usando método antigo para buscar itens de {pncp_id}")
            return self._fetch_items_from_pncp_api(pncp_id)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar itens via adapter: {e}")
            # Fallback em caso de erro
            return self._fetch_items_from_pncp_api(pncp_id)
    
    def _convert_frontend_bid_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Converte dados da licitação vindos do frontend para o formato do banco de dados."""
        pncp_id = data.get('numero_controle_pncp') or data.get('pncp_id')
        orgao_entidade = data.get('orgao_entidade') or data.get('orgaoEntidade') or {}
        unidade_orgao = data.get('unidade_orgao') or data.get('unidadeOrgao') or {}

        return {
            'pncp_id': pncp_id,  # Campo principal para identificação
            'numero_controle_pncp': pncp_id,
            'objeto_compra': data.get('objeto_compra') or data.get('objetoCompra'),
            'valor_total_estimado': data.get('valor_total_estimado') or data.get('valorTotalEstimado'),
            'modalidade_nome': data.get('modalidade_nome') or data.get('modalidadeNome'),
            'situacao_compra_nome': data.get('situacao_compra_nome') or data.get('situacaoCompraNome'),
            'data_publicacao_pncp': data.get('data_publicacao_pncp') or data.get('dataPublicacaoPncp'),
            'data_abertura_proposta': data.get('data_abertura_proposta') or data.get('dataAberturaProposta'),
            'data_encerramento_proposta': data.get('data_encerramento_proposta') or data.get('dataEncerramentoProposta'),
            'link_sistema_origem': data.get('link_sistema_origem') or data.get('linkSistemaOrigem'),
            'orgao_cnpj': orgao_entidade.get('cnpj'),
            'razao_social': orgao_entidade.get('razaoSocial'),
            'nome_unidade': unidade_orgao.get('nomeUnidade'),
            'municipio_nome': unidade_orgao.get('municipioNome'),
            'uf': unidade_orgao.get('ufSigla') or unidade_orgao.get('uf'),
            'ano_compra': self._extract_year_from_pncp_id(pncp_id),
            'sequencial_compra': self._extract_sequential_from_pncp_id(pncp_id),
        }

    def _convert_api_item_data(self, api_item: Dict[str, Any], licitacao_db_id: int) -> Dict[str, Any]:
        """Converte um item da API do PNCP para o formato do banco de dados."""
        return {
            'licitacao_id': licitacao_db_id,
            'numero_item': api_item.get('numeroItem'),
            'descricao': api_item.get('descricao'),
            'quantidade': api_item.get('quantidade'),
            'unidade_medida': api_item.get('unidadeMedida'),
            'valor_unitario_estimado': api_item.get('valorUnitarioEstimado'),
            'situacao_item_id': api_item.get('situacaoCompraItemId'),
            'criterio_julgamento_id': api_item.get('criterioJulgamentoId')
        }

    def _fetch_items_from_pncp_api(self, pncp_id: str) -> List[Dict[str, Any]]:
        """Busca itens diretamente na API do PNCP."""
        
        # O PNCP ID do frontend vem com / no final, ex: .../2025/
        parsed_id = self.pncp_repo._parse_pncp_id(pncp_id)
        if not parsed_id:
            return []

        pncp_api_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{parsed_id['cnpj']}/compras/{parsed_id['ano']}/{parsed_id['sequencial']}/itens"
        
        try:
            logger.info(f"Consultando API de itens: {pncp_api_url}")
            response = requests.get(pncp_api_url, timeout=20)
            response.raise_for_status()
            
            # A API pode retornar uma string vazia com status 200 se não houver itens
            if not response.text:
                logger.info(f"Nenhum item retornado pela API do PNCP para {pncp_id}")
                return []

            items_api = response.json()
            if not items_api:
                return []
            
            logger.info(f"✅ {len(items_api)} itens encontrados na API do PNCP para {pncp_id}")
            return items_api
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 404:
                logger.warning(f"Itens não encontrados na API do PNCP (404) para {pncp_id}")
            else:
                logger.error(f"Erro HTTP ao buscar itens na API do PNCP: {http_err}")
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar itens na API do PNCP: {e}", exc_info=True)
            
        return []

    def _format_items_for_frontend(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formatar itens de licitação para o frontend com campos necessários
        """
        formatted_items = []
        for item in items:
            formatted_item = {
                'id': item.get('id'),
                'numero_item': item.get('numeroItem') or item.get('numero_item'),
                'descricao': item.get('descricao') or item.get('nome_item'),
                'descricao_complementar': item.get('descricaoComplementar') or item.get('descricao_complementar'),
                'quantidade': item.get('quantidade'),
                'valor_unitario': item.get('valorUnitarioEstimado') or item.get('valor_unitario'),
                'valor_total': item.get('valorTotal') or item.get('valor_total_estimado', item.get('valor_unitario', 0) * item.get('quantidade', 0)),
                'ncm_nbs': item.get('ncmNbsCodigo') or item.get('ncm_nbs'),
                'unidade_medida': item.get('unidadeMedida') or item.get('unidade_medida'),
                'material_ou_servico': item.get('materialOuServico') or item.get('material_ou_servico'),
                'beneficio_micro_epp': item.get('tipoBeneficio') or item.get('beneficio_micro_epp', False),
                'participacao_exclusiva_me_epp': item.get('tipoBeneficio') == 1,
                'pncp_id': item.get('licitacao_pncp_id'),
                'criterio_julgamento': item.get('criterioJulgamentoNome') or item.get('criterio_julgamento'),
                'criterio_valor_nome': item.get('criterioJulgamentoNome') or item.get('criterio_valor_nome')
            }
            formatted_items.append(formatted_item)
        return formatted_items
    
    # ===== NOVOS MÉTODOS PARA PREPARAÇÃO AUTOMÁTICA DE ANÁLISE =====
    
    def start_document_preparation(self, licitacao_id: str, pncp_id: str) -> Tuple[Dict[str, Any], str]:
        """
        Iniciar processamento automático de documentos de uma licitação
        """
        try:
            # Importar o UnifiedDocumentProcessor aqui para evitar imports circulares
            from core.unified_document_processor import UnifiedDocumentProcessor
            import os
            
            logger.info(f"🚀 Iniciando preparação automática para licitacao_id: {licitacao_id}, pncp_id: {pncp_id}")
            
            # Verificar se licitação existe
            bid = self.licitacao_repo.find_by_pncp_id(pncp_id)
            if not bid:
                raise ValueError(f"Licitação com PNCP ID {pncp_id} não encontrada")
            
            # 🔧 CORREÇÃO: Obter configurações corretas do Supabase (priorizar SERVICE_KEY)
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # 🎯 USAR APENAS SERVICE_KEY
            
            # Fallback se SERVICE_KEY não existir (mas alertar)
            if not supabase_key:
                logger.warning("⚠️ SUPABASE_SERVICE_KEY não encontrada, usando ANON_KEY (pode causar erro 403)")
                supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Configurações do Supabase não encontradas")
            
            logger.info(f"🔧 Usando Supabase URL: {supabase_url}")
            logger.info(f"🔑 Tipo de chave: {'SERVICE_KEY' if os.getenv('SUPABASE_SERVICE_KEY') else 'ANON_KEY'}")
            
            # Instanciar o processador com configurações corretas
            from config.database import db_manager
            processor = UnifiedDocumentProcessor(db_manager, supabase_url, supabase_key)
            
            # Iniciar processamento
            logger.info("📋 Iniciando processamento de documentos...")
            
            # 🔧 CORREÇÃO: Usar método síncrono de processamento
            result = processor.processar_licitacao_sync(
                licitacao_id=licitacao_id,
                pncp_id=pncp_id,
                bid=bid
            )
            
            if result.get('success'):
                logger.info(f"✅ Processamento concluído: {result.get('documentos_processados', 0)} documentos")
                return {
                    'success': True,
                    'message': 'Preparação iniciada com sucesso',
                    'details': {
                        'licitacao_id': licitacao_id,
                        'pncp_id': pncp_id,
                        'documentos_processados': result.get('documentos_processados', 0),
                        'documentos_total': result.get('documentos_total', 0),
                        'tempo_processamento': result.get('tempo_processamento', 0)
                    }
                }, "Documentos preparados com sucesso"
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Erro no processamento'),
                    'details': result
                }, f"Erro na preparação: {result.get('error', 'Desconhecido')}"
                
        except Exception as e:
            logger.error(f"❌ Erro na preparação: {e}")
            return {
                'success': False,
                'error': str(e)
            }, f"Erro interno: {str(e)}"
    
    def get_preparation_status(self, licitacao_id: str) -> Tuple[Dict[str, Any], str]:
        """
        Verificar status da preparação de documentos de uma licitação
        """
        try:
            # Importar aqui para evitar imports circulares
            from core.unified_document_processor import UnifiedDocumentProcessor
            import os
            
            logger.info(f"📊 Verificando status de preparação para licitacao_id: {licitacao_id}")
            
            # 🔧 CORREÇÃO: Obter configurações corretas do Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            
            if not supabase_key:
                logger.warning("⚠️ SUPABASE_SERVICE_KEY não encontrada, usando ANON_KEY")
                supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Configurações do Supabase não encontradas")
            
            # Instanciar o processador
            from config.database import db_manager
            processor = UnifiedDocumentProcessor(db_manager, supabase_url, supabase_key)
            
            # 🔧 CORREÇÃO: Verificar status real dos documentos
            try:
                # Verificar documentos no banco de dados
                with db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT COUNT(*) as total_docs,
                                   COUNT(CASE WHEN arquivo_nuvem_url IS NOT NULL THEN 1 END) as docs_processados,
                                   COUNT(CASE WHEN texto_preview IS NOT NULL THEN 1 END) as docs_com_texto
                            FROM documentos_licitacao 
                            WHERE licitacao_id = %s
                        """, (licitacao_id,))
                        
                        result = cursor.fetchone()
                        total_docs = result[0] if result else 0
                        docs_processados = result[1] if result else 0
                        docs_com_texto = result[2] if result else 0
                
                # Determinar status baseado nos resultados
                if total_docs == 0:
                    status = 'not_started'
                    status_message = 'Nenhum documento encontrado'
                    progress = 0
                elif docs_processados == 0:
                    status = 'processing'
                    status_message = 'Iniciando processamento de documentos...'
                    progress = 5
                elif docs_processados < total_docs:
                    status = 'processing'
                    progress = int((docs_processados / total_docs) * 80)  # Até 80% para processamento
                    status_message = f'Processando documentos ({docs_processados}/{total_docs})'
                elif docs_com_texto < docs_processados:
                    status = 'processing'
                    progress = 85
                    status_message = 'Extraindo texto dos documentos...'
                else:
                    status = 'ready'
                    progress = 100
                    status_message = 'Preparação concluída com sucesso'
                
                logger.info(f"📊 Status calculado: {status} ({progress}%) - {total_docs} docs, {docs_processados} processados")
                
                return {
                    'success': True,
                    'licitacao_id': licitacao_id,
                    'status': status,
                    'progress': progress,
                    'message': status_message,
                    'details': {
                        'total_documents': total_docs,
                        'processed_documents': docs_processados,
                        'documents_with_text': docs_com_texto,
                        'estimated_completion_time': None  # TODO: implementar se necessário
                    }
                }, status_message
                
            except Exception as db_error:
                logger.error(f"❌ Erro ao consultar banco: {db_error}")
                return {
                    'success': False,
                    'licitacao_id': licitacao_id,
                    'status': 'error',
                    'progress': 0,
                    'message': 'Erro ao verificar status no banco de dados',
                    'error': str(db_error)
                }, f"Erro de banco: {str(db_error)}"
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {e}")
            return {
                'success': False,
                'licitacao_id': licitacao_id,
                'status': 'error',
                'progress': 0,
                'message': 'Erro interno ao verificar status',
                'error': str(e)
            }, f"Erro interno: {str(e)}"
    
    def cleanup_failed_preparation(self, licitacao_id: str) -> Tuple[Dict[str, Any], str]:
        """
        Limpar preparação que falhou, permitindo nova tentativa
        """
        try:
            from core.unified_document_processor import UnifiedDocumentProcessor
            import os
            
            logger.info(f"🧹 Limpando preparação falhada para {licitacao_id}")
            
            # Obter configurações do Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY', os.getenv('SUPABASE_ANON_KEY'))
            
            if not supabase_url or not supabase_key:
                raise ValueError("Configurações do Supabase não encontradas")
            
            # Instanciar o processador
            from config.database import db_manager
            processor = UnifiedDocumentProcessor(db_manager, supabase_url, supabase_key)
            result = processor.cleanup_failed_processing(licitacao_id)
            
            return {
                'licitacao_id': licitacao_id,
                'cleanup_status': 'success',
                'files_removed': result.get('files_removed', 0)
            }, "Limpeza concluída, nova preparação pode ser iniciada"
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza para {licitacao_id}: {str(e)}")
            return {
                'licitacao_id': licitacao_id,
                'cleanup_status': 'error',
                'error': str(e)
            }, f"Erro na limpeza: {str(e)}"

    # ===== Helpers de parsing de PNCP ID =====

    def _extract_year_from_pncp_id(self, pncp_id: str) -> Optional[int]:
        """Extrai o ano (parte após a barra) do PNCP ID. Ex: 08584229000122-1-000013/2025 → 2025"""
        if not pncp_id:
            return None
        try:
            return int(pncp_id.strip('/').split('/')[-1])
        except Exception:
            return None

    def _extract_sequential_from_pncp_id(self, pncp_id: str) -> Optional[int]:
        """Extrai o número sequencial da compra do PNCP ID. Ex: ...-000013/2025 → 13"""
        if not pncp_id:
            return None
        try:
            main_part = pncp_id.strip('/').split('-')[-1]
            seq_part = main_part.split('/')[0]
            seq_clean = seq_part.lstrip('0') or seq_part  # remove zeros à esquerda
            return int(seq_clean)
        except Exception:
            return None
    
    # ===== UNIFIED SEARCH METHODS (Phase 3 - Service Layer Abstraction) =====
    
    async def search_unified(self, filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Search opportunities using the unified multi-source search service
        
        This method provides the new multi-source search functionality while
        maintaining the same interface pattern as existing BidService methods.
        
        Args:
            filters: Dictionary with search criteria
            
        Returns:
            Tuple of (opportunities_list, message) for consistency with existing methods
        """
        try:
            logger.info(f"🔍 Starting unified search with filters: {filters}")
            
            # Check if unified search service is available
            if not self.unified_search_service:
                logger.warning("UnifiedSearchService not available, falling back to PNCP search")
                return self._fallback_to_pncp_search(filters)
            
            # Convert dictionary filters to SearchFilters object
            search_filters = self._convert_dict_to_search_filters(filters)
            
            # Perform unified search (await async call)
            combined_results = await self.unified_search_service.search_combined(search_filters)
            
            # Convert to frontend format (similar to existing bid formatting)
            formatted_results = []
            for result in combined_results:
                formatted_result = self._format_unified_result_for_frontend(result)
                formatted_results.append(formatted_result)
            
            message = f"{len(formatted_results)} opportunities found across all providers"
            
            logger.info(f"✅ Unified search completed: {len(formatted_results)} opportunities")
            
            return formatted_results, message
            
        except Exception as e:
            logger.error(f"❌ Error in unified search: {e}")
            # Fallback to traditional PNCP search
            return self._fallback_to_pncp_search(filters)
    
    async def get_unified_provider_stats(self) -> Tuple[Dict[str, Any], str]:
        """
        Get statistics and health information for all unified search providers
        
        Returns:
            Tuple of (stats_dict, message) for consistency with existing methods
        """
        try:
            logger.info("📊 Getting unified provider statistics")
            
            if not self.unified_search_service:
                return {}, "UnifiedSearchService not available"
            
            stats = await self.unified_search_service.get_provider_stats()
            
            message = f"Provider stats retrieved: {stats.get('summary', {}).get('active_providers', 0)} active providers"
            
            logger.info(f"✅ Provider stats retrieved successfully")
            
            return stats, message
            
        except Exception as e:
            logger.error(f"❌ Error getting provider stats: {e}")
            return {}, f"Error getting provider stats: {str(e)}"
    
    async def search_by_provider(self, provider_name: str, filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Search opportunities from a specific provider using unified search
        
        Args:
            provider_name: Name of the provider to search (e.g., 'pncp')
            filters: Dictionary with search criteria
            
        Returns:
            Tuple of (opportunities_list, message) for consistency with existing methods
        """
        try:
            logger.info(f"🔍 Starting provider-specific search: {provider_name}")
            
            if not self.unified_search_service:
                logger.warning("UnifiedSearchService not available")
                if provider_name.lower() == 'pncp':
                    return self._fallback_to_pncp_search(filters)
                else:
                    return [], f"Provider {provider_name} not available"
            
            # Convert dictionary filters to SearchFilters object
            search_filters = self._convert_dict_to_search_filters(filters)
            
            # Search specific provider (await async call)
            opportunities = await self.unified_search_service.search_by_provider(provider_name, search_filters)
            
            # Convert to frontend format
            formatted_results = []
            for opportunity in opportunities:
                opportunity_dict = self.unified_search_service._opportunity_to_dict(opportunity)
                opportunity_dict['provider_name'] = provider_name
                formatted_result = self._format_unified_result_for_frontend(opportunity_dict)
                formatted_results.append(formatted_result)
            
            message = f"{len(formatted_results)} opportunities found from {provider_name}"
            
            logger.info(f"✅ Provider search completed: {len(formatted_results)} opportunities from {provider_name}")
            
            return formatted_results, message
            
        except Exception as e:
            logger.error(f"❌ Error in provider search: {e}")
            return [], f"Error searching {provider_name}: {str(e)}"
    
    async def validate_provider_health(self, provider_name: str = None) -> Tuple[Dict[str, Any], str]:
        """
        Validate health/connectivity of providers
        
        Args:
            provider_name: Optional specific provider to validate (if None, validates all)
            
        Returns:
            Tuple of (validation_results, message)
        """
        try:
            logger.info(f"🔍 Validating provider health: {provider_name or 'all providers'}")
            
            if not self.unified_search_service:
                return {}, "UnifiedSearchService not available"
            
            if provider_name:
                # Validate specific provider (await async call)
                is_connected = await self.unified_search_service.validate_provider_connection(provider_name)
                result = {provider_name: is_connected}
                message = f"{provider_name}: {'Connected' if is_connected else 'Disconnected'}"
            else:
                # Validate all providers (await async call)
                stats = await self.unified_search_service.get_provider_stats()
                result = {
                    name: info.get('connected', False)
                    for name, info in stats.get('providers', {}).items()
                }
                connected_count = sum(1 for connected in result.values() if connected)
                message = f"{connected_count}/{len(result)} providers connected"
            
            logger.info(f"✅ Provider validation completed")
            
            return result, message
            
        except Exception as e:
            logger.error(f"❌ Error validating providers: {e}")
            return {}, f"Error validating providers: {str(e)}"
    
    def _convert_dict_to_search_filters(self, filters: Dict[str, Any]):
        """
        Convert dictionary filters to SearchFilters object
        
        Args:
            filters: Dictionary with search criteria
            
        Returns:
            SearchFilters object
        """
        try:
            from interfaces.procurement_data_source import SearchFilters
            
            # Map common filter names to SearchFilters parameters
            search_filters = SearchFilters(
                keywords=filters.get('keywords') or filters.get('search_term'),
                # keywords=filters.get('keywords'),
                region_code=filters.get('region_code') or filters.get('uf'),
                country_code=filters.get('country_code', 'BR'),
                min_value=filters.get('min_value'),
                max_value=filters.get('max_value'),
                # currency_code=filters.get('currency_code', 'BRL'),
                publication_date_from=filters.get('publication_date_from'),
                publication_date_to=filters.get('publication_date_to'),
                # submission_deadline_from=filters.get('submission_deadline_from'),
                # submission_deadline_to=filters.get('submission_deadline_to'),
                page=filters.get('page', 1),
                page_size=filters.get('page_size', 20),
                # sort_by=filters.get('sort_by'),
                # sort_order=filters.get('sort_order')
            )
            
            return search_filters
            
        except Exception as e:
            logger.error(f"❌ Error converting filters: {e}")
            # Return default SearchFilters if conversion fails
            from interfaces.procurement_data_source import SearchFilters
            return SearchFilters()
    
    def _format_unified_result_for_frontend(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format unified search result for frontend consumption
        
        This method converts unified search results to a format similar to
        existing bid formatting to maintain frontend compatibility.
        
        Args:
            result: Dictionary with unified search result
            
        Returns:
            Dictionary formatted for frontend
        """
        try:
            # Extract provider information
            provider_name = result.get('provider_name', 'unknown')
            provider_metadata = result.get('provider_metadata', {})
            
            # Create formatted result similar to existing bid format
            formatted_result = {
                # Basic opportunity information
                'id': result.get('external_id'),
                'pncp_id': result.get('external_id') if provider_name == 'pncp' else None,
                'external_id': result.get('external_id'),
                'title': result.get('title'),
                'objeto_compra': result.get('title'),  # Alias for compatibility
                'description': result.get('description'),
                'estimated_value': result.get('estimated_value'),
                'valor_total_estimado': result.get('estimated_value'),  # Alias for compatibility
                'currency_code': result.get('currency_code', 'BRL'),
                
                # Location information
                'country_code': result.get('country_code'),
                'region_code': result.get('region_code'),
                'uf': result.get('region_code'),  # Alias for compatibility
                'municipality': result.get('municipality'),
                'municipio_nome': result.get('municipality'),  # Alias for compatibility
                
                # Date information
                'publication_date': result.get('publication_date'),
                'data_publicacao': result.get('publication_date'),  # Alias for compatibility
                'submission_deadline': result.get('submission_deadline'),
                'data_encerramento_proposta': result.get('submission_deadline'),  # Alias for compatibility
                
                # Entity information
                'procuring_entity_id': result.get('procuring_entity_id'),
                'orgao_cnpj': result.get('procuring_entity_id'),  # Alias for compatibility
                'procuring_entity_name': result.get('procuring_entity_name'),
                'razao_social': result.get('procuring_entity_name'),  # Alias for compatibility
                
                # Provider information (new in unified search)
                'provider_name': provider_name,
                'provider_metadata': provider_metadata,
                'source_type': 'unified_search',
                
                # Provider-specific data
                'provider_specific_data': result.get('provider_specific_data', {}),
                
                # Compatibility fields
                'status_calculado': self._calculate_unified_status(result),
                'valor_display': self._format_unified_value_display(result.get('estimated_value')),
                'is_proposal_open': self._is_unified_proposal_open(result.get('submission_deadline'))
            }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"❌ Error formatting unified result: {e}")
            # Return minimal result if formatting fails
            return {
                'id': result.get('external_id', 'unknown'),
                'title': result.get('title', 'Unknown'),
                'provider_name': result.get('provider_name', 'unknown'),
                'error': f"Formatting error: {str(e)}"
            }
    
    def _fallback_to_pncp_search(self, filters: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Fallback to traditional PNCP search when unified search is not available
        
        Args:
            filters: Dictionary with search criteria
            
        Returns:
            Tuple of (opportunities_list, message)
        """
        try:
            logger.info("🔄 Falling back to traditional PNCP search")
            
            # Use existing search method based on available filters
            if 'search_term' in filters or 'keywords' in filters:
                search_term = filters.get('search_term') or filters.get('keywords')
                limit = filters.get('page_size', 50)
                results = self.search_bids_by_object(search_term, limit)
                message = f"PNCP fallback search: {len(results)} results for '{search_term}'"
            elif 'uf' in filters or 'region_code' in filters:
                uf = filters.get('uf') or filters.get('region_code')
                limit = filters.get('page_size', 50)
                results = self.get_bids_by_state(uf, limit)
                message = f"PNCP fallback search: {len(results)} results for state {uf}"
            elif 'min_value' in filters or 'max_value' in filters:
                min_val = filters.get('min_value', 0)
                max_val = filters.get('max_value', float('inf'))
                limit = filters.get('page_size', 50)
                results = self.get_bids_by_value_range(min_val, max_val, limit)
                message = f"PNCP fallback search: {len(results)} results for value range"
            else:
                # Default to recent bids
                limit = filters.get('page_size', 20)
                results, message = self.get_recent_bids(limit)
                message = f"PNCP fallback search: {message}"
            
            # Add provider information to results for consistency
            for result in results:
                result['provider_name'] = 'pncp'
                result['source_type'] = 'fallback_search'
            
            return results, message
            
        except Exception as e:
            logger.error(f"❌ Error in fallback search: {e}")
            return [], f"Fallback search failed: {str(e)}"
    
    def _calculate_unified_status(self, result: Dict[str, Any]) -> str:
        """Calculate status for unified search results"""
        submission_deadline = result.get('submission_deadline')
        if not submission_deadline:
            return 'Indefinido'
        
        try:
            from datetime import datetime
            if isinstance(submission_deadline, str):
                deadline_dt = datetime.fromisoformat(submission_deadline.replace('Z', '+00:00'))
            else:
                deadline_dt = submission_deadline
            
            if deadline_dt.replace(tzinfo=None) > datetime.now():
                return 'Ativa'
            else:
                return 'Fechada'
        except Exception:
            return 'Indefinido'
    
    def _format_unified_value_display(self, value) -> str:
        """Format value for display in unified search results"""
        if value is None or value == 0:
            return 'Sigiloso'
        try:
            return float(value)
        except (ValueError, TypeError):
            return 'Sigiloso'
    
    def _is_unified_proposal_open(self, submission_deadline) -> bool:
        """Check if proposal deadline is still open for unified search results"""
        if not submission_deadline:
            return False
        
        try:
            from datetime import datetime
            if isinstance(submission_deadline, str):
                deadline_dt = datetime.fromisoformat(submission_deadline.replace('Z', '+00:00'))
            else:
                deadline_dt = submission_deadline
            
            return deadline_dt.replace(tzinfo=None) > datetime.now()
        except Exception:
            return False 

    async def search_by_provider_no_cache(self, provider_name: str, filters_dict: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Search a specific provider with cache disabled - for testing
        
        Args:
            provider_name: Name of the provider to search
            filters_dict: Dictionary with search filters
            
        Returns:
            Tuple of (opportunities list, message)
        """
        try:
            logger.info(f"🔍 Searching {provider_name} provider (NO CACHE)")
            
            # Convert dictionary to SearchFilters object
            filters = self._convert_dict_to_search_filters(filters_dict)
            
            # Create provider with cache disabled
            from factories.data_source_factory import DataSourceFactory
            from config.data_source_config import DataSourceConfig
            
            config = DataSourceConfig()
            factory = DataSourceFactory(config)
            
            # Override config to disable cache
            config_override = {'disable_cache': True}
            provider = factory.create(provider_name, config_override)
            
            # Search opportunities (await async call)
            opportunities = await provider.search_opportunities(filters)
            
            # Convert to frontend format
            formatted_opportunities = []
            for opportunity in opportunities:
                formatted_result = self._format_unified_result_for_frontend({
                    'external_id': opportunity.external_id,
                    'title': opportunity.title,
                    'description': opportunity.description,
                    'estimated_value': opportunity.estimated_value,
                    'currency_code': opportunity.currency_code,
                    'country_code': opportunity.country_code,
                    'region_code': opportunity.region_code,
                    'municipality': opportunity.municipality,
                    'publication_date': opportunity.publication_date,
                    'submission_deadline': opportunity.submission_deadline,
                    'procuring_entity_id': opportunity.procuring_entity_id,
                    'procuring_entity_name': opportunity.procuring_entity_name,
                    'provider_specific_data': opportunity.provider_specific_data,
                    'provider_name': provider_name,
                    'provider_metadata': {}
                })
                formatted_opportunities.append(formatted_result)
            
            message = f"{len(opportunities)} opportunities found from {provider_name} (cache disabled)"
            logger.info(f"✅ Provider search completed: {message}")
            
            return formatted_opportunities, message
            
        except Exception as e:
            logger.error(f"❌ Error in provider search (no cache): {e}")
            return [], f"Error searching {provider_name}: {str(e)}"