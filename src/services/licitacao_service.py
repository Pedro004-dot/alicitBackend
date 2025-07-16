"""
Licitacao Service
Serviço principal para orquestrar a busca e o enriquecimento de dados de licitações.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

# Importar os novos componentes da arquitetura
from repositories.licitacao_pncp_repository import LicitacaoPNCPRepository
from services.openai_service import OpenAIService
from services.cache_service import CacheService  # ✨ NOVO
from matching.pncp_api import fetch_bid_items_from_pncp
from .search.source_registry import RegistroFontes
from .search.base_source import FonteBusca

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicitacaoService:
    """Serviço responsável por orquestrar a busca e a filtragem de licitações."""

    def __init__(self):
        if "pncp" not in RegistroFontes.listar_fontes():
            RegistroFontes.registrar("pncp", LicitacaoPNCPRepository)
        
        try:
            self.openai_service = OpenAIService()
            logger.info("OpenAI Service inicializado com sucesso.")
        except Exception as e:
            self.openai_service = None
            logger.warning(f"Não foi possível inicializar o OpenAI Service: {e}")

    def buscar_licitacoes(self, filtros: Optional[Dict] = None, fontes: Optional[List[str]] = None) -> Dict:
        filtros = filtros or {}
        fontes = fontes or ["pncp"]
        logger.info(f"Iniciando busca. Fontes: {fontes}, Filtros: {filtros}")

        # 1. Busca Bruta
        todas_licitacoes_brutas = []
        fontes_consultadas = []
        for nome_fonte in fontes:
            try:
                classe_fonte = RegistroFontes.obter_fonte(nome_fonte)
                fonte_instance = classe_fonte()
                logger.info(f"Buscando dados brutos na fonte: {nome_fonte}...")
                # A busca no repositório agora não usa filtros
                licitacoes_da_fonte = fonte_instance.buscar() 
                todas_licitacoes_brutas.extend(licitacoes_da_fonte)
                fontes_consultadas.append(nome_fonte)
                logger.info(f"Fonte {nome_fonte} retornou {len(licitacoes_da_fonte)} licitações brutas.")
            except Exception as e:
                logger.error(f"Erro ao buscar na fonte {nome_fonte}: {e}")

        # 2. Aplicar Filtros Locais
        logger.info(f"Total de {len(todas_licitacoes_brutas)} licitações brutas. Aplicando filtros locais...")
        licitacoes_filtradas = self._aplicar_filtros_locais(todas_licitacoes_brutas, filtros)
        logger.info(f"{len(licitacoes_filtradas)} licitações restantes após a filtragem.")

        # 3. Remover Duplicatas e Ordenar
        licitacoes_unicas = self._remover_duplicatas(licitacoes_filtradas)
        licitacoes_ordenadas = sorted(
            licitacoes_unicas,
            key=lambda x: x.get("data_abertura") or "",
            reverse=True
        )
        
        logger.info(f"Busca finalizada. Retornando {len(licitacoes_ordenadas)} licitações únicas e ordenadas.")
        return {
            "total": len(licitacoes_ordenadas),
            "licitacoes": licitacoes_ordenadas,
            "fontes_consultadas": fontes_consultadas
        }

    def _aplicar_filtros_locais(self, licitacoes: List[Dict], filtros: Dict) -> List[Dict]:
        """
        🔄 ATUALIZADO: Aplica a sequência de filtros em memória com sinônimos obrigatórios.
        """
        resultado = licitacoes

        # 1. Filtro de licitações ativas
        hoje = datetime.now().date()
        limite_futuro = hoje + timedelta(days=120)
        resultado = [
            lic for lic in resultado 
            if lic.get("data_encerramento") and 
               hoje < datetime.fromisoformat(lic["data_encerramento"].replace("Z", "+00:00")).date() <= limite_futuro
        ]
        logger.info(f"🕐 {len(resultado)} licitações ativas encontradas.")

        # 2. Filtro de Modalidade
        modalidades_filtro = filtros.get("modalidades")
        if modalidades_filtro:
            resultado = [lic for lic in resultado if lic.get("modalidade") in modalidades_filtro]
            logger.info(f"📋 {len(resultado)} licitações após filtro de modalidade.")

        # 3. Filtro de Estado (UF)
        estados_filtro = filtros.get("estados")
        if estados_filtro:
            resultado = [lic for lic in resultado if lic.get("uf") in estados_filtro]
            logger.info(f"🗺️ {len(resultado)} licitações após filtro de estado.")

        # 4. Filtro de Cidade
        cidades_filtro = filtros.get("cidades")
        if cidades_filtro:
             resultado = [lic for lic in resultado if lic.get("municipio") and any(c.lower() in lic.get("municipio").lower() for c in cidades_filtro)]
             logger.info(f"🏙️ {len(resultado)} licitações após filtro de cidade.")

        # 5. 🆕 MELHORADO: Filtro de Palavra-chave com Sinônimos SEMPRE APLICADOS
        palavra_chave = filtros.get("palavra_chave")
        if palavra_chave:
            logger.info(f"🔍 Aplicando filtro de palavra-chave: '{palavra_chave}'")
            
            # 🚀 SEMPRE gerar sinônimos (não depender de cache)
            termos_busca = self._gerar_palavras_busca(palavra_chave)
            logger.info(f"🎯 Filtrando com os termos: {termos_busca}")
            
            if termos_busca:
                filtrado_final = []
                matches_por_termo = {}
                
                for lic in resultado:
                    texto_busca = (lic.get("titulo", "") + " " + lic.get("descricao", "")).lower()
                    
                    # Verificar se algum termo está presente
                    match_encontrado = False
                    termo_match = None
                    
                    for termo in termos_busca:
                        if termo.lower() in texto_busca:
                            match_encontrado = True
                            termo_match = termo
                            
                            # Contabilizar matches por termo para analytics
                            if termo not in matches_por_termo:
                                matches_por_termo[termo] = 0
                            matches_por_termo[termo] += 1
                            break
                    
                    if match_encontrado:
                        lic['_matched_term'] = termo_match  # Debug info
                        filtrado_final.append(lic)
                
                resultado = filtrado_final
                
                # Log detalhado dos matches
                logger.info(f"🎯 {len(resultado)} licitações após filtro de palavra-chave.")
                for termo, count in matches_por_termo.items():
                    is_synonym = termo != palavra_chave.lower()
                    tipo = "sinônimo" if is_synonym else "termo original"
                    logger.info(f"   📊 '{termo}' ({tipo}): {count} matches")
            else:
                logger.warning("⚠️ Nenhum termo de busca válido gerado")
                
        return resultado

    def _gerar_palavras_busca(self, palavra_chave: str) -> List[str]:
        """
        🔄 ATUALIZADO: Gera uma lista de termos de busca, incluindo a palavra original e sinônimos.
        """
        if not palavra_chave: 
            return []
        
        # Sempre incluir a palavra original
        termos = [palavra_chave.lower()]
        
        if self.openai_service:
            try:
                logger.info(f"🔤 Gerando sinônimos para '{palavra_chave}'...")
                sinonimos = self.openai_service.gerar_sinonimos(palavra_chave, max_sinonimos=5)
                
                if sinonimos and len(sinonimos) > 1:
                    # sinonimos[0] é a palavra original, pegar os demais
                    sinonimos_novos = [s.lower() for s in sinonimos[1:] if s.lower() not in termos]
                    termos.extend(sinonimos_novos[:4])  # Limitar a 4 sinônimos extras
                    
                    logger.info(f"✅ Sinônimos gerados: {sinonimos_novos}")
                    logger.info(f"🎯 Termos finais para busca: {termos}")
                else:
                    logger.info("ℹ️ Nenhum sinônimo adicional gerado")
                    
            except Exception as e:
                logger.warning(f"⚠️ Erro ao gerar sinônimos: {e}. Usando apenas o termo original.")
        else:
            logger.info("ℹ️ OpenAI Service não disponível - usando apenas termo original")
            
        return termos

    def _remover_duplicatas(self, licitacoes: List[Dict]) -> List[Dict]:
        vistas = set()
        unicas = []
        for lic in licitacoes:
            id_lic = lic.get("id")
            if id_lic and id_lic not in vistas:
                vistas.add(id_lic)
                unicas.append(lic)
        return unicas

    def _resolver_provider(self, external_id: str) -> str:
        """
        Resolve o provider a partir do external_id.
        Pode ser expandido para novos providers facilmente.
        """
        if not external_id:
            return 'pncp'  # fallback seguro
        if external_id.startswith('pncp_') or external_id.isdigit():
            return 'pncp'
        elif external_id.startswith('comprasnet_'):
            return 'comprasnet'
        # Adicione outros providers conforme necessário
        return 'pncp'  # fallback

    def buscar_itens_para_licitacoes(self, licitacoes: List[Dict]) -> List[Dict]:
        """
        Para cada licitação, busca os itens usando o adaptador correto via factory.
        Retorna uma lista de dicts: {'licitacao': ..., 'itens': [...]}
        """
        from factories.data_source_factory import get_data_source_factory
        resultados = []
        factory = get_data_source_factory()

        for lic in licitacoes:
            external_id = lic.get('external_id') or lic.get('pncp_id')
            provider = self._resolver_provider(external_id)
            adapter = factory.get_data_source(provider)
            itens = []
            if adapter:
                try:
                    itens = adapter.get_opportunity_items(external_id)
                    logger.info(f"Itens buscados para {external_id} via provider {provider}: {len(itens)} encontrados.")
                except Exception as e:
                    logger.error(f"Erro ao buscar itens para {external_id} (provider {provider}): {e}")
            else:
                logger.warning(f"Provider '{provider}' não encontrado para external_id {external_id}")
            resultados.append({'licitacao': lic, 'itens': itens})
        return resultados

    def buscar_detalhes_por_id(self, licitacao_id):
        """
        Busca detalhes completos da licitação e seus itens pelo ID interno (UUID), apenas no banco local.
        """
        from repositories.licitacao_repository import LicitacaoRepository
        from repositories.bid_repository import BidRepository
        from config.database import db_manager
        lic_repo = LicitacaoRepository(db_manager)
        bid_repo = BidRepository(db_manager)
        licitacao = lic_repo.find_by_id(licitacao_id)
        if not licitacao:
            return None
        # Buscar itens relacionados
        itens = bid_repo.find_items_by_bid_id(licitacao_id)
        licitacao['itens'] = itens
        return licitacao

# Exemplo de uso (para teste)
if __name__ == '__main__':
    try:
        service = LicitacaoService()
        
        # Filtros de exemplo
        filtros_teste = {
            "palavra_chave": "sistema de monitoramento",
            "usar_sinonimos": True,
            "estados": ["RJ"],
            "valor_minimo": 100000
        }
        
        print("Iniciando busca completa pelo LicitacaoService...")
        resultado_final = service.buscar_licitacoes(filtros_teste)
        
        print("\n" + "="*50)
        print("      RESULTADO FINAL DA BUSCA")
        print("="*50)
        print(f"Total de Licitações Encontradas: {resultado_final['total']}")
        print(f"Página Atual: {resultado_final['pagina_atual']} de {resultado_final['total_paginas']}")
        print(f"Palavras Utilizadas na Busca: {resultado_final['palavras_utilizadas']}")
        
        print("\n--- Amostra de Licitações ---")
        for i, lic in enumerate(resultado_final['licitacoes'][:3]): # Mostra as 3 primeiras
            print(f"  {i+1}. Objeto: {lic['objeto_compra'][:80]}...")
            print(f"     Órgão: {lic['orgao']} ({lic['uf']})")
            print(f"     Modalidade: {lic['modalidade_nome']}")
            print(f"     Valor: R$ {lic['valor_total_estimado'] or 0:,.2f}")

        print("\n--- Agregações ---")
        print("Por Modalidade:", resultado_final['agregacoes'].get('por_modalidade'))
        print("Por UF:", resultado_final['agregacoes'].get('por_uf'))
        print(f"Valor Total Estimado (na página): R$ {resultado_final['agregacoes'].get('total_valor_estimado', 0):,.2f}")
        print("="*50)

    except (ValueError, ConnectionError) as e:
        print(f"ERRO: {e}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu no teste do serviço: {e}") 