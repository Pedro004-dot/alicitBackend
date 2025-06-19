#!/usr/bin/env python3
"""
Serviço de embeddings usando NeralMind BERT via Hugging Face API
Especializado para licitações brasileiras - Zero peso local!
"""

import os
import requests
import logging
import time
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

class NeuralMindEmbeddingService:
    """
    Serviço usando NeralMind BERT via Hugging Face API
    Especializado para licitações brasileiras
    
    Por que este modelo:
    - Treinado APENAS em português brasileiro
    - Entende jargão técnico e administrativo
    - 768 dimensões = ideal para textos complexos
    - Melhor performance para nosso domínio específico
    """
    
    def __init__(self):
        # Configuração da API
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        self.model_name = "neuralmind/bert-base-portuguese-cased"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        
        # Headers
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            logger.info("🔑 Hugging Face API key configurada (tier pago)")
        else:
            logger.info("🆓 Usando Hugging Face tier gratuito")
        
        # Configurações específicas para licitações
        self.embedding_dim = 768
        self.max_length = 512  # BERT limit
        
    def preprocess_for_licitacoes(self, text: str) -> str:
        """
        Pré-processamento específico para textos de licitação
        
        Por que fazemos isso:
        - Expandir siglas comuns (TI → tecnologia da informação)
        - Normalizar termos técnicos
        - Melhorar correlação entre licitação e empresa
        """
        if not text:
            return ""
        
        # Siglas comuns em licitações brasileiras
        siglas_licitacao = {
            r'\bTI\b': 'TI tecnologia da informação',
            r'\bRH\b': 'RH recursos humanos',
            r'\bCFTV\b': 'CFTV circuito fechado de televisão',
            r'\bGPS\b': 'GPS sistema de posicionamento global',
            r'\bEPP\b': 'EPP empresa de pequeno porte',
            r'\bME\b': 'ME microempresa',
            r'\bSRP\b': 'SRP sistema de registro de preços'
        }
        
        processed_text = text
        
        # Aplicar expansões (mantém sigla + adiciona expansão)
        for sigla_pattern, expansao in siglas_licitacao.items():
            processed_text = re.sub(
                sigla_pattern, 
                expansao, 
                processed_text, 
                flags=re.IGNORECASE
            )
        
        # Limitar tamanho (BERT tem limite de 512 tokens)
        if len(processed_text) > 1000:  # ~400 tokens
            processed_text = processed_text[:1000] + "..."
        
        return processed_text.strip()
    
    def generate_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Gera embeddings usando Hugging Face Inference API
        
        Como funciona:
        1. Prepara textos (pré-processamento)
        2. Faz requisição HTTP para HF
        3. Retorna embeddings de 768 dimensões
        """
        if not texts:
            return []
        
        try:
            # Pré-processar todos os textos
            processed_texts = []
            for text in texts:
                if text and text.strip():
                    processed = self.preprocess_for_licitacoes(text)
                    if processed:
                        processed_texts.append(processed)
            
            if not processed_texts:
                return []
            
            logger.info(f"🧠 NeralMind: processando {len(processed_texts)} textos")
            
            # Fazer requisição para Hugging Face
            payload = {
                "inputs": processed_texts,
                "options": {
                    "wait_for_model": True,  # Aguardar se modelo estiver carregando
                    "use_cache": True        # Usar cache do HF se disponível
                }
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=45  # Timeout mais alto para primeiro carregamento
            )
            
            # Tratar diferentes códigos de resposta
            if response.status_code == 200:
                embeddings = response.json()
                
                # Validar estrutura da resposta
                if isinstance(embeddings, list) and len(embeddings) == len(processed_texts):
                    logger.info(f"✅ {len(embeddings)} embeddings NeralMind gerados (768d)")
                    return embeddings
                else:
                    logger.error(f"❌ Estrutura de resposta inválida: {type(embeddings)}")
                    return None
                    
            elif response.status_code == 503:
                # Modelo carregando (comum na primeira requisição)
                logger.info("⏳ Modelo NeralMind carregando no servidor HF...")
                logger.info("💡 Primeira requisição pode demorar ~20-30s")
                
                # Aguardar e tentar novamente
                time.sleep(20)
                return self.generate_embeddings(texts)  # Retry uma vez
                
            elif response.status_code == 429:
                # Rate limit (tier gratuito)
                logger.warning("⚠️ Rate limit atingido - considere upgrade para HF Pro")
                time.sleep(5)
                return None
                
            else:
                logger.error(f"❌ Erro HF API: {response.status_code}")
                logger.error(f"Resposta: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("⏰ Timeout na requisição HF (>45s)")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao gerar embeddings NeralMind: {e}")
            return None
    
    def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Gera embedding único - mais simples"""
        result = self.generate_embeddings([text])
        return result[0] if result else None
    
    def test_connection(self) -> bool:
        """
        Testa se a conexão com HF está funcionando
        Use este método antes de integrar ao sistema principal
        """
        try:
            logger.info("🧪 Testando conexão NeralMind...")
            
            test_embedding = self.generate_single_embedding(
                "Contratação de serviços de tecnologia da informação"
            )
            
            if test_embedding and len(test_embedding) == 768:
                logger.info("✅ Teste NeralMind passou - sistema pronto")
                return True
            else:
                logger.error("❌ Teste NeralMind falhou")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """Informações do modelo para debug"""
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'api_endpoint': self.api_url,
            'has_api_key': bool(self.api_key),
            'preprocessing': 'licitacoes_brasileiras_optimized'
        } 