"""
Enhanced Bid Service com Sistema de Logs Detalhado
Garante consistência de dados em todas as licitações retornadas
"""
import logging
from typing import List, Dict, Any, Optional
from repositories.licitacao_repository_enhanced import LicitacaoPNCPRepositoryEnhanced
from repositories.licitacao_repository import LicitacaoPNCPRepository
from services.openai_service import OpenAIService

# Configurar logger específico para bid service
bid_logger = logging.getLogger('bid_service_enhanced')
bid_logger.setLevel(logging.INFO)

class BidServiceEnhanced:
    """
    Serviço melhorado para licitações com garantia de consistência de dados
    e logs detalhados para debugging
    """
    
    def __init__(self):
        self.enhanced_repo = LicitacaoPNCPRepositoryEnhanced()
        self.standard_repo = LicitacaoPNCPRepository()
        self.openai_service = OpenAIService()
        
        # Contadores para estatísticas da sessão
        self.session_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_licitacoes_found': 0,
            'licitacoes_enriched': 0,
            'enrichment_failures': 0,
            'data_inconsistencies': 0
        }
    
    def buscar_licitacoes_enhanced(
        self,
        filtros: Dict[str, Any],
        pagina: int = 1,
        itens_por_pagina: int = 100,
        enrich_data: bool = False
    ) -> Dict[str, Any]:
        """
        Busca licitações com sistema de logs detalhado e opção de enriquecimento
        
        Args:
            filtros: Filtros de busca
            pagina: Página atual
            itens_por_pagina: Itens por página
            enrich_data: Se True, enriquece cada licitação com dados detalhados
        """
        try:
            self.session_stats['total_searches'] += 1
            
            bid_logger.info("🔍 INICIANDO BUSCA ENHANCED DE LICITAÇÕES")
            bid_logger.info(f"   📋 Filtros: {filtros}")
            bid_logger.info(f"   📄 Página: {pagina}, Itens: {itens_por_pagina}")
            bid_logger.info(f"   🔄 Enriquecimento: {'Ativado' if enrich_data else 'Desativado'}")
            
            # Gerar sinônimos se necessário
            palavras_busca = self._processar_busca_sinonimos(filtros)
            
            # Executar busca usando repositório padrão (otimizado)
            resultado_busca = self.standard_repo.buscar_licitacoes(
                filtros, palavras_busca, pagina, itens_por_pagina
            )
            
            if not resultado_busca or not resultado_busca.get('data'):
                self.session_stats['failed_searches'] += 1
                bid_logger.warning("⚠️ Busca não retornou dados")
                return {
                    'success': False,
                    'data': [],
                    'metadados': {'totalRegistros': 0},
                    'message': 'Nenhuma licitação encontrada'
                }
            
            licitacoes = resultado_busca['data']
            self.session_stats['successful_searches'] += 1
            self.session_stats['total_licitacoes_found'] += len(licitacoes)
            
            bid_logger.info(f"✅ Busca inicial concluída: {len(licitacoes)} licitações encontradas")
            
            # Analisar estrutura das licitações encontradas
            self._analyze_licitacoes_structure(licitacoes)
            
            # Enriquecer dados se solicitado
            if enrich_data and licitacoes:
                bid_logger.info("🔄 Iniciando enriquecimento de dados...")
                licitacoes_enriquecidas = self._enrich_licitacoes_batch(licitacoes)
                resultado_busca['data'] = licitacoes_enriquecidas
                
                # Gerar relatório de consistência
                consistency_report = self.enhanced_repo.generate_data_consistency_report()
                resultado_busca['consistency_report'] = consistency_report
            
            # Adicionar estatísticas da sessão
            resultado_busca['session_stats'] = self.session_stats.copy()
            
            bid_logger.info("✅ BUSCA ENHANCED CONCLUÍDA COM SUCESSO")
            
            return {
                'success': True,
                'data': resultado_busca['data'],
                'metadados': resultado_busca.get('metadados', {}),
                'session_stats': self.session_stats.copy(),
                'consistency_report': resultado_busca.get('consistency_report'),
                'message': f'{len(resultado_busca["data"])} licitações encontradas'
            }
            
        except Exception as e:
            self.session_stats['failed_searches'] += 1
            bid_logger.error(f"❌ Erro na busca enhanced: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro na busca: {str(e)}',
                'session_stats': self.session_stats.copy()
            }
    
    def _processar_busca_sinonimos(self, filtros: Dict[str, Any]) -> List[str]:
        """
        Processa busca e gera sinônimos se necessário
        """
        try:
            termo_busca = filtros.get('busca', '').strip()
            if not termo_busca:
                bid_logger.info("📝 Nenhum termo de busca fornecido")
                return []
            
            bid_logger.info(f"📝 Processando termo: '{termo_busca}'")
            
            # Gerar sinônimos usando OpenAI
            sinonimos = self.openai_service.gerar_sinonimos(termo_busca)
            
            if sinonimos:
                palavras_busca = [termo_busca] + sinonimos
                bid_logger.info(f"🔤 Sinônimos gerados: {sinonimos}")
            else:
                palavras_busca = [termo_busca]
                bid_logger.warning("⚠️ Falha na geração de sinônimos, usando termo original")
            
            return palavras_busca
            
        except Exception as e:
            bid_logger.error(f"❌ Erro ao processar sinônimos: {str(e)}")
            return [filtros.get('busca', '').strip()] if filtros.get('busca') else []
    
    def _analyze_licitacoes_structure(self, licitacoes: List[Dict[str, Any]]) -> None:
        """
        Analisa a estrutura das licitações para identificar campos ausentes ou inconsistentes
        """
        try:
            bid_logger.info("🔍 ANALISANDO ESTRUTURA DAS LICITAÇÕES")
            
            if not licitacoes:
                bid_logger.warning("   ⚠️ Lista de licitações vazia")
                return
            
            # Campos esperados em uma licitação completa
            campos_esperados = [
                'numeroControlePNCP', 'objetoCompra', 'valorTotalEstimado',
                'dataPublicacaoPncp', 'dataAberturaProposta', 'dataEncerramentoProposta',
                'orgaoEntidade', 'unidadeOrgao', 'modalidadeNome', 'situacaoCompraNome'
            ]
            
            # Análise estatística
            total_licitacoes = len(licitacoes)
            campos_ausentes = {campo: 0 for campo in campos_esperados}
            
            for i, licitacao in enumerate(licitacoes):
                # Log detalhado para as primeiras 3 licitações
                if i < 3:
                    pncp_id = licitacao.get('numeroControlePNCP', f'ITEM_{i}')
                    self.enhanced_repo.log_api_response_structure(pncp_id, 'BUSCA_ANÁLISE', licitacao)
                
                # Contar campos ausentes
                for campo in campos_esperados:
                    if not licitacao.get(campo):
                        campos_ausentes[campo] += 1
            
            # Relatório de integridade
            bid_logger.info("📊 RELATÓRIO DE INTEGRIDADE DOS DADOS:")
            bid_logger.info(f"   📋 Total de licitações analisadas: {total_licitacoes}")
            
            for campo, ausentes in campos_ausentes.items():
                porcentagem = (ausentes / total_licitacoes) * 100
                status = "❌" if porcentagem > 10 else "⚠️" if porcentagem > 0 else "✅"
                bid_logger.info(f"   {status} {campo}: {ausentes}/{total_licitacoes} ausentes ({porcentagem:.1f}%)")
            
            # Identificar licitações problemáticas
            licitacoes_problematicas = []
            for licitacao in licitacoes:
                campos_vazios = sum(1 for campo in campos_esperados if not licitacao.get(campo))
                if campos_vazios > 3:  # Mais de 3 campos ausentes
                    licitacoes_problematicas.append({
                        'pncp_id': licitacao.get('numeroControlePNCP', 'SEM_ID'),
                        'campos_ausentes': campos_vazios,
                        'objeto': licitacao.get('objetoCompra', 'SEM_OBJETO')[:50] + '...'
                    })
            
            if licitacoes_problematicas:
                bid_logger.warning(f"⚠️ {len(licitacoes_problematicas)} licitações com dados incompletos:")
                for prob in licitacoes_problematicas[:5]:  # Mostrar apenas os primeiros 5
                    bid_logger.warning(f"   ID: {prob['pncp_id']}, {prob['campos_ausentes']} campos ausentes")
                    bid_logger.warning(f"   Objeto: {prob['objeto']}")
            else:
                bid_logger.info("✅ Todas as licitações têm estrutura adequada")
                
        except Exception as e:
            bid_logger.error(f"❌ Erro na análise de estrutura: {str(e)}")
    
    def _enrich_licitacoes_batch(self, licitacoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enriquece um lote de licitações com dados detalhados
        """
        try:
            total_licitacoes = len(licitacoes)
            bid_logger.info(f"🔄 Enriquecendo {total_licitacoes} licitações com dados detalhados")
            
            licitacoes_enriquecidas = []
            
            for i, licitacao in enumerate(licitacoes):
                pncp_id = licitacao.get('numeroControlePNCP')
                
                if not pncp_id:
                    bid_logger.warning(f"⚠️ Licitação {i+1}/{total_licitacoes} sem PNCP ID, pulando")
                    licitacoes_enriquecidas.append(licitacao)
                    continue
                
                try:
                    bid_logger.info(f"🔄 Enriquecendo {i+1}/{total_licitacoes}: {pncp_id}")
                    
                    licitacao_enriquecida = self.enhanced_repo.enrich_licitacao_with_details(licitacao)
                    licitacoes_enriquecidas.append(licitacao_enriquecida)
                    
                    self.session_stats['licitacoes_enriched'] += 1
                    
                except Exception as e:
                    bid_logger.error(f"❌ Erro ao enriquecer {pncp_id}: {str(e)}")
                    licitacoes_enriquecidas.append(licitacao)  # Manter dados originais
                    self.session_stats['enrichment_failures'] += 1
            
            success_rate = (self.session_stats['licitacoes_enriched'] / total_licitacoes) * 100
            bid_logger.info(f"✅ Enriquecimento concluído: {success_rate:.1f}% de sucesso")
            
            return licitacoes_enriquecidas
            
        except Exception as e:
            bid_logger.error(f"❌ Erro no enriquecimento em lote: {str(e)}")
            return licitacoes  # Retornar dados originais em caso de erro
    
    def buscar_licitacao_detalhada_enhanced(self, pncp_id: str) -> Dict[str, Any]:
        """
        Busca uma licitação específica com logs detalhados
        """
        try:
            bid_logger.info(f"🔍 Buscando detalhes enhanced para {pncp_id}")
            
            # Usar repositório enhanced para obter dados com logs
            resultado = self.enhanced_repo.test_data_consistency(pncp_id)
            
            if resultado['success']:
                bid_logger.info(f"✅ Detalhes obtidos com sucesso para {pncp_id}")
                return {
                    'success': True,
                    'data': resultado['data'],
                    'consistency_report': resultado.get('consistency_report'),
                    'message': f'Licitação {pncp_id} encontrada com dados consistentes'
                }
            else:
                bid_logger.warning(f"⚠️ Falha ao obter detalhes para {pncp_id}: {resultado.get('error')}")
                return {
                    'success': False,
                    'error': resultado.get('error'),
                    'pncp_id': pncp_id
                }
                
        except Exception as e:
            bid_logger.error(f"❌ Erro na busca detalhada enhanced: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}',
                'pncp_id': pncp_id
            }
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """
        Retorna estatísticas da sessão atual
        """
        try:
            # Calcular taxas de sucesso
            search_success_rate = 0
            if self.session_stats['total_searches'] > 0:
                search_success_rate = (self.session_stats['successful_searches'] / self.session_stats['total_searches']) * 100
            
            enrichment_success_rate = 0
            total_enrichments = self.session_stats['licitacoes_enriched'] + self.session_stats['enrichment_failures']
            if total_enrichments > 0:
                enrichment_success_rate = (self.session_stats['licitacoes_enriched'] / total_enrichments) * 100
            
            # Obter relatório de consistência
            consistency_report = self.enhanced_repo.generate_data_consistency_report()
            
            return {
                'session_stats': self.session_stats.copy(),
                'calculated_rates': {
                    'search_success_rate': search_success_rate,
                    'enrichment_success_rate': enrichment_success_rate
                },
                'consistency_report': consistency_report,
                'timestamp': consistency_report.get('timestamp')
            }
            
        except Exception as e:
            bid_logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
            return {
                'error': f'Erro ao obter estatísticas: {str(e)}',
                'session_stats': self.session_stats.copy()
            }
    
    def reset_session_stats(self) -> None:
        """
        Reseta as estatísticas da sessão
        """
        self.session_stats = {
            'total_searches': 0,
            'successful_searches': 0,
            'failed_searches': 0,
            'total_licitacoes_found': 0,
            'licitacoes_enriched': 0,
            'enrichment_failures': 0,
            'data_inconsistencies': 0
        }
        bid_logger.info("🔄 Estatísticas da sessão resetadas") 