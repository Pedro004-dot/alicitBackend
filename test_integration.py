#!/usr/bin/env python3

"""
🔗 Teste de Integração Frontend-Backend

Testa se as rotas usadas pelo LicitacaoModal.tsx estão funcionando
corretamente com o novo PNCPAdapter.
"""

import os
import sys
import logging
import json

# Adicionar o diretório src ao path para poder importar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.bid_service import BidService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_modal_integration():
    """🧪 Testa as funcionalidades usadas pelo Modal do Frontend (versão síncrona)"""
    
    print("🔗 TESTE DE INTEGRAÇÃO FRONTEND-BACKEND")
    print("=" * 50)
    
    # Inicializar o serviço
    bid_service = BidService()
    
    # PNCP ID de exemplo (baseado no histórico)
    test_pncp_id = "04892707000100-1-000246/2024"
    print(f"🧪 Testando com PNCP ID: {test_pncp_id}")
    
    print("\n🔍 1. TESTANDO get_bid_by_pncp_id")
    print("-" * 40)
    try:
        # Test get_bid_by_pncp_id function used by frontend modal
        bid_details = bid_service.get_bid_by_pncp_id(test_pncp_id)
        if bid_details:
            print(f"✅ Detalhes encontrados")
            print(f"🆔 CNPJ: {bid_details.get('orgao_cnpj', 'N/A')}")
            print(f"📝 Objeto: {bid_details.get('objeto_compra', 'N/A')[:100]}...")
            print(f"📅 Data Abertura: {bid_details.get('data_abertura_proposta', 'N/A')}")
            print(f"💰 Valor: {bid_details.get('valor_total_estimado', 'N/A')}")
        else:
            print("❌ Nenhum detalhe encontrado")
    except Exception as e:
        print(f"❌ Erro ao buscar detalhes: {e}")
    
    print("\n🔍 2. TESTANDO get_bid_items (NOVO FOCO)")
    print("-" * 40)
    try:
        # Test get_bid_items function used by frontend modal
        items_result = bid_service.get_bid_items(test_pncp_id)
        print(f"✅ Resultado da busca de itens:")
        print(f"   📊 Success: {items_result.get('success', False)}")
        print(f"   📝 Message: {items_result.get('message', 'N/A')}")
        
        if items_result.get('success') and items_result.get('data'):
            itens = items_result['data'].get('itens', [])
            print(f"   🔢 Total de itens: {len(itens)}")
            
            # 🔍 ANÁLISE DETALHADA DOS PRIMEIROS ITENS
            if itens:
                print(f"\n🔍 3. ANÁLISE DOS ITENS DA API v1")
                print("-" * 40)
                
                for i, item in enumerate(itens[:3]):  # Apenas os primeiros 3
                    print(f"\n📦 ITEM {i+1}:")
                    print(f"   📋 Estrutura completa: {json.dumps(item, indent=2, ensure_ascii=False)[:500]}...")
                    
                    # 🔧 IDENTIFICAR CAMPO numero_item
                    possibles_numero_item = ['numeroItem', 'numero_item', 'numero', 'item', 'sequencial', 'id']
                    numero_item_encontrado = None
                    
                    for field in possibles_numero_item:
                        if field in item:
                            numero_item_encontrado = field
                            print(f"   🎯 CAMPO numero_item ENCONTRADO: '{field}' = {item[field]}")
                            break
                    
                    if not numero_item_encontrado:
                        print(f"   ❌ CAMPO numero_item NÃO ENCONTRADO")
                        print(f"   📋 Campos disponíveis: {list(item.keys())}")
                    
                    # Outros campos importantes
                    print(f"   📝 Descrição: {item.get('descricao', item.get('descricaoItem', 'N/A'))[:100]}...")
                    print(f"   🔢 Quantidade: {item.get('quantidade', 'N/A')}")
                    print(f"   💰 Valor unitário: {item.get('valorUnitarioEstimado', 'N/A')}")
            
            # 🔍 ANÁLISE DOS PROBLEMAS DE SALVAMENTO
            print(f"\n🔍 4. DIAGNÓSTICO DO PROBLEMA numero_item NULL")
            print("-" * 40)
            if itens:
                item_sample = itens[0]
                # Verificar qual campo seria mapeado para numero_item
                mapped_numero_item = item_sample.get('numero_item')
                if mapped_numero_item is None:
                    print("❌ PROBLEMA IDENTIFICADO: campo 'numero_item' é NULL")
                    print("🔧 SOLUÇÃO: Verificar mapeamento no BidService._fetch_items_via_adapter")
                    
                    # Tentar identificar o campo correto
                    if 'numeroItem' in item_sample:
                        print(f"✅ SUGESTÃO: Usar 'numeroItem' = {item_sample['numeroItem']}")
                    elif any(k for k in item_sample.keys() if 'numero' in k.lower()):
                        numero_fields = [k for k in item_sample.keys() if 'numero' in k.lower()]
                        print(f"✅ CAMPOS CANDIDATOS: {numero_fields}")
                        
        else:
            print("❌ Nenhum item encontrado")
    except Exception as e:
        print(f"❌ Erro ao buscar itens: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🔍 5. TESTANDO DIRETAMENTE O PNCPAdapter")
    print("-" * 40)
    try:
        if bid_service.pncp_adapter:
            adapter_items = bid_service.pncp_adapter.get_opportunity_items(test_pncp_id)
            print(f"✅ PNCPAdapter retornou {len(adapter_items)} itens")
            
            if adapter_items:
                primeiro_item = adapter_items[0]
                print(f"📦 Primeiro item (estrutura da API v1):")
                print(f"   📋 Campos: {list(primeiro_item.keys())}")
                
                # Identificar o campo para numero_item
                for campo in ['numeroItem', 'numero', 'item', 'sequencial']:
                    if campo in primeiro_item:
                        print(f"   🎯 {campo}: {primeiro_item[campo]}")
        else:
            print("❌ PNCPAdapter não disponível")
    except Exception as e:
        print(f"❌ Erro ao testar PNCPAdapter: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 RESUMO DOS TESTES CONCLUÍDOS")
    print("=" * 50)

if __name__ == "__main__":
    test_modal_integration() 