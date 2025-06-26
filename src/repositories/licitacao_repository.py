"""
Licitacao Repository
Repositório para interação com licitações, tanto no banco de dados local quanto na API do PNCP.
"""
import os
import requests
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timedelta
from .base_repository import BaseRepository

# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicitacaoRepository(BaseRepository):
    """
    Repositório para operações com a tabela licitacoes no banco de dados.
    Esta classe herda de BaseRepository pois precisa do db_manager para acessar o banco.
    """
    
    @property
    def table_name(self) -> str:
        return "licitacoes"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def find_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Buscar licitação por ID"""
        query = """
            SELECT * FROM licitacoes WHERE id = %s
        """
        results = self.execute_custom_query(query, (id,))
        return results[0] if results else None
    
    def find_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """Buscar licitação por ID do PNCP"""
        query = """
            SELECT * FROM licitacoes WHERE numero_controle_pncp = %s LIMIT 1
        """
        results = self.execute_custom_query(query, (pncp_id,))
        return results[0] if results else None
    
    def find_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por status"""
        return self.find_by_filters({'status': status}, limit=limit)
    
    def find_by_value_range(self, min_value: Optional[float] = None, 
                           max_value: Optional[float] = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Buscar licitações por faixa de valor"""
        where_clauses = []
        params = []
        
        if min_value is not None:
            where_clauses.append("valor_total_estimado >= %s")
            params.append(min_value)
        
        if max_value is not None:
            where_clauses.append("valor_total_estimado <= %s")
            params.append(max_value)
        
        if not where_clauses:
            return self.find_all(limit=limit)
        
        query = f"""
            SELECT * FROM licitacoes 
            WHERE {' AND '.join(where_clauses)}
            ORDER BY valor_total_estimado DESC
            LIMIT %s
        """
        params.append(limit)
        
        return self.execute_custom_query(query, tuple(params))
    
    def find_by_state(self, uf: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações por estado"""
        return self.find_by_filters({'uf': uf}, limit=limit)
    
    def find_by_modality(self, modalidade: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações por modalidade (nome)"""
        query = """
            SELECT * FROM licitacoes 
            WHERE modalidade_nome ILIKE %s
            ORDER BY data_publicacao_pncp DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (f"%{modalidade}%", limit))
    
    def find_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar licitações mais recentes"""
        query = """
            SELECT * FROM licitacoes 
            ORDER BY data_publicacao_pncp DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (limit,))

    def find_active_bids_after_date(self, after_date: str = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Buscar licitações ativas após uma data específica"""
        # Com data específica
        if after_date:
            query = (
                """
                    SELECT * FROM licitacoes 
                WHERE data_encerramento_proposta > %s
                    ORDER BY data_encerramento_proposta ASC
                """
            )
            params: List[Any] = [after_date]
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            return self.execute_custom_query(query, tuple(params))

        # Sem data específica (apenas após o dia atual)
        query = (
            """
                    SELECT * FROM licitacoes 
            WHERE data_encerramento_proposta > CURRENT_DATE
                    ORDER BY data_encerramento_proposta ASC
                """
        )
        if limit:
            query += " LIMIT %s"
            return self.execute_custom_query(query, (limit,))
        return self.execute_custom_query(query)
    
    def find_high_value_bids(self, min_value: float = 1000000, limit: int = 50) -> List[Dict[str, Any]]:
        """Buscar licitações de alto valor"""
        query = """
            SELECT * FROM licitacoes 
            WHERE valor_total_estimado >= %s
            ORDER BY valor_total_estimado DESC
            LIMIT %s
        """
        return self.execute_custom_query(query, (min_value, limit))
    
class LicitacaoPNCPRepository:
    """
    VERSÃO REAL DA ESTRATÉGIA DO THIAGO
    Busca SIMPLES e AMPLA na API + Filtro LOCAL básico mas eficaz
    """

    def __init__(self):
        self.base_url = os.getenv('PNCP_BASE_URL', "https://pncp.gov.br/api/consulta/v1")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AlicitSaas/2.0 (Busca Inteligente de Licitações)',
            'Accept': 'application/json'
        })
        self.timeout = 30
        
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

    def _parse_pncp_id(self, pncp_id: str) -> Optional[Dict[str, str]]:
        """Extrai CNPJ, ano e sequencial do ID do PNCP (ex: 08584229000122-1-000013/2025)."""
        try:
            # O PNCP ID do frontend vem com / no final, ex: .../2025/
            clean_pncp_id = pncp_id.strip('/')
            
            # Formato: 08584229000122-1-000013/2025
            parts = clean_pncp_id.split('-')
            if len(parts) < 3 or '/' not in parts[-1]:
                logger.warning(f"Formato de PNCP ID inválido para busca: {pncp_id}")
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
            logger.error(f"Erro ao parsear PNCP ID '{pncp_id}': {e}")
            return None

    async def buscar_licitacao_detalhada_async(self, session: aiohttp.ClientSession, pncp_id: str) -> Optional[Dict[str, Any]]:
        """Busca os detalhes de uma única licitação na API do PNCP."""
        parsed_id = self._parse_pncp_id(pncp_id)
        if not parsed_id:
            return None
        
        # Endpoint de detalhes da compra (sem /itens)
        endpoint = f"https://pncp.gov.br/api/pncp/v1/orgaos/{parsed_id['cnpj']}/compras/{parsed_id['ano']}/{parsed_id['sequencial']}"
        
        try:
            logger.info(f"Consultando API de detalhes: {endpoint}")
            async with session.get(endpoint, timeout=self.timeout) as response:
                response.raise_for_status()
                
                if "application/json" not in response.headers.get("Content-Type", ""):
                    logger.warning(f"Resposta não-JSON ao buscar detalhes para {pncp_id}")
                    return None

                data = await response.json()
                logger.info(f"✅ Detalhes encontrados na API do PNCP para {pncp_id}")
                return data
        except aiohttp.ClientResponseError as http_err:
            if http_err.status == 404:
                logger.warning(f"Detalhes não encontrados na API do PNCP (404) para {pncp_id}")
            else:
                logger.error(f"Erro HTTP {http_err.status} ao buscar detalhes na API do PNCP: {http_err}")
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar detalhes na API do PNCP para {pncp_id}: {e}", exc_info=True)
            
        return None

    def buscar_licitacao_detalhada(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """Versão síncrona para buscar detalhes de uma licitação."""
        async def main():
            async with aiohttp.ClientSession() as session:
                return await self.buscar_licitacao_detalhada_async(session, pncp_id)
        return asyncio.run(main())

    async def buscar_licitacoes_paralelo(
        self,
        filtros: Dict[str, Any],
        palavras_busca: List[str],
        pagina: int = 1,
        itens_por_pagina: int = 500
    ) -> Dict[str, Any]:
        """
        BUSCA ESTILO THIAGO REAL:
        1. Busca SIMPLES na API (só filtros básicos)
        2. Poucas páginas por estado (máximo 3-5)
        3. Filtro local SIMPLES mas eficaz
        """
        try:
            # Preparar estados
            estados = filtros.get('estados', [])
            if not estados or not any(estados):
                logger.info("Nenhum estado especificado, buscando em todo o Brasil")
                estados = ['']
            else:
                logger.info(f"🗺️ Buscando nos estados: {estados}")
            
            # Preparar modalidades (SIMPLIFICADO)
            modalidades = filtros.get('modalidades', [])
            if not modalidades:
                logger.info("Usando modalidade padrão: pregão eletrônico")
                modalidades = ['pregao_eletronico']  # Só pregão por padrão
            else:
                logger.info(f"📋 Modalidades: {modalidades}")
            
            # ESTRATÉGIA SIMPLES: busca padrão sempre
            return await self._busca_real_thiago(
                estados, modalidades, filtros, palavras_busca, pagina, itens_por_pagina
            )

        except Exception as e:
            logger.error(f"Erro ao buscar licitações: {str(e)}")
            raise

    async def _busca_real_thiago(
        self,
        estados: List[str],
        modalidades: List[str],
        filtros: Dict[str, Any],
        palavras_busca: List[str],
        pagina: int,
        itens_por_pagina: int
    ) -> Dict[str, Any]:
        """
        BUSCA REAL COMO O THIAGO FAZ:
        - Máximo 5 páginas por estado (não 10)
        - Uma modalidade por vez
        - Foco em resultados, não volume
        """
        logger.info("🎯 INICIANDO BUSCA REAL ESTILO THIAGO")
        
        # CONFIGURAÇÃO REAL THIAGO
        max_paginas_por_estado = 5      # Reduzido de 10 para 5
        tamanho_pagina_api = 50         # Máximo da API
        
        logger.info(f"📊 Estratégia: {max_paginas_por_estado} páginas × {tamanho_pagina_api} = {max_paginas_por_estado * tamanho_pagina_api} por estado")
        
        # Criar combinações SIMPLES
        combinacoes = []
        for estado in estados:
            for modalidade in modalidades:
                for pagina_api in range(1, max_paginas_por_estado + 1):
                    filtros_busca = {
                        'estados': [estado] if estado else [],
                        'modalidades': [modalidade],
                        'valor_minimo': filtros.get('valor_minimo'),
                        'valor_maximo': filtros.get('valor_maximo'),
                        # NÃO inclui palavras_busca aqui - será usado só no filtro local
                    }
                    combinacoes.append((filtros_busca, [], pagina_api, tamanho_pagina_api))
        
        total_buscas = len(combinacoes)
        logger.info(f"🚀 Executando {total_buscas} buscas SIMPLES na API")
        
        # Executar buscas em paralelo
        async with aiohttp.ClientSession() as session:
            tarefas = [
                self._buscar_licitacoes_async(session, *args)
                for args in combinacoes
            ]
            resultados = await asyncio.gather(*tarefas, return_exceptions=True)
        
        # Processar resultados
        licitacoes_brutas = []
        sucessos = 0
        erros = 0
        
        for resultado in resultados:
            if isinstance(resultado, Exception):
                erros += 1
                continue
                
            if resultado and 'data' in resultado:
                licitacoes_brutas.extend(resultado['data'])
                sucessos += 1
        
        logger.info(f"✅ API: {sucessos} sucessos, {erros} erros")
        logger.info(f"📦 Licitações coletadas (bruto): {len(licitacoes_brutas)}")
        
        # FILTRO LOCAL SIMPLES (como Thiago)
        licitacoes_filtradas = self._filtro_local_thiago(licitacoes_brutas, filtros, palavras_busca)
        
        # Ordenar por data
        licitacoes_filtradas.sort(
            key=lambda x: x.get('dataPublicacaoPncp', ''),
            reverse=True
        )
        
        logger.info(f"🎯 RESULTADO FINAL: {len(licitacoes_filtradas)} licitações relevantes")
        
        return {
            'data': licitacoes_filtradas,
            'metadados': {
                'totalRegistros': len(licitacoes_filtradas),
                'totalPaginas': 1,
                'pagina': pagina,
                'buscas_executadas': total_buscas,
                'buscas_com_sucesso': sucessos,
                'buscas_com_erro': erros,
                'licitacoes_brutas_coletadas': len(licitacoes_brutas),
                'estrategia': 'real_thiago_simples',
                'filtros_ativos': {
                    'estados': estados if estados != [''] else [],
                    'modalidades': modalidades,
                    'cidades': filtros.get('cidades', []),
                    'palavras_busca': palavras_busca
                }
            }
        }

    def _filtro_local_thiago(
        self, 
        licitacoes: List[Dict[str, Any]], 
        filtros: Dict[str, Any],
        palavras_busca: List[str]
    ) -> List[Dict[str, Any]]:
        """
        FILTRO LOCAL REAL COMO O THIAGO FAZ:
        - Busca substring SIMPLES no objetoCompra
        - Sem threshold complexo
        - Sem stemmer agressivo
        - Foco na simplicidade e eficácia
        """
        from datetime import datetime
        
        logger.info("🔍 FILTRO LOCAL ESTILO THIAGO REAL")
        
        if not palavras_busca:
            logger.warning("⚠️ Nenhuma palavra de busca fornecida")
            return licitacoes
        
        # Normalizar palavras de busca SIMPLES
        termos_normalizados = []
        for palavra in palavras_busca:
            if palavra and isinstance(palavra, str):
                termo_clean = self._normalizar_simples(palavra.strip())
                if termo_clean and termo_clean not in self.stopwords:
                    termos_normalizados.append(termo_clean)
        
        logger.info(f"🎯 Termos para busca LOCAL: {termos_normalizados}")
        
        if not termos_normalizados:
            logger.warning("⚠️ Nenhum termo válido após normalização")
            return licitacoes
        
        # Extrair filtros adicionais
        cidades_filtro = {c.strip().upper() for c in filtros.get('cidades', []) if c.strip()}
        data_atual = datetime.now()
        
        # Processar licitações
        vistas = set()
        licitacoes_aprovadas = []
        total_analisadas = 0
        rejeitadas_duplicata = 0
        rejeitadas_palavra = 0
        rejeitadas_prazo = 0
        rejeitadas_cidade = 0
        
        for lic in licitacoes:
            total_analisadas += 1
            
            # Verificar duplicata
            numero_controle = lic.get('numeroControlePNCP')
            if not numero_controle or numero_controle in vistas:
                rejeitadas_duplicata += 1
                continue
            
            # FILTRO PRINCIPAL: Busca SIMPLES no objeto (como Thiago)
            objeto_compra = lic.get('objetoCompra', '')
            if not objeto_compra:
                rejeitadas_palavra += 1
                continue
            
            objeto_normalizado = self._normalizar_simples(objeto_compra)
            
            # Verifica se QUALQUER termo está presente (OR lógico)
            encontrou_termo = False
            for termo in termos_normalizados:
                if termo in objeto_normalizado:
                    encontrou_termo = True
                    break
            
            if not encontrou_termo:
                rejeitadas_palavra += 1
                logger.debug(f"❌ Rejeitada por palavra: {numero_controle} - '{objeto_compra[:50]}...'")
                continue
            
            # Filtro de data (SIMPLES como Thiago)
            data_encerramento = lic.get('dataEncerramentoProposta')
            if data_encerramento:
                try:
                    if isinstance(data_encerramento, str):
                        data_clean = data_encerramento.split('T')[0]
                        data_encerramento_dt = datetime.strptime(data_clean, '%Y-%m-%d')
                        
                        # Aceita licitações que encerram hoje ou no futuro
                        if data_encerramento_dt.date() < data_atual.date():
                            rejeitadas_prazo += 1
                            continue
                except:
                    pass  # Se erro na data, aceita a licitação
            
            # Filtro de cidade (se especificado)
            if cidades_filtro:
                cidade_licitacao = None
                unidade_orgao = lic.get('unidadeOrgao', {})
                if unidade_orgao:
                    cidade_licitacao = unidade_orgao.get('municipioNome', '').strip().upper()
                
                if not cidade_licitacao or cidade_licitacao not in cidades_filtro:
                    rejeitadas_cidade += 1
                    continue
            
            # Licitação aprovada
            vistas.add(numero_controle)
            licitacoes_aprovadas.append(lic)
        
        # Log dos resultados
        logger.info("📊 RESULTADO DO FILTRO LOCAL:")
        logger.info(f"   📋 Analisadas: {total_analisadas}")
        logger.info(f"   ✅ Aprovadas: {len(licitacoes_aprovadas)}")
        logger.info(f"   ❌ Rejeitadas:")
        logger.info(f"      🔄 Duplicatas: {rejeitadas_duplicata}")
        logger.info(f"      🔤 Palavra: {rejeitadas_palavra}")
        logger.info(f"      ⏰ Prazo: {rejeitadas_prazo}")
        logger.info(f"      🏙️ Cidade: {rejeitadas_cidade}")
        
        return licitacoes_aprovadas

    def _normalizar_simples(self, texto: str) -> str:
        """
        Normalização SIMPLES como o Thiago faz:
        - Remove acentos
        - Lowercase
        - Remove pontuação
        - NÃO aplica stemmer agressivo
        """
        import unicodedata
        import re
        
        if not texto:
            return ""
        
        # Lowercase
        texto = texto.lower()
        
        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
        
        # Remove pontuação mas mantém espaços
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        
        # Remove espaços múltiplos
        texto = ' '.join(texto.split())
        
        return texto

    def _construir_parametros(
        self,
        filtros: Dict[str, Any],
        palavras_busca: List[str],  # ❌ IGNORADO - não vai para API
        pagina: int,
        itens_por_pagina: int
    ) -> Dict[str, Any]:
        """
        PARÂMETROS REAIS DO THIAGO:
        - SÓ filtros básicos
        - SEM parâmetro 'busca'
        - Período amplo para pegar mais licitações
        """
        from datetime import datetime, timedelta

        # Período amplo como o Thiago
        hoje = datetime.now()
        data_inicio_dt = hoje - timedelta(days=7)   # Última semana
        data_fim_dt = hoje + timedelta(days=120)    # Próximos 4 meses
        data_inicial = data_inicio_dt.strftime('%Y%m%d')
        data_final = data_fim_dt.strftime('%Y%m%d')

        # Parâmetros BÁSICOS
        params = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': min(itens_por_pagina, 50)  # Máximo 50
        }

        # Modalidade (obrigatória)
        if filtros.get('modalidades'):
            modal_slug = filtros['modalidades'][0]
            modalidade_codigo = self.modalidade_para_codigo.get(modal_slug, 8)
            params['codigoModalidadeContratacao'] = modalidade_codigo
        else:
            params['codigoModalidadeContratacao'] = 8  # Pregão eletrônico

        # UF se especificada
        if filtros.get('estados') and filtros['estados'][0]:
            params['uf'] = filtros['estados'][0]

        # Valor mínimo/máximo (eficientes na API)
        if filtros.get('valor_minimo') is not None:
            params['valorMinimo'] = filtros['valor_minimo']
        if filtros.get('valor_maximo') is not None:
            params['valorMaximo'] = filtros['valor_maximo']

        # ❌ NÃO INCLUIR: params['busca'] = ...
        
        logger.debug("📤 Parâmetros API (SIMPLES):")
        for key, value in params.items():
            logger.debug(f"   {key}: {value}")
        
        if palavras_busca:
            logger.debug(f"🎯 Palavras para filtro LOCAL: {palavras_busca}")
        
        return params

    async def _buscar_licitacoes_async(
        self,
        session: aiohttp.ClientSession,
        filtros: Dict[str, Any],
        palavras_busca: List[str],
        pagina: int,
        itens_por_pagina: int
    ) -> Dict[str, Any]:
        """Busca assíncrona básica"""
        try:
            endpoint = f"{self.base_url}/contratacoes/publicacao"
            params = self._construir_parametros(filtros, palavras_busca, pagina, itens_por_pagina)
            
            async with session.get(endpoint, params=params, timeout=self.timeout) as response:
                if response.status != 200:
                    logger.warning(f"Erro HTTP {response.status} na página {pagina}")
                    return {'data': []}
                
                if "application/json" not in response.headers.get("Content-Type", ""):
                    logger.warning(f"Resposta não-JSON na página {pagina}")
                    return {'data': []}

                data = await response.json()
                resultados = data.get('data', [])
                
                logger.debug(f"API página {pagina}: {len(resultados)} licitações")
                return data

        except Exception as e:
            logger.warning(f"Erro na busca página {pagina}: {str(e)}")
            return {'data': []}

    def buscar_licitacoes(
        self,
        filtros: Dict[str, Any],
        palavras_busca: List[str],
        pagina: int = 1,
        itens_por_pagina: int = 500
    ) -> Dict[str, Any]:
        """Versão síncrona"""
        return asyncio.run(
            self.buscar_licitacoes_paralelo(
                filtros,
                palavras_busca,
                pagina,
                itens_por_pagina
            )
        )

# Exemplo de uso (para teste)
if __name__ == '__main__':
    try:
        repo = LicitacaoPNCPRepository()
        
        filtros_exemplo = {
            "estados": ["SC"],
            "valor_minimo": 10000,
            "modalidades": ["pregao_eletronico"]
        }
        palavras_exemplo = ["serviços de limpeza"]
        
        print("Buscando licitações com filtros...")
        resultado = repo.buscar_licitacoes(filtros_exemplo, palavras_exemplo)
        
        if resultado and resultado.get('data'):
            print(f"Total de registros encontrados: {resultado.get('metadados', {}).get('totalRegistros')}")
            print(f"Exibindo os primeiros {len(resultado['data'])} resultados:")
            for i, licitacao in enumerate(resultado['data']):
                print(f"  {i+1}. Objeto: {licitacao.get('objetoCompra')[:80]}...")
                print(f"     Órgão: {licitacao.get('orgaoEntidade', {}).get('razaoSocial')}")
                print(f"     Valor: {licitacao.get('valorTotalEstimado')}")
                print("-" * 20)
        else:
            print("Nenhuma licitação encontrada ou erro na busca.")

    except ConnectionError as e:
        print(e)
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante o teste: {e}") 