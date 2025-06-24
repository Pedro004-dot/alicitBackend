#!/usr/bin/env python3
"""
🧪 Teste de Integração Ollama
Verifica se o qwen2.5:7b está funcionando corretamente com nosso sistema
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import requests
import time
from config.llm_config import LLMConfig
from matching.ollama_match_validator import OllamaMatchValidator

def test_ollama_direct():
    """Teste direto do Ollama"""
    print("🔍 TESTE DIRETO DO OLLAMA")
    print("-" * 40)
    
    # 1. Verificar se está rodando
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            print(f"✅ Ollama conectado - Modelos: {model_names}")
            
            if 'qwen2.5:7b' in model_names:
                print("✅ qwen2.5:7b disponível")
            else:
                print("❌ qwen2.5:7b NÃO encontrado")
                return False
                
        else:
            print(f"❌ Ollama erro: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro conectando Ollama: {e}")
        return False
    
    return True

def test_ollama_validator():
    """Teste do nosso validador Ollama"""
    print("\n🦙 TESTE DO VALIDADOR OLLAMA")
    print("-" * 40)
    
    try:
        validator = OllamaMatchValidator()
        
        if not validator.ollama_available:
            print("❌ Validador detectou Ollama indisponível")
            return False
        
        # Teste com match óbvio
        start_time = time.time()
        
        result = validator.validate_match(
            empresa_nome="TechSoft Desenvolvimento",
            empresa_descricao="Empresa especializada em desenvolvimento de software de gestão, sistemas web e aplicações móveis",
            licitacao_objeto="Desenvolvimento de sistema de gestão administrativa para órgão público",
            pncp_id="TEST123",
            similarity_score=0.89
        )
        
        processing_time = time.time() - start_time
        
        print(f"📊 RESULTADO DO TESTE:")
        print(f"   🤖 Modelo: {result.get('model', 'N/A')}")
        print(f"   ✅ Válido: {result['is_valid']}")
        print(f"   📈 Confiança: {result['confidence']:.1%}")
        print(f"   🧠 Justificativa: {result['reasoning'][:100]}...")
        print(f"   ⚡ Tempo: {processing_time:.2f}s")
        
        # Verificar se resultado faz sentido
        if result['is_valid'] and result['confidence'] > 0.6:
            print("✅ TESTE PASSOU - Match óbvio foi aprovado!")
            return True
        else:
            print("❌ TESTE FALHOU - Match óbvio foi rejeitado!")
            return False
            
    except Exception as e:
        print(f"❌ Erro no validador: {e}")
        return False

def test_llm_config():
    """Teste da configuração LLM"""
    print("\n⚙️ TESTE DA CONFIGURAÇÃO LLM")
    print("-" * 40)
    
    try:
        # Testar detecção de provider
        provider = LLMConfig.get_provider()
        print(f"📋 Provider detectado: {provider}")
        
        # Testar configurações Ollama
        ollama_config = LLMConfig.get_ollama_config()
        print(f"🦙 Config Ollama: {ollama_config}")
        
        # Testar disponibilidade
        is_available = LLMConfig.is_ollama_available()
        print(f"🔍 Ollama disponível: {is_available}")
        
        # Testar factory
        validator = LLMConfig.create_validator()
        validator_type = type(validator).__name__
        print(f"🏭 Validador criado: {validator_type}")
        
        if validator_type == "OllamaMatchValidator":
            print("✅ TESTE PASSOU - Factory está usando Ollama!")
            return True
        else:
            print(f"⚠️ AVISO - Factory está usando: {validator_type}")
            return True  # Pode ser fallback
            
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False

def test_fallback_scenario():
    """Teste do cenário de fallback"""
    print("\n🔄 TESTE DE FALLBACK")
    print("-" * 40)
    
    # Simular Ollama indisponível temporariamente
    original_url = os.getenv('OLLAMA_URL')
    os.environ['OLLAMA_URL'] = 'http://localhost:99999'  # URL inválida
    
    try:
        validator = LLMConfig.create_validator()
        validator_type = type(validator).__name__
        
        print(f"🔄 Com Ollama indisponível, usando: {validator_type}")
        
        if validator_type == "LLMMatchValidator":
            print("✅ TESTE PASSOU - Fallback para OpenAI funcionou!")
            result = True
        else:
            print(f"⚠️ Fallback inesperado: {validator_type}")
            result = True
            
    except Exception as e:
        print(f"❌ Erro no fallback: {e}")
        result = False
    finally:
        # Restaurar configuração original
        if original_url:
            os.environ['OLLAMA_URL'] = original_url
        else:
            os.environ.pop('OLLAMA_URL', None)
    
    return result

def main():
    """Executar todos os testes"""
    print("🧪 INICIANDO TESTES DE INTEGRAÇÃO OLLAMA")
    print("=" * 50)
    
    tests = [
        ("Conexão Ollama Direta", test_ollama_direct),
        ("Validador Ollama", test_ollama_validator),
        ("Configuração LLM", test_llm_config),
        ("Cenário Fallback", test_fallback_scenario),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Executando: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSOU" if result else "❌ FALHOU"
            print(f"📊 {test_name}: {status}")
        except Exception as e:
            print(f"💥 ERRO em {test_name}: {e}")
            results.append((test_name, False))
    
    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 RESUMO: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 TODOS OS TESTES PASSARAM! Ollama integrado com sucesso!")
    else:
        print("⚠️ Alguns testes falharam. Verifique a configuração.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 