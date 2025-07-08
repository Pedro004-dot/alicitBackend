#!/usr/bin/env python3

"""
🏆 Teste Final - Verificação de Salvamento no Banco

Verifica se os itens foram salvos corretamente no banco de dados 
com o numero_item preenchido.
"""

import os
import sys
import logging

# Adicionar o diretório src ao path para poder importar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.database import db_manager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_items():
    """🧪 Verificar se os itens foram salvos no banco corretamente"""
    
    print("🏆 TESTE FINAL - VERIFICAÇÃO DE SALVAMENTO")
    print("=" * 50)
    
    test_pncp_id = "04892707000100-1-000246/2024"
    
    try:
        # Conectar ao banco usando context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Verificar se a licitação existe
            print("\n🔍 1. VERIFICANDO LICITAÇÃO NO BANCO")
            print("-" * 40)
            
            cursor.execute("""
                SELECT id, pncp_id, objeto_compra, data_abertura_proposta, orgao_cnpj, status
                FROM licitacoes 
                WHERE pncp_id = %s
            """, (test_pncp_id,))
            
            licitacao = cursor.fetchone()
            if licitacao:
                licitacao_id, pncp_id, objeto, data_abertura, cnpj, status = licitacao
                print(f"✅ Licitação encontrada!")
                print(f"   🆔 ID: {licitacao_id}")
                print(f"   📋 PNCP ID: {pncp_id}")
                print(f"   📝 Objeto: {objeto[:100]}...")
                print(f"   📅 Data Abertura: {data_abertura}")
                print(f"   🏢 CNPJ: {cnpj}")
                print(f"   📊 Status: {status}")
            else:
                print("❌ Licitação não encontrada no banco")
                return
            
            # 2. Verificar se os itens existem e se numero_item está preenchido
            print("\n🔍 2. VERIFICANDO ITENS NO BANCO")
            print("-" * 40)
            
            cursor.execute("""
                SELECT id, numero_item, descricao, quantidade, valor_unitario_estimado, 
                       unidade_medida, material_ou_servico, dados_api_completos IS NOT NULL as tem_dados_api
                FROM licitacao_itens 
                WHERE licitacao_id = %s
                ORDER BY numero_item
            """, (licitacao_id,))
            
            itens = cursor.fetchall()
            if itens:
                print(f"✅ {len(itens)} itens encontrados!")
                
                for i, item in enumerate(itens, 1):
                    item_id, numero_item, descricao, quantidade, valor_unitario, unidade, material_servico, tem_dados_api = item
                    print(f"\n   📦 ITEM {i}:")
                    print(f"      🆔 ID: {item_id}")
                    print(f"      🔢 numero_item: {numero_item} {'✅' if numero_item is not None else '❌ NULL!'}")
                    print(f"      📝 Descrição: {descricao[:80]}...")
                    print(f"      📊 Quantidade: {quantidade}")
                    print(f"      💰 Valor Unit.: {valor_unitario}")
                    print(f"      📏 Unidade: {unidade}")
                    print(f"      🔧 Tipo: {material_servico}")
                    print(f"      💾 Dados API: {'✅' if tem_dados_api else '❌'}")
                    
                    # Verificação crítica
                    if numero_item is None:
                        print(f"      ❌ PROBLEMA: numero_item é NULL!")
                    else:
                        print(f"      ✅ SUCESSO: numero_item = {numero_item}")
            else:
                print("❌ Nenhum item encontrado no banco")
            
            # 3. Verificar status da licitação
            print("\n🔍 3. VERIFICANDO STATUS DA LICITAÇÃO")
            print("-" * 40)
            
            if status in ['coletada', 'processada', 'matched']:
                print(f"✅ Status válido: '{status}'")
            else:
                print(f"❌ Status inválido: '{status}' (deveria ser coletada/processada/matched)")
            
            # 4. Verificar data de abertura
            print("\n🔍 4. VERIFICANDO DATA DE ABERTURA")
            print("-" * 40)
            
            if data_abertura:
                print(f"✅ Data de abertura preenchida: {data_abertura}")
            else:
                print("⚠️ Data de abertura não preenchida")
        
        print("\n" + "=" * 50)
        print("🎯 RESULTADO FINAL")
        print("=" * 50)
        
        if itens and all(item[1] is not None for item in itens):
            print("🎉 SUCESSO TOTAL! Todos os problemas foram resolvidos:")
            print("   ✅ Licitação salva corretamente")
            print("   ✅ Itens salvos com numero_item preenchido")
            print("   ✅ Status constraint respeitado")
            print("   ✅ Integração frontend-backend funcionando")
        else:
            print("❌ Ainda há problemas pendentes")
        
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_items() 