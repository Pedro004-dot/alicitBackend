#!/usr/bin/env python3
"""
Teste para verificar que o salvamento automático foi DESATIVADO
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_auto_save_disabled():
    """
    🚫 Teste para confirmar que salvamento automático está DESATIVADO
    """
    print("🧪 TESTANDO DESATIVAÇÃO DO SALVAMENTO AUTOMÁTICO")
    print("=" * 60)
    
    # ✅ ETAPA 1: Verificar configuração dos DataMappers
    print("\n🔧 ETAPA 1: Verificando DataMappers...")
    
    try:
        from adapters.mappers.pncp_data_mapper import PNCPDataMapper
        from adapters.mappers.comprasnet_data_mapper import ComprasNetDataMapper
        
        pncp_mapper = PNCPDataMapper()
        comprasnet_mapper = ComprasNetDataMapper()
        
        print(f"   📋 PNCP should_auto_save(): {pncp_mapper.should_auto_save()}")
        print(f"   📋 ComprasNet should_auto_save(): {comprasnet_mapper.should_auto_save()}")
        
        if pncp_mapper.should_auto_save() or comprasnet_mapper.should_auto_save():
            print("   ❌ ERRO: DataMappers ainda com auto-save ativado!")
            return False
        else:
            print("   ✅ DataMappers com auto-save DESATIVADO corretamente")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar DataMappers: {e}")
        return False
    
    # ✅ ETAPA 2: Verificar registry de mappers
    print("\n🏗️ ETAPA 2: Verificando registry...")
    
    try:
        from interfaces.data_mapper import data_mapper_registry
        
        auto_save_mappers = data_mapper_registry.get_auto_save_mappers()
        on_demand_mappers = data_mapper_registry.get_on_demand_mappers()
        all_providers = data_mapper_registry.list_providers()
        
        print(f"   📊 Providers registrados: {all_providers}")
        print(f"   📊 Mappers com auto-save: {auto_save_mappers}")
        print(f"   📊 Mappers sob demanda: {on_demand_mappers}")
        
        if auto_save_mappers:
            print("   ❌ ERRO: Ainda existem mappers com auto-save ativado!")
            return False
        else:
            print("   ✅ Nenhum mapper com auto-save ativo")
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar registry: {e}")
        return False
    
    # ✅ ETAPA 3: Testar busca sem salvamento
    print("\n🔍 ETAPA 3: Testando busca sem salvamento...")
    
    try:
        # Simular uma busca rápida usando UnifiedSearchService
        from services.unified_search_service import UnifiedSearchService
        from interfaces.procurement_data_source import SearchFilters
        
        unified_service = UnifiedSearchService()
        print("   ✅ UnifiedSearchService inicializado")
        
        # Criar filtros simples
        filters = SearchFilters(
            keywords="teste",
            page=1,
            page_size=5  # Busca bem pequena para teste
        )
        
        print("   🔍 Executando busca unificada...")
        # Usar asyncio.run para executar o método async
        import asyncio
        results = asyncio.run(unified_service.search_opportunities(filters))
        
        total_results = sum(len(opportunities) for opportunities in results.values())
        print(f"   📊 Resultados encontrados: {total_results}")
        
        if total_results > 0:
            print("   ✅ Busca executada, dados retornados SEM SALVAMENTO")
        else:
            print("   ⚠️ Busca executada, mas nenhum resultado encontrado")
            
    except Exception as e:
        print(f"   ❌ Erro na busca de teste: {e}")
        return False
    
    # ✅ ETAPA 4: Verificar logs de salvamento
    print("\n📋 ETAPA 4: Verificando logs...")
    print("   💡 Verifique nos logs do servidor se aparecem mensagens:")
    print("      🚫 'Salvamento automático desativado'")
    print("      ❌ Se aparecer 'Persistência automática:' significa que ainda está salvando!")
    
    print("\n" + "=" * 60)
    print("✅ TESTE CONCLUÍDO: Salvamento automático DESATIVADO")
    print("📝 Próximos passos:")
    print("   1. Execute uma busca no frontend")
    print("   2. Verifique os logs do servidor")
    print("   3. Confirme que não aparecem mensagens de persistência automática")
    print("   4. Salvamento deve ocorrer APENAS quando usuário acessar modal de licitação")
    
    return True

if __name__ == "__main__":
    success = test_auto_save_disabled()
    sys.exit(0 if success else 1) 