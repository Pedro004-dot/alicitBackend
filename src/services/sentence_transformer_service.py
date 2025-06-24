# src/services/sentence_transformer_service.py
import torch
import logging
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

class SentenceTransformerService:
    """Sentence Transformers otimizado para Railway"""
    
    _instances = {}  # Cache de instâncias por modelo
    
    def __new__(cls, model_name: str = "neuralmind/bert-base-portuguese-cased"):
        # Implementar singleton por modelo
        if model_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[model_name] = instance
            instance._initialized = False
        return cls._instances[model_name]
    
    def __init__(self, model_name: str = "neuralmind/bert-base-portuguese-cased"):
        # Evitar re-inicialização
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.model_name = model_name
        self.device = 'cpu'  # Railway não tem GPU
        self.model = None
        
        # Configurações de otimização para CPU
        self._configure_cpu_optimization()
        
        # Carregar modelo apenas uma vez
        self._load_model()
        self._initialized = True
    
    def _configure_cpu_optimization(self):
        """Otimizações específicas para CPU no Railway"""
        # Configurar PyTorch para CPU
        torch.set_num_threads(2)  # Railway tem 2 vCPUs
        os.environ['OMP_NUM_THREADS'] = '2'
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        
        # Configurações de memória
        torch.backends.cudnn.enabled = False
        
        logger.info("🔧 Configurações CPU aplicadas para Railway")
    
    def _load_model(self):
        """Carrega modelo apenas uma vez por instância"""
        try:
            logger.info(f"📥 Carregando {self.model_name}...")
            
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=os.getenv('TRANSFORMERS_CACHE', './cache/transformers')
            )
            
            # Configurações de inferência
            self.model.eval()  # Modo de avaliação
            
            # Configurar para usar menos memória
            if hasattr(self.model._modules['0'], 'auto_model'):
                self.model._modules['0'].auto_model.config.use_cache = False
            
            logger.info(f"✅ Modelo carregado: {self.model_name}")
            logger.info(f"📊 Dimensões: {self.model.get_sentence_embedding_dimension()}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar modelo: {e}")
            self.model = None
            raise
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 32) -> Optional[List[List[float]]]:
        """Gera embeddings otimizado para CPU"""
        if not self.model:
            logger.error("❌ Modelo não carregado")
            return None
        
        if not texts:
            return []
        
        try:
            logger.info(f"🔄 Gerando embeddings ST para {len(texts)} textos")
            
            # Preprocessing otimizado
            processed_texts = [self._preprocess_text(text) for text in texts]
            
            # Remover textos vazios
            valid_texts = [text for text in processed_texts if text.strip()]
            
            if not valid_texts:
                logger.warning("⚠️ Nenhum texto válido encontrado")
                return []
            
            # Gerar embeddings em batches pequenos para Railway
            all_embeddings = []
            
            with torch.no_grad():  # Economizar memória
                for i in range(0, len(valid_texts), batch_size):
                    batch = valid_texts[i:i + batch_size]
                    
                    logger.debug(f"📦 Processando batch {i//batch_size + 1}")
                    
                    # Encoding otimizado
                    batch_embeddings = self.model.encode(
                        batch,
                        batch_size=len(batch),
                        show_progress_bar=False,
                        convert_to_numpy=True,
                        normalize_embeddings=True  # Normalização para melhor similaridade
                    )
                    
                    # Converter para lista de listas
                    for embedding in batch_embeddings:
                        all_embeddings.append(embedding.tolist())
            
            logger.info(f"✅ {len(all_embeddings)} embeddings ST gerados")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar embeddings ST: {e}")
            return None
    
    def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Gera embedding único"""
        result = self.generate_embeddings([text])
        return result[0] if result else None
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocessing otimizado para português"""
        if not text:
            return ""
        
        # Limpeza básica
        text = text.strip()
        
        # Limitar tamanho (BERT tem limite de 512 tokens)
        if len(text) > 2000:  # ~500 tokens aproximadamente
            text = text[:2000] + "..."
        
        return text
    
    def get_model_info(self) -> dict:
        """Informações do modelo"""
        if not self.model:
            return {'status': 'not_loaded'}
        
        return {
            'model_name': self.model_name,
            'device': self.device,
            'dimensions': self.model.get_sentence_embedding_dimension(),
            'max_seq_length': getattr(self.model, 'max_seq_length', 512),
            'status': 'loaded'
        }