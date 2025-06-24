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
load_dotenv('config.env')

# Importações do projeto
from src.matching.ollama_match_validator import OllamaMatchValidator
from src.matching.llm_config import LLMValidatorFactory

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
            
            # 🔥 BUSCA EXPANDIDA - Mais licitações de setores variados
            query = """
                SELECT DISTINCT
                    l.pncp_id,
                    l.objeto_compra,
                    l.situacao_compra_nome,
                    COALESCE(
                        CASE 
                            WHEN COUNT(li.id) > 0 
                            THEN json_agg(
                                json_build_object(
                                    'numero_item', li.numero_item,
                                    'descricao', li.descricao,
                                    'quantidade', li.quantidade,
                                    'valor_unitario_estimado', li.valor_unitario_estimado,
                                    'unidade_medida', li.unidade_medida
                                ) ORDER BY li.numero_item
                            )
                            ELSE '[]'::json
                        END, '[]'::json
                    ) as itens
                FROM licitacoes l
                LEFT JOIN licitacao_itens li ON l.id = li.licitacao_id
                WHERE l.objeto_compra IS NOT NULL 
                    AND LENGTH(l.objeto_compra) > 50
                    AND (
                        l.objeto_compra ILIKE '%equipamento%' OR
                        l.objeto_compra ILIKE '%software%' OR
                        l.objeto_compra ILIKE '%medicamento%' OR
                        l.objeto_compra ILIKE '%combustível%' OR
                        l.objeto_compra ILIKE '%limpeza%' OR
                        l.objeto_compra ILIKE '%material%' OR
                        l.objeto_compra ILIKE '%serviço%' OR
                        l.objeto_compra ILIKE '%água%' OR
                        l.objeto_compra ILIKE '%escritório%' OR
                        l.objeto_compra ILIKE '%veículo%'
                    )
                GROUP BY l.pncp_id, l.objeto_compra, l.situacao_compra_nome
                ORDER BY RANDOM()
                LIMIT %s;
            """
            
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            licitacoes = []
            for row in results:
                licitacao = {
                    'pncp_id': row[0],
                    'objeto_compra': row[1],
                    'situacao_compra_nome': row[2] or 'Em andamento',
                    'itens': row[3] if row[3] else []
                }
                licitacoes.append(licitacao)
            
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
            # 🏗️ INICIALIZAR VALIDADOR
            factory = LLMValidatorFactory()
            validator = factory.get_validator()
            
            if not isinstance(validator, OllamaMatchValidator):
                self.logger.error(f"❌ Esperado OllamaMatchValidator, got {type(validator)}")
                return {'error': 'Invalid validator type'}
            
            # 🔧 CONFIGURAR MODELO
            validator.model_name = model_name
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