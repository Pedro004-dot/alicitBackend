#!/usr/bin/env python3
"""
Script de DEBUG para analisar por que o filtro de relevância está rejeitando todas as licitações.
"""

import os
import sys

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from repositories.licitacao_repository import LicitacaoPNCPRepository
import logging
import asyncio

# Configurar logging para DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_filtro_relevancia():
    """
    Debug específico do filtro de relevância.
    """
    print("🔧 DEBUG: Analisando filtro de relevância")
    print("=" * 60)
    
    repo = LicitacaoPNCPRepository()
    
    # Buscar dados reais da API
    filtros = {
        "estados": ["SP"],
        "modalidades": ["pregao_eletronico"],
        "palavras_busca": ["limpeza"]
    }
    
    # 1. Fazer a busca na API sem filtro local
    print("\n📡 PASSO 1: Buscar dados da API...")
    
    # Construir parâmetros
    params = repo._construir_parametros(filtros, ["limpeza"], 1, 5)
    print(f"📤 Parâmetros: {params}")
    
    # Fazer requisição direta
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", params=params) as response:
            if response.status == 200:
                data = await response.json()
                licitacoes_raw = data.get('data', [])
                print(f"✅ API retornou {len(licitacoes_raw)} licitações")
            else:
                print(f"❌ Erro na API: {response.status}")
                return
    
    # 2. Analisar cada licitação individualmente
    print(f"\n🔍 PASSO 2: Analisando {len(licitacoes_raw)} licitações...")
    
    for i, lic in enumerate(licitacoes_raw[:3]):  # Só as 3 primeiras para debug
        print(f"\n--- LICITAÇÃO {i+1} ---")
        numero_controle = lic.get('numeroControlePNCP', 'N/A')
        objeto_compra = lic.get('objetoCompra', '')
        
        print(f"🆔 ID: {numero_controle}")
        print(f"📝 Objeto original: '{objeto_compra}'")
        
        # Normalizar texto
        objeto_normalizado = repo._normalizar_texto(objeto_compra)
        print(f"📝 Objeto normalizado: '{objeto_normalizado}'")
        
        # Testar relevância com diferentes termos
        termos_teste = [
            ["limpeza"],
            ["limpeza", "higienização", "asseio"],
            ["sistema"],
            ["equipamento"]
        ]
        
        for termos in termos_teste:
            score = repo._calcular_relevancia_objeto(objeto_compra, termos)
            print(f"   🎯 Score para {termos}: {score:.3f}")
            
            # Testar diferentes thresholds
            for threshold in [0.1, 0.3, 0.5, 0.7]:
                aprovado = "✅" if score >= threshold else "❌"
                print(f"      {aprovado} Threshold {threshold:.1f}: {score:.3f}")
        
        print()
    
    # 3. Testar função de normalização
    print("\n🔧 PASSO 3: Testando normalização...")
    
    textos_teste = [
        "Serviços de limpeza predial e conservação",
        "Aquisição de equipamentos de informática", 
        "Sistema de monitoramento de segurança",
        "PRESTAÇÃO DE SERVIÇOS DE LIMPEZA E CONSERVAÇÃO",
        "Licitação para contratação de empresa"
    ]
    
    for texto in textos_teste:
        normalizado = repo._normalizar_texto(texto)
        print(f"📝 '{texto}' → '{normalizado}'")
    
    # 4. Testar cálculo de relevância manualmente
    print("\n🧮 PASSO 4: Teste manual de relevância...")
    
    casos_teste = [
        ("Serviços de limpeza predial", ["limpeza"], "Match exato esperado"),
        ("Prestação de serviços de conservação e limpeza", ["limpeza"], "Match presente"),
        ("Aquisição de equipamentos", ["limpeza"], "Sem match esperado"),
        ("Sistema de informática", ["sistema", "informatica"], "Match duplo"),
        ("Serviços gerais de manutenção", ["limpeza"], "Sem match"),
    ]
    
    for objeto, termos, expectativa in casos_teste:
        score = repo._calcular_relevancia_objeto(objeto, termos)
        print(f"📊 '{objeto}' + {termos}")
        print(f"   → Score: {score:.3f} ({expectativa})")
        print()

def debug_sync():
    """Versão síncrona do debug."""
    asyncio.run(debug_filtro_relevancia())

if __name__ == "__main__":
    debug_sync() 