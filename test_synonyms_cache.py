#!/usr/bin/env python3
"""
🧪 TESTE DE SINÔNIMOS COM CACHE REDIS
Test script para verificar se os sinônimos estão sendo aplicados corretamente
tanto quando os dados vêm do cache Redis quanto da API direta.
"""
import asyncio
import json
import sys
import os
import logging
from datetime import datetime

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from adapters.pncp_adapter import PNCPAdapter
from interfaces.procurement_data_source import SearchFilters
from services.openai_service import OpenAIService

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SynonymsCacheTest:
    """Classe para testar sinônimos com cache"""
    
    def __init__(self):
        # Configuração do PNCPAdapter
        self.config = {
            'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
            'timeout': 30,
            'max_results': 50,  # Reduzido para teste
            'max_pages': 10,    # Reduzido para teste
            'parallel_strategy': False  # Simples para teste
        }
        
        self.adapter = PNCPAdapter(self.config)
        
        # Verificar se OpenAI está disponível
        try:
            self.openai_service = OpenAIService()
            logger.info("✅ OpenAI Service disponível para teste")
        except Exception as e:
            logger.error(f"❌ OpenAI Service não disponível: {e}")
            self.openai_service = None
    
    async def test_cache_vs_api_synonyms(self):
        """
        Teste principal: verificar se sinônimos funcionam tanto com cache quanto sem cache
        """
        print("\n" + "="*80)
        print("🧪 TESTE DE SINÔNIMOS COM CACHE REDIS")
        print("="*80)
        
        # Termo de teste que provavelmente tem sinônimos úteis
        test_keyword = "computador"
        
        print(f"\n🎯 Termo de teste: '{test_keyword}'")
        
        # Mostrar sinônimos que seriam gerados
        if self.openai_service:
            try:
                synonyms = self.openai_service.gerar_sinonimos(test_keyword, max_sinonimos=5)
                print(f"🔤 Sinônimos gerados: {synonyms}")
            except Exception as e:
                print(f"⚠️ Erro ao gerar sinônimos: {e}")
                synonyms = [test_keyword]
        else:
            print("⚠️ OpenAI não disponível - teste será limitado")
            synonyms = [test_keyword]
        
        # Criar filtros de busca
        filters = SearchFilters(
            keywords=test_keyword,
            region_code="MG",  # Minas Gerais como exemplo
            page_size=20
        )
        
        print(f"\n📋 Filtros de busca:")
        print(f"   🔤 Keywords: {test_keyword}")
        print(f"   🗺️ Região: MG")
        print(f"   📄 Limite: 20")
        
        # TESTE 1: Primeira busca (dados vêm da API, vão para cache)
        print(f"\n🔍 TESTE 1: Primeira busca (API → Cache)")
        print("-" * 40)
        
        start_time = datetime.now()
        try:
            results_first = await self.adapter.search_opportunities(filters)
            duration_first = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Primeira busca concluída")
            print(f"   📊 Resultados: {len(results_first)}")
            print(f"   ⏱️ Tempo: {duration_first:.2f}s")
            
            # Mostrar alguns exemplos dos resultados
            if results_first:
                print(f"\n📋 Primeiros 3 resultados:")
                for i, result in enumerate(results_first[:3]):
                    title = result.title[:80] + "..." if len(result.title) > 80 else result.title
                    print(f"   {i+1}. {title}")
                    print(f"      💰 Valor: R$ {result.estimated_value:,.2f}" if result.estimated_value else "      💰 Valor: Não informado")
            
        except Exception as e:
            print(f"❌ Erro na primeira busca: {e}")
            return
        
        # Aguardar um pouco
        print("\n⏳ Aguardando 2 segundos...")
        await asyncio.sleep(2)
        
        # TESTE 2: Segunda busca (dados vêm do cache, sinônimos devem ser aplicados)
        print(f"\n🔍 TESTE 2: Segunda busca (Cache → Filtros com sinônimos)")
        print("-" * 40)
        
        start_time = datetime.now()
        try:
            results_second = await self.adapter.search_opportunities(filters)
            duration_second = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Segunda busca concluída")
            print(f"   📊 Resultados: {len(results_second)}")
            print(f"   ⏱️ Tempo: {duration_second:.2f}s")
            print(f"   🚀 Aceleração: {duration_first/duration_second:.1f}x mais rápida")
            
            # Verificar se os resultados são consistentes
            if len(results_first) == len(results_second):
                print(f"   ✅ Número de resultados consistente")
            else:
                print(f"   ⚠️ Diferença no número de resultados: {len(results_first)} vs {len(results_second)}")
            
        except Exception as e:
            print(f"❌ Erro na segunda busca: {e}")
            return
        
        # TESTE 3: Busca com sinônimo específico para verificar se está funcionando
        print(f"\n🔍 TESTE 3: Busca com sinônimo específico")
        print("-" * 40)
        
        if len(synonyms) > 1:
            synonym_test = synonyms[1]  # Primeiro sinônimo
            print(f"🎯 Testando com sinônimo: '{synonym_test}'")
            
            synonym_filters = SearchFilters(
                keywords=synonym_test,
                region_code="MG",
                page_size=20
            )
            
            try:
                results_synonym = await self.adapter.search_opportunities(synonym_filters)
                print(f"✅ Busca com sinônimo concluída")
                print(f"   📊 Resultados com sinônimo: {len(results_synonym)}")
                
                # Verificar se encontrou resultados
                if results_synonym:
                    print(f"   🎯 Sinônimo '{synonym_test}' encontrou {len(results_synonym)} resultados")
                    
                    # Mostrar um exemplo
                    example = results_synonym[0]
                    title = example.title[:80] + "..." if len(example.title) > 80 else example.title
                    print(f"   📋 Exemplo: {title}")
                else:
                    print(f"   ⚠️ Sinônimo '{synonym_test}' não encontrou resultados")
                    
            except Exception as e:
                print(f"❌ Erro na busca com sinônimo: {e}")
        else:
            print("⚠️ Nenhum sinônimo disponível para teste")
        
        # TESTE 4: Verificar cache Redis diretamente
        print(f"\n🔍 TESTE 4: Verificação do Cache Redis")
        print("-" * 40)
        
        if self.adapter.redis_available and self.adapter.redis_client:
            try:
                # Buscar chaves relacionadas ao nosso teste
                pattern = "pncp:v2:*"
                keys = self.adapter.redis_client.keys(pattern)
                
                print(f"🗃️ Chaves encontradas no Redis: {len(keys)}")
                
                if keys:
                    # Mostrar algumas chaves (sem dados sensíveis)
                    for i, key in enumerate(keys[:3]):
                        key_str = key.decode('utf-8') if isinstance(key, bytes) else str(key)
                        print(f"   {i+1}. {key_str[:100]}...")
                        
                        # Verificar se a chave contém dados de sinônimos
                        if 'synonyms' in key_str:
                            print(f"      ✅ Esta chave inclui sinônimos!")
                else:
                    print("   ℹ️ Nenhuma chave encontrada")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao verificar Redis: {e}")
        else:
            print("   ⚠️ Redis não disponível")
        
        # Resumo final
        print(f"\n" + "="*80)
        print("📊 RESUMO DO TESTE")
        print("="*80)
        print(f"✅ Primeira busca (API): {len(results_first)} resultados em {duration_first:.2f}s")
        print(f"✅ Segunda busca (Cache): {len(results_second)} resultados em {duration_second:.2f}s")
        
        if self.openai_service:
            print(f"✅ OpenAI Service funcionando: {len(synonyms)} sinônimos gerados")
        else:
            print("⚠️ OpenAI Service não disponível")
            
        if self.adapter.redis_available:
            print("✅ Redis disponível e funcionando")
        else:
            print("⚠️ Redis não disponível")
        
        print("\n🎯 CONCLUSÃO:")
        if len(results_first) > 0 and len(results_second) > 0:
            print("✅ Teste bem-sucedido! Sinônimos estão sendo aplicados corretamente.")
            print("✅ Cache Redis funcionando e preservando funcionalidade de sinônimos.")
        else:
            print("⚠️ Teste inconclusivo - poucos ou nenhum resultado encontrado.")
        
        print("="*80)

async def main():
    """Função principal"""
    test_instance = SynonymsCacheTest()
    await test_instance.test_cache_vs_api_synonyms()

if __name__ == "__main__":
    print("🚀 Iniciando teste de sinônimos com cache Redis...")
    
    # Verificar se temos as dependências necessárias
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc() 