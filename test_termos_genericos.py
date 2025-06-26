#!/usr/bin/env python3

"""
Teste com termos mais genéricos para encontrar licitações reais.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.licitacao_service import LicitacaoService
import logging

logging.basicConfig(level=logging.INFO)

def testar_termos_genericos():
    """
    Testa com termos mais genéricos que podem estar nas licitações atuais.
    """
    print("🔍 TESTE COM TERMOS GENÉRICOS")
    print("=" * 50)
    
    service = LicitacaoService()
    
    # Termos baseados nos objetos reais que vimos
    termos_teste = [
        {
            "termo": "servico",
            "threshold": 0.3,
            "descricao": "Termo genérico muito comum"
        },
        {
            "termo": "aquisicao",
            "threshold": 0.3, 
            "descricao": "Aquisição - muito comum"
        },
        {
            "termo": "material",
            "threshold": 0.3,
            "descricao": "Material - genérico"
        },
        {
            "termo": "medicamento",
            "threshold": 0.5,
            "descricao": "Medicamento - específico"
        },
        {
            "termo": "uniforme",
            "threshold": 0.5,
            "descricao": "Uniforme - específico"
        }
    ]
    
    for i, teste in enumerate(termos_teste):
        print(f"\n🧪 TESTE {i+1}: '{teste['termo']}'")
        print(f"   📝 Descrição: {teste['descricao']}")
        print(f"   🎯 Threshold: {teste['threshold']:.1%}")
        print("-" * 40)
        
        filtros = {
            "palavra_chave": teste['termo'],
            "usar_sinonimos": False,  # Sem sinônimos para teste mais direto
            "estados": ["SP"],
            "modalidades": ["pregao_eletronico"],
            "threshold_relevancia": teste['threshold']
        }
        
        try:
            resultado = service.buscar_licitacoes_pncp(
                filtros,
                [teste['termo']],
                pagina=1,
                itens_por_pagina=50
            )
            
            encontradas = len(resultado.get('data', []))
            print(f"   ✅ Encontradas: {encontradas} licitações")
            
            # Mostrar algumas amostras
            if encontradas > 0:
                print("   📋 AMOSTRAS:")
                for j, lic in enumerate(resultado.get('data', [])[:3]):
                    score = lic.get('_score_relevancia', 0)
                    objeto = lic.get('objetoCompra', '')[:50]
                    print(f"      {j+1}. [{score:.2f}] {objeto}...")
            else:
                print("   ❌ Nenhuma licitação encontrada")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    print("\n" + "=" * 50)
    print("📊 CONCLUSÃO:")
    print("Se encontrarmos resultados, a estratégia está funcionando!")
    print("Se não, o problema pode ser:")
    print("1. Período de datas muito restrito")
    print("2. Modalidade/estado muito específico") 
    print("3. Licitações reais não têm esses termos no momento")

if __name__ == "__main__":
    testar_termos_genericos() 