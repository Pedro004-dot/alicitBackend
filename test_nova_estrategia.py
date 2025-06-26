#!/usr/bin/env python3
"""
Script de teste para validar a nova estratégia de busca estilo Thiago.

NOVA ESTRATÉGIA:
- Busca ampla na API (sem parâmetro 'busca')
- Filtro rigoroso local com threshold de relevância
- Sinônimos aplicados apenas localmente
"""

import os
import sys

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.licitacao_service import LicitacaoService
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def testar_estrategia_thiago():
    """
    Testa a nova estratégia com termos simples como recomendado.
    """
    print("🚀 TESTE DA NOVA ESTRATÉGIA ESTILO THIAGO")
    print("=" * 60)
    
    service = LicitacaoService()
    
    # Teste 1: Termo simples (recomendado pelo Claude)
    print("\n🔍 TESTE 1: Termo simples - 'limpeza'")
    print("-" * 40)
    
    filtros_1 = {
        "palavra_chave": "limpeza",
        "usar_sinonimos": True,
        "estados": ["SP"],
        "modalidades": ["pregao_eletronico"],
        "threshold_relevancia": 0.6
    }
    
    try:
        resultado_1 = service.buscar_licitacoes_pncp(
            filtros_1, 
            ["limpeza"], 
            pagina=1, 
            itens_por_pagina=50  # ✅ LIMITE MÁXIMO
        )
        
        print(f"✅ Total encontrado: {len(resultado_1.get('data', []))}")
        
        # Verificar se sinônimos foram gerados
        estrategia_info = resultado_1.get('metadados', {}).get('estrategia_busca', {})
        print(f"✨ Sinônimos aplicados: {estrategia_info.get('sinonimos_locais', False)}")
        
        # Mostrar algumas licitações
        for i, lic in enumerate(resultado_1.get('data', [])[:3]):
            score = lic.get('_score_relevancia', 'N/A')
            print(f"  {i+1}. [{score:.2f}] {lic.get('objetoCompra', '')[:70]}...")
            
    except Exception as e:
        print(f"❌ Erro no teste 1: {e}")
    
    # Teste 2: Múltiplos estados
    print("\n🌍 TESTE 2: Múltiplos estados - 'sistema informatica'")
    print("-" * 50)
    
    filtros_2 = {
        "palavra_chave": "sistema informatica",
        "usar_sinonimos": True,
        "estados": ["SP", "RJ", "MG"],  # 📍 MÚLTIPLOS ESTADOS
        "modalidades": ["pregao_eletronico"],
        "threshold_relevancia": 0.5  # Threshold mais baixo para termo específico
    }
    
    try:
        resultado_2 = service.buscar_licitacoes_pncp(
            filtros_2, 
            ["sistema", "informatica"], 
            pagina=1, 
            itens_por_pagina=50
        )
        
        print(f"✅ Total encontrado: {len(resultado_2.get('data', []))}")
        
        # Verificar distribuição por estado
        estados_encontrados = {}
        for lic in resultado_2.get('data', []):
            uf = lic.get('uf', 'N/A')
            estados_encontrados[uf] = estados_encontrados.get(uf, 0) + 1
        
        print(f"📊 Por estado: {estados_encontrados}")
        
    except Exception as e:
        print(f"❌ Erro no teste 2: {e}")
    
    # Teste 3: Múltiplas cidades
    print("\n🏙️ TESTE 3: Múltiplas cidades - 'seguranca'")
    print("-" * 40)
    
    filtros_3 = {
        "palavra_chave": "seguranca",
        "usar_sinonimos": True,
        "estados": ["SP"],
        "cidades": ["SAO PAULO", "CAMPINAS", "SANTOS"],  # 🏙️ MÚLTIPLAS CIDADES
        "modalidades": ["pregao_eletronico"],
        "threshold_relevancia": 0.6
    }
    
    try:
        resultado_3 = service.buscar_licitacoes_pncp(
            filtros_3, 
            ["seguranca"], 
            pagina=1, 
            itens_por_pagina=50
        )
        
        print(f"✅ Total encontrado: {len(resultado_3.get('data', []))}")
        
        # Verificar se busca inteligente foi ativada
        busca_inteligente = resultado_3.get('metadados', {}).get('busca_inteligente', {})
        if busca_inteligente.get('ativa'):
            print(f"🧠 Busca inteligente ativada:")
            print(f"   📄 Páginas buscadas: {busca_inteligente.get('paginas_buscadas', 0)}")
            print(f"   🔍 Total buscas API: {busca_inteligente.get('total_buscas_api', 0)}")
        
    except Exception as e:
        print(f"❌ Erro no teste 3: {e}")
    
    # Teste 4: Teste de rota POST (Controller)
    print("\n📋 TESTE 4: Rota POST - Compatibilidade")
    print("-" * 40)
    
    filtros_4 = {
        "palavra_chave": "alimentacao",
        "usar_sinonimos": True,
        "estados": ["SP", "RJ"],
        "modalidades": ["pregao_eletronico"]
    }
    
    try:
        # Simular o que o controller POST faz
        resultado_4 = service.buscar_licitacoes(
            filtros_4, 
            pagina=1, 
            itens_por_pagina=50
        )
        
        print(f"✅ Total (POST): {resultado_4.get('total', 0)}")
        print(f"📄 Páginas: {resultado_4.get('pagina_atual', 0)}/{resultado_4.get('total_paginas', 0)}")
        print(f"✨ Palavras utilizadas: {resultado_4.get('palavras_utilizadas', [])}")
        
        # Verificar se estratégia foi aplicada
        estrategia = resultado_4.get('estrategia_aplicada', {})
        if estrategia:
            print(f"🎯 Estratégia aplicada: {estrategia.get('tipo', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Erro no teste 4: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 TESTES CONCLUÍDOS!")
    print("✅ Rotas para testar no Postman:")
    print("   GET:  /api/licitacoes/buscar?palavras_busca=limpeza&estados=SP&modalidades=pregao_eletronico")
    print("   POST: /api/licitacoes/buscar (JSON body)")
    print("=" * 60)

if __name__ == "__main__":
    testar_estrategia_thiago() 