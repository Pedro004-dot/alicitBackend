"""
Enhanced Licitacao Repository com Sistema de Logs Detalhado
Solução para identificar e resolver inconsistências de dados entre APIs
"""
import os
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, timedelta
# from .base_repository import BaseRepository  # Não necessário para esta implementação

# Configurar logger específico para debugging de dados
data_logger = logging.getLogger('data_consistency')
data_logger.setLevel(logging.INFO)

class LicitacaoPNCPRepositoryEnhanced:
    """
    Versão melhorada do repositório PNCP com logs detalhados
    para identificar inconsistências de dados
    """
    
    def __init__(self):
        self.base_url = os.getenv('PNCP_BASE_URL', "https://pncp.gov.br/api/consulta/v1")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AlicitSaas/2.0 (Busca Inteligente de Licitações)',
            'Accept': 'application/json'
        })
        self.timeout = 30
        
        # Contadores para estatísticas
        self.stats = {
            'total_processed': 0,
            'api_search_success': 0,
            'api_search_errors': 0,
            'api_detail_success': 0,
            'api_detail_errors': 0,
            'data_inconsistencies': 0,
            'missing_fields': {}
        }
        
        # Stopwords REDUZIDAS (só as mais comuns)
        self.stopwords = {
            'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'com', 'nao', 
            'uma', 'os', 'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas'
        }
        
        # Mapeamento de modalidades
        self.modalidade_para_codigo = {
            'pregao_eletronico': 8,
            'concorrencia': 5,
            'dispensa': 1,
            'tomada_precos': 7,
            'convite': 6,
            'inexigibilidade': 2,
        }

    def log_api_response_structure(self, pncp_id: str, api_type: str, response_data: Dict[str, Any]) -> None:
        """
        Log detalhado da estrutura da resposta da API para debugging
        """
        try:
            # Log básico
            data_logger.info(f"📡 [{api_type}] Resposta da API para {pncp_id}")
            data_logger.info(f"   🔗 Tipo: {api_type}")
            data_logger.info(f"   📊 Tamanho da resposta: {len(json.dumps(response_data, default=str))} chars")
            
            # Log dos campos principais sempre presentes
            main_fields = [
                'numeroControlePNCP', 'objetoCompra', 'valorTotalEstimado',
                'dataPublicacaoPncp', 'dataAberturaProposta', 'dataEncerramentoProposta',
                'orgaoEntidade', 'unidadeOrgao', 'modalidadeNome', 'situacaoCompraNome'
            ]
            
            data_logger.info(f"   📋 Campos principais:")
            for field in main_fields:
                value = response_data.get(field)
                if value is not None:
                    if isinstance(value, dict):
                        data_logger.info(f"      ✅ {field}: {len(value)} sub-campos")
                    elif isinstance(value, str) and len(value) > 100:
                        data_logger.info(f"      ✅ {field}: {value[:100]}...")
                    else:
                        data_logger.info(f"      ✅ {field}: {value}")
                else:
                    data_logger.info(f"      ❌ {field}: AUSENTE")
                    # Contar campos ausentes
                    self.stats['missing_fields'][field] = self.stats['missing_fields'].get(field, 0) + 1
            
            # Log específico para dados estruturados críticos
            if 'orgaoEntidade' in response_data:
                orgao = response_data['orgaoEntidade']
                data_logger.info(f"   🏢 OrgaoEntidade: cnpj={orgao.get('cnpj')}, razaoSocial={orgao.get('razaoSocial')}")
            else:
                data_logger.warning(f"   🏢 OrgaoEntidade: AUSENTE")
            
            if 'unidadeOrgao' in response_data:
                unidade = response_data['unidadeOrgao']
                data_logger.info(f"   🏛️ UnidadeOrgao: uf={unidade.get('ufSigla')}, municipio={unidade.get('municipioNome')}")
            else:
                data_logger.warning(f"   🏛️ UnidadeOrgao: AUSENTE")
            
            # Log de todos os campos para análise completa
            data_logger.info(f"   📝 Todos os campos disponíveis:")
            for key, value in response_data.items():
                if isinstance(value, dict):
                    data_logger.info(f"      {key}: dict com {len(value)} campos")
                elif isinstance(value, list):
                    data_logger.info(f"      {key}: list com {len(value)} itens")
                elif isinstance(value, str) and len(value) > 100:
                    data_logger.info(f"      {key}: string({len(value)} chars)")
                else:
                    data_logger.info(f"      {key}: {type(value).__name__}({value})")
                    
        except Exception as e:
            data_logger.error(f"❌ Erro ao analisar estrutura da resposta: {e}")

    def detect_data_inconsistencies(self, search_data: Dict[str, Any], detail_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Detecta inconsistências entre dados de busca e detalhes
        """
        try:
            pncp_id = search_data.get('numeroControlePNCP', 'UNKNOWN')
            
            # Se não há dados detalhados, não há comparação
            if detail_data is None:
                data_logger.info(f"🔍 [{pncp_id}] Apenas dados de busca disponíveis")
                return
            
            data_logger.info(f"🔍 [{pncp_id}] Comparando dados de busca vs detalhes")
            
            # Campos a comparar
            comparison_fields = [
                ('objetoCompra', 'objeto'),
                ('valorTotalEstimado', 'valor'),
                ('modalidadeNome', 'modalidade'),
                ('situacaoCompraNome', 'situacao')
            ]
            
            inconsistencies = []
            
            for field, friendly_name in comparison_fields:
                search_value = search_data.get(field)
                detail_value = detail_data.get(field)
                
                if search_value != detail_value:
                    inconsistencies.append({
                        'field': field,
                        'friendly_name': friendly_name,
                        'search_value': search_value,
                        'detail_value': detail_value
                    })
            
            if inconsistencies:
                self.stats['data_inconsistencies'] += 1
                data_logger.warning(f"⚠️ [{pncp_id}] {len(inconsistencies)} inconsistências detectadas:")
                for inc in inconsistencies:
                    data_logger.warning(f"   {inc['friendly_name']}: '{inc['search_value']}' vs '{inc['detail_value']}'")
            else:
                data_logger.info(f"✅ [{pncp_id}] Dados consistentes entre busca e detalhes")
                
        except Exception as e:
            data_logger.error(f"❌ Erro ao detectar inconsistências: {e}")

    async def buscar_licitacao_detalhada_async_enhanced(
        self, 
        session: aiohttp.ClientSession, 
        pncp_id: str,
        search_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Versão melhorada da busca de detalhes com logs detalhados
        """
        parsed_id = self._parse_pncp_id(pncp_id)
        if not parsed_id:
            data_logger.error(f"❌ [{pncp_id}] Falha ao parsear PNCP ID")
            return None
        
        # Endpoint de detalhes da compra
        endpoint = f"https://pncp.gov.br/api/pncp/v1/orgaos/{parsed_id['cnpj']}/compras/{parsed_id['ano']}/{parsed_id['sequencial']}"
        
        try:
            data_logger.info(f"📡 [{pncp_id}] Consultando API de detalhes: {endpoint}")
            
            async with session.get(endpoint, timeout=self.timeout) as response:
                response.raise_for_status()
                
                if "application/json" not in response.headers.get("Content-Type", ""):
                    data_logger.warning(f"⚠️ [{pncp_id}] Resposta não-JSON da API de detalhes")
                    self.stats['api_detail_errors'] += 1
                    return None

                data = await response.json()
                self.stats['api_detail_success'] += 1
                
                # Log detalhado da estrutura da resposta
                self.log_api_response_structure(pncp_id, 'DETALHES', data)
                
                # Detectar inconsistências se temos dados de busca
                if search_data:
                    self.detect_data_inconsistencies(search_data, data)
                
                data_logger.info(f"✅ [{pncp_id}] Detalhes obtidos com sucesso da API")
                return data
                
        except aiohttp.ClientResponseError as http_err:
            self.stats['api_detail_errors'] += 1
            if http_err.status == 404:
                data_logger.warning(f"🔍 [{pncp_id}] Detalhes não encontrados na API (404)")
            else:
                data_logger.error(f"❌ [{pncp_id}] Erro HTTP {http_err.status} na API de detalhes")
        except Exception as e:
            self.stats['api_detail_errors'] += 1
            data_logger.error(f"❌ [{pncp_id}] Erro inesperado na API de detalhes: {e}", exc_info=True)
            
        return None

    def enrich_licitacao_with_details(self, licitacao_busca: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enriquece uma licitação da busca com dados detalhados da API
        """
        pncp_id = licitacao_busca.get('numeroControlePNCP')
        if not pncp_id:
            data_logger.warning(f"⚠️ Licitação sem PNCP ID, pulando enriquecimento")
            return licitacao_busca
        
        try:
            # Log inicial dos dados de busca
            self.log_api_response_structure(pncp_id, 'BUSCA', licitacao_busca)
            
            # Buscar detalhes
            data_logger.info(f"🔄 [{pncp_id}] Iniciando enriquecimento com detalhes")
            
            async def main():
                async with aiohttp.ClientSession() as session:
                    return await self.buscar_licitacao_detalhada_async_enhanced(
                        session, pncp_id, licitacao_busca
                    )
            
            detalhes = asyncio.run(main())
            
            if detalhes:
                # Merge inteligente: dados de detalhes sobrepõem dados de busca
                licitacao_enriquecida = {**licitacao_busca, **detalhes}
                
                data_logger.info(f"✅ [{pncp_id}] Licitação enriquecida com sucesso")
                data_logger.info(f"   📊 Campos de busca: {len(licitacao_busca)}")
                data_logger.info(f"   📊 Campos de detalhes: {len(detalhes)}")
                data_logger.info(f"   📊 Campos final: {len(licitacao_enriquecida)}")
                
                return licitacao_enriquecida
            else:
                data_logger.warning(f"⚠️ [{pncp_id}] Falha no enriquecimento, mantendo dados de busca")
                return licitacao_busca
                
        except Exception as e:
            data_logger.error(f"❌ [{pncp_id}] Erro no enriquecimento: {e}")
            return licitacao_busca

    def _parse_pncp_id(self, pncp_id: str) -> Optional[Dict[str, str]]:
        """Extrai CNPJ, ano e sequencial do ID do PNCP (ex: 08584229000122-1-000013/2025)."""
        try:
            # O PNCP ID do frontend vem com / no final, ex: .../2025/
            clean_pncp_id = pncp_id.strip('/')
            
            # Formato: 08584229000122-1-000013/2025
            parts = clean_pncp_id.split('-')
            if len(parts) < 3 or '/' not in parts[-1]:
                data_logger.warning(f"⚠️ Formato de PNCP ID inválido: {pncp_id}")
                return None

            cnpj = parts[0]
            compra_parts = parts[-1].split('/')
            ano_compra = compra_parts[-1]
            sequencial_compra = compra_parts[0]
            
            # Se o formato for CNPJ-MOD-SEQ/ANO
            if len(parts) > 2:
                sequencial_compra = parts[-1].split('/')[0]

            return {'cnpj': cnpj, 'ano': ano_compra, 'sequencial': sequencial_compra}
        except Exception as e:
            data_logger.error(f"❌ Erro ao parsear PNCP ID '{pncp_id}': {e}")
            return None

    def generate_data_consistency_report(self) -> Dict[str, Any]:
        """
        Gera relatório de consistência de dados
        """
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'statistics': self.stats.copy(),
                'recommendations': []
            }
            
            # Calcular taxas de sucesso
            total_api_calls = self.stats['api_search_success'] + self.stats['api_search_errors']
            if total_api_calls > 0:
                report['api_search_success_rate'] = self.stats['api_search_success'] / total_api_calls
            
            total_detail_calls = self.stats['api_detail_success'] + self.stats['api_detail_errors']
            if total_detail_calls > 0:
                report['api_detail_success_rate'] = self.stats['api_detail_success'] / total_detail_calls
            
            # Gerar recomendações
            if self.stats['data_inconsistencies'] > 0:
                report['recommendations'].append(
                    f"Detectadas {self.stats['data_inconsistencies']} inconsistências. "
                    "Considere priorizar dados de detalhes sobre dados de busca."
                )
            
            # Campos mais ausentes
            if self.stats['missing_fields']:
                sorted_missing = sorted(
                    self.stats['missing_fields'].items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                top_missing = sorted_missing[:5]
                report['most_missing_fields'] = top_missing
                report['recommendations'].append(
                    f"Campos mais ausentes: {', '.join([f[0] for f in top_missing])}. "
                    "Implemente fallbacks robustos."
                )
            
            data_logger.info(f"📋 Relatório de consistência gerado: {json.dumps(report, indent=2, default=str)}")
            return report
            
        except Exception as e:
            data_logger.error(f"❌ Erro ao gerar relatório: {e}")
            return {'error': str(e)}

    # Método de teste para usar o novo sistema
    def test_data_consistency(self, pncp_id: str) -> Dict[str, Any]:
        """
        Método de teste para verificar consistência de dados de uma licitação específica
        """
        try:
            data_logger.info(f"🧪 Iniciando teste de consistência para {pncp_id}")
            
            # Simular dados de busca (normalmente viriam da API de busca)
            # Aqui vamos buscar direto os detalhes para demonstração
            async def main():
                async with aiohttp.ClientSession() as session:
                    return await self.buscar_licitacao_detalhada_async_enhanced(session, pncp_id)
            
            detalhes = asyncio.run(main())
            
            if detalhes:
                # Log da estrutura
                self.log_api_response_structure(pncp_id, 'TESTE', detalhes)
                
                # Gerar relatório
                report = self.generate_data_consistency_report()
                
                return {
                    'success': True,
                    'pncp_id': pncp_id,
                    'data': detalhes,
                    'consistency_report': report
                }
            else:
                return {
                    'success': False,
                    'pncp_id': pncp_id,
                    'error': 'Não foi possível obter dados'
                }
                
        except Exception as e:
            data_logger.error(f"❌ Erro no teste: {e}")
            return {
                'success': False,
                'pncp_id': pncp_id,
                'error': str(e)
            } 