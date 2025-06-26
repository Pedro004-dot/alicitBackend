#!/usr/bin/env python3

"""
Debug direto da função de relevância.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from repositories.licitacao_repository import LicitacaoPNCPRepository
import logging

# Habilitar logs de DEBUG
logging.basicConfig(level=logging.DEBUG)

def testar_relevancia_direta():
    """
    Teste direto da função de relevância.
    """
    print("🔧 DEBUG: Teste direto da função de relevância")
    print("=" * 60)
    
    repo = LicitacaoPNCPRepository()
    
    # Casos de teste
    casos_teste = [
        {
            "objeto": "SERVIÇOS DE LIMPEZA E CONSERVAÇÃO",
            "termos": ["limpeza"],
            "esperado": "> 0.5"
        },
        {
            "objeto": "Contratação de empresa especializada em desinsetização, desratização e dedetização",  
            "termos": ["limpeza"],
            "esperado": "< 0.5"
        },
        {
            "objeto": "AQUISIÇÃO DE ALIMENTAÇÃO ESCOLAR",
            "termos": ["alimentação"],
            "esperado": "> 0.5"
        },
        {
            "objeto": "SISTEMA DE GESTÃO INTEGRADA",
            "termos": ["sistema"],
            "esperado": "> 0.5"
        },
        {
            "objeto": "REF. A COMPRA DE COMPTADORES E NOTEBOOK PARA A PROMOÇÃO SOCIAL",
            "termos": ["sistema", "informatica"],
            "esperado": "< 0.3"
        }
    ]
    
    print("🧪 EXECUTANDO TESTES DE RELEVÂNCIA:")
    print("-" * 60)
    
    for i, caso in enumerate(casos_teste):
        print(f"\n🔍 TESTE {i+1}:")
        print(f"   📝 Objeto: {caso['objeto']}")
        print(f"   🎯 Termos: {caso['termos']}")
        print(f"   📊 Esperado: {caso['esperado']}")
        
        # Executar teste
        score = repo._calcular_relevancia_objeto(caso['objeto'], caso['termos'])
        print(f"   ✅ Resultado: {score:.3f}")
        
        # Verificar se está correto
        if caso['esperado'].startswith('>'):
            limite = float(caso['esperado'][2:])
            status = "✅ PASSOU" if score > limite else "❌ FALHOU"
        else:
            limite = float(caso['esperado'][2:])
            status = "✅ PASSOU" if score < limite else "❌ FALHOU"
        
        print(f"   🏁 Status: {status}")
    
    # Teste adicional: normalização
    print("\n🔧 TESTE DE NORMALIZAÇÃO:")
    print("-" * 30)
    
    textos_teste = [
        "SERVIÇOS DE LIMPEZA",
        "serviços de limpeza",
        "Serviços de Limpeza e Conservação",
        "alimentação escolar",
        "ALIMENTAÇÃO",
        "sistema",
        "SISTEMA DE GESTÃO"
    ]
    
    for texto in textos_teste:
        normalizado = repo._normalizar_texto(texto)
        print(f"   '{texto}' -> '{normalizado}'")

if __name__ == "__main__":
    testar_relevancia_direta() 