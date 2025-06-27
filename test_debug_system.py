#!/usr/bin/env python3
"""
Script de Teste para Sistema Enhanced de Debug de Licitações
Testa todas as funcionalidades implementadas com exemplos práticos
"""
import requests
import json
import sys
import time
from typing import Dict, Any

# Configuração da API
BASE_URL = "http://localhost:5001/api"
DEBUG_BASE = f"{BASE_URL}/debug"

def print_header(title: str):
    """Imprime cabeçalho formatado"""
    print("\n" + "="*80)
    print(f"🧪 {title}")
    print("="*80)

def print_result(test_name: str, response: Dict[str, Any], success: bool = True):
    """Imprime resultado formatado"""
    status = "✅ SUCESSO" if success else "❌ ERRO"
    print(f"\n{status} - {test_name}")
    print("-" * 50)
    print(json.dumps(response, indent=2, ensure_ascii=False))

def test_health_check():
    """Teste 1: Health Check do Sistema"""
    print_header("TESTE 1: Health Check do Sistema de Debug")
    
    try:
        response = requests.get(f"{DEBUG_BASE}/health", timeout=10)
        response.raise_for_status()
        
        result = response.json()
        print_result("Health Check", result)
        
        if result.get('success'):
            print("🎯 Sistema de debug está funcionando!")
            return True
        else:
            print("⚠️ Sistema de debug com problemas")
            return False
            
    except Exception as e:
        print_result("Health Check", {"error": str(e)}, False)
        return False

def test_consistency_report():
    """Teste 2: Relatório de Consistência"""
    print_header("TESTE 2: Relatório de Consistência Atual")
    
    try:
        response = requests.get(f"{DEBUG_BASE}/consistency-report", timeout=15)
        response.raise_for_status()
        
        result = response.json()
        print_result("Relatório de Consistência", result)
        return True
        
    except Exception as e:
        print_result("Relatório de Consistência", {"error": str(e)}, False)
        return False

def test_individual_licitacao():
    """Teste 3: Análise Individual de Licitação"""
    print_header("TESTE 3: Análise Individual de Licitação")
    
    # Vamos usar um ID que provavelmente existe baseado nos logs
    pncp_id = "08584229000122-1-000013/2025"
    
    try:
        response = requests.get(
            f"{DEBUG_BASE}/test-consistency",
            params={"pncp_id": pncp_id},
            timeout=30
        )
        
        result = response.json()
        print_result(f"Teste Individual - {pncp_id}", result, response.status_code == 200)
        
        if response.status_code == 200 and result.get('success'):
            print("🎯 Licitação analisada com sucesso!")
        elif response.status_code == 404:
            print("⚠️ Licitação não encontrada - vamos tentar outro ID")
        
        return response.status_code == 200
        
    except Exception as e:
        print_result(f"Teste Individual - {pncp_id}", {"error": str(e)}, False)
        return False

def test_api_response_debug():
    """Teste 4: Debug Detalhado de Resposta da API"""
    print_header("TESTE 4: Debug Detalhado de Resposta da API")
    
    pncp_id = "08584229000122-1-000013/2025"
    
    try:
        response = requests.get(
            f"{DEBUG_BASE}/api-responses",
            params={"pncp_id": pncp_id},
            timeout=30
        )
        
        result = response.json()
        print_result(f"Debug API - {pncp_id}", result, response.status_code == 200)
        return response.status_code == 200
        
    except Exception as e:
        print_result(f"Debug API - {pncp_id}", {"error": str(e)}, False)
        return False

def test_licitacao_enrichment():
    """Teste 5: Enriquecimento de Licitação"""
    print_header("TESTE 5: Enriquecimento de Licitação com Dados Detalhados")
    
    # Dados de exemplo de uma licitação (dados básicos de busca)
    licitacao_exemplo = {
        "numeroControlePNCP": "08584229000122-1-000013/2025",
        "objetoCompra": "Contratação de serviços de software",
        "valorTotalEstimado": 50000.00,
        "dataPublicacaoPncp": "2025-01-15T10:00:00Z",
        "modalidadeNome": "Pregão Eletrônico"
    }
    
    try:
        response = requests.post(
            f"{DEBUG_BASE}/enrich-licitacao",
            json={"licitacao": licitacao_exemplo},
            timeout=30
        )
        
        result = response.json()
        print_result("Enriquecimento de Licitação", result, response.status_code == 200)
        return response.status_code == 200
        
    except Exception as e:
        print_result("Enriquecimento de Licitação", {"error": str(e)}, False)
        return False

def test_batch_analysis():
    """Teste 6: Análise em Lote"""
    print_header("TESTE 6: Análise de Consistência em Lote")
    
    # Lista de IDs para testar (alguns podem não existir)
    pncp_ids = [
        "08584229000122-1-000013/2025",
        "04215147000150-1-000210/2025",
        "28305936000140-1-000129/2025"
    ]
    
    try:
        response = requests.post(
            f"{DEBUG_BASE}/batch-consistency",
            json={"pncp_ids": pncp_ids},
            timeout=60
        )
        
        result = response.json()
        print_result("Análise em Lote", result, response.status_code == 200)
        return response.status_code == 200
        
    except Exception as e:
        print_result("Análise em Lote", {"error": str(e)}, False)
        return False

def test_data_comparison():
    """Teste 7: Comparação de Dados"""
    print_header("TESTE 7: Comparação entre Dados de Busca vs Detalhes")
    
    # Dados simulados para comparação
    dados_comparacao = {
        "search_data": {
            "numeroControlePNCP": "08584229000122-1-000013/2025",
            "objetoCompra": "Contratação de software básico",
            "valorTotalEstimado": 50000.00,
            "modalidadeNome": "Pregão Eletrônico"
        },
        "detail_data": {
            "numeroControlePNCP": "08584229000122-1-000013/2025",
            "objetoCompra": "Contratação de software avançado com suporte técnico",
            "valorTotalEstimado": 55000.00,
            "modalidadeNome": "Pregão Eletrônico"
        }
    }
    
    try:
        response = requests.post(
            f"{DEBUG_BASE}/compare-data",
            json=dados_comparacao,
            timeout=30
        )
        
        result = response.json()
        print_result("Comparação de Dados", result, response.status_code == 200)
        return response.status_code == 200
        
    except Exception as e:
        print_result("Comparação de Dados", {"error": str(e)}, False)
        return False

def main():
    """Executa todos os testes do sistema de debug"""
    print_header("INICIANDO TESTES DO SISTEMA ENHANCED DE DEBUG")
    print("🎯 Testando todas as funcionalidades implementadas...")
    print(f"🔗 Base URL: {DEBUG_BASE}")
    
    # Lista de testes
    tests = [
        ("Health Check", test_health_check),
        ("Relatório de Consistência", test_consistency_report),
        ("Análise Individual", test_individual_licitacao),
        ("Debug API", test_api_response_debug),
        ("Enriquecimento", test_licitacao_enrichment),
        ("Análise em Lote", test_batch_analysis),
        ("Comparação de Dados", test_data_comparison)
    ]
    
    results = {}
    
    # Executar testes
    for test_name, test_func in tests:
        print(f"\n⏳ Executando: {test_name}...")
        start_time = time.time()
        
        try:
            success = test_func()
            results[test_name] = success
            elapsed = time.time() - start_time
            status = "✅" if success else "❌"
            print(f"{status} {test_name} concluído em {elapsed:.2f}s")
        except Exception as e:
            results[test_name] = False
            print(f"❌ {test_name} falhou: {str(e)}")
    
    # Relatório final
    print_header("RELATÓRIO FINAL DOS TESTES")
    total_tests = len(results)
    successful_tests = sum(results.values())
    
    print(f"📊 Total de testes: {total_tests}")
    print(f"✅ Sucessos: {successful_tests}")
    print(f"❌ Falhas: {total_tests - successful_tests}")
    print(f"📈 Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
    
    print("\n📋 Detalhes por teste:")
    for test_name, success in results.items():
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"  {status} - {test_name}")
    
    if successful_tests == total_tests:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema enhanced funcionando perfeitamente!")
    else:
        print(f"\n⚠️ {total_tests - successful_tests} teste(s) falharam. Verifique os logs acima.")
    
    # Salvar relatório
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "success_rate": (successful_tests/total_tests)*100,
        "test_results": results
    }
    
    with open("test_debug_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Relatório salvo em: test_debug_report.json")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Erro inesperado: {str(e)}")
        sys.exit(1) 