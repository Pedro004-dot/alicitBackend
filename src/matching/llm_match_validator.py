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
        
        # Thresholds para validação
        self.HIGH_SCORE_THRESHOLD = 0.80  # Acima de 80% vai para validação LLM
        self.LLM_CONFIDENCE_THRESHOLD = 0.75  # Confiança mínima do LLM para aprovar
        
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
        """Determina se o match precisa de validação LLM"""
        return score >= self.HIGH_SCORE_THRESHOLD and self.openai_client is not None
    
    def validate_match(
        self, 
        empresa_nome: str,
        empresa_descricao: str,
        licitacao_objeto: str,
        pncp_id: str,
        similarity_score: float
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
                empresa_nome, empresa_descricao, licitacao_objeto, pncp_id, similarity_score
            )
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Modelo otimizado para custo-efetividade
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
            
            result = json.loads(response.choices[0].message.content)
            
            # Validar estrutura da resposta
            validation_result = self._parse_llm_response(result, similarity_score)
            
            logger.info(f"🤖 LLM validação: {empresa_nome} vs {pncp_id} = {validation_result['is_valid']} (conf: {validation_result['confidence']:.1%})")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Erro na validação LLM: {e}")
            
            # Fallback: aprovar automaticamente em caso de erro
            return {
                'is_valid': True,
                'confidence': similarity_score * 0.9,  # Penalizar levemente por falha LLM
                'reasoning': f'Erro na validação LLM: {str(e)} - Aprovado por fallback',
                'recommendation': 'Verificar manualmente',
                'llm_used': False
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
        similarity_score: float
    ) -> str:
        """Constrói o prompt de validação"""
        
        return f"""ANÁLISE DE MATCH PARA VALIDAÇÃO:

**EMPRESA:**
- Nome: {empresa_nome}
- Descrição: {empresa_descricao}

**LICITAÇÃO:**
- PNCP ID: {pncp_id}
- Objeto: {licitacao_objeto}

**SCORE SEMÂNTICO:** {similarity_score:.1%}

PERGUNTA: Esta empresa tem competência e capacidade real para executar este objeto licitado? 
O match faz sentido do ponto de vista de negócio e adequação técnica?

Analise cuidadosamente se há compatibilidade real entre:
- As competências/experiência da empresa
- Os requisitos técnicos da licitação
- A viabilidade comercial do match

Responda em JSON conforme especificado."""
    
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
                    similarity_score=score
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


# Instância global do validador
llm_validator = LLMMatchValidator()


def validate_high_score_match(
    empresa_nome: str,
    empresa_descricao: str, 
    licitacao_objeto: str,
    pncp_id: str,
    similarity_score: float
) -> Dict[str, Any]:
    """
    🎯 Função de conveniência para validar um match individual
    
    Wrapper around LLMMatchValidator.validate_match()
    """
    return llm_validator.validate_match(
        empresa_nome, empresa_descricao, licitacao_objeto, 
        pncp_id, similarity_score
    )


if __name__ == "__main__":
    # Teste com exemplos reais ruins
    validator = LLMMatchValidator()
    
    # Exemplo 1: Software vs Manutenção de Veículos (deveria ser rejeitado)
    result1 = validator.validate_match(
        empresa_nome="InfinitiFy",
        empresa_descricao="Empresa especialista no fornecimento de softwares, sistemas de redes, banco de dados, inteligencia artificial.",
        licitacao_objeto="Registro de preços para a prestação de serviços de manutenção em veículos leves, vans, minivans, micro-ônibus e caminhões, sendo: mecânica, elétrica e eletrônica, funilaria, lanternagem e pintura",
        pncp_id="87613196000178-1-000045/2025",
        similarity_score=0.892
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
        similarity_score=0.850
    )
    
    print("🧪 TESTE 2 - Software vs Software (match bom):")
    print(f"✅ Válido: {result2['is_valid']}")
    print(f"📊 Confiança: {result2['confidence']:.1%}")
    print(f"💭 Raciocínio: {result2['reasoning']}")
    print(f"🎯 Recomendação: {result2['recommendation']}") 