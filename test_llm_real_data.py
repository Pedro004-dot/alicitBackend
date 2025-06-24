#!/usr/bin/env python3
"""
🔥 TESTE COMPARATIVO COM DADOS REAIS: llama3.2 vs qwen2.5:7b
Conecta ao Supabase e testa validação de matches com licitações e empresas REAIS
"""

import time
import json
import logging
import requests
import os
import psycopg2
from datetime import datetime
from typing import Dict, List, Any, Optional
from psycopg2.extras import DictCursor

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealDataOllamaTest:
    def __init__(self):
        self.ollama_base_url = "http://localhost:11434"
        self.models = ["llama3.2:latest", "qwen2.5:7b"]
        
        # Configuração do banco de dados (usando as mesmas configurações do projeto)
        self.db_config = {
            'host': 'aws-0-sa-east-1.pooler.supabase.com',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres.hdlowzlkwrboqfzjewom',
            'password': os.getenv('SUPABASE_DB_PASSWORD', 'Oqj7QlCCJvEL9J3O')  # Use env var se disponível
        }
    
    def get_db_connection(self):
        """Conectar ao banco de dados"""
        return psycopg2.connect(**self.db_config)
    
    def fetch_real_licitacoes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Buscar licitações reais com itens do Supabase"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        l.pncp_id,
                        l.objeto_compra,
                        array_agg(DISTINCT li.descricao) as itens
                    FROM licitacoes l
                    LEFT JOIN licitacao_itens li ON l.id = li.licitacao_id
                    WHERE l.objeto_compra IS NOT NULL 
                        AND l.objeto_compra != ''
                        AND li.descricao IS NOT NULL
                    GROUP BY l.id, l.pncp_id, l.objeto_compra
                    HAVING COUNT(li.id) > 0
                    ORDER BY l.created_at DESC
                    LIMIT %s
                """, (limit,))
                
                licitacoes = []
                for row in cursor.fetchall():
                    # Limpar itens None ou vazios
                    itens_limpos = [item for item in row['itens'] if item and item.strip()]
                    if itens_limpos:  # Só incluir se tiver itens válidos
                        licitacoes.append({
                            'pncp_id': row['pncp_id'],
                            'objeto_compra': row['objeto_compra'],
                            'itens': itens_limpos[:3]  # Limitar a 3 itens para manter prompt gerenciável
                        })
                
                return licitacoes
        finally:
            conn.close()
    
    def fetch_real_empresas(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar empresas reais com produtos do Supabase"""
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        nome_fantasia,
                        descricao_servicos_produtos,
                        produtos
                    FROM empresas 
                    WHERE produtos IS NOT NULL 
                        AND produtos != '[]'::jsonb
                        AND descricao_servicos_produtos IS NOT NULL
                        AND descricao_servicos_produtos != ''
                        AND jsonb_array_length(produtos) > 0
                    ORDER BY nome_fantasia
                    LIMIT %s
                """, (limit,))
                
                empresas = []
                for row in cursor.fetchall():
                    # Parse dos produtos JSON
                    produtos = row['produtos'] if isinstance(row['produtos'], list) else []
                    if produtos:  # Só incluir se tiver produtos
                        empresas.append({
                            'nome': row['nome_fantasia'],
                            'descricao': row['descricao_servicos_produtos'],
                            'produtos': produtos[:5]  # Limitar a 5 produtos para prompt
                        })
                
                return empresas
        finally:
            conn.close()
    
    def build_optimized_prompt_llama32_v2(self, empresa_nome: str, empresa_descricao: str, 
                                          empresa_produtos: List[str], licitacao_objeto: str, 
                                          licitacao_itens: List[str], similarity_score: float) -> str:
        """
        Prompt MELHORADO para llama3.2 - Mais equilibrado, menos rigoroso
        """
        produtos_texto = "\n".join([f"• {p}" for p in empresa_produtos]) if empresa_produtos else "Não especificados"
        itens_texto = "\n".join([f"• {i[:100]}..." if len(i) > 100 else f"• {i}" for i in licitacao_itens]) if licitacao_itens else "Não especificados"
        
        return f"""ANÁLISE DE COMPATIBILIDADE EMPRESARIAL

**EMPRESA: {empresa_nome}**
Atividades: {empresa_descricao}
Produtos/Serviços oferecidos:
{produtos_texto}

**LICITAÇÃO:**
Objetivo: {licitacao_objeto[:200]}...
Itens necessários:
{itens_texto}

**CRITÉRIOS DE AVALIAÇÃO:**
1. A empresa tem produtos/serviços relacionados aos itens da licitação?
2. A área de atuação é compatível com o objetivo da licitação?
3. É razoável que esta empresa possa atender esta demanda?

**INSTRUÇÕES:**
- APROVE se houver compatibilidade clara entre os produtos da empresa e os itens da licitação
- APROVE se a empresa atua na mesma área geral (ex: escritório vs materiais de escritório)
- REJEITE apenas se for claramente incompatível (ex: empresa de alimentos vs equipamentos médicos)
- Em caso de dúvida, seja moderadamente favorável à aprovação

Responda APENAS em JSON válido:
{{"compativel": true/false, "confianca": 0.XX, "justificativa": "explicação breve"}}"""

    def build_balanced_prompt_qwen(self, empresa_nome: str, empresa_descricao: str, 
                                   empresa_produtos: List[str], licitacao_objeto: str, 
                                   licitacao_itens: List[str], similarity_score: float) -> str:
        """
        Prompt BALANCEADO para qwen2.5:7b - Mantém qualidade mas mais rigoroso
        """
        produtos_texto = "\n".join([f"• {p}" for p in empresa_produtos]) if empresa_produtos else "Não especificados"
        itens_texto = "\n".join([f"• {i[:100]}..." if len(i) > 100 else f"• {i}" for i in licitacao_itens]) if licitacao_itens else "Não especificados"
        
        return f"""ANÁLISE RIGOROSA DE COMPATIBILIDADE COMERCIAL

### DADOS DA EMPRESA
**Nome:** {empresa_nome}
**Descrição:** {empresa_descricao}
**Produtos/Serviços:**
{produtos_texto}

### DADOS DA LICITAÇÃO
**Objeto:** {licitacao_objeto[:250]}...
**Itens Específicos:**
{itens_texto}

**Score Semântico:** {similarity_score:.1%}

### CRITÉRIOS DE AVALIAÇÃO RIGOROSA:
1. **Compatibilidade Direta**: Os produtos da empresa atendem ESPECIFICAMENTE aos itens licitados?
2. **Experiência Setorial**: A empresa demonstra experiência na área requerida?
3. **Viabilidade Técnica**: A empresa tem capacidade real de entregar o que é solicitado?
4. **Coerência Comercial**: Faz sentido comercial esta empresa participar desta licitação?

### DECISÃO:
- ✅ APROVAR: Somente se houver correspondência clara e direta
- 🚫 REJEITAR: Se houver qualquer dúvida significativa sobre a capacidade

Responda APENAS com JSON válido:
{{"compativel": true/false, "confianca": 0.XX, "justificativa": "análise detalhada"}}"""

    def create_realistic_test_scenarios(self) -> List[Dict[str, Any]]:
        """Criar cenários de teste com dados reais do Supabase"""
        print("🔍 Buscando dados reais do Supabase...")
        
        try:
            licitacoes = self.fetch_real_licitacoes(5)
            empresas = self.fetch_real_empresas(10)
            
            print(f"📋 {len(licitacoes)} licitações carregadas")
            print(f"🏢 {len(empresas)} empresas carregadas")
            
            # Criar cenários manuais baseados nos dados reais
            scenarios = []
            
            # Cenário 1: Match óbvio - Materiais de escritório
            materiais_escritorio = next((e for e in empresas if 'escritorio' in e['nome'].lower()), None)
            licitacao_equipamentos = next((l for l in licitacoes if any(
                'equipamento' in item.lower() or 'material' in item.lower() 
                for item in l['itens']
            )), None)
            
            if materiais_escritorio and licitacao_equipamentos:
                scenarios.append({
                    "nome": "Match Realista - Equipamentos/Materiais",
                    "empresa": materiais_escritorio,
                    "licitacao": licitacao_equipamentos,
                    "expected": True,
                    "justificativa": "Empresa de materiais pode fornecer equipamentos correlatos"
                })
            
            # Cenário 2: Match impossível - Software vs Agro
            empresa_tech = next((e for e in empresas if any(
                tech in e['descricao'].lower() for tech in ['software', 'tecnologia', 'ia']
            )), None)
            licitacao_agro = next((l for l in licitacoes if any(
                agro in l['objeto_compra'].lower() for agro in ['agr', 'fertilizante', 'campo']
            )), None)
            
            if empresa_tech:
                # Usar qualquer licitação não-tech como contraste
                licitacao_contraste = next((l for l in licitacoes if not any(
                    tech in l['objeto_compra'].lower() for tech in ['software', 'sistema', 'tecnologia']
                )), None)
                
                if licitacao_contraste:
                    scenarios.append({
                        "nome": "Match Impossível - Tech vs Físico",
                        "empresa": empresa_tech,
                        "licitacao": licitacao_contraste,
                        "expected": False,
                        "justificativa": "Empresa de tecnologia não fornece produtos físicos não-tech"
                    })
            
            # Cenário 3: Match questionável - AgroFrare
            agrofware = next((e for e in empresas if 'agro' in e['nome'].lower()), None)
            if agrofware:
                licitacao_nao_agro = next((l for l in licitacoes if not any(
                    agro in l['objeto_compra'].lower() for agro in ['agr', 'fertilizante', 'campo', 'rural']
                )), None)
                
                if licitacao_nao_agro:
                    scenarios.append({
                        "nome": "Match Questionável - Agro vs Outros",
                        "empresa": agrofware,
                        "licitacao": licitacao_nao_agro,
                        "expected": False,
                        "justificativa": "Empresa agro especializada não atende demandas gerais"
                    })
            
            # Cenário 4: Usar dados diversos
            for i, (empresa, licitacao) in enumerate(zip(empresas[:2], licitacoes[:2])):
                # Tentar determinar se é um match razoável baseado em palavras-chave
                empresa_keywords = set(empresa['descricao'].lower().split() + 
                                     [p.lower() for p in empresa['produtos']])
                licitacao_keywords = set(licitacao['objeto_compra'].lower().split() + 
                                       [item.lower() for item in licitacao['itens']])
                
                # Interseção simples para determinar expectativa
                overlap = len(empresa_keywords.intersection(licitacao_keywords))
                expected = overlap > 2  # Se houver mais de 2 palavras em comum
                
                scenarios.append({
                    "nome": f"Cenário Real {i+1} - {empresa['nome']} vs Licitação",
                    "empresa": empresa,
                    "licitacao": licitacao,
                    "expected": expected,
                    "justificativa": f"Baseado em análise de palavras-chave (overlap: {overlap})"
                })
            
            return scenarios
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar dados do Supabase: {e}")
            return []

    def call_ollama_model(self, model: str, prompt: str, timeout: int = 90) -> Dict[str, Any]:
        """Chamar modelo específico no Ollama com timeout aumentado"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Ligeiramente mais criativo
                        "top_p": 0.9,
                        "num_predict": 300   # Respostas mais curtas
                    }
                },
                timeout=timeout
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()
                
                # Parse mais robusto do JSON
                try:
                    # Múltiplas tentativas de extrair JSON
                    json_attempts = [
                        raw_response,  # Resposta completa
                        raw_response[raw_response.find('{'):raw_response.rfind('}')+1],  # Entre chaves
                        raw_response[raw_response.find('{"'):raw_response.rfind('"}')+2]  # JSON quoted
                    ]
                    
                    parsed_result = None
                    for attempt in json_attempts:
                        try:
                            if attempt and '{' in attempt and '}' in attempt:
                                parsed_result = json.loads(attempt)
                                break
                        except:
                            continue
                    
                    if parsed_result:
                        return {
                            "success": True,
                            "processing_time": processing_time,
                            "raw_response": raw_response,
                            "parsed_result": parsed_result,
                            "compativel": parsed_result.get("compativel", False),
                            "confianca": float(parsed_result.get("confianca", 0.0)),
                            "justificativa": parsed_result.get("justificativa", "")
                        }
                    else:
                        raise ValueError("Não foi possível extrair JSON válido")
                        
                except Exception as e:
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

    def run_real_data_test(self):
        """Executar teste com dados reais do Supabase"""
        
        print("🔥 INICIANDO TESTE COM DADOS REAIS DO SUPABASE")
        print("=" * 70)
        
        # Verificar conectividade
        try:
            conn = self.get_db_connection()
            conn.close()
            print("✅ Conexão com Supabase estabelecida")
        except Exception as e:
            logger.error(f"❌ Erro de conexão com Supabase: {e}")
            return
        
        # Verificar Ollama
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                available_models = [model['name'] for model in response.json().get('models', [])]
                print(f"🦙 Ollama ativo. Modelos: {available_models}")
                
                for model in self.models:
                    if model not in available_models:
                        logger.error(f"❌ Modelo {model} não disponível!")
                        return
            else:
                logger.error("❌ Ollama não está respondendo")
                return
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com Ollama: {e}")
            return
        
        # Criar cenários de teste
        test_scenarios = self.create_realistic_test_scenarios()
        if not test_scenarios:
            logger.error("❌ Não foi possível criar cenários de teste")
            return
        
        print(f"📋 {len(test_scenarios)} cenários de teste criados")
        
        results = {}
        
        for model in self.models:
            print(f"\n🤖 TESTANDO MODELO: {model}")
            print("-" * 50)
            
            results[model] = {
                "total_time": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "correct_decisions": 0,
                "test_details": []
            }
            
            for i, scenario in enumerate(test_scenarios, 1):
                print(f"\n[{i}/{len(test_scenarios)}] {scenario['nome']}")
                print(f"   🏢 Empresa: {scenario['empresa']['nome']}")
                print(f"   📋 Licitação: {scenario['licitacao']['pncp_id']}")
                
                # Escolher prompt baseado no modelo
                if model == "llama3.2:latest":
                    prompt = self.build_optimized_prompt_llama32_v2(
                        scenario['empresa']['nome'],
                        scenario['empresa']['descricao'],
                        scenario['empresa']['produtos'],
                        scenario['licitacao']['objeto_compra'],
                        scenario['licitacao']['itens'],
                        0.75
                    )
                else:
                    prompt = self.build_balanced_prompt_qwen(
                        scenario['empresa']['nome'],
                        scenario['empresa']['descricao'],
                        scenario['empresa']['produtos'],
                        scenario['licitacao']['objeto_compra'],
                        scenario['licitacao']['itens'],
                        0.75
                    )
                
                result = self.call_ollama_model(model, prompt)
                
                if result["success"]:
                    decision = result["compativel"]
                    confidence = result["confianca"]
                    processing_time = result["processing_time"]
                    justificativa = result["justificativa"]
                    
                    is_correct = decision == scenario["expected"]
                    
                    print(f"   ⏱️  Tempo: {processing_time:.1f}s")
                    print(f"   🎯 Decisão: {'✅ APROVOU' if decision else '🚫 REJEITOU'}")
                    print(f"   📊 Confiança: {confidence:.0%}")
                    print(f"   ✅ Correto: {'SIM' if is_correct else 'NÃO'}")
                    print(f"   💭 Justificativa: {justificativa[:100]}...")
                    
                    results[model]["total_time"] += processing_time
                    results[model]["successful_tests"] += 1
                    if is_correct:
                        results[model]["correct_decisions"] += 1
                    
                    results[model]["test_details"].append({
                        "scenario_name": scenario["nome"],
                        "empresa_nome": scenario['empresa']['nome'],
                        "licitacao_id": scenario['licitacao']['pncp_id'],
                        "expected": scenario["expected"],
                        "decision": decision,
                        "confidence": confidence,
                        "processing_time": processing_time,
                        "is_correct": is_correct,
                        "justificativa": justificativa,
                        "scenario_justificativa": scenario["justificativa"]
                    })
                else:
                    print(f"   ❌ ERRO: {result['error']}")
                    results[model]["failed_tests"] += 1
        
        # Análise final
        self.print_real_data_results(results)
        self.save_real_data_results(results)
        
        return results

    def print_real_data_results(self, results: Dict):
        """Imprimir análise dos resultados com dados reais"""
        print("\n" + "=" * 70)
        print("📊 ANÁLISE COMPARATIVA - DADOS REAIS DO SUPABASE")
        print("=" * 70)
        
        for model in self.models:
            data = results[model]
            if data["successful_tests"] > 0:
                avg_time = data["total_time"] / data["successful_tests"]
                accuracy = (data["correct_decisions"] / data["successful_tests"]) * 100
                
                print(f"\n🤖 {model.upper()}:")
                print(f"   ⏱️  Tempo médio: {avg_time:.1f}s")
                print(f"   🎯 Acurácia: {accuracy:.1f}% ({data['correct_decisions']}/{data['successful_tests']})")
                print(f"   ✅ Sucessos: {data['successful_tests']}")
                print(f"   ❌ Falhas: {data['failed_tests']}")
        
        # Comparação e recomendação
        if len(self.models) == 2 and all(results[m]["successful_tests"] > 0 for m in self.models):
            model1, model2 = self.models
            data1, data2 = results[model1], results[model2]
            
            avg_time1 = data1["total_time"] / data1["successful_tests"]
            avg_time2 = data2["total_time"] / data2["successful_tests"]
            
            accuracy1 = (data1["correct_decisions"] / data1["successful_tests"]) * 100
            accuracy2 = (data2["correct_decisions"] / data2["successful_tests"]) * 100
            
            print(f"\n🏆 COMPARAÇÃO FINAL:")
            print(f"   ⚡ Velocidade: {model1} {avg_time1:.1f}s vs {model2} {avg_time2:.1f}s")
            print(f"   🎯 Precisão: {model1} {accuracy1:.1f}% vs {model2} {accuracy2:.1f}%")
            
            # Calcular "score" combinado (velocidade + precisão)
            speed_score1 = 100 / avg_time1 if avg_time1 > 0 else 0
            speed_score2 = 100 / avg_time2 if avg_time2 > 0 else 0
            
            combined_score1 = (accuracy1 * 0.7) + (speed_score1 * 0.3)  # 70% precisão, 30% velocidade
            combined_score2 = (accuracy2 * 0.7) + (speed_score2 * 0.3)
            
            print(f"\n💡 RECOMENDAÇÃO:")
            if combined_score1 > combined_score2:
                print(f"   🏆 Use {model1} - Melhor equilíbrio geral")
                if accuracy1 > accuracy2:
                    print(f"   ✅ Mais preciso E mais rápido")
                else:
                    print(f"   ⚡ Velocidade compensa a menor precisão")
            else:
                print(f"   🏆 Use {model2} - Melhor equilíbrio geral")
                if accuracy2 > accuracy1:
                    print(f"   ✅ Maior precisão justifica tempo extra")
                else:
                    print(f"   ⚡ Velocidade superior")

    def save_real_data_results(self, results: Dict):
        """Salvar resultados detalhados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"real_data_test_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados salvos em: {filename}")

def main():
    """Função principal"""
    tester = RealDataOllamaTest()
    tester.run_real_data_test()

if __name__ == "__main__":
    main() 