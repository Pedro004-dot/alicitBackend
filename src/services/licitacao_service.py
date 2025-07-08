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
        """Aplica a sequência de filtros em memória."""
        resultado = licitacoes

        # 1. Filtro de licitações ativas
        hoje = datetime.now().date()
        limite_futuro = hoje + timedelta(days=120)
        resultado = [
            lic for lic in resultado 
            if lic.get("data_encerramento") and 
               hoje < datetime.fromisoformat(lic["data_encerramento"].replace("Z", "+00:00")).date() <= limite_futuro
        ]
        logger.info(f"{len(resultado)} licitações ativas encontradas.")

        # 2. Filtro de Modalidade
        modalidades_filtro = filtros.get("modalidades")
        if modalidades_filtro:
            resultado = [lic for lic in resultado if lic.get("modalidade") in modalidades_filtro]
            logger.info(f"{len(resultado)} licitações após filtro de modalidade.")

        # 3. Filtro de Estado (UF)
        estados_filtro = filtros.get("estados")
        if estados_filtro:
            resultado = [lic for lic in resultado if lic.get("uf") in estados_filtro]
            logger.info(f"{len(resultado)} licitações após filtro de estado.")

        # 4. Filtro de Cidade
        cidades_filtro = filtros.get("cidades")
        if cidades_filtro:
             resultado = [lic for lic in resultado if lic.get("municipio") and any(c.lower() in lic.get("municipio").lower() for c in cidades_filtro)]
             logger.info(f"{len(resultado)} licitações após filtro de cidade.")

        # 5. Filtro de Palavra-chave com Sinônimos
        palavra_chave = filtros.get("palavra_chave")
        if palavra_chave:
            termos_busca = self._gerar_palavras_busca(palavra_chave)
            logger.info(f"Filtrando com os termos: {termos_busca}")
            
            filtrado_final = []
            for lic in resultado:
                texto_busca = (lic.get("titulo", "") + " " + lic.get("descricao", "")).lower()
                if any(termo.lower() in texto_busca for termo in termos_busca):
                    filtrado_final.append(lic)
            resultado = filtrado_final
            logger.info(f"{len(resultado)} licitações após filtro de palavra-chave.")
            
        return resultado

    def _gerar_palavras_busca(self, palavra_chave: str) -> List[str]:
        """Gera uma lista de termos de busca, incluindo a palavra original e sinônimos."""
        if not palavra_chave: return []
        
        termos = [palavra_chave.lower()]
        if self.openai_service:
            try:
                logger.info(f"Gerando sinônimos para '{palavra_chave}'...")
                sinonimos = self.openai_service.gerar_sinonimos(palavra_chave)
                if sinonimos:
                    termos.extend([s.lower() for s in sinonimos[:4] if s.lower() not in termos])
            except Exception as e:
                logger.warning(f"Erro ao gerar sinônimos: {e}. Usando apenas o termo original.")
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