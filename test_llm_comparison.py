#!/usr/bin/env python3
"""
🧪 TESTE COMPARATIVO: llama3.2 vs qwen2.5:7b
Compara velocidade e acurácia dos dois modelos LLM para validação de matches
"""

import time
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OllamaModelTester:
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.models = ["llama3.2:latest", "qwen2.5:7b"]
        self.test_results = {}
    
    def check_ollama_health(self):
        """Verificar se Ollama está rodando"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = [model['name'] for model in response.json().get('models', [])]
                logger.info(f"🦙 Ollama ativo. Modelos disponíveis: {available_models}")
                return available_models
            return []
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com Ollama: {e}")
            return []
    
    def build_optimized_prompt_llama32(self, empresa_nome: str, empresa_descricao: str, 
                                       empresa_produtos: List[str], licitacao_objeto: str, 
                                       licitacao_itens: List[str], similarity_score: float) -> str:
        """
        Prompt OTIMIZADO para llama3.2 - mais direto e rigoroso
        """
        produtos_texto = "\n".join([f"• {p}" for p in empresa_produtos]) if empresa_produtos else "Não especificados"
        itens_texto = "\n".join([f"• {i}" for i in licitacao_itens]) if licitacao_itens else "Não especificados"
        
        return f"""ANÁLISE RIGOROSA DE COMPATIBILIDADE

**EMPRESA: {empresa_nome}**
Descrição: {empresa_descricao}
Produtos/Serviços:
{produtos_texto}

**LICITAÇÃO:**
Objeto: {licitacao_objeto}
Itens específicos:
{itens_texto}

**INSTRUÇÕES CRÍTICAS:**
1. SEJA RIGOROSO! Apenas aprove se houver CLARA compatibilidade
2. A empresa DEVE ter produtos/serviços DIRETAMENTE relacionados
3. NÃO faça conexões forçadas ou interpretações vagas
4. REJEITE qualquer dúvida ou incompatibilidade

**CRITÉRIOS DE APROVAÇÃO:**
✅ Empresa tem produtos ESPECÍFICOS para os itens solicitados
✅ Experiência COMPROVADA na área
✅ Match técnico ÓBVIO

Responda APENAS em JSON:
{{"compativel": true/false, "confianca": 0.XX, "justificativa": "explicação concisa"}}"""

    def build_current_prompt_qwen(self, empresa_nome: str, empresa_descricao: str, 
                                  empresa_produtos: List[str], licitacao_objeto: str, 
                                  licitacao_itens: List[str], similarity_score: float) -> str:
        """
        Prompt atual usado pelo qwen2.5:7b
        """
        produtos_texto = "\n".join([f"• {p}" for p in empresa_produtos]) if empresa_produtos else "Não especificados"
        itens_texto = "\n".join([f"• {i}" for i in licitacao_itens]) if licitacao_itens else "Não especificados"
        
        return f"""ANÁLISE DE COMPATIBILIDADE DETALHADA (PRODUTO A PRODUTO)

### DADOS DA EMPRESA
- **NOME:** {empresa_nome}
- **DESCRIÇÃO:** {empresa_descricao}
- **PRODUTOS/SERVIÇOS:**
{produtos_texto}

### DADOS DA LICITAÇÃO
- **OBJETO:** {licitacao_objeto}
- **ITENS ESPECÍFICOS:**
{itens_texto}

**Score Semântico:** {similarity_score:.1%}

Analise se a empresa tem CAPACIDADE REAL de atender esta licitação, considerando:
1. Produtos específicos da empresa vs itens da licitação
2. Experiência no setor
3. Viabilidade técnica e comercial

Responda APENAS com o formato JSON:
{{"compativel": true/false, "confianca": 0.XX, "justificativa": "explicação detalhada"}}"""

    def call_ollama_model(self, model: str, prompt: str, timeout: int = 60) -> Dict[str, Any]:
        """Chamar modelo específico no Ollama"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 500
                    }
                },
                timeout=timeout
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # Tentar fazer parse do JSON
                try:
                    # Extrair JSON da resposta
                    json_start = raw_response.find('{')
                    json_end = raw_response.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = raw_response[json_start:json_end]
                        parsed_result = json.loads(json_str)
                        
                        return {
                            "success": True,
                            "processing_time": processing_time,
                            "raw_response": raw_response,
                            "parsed_result": parsed_result,
                            "compativel": parsed_result.get("compativel", False),
                            "confianca": parsed_result.get("confianca", 0.0),
                            "justificativa": parsed_result.get("justificativa", "")
                        }
                    else:
                        raise ValueError("JSON não encontrado na resposta")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    return {
                        "success": False,
                        "processing_time": processing_time,
                        "error": f"Erro ao parsear JSON: {e}",
                        "raw_response": raw_response
                    }
            else:
                return {
                    "success": False,
                    "processing_time": processing_time,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "processing_time": 0,
                "error": str(e)
            }

    def run_comparison_test(self):
        """Executar teste comparativo completo"""
        
        # Casos de teste representativos
        test_cases = [
            {
                "nome": "Match Óbvio - DEVE APROVAR",
                "empresa_nome": "Materias de escritorio",
                "empresa_descricao": "Distribuidora de materiais de escritório e papelaria",
                "empresa_produtos": ["caneta", "papel", "grampeador", "pastas", "lapis", "borrachas"],
                "licitacao_objeto": "Aquisição de materiais de expediente para escritório",
                "licitacao_itens": ["Canetas esferográficas", "Papel A4", "Grampeadores", "Pastas suspensas"],
                "expected": True
            },
            {
                "nome": "Match Impossível - DEVE REJEITAR", 
                "empresa_nome": "AgroFrare",
                "empresa_descricao": "Empresa especializada em soluções para o agronegócio",
                "empresa_produtos": ["fertilizantes", "defensivos", "sementes", "consultoria agronômica"],
                "licitacao_objeto": "Aquisição de licenças de software de análise de dados",
                "licitacao_itens": ["Licenças perpétuas I2 Analyst", "Treinamento online", "Suporte técnico"],
                "expected": False
            },
            {
                "nome": "Match Limítrofe - Software vs TI",
                "empresa_nome": "Clonex", 
                "empresa_descricao": "Empresa desenvolvedora de softwares com IA",
                "empresa_produtos": ["Inteligencia artificial", "Software"],
                "licitacao_objeto": "Aquisição de materiais de expediente",
                "licitacao_itens": ["Baterias", "Calculadoras", "Dispositivos de armazenamento"],
                "expected": False
            },
            {
                "nome": "Match Questionável - Agro vs Construção",
                "empresa_nome": "AgroFrare",
                "empresa_descricao": "Empresa especializada em soluções para o agronegócio", 
                "empresa_produtos": ["fertilizantes", "defensivos", "sementes"],
                "licitacao_objeto": "Contratação para execução de pavimentação asfáltica",
                "licitacao_itens": ["Asfalto", "Brita", "Mão de obra especializada"],
                "expected": False
            },
            {
                "nome": "Match Correto - Limpeza vs Limpeza",
                "empresa_nome": "Risadinha company",
                "empresa_descricao": "Distribuidora de produtos de limpeza e descartáveis",
                "empresa_produtos": ["produtos de limpeza", "materiais descartáveis", "produtos de higiene"],
                "licitacao_objeto": "Aquisição de materiais de higiene e limpeza",
                "licitacao_itens": ["Detergente", "Desinfetante", "Papel toalha", "Sacos de lixo"],
                "expected": True
            }
        ]
        
        print("🧪 INICIANDO TESTE COMPARATIVO LLM")
        print("=" * 60)
        
        # Verificar se modelos estão disponíveis
        available_models = self.check_ollama_health()
        for model in self.models:
            if model not in available_models:
                logger.error(f"❌ Modelo {model} não está disponível!")
                return
        
        results = {}
        
        for model in self.models:
            print(f"\n🤖 TESTANDO MODELO: {model}")
            print("-" * 40)
            
            results[model] = {
                "total_time": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "correct_decisions": 0,
                "test_details": []
            }
            
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n[{i}/5] {test_case['nome']}")
                
                # Escolher prompt baseado no modelo
                if model == "llama3.2":
                    prompt = self.build_optimized_prompt_llama32(
                        test_case["empresa_nome"],
                        test_case["empresa_descricao"], 
                        test_case["empresa_produtos"],
                        test_case["licitacao_objeto"],
                        test_case["licitacao_itens"],
                        0.75
                    )
                else:
                    prompt = self.build_current_prompt_qwen(
                        test_case["empresa_nome"],
                        test_case["empresa_descricao"],
                        test_case["empresa_produtos"], 
                        test_case["licitacao_objeto"],
                        test_case["licitacao_itens"],
                        0.75
                    )
                
                result = self.call_ollama_model(model, prompt)
                
                if result["success"]:
                    decision = result["compativel"]
                    confidence = result["confianca"]
                    processing_time = result["processing_time"]
                    
                    # Verificar se a decisão está correta
                    is_correct = decision == test_case["expected"]
                    
                    print(f"   ⏱️  Tempo: {processing_time:.1f}s")
                    print(f"   🎯 Decisão: {'✅ APROVOU' if decision else '🚫 REJEITOU'}")
                    print(f"   📊 Confiança: {confidence:.0%}")
                    print(f"   ✅ Correto: {'SIM' if is_correct else 'NÃO'}")
                    
                    results[model]["total_time"] += processing_time
                    results[model]["successful_tests"] += 1
                    if is_correct:
                        results[model]["correct_decisions"] += 1
                        
                    results[model]["test_details"].append({
                        "test_name": test_case["nome"],
                        "expected": test_case["expected"],
                        "decision": decision,
                        "confidence": confidence,
                        "processing_time": processing_time,
                        "is_correct": is_correct,
                        "justificativa": result["justificativa"]
                    })
                else:
                    print(f"   ❌ ERRO: {result['error']}")
                    results[model]["failed_tests"] += 1
        
        # Análise comparativa
        self.print_comparison_results(results)
        
        # Salvar resultados detalhados
        self.save_detailed_results(results)
        
        return results

    def print_comparison_results(self, results: Dict):
        """Imprimir análise comparativa dos resultados"""
        print("\n" + "=" * 60)
        print("📊 ANÁLISE COMPARATIVA DOS RESULTADOS")
        print("=" * 60)
        
        for model in self.models:
            data = results[model]
            avg_time = data["total_time"] / max(data["successful_tests"], 1)
            accuracy = (data["correct_decisions"] / max(data["successful_tests"], 1)) * 100
            
            print(f"\n🤖 {model.upper()}:")
            print(f"   ⏱️  Tempo médio por validação: {avg_time:.1f}s")
            print(f"   🎯 Acurácia: {accuracy:.1f}% ({data['correct_decisions']}/{data['successful_tests']})")
            print(f"   ✅ Testes bem-sucedidos: {data['successful_tests']}")
            print(f"   ❌ Testes falhados: {data['failed_tests']}")
        
        # Comparação direta
        if len(self.models) == 2:
            model1, model2 = self.models
            data1, data2 = results[model1], results[model2]
            
            avg_time1 = data1["total_time"] / max(data1["successful_tests"], 1)
            avg_time2 = data2["total_time"] / max(data2["successful_tests"], 1)
            
            accuracy1 = (data1["correct_decisions"] / max(data1["successful_tests"], 1)) * 100
            accuracy2 = (data2["correct_decisions"] / max(data2["successful_tests"], 1)) * 100
            
            print(f"\n🏆 COMPARAÇÃO DIRETA:")
            print(f"   ⚡ Velocidade: {model1} é {avg_time2/avg_time1:.1f}x {'mais rápido' if avg_time1 < avg_time2 else 'mais lento'}")
            print(f"   🎯 Acurácia: {model1} {accuracy1:.1f}% vs {model2} {accuracy2:.1f}%")
            
            if accuracy1 > accuracy2 and avg_time1 < avg_time2:
                print(f"   🏆 VENCEDOR ABSOLUTO: {model1} (mais rápido E mais preciso)")
            elif accuracy1 > accuracy2:
                print(f"   🏆 MAIS PRECISO: {model1}")
            elif avg_time1 < avg_time2:
                print(f"   🏆 MAIS RÁPIDO: {model1}")
            else:
                print(f"   🏆 MAIS PRECISO: {model2}")

    def save_detailed_results(self, results: Dict):
        """Salvar resultados detalhados em arquivo JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_comparison_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados detalhados salvos em: {filename}")

def main():
    """Função principal"""
    tester = OllamaModelTester()
    tester.run_comparison_test()

if __name__ == "__main__":
    main() 