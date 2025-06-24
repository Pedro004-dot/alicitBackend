"""
🦙 Configuração centralizada para LLMs (Ollama + OpenAI Fallback)
"""

import os
import requests
import logging
from enum import Enum
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    AUTO = "auto"  # Tenta Ollama primeiro, fallback OpenAI

class LLMConfig:
    """Configuração centralizada de LLM"""
    
    @staticmethod
    def get_provider() -> LLMProvider:
        """Determina qual LLM usar baseado nas configurações"""
        provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        
        if provider == 'openai':
            return LLMProvider.OPENAI
        elif provider == 'ollama':
            return LLMProvider.OLLAMA
        else:
            return LLMProvider.AUTO  # Default: tenta Ollama primeiro
    
    @staticmethod
    def get_ollama_config() -> Dict[str, Any]:
        """Configurações do Ollama"""
        return {
            'url': os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            'model': os.getenv('OLLAMA_MODEL', 'qwen2.5:7b'),
            'timeout': int(os.getenv('OLLAMA_TIMEOUT', '45')),
            'temperature': float(os.getenv('OLLAMA_TEMPERATURE', '0.05')),
        }
    
    @staticmethod
    def get_openai_config() -> Dict[str, Any]:
        """Configurações do OpenAI"""
        return {
            'api_key': os.getenv('OPENAI_API_KEY'),
            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.1')),
            'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '300')),
        }
    
    @staticmethod
    def is_ollama_available() -> bool:
        """Verifica se o Ollama está disponível"""
        try:
            config = LLMConfig.get_ollama_config()
            response = requests.get(
                f"{config['url']}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama não disponível: {e}")
            return False
    
    @staticmethod
    def create_validator():
        """Factory para criar o validador apropriado"""
        provider = LLMConfig.get_provider()
        
        if provider == LLMProvider.OPENAI:
            from matching.llm_match_validator import LLMMatchValidator
            return LLMMatchValidator()
        
        elif provider == LLMProvider.OLLAMA:
            from matching.ollama_match_validator import OllamaMatchValidator
            return OllamaMatchValidator()
        
        else:  # AUTO
            # Tenta Ollama primeiro, fallback OpenAI
            if LLMConfig.is_ollama_available():
                logger.info("🦙 Usando Ollama como LLM principal")
                from matching.ollama_match_validator import OllamaMatchValidator
                return OllamaMatchValidator()
            else:
                logger.warning("🦙 Ollama indisponível, usando OpenAI como fallback")
                from matching.llm_match_validator import LLMMatchValidator
                return LLMMatchValidator() 