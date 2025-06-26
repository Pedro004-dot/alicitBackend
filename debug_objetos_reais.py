#!/usr/bin/env python3

"""
Debug dos objetos reais das licitações para entender por que estão sendo rejeitadas.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from repositories.licitacao_repository import LicitacaoPNCPRepository
import asyncio

async def debug_objetos_reais():
    """
    Debug dos objetos reais para entender a rejeição.
    """
    print("🔍 DEBUG: Analisando objetos reais das licitações")
    print("=" * 60)
    
    repo = LicitacaoPNCPRepository()
    
    # Buscar dados da API sem filtro local
    filtros = {
        "estados": ["SP"],
        "modalidades": ["pregao_eletronico"]
    }
    
    params = repo._construir_parametros(filtros, [], 1, 10)
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", params=params) as response:
            if response.status == 200:
                data = await response.json()
                licitacoes = data.get('data', [])
                
                print(f"✅ API retornou {len(licitacoes)} licitações")
                print("\n📋 OBJETOS DAS LICITAÇÕES:")
                print("-" * 60)
                
                for i, lic in enumerate(licitacoes[:10]):
                    objeto = lic.get('objetoCompra', 'N/A')
                    numero = lic.get('numeroControlePNCP', 'N/A')
                    
                    print(f"\n{i+1}. [{numero}]")
                    print(f"   📝 Objeto: {objeto}")
                    
                    # Testar relevância para "limpeza"
                    score_limpeza = repo._calcular_relevancia_objeto(objeto, ['limpeza'])
                    print(f"   🧹 Score 'limpeza': {score_limpeza:.3f} {'✅' if score_limpeza >= 0.6 else '❌'}")
                    
                    # Testar relevância para "alimentação"
                    score_alimentacao = repo._calcular_relevancia_objeto(objeto, ['alimentação'])
                    print(f"   🍽️ Score 'alimentação': {score_alimentacao:.3f} {'✅' if score_alimentacao >= 0.6 else '❌'}")
                    
                    # Testar relevância para "sistema"
                    score_sistema = repo._calcular_relevancia_objeto(objeto, ['sistema'])
                    print(f"   💻 Score 'sistema': {score_sistema:.3f} {'✅' if score_sistema >= 0.6 else '❌'}")
                
                print("\n" + "=" * 60)
                print("📊 ANÁLISE:")
                print("Se todos os scores estão baixos, o problema pode ser:")
                print("1. Threshold muito alto (60%)")
                print("2. Normalização de texto muito rigorosa")
                print("3. Lógica de cálculo de relevância")
                print("4. Objetos realmente não contêm os termos buscados")
                
            else:
                print(f"❌ Erro na API: {response.status}")

if __name__ == "__main__":
    asyncio.run(debug_objetos_reais()) 