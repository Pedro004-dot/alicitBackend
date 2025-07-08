from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
from services.search.base_source import FonteBusca
from config.env_loader import get_env_var
import logging

logger = logging.getLogger(__name__)

class LicitacaoPNCPRepository(FonteBusca):
    """
    Implementação da fonte de busca para o PNCP.
    Busca um grande volume de dados brutos, iterando sobre cada modalidade conhecida,
    e usando apenas os filtros obrigatórios da API.
    """
    MODALIDADES_MAP = {
        "pregao_eletronico": 8,
        "concorrencia": 6,
        "convite": 3,
        "tomada_de_precos": 4,
    }

    def __init__(self):
        self.base_url = get_env_var("PNCP_API_URL", "https://pncp.gov.br/api/consulta/v1")
    
    def buscar(self, filtros: Optional[Dict] = None) -> List[Dict]:
        """
        Busca licitações no PNCP iterando sobre todas as modalidades conhecidas.
        A filtragem por palavra-chave, estado, etc., é feita posteriormente no LicitacaoService.
        """
        todas_licitacoes_normalizadas = []
        vistos = set()

        for nome, id_modalidade in self.MODALIDADES_MAP.items():
            try:
                logger.info(f"Iniciando busca para modalidade: {nome} (ID: {id_modalidade})")
                params = self._construir_parametros_request(id_modalidade)
                licitacoes_brutas = self._executar_request_pncp(params)

                for lic_bruta in licitacoes_brutas:
                    lic_normalizada = self.normalizar_licitacao(lic_bruta)
                    lic_id = lic_normalizada.get("id")
                    if lic_id and lic_id not in vistos:
                        vistos.add(lic_id)
                        todas_licitacoes_normalizadas.append(lic_normalizada)
            except Exception as e:
                logger.error(f"Falha na busca para modalidade {nome}: {e}")

        logger.info(f"Busca bruta finalizada. Total de {len(todas_licitacoes_normalizadas)} licitações únicas coletadas.")
        return todas_licitacoes_normalizadas

    def _executar_request_pncp(self, params: Dict) -> List[Dict]:
        """
        Executa chamadas GET para a API do PNCP com paginação.
        """
        url = f"{self.base_url}/contratacoes/proposta"
        resultados_acumulados = []
        pagina_atual = 1
        limite_total_registros = 20000  # AUMENTADO: de 10.000 para 20.000
        tamanho_pagina_real = 50  # CORRIGIR: usar o tamanho real configurado

        while len(resultados_acumulados) < limite_total_registros:
            params['pagina'] = pagina_atual
            
            try:
                response = requests.get(url, params=params, timeout=90)
                response.raise_for_status()
                
                dados = response.json()
                licitacoes_pagina = dados.get('data', []) if isinstance(dados, dict) else dados

                if not licitacoes_pagina:
                    logger.info(f"Paginação encerrada na página {pagina_atual} para modalidade {params['codigoModalidadeContratacao']}.")
                    break

                resultados_acumulados.extend(licitacoes_pagina)
                logger.info(f"Página {pagina_atual} retornou {len(licitacoes_pagina)} resultados. Total acumulado: {len(resultados_acumulados)}")

                # CORRIGIR: usar tamanho real da página para verificar se é a última
                if len(licitacoes_pagina) < tamanho_pagina_real:
                    logger.info(f"Última página de resultados alcançada para a modalidade {params['codigoModalidadeContratacao']}.")
                    break

                pagina_atual += 1
                
                # ADICIONAR: limite máximo de páginas para evitar loops infinitos
                if pagina_atual > 400:  # AUMENTADO: Máximo 400 páginas (20.000 / 50)
                    logger.info(f"Limite de páginas (400) alcançado para modalidade {params['codigoModalidadeContratacao']}.")
                    break

            except requests.RequestException as e:
                logger.error(f"Erro de request ao PNCP na página {pagina_atual}: {e}")
                break

        return resultados_acumulados

    def _construir_parametros_request(self, modalidade_id: int) -> Dict:
        """Constrói os parâmetros com datas e o ID da modalidade."""
        hoje = datetime.now()
        data_inicio = (hoje - timedelta(days=90)).strftime('%Y%m%d')
        data_fim = (hoje + timedelta(days=120)).strftime('%Y%m%d')

        return {
            'dataInicial': data_inicio,
            'dataFinal': data_fim,
            'tamanhoPagina': 50,
            'codigoModalidadeContratacao': modalidade_id
        }

    def normalizar_licitacao(self, licitacao: Dict) -> Dict:
        """Converte o formato do PNCP para o formato padronizado do sistema."""
        return {
            "id": licitacao.get("numeroControlePNCP"),
            "titulo": licitacao.get("objetoCompra"),
            "descricao": licitacao.get("objetoCompra"),
            "modalidade": licitacao.get("modalidadeNome"),
            "valor_estimado": licitacao.get("valorTotalEstimado"),
            "data_abertura": licitacao.get("dataAberturaProposta"),
            "data_encerramento": licitacao.get("dataEncerramentoProposta"),
            "situacao": licitacao.get("situacaoCompraNome"),
            "orgao": licitacao.get("orgaoEntidade", {}).get("razaoSocial"),
            "uf": licitacao.get("unidadeOrgao", {}).get("ufSigla"),
            "municipio": licitacao.get("unidadeOrgao", {}).get("municipioNome"),
            "fonte": "pncp",
            "dados_originais": licitacao
        } 