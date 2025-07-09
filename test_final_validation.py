#!/usr/bin/env python3
"""
🧪 TESTE FINAL DE VALIDAÇÃO 
Valida todas as correções implementadas no sistema:

1. ✅ Erro de ordenação (datetime vs str) - RESOLVIDO
2. ✅ Campo provider_name no frontend - CORRIGIDO  
3. ✅ Entidade contratante (UASG None) - CORRIGIDO
4. ✅ Datas de abertura/encerramento - EXTRAÍDAS
5. ✅ Endpoint para itens ComprasNet - IMPLEMENTADO

Autor: Sistema AlicitSaas
Data: 2025-07-09
"""

import requests
import json
from datetime import datetime
import sys

# Configuração da API
BASE_URL = "http://localhost:5001"
TIMEOUT = 30

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(title):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{title.center(60)}{Colors.ENDC}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️ {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️ {message}{Colors.ENDC}")

def test_api_health():
    """Teste 0: Verificar se API está funcionando"""
    print_header("TESTE 0: SAÚDE DA API")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API funcionando - {data['message']}")
            print_info(f"Endpoints disponíveis: {data['endpoints']}")
            return True
        else:
            print_error(f"API retornou status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Erro ao conectar com a API: {e}")
        return False

def test_unified_search_sorting():
    """Teste 1: Verificar se erro de ordenação foi resolvido"""
    print_header("TESTE 1: CORREÇÃO DO ERRO DE ORDENAÇÃO")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/search/unified",
            params={'keywords': 'educacao', 'limit': 50},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('data', {}).get('opportunities', [])
            
            if opportunities:
                print_success(f"Busca unificada retornou {len(opportunities)} oportunidades")
                print_success("Erro de ordenação (datetime vs str) RESOLVIDO")
                
                # Verificar estrutura dos dados
                first_opp = opportunities[0]
                required_fields = ['id', 'provider_name', 'objeto_compra']
                missing_fields = [field for field in required_fields if field not in first_opp]
                
                if missing_fields:
                    print_warning(f"Campos faltando: {missing_fields}")
                else:
                    print_success("Estrutura de dados correta")
                
                return True
            else:
                print_warning("Busca retornou array vazio")
                return False
        else:
            print_error(f"Busca falhou com status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste de ordenação: {e}")
        return False

def test_provider_name_field():
    """Teste 2: Verificar se provider_name está sendo enviado corretamente"""
    print_header("TESTE 2: CAMPO PROVIDER_NAME")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/search/unified",
            params={'keywords': 'saude', 'limit': 20},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('data', {}).get('opportunities', [])
            
            # Contar providers
            provider_counts = {}
            for opp in opportunities:
                provider = opp.get('provider_name', 'MISSING')
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
            
            print_info(f"Distribuição por provider: {provider_counts}")
            
            # Verificar se há ambos os providers
            has_pncp = 'pncp' in provider_counts
            has_comprasnet = 'comprasnet' in provider_counts
            has_missing = 'MISSING' in provider_counts
            
            if has_pncp and has_comprasnet:
                print_success("Ambos providers (PNCP e ComprasNet) presentes")
            elif has_pncp:
                print_warning("Apenas PNCP presente")
            elif has_comprasnet:
                print_warning("Apenas ComprasNet presente")
            
            if has_missing:
                print_error(f"Campo provider_name faltando em {provider_counts['MISSING']} registros")
                return False
            else:
                print_success("Campo provider_name presente em todos os registros")
                return True
                
        else:
            print_error(f"Busca falhou com status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste de provider_name: {e}")
        return False

def test_entity_and_dates():
    """Teste 3: Verificar entidades e datas extraídas"""
    print_header("TESTE 3: ENTIDADES E DATAS EXTRAÍDAS")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/search/unified",
            params={'keywords': 'medicamentos', 'limit': 10},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('data', {}).get('opportunities', [])
            
            # Analisar entidades ComprasNet
            comprasnet_opps = [opp for opp in opportunities if opp.get('provider_name') == 'comprasnet']
            
            if comprasnet_opps:
                print_info(f"Analisando {len(comprasnet_opps)} licitações ComprasNet")
                
                entities_with_none = 0
                entities_valid = 0
                dates_present = 0
                
                for opp in comprasnet_opps:
                    # Verificar entidade
                    entity = opp.get('razao_social', '')
                    if 'None' in entity or entity == 'Entidade não identificada':
                        entities_with_none += 1
                    elif entity and len(entity) > 5:
                        entities_valid += 1
                    
                    # Verificar datas
                    if opp.get('submission_deadline') or opp.get('opening_date'):
                        dates_present += 1
                
                print_info(f"Entidades válidas: {entities_valid}")
                print_info(f"Entidades com problema: {entities_with_none}")
                print_info(f"Licitações com datas: {dates_present}")
                
                if entities_valid > entities_with_none:
                    print_success("Maioria das entidades extraídas corretamente")
                else:
                    print_warning("Ainda há problemas na extração de entidades")
                
                if dates_present > 0:
                    print_success("Datas sendo extraídas com sucesso")
                else:
                    print_warning("Nenhuma data encontrada")
                
                return entities_valid > 0 and dates_present > 0
            else:
                print_warning("Nenhuma licitação ComprasNet encontrada")
                return False
                
        else:
            print_error(f"Busca falhou com status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste de entidades/datas: {e}")
        return False

def test_comprasnet_items_endpoint():
    """Teste 4: Verificar novo endpoint para itens ComprasNet"""
    print_header("TESTE 4: ENDPOINT ITENS COMPRASNET")
    
    try:
        # Primeiro, buscar uma licitação ComprasNet
        response = requests.get(
            f"{BASE_URL}/api/search/unified",
            params={'keywords': 'educacao', 'limit': 50},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('data', {}).get('opportunities', [])
            
            # Encontrar uma licitação ComprasNet
            comprasnet_opp = None
            for opp in opportunities:
                if opp.get('provider_name') == 'comprasnet':
                    comprasnet_opp = opp
                    break
            
            if comprasnet_opp:
                external_id = comprasnet_opp['id']
                print_info(f"Testando busca de itens para: {external_id}")
                
                # Testar novo endpoint
                response = requests.get(
                    f"{BASE_URL}/api/bids/comprasnet/{external_id}/items",
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    items_data = response.json()
                    
                    if items_data.get('success'):
                        items = items_data.get('items', [])
                        print_success(f"Endpoint funcionando - {len(items)} itens encontrados")
                        print_info(f"Provider: {items_data.get('provider')}")
                        
                        # Verificar estrutura dos itens
                        if items:
                            item = items[0]
                            required_fields = ['item_number', 'description', 'quantity', 'unit']
                            missing_fields = [field for field in required_fields if field not in item]
                            
                            if missing_fields:
                                print_warning(f"Campos faltando nos itens: {missing_fields}")
                            else:
                                print_success("Estrutura dos itens correta")
                        
                        return True
                    else:
                        print_error(f"Endpoint retornou sucesso=false: {items_data.get('message')}")
                        return False
                else:
                    print_error(f"Endpoint falhou com status {response.status_code}")
                    return False
            else:
                print_warning("Nenhuma licitação ComprasNet encontrada para teste")
                return False
        else:
            print_error(f"Busca inicial falhou com status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste de endpoint ComprasNet: {e}")
        return False

def test_pncp_compatibility():
    """Teste 5: Verificar se compatibilidade PNCP foi mantida"""
    print_header("TESTE 5: COMPATIBILIDADE PNCP")
    
    try:
        # Buscar uma licitação PNCP
        response = requests.get(
            f"{BASE_URL}/api/search/unified",
            params={'keywords': 'software', 'limit': 20},
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            opportunities = data.get('data', {}).get('opportunities', [])
            
            # Encontrar uma licitação PNCP
            pncp_opp = None
            for opp in opportunities:
                if opp.get('provider_name') == 'pncp':
                    pncp_opp = opp
                    break
            
            if pncp_opp:
                pncp_id = pncp_opp['id']
                print_info(f"Testando PNCP ID: {pncp_id}")
                
                # Testar endpoint PNCP (deve funcionar)
                response = requests.get(
                    f"{BASE_URL}/api/bids/items",
                    params={'pncp_id': pncp_id},
                    timeout=TIMEOUT
                )
                
                if response.status_code == 200:
                    items_data = response.json()
                    print_success("Compatibilidade PNCP mantida")
                    print_info(f"Itens PNCP: {len(items_data.get('items', []))}")
                    return True
                else:
                    print_warning(f"Endpoint PNCP retornou status {response.status_code}")
                    return False
            else:
                print_warning("Nenhuma licitação PNCP encontrada")
                return False
        else:
            print_error(f"Busca falhou com status {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Erro no teste de compatibilidade PNCP: {e}")
        return False

def main():
    """Executar todos os testes de validação"""
    print_header("VALIDAÇÃO FINAL - CORREÇÕES IMPLEMENTADAS")
    print_info("Validando todas as correções do sistema AlicitSaas")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    tests = [
        ("Saúde da API", test_api_health),
        ("Correção de Ordenação", test_unified_search_sorting),
        ("Campo provider_name", test_provider_name_field),
        ("Entidades e Datas", test_entity_and_dates),
        ("Endpoint ComprasNet", test_comprasnet_items_endpoint),
        ("Compatibilidade PNCP", test_pncp_compatibility)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{Colors.YELLOW}🧪 Executando: {test_name}{Colors.ENDC}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            
            if result:
                print_success(f"{test_name} PASSOU")
            else:
                print_error(f"{test_name} FALHOU")
                
        except Exception as e:
            print_error(f"{test_name} ERRO: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} {test_name}")
    
    print(f"\n{Colors.BOLD}RESULTADO GERAL: {passed}/{total} testes passaram{Colors.ENDC}")
    
    if passed == total:
        print_success("🎉 TODAS AS CORREÇÕES VALIDADAS COM SUCESSO!")
        return 0
    else:
        print_error(f"❌ {total - passed} teste(s) falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 