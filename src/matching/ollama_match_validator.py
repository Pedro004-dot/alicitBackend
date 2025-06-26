"""
🦙 VALIDADOR LLM LOCAL USANDO OLLAMA
Integração com qwen2.5:7b para validação de matches de licitações
"""

import os
import json
import logging
import requests
import time
from typing import Dict, Any, Optional
from config.llm_config import LLMConfig
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('config.env')

logger = logging.getLogger(__name__)

class OllamaMatchValidator:
    """
    🦙 Validador de matches usando Ollama local
    
    Usa qwen2.5:7b para análise semântica de compatibilidade
    entre empresas e licitações, com fallback para OpenAI.
    """

    def __init__(self):
        """Inicializar o validador Ollama"""
        self.config = LLMConfig.get_ollama_config()
        self._setup_ollama()
        
        # Thresholds para validação (ajustados conforme config.env)
        self.HIGH_SCORE_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD_PHASE1', '0.70'))  # Threshold do config.env
        self.LLM_CONFIDENCE_THRESHOLD = 0.65  # Aprovação LLM
        
    def _setup_ollama(self):
        """Configurar conexão com Ollama"""
        try:
            response = requests.get(
                f"{self.config['url']}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.config['model'] in model_names:
                    logger.info(f"🦙 Ollama conectado - Modelo: {self.config['model']}")
                    self.ollama_available = True
                else:
                    logger.error(f"❌ Modelo {self.config['model']} não encontrado. Disponíveis: {model_names}")
                    self.ollama_available = False
            else:
                logger.error(f"❌ Ollama retornou status {response.status_code}")
                self.ollama_available = False
                
        except Exception as e:
            logger.error(f"❌ Erro conectando Ollama: {e}")
            self.ollama_available = False

    def should_validate_with_llm(self, score: float) -> bool:
        """
        🔥 NOVA POLÍTICA: Validar TODOS os matches acima do threshold
        """
        return score >= self.HIGH_SCORE_THRESHOLD

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
        🦙 Validar match usando Ollama com fallback OpenAI
        
        Returns:
            Dict com 'is_valid', 'confidence', 'reasoning'
        """
        
        if not self.ollama_available:
            logger.warning("🦙 Ollama indisponível, usando fallback OpenAI")
            return self._fallback_to_openai(
                empresa_nome, empresa_descricao, licitacao_objeto, 
                pncp_id, similarity_score, licitacao_itens, empresa_produtos
            )
        
        try:
            start_time = time.time()
            
            # Construir prompt otimizado para qwen2.5:7b
            prompt = self._build_validation_prompt(
                empresa_nome, empresa_descricao, licitacao_objeto, similarity_score, licitacao_itens, empresa_produtos
            )
            
            # Fazer requisição para Ollama
            payload = {
                "model": self.config['model'],
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config['temperature'],
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            response = requests.post(
                f"{self.config['url']}/api/generate",
                json=payload,
                timeout=self.config['timeout']
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Ollama erro HTTP {response.status_code}")
                return self._fallback_to_openai(
                    empresa_nome, empresa_descricao, licitacao_objeto, 
                    pncp_id, similarity_score, licitacao_itens, empresa_produtos
                )
            
            result = response.json()
            llm_response = result.get('response', '').strip()
            
            processing_time = time.time() - start_time
            logger.info(f"🦙 Ollama processou em {processing_time:.2f}s")
            
            # Analisar resposta do LLM
            validation_result = self._parse_llm_response(llm_response, similarity_score)
            
            # Log detalhado
            logger.info(
                f"🦙 OLLAMA VALIDATION - "
                f"Empresa: {empresa_nome[:30]}... | "
                f"Objeto: {licitacao_objeto[:40]}... | "
                f"Score: {similarity_score:.1%} | "
                f"Decisão: {'✅ APROVADO' if validation_result['is_valid'] else '🚫 REJEITADO'} | "
                f"Confiança: {validation_result['confidence']:.1%}"
            )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Erro na validação Ollama: {e}")
            return self._fallback_to_openai(
                empresa_nome, empresa_descricao, licitacao_objeto, 
                pncp_id, similarity_score, licitacao_itens, empresa_produtos
            )

    def _build_validation_prompt(
        self, 
        empresa_nome: str, 
        empresa_descricao: str, 
        licitacao_objeto: str, 
        similarity_score: float,
        licitacao_itens: Optional[list] = None,
        empresa_produtos: Optional[list] = None
    ) -> str:
        """
        🚀 Construir prompt OTIMIZADO específico para cada modelo
        """
        
        # 🔀 Validação robusta dos parâmetros de entrada
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
        
        # Formatação otimizada dos dados
        produtos_texto = "\n".join([f"• {p}" for p in empresa_produtos[:5]]) if empresa_produtos else "Não especificados"
        itens_texto = "\n".join([f"• {item.get('descricao', str(item))[:80]}..." if isinstance(item, dict) 
                                else f"• {str(item)[:80]}..." for item in licitacao_itens[:4]]) if licitacao_itens else "Não especificados"
        
        # 🚀 PROMPT OTIMIZADO PARA QWEN2.5:7B - Mais direto e estruturado
        if self.config['model'] in ['qwen2.5:7b', 'qwen2.5']:
            return f"""ANÁLISE RÁPIDA DE COMPATIBILIDADE COMERCIAL

EMPRESA: {empresa_nome}
PRODUTOS: {produtos_texto}

LICITAÇÃO: {licitacao_objeto[:150]}
ITENS: {itens_texto}

SCORE SEMÂNTICO: {similarity_score:.0%}

CRITÉRIOS:
1. Produtos da empresa atendem itens da licitação?
2. Área de atuação é compatível?
3. Empresa tem capacidade técnica?

DECISÃO: [SIM/NÃO]
CONFIANÇA: [0-100]%
JUSTIFICATIVA: [máximo 100 caracteres]"""

        # 🦙 PROMPT MELHORADO PARA LLAMA3.2 - Mais reflexivo e criterioso
        else:
            return f"""VALIDAÇÃO CRITERIOSA DE COMPATIBILIDADE

### ANÁLISE DETALHADA NECESSÁRIA ###

EMPRESA CANDIDATA:
- Nome: {empresa_nome}
- Descrição: {empresa_descricao[:100]}
- Produtos/Serviços: {produtos_texto}

DEMANDA DA LICITAÇÃO:
- Objeto: {licitacao_objeto[:200]}
- Itens Específicos: {itens_texto}
- Score Inicial: {similarity_score:.1%}

### INSTRUÇÕES PARA ANÁLISE RIGOROSA ###

1. **PRIMEIRO PASSO**: Analise se os produtos da empresa são DIRETAMENTE relacionados aos itens da licitação
2. **SEGUNDO PASSO**: Verifique se a empresa tem EXPERIÊNCIA COMPROVADA na área
3. **TERCEIRO PASSO**: Considere se é COMERCIALMENTE VIÁVEL para a empresa participar
4. **DECISÃO FINAL**: Seja CRITERIOSO - aprove apenas matches com alta probabilidade de sucesso

IMPORTANTE: 
- NÃO aprove por "possível compatibilidade" - exija compatibilidade CLARA
- NÃO confunda área geral com especialização específica
- REJEITE se houver dúvidas significativas sobre capacidade

RESPOSTA OBRIGATÓRIA:
DECISÃO: [SIM/NÃO]
CONFIANÇA: [0-100]%
JUSTIFICATIVA: [explicação da decisão em até 150 caracteres]"""

    def _parse_llm_response(self, response: str, similarity_score: float) -> Dict[str, Any]:
        """
        🧠 Analisar resposta do LLM e extrair decisão estruturada
        """
        response_lower = response.lower().strip()
        
        # Buscar decisão
        is_valid = False
        confidence = 0.5  # Default
        reasoning = response.strip()
        
        # Análise de padrões na resposta
        if any(palavra in response_lower for palavra in ['sim', 'compatível', 'adequado', 'capaz']):
            is_valid = True
            confidence = 0.75
        elif any(palavra in response_lower for palavra in ['não', 'incompatível', 'inadequado', 'incapaz']):
            is_valid = False
            confidence = 0.8
        
        # Buscar confiança explícita (formato CONFIANÇA: XX%)
        import re
        confidence_match = re.search(r'confiança[:\s]*(\d+)%?', response_lower)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1)) / 100
            except:
                pass
        
        # Ajustar baseado no score semântico
        if similarity_score >= 0.85:
            confidence = min(confidence + 0.1, 1.0)
        elif similarity_score <= 0.60:
            confidence = max(confidence - 0.1, 0.1)
        
        # Aplicar threshold de confiança
        final_is_valid = is_valid and confidence >= self.LLM_CONFIDENCE_THRESHOLD
        
        return {
            'is_valid': final_is_valid,
            'confidence': confidence,
            'reasoning': reasoning[:200],  # Limitar tamanho
            'provider': 'ollama',
            'model': self.config['model']
        }

    def _fallback_to_openai(
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
        🔄 Fallback para OpenAI quando Ollama falha
        """
        try:
            from matching.llm_match_validator import LLMMatchValidator
            
            logger.info("🔄 Usando OpenAI como fallback...")
            openai_validator = LLMMatchValidator()
            
            result = openai_validator.validate_match(
                empresa_nome, empresa_descricao, licitacao_objeto, 
                pncp_id, similarity_score, licitacao_itens, empresa_produtos
            )
            
            # Marcar como fallback
            result['provider'] = 'openai_fallback'
            return result
            
        except Exception as e:
            logger.error(f"❌ Fallback OpenAI também falhou: {e}")
            
            # Último recurso: aprovação conservadora baseada no score
            is_valid = similarity_score >= 0.85  # Só aprova scores muito altos
            
            return {
                'is_valid': is_valid,
                'confidence': 0.5,
                'reasoning': f"Fallback: Score {similarity_score:.1%} {'≥' if is_valid else '<'} 85%",
                'provider': 'fallback_conservative'
            } 