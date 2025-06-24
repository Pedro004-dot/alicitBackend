"""
PNCP Search Service
Serviço para busca de licitações na API oficial do PNCP por palavras-chave
"""
import requests
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import re

# Importar serviço de persistência
try:
    from .supabase_persistence_service import SupabasePersistenceService
except ImportError:
    SupabasePersistenceService = None

# Importar BidRepository para salvamento compatível com pncp_api.py
try:
    from ..repositories.bid_repository import BidRepository
    from ..config.database import db_manager
except ImportError:
    try:
        # Fallback para import absoluto
        from src.repositories.bid_repository import BidRepository
        from src.config.database import db_manager
    except ImportError:
        BidRepository = None
        db_manager = None

logger = logging.getLogger(__name__)

class PNCPSearchService:
    """Service para busca de licitações na API oficial do PNCP"""
    
    def __init__(self):
        self.base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
        self.items_base_url = "https://pncp.gov.br/api/pncp/v1/orgaos"
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 2
        
        # Modalidades corrigidas (códigos oficiais da API PNCP)
        self.modalidades = {
            'pregao_eletronico': 8,  # Corrigido: era 5, agora 8
            'pregao_presencial': 8,  # Mesmo código, diferenciado por outros campos
            'concorrencia': 5,
            'convite': 6,
            'tomada_precos': 7,
            'dispensa': 1,
            'inexigibilidade': 2,
            'leilao': 9,
            'concurso': 10,
            'todas': None  # Para buscar todas as modalidades
        }
        
        # Cache para evitar requisições repetidas
        self._items_cache = {}
        
        # Inicializar serviço de persistência Supabase
        if SupabasePersistenceService:
            self.persistence_service = SupabasePersistenceService()
        else:
            self.persistence_service = None
            logger.warning("⚠️ Serviço de persistência não disponível")
        
        # Inicializar BidRepository para salvamento compatível
        if BidRepository and db_manager:
            self.bid_repository = BidRepository(db_manager)
        else:
            self.bid_repository = None
            logger.warning("⚠️ BidRepository não disponível")
    
    def search_by_keywords(
        self, 
        keywords: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        modalidade: str = 'todas',  # Mudado padrão para 'todas'
        max_pages: int = 10,  # Aumentado para 10 páginas
        limit_per_page: int = 500,
        save_results: bool = False,
        apenas_abertas: bool = False  # ← NOVO PARÂMETRO
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Busca licitações na API do PNCP por palavras-chave no objeto
        
        Args:
            keywords: Palavras-chave separadas por espaço (ex: "computadores notebooks")
            data_inicio: Data inicial no formato AAAAMMDD (opcional, padrão: 30 dias atrás)
            data_fim: Data final no formato AAAAMMDD (opcional, padrão: 60 dias no futuro)
            modalidade: Modalidade da licitação (padrão: 'todas' para buscar todas)
            max_pages: Máximo de páginas para buscar (padrão: 10)
            limit_per_page: Limite de resultados por página (máximo da API: 500)
            save_results: Se deve salvar resultados no Supabase (padrão: False)
            apenas_abertas: Se deve retornar apenas licitações com status "aberta" ou em andamento (padrão: False)
            
        Returns:
            Tupla com (lista_de_licitacoes, metadados_da_busca)
        """
        try:
            logger.info(f"🔍 Iniciando busca PNCP por palavras-chave: '{keywords}'" + 
                       (" (APENAS ABERTAS)" if apenas_abertas else " (TODAS)"))
            
            # ===== DATAS OTIMIZADAS PARA LICITAÇÕES ATIVAS =====
            if not data_inicio or not data_fim:
                hoje = datetime.now()
                
                if apenas_abertas:
                    # Para licitações abertas: 60 dias atrás até 60 dias no futuro (período equilibrado)
                    inicio = hoje - timedelta(days=60)
                    fim = hoje + timedelta(days=60)
                    data_inicio = data_inicio or inicio.strftime('%Y%m%d')
                    data_fim = data_fim or fim.strftime('%Y%m%d')
                    logger.info(f"📅 Modo 'apenas abertas': {data_inicio} a {data_fim} (120 dias total)")
                else:
                    # Para todas: últimos 90 dias (como antes)
                    inicio = hoje - timedelta(days=90)
                    data_inicio = data_inicio or inicio.strftime('%Y%m%d')
                    data_fim = data_fim or (hoje - timedelta(days=1)).strftime('%Y%m%d')
                    logger.info(f"📅 Modo 'todas': {data_inicio} a {data_fim}")
            
            # Validar datas
            self._validate_date_range(data_inicio, data_fim)
            
            # Preparar palavras-chave para busca
            keywords_list = self._prepare_keywords(keywords)
            
            # Buscar licitações na API - usar lógica avançada para modalidade "todas"
            all_results = []
            search_metadata = {
                'total_pages_searched': 0,
                'total_api_results': 0,
                'total_filtered_results': 0,
                'keywords_used': keywords_list,
                'date_range': f"{data_inicio} a {data_fim}",
                'modalidade': modalidade,
                'apenas_abertas': apenas_abertas,  # ← NOVO METADATA
                'search_time': datetime.now().isoformat()
            }
            
            # Obter modalidades a buscar usando lógica do método avançado
            if modalidade == 'todas':
                # Usar múltiplas modalidades como no método avançado
                modalidades_busca = [8, 5, 6, 7, 1, 2]  # Pregão, Concorrência, Convite, Tomada, Dispensa, Inexigibilidade
                logger.info(f"🔍 Modalidade 'todas': buscando em {len(modalidades_busca)} modalidades")
            else:
                codigo_modalidade = self.modalidades.get(modalidade, 8)
                modalidades_busca = [codigo_modalidade]
            
            # Buscar em cada modalidade
            for modalidade_codigo in modalidades_busca:
                logger.info(f"📋 Buscando modalidade {modalidade_codigo}")
                
                page = 1
                while page <= max_pages:
                    logger.info(f"📄 Modalidade {modalidade_codigo} - Página {page}/{max_pages}")
                    
                    # Fazer requisição para a API
                    page_results, has_next = self._fetch_page(
                        data_inicio, data_fim, modalidade_codigo, page, limit_per_page
                    )
                    
                    if not page_results:
                        logger.info(f"⚠️ Modalidade {modalidade_codigo} - Página {page} retornou vazia, parando busca desta modalidade")
                        break
                    
                    search_metadata['total_api_results'] += len(page_results)
                    
                    # Filtrar resultados por palavras-chave (busca mais flexível)
                    filtered_results = self._filter_by_keywords_flexible(page_results, keywords_list)
                    logger.info(f"🎯 Modalidade {modalidade_codigo} - Página {page}: {len(page_results)} da API → {len(filtered_results)} após filtro")
                    all_results.extend(filtered_results)
                    
                    # Se não há próxima página, parar busca desta modalidade
                    if not has_next:
                        logger.info(f"✅ Modalidade {modalidade_codigo} - Última página alcançada na página {page}")
                        break
                    
                    page += 1
                    
                    # Pequeno delay para não sobrecarregar a API
                    time.sleep(0.5)
                
                # Atualizar total de páginas pesquisadas
                search_metadata['total_pages_searched'] += page - 1
                
                # Delay entre modalidades para não sobrecarregar
                if modalidade_codigo != modalidades_busca[-1]:  # Não fazer delay na última modalidade
                    time.sleep(1)
            
            search_metadata['total_filtered_results'] = len(all_results)
            
            # Ordenar por relevância se temos palavras-chave
            if keywords_list:
                all_results = self._sort_by_relevance(all_results, keywords_list)
            
            # Formatar resultados para o padrão do sistema
            formatted_results = self._format_results_for_system(all_results)
            
            # ===== FILTRAR APENAS LICITAÇÕES ABERTAS SE SOLICITADO =====
            if apenas_abertas and formatted_results:
                logger.info(f"🔍 Aplicando filtro 'apenas abertas' em {len(formatted_results)} licitações...")
                formatted_results = self._filter_apenas_abertas(formatted_results)
                search_metadata['total_filtered_results'] = len(formatted_results)
                search_metadata['filtro_abertas_aplicado'] = True
                logger.info(f"✅ {len(formatted_results)} licitações abertas encontradas")
            
            # Salvar resultados no Supabase se solicitado
            if save_results and formatted_results and self.persistence_service:
                try:
                    logger.info(f"💾 Salvando {len(formatted_results)} licitações no Supabase...")
                    persistence_stats = self.persistence_service.save_licitacoes(
                        formatted_results, 
                        include_items=False,  # Busca básica não inclui itens
                        search_metadata=search_metadata
                    )
                    search_metadata['persistence_stats'] = persistence_stats
                    logger.info(f"✅ Salvamento concluído: {persistence_stats}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar resultados: {e}")
                    search_metadata['persistence_error'] = str(e)
            
            logger.info(f"✅ Busca concluída: {len(formatted_results)} licitações encontradas")
            
            return formatted_results, search_metadata
            
        except Exception as e:
            logger.error(f"❌ Erro na busca PNCP: {e}")
            return [], {'error': str(e), 'search_time': datetime.now().isoformat()}
    
    def _fetch_page(
        self, 
        data_inicio: str, 
        data_fim: str, 
        codigo_modalidade: Optional[int], 
        page: int,
        limit: int = 500
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Busca uma página específica na API do PNCP
        
        Returns:
            Tupla com (resultados_da_pagina, tem_proxima_pagina)
        """
        params = {
            'dataInicial': data_inicio,
            'dataFinal': data_fim,
            'pagina': page
        }
        
        # A API agora EXIGE codigoModalidadeContratacao
        # Se não especificado, usar 8 (Pregão Eletrônico) como padrão
        if codigo_modalidade is not None:
            params['codigoModalidadeContratacao'] = codigo_modalidade
        else:
            # Para buscar "todas", vamos usar modalidade mais comum (Pregão Eletrônico)
            params['codigoModalidadeContratacao'] = 8
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"🌐 Requisição PNCP: {self.base_url} - Página {page} (tentativa {attempt + 1})")
                logger.debug(f"📝 Parâmetros: {params}")
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'AlicitSaas/1.0 (Busca Automatizada de Licitações)',
                        'Accept': 'application/json'
                    }
                )
                
                logger.debug(f"📡 Status Code: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                # Extrair dados e metadados
                results = data.get('data', [])
                metadata = data.get('metadados', {})
                
                # Verificar se há próxima página
                has_next = metadata.get('proximaPagina') is not None
                
                logger.debug(f"✅ Página {page}: {len(results)} resultados, próxima: {has_next}")
                
                return results, has_next
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ Erro na tentativa {attempt + 1}: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise Exception(f"Falha após {self.max_retries} tentativas: {e}")
        
        return [], False
    
    def _prepare_keywords(self, keywords: str) -> List[str]:
        """
        Prepara e normaliza palavras-chave para busca
        """
        # Limpar e normalizar
        keywords = keywords.lower().strip()
        
        # Remover caracteres especiais, manter apenas letras, números e espaços
        keywords = re.sub(r'[^a-záàâãéèêíìîóòôõúùûç\s\d]', ' ', keywords)
        
        # Dividir por espaços e remover palavras muito pequenas
        words = [word.strip() for word in keywords.split() if len(word.strip()) >= 2]
        
        # Remover palavras muito comuns que não agregam valor à busca
        stop_words = {'de', 'da', 'do', 'das', 'dos', 'e', 'ou', 'para', 'com', 'sem', 'por', 'em', 'no', 'na', 'nos', 'nas'}
        words = [word for word in words if word not in stop_words]
        
        return words
    
    def _filter_by_keywords_flexible(self, results: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Filtra resultados por palavras-chave com busca flexível (OU) usando estrutura real da API PNCP
        Com DEBUG para identificar problemas na busca
        """
        if not keywords:
            logger.info("⚠️ Nenhuma palavra-chave fornecida, retornando todos os resultados")
            return results
        
        logger.info(f"🔍 Filtrando {len(results)} resultados por palavras-chave: {keywords}")
        
        filtered = []
        
        for i, result in enumerate(results):
            # Usar estrutura real da API PNCP - com LOG DEBUG
            objeto_compra_raw = result.get('objetoCompra', '')
            info_complementar_raw = result.get('informacaoComplementar', '')
            
            # DEBUG: Mostrar primeira licitação como exemplo
            if i == 0:
                logger.info(f"📋 EXEMPLO - Primeira licitação:")
                logger.info(f"   🎯 Objeto: {objeto_compra_raw[:100]}...")
                logger.info(f"   ℹ️ Info complementar: {info_complementar_raw[:50]}...")
                logger.info(f"   🏢 Órgão: {result.get('orgaoEntidade', {}).get('razaoSocial', 'N/A')}")
                logger.info(f"   🔗 PNCP ID: {result.get('numeroControlePNCP', 'N/A')}")
            
            objeto_compra = str(objeto_compra_raw).lower()
            info_complementar = str(info_complementar_raw).lower()
            
            # Extrair dados de órgão da estrutura aninhada
            orgao_entidade = result.get('orgaoEntidade', {})
            nome_orgao = str(orgao_entidade.get('razaoSocial', '')).lower()
            
            unidade_orgao = result.get('unidadeOrgao', {})
            nome_unidade = str(unidade_orgao.get('nomeUnidade', '')).lower()
            
            numero_compra = str(result.get('numeroCompra', '')).lower()
            processo = str(result.get('processo', '')).lower()
            
            # Texto completo para busca
            texto_completo = f"{objeto_compra} {info_complementar} {nome_orgao} {nome_unidade} {numero_compra} {processo}"
            
            # DEBUG: Para as primeiras 3 licitações, mostrar o processo de matching
            if i < 3:
                logger.info(f"🔍 [{i+1}] Analisando: {result.get('numeroControlePNCP', 'N/A')}")
                logger.info(f"   📝 Texto completo (primeiros 100 chars): {texto_completo[:100]}...")
                matches_found = []
                for keyword in keywords:
                    if keyword in texto_completo:
                        matches_found.append(keyword)
                        
                logger.info(f"   ✅ Palavras encontradas: {matches_found if matches_found else 'Nenhuma'}")
                
                # Se não achou nenhuma palavra, tentar busca mais flexível
                if not matches_found:
                    # Tentar busca por partes da palavra (substring)
                    flexible_matches = []
                    for keyword in keywords:
                        if any(keyword in word for word in texto_completo.split()):
                            flexible_matches.append(f"{keyword}*")
                    
                    if flexible_matches:
                        logger.info(f"   🔍 Matches flexíveis: {flexible_matches}")
            
            # Verificar se PELO MENOS UMA palavra-chave está presente (busca OU)
            keyword_found = False
            for keyword in keywords:
                if keyword in texto_completo:
                    keyword_found = True
                    break
            
            if keyword_found:
                # Calcular score de relevância básico
                score = 0
                matched_keywords = []
                for keyword in keywords:
                    if keyword in objeto_compra:
                        score += 3  # Peso maior para objeto
                        matched_keywords.append(f"{keyword}(obj:3)")
                    elif keyword in info_complementar:
                        score += 2  # Peso médio para info complementar
                        matched_keywords.append(f"{keyword}(info:2)")
                    elif keyword in nome_orgao or keyword in nome_unidade:
                        score += 1  # Peso menor para órgão/unidade
                        matched_keywords.append(f"{keyword}(org:1)")
                    elif keyword in numero_compra or keyword in processo:
                        score += 0.5  # Peso pequeno para número/processo
                        matched_keywords.append(f"{keyword}(proc:0.5)")
                
                result['relevance_score'] = score
                result['matched_keywords'] = matched_keywords  # Para debug
                filtered.append(result)
                
                # Log das primeiras 3 que passaram no filtro
                if len(filtered) <= 3:
                    logger.info(f"✅ PASSOU NO FILTRO: {result.get('numeroControlePNCP', 'N/A')}")
                    logger.info(f"   🎯 Score: {score}")
                    logger.info(f"   🔑 Matches: {matched_keywords}")
        
        logger.info(f"📊 Filtro finalizado: {len(filtered)}/{len(results)} licitações passaram")
        
        # Se nenhuma licitação passou, fazer um diagnóstico
        if len(filtered) == 0:
            logger.warning("⚠️ NENHUMA LICITAÇÃO PASSOU NO FILTRO - DIAGNÓSTICO:")
            logger.warning(f"   🔍 Palavras-chave procuradas: {keywords}")
            
            # Mostrar amostras do que foi encontrado na primeira licitação
            if results:
                first_result = results[0]
                objeto_sample = str(first_result.get('objetoCompra', ''))[:200]
                logger.warning(f"   📝 Exemplo de objeto encontrado: {objeto_sample}")
                
                # Tentar encontrar palavras similares
                palavras_do_objeto = objeto_sample.lower().split()
                logger.warning(f"   🔤 Algumas palavras do objeto: {palavras_do_objeto[:10]}")
                
                # Busca flexível - verificar se há palavras que contenham as keywords
                for keyword in keywords:
                    similar_words = [word for word in palavras_do_objeto if keyword in word or word in keyword]
                    if similar_words:
                        logger.warning(f"   🔍 Palavras similares a '{keyword}': {similar_words}")
        
        return filtered

    def _sort_by_relevance(self, results: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Ordena resultados por relevância baseada no score
        """
        return sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    def _format_results_for_system(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Formata resultados da API PNCP para o padrão do sistema usando estrutura real da API
        """
        formatted = []
        
        for result in results:
            try:
                # Extrair dados de estruturas aninhadas
                orgao_entidade = result.get('orgaoEntidade', {})
                unidade_orgao = result.get('unidadeOrgao', {})
                
                # ===== EXTRAÇÃO MELHORADA DE UF E MUNICÍPIO =====
                uf = ''
                municipio = ''
                
                # Método 1: Tentar extrair UF/município do unidadeOrgao (mais específico)
                if unidade_orgao:
                    # UF pode estar diretamente no unidadeOrgao
                    uf = unidade_orgao.get('ufSigla', '') or unidade_orgao.get('uf', '')
                    municipio = unidade_orgao.get('municipioNome', '') or unidade_orgao.get('municipio', '')
                    
                    # Se ainda não temos UF, tentar no endereço da unidade
                    if not uf and 'endereco' in unidade_orgao:
                        endereco = unidade_orgao['endereco']
                        uf = endereco.get('uf', '') or endereco.get('ufSigla', '')
                        municipio = municipio or endereco.get('municipio', '') or endereco.get('municipioNome', '')
                
                # Método 2: Fallback para orgao_entidade se não encontrou na unidade
                if not uf and orgao_entidade:
                    if 'endereco' in orgao_entidade:
                        endereco = orgao_entidade['endereco']
                        uf = endereco.get('uf', '') or endereco.get('ufSigla', '')
                        municipio = municipio or endereco.get('municipio', '') or endereco.get('municipioNome', '')
                
                # Normalizar UF para 2 caracteres
                if uf and len(uf) > 2:
                    uf = uf[:2].upper()
                elif uf:
                    uf = uf.upper()

                # Mapeamento de campos da API PNCP real para o sistema
                formatted_result = {
                    'pncp_id': result.get('numeroControlePNCP', ''),
                    'objeto_compra': result.get('objetoCompra', ''),
                    'modalidade_nome': result.get('modalidadeNome', ''),
                    'codigo_modalidade': result.get('modalidadeId'),
                    'unidade_compra': unidade_orgao.get('codigoUnidade', ''),
                    'data_abertura_proposta': result.get('dataAberturaProposta'),
                    'data_encerramento_proposta': result.get('dataEncerramentoProposta'),
                    'valor_total_estimado': result.get('valorTotalEstimado', 0),
                    'valor_total_homologado': result.get('valorTotalHomologado', 0),
                    'uf': uf,
                    'municipio': municipio,
                    'situacao': result.get('situacaoCompraNome', ''),
                    'situacao_id': result.get('situacaoCompraId'),
                    'srp': result.get('srp', False),
                    'fonte_dados': 'PNCP_API',
                    'data_importacao': datetime.now().isoformat(),
                    
                    # Campos específicos da API PNCP (estrutura real)
                    'orgao_cnpj': orgao_entidade.get('cnpj', ''),
                    'orgao_razao_social': orgao_entidade.get('razaoSocial', ''),
                    'unidade_nome': unidade_orgao.get('nomeUnidade', ''),
                    'numero_compra': result.get('numeroCompra', ''),
                    'processo': result.get('processo', ''),
                    'ano_compra': result.get('anoCompra'),
                    'sequencial_compra': result.get('sequencialCompra'),
                    'data_publicacao_pncp': result.get('dataPublicacaoPncp'),
                    'data_atualizacao': result.get('dataAtualizacao'),
                    'modo_disputa': result.get('modoDisputaNome', ''),
                    'modo_disputa_id': result.get('modoDisputaId'),  # ← CAMPO ADICIONADO
                    'tipo_instrumento': result.get('tipoInstrumentoConvocatorioNome', ''),
                    'informacao_complementar': result.get('informacaoComplementar'),
                    'link_sistema_origem': result.get('linkSistemaOrigem'),
                    
                    # Scores de relevância se disponíveis
                    'relevance_score': result.get('relevance_score', 0),
                    'keyword_score': result.get('keyword_score', 0),
                    'item_score': result.get('item_score', 0),
                    'total_score': result.get('total_score', 0),
                    
                    # Dados completos da API para referência
                    'api_data': result
                }
                
                formatted.append(formatted_result)
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao formatar resultado: {e}")
                continue
        
        return formatted
    
    def _get_modalidade_name(self, codigo: Optional[int]) -> str:
        """
        Converte código da modalidade para nome amigável
        """
        modalidades_map = {
            5: 'Concorrência',
            6: 'Convite',
            7: 'Tomada de Preços',
            8: 'Pregão Eletrônico',
            9: 'Leilão',
            10: 'Concurso'
        }
        
        return modalidades_map.get(codigo, f'Modalidade {codigo}' if codigo else 'Não informado')
    
    def _validate_date_range(self, data_inicio: str, data_fim: str):
        """
        Valida intervalo de datas
        """
        try:
            inicio = datetime.strptime(data_inicio, '%Y%m%d')
            fim = datetime.strptime(data_fim, '%Y%m%d')
            
            if inicio > fim:
                raise ValueError("Data de início deve ser anterior à data de fim")
            
            # Limitar a 90 dias para evitar sobrecarga
            diff = (fim - inicio).days
            if diff > 90:
                raise ValueError("Intervalo máximo permitido é de 90 dias")
                
        except ValueError as e:
            if "time data" in str(e):
                raise ValueError("Formato de data inválido. Use AAAAMMDD (ex: 20240101)")
            raise
    
    def get_available_modalities(self) -> Dict[str, Any]:
        """
        Retorna modalidades disponíveis para busca
        """
        return {
            'modalidades': [
                {'codigo': 'pregao_eletronico', 'nome': 'Pregão Eletrônico', 'api_code': 8},
                {'codigo': 'concorrencia', 'nome': 'Concorrência', 'api_code': 5},
                {'codigo': 'convite', 'nome': 'Convite', 'api_code': 6},
                {'codigo': 'tomada_precos', 'nome': 'Tomada de Preços', 'api_code': 7},
                {'codigo': 'leilao', 'nome': 'Leilão', 'api_code': 9},
                {'codigo': 'concurso', 'nome': 'Concurso', 'api_code': 10}
            ],
            'recomendacoes': {
                'modalidade_padrao': 'pregao_eletronico',
                'intervalo_maximo_dias': 90,
                'palavras_minimas': 2,
                'max_paginas_recomendado': 5
            }
        }

    def search_by_keywords_advanced(
        self, 
        keywords: str,
        filtros: Dict[str, Any] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        max_pages: int = 10,  # Aumentado para 10 páginas
        limit_per_page: int = 500,
        include_items: bool = True,
        save_results: bool = False,
        apenas_abertas: bool = False  # ← NOVO PARÂMETRO
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Busca avançada de licitações com sistema de score de relevância
        
        Args:
            keywords: Palavras-chave separadas por espaço
            filtros: Filtros avançados (UF, valor, modalidades, etc.)
            data_inicio: Data inicial no formato AAAAMMDD (padrão: 90 dias atrás)
            data_fim: Data final no formato AAAAMMDD (padrão: hoje)
            max_pages: Máximo de páginas para buscar (padrão: 10)
            limit_per_page: Limite de resultados por página
            include_items: Se deve buscar itens detalhados (mais lento)
            save_results: Se deve salvar resultados no Supabase (padrão: False)
            apenas_abertas: Se deve retornar apenas licitações com status "aberta" ou em andamento (padrão: False)
            
        Returns:
            Tupla com (lista_de_licitacoes_com_score, metadados_da_busca)
        """
        try:
            logger.info(f"🔍 Iniciando busca PNCP avançada: '{keywords}'" + 
                       (" (APENAS ABERTAS)" if apenas_abertas else " (TODAS)"))
            
            # Preparar filtros padrão
            filtros = filtros or {}
            
            # ===== DATAS OTIMIZADAS PARA LICITAÇÕES ATIVAS =====
            if not data_inicio or not data_fim:
                hoje = datetime.now()
                
                if apenas_abertas:
                    # Para licitações abertas: 60 dias atrás até 60 dias no futuro (período equilibrado)
                    inicio = hoje - timedelta(days=60)
                    fim = hoje + timedelta(days=60)
                    data_inicio = data_inicio or inicio.strftime('%Y%m%d')
                    data_fim = data_fim or fim.strftime('%Y%m%d')
                    logger.info(f"📅 Modo 'apenas abertas': {data_inicio} a {data_fim} (120 dias total)")
                else:
                    # Para todas: últimos 90 dias (como antes)
                    inicio = hoje - timedelta(days=90)
                    data_inicio = data_inicio or inicio.strftime('%Y%m%d')
                    data_fim = data_fim or (hoje - timedelta(days=1)).strftime('%Y%m%d')
                    logger.info(f"📅 Modo 'todas': {data_inicio} a {data_fim}")
            
            # Validar datas
            self._validate_date_range(data_inicio, data_fim)
            
            # Preparar palavras-chave
            keywords_list = self._prepare_keywords(keywords)
            
            # 1. BUSCAR LICITAÇÕES BÁSICAS
            all_results = []
            search_metadata = {
                'total_pages_searched': 0,
                'total_api_results': 0,
                'total_filtered_results': 0,
                'keywords_used': keywords_list,
                'date_range': f"{data_inicio} a {data_fim}",
                'filtros_aplicados': filtros,
                'search_time': datetime.now().isoformat(),
                'include_items': include_items,
                'apenas_abertas': apenas_abertas  # ← NOVO METADATA
            }
            
            # Obter modalidades a buscar (padrão: todas se não especificado)
            modalidades_busca = self._get_modalidades_filtro(filtros)
            
            for modalidade_codigo in modalidades_busca:
                logger.info(f"📋 Buscando modalidade {modalidade_codigo or 'todas'}")
                
                # Buscar licitações desta modalidade
                modalidade_results = self._fetch_all_pages(
                    data_inicio, data_fim, modalidade_codigo, max_pages, 
                    limit_per_page, filtros
                )
                
                all_results.extend(modalidade_results)
                search_metadata['total_api_results'] += len(modalidade_results)
            
            search_metadata['total_pages_searched'] = max_pages * len(modalidades_busca)
            
            # 2. FILTRAR E CALCULAR SCORE DE RELEVÂNCIA
            logger.info(f"🎯 Processando {len(all_results)} licitações da API")
            
            licitacoes_com_score = []
            for licitacao in all_results:
                # Usar busca flexível primeiro
                if self._matches_keywords_flexible(licitacao, keywords_list):
                    score = self._calculate_keyword_score(licitacao, keywords_list)
                    licitacao['keyword_score'] = score
                    licitacoes_com_score.append(licitacao)
            
            logger.info(f"🔍 {len(licitacoes_com_score)} licitações passaram no filtro de palavras-chave")
            
            # 3. BUSCAR ITENS DETALHADOS (se solicitado)
            if include_items and licitacoes_com_score:
                logger.info(f"📦 Buscando itens detalhados para todas as {len(licitacoes_com_score)} licitações encontradas")
                
                # Buscar itens para TODAS as licitações encontradas
                for i, licitacao in enumerate(licitacoes_com_score, 1):
                    numero_controle = licitacao.get('numeroControlePNCP', 'N/A')
                    logger.info(f"📦 [{i}/{len(licitacoes_com_score)}] Buscando itens para {numero_controle}")
                    
                    try:
                        itens = self._get_licitacao_items(licitacao)
                        if itens:
                            # Recalcular score incluindo itens
                            item_score = self._calculate_items_keyword_score(itens, keywords_list)
                            licitacao['item_score'] = item_score
                            licitacao['total_score'] = licitacao['keyword_score'] + item_score
                            licitacao['itens_detalhados'] = itens  # Todos os itens
                            licitacao['total_itens'] = len(itens)
                            logger.info(f"✅ {len(itens)} itens encontrados e adicionados ao score")
                        else:
                            licitacao['total_score'] = licitacao['keyword_score']
                            licitacao['item_score'] = 0
                            licitacao['itens_detalhados'] = []
                            licitacao['total_itens'] = 0
                            logger.info("⚠️ Nenhum item encontrado")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao buscar itens para {numero_controle}: {e}")
                        licitacao['total_score'] = licitacao['keyword_score']
                        licitacao['item_score'] = 0
                        licitacao['itens_detalhados'] = []
                        licitacao['total_itens'] = 0
                    
                    # Pequeno delay para não sobrecarregar a API de itens
                    time.sleep(0.3)
            else:
                # Sem busca de itens, score total = score básico
                for licitacao in licitacoes_com_score:
                    licitacao['total_score'] = licitacao['keyword_score']
                    licitacao['item_score'] = 0
                    licitacao['itens_detalhados'] = []
                    licitacao['total_itens'] = 0
            
            # 4. APLICAR FILTROS AVANÇADOS
            licitacoes_filtradas = self._apply_advanced_filters(licitacoes_com_score, filtros)
            
            search_metadata['total_filtered_results'] = len(licitacoes_filtradas)
            
            # 5. ORDENAR POR RELEVÂNCIA
            licitacoes_ordenadas = sorted(
                licitacoes_filtradas, 
                key=lambda x: x['total_score'], 
                reverse=True
            )
            
            # 6. FORMATAR RESULTADOS
            formatted_results = self._format_results_for_system(licitacoes_ordenadas)
            
            # ===== FILTRAR APENAS LICITAÇÕES ABERTAS SE SOLICITADO =====
            if apenas_abertas and formatted_results:
                logger.info(f"🔍 Aplicando filtro 'apenas abertas' em {len(formatted_results)} licitações...")
                formatted_results = self._filter_apenas_abertas(formatted_results)
                search_metadata['total_filtered_results'] = len(formatted_results)
                search_metadata['filtro_abertas_aplicado'] = True
                logger.info(f"✅ {len(formatted_results)} licitações abertas encontradas")
            
            # 7. SALVAR RESULTADOS NO SUPABASE SE SOLICITADO
            if save_results and formatted_results and self.persistence_service:
                try:
                    logger.info(f"💾 Salvando {len(formatted_results)} licitações no Supabase...")
                    persistence_stats = self.persistence_service.save_licitacoes(
                        formatted_results, 
                        include_items=include_items,  # Incluir itens se foram buscados
                        search_metadata=search_metadata
                    )
                    search_metadata['persistence_stats'] = persistence_stats
                    logger.info(f"✅ Salvamento concluído: {persistence_stats}")
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar resultados: {e}")
                    search_metadata['persistence_error'] = str(e)
            
            logger.info(f"✅ Busca avançada concluída: {len(formatted_results)} licitações relevantes")
            
            return formatted_results, search_metadata
            
        except Exception as e:
            logger.error(f"❌ Erro na busca PNCP avançada: {e}")
            return [], {'error': str(e), 'search_time': datetime.now().isoformat()}

    def _matches_keywords_flexible(self, licitacao: Dict[str, Any], keywords: List[str]) -> bool:
        """
        Verifica se a licitação contém pelo menos uma das palavras-chave (busca OU) - estrutura real API PNCP
        """
        if not keywords:
            return True
        
        # Usar estrutura real da API PNCP
        objeto_compra = str(licitacao.get('objetoCompra', '')).lower()
        info_complementar = str(licitacao.get('informacaoComplementar', '')).lower()
        
        # Extrair dados de órgão da estrutura aninhada
        orgao_entidade = licitacao.get('orgaoEntidade', {})
        nome_orgao = str(orgao_entidade.get('razaoSocial', '')).lower()
        
        unidade_orgao = licitacao.get('unidadeOrgao', {})
        nome_unidade = str(unidade_orgao.get('nomeUnidade', '')).lower()
        
        numero_compra = str(licitacao.get('numeroCompra', '')).lower()
        processo = str(licitacao.get('processo', '')).lower()
        
        # Texto completo para busca
        texto_completo = f"{objeto_compra} {info_complementar} {nome_orgao} {nome_unidade} {numero_compra} {processo}"
        
        # Verificar se PELO MENOS UMA palavra-chave está presente
        return any(keyword in texto_completo for keyword in keywords)

    def _get_modalidades_filtro(self, filtros: Dict[str, Any]) -> List[Optional[int]]:
        """Obtém lista de códigos de modalidades baseado nos filtros"""
        modalidades_filtro = filtros.get('modalidades', ['todas'])  # Padrão: buscar todas
        
        if not modalidades_filtro or 'todas' in modalidades_filtro:
            # Como a API agora exige modalidade, buscar as principais modalidades
            return [8, 5, 6, 7, 1, 2]  # Pregão, Concorrência, Convite, Tomada, Dispensa, Inexigibilidade
        
        codigos = []
        for modalidade in modalidades_filtro:
            codigo = self.modalidades.get(modalidade)
            if codigo is not None and codigo not in codigos:
                codigos.append(codigo)
        
        return codigos if codigos else [8]  # Pregão eletrônico como fallback

    def _fetch_all_pages(
        self, 
        data_inicio: str, 
        data_fim: str, 
        codigo_modalidade: Optional[int], 
        max_pages: int,
        limit_per_page: int,
        filtros: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Busca todas as páginas de uma modalidade específica"""
        all_results = []
        
        page = 1
        while page <= max_pages:
            logger.debug(f"📄 Buscando página {page}/{max_pages} - modalidade {codigo_modalidade}")
            
            page_results, has_next = self._fetch_page_with_filters(
                data_inicio, data_fim, codigo_modalidade, page, limit_per_page, filtros
            )
            
            if not page_results:
                break
            
            all_results.extend(page_results)
            
            if not has_next:
                logger.debug(f"✅ Última página alcançada na página {page}")
                break
            
            page += 1
            time.sleep(0.5)  # Rate limiting
        
        return all_results

    def _fetch_page_with_filters(
        self, 
        data_inicio: str, 
        data_fim: str, 
        codigo_modalidade: Optional[int], 
        page: int,
        limit: int,
        filtros: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Busca uma página com filtros geográficos aplicados"""
        params = {
            'dataInicial': data_inicio,
            'dataFinal': data_fim,
            'pagina': page
        }
        
        # Adicionar modalidade se especificada
        if codigo_modalidade is not None:
            params['codigoModalidadeContratacao'] = codigo_modalidade
        
        # Aplicar filtros geográficos
        if filtros.get('uf'):
            params['uf'] = filtros['uf']
        
        if filtros.get('municipio_ibge'):
            params['codigoMunicipioIbge'] = filtros['municipio_ibge']
        
        if filtros.get('cnpj_orgao'):
            params['cnpj'] = filtros['cnpj_orgao']
        
        # Usar método de fetch existente
        return self._fetch_page(data_inicio, data_fim, codigo_modalidade, page, limit)

    def _calculate_keyword_score(self, licitacao: Dict[str, Any], keywords: List[str]) -> float:
        """
        Calcula score de relevância baseado em palavras-chave com pesos - estrutura real API PNCP
        """
        if not keywords:
            return 0.0
        
        score = 0.0
        
        # Usar estrutura real da API PNCP com tratamento de None
        objeto_compra_raw = licitacao.get('objetoCompra') or ''
        info_raw = licitacao.get('informacaoComplementar') or ''
        
        # Extrair dados de órgão da estrutura aninhada
        orgao_entidade = licitacao.get('orgaoEntidade', {})
        nome_orgao_raw = orgao_entidade.get('razaoSocial') or ''
        
        unidade_orgao = licitacao.get('unidadeOrgao', {})
        nome_unidade_raw = unidade_orgao.get('nomeUnidade') or ''
        
        # Garantir que são strings antes de aplicar .lower()
        texto_objeto = str(objeto_compra_raw).lower() if objeto_compra_raw else ''
        texto_info_complementar = str(info_raw).lower() if info_raw else ''
        texto_orgao = str(nome_orgao_raw).lower() if nome_orgao_raw else ''
        texto_unidade = str(nome_unidade_raw).lower() if nome_unidade_raw else ''
        
        for keyword in keywords:
            keyword_lower = str(keyword).lower()
            
            # Peso 4.0 para matches no objeto principal (campo mais importante)
            if texto_objeto:
                count_objeto = texto_objeto.count(keyword_lower)
                score += count_objeto * 4.0
                
                # Bonus para match exato da keyword completa
                if keyword_lower in texto_objeto:
                    score += 2.0
            
            # Peso 1.5 para matches em informações complementares
            if texto_info_complementar:
                count_info = texto_info_complementar.count(keyword_lower)
                score += count_info * 1.5
            
            # Peso 1.0 para matches em dados do órgão
            if texto_orgao:
                count_orgao = texto_orgao.count(keyword_lower)
                score += count_orgao * 1.0
            
            # Peso 0.8 para matches em dados da unidade
            if texto_unidade:
                count_unidade = texto_unidade.count(keyword_lower)
                score += count_unidade * 0.8
        
        return score

    def get_licitacao_items(self, pncp_id: str) -> List[Dict[str, Any]]:
        """
        Método público para buscar itens de uma licitação pelo PNCP ID
        """
        try:
            # Parse do número de controle para construir URL
            # Formato esperado: CNPJ-1-SEQUENCIAL/ANO
            parts = pncp_id.split('-')
            if len(parts) < 3:
                logger.warning(f"⚠️ Formato inválido do PNCP ID: {pncp_id}")
                return []
            
            cnpj = parts[0]
            ano_seq = parts[2].split('/')
            if len(ano_seq) != 2:
                logger.warning(f"⚠️ Formato inválido do ano/sequencial: {parts[2]}")
                return []
            
            sequencial = ano_seq[0].lstrip('0') or '0'  # Remove zeros à esquerda
            ano = ano_seq[1]
            
            # Montar URL da API de itens
            url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"
            
            logger.info(f"📦 Buscando itens para {pncp_id}: {url}")
            
            # Fazer requisição
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'AlicitSaas/1.0 (Busca Automatizada de Licitações)',
                    'Accept': 'application/json'
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extrair itens
            itens = data if isinstance(data, list) else data.get('data', [])
            
            logger.info(f"✅ {len(itens)} itens encontrados para {pncp_id}")
            
            # Cache do resultado
            self._items_cache[pncp_id] = itens
            
            return itens
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar itens para {pncp_id}: {e}")
            return []

    def _get_licitacao_items(self, licitacao: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Busca itens específicos de uma licitação usando a API de itens PNCP
        Baseado na mesma lógica do sistema de matching em pncp_api.py
        """
        try:
            # Tentar extrair informações do número de controle PNCP
            numero_controle = licitacao.get('numeroControlePNCP', '')
            if not numero_controle:
                return []
            
            # Verificar cache primeiro
            if numero_controle in self._items_cache:
                return self._items_cache[numero_controle]
            
            # Método 1: Usar estrutura da API PNCP diretamente (mais confiável)
            orgao_entidade = licitacao.get('orgaoEntidade', {})
            orgao_cnpj = orgao_entidade.get('cnpj', '')
            ano_compra = licitacao.get('anoCompra', '')
            sequencial_compra = licitacao.get('sequencialCompra', '')
            
            if orgao_cnpj and ano_compra and sequencial_compra:
                # Montar URL da API de itens (mesmo formato do matching)
                url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{orgao_cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
                
                logger.info(f"📦 Buscando itens para {numero_controle}: {url}")
                
                # Fazer requisição
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'AlicitSaas/1.0 (Busca Automatizada de Licitações)',
                        'Accept': 'application/json'
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extrair itens
                itens = data if isinstance(data, list) else data.get('data', [])
                
                logger.info(f"✅ {len(itens)} itens encontrados para {numero_controle}")
                
                # Cache do resultado
                self._items_cache[numero_controle] = itens
                
                return itens
            
            else:
                # Método 2: Parse do número de controle (fallback)
                # Formato esperado: CNPJ-1-SEQUENCIAL/ANO
                parts = numero_controle.split('-')
                if len(parts) < 3:
                    return []
                
                cnpj = parts[0]
                ano_seq = parts[2].split('/')
                if len(ano_seq) != 2:
                    return []
                
                sequencial = ano_seq[0]
                ano = ano_seq[1]
                
                # Montar URL da API de itens
                url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"
                
                logger.info(f"📦 Buscando itens (fallback) para {numero_controle}: {url}")
                
                # Fazer requisição
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={
                        'User-Agent': 'AlicitSaas/1.0 (Busca Automatizada de Licitações)',
                        'Accept': 'application/json'
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extrair itens
                itens = data if isinstance(data, list) else data.get('data', [])
                
                logger.info(f"✅ {len(itens)} itens encontrados (fallback) para {numero_controle}")
                
                # Cache do resultado
                self._items_cache[numero_controle] = itens
                
                return itens
            
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível buscar itens para {numero_controle}: {e}")
            return []

    def _calculate_items_keyword_score(self, itens: List[Dict[str, Any]], keywords: List[str]) -> float:
        """Calcula score baseado nos itens detalhados da licitação"""
        if not itens or not keywords:
            return 0.0
        
        score = 0.0
        
        for item in itens:
            # Tratamento seguro para campos que podem ser None
            desc_raw = item.get('descricaoItem') or item.get('descricao') or ''
            det_raw = item.get('descricaoDetalhada') or ''
            
            item_descricao = str(desc_raw).lower() if desc_raw else ''
            item_detalhada = str(det_raw).lower() if det_raw else ''
            
            for keyword in keywords:
                keyword_lower = str(keyword).lower()
                
                # Peso 2.0 para matches na descrição do item
                if item_descricao:
                    count_desc = item_descricao.count(keyword_lower)
                    score += count_desc * 2.0
                
                # Peso 1.0 para matches na descrição detalhada
                if item_detalhada:
                    count_det = item_detalhada.count(keyword_lower)
                    score += count_det * 1.0
        
        return score

    def _apply_advanced_filters(self, licitacoes: List[Dict[str, Any]], filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aplica filtros avançados às licitações"""
        if not filtros:
            return licitacoes
        
        resultado = licitacoes
        
        # Filtro por valor
        valor_min = filtros.get('valor_min')
        if valor_min is not None:
            resultado = [l for l in resultado if l.get('valorTotalEstimado', 0) >= valor_min]
        
        valor_max = filtros.get('valor_max')
        if valor_max is not None:
            resultado = [l for l in resultado if l.get('valorTotalEstimado', 0) <= valor_max]
        
        # Filtro por benefício MEI/EPP
        if filtros.get('apenas_mei_epp', False):
            resultado = [l for l in resultado if self._has_mei_epp_benefit(l)]
        
        # Filtro por situação
        situacao = filtros.get('situacao')
        if situacao:
            resultado = [l for l in resultado if l.get('situacaoCompraId') == situacao]
        
        # Filtro por SRP (Sistema de Registro de Preços)
        if filtros.get('apenas_srp', False):
            resultado = [l for l in resultado if l.get('srp', False)]
        
        # Filtro por categoria/tipo
        categoria = filtros.get('categoria')
        if categoria:
            resultado = [l for l in resultado if self._match_categoria(l, categoria)]
        
        return resultado

    def _has_mei_epp_benefit(self, licitacao: Dict[str, Any]) -> bool:
        """Verifica se a licitação tem benefícios para MEI/EPP"""
        # Implementar lógica baseada nos campos da API PNCP
        # Campos possíveis: beneficioMeEpp, participacaoExclusivaMeEpp, etc.
        return (
            licitacao.get('beneficioMeEpp', False) or
            licitacao.get('participacaoExclusivaMeEpp', False) or
            licitacao.get('subcontratacaoMeEpp', False)
        )

    def _match_categoria(self, licitacao: Dict[str, Any], categoria: str) -> bool:
        """Verifica se a licitação pertence à categoria especificada"""
        # Implementar baseado em classificação de objeto ou outros campos
        objeto = licitacao.get('objeto', '').lower()
        
        categorias_map = {
            'material': ['material', 'equipamento', 'produto', 'bem'],
            'servico': ['serviço', 'prestação', 'manutenção', 'consultoria'],
            'obra': ['obra', 'construção', 'reforma', 'edificação'],
            'tic': ['software', 'sistema', 'tecnologia', 'informática', 'ti']
        }
        
        keywords_categoria = categorias_map.get(categoria.lower(), [])
        return any(kw in objeto for kw in keywords_categoria)

    def get_available_filters(self) -> Dict[str, Any]:
        """
        Retorna filtros disponíveis para a busca avançada
        """
        return {
            'modalidades': [
                {'codigo': 'pregao_eletronico', 'nome': 'Pregão Eletrônico', 'api_code': 8},
                {'codigo': 'pregao_presencial', 'nome': 'Pregão Presencial', 'api_code': 8},
                {'codigo': 'concorrencia', 'nome': 'Concorrência', 'api_code': 5},
                {'codigo': 'convite', 'nome': 'Convite', 'api_code': 6},
                {'codigo': 'tomada_precos', 'nome': 'Tomada de Preços', 'api_code': 7},
                {'codigo': 'dispensa', 'nome': 'Dispensa', 'api_code': 1},
                {'codigo': 'inexigibilidade', 'nome': 'Inexigibilidade', 'api_code': 2},
                {'codigo': 'leilao', 'nome': 'Leilão', 'api_code': 9},
                {'codigo': 'concurso', 'nome': 'Concurso', 'api_code': 10}
            ],
            'categorias': [
                {'codigo': 'material', 'nome': 'Materiais/Produtos'},
                {'codigo': 'servico', 'nome': 'Serviços'},
                {'codigo': 'obra', 'nome': 'Obras/Construção'},
                {'codigo': 'tic', 'nome': 'Tecnologia da Informação'}
            ],
            'faixas_valor': [
                {'codigo': 'pequena', 'nome': 'Até R$ 10.000', 'min': 0, 'max': 10000},
                {'codigo': 'media', 'nome': 'R$ 10.001 a R$ 100.000', 'min': 10001, 'max': 100000},
                {'codigo': 'grande', 'nome': 'R$ 100.001 a R$ 1.000.000', 'min': 100001, 'max': 1000000},
                {'codigo': 'muito_grande', 'nome': 'Acima de R$ 1.000.000', 'min': 1000001, 'max': None}
            ],
            'recomendacoes': {
                'modalidade_padrao': 'pregao_eletronico',
                'intervalo_maximo_dias': 90,
                'palavras_minimas': 2,
                'max_paginas_recomendado': 5,
                'incluir_itens_padrao': True
            }
        }

    def save_results_to_postgres(self, licitacoes: List[Dict[str, Any]], include_items: bool = True) -> Dict[str, Any]:
        """
        Salva resultados de busca usando BidRepository para compatibilidade total com pncp_api.py
        Garante que todos os campos sejam salvos corretamente, incluindo datas de abertura e encerramento
        """
        if not self.bid_repository:
            logger.error("❌ BidRepository não está disponível para salvamento")
            return {
                'licitacoes_salvas': 0,
                'licitacoes_atualizadas': 0,
                'itens_salvos': 0,
                'erros': [{'erro': 'BidRepository não disponível'}]
            }
        
        stats = {
            'licitacoes_salvas': 0,
            'licitacoes_atualizadas': 0,
            'itens_salvos': 0,
            'erros': []
        }
        
        try:
            logger.info(f"💾 Iniciando salvamento de {len(licitacoes)} licitações no PostgreSQL...")
            
            for i, licitacao in enumerate(licitacoes, 1):
                pncp_id = licitacao.get('pncp_id', '')
                logger.info(f"📝 [{i}/{len(licitacoes)}] Processando {pncp_id}")
                
                try:
                    # Verificar se licitação já existe
                    existing = self.bid_repository.get_by_pncp_id(pncp_id)
                    
                    # Salvar licitação usando método compatível com pncp_api.py
                    licitacao_id = self.bid_repository.save_licitacao(licitacao)
                    
                    if licitacao_id:
                        if existing:
                            stats['licitacoes_atualizadas'] += 1
                            logger.info(f"   🔄 Licitação atualizada: {pncp_id}")
                        else:
                            stats['licitacoes_salvas'] += 1
                            logger.info(f"   ✅ Licitação nova salva: {pncp_id}")
                        
                        # Salvar itens se disponíveis e solicitado
                        if include_items and licitacao.get('itens_detalhados'):
                            try:
                                success = self.bid_repository.save_bid_items(
                                    licitacao_id, 
                                    licitacao['itens_detalhados']
                                )
                                if success:
                                    itens_count = len(licitacao['itens_detalhados'])
                                    stats['itens_salvos'] += itens_count
                                    logger.info(f"   📦 {itens_count} itens salvos")
                                else:
                                    logger.warning(f"   ⚠️ Erro ao salvar itens para {pncp_id}")
                            except Exception as e:
                                logger.error(f"   ❌ Erro ao salvar itens para {pncp_id}: {e}")
                                stats['erros'].append({
                                    'pncp_id': pncp_id,
                                    'tipo': 'itens',
                                    'erro': str(e)
                                })
                        
                    else:
                        logger.error(f"   ❌ Falha ao salvar licitação {pncp_id}")
                        stats['erros'].append({
                            'pncp_id': pncp_id,
                            'tipo': 'licitacao',
                            'erro': 'Salvamento retornou None'
                        })
                
                except Exception as e:
                    logger.error(f"   ❌ Erro ao processar licitação {pncp_id}: {e}")
                    stats['erros'].append({
                        'pncp_id': pncp_id,
                        'tipo': 'processamento',
                        'erro': str(e)
                    })
            
            logger.info(f"✅ Salvamento PostgreSQL concluído:")
            logger.info(f"   📊 {stats['licitacoes_salvas']} novas licitações salvas")
            logger.info(f"   🔄 {stats['licitacoes_atualizadas']} licitações atualizadas")
            logger.info(f"   📦 {stats['itens_salvos']} itens salvos")
            logger.info(f"   ❌ {len(stats['erros'])} erros encontrados")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Erro geral no salvamento PostgreSQL: {e}")
            stats['erros'].append({'erro_geral': str(e)})
            return stats

    def _filter_apenas_abertas(self, licitacoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra apenas licitações que ainda estão abertas para propostas
        e adiciona classificação de urgência baseada no prazo
        
        Args:
            licitacoes: Lista de licitações formatadas
            
        Returns:
            Lista de licitações ainda abertas com classificação de urgência
        """
        abertas = []
        hoje = datetime.now()
        
        for licitacao in licitacoes:
            try:
                # Verificar situação/status
                situacao = str(licitacao.get('situacao', '')).lower()
                situacao_id = licitacao.get('situacao_id')
                
                # Status que indicam licitação aberta (baseado na API PNCP)
                status_abertas = [
                    'aberta', 'publicada', 'andamento', 'em andamento', 
                    'aguardando', 'recebendo propostas', 'ativa', 'publicado'
                ]
                
                # Verificar por nome da situação
                situacao_aberta = any(status in situacao for status in status_abertas)
                
                # Verificar por ID (códigos comuns de licitações abertas na API PNCP)
                # Baseado nos códigos mais comuns: 1=Publicada, 2=Aberta, etc.
                ids_abertas = [1, 2, 3, 4]  # Ajustar conforme necessário
                id_aberta = situacao_id in ids_abertas if situacao_id else False
                
                # ===== ANÁLISE DE DATAS E URGÊNCIA =====
                data_abertura_str = licitacao.get('data_inicio_lances') or licitacao.get('data_abertura_proposta')
                data_encerramento_str = licitacao.get('data_encerramento_proposta')
                
                data_valida = False
                dias_restantes = None
                urgencia = "indefinida"
                recomendada = False
                
                if data_encerramento_str:
                    try:
                        # Parse da data de encerramento
                        if 'T' in data_encerramento_str:
                            data_encerramento = datetime.fromisoformat(data_encerramento_str.replace('Z', '+00:00'))
                        else:
                            data_encerramento = datetime.strptime(data_encerramento_str, '%Y%m%d')
                        
                        # Calcular dias restantes
                        delta = data_encerramento - hoje
                        dias_restantes = delta.days
                        
                        # Licitação ainda está aberta se data de encerramento é futura
                        data_valida = dias_restantes > 0
                        
                        # ===== CLASSIFICAÇÃO DE URGÊNCIA =====
                        if dias_restantes <= 0:
                            urgencia = "encerrada"
                        elif dias_restantes <= 7:
                            urgencia = "urgente"      # 0-7 dias: URGENTE
                            recomendada = True
                        elif dias_restantes <= 15:
                            urgencia = "importante"   # 8-15 dias: IMPORTANTE  
                            recomendada = True
                        elif dias_restantes <= 30:
                            urgencia = "moderada"     # 16-30 dias: MODERADA
                            recomendada = True
                        elif dias_restantes <= 60:
                            urgencia = "planejamento" # 31-60 dias: PLANEJAMENTO
                            recomendada = True
                        else:
                            urgencia = "futura"       # 60+ dias: FUTURA
                            recomendada = False
                        
                        logger.debug(f"📅 {licitacao.get('pncp_id')}: {dias_restantes} dias → {urgencia}")
                        
                    except (ValueError, TypeError) as e:
                        logger.debug(f"⚠️ Erro ao parsear data de encerramento: {e}")
                        data_valida = False
                
                # Critério final: deve ter situação aberta OU data de encerramento futura
                if situacao_aberta or id_aberta or data_valida:
                    # ===== ADICIONAR METADADOS DE URGÊNCIA =====
                    licitacao['dias_restantes'] = dias_restantes
                    licitacao['urgencia'] = urgencia
                    licitacao['recomendada'] = recomendada
                    licitacao['prazo_score'] = self._calculate_prazo_score(dias_restantes)
                    
                    abertas.append(licitacao)
                    
                    if recomendada:
                        logger.debug(f"⭐ RECOMENDADA: {licitacao.get('pncp_id')} - {urgencia} ({dias_restantes} dias)")
                    else:
                        logger.debug(f"✅ Aberta: {licitacao.get('pncp_id')} - {urgencia}")
                else:
                    logger.debug(f"❌ Fechada: {licitacao.get('pncp_id')} - {situacao}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar licitação: {e}")
                # Em caso de erro, incluir na lista (comportamento conservador)
                licitacao['urgencia'] = "indefinida"
                licitacao['recomendada'] = False
                licitacao['dias_restantes'] = None
                licitacao['prazo_score'] = 0
                abertas.append(licitacao)
        
        # ===== ORDENAR POR URGÊNCIA (mais urgentes primeiro) =====
        abertas_ordenadas = sorted(abertas, key=lambda x: (
            x.get('prazo_score', 0),           # Score de prazo (maior = mais urgente)
            -(x.get('dias_restantes') or 999), # Menos dias restantes primeiro
            x.get('relevance_score', 0)        # Score de relevância como desempate
        ), reverse=True)
        
        # Log do resumo de urgência
        recomendadas = sum(1 for l in abertas_ordenadas if l.get('recomendada', False))
        urgentes = sum(1 for l in abertas_ordenadas if l.get('urgencia') == 'urgente')
        importantes = sum(1 for l in abertas_ordenadas if l.get('urgencia') == 'importante')
        
        logger.info(f"📊 Classificação de urgência:")
        logger.info(f"   ⭐ {recomendadas} RECOMENDADAS (0-60 dias)")
        logger.info(f"   🚨 {urgentes} URGENTES (0-7 dias)")
        logger.info(f"   ⚠️ {importantes} IMPORTANTES (8-15 dias)")
        
        return abertas_ordenadas
    
    def _calculate_prazo_score(self, dias_restantes: Optional[int]) -> float:
        """
        Calcula score baseado na urgência do prazo
        Quanto menor o prazo, maior o score (mais urgente = mais importante)
        """
        if dias_restantes is None or dias_restantes <= 0:
            return 0.0
        
        if dias_restantes <= 7:
            return 100.0    # URGENTE: score máximo
        elif dias_restantes <= 15:
            return 80.0     # IMPORTANTE: score alto
        elif dias_restantes <= 30:
            return 60.0     # MODERADA: score médio-alto
        elif dias_restantes <= 60:
            return 40.0     # PLANEJAMENTO: score médio
        else:
            return 20.0     # FUTURA: score baixo 