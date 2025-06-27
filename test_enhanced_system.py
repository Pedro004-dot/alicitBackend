#!/usr/bin/env python3
"""
Script de Teste do Sistema Enhanced de Logs e Debugging
Testa todas as funcionalidades do novo sistema de análise de dados
"""
import requests
import json
import time
from typing import Dict, Any, List

class EnhancedSystemTester:
    """
    Testador para o sistema enhanced de debugging e análise de dados
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Registra resultado de um teste"""
        result = {
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': time.time()
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
    
    def test_debug_health(self) -> bool:
        """Testa health check do sistema de debug"""
        try:
            response = self.session.get(f"{self.base_url}/api/debug/health")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Debug Health Check", True, f"Sistema funcionando com {len(data.get('available_endpoints', []))} endpoints")
                    return True
                else:
                    self.log_test("Debug Health Check", False, "Sistema reportou erro")
                    return False
            else:
                self.log_test("Debug Health Check", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Debug Health Check", False, f"Erro: {str(e)}")
            return False
    
    def test_consistency_report(self) -> bool:
        """Testa geração de relatório de consistência"""
        try:
            response = self.session.get(f"{self.base_url}/api/debug/consistency-report")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    report = data.get('report', {})
                    stats = report.get('statistics', {})
                    self.log_test("Consistency Report", True, f"Relatório gerado com {len(stats)} estatísticas")
                    return True
                else:
                    self.log_test("Consistency Report", False, "Falha na geração do relatório")
                    return False
            else:
                self.log_test("Consistency Report", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Consistency Report", False, f"Erro: {str(e)}")
            return False
    
    def test_licitacao_consistency(self, pncp_id: str = "08584229000122-1-000013/2025") -> bool:
        """Testa análise de consistência de uma licitação específica"""
        try:
            url = f"{self.base_url}/api/debug/test-consistency"
            params = {'pncp_id': pncp_id}
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test(f"Licitação Consistency ({pncp_id})", True, "Análise concluída com sucesso")
                    return True
                else:
                    self.log_test(f"Licitação Consistency ({pncp_id})", False, data.get('error', 'Erro desconhecido'))
                    return False
            elif response.status_code == 404:
                self.log_test(f"Licitação Consistency ({pncp_id})", False, "Licitação não encontrada (esperado)")
                return True  # 404 é esperado se a licitação não existir
            else:
                self.log_test(f"Licitação Consistency ({pncp_id})", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"Licitação Consistency ({pncp_id})", False, f"Erro: {str(e)}")
            return False
    
    def test_api_response_debug(self, pncp_id: str = "08584229000122-1-000013/2025") -> bool:
        """Testa debug detalhado das respostas da API"""
        try:
            url = f"{self.base_url}/api/debug/api-responses"
            params = {'pncp_id': pncp_id}
            
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test(f"API Response Debug ({pncp_id})", True, "Debug de API concluído")
                    return True
                else:
                    self.log_test(f"API Response Debug ({pncp_id})", False, data.get('error', 'Erro desconhecido'))
                    return False
            else:
                self.log_test(f"API Response Debug ({pncp_id})", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test(f"API Response Debug ({pncp_id})", False, f"Erro: {str(e)}")
            return False
    
    def test_licitacao_enrichment(self) -> bool:
        """Testa enriquecimento de licitação com dados detalhados"""
        try:
            # Dados de exemplo de uma licitação da busca
            licitacao_exemplo = {
                "numeroControlePNCP": "08584229000122-1-000013/2025",
                "objetoCompra": "Serviços de limpeza predial",
                "valorTotalEstimado": 50000.00,
                "modalidadeNome": "Pregão Eletrônico",
                "orgaoEntidade": {
                    "cnpj": "08584229000122",
                    "razaoSocial": "Exemplo de Órgão"
                }
            }
            
            url = f"{self.base_url}/api/debug/enrich-licitacao"
            payload = {"licitacao": licitacao_exemplo}
            
            response = self.session.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    enhancement_summary = data.get('enhancement_summary', {})
                    new_fields = enhancement_summary.get('new_fields_added', 0)
                    self.log_test("Licitação Enrichment", True, f"{new_fields} novos campos adicionados")
                    return True
                else:
                    self.log_test("Licitação Enrichment", False, data.get('error', 'Erro desconhecido'))
                    return False
            else:
                self.log_test("Licitação Enrichment", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Licitação Enrichment", False, f"Erro: {str(e)}")
            return False
    
    def test_batch_consistency(self) -> bool:
        """Testa análise de consistência em lote"""
        try:
            # Lista de exemplo de PNCP IDs
            pncp_ids = [
                "08584229000122-1-000013/2025",
                "11222333000144-1-000001/2025",
                "99888777000166-1-000005/2025"
            ]
            
            url = f"{self.base_url}/api/debug/batch-consistency"
            payload = {"pncp_ids": pncp_ids}
            
            response = self.session.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    summary = data.get('summary', {})
                    total = summary.get('total_analyzed', 0)
                    success_rate = summary.get('success_rate', 0) * 100
                    self.log_test("Batch Consistency", True, f"{total} licitações analisadas, {success_rate:.1f}% sucesso")
                    return True
                else:
                    self.log_test("Batch Consistency", False, data.get('error', 'Erro desconhecido'))
                    return False
            else:
                self.log_test("Batch Consistency", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Batch Consistency", False, f"Erro: {str(e)}")
            return False
    
    def test_data_comparison(self) -> bool:
        """Testa comparação entre dados de busca e detalhes"""
        try:
            # Dados de exemplo simulando diferenças
            search_data = {
                "numeroControlePNCP": "08584229000122-1-000013/2025",
                "objetoCompra": "Serviços de limpeza",
                "valorTotalEstimado": 50000.00,
                "modalidadeNome": "Pregão Eletrônico"
            }
            
            detail_data = {
                "numeroControlePNCP": "08584229000122-1-000013/2025",
                "objetoCompra": "Serviços de limpeza predial e conservação",  # Diferente
                "valorTotalEstimado": 52000.00,  # Diferente
                "modalidadeNome": "Pregão Eletrônico"
            }
            
            url = f"{self.base_url}/api/debug/compare-data"
            payload = {
                "search_data": search_data,
                "detail_data": detail_data
            }
            
            response = self.session.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.log_test("Data Comparison", True, "Comparação entre dados concluída")
                    return True
                else:
                    self.log_test("Data Comparison", False, data.get('error', 'Erro desconhecido'))
                    return False
            else:
                self.log_test("Data Comparison", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Data Comparison", False, f"Erro: {str(e)}")
            return False
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes do sistema enhanced"""
        print("🧪 INICIANDO TESTES DO SISTEMA ENHANCED")
        print("=" * 50)
        
        tests = [
            self.test_debug_health,
            self.test_consistency_report,
            self.test_licitacao_consistency,
            self.test_api_response_debug,
            self.test_licitacao_enrichment,
            self.test_batch_consistency,
            self.test_data_comparison
        ]
        
        total_tests = len(tests)
        passed_tests = 0
        
        for test in tests:
            try:
                if test():
                    passed_tests += 1
                time.sleep(1)  # Pausa entre testes
            except Exception as e:
                print(f"❌ Erro no teste {test.__name__}: {str(e)}")
        
        print("=" * 50)
        print(f"📊 RESULTADOS: {passed_tests}/{total_tests} testes passaram")
        print(f"📈 Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'test_results': self.test_results
        }
    
    def print_detailed_results(self):
        """Imprime resultados detalhados dos testes"""
        print("\n🔍 RESULTADOS DETALHADOS:")
        print("-" * 40)
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}")
            if result['details']:
                print(f"   {result['details']}")
        
        # Resumo de falhas
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print("\n🚨 TESTES QUE FALHARAM:")
            for failed in failed_tests:
                print(f"   - {failed['test']}: {failed['details']}")

def main():
    """Função principal do script de teste"""
    import sys
    
    # Permitir especificar URL base como argumento
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    print(f"🎯 Testando sistema enhanced em: {base_url}")
    
    tester = EnhancedSystemTester(base_url)
    results = tester.run_all_tests()
    
    # Imprimir resultados detalhados
    tester.print_detailed_results()
    
    # Salvar resultados em arquivo
    with open('test_results_enhanced.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Resultados salvos em: test_results_enhanced.json")
    
    # Exit code baseado no sucesso
    exit_code = 0 if results['success_rate'] >= 70 else 1
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 