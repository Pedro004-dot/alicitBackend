#!/usr/bin/env python3
"""
🔬 TESTE EXPANDIDO DE VALIDAÇÃO LLM COM DADOS REAIS DO SUPABASE
=================================================================

Este script testa os validadores LLM (OLLAMA local) com dados reais do banco Supabase.
Agora com prompts otimizados e cenários de teste mais abrangentes.

Prompts Otimizados:
- QWEN2.5: Foco na velocidade mantendo qualidade
- LLAMA3.2: Mais reflexão e critério rigoroso

Funcionalidades:
✅ Busca licitações e empresas reais do Supabase  
✅ Testa validadores OLLAMA (qwen2.5:7b e llama3.2)
✅ Análise de produtos vs itens detalhada
✅ Prompts otimizados para cada modelo
✅ Cenários de teste variados (muito específicos, genéricos, incompatíveis)
✅ Métricas de performance (tempo + acurácia)
"""

import os
import sys
import json
import time
import logging
import asyncio
import psycopg2
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 🔧 CONFIGURAÇÃO DO AMBIENTE
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
load_dotenv('config.env')

# ⚠️  IMPORT DIRETO PARA EVITAR PROBLEMAS DE DEPENDÊNCIA
import aiohttp
import json as json_lib
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Resultado da validação LLM"""
    approved: bool
    reasoning: str
    confidence: float = 0.0

class SimpleOllamaValidator:
    """🔬 Validador OLLAMA simplificado para testes"""
    
    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
    
    def _build_optimized_prompt(self, empresa_nome: str, empresa_descricao: str, 
                              licitacao_objeto: str, similarity_score: float,
                              licitacao_itens: list = None, empresa_produtos: list = None) -> str:
        """🚀 Prompt otimizado específico para cada modelo"""
        
        # Validação robusta dos parâmetros
        if licitacao_itens is None:
            licitacao_itens = []
        if empresa_produtos is None:
            empresa_produtos = []
        
        # Converter para string se necessário
        if isinstance(licitacao_itens, str):
            try:
                licitacao_itens = json_lib.loads(licitacao_itens)
            except:
                licitacao_itens = []
        
        if isinstance(empresa_produtos, str):
            try:
                empresa_produtos = json_lib.loads(empresa_produtos)
            except:
                empresa_produtos = []
        
        # 🎯 PROMPT ESPECÍFICO POR MODELO
        if "qwen" in self.model_name.lower():
            return self._qwen_prompt(empresa_nome, empresa_descricao, licitacao_objeto, 
                                   similarity_score, licitacao_itens, empresa_produtos)
        elif "llama" in self.model_name.lower():
            return self._llama_prompt(empresa_nome, empresa_descricao, licitacao_objeto,
                                    similarity_score, licitacao_itens, empresa_produtos)
        else:
            return self._default_prompt(empresa_nome, empresa_descricao, licitacao_objeto,
                                      similarity_score, licitacao_itens, empresa_produtos)
    
    def _qwen_prompt(self, empresa_nome: str, empresa_descricao: str, licitacao_objeto: str,
                     similarity_score: float, licitacao_itens: list, empresa_produtos: list) -> str:
        """⚡ PROMPT OTIMIZADO PARA QWEN2.5 - FOCO NA VELOCIDADE"""
        
        itens_str = ""
        if licitacao_itens:
            itens_resumo = []
            for item in licitacao_itens[:3]:  # Máximo 3 itens para velocidade
                if isinstance(item, dict):
                    desc = item.get('descricao', '')
                    itens_resumo.append(f"• {desc}")
            if itens_resumo:
                itens_str = f"\nItens principais:\n" + "\n".join(itens_resumo)
        
        produtos_str = ""
        if empresa_produtos:
            produtos_resumo = empresa_produtos[:5]  # Máximo 5 produtos
            produtos_str = f"\nProdutos/serviços: {', '.join(produtos_resumo)}"
        
        return f"""🎯 ANÁLISE RÁPIDA DE COMPATIBILIDADE

EMPRESA: {empresa_nome}
Descrição: {empresa_descricao}{produtos_str}

LICITAÇÃO: {licitacao_objeto}{itens_str}

Score de similaridade: {similarity_score:.2f}

TAREFA: Avaliar se a empresa pode fornecer o que a licitação solicita.

CRITÉRIOS DIRETOS:
✅ APROVAR se: produtos/serviços da empresa atendem diretamente aos itens
❌ REJEITAR se: incompatibilidade clara ou falta de especificidade

RESPOSTA (JSON):
{{"approved": true/false, "reasoning": "explicação objetiva em 1-2 frases"}}"""
    
    def _llama_prompt(self, empresa_nome: str, empresa_descricao: str, licitacao_objeto: str,
                      similarity_score: float, licitacao_itens: list, empresa_produtos: list) -> str:
        """🧠 PROMPT OTIMIZADO PARA LLAMA3.2 - FOCO NA REFLEXÃO E CRITÉRIO"""
        
        itens_str = ""
        if licitacao_itens:
            itens_detalhados = []
            for item in licitacao_itens:
                if isinstance(item, dict):
                    desc = item.get('descricao', '')
                    qtd = item.get('quantidade', '')
                    unidade = item.get('unidade_medida', '')
                    itens_detalhados.append(f"• {desc} ({qtd} {unidade})")
            if itens_detalhados:
                itens_str = f"\n\nItens detalhados da licitação:\n" + "\n".join(itens_detalhados)
        
        produtos_str = ""
        if empresa_produtos:
            produtos_str = f"\n\nProdutos/serviços oferecidos pela empresa:\n• " + "\n• ".join(empresa_produtos)
        
        return f"""🔍 ANÁLISE CRITERIOSA DE COMPATIBILIDADE PARA LICITAÇÃO

DADOS DA EMPRESA:
Nome: {empresa_nome}
Descrição: {empresa_descricao}{produtos_str}

DADOS DA LICITAÇÃO:
Objeto: {licitacao_objeto}{itens_str}

Score de similaridade inicial: {similarity_score:.2f}

🧠 PROCESSO DE ANÁLISE REFLEXIVA:

1️⃣ PRIMEIRO: Analise se os produtos/serviços da empresa têm RELAÇÃO DIRETA com os itens solicitados.

2️⃣ SEGUNDO: Considere se a empresa tem CAPACIDADE TÉCNICA para fornecer especificamente o que é pedido.

3️⃣ TERCEIRO: Avalie se existe COMPATIBILIDADE SETORIAL real (não apenas palavras genéricas).

4️⃣ QUARTO: QUESTIONE-SE: "Essa empresa realmente pode cumprir este contrato específico?"

5️⃣ DECISÃO FINAL: 
- APROVADO apenas se houver compatibilidade clara e específica
- REJEITADO se houver dúvidas ou incompatibilidade

🚨 ATENÇÃO: Seja RIGOROSO. Evite aprovações por similaridade superficial.

RESPOSTA OBRIGATÓRIA (JSON):
{{"approved": true/false, "reasoning": "explicação detalhada do raciocínio em 2-3 frases"}}"""
    
    def _default_prompt(self, empresa_nome: str, empresa_descricao: str, licitacao_objeto: str,
                       similarity_score: float, licitacao_itens: list, empresa_produtos: list) -> str:
        """📝 Prompt padrão para outros modelos"""
        return f"""Analise a compatibilidade entre a empresa e a licitação.

EMPRESA: {empresa_nome}
DESCRIÇÃO: {empresa_descricao}
PRODUTOS: {empresa_produtos}

LICITAÇÃO: {licitacao_objeto}
ITENS: {licitacao_itens}

Responda apenas em JSON: {{"approved": true/false, "reasoning": "explicação"}}"""
    
    async def validate_match(self, empresa_nome: str, empresa_descricao: str,
                           licitacao_objeto: str, similarity_score: float,
                           licitacao_itens: list = None, empresa_produtos: list = None) -> ValidationResult:
        """🔍 Validar match usando OLLAMA"""
        
        prompt = self._build_optimized_prompt(
            empresa_nome, empresa_descricao, licitacao_objeto,
            similarity_score, licitacao_itens, empresa_produtos
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 200
                    }
                }
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        return ValidationResult(False, f"Erro HTTP {response.status}", 0.0)
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    # Tentar extrair JSON da resposta
                    try:
                        # Buscar JSON na resposta
                        start_idx = response_text.find('{')
                        end_idx = response_text.rfind('}') + 1
                        
                        if start_idx >= 0 and end_idx > start_idx:
                            json_str = response_text[start_idx:end_idx]
                            parsed = json_lib.loads(json_str)
                            
                            approved = parsed.get('approved', False)
                            reasoning = parsed.get('reasoning', 'Sem explicação fornecida')
                            
                            return ValidationResult(approved, reasoning, 0.8)
                        else:
                            # Fallback: tentar interpretar texto
                            approved = any(word in response_text.lower() for word in ['true', 'aprovado', 'sim', 'yes'])
                            return ValidationResult(approved, response_text[:200], 0.5)
                            
                    except json_lib.JSONDecodeError:
                        # Fallback para análise de texto
                        approved = any(word in response_text.lower() for word in ['true', 'aprovado', 'sim'])
                        return ValidationResult(approved, response_text[:200], 0.3)
                        
        except Exception as e:
            return ValidationResult(False, f"Erro na validação: {str(e)}", 0.0)

class EnhancedRealDataLLMTester:
    """🔬 Testador avançado com dados reais do Supabase"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.validators = {}
        
        # 🎯 MODELOS A TESTAR
        self.models_to_test = [
            'qwen2.5:7b',  # Mais rápido com prompts otimizados
            'llama3.2'     # Mais criterioso com reflexão
        ]
        
        self.results = {
            'test_start_time': time.time(),
            'models_tested': {},
            'summary': {}
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Configurar logging detalhado"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('test_real_data_llm.log')
            ]
        )
        return logging.getLogger(__name__)

    def get_db_connection(self):
        """🔗 Conectar ao Supabase usando DATABASE_URL"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise ValueError("DATABASE_URL não encontrada no ambiente")
            
            self.logger.info(f"🔗 Conectando ao banco: {database_url[:30]}...")
            conn = psycopg2.connect(database_url)
            self.logger.info("✅ Conexão estabelecida com sucesso")
            return conn
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conexão: {e}")
            raise
    
    def fetch_real_licitacoes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """🏛️ Buscar licitações reais com mais variedade"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 🔥 BUSCA SIMPLIFICADA - Apenas dados essenciais
            query = """
                SELECT 
                    pncp_id,
                    objeto_compra
                FROM licitacoes 
                WHERE objeto_compra IS NOT NULL 
                    AND LENGTH(objeto_compra) > 50
                    AND (
                        objeto_compra ILIKE '%equipamento%' OR
                        objeto_compra ILIKE '%software%' OR
                        objeto_compra ILIKE '%medicamento%' OR
                        objeto_compra ILIKE '%combustível%' OR
                        objeto_compra ILIKE '%limpeza%' OR
                        objeto_compra ILIKE '%material%' OR
                        objeto_compra ILIKE '%serviço%' OR
                        objeto_compra ILIKE '%água%' OR
                        objeto_compra ILIKE '%escritório%' OR
                        objeto_compra ILIKE '%veículo%'
                    )
                ORDER BY RANDOM()
                LIMIT %s;
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            licitacoes = []
            for row in results:
                licitacao_base = {
                    'pncp_id': row[0],
                    'objeto_compra': row[1],
                    'situacao_compra_nome': 'Em andamento',  # Valor padrão
                    'itens': []
                }
                
                # 🔍 BUSCAR ITENS SEPARADAMENTE PARA ESTA LICITAÇÃO
                itens_query = """
                    SELECT 
                        li.numero_item,
                        li.descricao,
                        li.quantidade,
                        li.valor_unitario_estimado,
                        li.unidade_medida
                    FROM licitacao_itens li
                    INNER JOIN licitacoes l ON l.id = li.licitacao_id
                    WHERE l.pncp_id = %s
                    ORDER BY li.numero_item
                    LIMIT 5;
                """
                
                cursor.execute(itens_query, (row[0],))
                itens_results = cursor.fetchall()
                
                itens = []
                for item_row in itens_results:
                    item = {
                        'numero_item': item_row[0],
                        'descricao': item_row[1],
                        'quantidade': item_row[2],
                        'valor_unitario_estimado': item_row[3],
                        'unidade_medida': item_row[4]
                    }
                    itens.append(item)
                
                licitacao_base['itens'] = itens
                licitacoes.append(licitacao_base)
            
            cursor.close()
            conn.close()
            
            self.logger.info(f"📋 Buscadas {len(licitacoes)} licitações do Supabase")
            return licitacoes
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar licitações: {e}")
            return []

    def fetch_real_empresas(self, limit: int = 8) -> List[Dict[str, Any]]:
        """🏢 Buscar empresas reais com mais diversidade"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 🔥 BUSCA EXPANDIDA - Empresas de setores bem diversos
            query = """
                SELECT 
                    nome_fantasia,
                    descricao_servicos_produtos,
                    produtos
                FROM empresas 
                WHERE descricao_servicos_produtos IS NOT NULL 
                    AND LENGTH(descricao_servicos_produtos) > 20
                    AND produtos IS NOT NULL 
                    AND jsonb_array_length(produtos) > 0
                ORDER BY RANDOM()
                LIMIT %s;
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            empresas = []
            for row in results:
                empresa = {
                    'nome_fantasia': row[0],
                    'descricao_servicos_produtos': row[1],
                    'produtos': row[2] if row[2] else []
                }
                empresas.append(empresa)
            
            cursor.close()
            conn.close()
            
            self.logger.info(f"🏢 Buscadas {len(empresas)} empresas do Supabase")
            return empresas
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao buscar empresas: {e}")
            return []

    def create_test_scenarios(self, licitacoes: List[Dict], empresas: List[Dict]) -> List[Dict]:
        """🎯 Criar cenários de teste mais inteligentes e variados"""
        scenarios = []
        scenario_id = 1
        
        # 📊 ANÁLISE INTELIGENTE PARA CRIAR CENÁRIOS DIVERSOS
        self.logger.info("🧠 Analisando dados para criar cenários de teste...")
        
        for licitacao in licitacoes:
            for empresa in empresas:
                
                # 🎯 CATEGORIZAÇÃO INTELIGENTE
                objeto_lower = licitacao['objeto_compra'].lower()
                empresa_desc_lower = empresa['descricao_servicos_produtos'].lower()
                produtos_texto = ' '.join(empresa['produtos']).lower() if empresa['produtos'] else ''
                
                # 🔍 DETECÇÃO DE COMPATIBILIDADE
                match_type = self._detect_match_type(objeto_lower, empresa_desc_lower, produtos_texto)
                expected_result = self._determine_expected_result(match_type, objeto_lower, empresa_desc_lower, produtos_texto)
                
                scenario = {
                    'id': scenario_id,
                    'match_type': match_type,
                    'expected_result': expected_result,
                    'confidence': self._calculate_confidence(match_type),
                    'empresa_nome': empresa['nome_fantasia'],
                    'empresa_descricao': empresa['descricao_servicos_produtos'],
                    'empresa_produtos': empresa['produtos'],
                    'licitacao_objeto': licitacao['objeto_compra'],
                    'licitacao_itens': licitacao['itens'],
                    'similarity_score': 0.85,  # Score alto para forçar validação LLM
                    'description': self._generate_scenario_description(match_type, empresa['nome_fantasia'], licitacao['objeto_compra'])
                }
                
                scenarios.append(scenario)
                scenario_id += 1
        
        self.logger.info(f"🎯 Criados {len(scenarios)} cenários de teste")
        return scenarios

    def _detect_match_type(self, objeto: str, empresa_desc: str, produtos: str) -> str:
        """🔍 Detectar tipo de compatibilidade"""
        
        # 🎯 ALTA COMPATIBILIDADE
        high_match_keywords = {
            'medicamento': ['medicamento', 'farmac', 'saúde', 'hospital'],
            'software': ['software', 'sistema', 'tecnologia', 'informática', 'ti'],
            'equipamento': ['equipamento', 'máquina', 'ferramenta', 'aparelho'],
            'combustível': ['combustível', 'gasolina', 'diesel', 'posto'],
            'limpeza': ['limpeza', 'higiene', 'detergente', 'produto de limpeza'],
            'escritório': ['escritório', 'papelaria', 'material escolar'],
            'veículo': ['veículo', 'carro', 'caminhão', 'transporte'],
            'água': ['água', 'mineral', 'bebida']
        }
        
        for categoria, keywords in high_match_keywords.items():
            if any(keyword in objeto for keyword in keywords):
                if any(keyword in empresa_desc or keyword in produtos for keyword in keywords):
                    return 'highly_compatible'
        
        # 🎯 COMPATIBILIDADE GENÉRICA
        generic_keywords = ['material', 'produto', 'serviço', 'fornecimento', 'aquisição']
        if any(keyword in objeto for keyword in generic_keywords):
            return 'generic_compatible'
        
        # 🎯 INCOMPATÍVEL
        return 'incompatible'

    def _determine_expected_result(self, match_type: str, objeto: str, empresa_desc: str, produtos: str) -> str:
        """🎯 Determinar resultado esperado"""
        if match_type == 'highly_compatible':
            return 'APROVADO'
        elif match_type == 'generic_compatible':
            # Análise mais detalhada para genéricos
            if any(word in empresa_desc for word in ['diversos', 'geral', 'variados']):
                return 'APROVADO'
            return 'REJEITADO'
        else:
            return 'REJEITADO'

    def _calculate_confidence(self, match_type: str) -> float:
        """📊 Calcular confiança na predição"""
        confidence_map = {
            'highly_compatible': 0.9,
            'generic_compatible': 0.6,
            'incompatible': 0.95
        }
        return confidence_map.get(match_type, 0.5)

    def _generate_scenario_description(self, match_type: str, empresa: str, licitacao: str) -> str:
        """📝 Gerar descrição do cenário"""
        descriptions = {
            'highly_compatible': f"✅ MATCH ESPERADO: {empresa} vs {licitacao[:50]}...",
            'generic_compatible': f"❓ GENÉRICO: {empresa} vs {licitacao[:50]}...",
            'incompatible': f"❌ INCOMPATÍVEL: {empresa} vs {licitacao[:50]}..."
        }
        return descriptions.get(match_type, f"Teste: {empresa} vs {licitacao[:50]}...")

    async def test_model_performance(self, model_name: str, scenarios: List[Dict]) -> Dict:
        """🚀 Testar performance de um modelo específico"""
        self.logger.info(f"\n🚀 TESTANDO MODELO: {model_name}")
        self.logger.info("=" * 60)
        
        try:
            # 🏗️ INICIALIZAR VALIDADOR SIMPLIFICADO
            validator = SimpleOllamaValidator(model_name)
            self.logger.info(f"🔧 Modelo configurado: {model_name}")
            
            results = {
                'model_name': model_name,
                'total_tests': len(scenarios),
                'correct_predictions': 0,
                'incorrect_predictions': 0,
                'total_time': 0.0,
                'average_time': 0.0,
                'test_details': [],
                'performance_summary': {}
            }
            
            # 🎯 EXECUTAR TESTES
            for i, scenario in enumerate(scenarios):
                self.logger.info(f"\n📝 TESTE {i+1}/{len(scenarios)}: {scenario['description']}")
                
                start_time = time.time()
                
                try:
                    # 🔍 EXECUTAR VALIDAÇÃO
                    resultado = await validator.validate_match(
                        empresa_nome=scenario['empresa_nome'],
                        empresa_descricao=scenario['empresa_descricao'],
                        licitacao_objeto=scenario['licitacao_objeto'],
                        similarity_score=scenario['similarity_score'],
                        licitacao_itens=scenario['licitacao_itens'],
                        empresa_produtos=scenario['empresa_produtos']
                    )
                    
                    end_time = time.time()
                    test_time = end_time - start_time
                    
                    # 📊 ANALISAR RESULTADO
                    is_correct = resultado.approved == (scenario['expected_result'] == 'APROVADO')
                    
                    if is_correct:
                        results['correct_predictions'] += 1
                        status = "✅ CORRETO"
                    else:
                        results['incorrect_predictions'] += 1
                        status = "❌ INCORRETO"
                    
                    # 📋 REGISTRAR DETALHES
                    test_detail = {
                        'scenario_id': scenario['id'],
                        'expected': scenario['expected_result'],
                        'actual': 'APROVADO' if resultado.approved else 'REJEITADO',
                        'correct': is_correct,
                        'time_seconds': round(test_time, 2),
                        'confidence': scenario['confidence'],
                        'reasoning': resultado.reasoning[:200] + "..." if len(resultado.reasoning) > 200 else resultado.reasoning
                    }
                    
                    results['test_details'].append(test_detail)
                    results['total_time'] += test_time
                    
                    # 📊 LOG DO RESULTADO
                    self.logger.info(f"   {status} | Tempo: {test_time:.2f}s | Esperado: {scenario['expected_result']} | Obtido: {'APROVADO' if resultado.approved else 'REJEITADO'}")
                    self.logger.info(f"   💭 Raciocínio: {resultado.reasoning[:100]}...")
                    
                except Exception as e:
                    self.logger.error(f"   ❌ Erro no teste: {e}")
                    test_detail = {
                        'scenario_id': scenario['id'],
                        'expected': scenario['expected_result'],
                        'actual': 'ERRO',
                        'correct': False,
                        'time_seconds': 0,
                        'error': str(e)
                    }
                    results['test_details'].append(test_detail)
                    results['incorrect_predictions'] += 1
            
            # 📊 CALCULAR MÉTRICAS FINAIS
            results['average_time'] = results['total_time'] / len(scenarios) if scenarios else 0
            results['accuracy'] = results['correct_predictions'] / len(scenarios) if scenarios else 0
            
            # 📈 RESUMO DE PERFORMANCE
            results['performance_summary'] = {
                'accuracy_percentage': round(results['accuracy'] * 100, 1),
                'total_time_minutes': round(results['total_time'] / 60, 2),
                'avg_time_per_test': round(results['average_time'], 2),
                'tests_per_minute': round(60 / results['average_time'], 1) if results['average_time'] > 0 else 0
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erro geral no teste do modelo {model_name}: {e}")
            return {'error': str(e)}

    def print_comprehensive_report(self, all_results: Dict):
        """📊 Relatório detalhado de todos os testes"""
        print("\n" + "=" * 80)
        print("🎯 RELATÓRIO DETALHADO DE TESTES LLM COM DADOS REAIS")
        print("=" * 80)
        
        print(f"\n⏰ Tempo total dos testes: {time.time() - self.results['test_start_time']:.1f}s")
        print(f"📋 Total de cenários testados: {len(all_results.get(list(all_results.keys())[0], {}).get('test_details', []))}")
        
        # 📊 COMPARAÇÃO ENTRE MODELOS
        print(f"\n{'='*50}")
        print("📊 COMPARAÇÃO DE PERFORMANCE ENTRE MODELOS")
        print(f"{'='*50}")
        
        comparison_data = []
        for model_name, results in all_results.items():
            if 'performance_summary' in results:
                summary = results['performance_summary']
                comparison_data.append({
                    'model': model_name,
                    'accuracy': summary['accuracy_percentage'],
                    'avg_time': summary['avg_time_per_test'],
                    'tests_per_min': summary['tests_per_minute']
                })
        
        # 🏆 RANKING POR ACURÁCIA
        comparison_data.sort(key=lambda x: x['accuracy'], reverse=True)
        
        print(f"\n🏆 RANKING POR ACURÁCIA:")
        print(f"{'Modelo':<15} {'Acurácia':<10} {'Tempo/Teste':<12} {'Testes/Min':<12}")
        print("-" * 55)
        
        for i, data in enumerate(comparison_data):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(f"{medal} {data['model']:<13} {data['accuracy']:<9.1f}% {data['avg_time']:<11.2f}s {data['tests_per_min']:<11.1f}")
        
        # ⚡ RANKING POR VELOCIDADE
        comparison_data.sort(key=lambda x: x['avg_time'])
        
        print(f"\n⚡ RANKING POR VELOCIDADE:")
        print(f"{'Modelo':<15} {'Tempo/Teste':<12} {'Testes/Min':<12} {'Acurácia':<10}")
        print("-" * 55)
        
        for i, data in enumerate(comparison_data):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            print(f"{medal} {data['model']:<13} {data['avg_time']:<11.2f}s {data['tests_per_min']:<11.1f} {data['accuracy']:<9.1f}%")
        
        # 📈 DETALHES POR MODELO
        for model_name, results in all_results.items():
            if 'error' in results:
                print(f"\n❌ ERRO NO MODELO {model_name}: {results['error']}")
                continue
                
            summary = results['performance_summary']
            
            print(f"\n{'='*60}")
            print(f"📋 DETALHES - {model_name.upper()}")
            print(f"{'='*60}")
            
            print(f"✅ Acertos: {results['correct_predictions']}/{results['total_tests']} ({summary['accuracy_percentage']}%)")
            print(f"❌ Erros: {results['incorrect_predictions']}/{results['total_tests']}")
            print(f"⏱️  Tempo total: {summary['total_time_minutes']} min")
            print(f"⚡ Tempo médio por teste: {summary['avg_time_per_test']}s")
            print(f"🚀 Testes por minuto: {summary['tests_per_minute']}")
            
            # 🔍 ANÁLISE DE ERROS
            errors = [detail for detail in results['test_details'] if not detail['correct']]
            if errors:
                print(f"\n🔍 ANÁLISE DE ERROS ({len(errors)} casos):")
                for error in errors[:3]:  # Mostrar apenas os primeiros 3
                    print(f"   • Esperado: {error['expected']} | Obtido: {error['actual']}")
                    if 'reasoning' in error:
                        print(f"     Raciocínio: {error['reasoning'][:80]}...")

        # 🎯 RECOMENDAÇÕES FINAIS
        print(f"\n{'='*60}")
        print("🎯 RECOMENDAÇÕES E CONCLUSÕES")
        print(f"{'='*60}")
        
        best_accuracy = max((data['accuracy'] for data in comparison_data), default=0)
        fastest_model = min(comparison_data, key=lambda x: x['avg_time'])['model'] if comparison_data else "N/A"
        most_accurate = max(comparison_data, key=lambda x: x['accuracy'])['model'] if comparison_data else "N/A"
        
        print(f"\n🏆 Modelo mais preciso: {most_accurate} ({best_accuracy:.1f}% acurácia)")
        print(f"⚡ Modelo mais rápido: {fastest_model}")
        
        if best_accuracy >= 80:
            print("\n✅ RESULTADO POSITIVO: Pelo menos um modelo atingiu boa acurácia (≥80%)")
        else:
            print("\n⚠️  ATENÇÃO: Nenhum modelo atingiu acurácia satisfatória (≥80%)")
            print("   Considere ajustar prompts ou testar outros modelos.")
        
        # 💡 RECOMENDAÇÃO DE USO
        balanced_scores = []
        for data in comparison_data:
            # Score balanceado: acurácia ponderada por velocidade
            balanced_score = data['accuracy'] * (60 / data['avg_time']) if data['avg_time'] > 0 else 0
            balanced_scores.append((data['model'], balanced_score, data['accuracy'], data['avg_time']))
        
        best_balanced = max(balanced_scores, key=lambda x: x[1]) if balanced_scores else None
        
        if best_balanced:
            print(f"\n💡 RECOMENDAÇÃO PARA PRODUÇÃO:")
            print(f"   Modelo: {best_balanced[0]}")
            print(f"   Justificativa: Melhor equilíbrio entre acurácia ({best_balanced[2]:.1f}%) e velocidade ({best_balanced[3]:.1f}s)")

    async def run_comprehensive_tests(self):
        """🎯 Executar bateria completa de testes"""
        try:
            self.logger.info("🚀 INICIANDO TESTES EXPANDIDOS DE VALIDAÇÃO LLM")
            self.logger.info("=" * 80)
            
            # 📊 BUSCAR DADOS REAIS
            self.logger.info("📊 Buscando dados reais do Supabase...")
            licitacoes = self.fetch_real_licitacoes(limit=10)  # Mais licitações
            empresas = self.fetch_real_empresas(limit=8)       # Mais empresas
            
            if not licitacoes or not empresas:
                self.logger.error("❌ Não foi possível buscar dados suficientes")
                return
            
            # 🎯 CRIAR CENÁRIOS DE TESTE
            scenarios = self.create_test_scenarios(licitacoes, empresas)
            
            if not scenarios:
                self.logger.error("❌ Nenhum cenário de teste foi criado")
                return
            
            # 📊 RESUMO PRÉ-TESTE
            self.logger.info(f"📋 Dados coletados:")
            self.logger.info(f"   • {len(licitacoes)} licitações")
            self.logger.info(f"   • {len(empresas)} empresas") 
            self.logger.info(f"   • {len(scenarios)} cenários de teste")
            
            # 🚀 TESTAR CADA MODELO
            all_results = {}
            
            for model_name in self.models_to_test:
                try:
                    self.logger.info(f"\n🎯 Iniciando testes com {model_name}...")
                    results = await self.test_model_performance(model_name, scenarios)
                    all_results[model_name] = results
                    
                except Exception as e:
                    self.logger.error(f"❌ Erro ao testar {model_name}: {e}")
                    all_results[model_name] = {'error': str(e)}
            
            # 📊 RELATÓRIO FINAL DETALHADO
            self.print_comprehensive_report(all_results)
            
            # 💾 SALVAR RESULTADOS
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"test_results_expanded_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': timestamp,
                    'test_config': {
                        'models_tested': self.models_to_test,
                        'total_scenarios': len(scenarios),
                        'licitacoes_count': len(licitacoes),
                        'empresas_count': len(empresas)
                    },
                    'results': all_results,
                    'scenarios': scenarios
                }, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"\n💾 Resultados salvos em: {filename}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro geral nos testes: {e}")
            raise

if __name__ == "__main__":
    print("🔬 TESTE EXPANDIDO DE VALIDAÇÃO LLM COM DADOS REAIS")
    print("=" * 60)
    print("🎯 Testando modelos OLLAMA com prompts otimizados")
    print("📊 Usando dados reais do Supabase")
    print("=" * 60)
    
    tester = EnhancedRealDataLLMTester()
    asyncio.run(tester.run_comprehensive_tests()) 