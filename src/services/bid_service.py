"""
Bid Service (Licitação Service)
Lógica de negócio para operações com licitações
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from repositories.licitacao_repository import LicitacaoRepository
from config.database import db_manager

logger = logging.getLogger(__name__)

class BidService:
    """Service para regras de negócio de licitações"""
    
    def __init__(self):
        self.licitacao_repo = LicitacaoRepository(db_manager)
    
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
        """Buscar licitação por PNCP ID com formatação"""
        try:
            bid = self.licitacao_repo.find_by_pncp_id(pncp_id)
            if bid:
                return self._format_bid_for_frontend(bid)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar licitação por PNCP {pncp_id}: {e}")
            return None
    
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
    
    def get_bid_items(self, pncp_id: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Buscar itens de uma licitação por PNCP ID
        
        Args:
            pncp_id: ID da licitação no PNCP
            
        Returns:
            Tupla com lista de itens e mensagem de status
        """
        try:
            # Primeiro, buscar a licitação pelo pncp_id
            bid = self.licitacao_repo.find_by_pncp_id(pncp_id)
            
            if not bid:
                return [], "Licitação não encontrada"
            
            # Buscar itens da licitação usando o ID interno
            items = self.licitacao_repo.find_items_by_licitacao_id(bid['id'])
            
            # Formatar itens para o frontend
            formatted_items = self._format_items_for_frontend(items)
            
            message = f"{len(formatted_items)} itens encontrados para a licitação {pncp_id}"
            return formatted_items, message
            
        except Exception as e:
            logger.error(f"Erro ao buscar itens da licitação {pncp_id}: {e}")
            return [], f"Erro ao buscar itens da licitação: {str(e)}"

    def _format_items_for_frontend(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formatar itens de licitação para o frontend com campos necessários
        """
        formatted_items = []
        for item in items:
            formatted_item = {
                'id': item.get('id'),
                'numero_item': item.get('numero_item'),
                'nome_item': item.get('nome_item'),
                'descricao_complementar': item.get('descricao_complementar'),
                'quantidade': item.get('quantidade'),
                'valor_unitario': item.get('valor_unitario'),
                'valor_total': item.get('valor_total_estimado', item.get('valor_unitario', 0) * item.get('quantidade', 0)),
                'ncm_nbs': item.get('ncm_nbs'),
                'unidade_medida': item.get('unidade_medida'),
                'material_ou_servico': item.get('material_ou_servico'),
                'beneficio_micro_epp': item.get('beneficio_micro_epp', False),
                'participacao_exclusiva_me_epp': item.get('participacao_exclusiva_me_epp', False),
                'pncp_id': item.get('licitacao_pncp_id'),
                'criterio_julgamento': item.get('criterio_julgamento'),
                'criterio_valor_nome': item.get('criterio_valor_nome')
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