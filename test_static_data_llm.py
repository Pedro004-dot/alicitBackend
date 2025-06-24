#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import statistics

# Configurações OLLAMA
OLLAMA_BASE_URL = "http://localhost:11434"

# Dados estáticos das licitações (primeiras 50)
LICITACOES_DATA = [
    {
        "pncp_id": "09012493000154-1-000100/2025",
        "objeto_compra": "Fornecimento de produtos gêneros alimentícios - SECOS, destinados a suprir as necessidades dos Serviços e Programas da Secretaria Municipal de Assistência Social",
        "itens": [
            {"descricao": "ACHOCOLATADO EM PÓ VITAMINADO- EMBALAGEM DE 400G", "quantidade": "1560.000", "unidade": "UND"},
            {"descricao": "AÇÚCAR, TIPO CRISTAL, COMPOSIÇÃO ORIGEM VEGETAL, SACAROSE DE CANA DE AÇÚCAR BRANCO PACOTE 1KG", "quantidade": "1560.000", "unidade": "KG"},
            {"descricao": "ADOÇANTE LÍQUIDO, TIPO SACARINA, PRIMEIRA QUALIDADE, COM 100 ML", "quantidade": "20.000", "unidade": "UND"}
        ]
    },
    {
        "pncp_id": "30957190000109-1-000016/2025",
        "objeto_compra": "Contratação De Empresa Para Fornecimento De Material Didático Para Atender As Necessidades Da Secretaria De Educação E Demais Unidades Escolares Da Rede Pública Municipal De Lagoa Do Carro/PE.",
        "itens": [
            {"descricao": "Papel crepom", "quantidade": "300.000", "unidade": "Unidade"},
            {"descricao": "Papel correspondência", "quantidade": "50.000", "unidade": "Unidade"},
            {"descricao": "Cartolina", "quantidade": "50.000", "unidade": "Unidade"}
        ]
    },
    {
        "pncp_id": "00509968000148-1-001718/2025",
        "objeto_compra": "Prestação de serviços de execução de projeto executivo de instalação de sistema central de ar condicionado.",
        "itens": [
            {"descricao": "Manutenção / Reforma Predial", "quantidade": "1.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "46482832000192-1-000171/2025",
        "objeto_compra": "FORNECIMENTO DE KIT MATERNIDADE PARA FORNECIMENTO AS PARTURIENTES DO HOSPITAL DE CLINICAS DE SAO SEBASTIAO E HOSPITAL DE CLINICAS DA COSTA SUL.",
        "itens": [
            {"descricao": "BANHEIRA PARA BEBE EM PLASTICO RESISTENTE E ATOXICO", "quantidade": "1500.000", "unidade": "UNIDADE"},
            {"descricao": "COBERTOR INFANTIL", "quantidade": "1500.000", "unidade": "UNIDADE"},
            {"descricao": "FRONHA PARA TRAVESSEIRO DE BEBE", "quantidade": "1500.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "42441758000105-1-000039/2025",
        "objeto_compra": "Aquisição, por Sistema de Registro de Preços, de materiais para Manutenção Predial, nos termos do edital e seus anexos.",
        "itens": [
            {"descricao": "Cadeado", "quantidade": "351.000", "unidade": "Unidade"},
            {"descricao": "Lixa", "quantidade": "380.000", "unidade": "Unidade"},
            {"descricao": "Porta", "quantidade": "52.000", "unidade": "Unidade"}
        ]
    }
]

# Dados estáticos das empresas
EMPRESAS_DATA = [
    {
        "nome_fantasia": "InfinitiFy",
        "descricao_servicos_produtos": "Empresa especialista no fornecimento de softwares, sistemas de redes, banco de dados, inteligencia artificial.",
        "produtos": ["Software", "Sistemas"]
    },
    {
        "nome_fantasia": "locação de caminhões",
        "descricao_servicos_produtos": "locação de caminhões",
        "produtos": ["locação de caminhões", "caminhões basculantes", "caminhão pipa", "caminhão traçado", "caminhão prancha", "caminhão munck", "locação de caminhão munck"]
    },
    {
        "nome_fantasia": "MelBrás",
        "descricao_servicos_produtos": "Empresa fornecedora de mel",
        "produtos": ["Mel", "MEL", "Melado"]
    },
    {
        "nome_fantasia": "Coleta de lixo",
        "descricao_servicos_produtos": "Coleta de lixo e varricao publica",
        "produtos": ["Caminhao compactador de lixo urbano", "caminhao de lixo", "caminhao basculante", "varredeira mecanica", "lixeiras publicas", "coletor seletivo", "carrinhos coletores", "sacos de lixo", "servico de coleta e transporte de residuos solidos", "residuos hospitalares", "operacao de aterros sanitarios", "aterros sanitarios", "transbordo", "ecopontos"]
    },
    {
        "nome_fantasia": "Ontrack",
        "descricao_servicos_produtos": "Agencia de markenting, especialista em publicidade , propagandas , folders, painéis",
        "produtos": ["Propagandas", "Markenting"]
    },
    {
        "nome_fantasia": "Atn",
        "descricao_servicos_produtos": "empresa especializada em serviços de construção civil como recapeamento e terraplanagem",
        "produtos": ["recapeamento de asfalto", "asfalto", "tapa-buraco", "terraplanagem"]
    },
    {
        "nome_fantasia": "distribuição",
        "descricao_servicos_produtos": "comercio varejista de agua",
        "produtos": ["água", "galão de água"]
    },
    {
        "nome_fantasia": "AgroFrare",
        "descricao_servicos_produtos": "Somos uma empresa especializada em soluções para o agronegócio, oferecendo consultoria agronômica estratégica, assistência técnica qualificada e a distribuição de insumos agrícolas, incluindo produtos biológicos e fertilizantes foliares. Atendemos órgãos públicos com eficiência e responsabilidade, promovendo práticas sustentáveis e alto desempenho produtivo no campo.",
        "produtos": ["Biologicos", "Adubos", "Assistencia técnica", "Foliar"]
    },
    {
        "nome_fantasia": "DBN serviços",
        "descricao_servicos_produtos": "montagem de palcos",
        "produtos": ["locação de palcos", "montagem de palcos", "sonorização", "iluminação", "sistemas de som", "gradil"]
    },
    {
        "nome_fantasia": "Materias de escritorio",
        "descricao_servicos_produtos": "Varejo e distribuicao de itens de escritorio",
        "produtos": ["escritorio", "caneta", "papel", "copos", "filtro de cafe", "cadeiras", "mesas", "grampeador", "pastas", "lapis", "borrachas", "reguas", "Agendas", "Papel timbrado", "Caixas organizadoras", "Ficharios", "Tesouras", "Grampos", "Fitas adesivas", "Clipes de papel"]
    },
    {
        "nome_fantasia": "Risadinha company",
        "descricao_servicos_produtos": "Distribuidora de produtos de limpeza e descartáveis",
        "produtos": ["produtos de limpeza", "Descartáveis", "luvas descartáveis", "copos descartáveis", "detergente", "álcool", "Sabão em pó", "pano de limpeza", "Multiuso", "Sabão", "pratos descartáveis", "sacos ziplock", "embalagens de isopor", "marmitex descartável", "papel toalha", "Filtro de café", "embalagens"]
    },
    {
        "nome_fantasia": "Globo esporte",
        "descricao_servicos_produtos": "Fornecimento de materiais esportivos principalmente futebol",
        "produtos": ["Bola de futebol", "Bola de basquete"]
    },
    {
        "nome_fantasia": "Clonex",
        "descricao_servicos_produtos": "Desenvolvimento de software",
        "produtos": ["software", "desenvolvimento de software", "inteligência artificial", "sistema", "algoritmo", "dados", "automatização", "Analise de dados", "sites"]
    },
    {
        "nome_fantasia": "Locacao de equipamentos",
        "descricao_servicos_produtos": "Locacao de equipamentos pesados e agricolas",
        "produtos": ["retroescavadeira", "escavadeira", "trator agricola", "Pa carregadeira frontal", "motoniveladora", "Rolo compactador", "Caminhao basculante", "perfuratriz"]
    },
    {
        "nome_fantasia": "W4Editora",
        "descricao_servicos_produtos": "Empresa fornecedora de livros didaticos",
        "produtos": ["Livros de literatura brasileira e estrangeira", "Obras de referência, dicionários e enciclopédias", "Livros Didaticos"]
    }
]

# Completar com as 50 licitações
LICITACOES_COMPLETAS = LICITACOES_DATA + [
    {
        "pncp_id": "10724903000179-1-000128/2025",
        "objeto_compra": "Contratação de Empresa Especializada para Manutenção Preventiva e Corretiva de Aparelhos de Ar Condicionado, com fornecimento de peças para o IFBAIANO Campus Itaberaba.",
        "itens": [
            {"descricao": "Manutenção de aparelhos de ar condicionado", "quantidade": "1.000", "unidade": "SERVIÇO"},
            {"descricao": "Peças para ar condicionado", "quantidade": "100.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "13717277000181-1-000004/2025",
        "objeto_compra": "AQUISIÇÃO DE ALIMENTOS PERECÍVEIS E NÃO PERECÍVEIS, PARA ATENDER ÀS DEMANDAS DA MERENDA ESCOLAR DO MUNICÍPIO DE JUSSARA/BA.",
        "itens": [
            {"descricao": "Frutas frescas", "quantidade": "500.000", "unidade": "KG"},
            {"descricao": "Leite em pó", "quantidade": "200.000", "unidade": "KG"},
            {"descricao": "Carne bovina", "quantidade": "300.000", "unidade": "KG"}
        ]
    },
    {
        "pncp_id": "15126437000305-1-001191/2025",
        "objeto_compra": "Aquisição de Material Farmacológico (Aparelho Digestório, Metabolismo, Vitaminas e Suplementos).",
        "itens": [
            {"descricao": "Medicamentos para aparelho digestório", "quantidade": "1000.000", "unidade": "UNIDADE"},
            {"descricao": "Vitaminas e suplementos", "quantidade": "500.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "07954480000179-1-008420/2025",
        "objeto_compra": "O objeto da licitação é a contratação de empresa para prestação de serviços contínuos a serem executados com dedicação exclusiva de mão de obra terceirizada, regidos pela Consolidação da Leis Trabalhistas (CLT).",
        "itens": [
            {"descricao": "Serviços de limpeza", "quantidade": "12.000", "unidade": "MÊS"},
            {"descricao": "Serviços de segurança", "quantidade": "12.000", "unidade": "MÊS"}
        ]
    },
    {
        "pncp_id": "88830609000139-1-000401/2025",
        "objeto_compra": "Fornecimento e garantia de materiais de expediente (baterias, pilhas, calculadora e dispositivos de armazenamentos de dados).",
        "itens": [
            {"descricao": "Baterias AA", "quantidade": "1000.000", "unidade": "UNIDADE"},
            {"descricao": "Pilhas AAA", "quantidade": "1000.000", "unidade": "UNIDADE"},
            {"descricao": "Calculadoras", "quantidade": "50.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "03408911000140-1-000028/2025",
        "objeto_compra": "AQUISIÇÃO DE SUPRIMENTOS DE IMPRESSORAS PARA ATENDER ÀS DEMANDAS DAS SECRETARIAS MUNICIPAIS.",
        "itens": [
            {"descricao": "Cartuchos de tinta", "quantidade": "500.000", "unidade": "UNIDADE"},
            {"descricao": "Toners para impressora", "quantidade": "200.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "31073338000105-1-000004/2025",
        "objeto_compra": "Registro de preços para futura e eventual Contratação de empresa especializada para o fornecimento de Livros Didáticos de LÍNGUA INGLESA, EDUCAÇÃO FÍSICA, ÉTNICOS RACIAIS E DE EDUCAÇÃO AMBIENTAL.",
        "itens": [
            {"descricao": "Livros didáticos de língua inglesa", "quantidade": "1000.000", "unidade": "UNIDADE"},
            {"descricao": "Livros de educação física", "quantidade": "800.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "05943030000155-1-000149/2025",
        "objeto_compra": "Eventual aquisição de Insumos odontológicos, para atendimento das Unidades de Saúde da Secretaria Municipal de Saúde.",
        "itens": [
            {"descricao": "Materiais odontológicos", "quantidade": "500.000", "unidade": "UNIDADE"},
            {"descricao": "Equipamentos odontológicos", "quantidade": "50.000", "unidade": "UNIDADE"}
        ]
    },
    {
        "pncp_id": "01612574000183-1-000031/2025",
        "objeto_compra": "Contratação de empresa para prestação de serviço de internet banda larga fibra ótica para atender as necessidades da prefeitura municipal.",
        "itens": [
            {"descricao": "Serviço de internet banda larga", "quantidade": "12.000", "unidade": "MÊS"},
            {"descricao": "Instalação de fibra ótica", "quantidade": "1.000", "unidade": "SERVIÇO"}
        ]
    },
    {
        "pncp_id": "08761140000194-1-000179/2025",
        "objeto_compra": "Registro de preços para aquisição de gênero alimentício (mercearia parte 2)",
        "itens": [
            {"descricao": "Produtos de mercearia", "quantidade": "2000.000", "unidade": "KG"},
            {"descricao": "Conservas alimentícias", "quantidade": "1000.000", "unidade": "UNIDADE"}
        ]
    }
]

# Prompts otimizados para cada modelo
PROMPT_QWEN_OPTIMIZED = """Analise RAPIDAMENTE se a empresa pode executar esta licitação.

LICITAÇÃO:
Objeto: {objeto_compra}
Itens (máximo 3): {itens_limitados}

EMPRESA:
Nome: {nome_empresa}
Descrição: {descricao_empresa}
Produtos (máximo 5): {produtos_limitados}

CRITÉRIOS OBJETIVOS:
✅ APROVAR se: Produtos/serviços da empresa são compatíveis diretos com os itens da licitação
❌ REJEITAR se: Incompatível ou muito genérico

Responda APENAS em JSON:
{{"match": true/false, "motivo": "explicação em 1 linha"}}"""

PROMPT_LLAMA_RIGOROSO = """ANÁLISE RIGOROSA DE COMPATIBILIDADE - SEJA CRITERIOSO!

Processo em 5 etapas:

1) LICITAÇÃO DETALHADA:
Objeto: {objeto_compra}
Itens: {itens_detalhados}

2) EMPRESA ANALISADA:
Nome: {nome_empresa}
Descrição: {descricao_empresa}
Produtos/Serviços: {produtos_completos}

3) ANÁLISE DE CAPACIDADE TÉCNICA:
- A empresa tem produtos/serviços ESPECÍFICOS para esta demanda?
- Há compatibilidade setorial real?
- A descrição da empresa indica expertise nesta área?

4) QUESTIONAMENTO CRÍTICO:
- Essa empresa REALMENTE pode cumprir este contrato?
- Não é apenas uma correspondência superficial de palavras?
- Tem experiência comprovada no setor?

5) DECISÃO RIGOROSA:
Seja RIGOROSO. Evite aprovações superficiais.
Aprove APENAS se houver compatibilidade técnica REAL e ESPECÍFICA.

Responda em JSON:
{{"match": true/false, "raciocinio": "análise detalhada em 2-3 linhas", "confianca": "alta/média/baixa"}}"""

class OllamaValidator:
    def __init__(self, base_url=OLLAMA_BASE_URL):
        self.base_url = base_url

    async def validate_match(self, licitacao, empresa, model="qwen2.5:7b", timeout=30):
        """Valida match usando OLLAMA local"""
        start_time = time.time()
        
        try:
            # Preparar dados limitados para QWEN
            if "qwen" in model.lower():
                itens_text = "; ".join([f"{item['descricao'][:50]}..." for item in licitacao['itens'][:3]])
                produtos_text = "; ".join(empresa['produtos'][:5])
                
                prompt = PROMPT_QWEN_OPTIMIZED.format(
                    objeto_compra=licitacao['objeto_compra'][:200],
                    itens_limitados=itens_text,
                    nome_empresa=empresa['nome_fantasia'],
                    descricao_empresa=empresa['descricao_servicos_produtos'][:150],
                    produtos_limitados=produtos_text
                )
            
            # Preparar dados completos para LLAMA
            else:
                itens_text = "\n".join([f"- {item['descricao']} ({item['quantidade']} {item['unidade']})" for item in licitacao['itens']])
                produtos_text = ", ".join(empresa['produtos'])
                
                prompt = PROMPT_LLAMA_RIGOROSO.format(
                    objeto_compra=licitacao['objeto_compra'],
                    itens_detalhados=itens_text,
                    nome_empresa=empresa['nome_fantasia'],
                    descricao_empresa=empresa['descricao_servicos_produtos'],
                    produtos_completos=produtos_text
                )

            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 200 if "qwen" in model.lower() else 300
                    }
                }
                
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"OLLAMA error: {response.status}")
                    
                    result = await response.json()
                    response_text = result.get('response', '').strip()
                    
                    # Parse JSON response
                    try:
                        parsed = json.loads(response_text)
                        match_result = bool(parsed.get('match', False))
                        execution_time = time.time() - start_time
                        
                        return {
                            'match': match_result,
                            'execution_time': execution_time,
                            'raw_response': response_text,
                            'model': model
                        }
                    except json.JSONDecodeError:
                        print(f"Erro parsing JSON: {response_text}")
                        return {
                            'match': False,
                            'execution_time': time.time() - start_time,
                            'raw_response': response_text,
                            'model': model,
                            'error': 'JSON parse error'
                        }
                        
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"Erro na validação: {e}")
            return {
                'match': False,
                'execution_time': execution_time,
                'error': str(e),
                'model': model
            } 

def analyze_compatibility(licitacao, empresa):
    """
    Analisa compatibilidade e classifica em:
    - highly_compatible: Match direto e específico
    - generic_compatible: Match genérico mas aceitável
    - incompatible: Incompatível
    """
    objeto_lower = licitacao['objeto_compra'].lower()
    descricao_lower = empresa['descricao_servicos_produtos'].lower()
    produtos_lower = [p.lower() for p in empresa['produtos']]
    
    # Análise por categorias
    
    # Tecnologia/Software
    if any(tech in objeto_lower for tech in ['software', 'sistema', 'tecnologia', 'inteligência artificial', 'ti']):
        if any(tech in descricao_lower for tech in ['software', 'sistema', 'tecnologia', 'inteligência artificial']) or \
           any(tech in p for p in produtos_lower for tech in ['software', 'sistema', 'tecnologia', 'inteligência artificial']):
            return "highly_compatible"
    
    # Alimentos
    if any(food in objeto_lower for food in ['alimento', 'merenda', 'gênero alimentício', 'açúcar', 'mel']):
        if any(food in descricao_lower for food in ['alimento', 'mel', 'açúcar']) or \
           any(food in p for p in produtos_lower for food in ['mel', 'açúcar', 'alimento']):
            return "highly_compatible"
    
    # Material de escritório/educação
    if any(office in objeto_lower for office in ['material didático', 'expediente', 'papel', 'livro']):
        if any(office in descricao_lower for office in ['escritório', 'papel', 'livro', 'didático']) or \
           any(office in p for p in produtos_lower for office in ['papel', 'livro', 'escritório', 'caneta']):
            return "highly_compatible"
    
    # Construção civil/manutenção
    if any(const in objeto_lower for const in ['manutenção predial', 'construção', 'reforma', 'ar condicionado']):
        if any(const in descricao_lower for const in ['construção', 'manutenção', 'predial', 'reforma']) or \
           any(const in p for p in produtos_lower for const in ['construção', 'manutenção', 'reforma']):
            return "highly_compatible"
    
    # Materiais hospitalares/kit maternidade
    if any(hosp in objeto_lower for hosp in ['kit maternidade', 'hospital', 'farmacológico', 'medicamento']):
        if any(hosp in descricao_lower for hosp in ['hospital', 'medicamento', 'farmácia']) or \
           any(hosp in p for p in produtos_lower for hosp in ['medicamento', 'hospital']):
            return "highly_compatible"
    
    # Limpeza
    if any(clean in objeto_lower for clean in ['limpeza', 'higiene', 'resíduo', 'coleta']):
        if any(clean in descricao_lower for clean in ['limpeza', 'resíduo', 'coleta']) or \
           any(clean in p for p in produtos_lower for clean in ['limpeza', 'resíduo', 'coleta']):
            return "highly_compatible"
    
    # Veículos/transporte
    if any(vehicle in objeto_lower for vehicle in ['veículo', 'caminhão', 'locação']):
        if any(vehicle in descricao_lower for vehicle in ['veículo', 'caminhão', 'locação']) or \
           any(vehicle in p for p in produtos_lower for vehicle in ['caminhão', 'veículo', 'locação']):
            return "highly_compatible"
    
    # Matches genéricos (empresas muito generalistas)
    generic_terms = ['equipamento', 'material', 'serviço', 'fornecimento']
    if any(term in objeto_lower for term in generic_terms):
        if any(term in descricao_lower for term in generic_terms):
            return "generic_compatible"
    
    # Incompatível
    return "incompatible"

def create_test_scenarios():
    """Cria cenários de teste com expectativas baseadas na análise de compatibilidade"""
    scenarios = []
    
    # Usar todas as licitações e empresas disponíveis
    for licitacao in LICITACOES_COMPLETAS:  # Todas as licitações disponíveis
        for empresa in EMPRESAS_DATA:
            compatibility = analyze_compatibility(licitacao, empresa)
            
            # Definir expectativa baseada na compatibilidade
            if compatibility == "highly_compatible":
                expected = True
            elif compatibility == "generic_compatible":
                expected = True  # Pode ser aceito dependendo do modelo
            else:
                expected = False
            
            scenarios.append({
                'licitacao': licitacao,
                'empresa': empresa,
                'expected': expected,
                'compatibility': compatibility
            })
    
    return scenarios

async def run_test_batch(validator, scenarios, model, batch_size=5):
    """Executa testes em lotes para evitar sobrecarga"""
    results = []
    total_scenarios = len(scenarios)
    
    print(f"\n🧪 Testando {model.upper()} com {total_scenarios} cenários...")
    
    for i in range(0, total_scenarios, batch_size):
        batch = scenarios[i:i+batch_size]
        batch_results = []
        
        for j, scenario in enumerate(batch):
            print(f"  📊 Teste {i+j+1}/{total_scenarios}: {scenario['empresa']['nome_fantasia']} x {scenario['licitacao']['pncp_id'][:20]}...")
            
            result = await validator.validate_match(
                scenario['licitacao'], 
                scenario['empresa'], 
                model
            )
            
            result.update({
                'expected': scenario['expected'],
                'compatibility': scenario['compatibility'],
                'empresa_nome': scenario['empresa']['nome_fantasia'],
                'licitacao_id': scenario['licitacao']['pncp_id']
            })
            
            batch_results.append(result)
        
        results.extend(batch_results)
        
        # Pequena pausa entre lotes
        if i + batch_size < total_scenarios:
            await asyncio.sleep(1)
    
    return results

def calculate_metrics(results):
    """Calcula métricas de performance"""
    valid_results = [r for r in results if 'error' not in r]
    
    if not valid_results:
        return None
    
    # Acurácia
    correct = sum(1 for r in valid_results if r['match'] == r['expected'])
    accuracy = (correct / len(valid_results)) * 100
    
    # Tempos
    times = [r['execution_time'] for r in valid_results]
    avg_time = statistics.mean(times)
    median_time = statistics.median(times)
    
    # Análise por compatibilidade
    by_compatibility = {}
    for result in valid_results:
        comp = result['compatibility']
        if comp not in by_compatibility:
            by_compatibility[comp] = {'correct': 0, 'total': 0}
        
        by_compatibility[comp]['total'] += 1
        if result['match'] == result['expected']:
            by_compatibility[comp]['correct'] += 1
    
    # Calcular acurácia por categoria
    for comp in by_compatibility:
        if by_compatibility[comp]['total'] > 0:
            by_compatibility[comp]['accuracy'] = (
                by_compatibility[comp]['correct'] / by_compatibility[comp]['total']
            ) * 100
    
    return {
        'total_tests': len(results),
        'valid_tests': len(valid_results),
        'accuracy': round(accuracy, 1),
        'avg_time': round(avg_time, 2),
        'median_time': round(median_time, 2),
        'tests_per_minute': round(60 / avg_time if avg_time > 0 else 0, 1),
        'by_compatibility': by_compatibility,
        'errors': len(results) - len(valid_results)
    }

def print_results(model, metrics):
    """Imprime resultados formatados"""
    print(f"\n" + "="*60)
    print(f"📈 RESULTADOS - {model.upper()}")
    print("="*60)
    
    if not metrics:
        print("❌ Erro: Nenhum resultado válido")
        return
    
    print(f"✅ Testes válidos: {metrics['valid_tests']}/{metrics['total_tests']}")
    print(f"🎯 Acurácia: {metrics['accuracy']}%")
    print(f"⏱️  Tempo médio: {metrics['avg_time']}s")
    print(f"⚡ Testes por minuto: {metrics['tests_per_minute']}")
    
    if metrics['errors'] > 0:
        print(f"❌ Erros: {metrics['errors']}")
    
    print("\n📊 ACURÁCIA POR CATEGORIA:")
    for comp, data in metrics['by_compatibility'].items():
        acc = data.get('accuracy', 0)
        total = data['total']
        print(f"  {comp.replace('_', ' ').title()}: {acc:.1f}% ({total} testes)")

async def main():
    """Função principal de teste"""
    print("🚀 INICIANDO TESTE DOS MODELOS LLM OTIMIZADOS")
    print("=" * 60)
    
    # Verificar OLLAMA
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as response:
                if response.status != 200:
                    print("❌ OLLAMA não está rodando. Execute: ollama serve")
                    return
                
                models_info = await response.json()
                available_models = [m['name'] for m in models_info.get('models', [])]
                print(f"✅ OLLAMA ativo. Modelos: {available_models}")
    except Exception as e:
        print(f"❌ Erro conectando OLLAMA: {e}")
        return
    
    # Criar cenários de teste
    scenarios = create_test_scenarios()
    print(f"📝 Criados {len(scenarios)} cenários de teste")
    
    # Testar modelos
    validator = OllamaValidator()
    models_to_test = ["qwen2.5:7b", "llama3.2"]
    
    all_results = {}
    
    for model in models_to_test:
        if model not in [m.split(':')[0] for m in available_models]:
            print(f"⚠️ Modelo {model} não encontrado")
            continue
            
        start_time = time.time()
        results = await run_test_batch(validator, scenarios, model)
        total_time = time.time() - start_time
        
        metrics = calculate_metrics(results)
        all_results[model] = {
            'metrics': metrics,
            'results': results,
            'total_time': total_time
        }
        
        print_results(model, metrics)
        print(f"⏱️ Tempo total do modelo: {total_time:.1f}s")
    
    # Comparação final
    print("\n" + "="*60)
    print("🏆 COMPARAÇÃO FINAL")
    print("="*60)
    
    for model, data in all_results.items():
        metrics = data['metrics']
        if metrics:
            print(f"{model.upper():12} | Acurácia: {metrics['accuracy']:5.1f}% | "
                  f"Tempo: {metrics['avg_time']:5.2f}s | "
                  f"TPM: {metrics['tests_per_minute']:5.1f}")

if __name__ == "__main__":
    asyncio.run(main()) 