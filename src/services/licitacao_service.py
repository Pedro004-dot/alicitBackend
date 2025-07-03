"""
Licitacao Service
Serviço principal para orquestrar a busca e o enriquecimento de dados de licitações.
"""
import logging
from typing import List, Dict, Any
import hashlib
import json

# Importar os novos componentes da arquitetura
from repositories.licitacao_repository import LicitacaoPNCPRepository
from services.openai_service import OpenAIService
from services.cache_service import CacheService  # ✨ NOVO
from matching.pncp_api import fetch_bid_items_from_pncp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicitacaoService:
    """
    Service com ESTRATÉGIA REAL DO THIAGO:
    - Busca simples mas eficaz
    - Sinônimos opcionais e controlados
    - Foco em resultados práticos
    """

    def __init__(self):
        try:
            self.openai_service = OpenAIService()
            logger.info("✅ OpenAI Service inicializado")
        except Exception as e:
            logger.warning(f"⚠️ OpenAI Service indisponível: {e}")
            self.openai_service = None
            
        self.licitacao_repository = LicitacaoPNCPRepository()
        self.cache_service = CacheService(ttl_seconds=3600) # ✨ NOVO: Cache com 1h de TTL

    def _gerar_cache_key(self, filtros: Dict[str, Any]) -> str:
        """Gera uma chave de cache única e determinística a partir dos filtros."""
        
        # Normalizar e ordenar os filtros para garantir que a mesma busca sempre gere a mesma chave
        filtros_para_hash = {
            'palavra_chave': filtros.get('palavra_chave', '').lower().strip(),
            'estados': sorted([uf.upper() for uf in filtros.get('estados', []) if uf]),
            'modalidades': sorted([m.lower() for m in filtros.get('modalidades', []) if m]),
            'cidades': sorted([c.lower() for c in filtros.get('cidades', []) if c]),
            'valor_minimo': filtros.get('valor_minimo'),
            'valor_maximo': filtros.get('valor_maximo'),
            'usar_sinonimos': filtros.get('usar_sinonimos', False),
            'incluir_itens': filtros.get('incluir_itens', False)
        }
        
        # Converter o dicionário ordenado para uma string JSON
        filtros_str = json.dumps(filtros_para_hash, sort_keys=True)
        
        # Gerar o hash MD5 da string
        hash_obj = hashlib.md5(filtros_str.encode('utf-8'))
        
        return f"licitacoes:{hash_obj.hexdigest()}"

    def _gerar_palavras_busca_simples(self, palavra_chave: str, usar_sinonimos: bool = False) -> List[str]:
        """
        GERAÇÃO OBRIGATÓRIA DE SINÔNIMOS:
        - A busca agora é conceitual, não por palavras soltas.
        - Palavra original sempre incluída + sinônimos gerados via IA.
        """
        if not palavra_chave:
            raise ValueError("Palavra-chave é obrigatória")
            
        palavras_busca = [palavra_chave]
        
        # A geração de sinônimos agora é OBRIGATÓRIA para enriquecer a busca.
        if self.openai_service:
            try:
                logger.info(f"🔍 Gerando sinônimos obrigatórios para: '{palavra_chave}'")
                sinonimos = self.openai_service.gerar_sinonimos(palavra_chave)
                
                # Limitar a 4 sinônimos (5 termos total) para não diluir
                sinonimos_limitados = sinonimos[:4] if sinonimos else []
                
                # Adicionar só sinônimos válidos e diferentes
                for sinonimo in sinonimos_limitados:
                    if (sinonimo and 
                        len(sinonimo.strip()) > 2 and 
                        sinonimo.lower() != palavra_chave.lower() and
                        sinonimo not in palavras_busca):
                        palavras_busca.append(sinonimo)
                
                logger.info(f"✨ Sinônimos adicionados: {palavras_busca[1:]}")
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao gerar sinônimos, busca seguirá com o termo original: {e}")
        else:
            logger.warning("⚠️ OpenAI Service não está disponível. A busca usará apenas o termo original.")
        
        # Garantir máximo de 5 termos
        palavras_busca = palavras_busca[:5]
        
        logger.info(f"🎯 Palavras finais para busca: {palavras_busca}")
        return palavras_busca

    def buscar_licitacoes(
        self,
        filtros: Dict[str, Any],
        pagina: int = 1,
        itens_por_pagina: int = 500
    ) -> Dict[str, Any]:
        """
        BUSCA PRINCIPAL com estratégia REAL DO THIAGO e CACHE:
        - Verifica o cache antes de executar a busca pesada.
        - Salva o resultado no cache após uma busca bem-sucedida.
        """
        # ✨ NOVO: Lógica de cache
        cache_key = self._gerar_cache_key(filtros)
        resultado_cache = self.cache_service.get(cache_key)

        if resultado_cache:
            # Se encontrou no cache, aplica a paginação e retorna
            return self._aplicar_paginacao_no_resultado(resultado_cache, pagina, itens_por_pagina)

        # Se não estiver no cache, executa a busca completa
        try:
            palavra_chave = filtros.get('palavra_chave')
            if not palavra_chave:
                raise ValueError("Palavra-chave é obrigatória")
                
            # Gerar palavras de busca (SIMPLES)
            usar_sinonimos = filtros.get('usar_sinonimos', False)  # Padrão FALSE
            palavras_busca = self._gerar_palavras_busca_simples(palavra_chave, usar_sinonimos)
            
            logger.info(f"🎯 BUSCA ESTRATÉGIA REAL THIAGO")
            logger.info(f"📝 Palavra-chave: '{palavra_chave}'")
            logger.info(f"✨ Sinônimos: {'habilitados' if usar_sinonimos else 'desabilitados'}")
            logger.info(f"🔍 Termos de busca: {palavras_busca}")
            
            # Busca direta no PNCP (estratégia real Thiago)
            resultado_busca = self.buscar_licitacoes_pncp_simples(
                filtros,
                palavras_busca,
                pagina,
                itens_por_pagina
            )
            
            # Converter para formato esperado
            licitacoes_raw = resultado_busca.get('data', [])
            incluir_itens = filtros.get('incluir_itens', False)
            licitacoes_processadas = self._converter_licitacoes(licitacoes_raw, incluir_itens=incluir_itens)
            
            # Calcular agregações
            agregacoes = self._calcular_agregacoes(licitacoes_processadas)
            
            # Resultado final
            metadata_api = resultado_busca.get('metadados', {})
            resultado_final = {
                'total': metadata_api.get('totalRegistros', 0),
                'pagina_atual': metadata_api.get('pagina', pagina),
                'total_paginas': metadata_api.get('totalPaginas', 0),
                'licitacoes': licitacoes_processadas,
                'palavras_utilizadas': palavras_busca,
                'filtros_aplicados': filtros,
                'agregacoes': agregacoes,
                'combinacoes_buscadas': {
                    'estados': filtros.get('estados', []),
                    'modalidades': filtros.get('modalidades', [])
                },
                'estrategia_aplicada': {
                    'tipo': 'real_thiago_simples',
                    'sinonimos_usados': usar_sinonimos,
                    'total_termos': len(palavras_busca)
                }
            }

            logger.info(f"✅ Busca concluída: {len(licitacoes_processadas)} licitações encontradas")
            
            # ✨ NOVO: Salvar no cache antes de retornar
            self.cache_service.set(cache_key, resultado_final)
            
            # Aplicar paginação no resultado final antes de retornar
            return self._aplicar_paginacao_no_resultado(resultado_final, pagina, itens_por_pagina)

        except Exception as e:
            logger.error(f"❌ Erro na busca: {str(e)}")
            raise

    def buscar_licitacoes_pncp_simples(
        self,
        filtros: Dict[str, Any],
        palavras_busca: List[str],
        pagina: int = 1,
        itens_por_pagina: int = 500
    ) -> Dict[str, Any]:
        """
        Busca PNCP SIMPLES como o Thiago:
        - Sem threshold complexo
        - Sem configurações avançadas
        - Foco na simplicidade
        """
        try:
            logger.info(f"🔍 Busca PNCP SIMPLES")
            logger.info(f"📋 Filtros: {filtros}")
            logger.info(f"🎯 Palavras: {palavras_busca}")

            # Preparar filtros SIMPLES
            filtros_simples = {
                'estados': filtros.get('estados', []),
                'modalidades': filtros.get('modalidades', []),
                'cidades': filtros.get('cidades', []),
                'valor_minimo': filtros.get('valor_minimo'),
                'valor_maximo': filtros.get('valor_maximo'),
                # NÃO incluir configurações complexas
            }

            # Buscar no repositório
            resultado = self.licitacao_repository.buscar_licitacoes_paralelo(
                filtros_simples,
                palavras_busca,
                pagina,
                itens_por_pagina
            )
            
            # Aguardar se assíncrono
            if hasattr(resultado, '__await__'):
                import asyncio
                resultado = asyncio.run(resultado)

            licitacoes_encontradas = len(resultado.get('data', []))
            logger.info(f"✅ Busca SIMPLES concluída: {licitacoes_encontradas} licitações")
            
            return resultado

        except Exception as e:
            logger.error(f"❌ Erro na busca PNCP simples: {str(e)}")
            raise

    def _aplicar_paginacao_no_resultado(
        self, 
        resultado_completo: Dict[str, Any], 
        pagina: int, 
        itens_por_pagina: int
    ) -> Dict[str, Any]:
        """Aplica a paginação a um conjunto de resultados de licitação já carregado."""
        licitacoes = resultado_completo.get('licitacoes', [])
        total_itens = len(licitacoes)
        
        if total_itens == 0:
            return {
                **resultado_completo,
                'pagina_atual': pagina,
                'total_paginas': 0,
                'itens_por_pagina': itens_por_pagina,
            }

        inicio = (pagina - 1) * itens_por_pagina
        fim = inicio + itens_por_pagina
        licitacoes_paginadas = licitacoes[inicio:fim]
        
        total_paginas = (total_itens + itens_por_pagina - 1) // itens_por_pagina
        
        # Cria uma cópia do resultado e atualiza com os dados de paginação
        resultado_paginado = resultado_completo.copy()
        resultado_paginado.update({
            'licitacoes': licitacoes_paginadas,
            'pagina_atual': pagina,
            'total_paginas': total_paginas,
            'itens_por_pagina': itens_por_pagina,
            'total': total_itens, # Garante que o total reflita o número de itens antes da paginação
        })
        
        return resultado_paginado

    def _converter_licitacoes(self, licitacoes_raw: List[Dict[str, Any]], incluir_itens: bool = False) -> List[Dict[str, Any]]:
        """Conversão mantida igual - já está boa"""
        licitacoes_convertidas = []
        for raw in licitacoes_raw:
            try:
                orgao_info = raw.get('orgaoEntidade', {})
                unidade_info = raw.get('unidadeOrgao', {})
                uf = unidade_info.get('ufSigla') or orgao_info.get('uf') or 'N/A'

                licitacao = raw.copy()
                
                # Campos principais
                licitacao.update({
                    'id': raw.get('numeroControlePNCP'),
                    'numero_controle_pncp': raw.get('numeroControlePNCP'),
                    'objeto_compra': raw.get('objetoCompra'),
                    'modalidade_nome': raw.get('modalidadeNome'),
                    'orgao': orgao_info.get('razaoSocial'),
                    'unidade': unidade_info.get('nomeUnidade'),
                    'municipio_nome': unidade_info.get('municipioNome'),
                    'uf': uf,
                    'valor_total_estimado': raw.get('valorTotalEstimado'),
                    'data_publicacao_pncp': raw.get('dataPublicacaoPncp'),
                    'data_abertura_proposta': raw.get('dataAberturaProposta'),
                    'data_encerramento_proposta': raw.get('dataEncerramentoProposta'),
                    'situacao_compra_nome': raw.get('situacaoCompraNome'),
                    'link_sistema_origem': raw.get('linkSistemaOrigem'),
                })
                
                licitacoes_convertidas.append(licitacao)
                
            except Exception as e:
                logger.warning(f"Erro ao converter licitação {raw.get('numeroControlePNCP')}: {e}")
                continue
                
        return licitacoes_convertidas

    def _calcular_agregacoes(self, licitacoes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Agregações mantidas iguais"""
        if not licitacoes:
            return {}

        agregacoes = {
            'por_modalidade': {},
            'por_uf': {},
            'total_valor_estimado': 0,
        }
        
        for licitacao in licitacoes:
            # Por modalidade
            modalidade = licitacao.get('modalidade_nome', 'Não informada')
            agregacoes['por_modalidade'][modalidade] = agregacoes['por_modalidade'].get(modalidade, 0) + 1
            
            # Por UF
            uf = licitacao.get('uf', 'N/A')
            agregacoes['por_uf'][uf] = agregacoes['por_uf'].get(uf, 0) + 1
            
            # Valor total
            if licitacao.get('valor_total_estimado'):
                agregacoes['total_valor_estimado'] += licitacao['valor_total_estimado']
        
        # Ordenar por quantidade
        agregacoes['por_modalidade'] = dict(sorted(agregacoes['por_modalidade'].items(), key=lambda item: item[1], reverse=True))
        agregacoes['por_uf'] = dict(sorted(agregacoes['por_uf'].items(), key=lambda item: item[1], reverse=True))

        return agregacoes

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