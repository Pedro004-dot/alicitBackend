#!/usr/bin/env python3
"""
🤖 VALIDADOR LLM PARA MATCHES DE ALTA QUALIDADE
Sistema de validação final para matches acima de 80% usando IA generativa
"""

import os
import json
from typing import Dict, Any, List, Tuple, Optional
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class LLMMatchValidator:
    """
    🎯 Validador inteligente para matches de alta qualidade
    
    Analisa matches acima de 80% usando LLM para determinar se realmente
    fazem sentido do ponto de vista de negócio e competência empresarial.
    """
    
    def __init__(self):
        """Inicializar o validador com configurações"""
        self.openai_client = None
        self._setup_llm()
        
        # 🔥 NOVO: Thresholds ajustados para validar TODOS os matches
        self.HIGH_SCORE_THRESHOLD = 0.50  # Diminuído de 0.80 para 0.50 - valida mais matches
        self.LLM_CONFIDENCE_THRESHOLD = 0.65  # Diminuído de 0.75 para 0.65 - mais inclusivo
        
    def _setup_llm(self):
        """Configurar cliente OpenAI"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("✅ Cliente OpenAI configurado para validação LLM")
            else:
                logger.warning("⚠️ OPENAI_API_KEY não encontrada - validação LLM desabilitada")
        except Exception as e:
            logger.error(f"❌ Erro ao configurar OpenAI: {e}")
    
    def should_validate_with_llm(self, score: float) -> bool:
        """
        🔥 NOVA POLÍTICA: Validar TODOS os matches acima do threshold mínimo
        
        Agora valida matches a partir de 50% para garantir qualidade total da base
        """
        return score >= self.HIGH_SCORE_THRESHOLD and self.openai_client is not None
    
    def validate_all_matches(self, score: float) -> bool:
        """
        🎯 NOVA FUNÇÃO: Força validação LLM independente do score
        
        Para uso quando queremos validar 100% dos matches
        """
        return self.openai_client is not None
    
    def validate_match(
        self, 
        empresa_nome: str,
        empresa_descricao: str,
        licitacao_objeto: str,
        pncp_id: str,
        similarity_score: float,
        licitacao_itens: Optional[list] = None,
        empresa_produtos: Optional[list] = None  # 🔀 NOVO: Produtos da empresa
    ) -> Dict[str, Any]:
        """
        🤖 Validação inteligente de match usando LLM
        
        Returns:
            Dict com resultado da validação:
            {
                'is_valid': bool,
                'confidence': float,
                'reasoning': str,
                'recommendation': str,
                'llm_used': bool
            }
        """
        
        if not self.should_validate_with_llm(similarity_score):
            return {
                'is_valid': True,
                'confidence': similarity_score,
                'reasoning': f'Score {similarity_score:.1%} abaixo do threshold LLM ({self.HIGH_SCORE_THRESHOLD:.1%})',
                'recommendation': 'Aprovado sem validação LLM',
                'llm_used': False
            }
        
        if not self.openai_client:
            logger.warning("⚠️ LLM não disponível - aprovando match automaticamente")
            return {
                'is_valid': True,
                'confidence': similarity_score,
                'reasoning': 'LLM indisponível - validação automática',
                'recommendation': 'Aprovado por fallback',
                'llm_used': False
            }
        
        try:
            # Prompt especializado para validação de matches
            prompt = self._build_validation_prompt(
                empresa_nome, empresa_descricao, licitacao_objeto, pncp_id, similarity_score, licitacao_itens, empresa_produtos
            )
            
            # 🎯 Sistema de fallback: gpt-4o-mini -> gpt-4o -> gpt-3.5-turbo
            model_used = "gpt-4o-mini"
            
            try:
                logger.info("🚀 Tentando gpt-4o-mini para validação de match...")
                response = self._make_openai_validation_request(prompt, model_used)
                logger.info("✅ gpt-4o-mini respondeu com sucesso!")
                
            except Exception as e:
                logger.warning(f"⚠️ gpt-4o-mini falhou: {e}")
                logger.info("🔄 Fazendo fallback para gpt-4o...")
                
                model_used = "gpt-4o"
                try:
                    response = self._make_openai_validation_request(prompt, model_used)
                    logger.info("✅ gpt-4o (fallback) respondeu com sucesso!")
                    
                except Exception as e2:
                    logger.error(f"❌ gpt-4o também falhou: {e2}")
                    logger.info("🔄 Tentando gpt-3.5-turbo como último recurso...")
                    
                    model_used = "gpt-3.5-turbo"
                    response = self._make_openai_validation_request(prompt, model_used)
                    logger.info("✅ gpt-3.5-turbo (último recurso) respondeu!")
            
            result = json.loads(response.choices[0].message.content)
            
            # Validar estrutura da resposta
            validation_result = self._parse_llm_response(result, similarity_score)
            validation_result['model_used'] = model_used  # Adicionar modelo usado
            
            logger.info(f"🤖 LLM validação ({model_used}): {empresa_nome} vs {pncp_id} = {validation_result['is_valid']} (conf: {validation_result['confidence']:.1%})")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Erro na validação LLM: {e}")
            
            # Fallback: aprovar automaticamente em caso de erro
            return {
                'is_valid': True,
                'confidence': similarity_score * 0.9,  # Penalizar levemente por falha LLM
                'reasoning': f'Erro na validação LLM: {str(e)} - Aprovado por fallback',
                'recommendation': 'Verificar manualmente',
                'llm_used': False,
                'model_used': 'fallback'
            }
    
    def _get_system_prompt(self) -> str:
        """Prompt do sistema para o LLM"""
        return """Você é um especialista em análise de licitações públicas brasileiras e competências empresariais.

Sua tarefa é validar se um match entre uma empresa e uma licitação faz sentido do ponto de vista de negócio e capacidade técnica.

CRITÉRIOS DE AVALIAÇÃO:
1. **Competência Técnica**: A empresa tem capacidade de executar o objeto da licitação?
2. **Área de Atuação**: O ramo de atividade da empresa é compatível com o serviço/produto licitado?
3. **Experiência Relevante**: A descrição da empresa indica experiência no setor?
4. **Viabilidade Comercial**: Faz sentido comercial a empresa participar desta licitação?
5. **Análise de Itens**: A empresa fornece os produtos/serviços específicos listados na licitação? (Mais importante)

RESPONDA SEMPRE EM JSON com esta estrutura:
{
    "is_valid": boolean,
    "confidence": number (0.0 a 1.0),
    "reasoning": "explicação detalhada da análise",
    "recommendation": "RECOMENDADO | NÃO_RECOMENDADO | REVISAR_MANUALMENTE"
}

Seja rigoroso: prefira reprovar matches duvidosos a aprovar matches irrelevantes."""
    
    def _build_validation_prompt(
        self, 
        empresa_nome: str, 
        empresa_descricao: str, 
        licitacao_objeto: str, 
        pncp_id: str, 
        similarity_score: float,
        licitacao_itens: Optional[list] = None,
        empresa_produtos: Optional[list] = None
    ) -> str:
        """Construir prompt específico para validação de matches"""
        
        # 🔀 CORREÇÃO: Validação robusta dos parâmetros de entrada
        # Garantir que licitacao_itens seja uma lista válida
        if licitacao_itens is None:
            licitacao_itens = []
        elif isinstance(licitacao_itens, str):
            try:
                import json
                licitacao_itens = json.loads(licitacao_itens)
            except (json.JSONDecodeError, TypeError):
                licitacao_itens = []
        elif not isinstance(licitacao_itens, list):
            licitacao_itens = []
        
        # Garantir que empresa_produtos seja uma lista válida
        if empresa_produtos is None:
            empresa_produtos = []
        elif isinstance(empresa_produtos, str):
            try:
                import json
                empresa_produtos = json.loads(empresa_produtos)
            except (json.JSONDecodeError, TypeError):
                empresa_produtos = []
        elif not isinstance(empresa_produtos, list):
            empresa_produtos = []
        
        # Formatação dos itens da licitação
        itens_info = "Não especificados"
        if licitacao_itens:
            itens_formatados = []
            for item in licitacao_itens:
                if isinstance(item, dict):
                    descricao = item.get('descricao', 'Sem descrição')
                    quantidade = item.get('quantidade', 'N/A')
                    itens_formatados.append(f"• {descricao} (Qtd: {quantidade})")
                elif isinstance(item, str):
                    itens_formatados.append(f"• {item}")
                else:
                    itens_formatados.append(f"• {str(item)}")
            itens_info = "\n".join(itens_formatados)
        
        # Formatação dos produtos da empresa
        produtos_info = "Não especificados"
        if empresa_produtos:
            produtos_formatados = []
            for produto in empresa_produtos:
                if isinstance(produto, str):
                    produtos_formatados.append(f"• {produto}")
                else:
                    produtos_formatados.append(f"• {str(produto)}")
            produtos_info = "\n".join(produtos_formatados)
        
        return f"""
        Você é um especialista em análise de compatibilidade entre empresas e licitações públicas.
        Analise SE a empresa abaixo tem capacidade REAL de atender à licitação específica.
        
        **EMPRESA: {empresa_nome}**
        Descrição: {empresa_descricao}
        
        **PRODUTOS/SERVIÇOS DA EMPRESA:**
        {produtos_info}
        
        **LICITAÇÃO (ID: {pncp_id})**
        Objeto: {licitacao_objeto}
        
        **ITENS ESPECÍFICOS DA LICITAÇÃO:**
        {itens_info}
        
        **Score de Similaridade Semântica: {similarity_score:.1%}**
        
        **CRITÉRIOS DE ANÁLISE:**
        1. **Capacidade Técnica**: A empresa possui os produtos/serviços específicos solicitados?
        2. **Área de Atuação**: O ramo de atividade da empresa é compatível com o serviço/produto licitado?
        3. **Experiência Relevante**: A descrição da empresa indica experiência no setor?
        4. **Viabilidade Comercial**: Faz sentido comercial a empresa participar desta licitação?
        5. **Análise de Itens**: A empresa tem capacidade de fornecer os itens específicos listados?
        
        **IMPORTANTE**: Considere tanto a descrição geral quanto a lista específica de produtos da empresa.
        
        Responda em formato JSON:
        {{
            "compativel": true/false,
            "confianca": 0.XX,
            "justificativa": "explicação detalhada da compatibilidade"
        }}
        """
    
    def _parse_llm_response(self, llm_result: Dict, original_score: float) -> Dict[str, Any]:
        """Parseia e valida a resposta do LLM"""
        
        try:
            is_valid = llm_result.get('is_valid', False)
            confidence = float(llm_result.get('confidence', 0.0))
            reasoning = llm_result.get('reasoning', 'Sem justificativa fornecida')
            recommendation = llm_result.get('recommendation', 'REVISAR_MANUALMENTE')
            
            # Aplicar threshold de confiança
            if confidence < self.LLM_CONFIDENCE_THRESHOLD:
                is_valid = False
                reasoning += f" | Confiança LLM ({confidence:.1%}) abaixo do mínimo ({self.LLM_CONFIDENCE_THRESHOLD:.1%})"
            
            # Garantir que confiança não seja maior que score original
            confidence = min(confidence, original_score)
            
            return {
                'is_valid': is_valid,
                'confidence': confidence,
                'reasoning': reasoning,
                'recommendation': recommendation,
                'llm_used': True
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao parsear resposta LLM: {e}")
            
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reasoning': f'Erro ao processar resposta LLM: {str(e)}',
                'recommendation': 'REVISAR_MANUALMENTE',
                'llm_used': True
            }
    
    def validate_matches_batch(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Valida múltiplos matches em lote
        
        Args:
            matches: Lista de dicts com campos:
                - empresa_nome, empresa_descricao
                - licitacao_objeto, pncp_id  
                - score_similaridade
        
        Returns:
            Lista de matches com validação LLM aplicada
        """
        
        validated_matches = []
        llm_validations_count = 0
        
        for match in matches:
            try:
                score = float(match.get('score_similaridade', 0))
                
                # Aplicar validação LLM se necessário
                validation = self.validate_match(
                    empresa_nome=match.get('empresa_nome', ''),
                    empresa_descricao=match.get('empresa_descricao', ''),
                    licitacao_objeto=match.get('licitacao_objeto', ''),
                    pncp_id=match.get('pncp_id', ''),
                    similarity_score=score,
                    licitacao_itens=match.get('licitacao_itens', []),
                    empresa_produtos=match.get('empresa_produtos', [])
                )
                
                # Adicionar resultado da validação ao match
                enhanced_match = match.copy()
                enhanced_match.update({
                    'llm_validation': validation,
                    'final_score': validation['confidence'],
                    'is_recommended': validation['is_valid']
                })
                
                # Só adicionar à lista se for válido
                if validation['is_valid']:
                    validated_matches.append(enhanced_match)
                else:
                    logger.info(f"🚫 Match rejeitado pela validação LLM: {match.get('empresa_nome')} vs {match.get('pncp_id')}")
                
                if validation['llm_used']:
                    llm_validations_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Erro ao validar match: {e}")
                # Em caso de erro, incluir o match original sem validação
                validated_matches.append(match)
        
        logger.info(f"🤖 Validação LLM: {llm_validations_count} matches analisados, {len(validated_matches)}/{len(matches)} aprovados")
        
        return validated_matches

    def _make_openai_validation_request(self, prompt: str, model: str):
        """Faz requisição para OpenAI com modelo específico para validação"""
        return self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": self._get_system_prompt()
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.1,  # Baixa criatividade para análise objetiva
            max_tokens=500,
            response_format={"type": "json_object"}
        )


# Instância global do validador
llm_validator = LLMMatchValidator()


def validate_high_score_match(
    empresa_nome: str,
    empresa_descricao: str, 
    licitacao_objeto: str,
    pncp_id: str,
    similarity_score: float,
    licitacao_itens: Optional[list] = None,
    empresa_produtos: Optional[list] = None  # 🔀 NOVO: Produtos da empresa
) -> Dict[str, Any]:
    """
    Função helper para validar um único match de alta qualidade, agora com itens e produtos.
    
    Wrapper around LLMMatchValidator.validate_match()
    """
    validator = LLMMatchValidator()
    return validator.validate_match(
        empresa_nome, empresa_descricao, licitacao_objeto, pncp_id, similarity_score, licitacao_itens, empresa_produtos
    )


def main():
    # Teste com exemplos reais ruins
    validator = LLMMatchValidator()
    
    # Exemplo 1: Software vs Manutenção de Veículos (deveria ser rejeitado)
    result1 = validator.validate_match(
        empresa_nome="InfinitiFy",
        empresa_descricao="Empresa especialista no fornecimento de softwares, sistemas de redes, banco de dados, inteligencia artificial.",
        licitacao_objeto="Registro de preços para a prestação de serviços de manutenção em veículos leves, vans, minivans, micro-ônibus e caminhões, sendo: mecânica, elétrica e eletrônica, funilaria, lanternagem e pintura",
        pncp_id="87613196000178-1-000045/2025",
        similarity_score=0.892,
        licitacao_itens=[
            {"descricao": "Mecânica"},
            {"descricao": "Elétrica"},
            {"descricao": "Eletrônica"},
            {"descricao": "Funilaria"},
            {"descricao": "Lanternagem"},
            {"descricao": "Pintura"}
        ]
    )
    
    print("🧪 TESTE 1 - Software vs Veículos:")
    print(f"✅ Válido: {result1['is_valid']}")
    print(f"📊 Confiança: {result1['confidence']:.1%}")
    print(f"💭 Raciocínio: {result1['reasoning']}")
    print(f"🎯 Recomendação: {result1['recommendation']}")
    print()
    
    # Exemplo 2: Match que deveria ser aprovado
    result2 = validator.validate_match(
        empresa_nome="TechSoft Solutions",
        empresa_descricao="Empresa especializada em desenvolvimento de software de gestão pública, sistemas de ponto eletrônico e controle de acesso, com experiência em implementação de soluções tecnológicas para órgãos públicos.",
        licitacao_objeto="Contratação de empresa especializada na prestação de serviços de implantação de sistema de gestão administrativa de ponto eletrônico facial e controle de acesso de funcionários",
        pncp_id="19904298000192-1-000012/2025",
        similarity_score=0.850,
        licitacao_itens=[
            {"descricao": "Sistema de Gestão Administrativa"},
            {"descricao": "Ponto Eletrônico"},
            {"descricao": "Controle de Acesso"},
            {"descricao": "Implantação de Sistema"},
            {"descricao": "Facial"},
            {"descricao": "Controle de Acesso"}
        ]
    )
    
    print("🧪 TESTE 2 - Software vs Software (match bom):")
    print(f"✅ Válido: {result2['is_valid']}")
    print(f"📊 Confiança: {result2['confidence']:.1%}")
    print(f"💭 Raciocínio: {result2['reasoning']}")
    print(f"🎯 Recomendação: {result2['recommendation']}")

    # Exemplo 3: Match que deveria ser rejeitado
    result3 = validate_high_score_match(
        empresa_nome="EMPRESA DE TECNOLOGIA ABC LTDA",
        empresa_descricao="Desenvolvimento de software, aplicativos mobile e consultoria em TI. Venda de servidores Dell e licenças Microsoft.",
        licitacao_objeto="Aquisição de equipamentos de informática",
        pncp_id="123456-1-2024",
        similarity_score=0.85,
        licitacao_itens=[
            {"descricao": "100x Mouse sem fio"},
            {"descricao": "50x Teclado ABNT2"},
            {"descricao": "20x Servidor Dell PowerEdge R750"}
        ],
        empresa_produtos=[
            {"nome": "Servidores Dell", "descricao": "Venda e manutenção de servidores Dell PowerEdge."},
            {"nome": "Software Microsoft", "descricao": "Licenciamento de Windows Server e Office 365."}
        ]
    )
    print("🧪 TESTE 3 - Match com itens e produtos:")
    print(json.dumps(result3, indent=2))


if __name__ == "__main__":
    main() 