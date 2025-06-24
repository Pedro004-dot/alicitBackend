#!/usr/bin/env python3
"""
Serviço de embeddings usando NeralMind BERT via Hugging Face API
Especializado para licitações brasileiras - Zero peso local!
"""

import os
import logging
import time
import re
from typing import List, Optional

try:
    from huggingface_hub import InferenceClient
except ImportError:
    print("📦 Instalando huggingface_hub...")
    import subprocess
    subprocess.check_call(["pip", "install", "huggingface_hub"])
    from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

class NeuralMindEmbeddingService:
    """
    Serviço usando modelo multilíngue via Hugging Face API
    Especializado para licitações brasileiras
    
    Modelo usado: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
    - Suporte a português e múltiplas línguas
    - Otimizado para similaridade semântica
    - 384 dimensões = eficiente e performático
    - Funciona bem com a API Inference do HuggingFace
    """
    
    def __init__(self):
        # Configuração da API
        self.api_key = os.getenv('HUGGINGFACE_API_KEY')
        # Usar um modelo que funciona com a API Inference para feature extraction
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        
        # Criar cliente HuggingFace
        self.client = InferenceClient(token=self.api_key)
        
        if self.api_key:
            logger.info("🔑 Hugging Face API key configurada (tier pago)")
        else:
            logger.info("🆓 Usando Hugging Face tier gratuito")
        
        # Configurações específicas para licitações
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimensions
        self.max_length = 512  # Model limit
        
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
        Gera embeddings usando Hugging Face Inference Client
        
        Como funciona:
        1. Prepara textos (pré-processamento)
        2. Usa o cliente oficial do HuggingFace
        3. Retorna embeddings de 384 dimensões
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
            
            logger.info(f"🧠 HuggingFace: processando {len(processed_texts)} textos")
            
            # Gerar embeddings usando o cliente oficial
            embeddings = []
            for text in processed_texts:
                try:
                    # O cliente retorna numpy array, converter para lista
                    embedding = self.client.feature_extraction(
                        text=text,
                        model=self.model_name
                    )
                    
                    # Converter numpy array para lista Python
                    if hasattr(embedding, 'tolist'):
                        embedding_list = embedding.tolist()
                    elif isinstance(embedding, list):
                        embedding_list = embedding
                    else:
                        logger.error(f"❌ Formato inesperado: {type(embedding)}")
                        return None
                    
                    embeddings.append(embedding_list)
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar texto: {str(e)}")
                    if "loading" in str(e).lower():
                        logger.info("⏳ Modelo carregando... aguardando...")
                        time.sleep(20)
                        # Retry uma vez
                        try:
                            embedding = self.client.feature_extraction(
                                text=text,
                                model=self.model_name
                            )
                            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else embedding
                            embeddings.append(embedding_list)
                        except Exception as retry_e:
                            logger.error(f"❌ Falha no retry: {retry_e}")
                            return None
                    else:
                        return None
            
            if len(embeddings) == len(processed_texts):
                logger.info(f"✅ {len(embeddings)} embeddings HuggingFace gerados ({self.embedding_dim}d)")
                return embeddings
            else:
                logger.error(f"❌ Número de embeddings inconsistente: {len(embeddings)} vs {len(processed_texts)}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro geral ao gerar embeddings: {e}")
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
            
            if test_embedding and len(test_embedding) == 384:
                logger.info("✅ Teste HuggingFace passou - sistema pronto")
                return True
            else:
                logger.error("❌ Teste HuggingFace falhou")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """Informações do modelo para debug"""
        return {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'api_provider': 'huggingface_inference_client',
            'has_api_key': bool(self.api_key),
            'preprocessing': 'licitacoes_brasileiras_optimized'
        } 