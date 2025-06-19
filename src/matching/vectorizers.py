#!/usr/bin/env python3
"""
Vetorizadores de texto para matching semântico com cache inteligente
"""

import os
import logging
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
import numpy as np

from src.services.sentence_transformer_service import SentenceTransformerService
from src.services.embedding_cache_service import EmbeddingCacheService

logger = logging.getLogger(__name__)

class BaseTextVectorizer(ABC):
    """Interface base para vetorizadores de texto"""
    
    @abstractmethod
    def vectorize(self, text: str) -> List[float]:
        """Vetoriza um único texto"""
        pass
    
    @abstractmethod
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetoriza múltiplos textos"""
        pass
    
    def preprocess_text(self, text: str) -> str:
        """Preprocessamento básico do texto"""
        if not text:
            return ""
        
        # Limpeza básica
        text = text.strip()
        
        # Remover caracteres especiais problemáticos
        text = text.replace('\x00', '')  # Remove null bytes
        
        return text

class HybridTextVectorizer(BaseTextVectorizer):
    """
    Sistema híbrido OTIMIZADO para licitações brasileiras
    
    Ordem de prioridade:
    1. 🧠 SentenceTransformers LOCAL (NeralMind BERT português)
    2. 🚀 NeralMind via HuggingFace API (fallback se local falhar)  
    3. 🚢 VoyageAI (fallback internacional)
    4. 🔥 OpenAI (último recurso)
    """
    
    def __init__(self, db_manager=None):
        # Importar db_manager se não fornecido
        if db_manager is None:
            from src.config.database import db_manager as default_db_manager
            self.db_manager = default_db_manager
        else:
            self.db_manager = db_manager
        
        # Inicializar cache
        self.cache_service = EmbeddingCacheService(self.db_manager)
        
        # Hierarquia de vetorizadores (ordem de prioridade)
        self.vectorizers = []
        
        # 1. SentenceTransformers LOCAL (PRINCIPAL - especializado em português)
        try:
            self.st_service = SentenceTransformerService()
            self.vectorizers.append(('sentence-transformers', self.st_service))
            print("🧠 SentenceTransformers LOCAL carregado como PRINCIPAL")
            print(f"   📊 Modelo: {self.st_service.model_name}")
            print(f"   🎯 Especializado em: Português brasileiro")
            print(f"   📏 Dimensões: {self.st_service.get_model_info().get('dimensions', 'N/A')}")
        except Exception as e:
            print(f"⚠️ SentenceTransformers LOCAL falhou: {e}")
            self.st_service = None
        
        # 2. NeralMind via HuggingFace API (FALLBACK PORTUGUÊS)
        try:
            from src.services.neuralmind_embedding_service import NeuralMindEmbeddingService
            self.neuralmind_service = NeuralMindEmbeddingService()
            
            # Teste rápido da conexão (sem log verboso)
            test_result = self.neuralmind_service.generate_single_embedding("teste")
            if test_result and len(test_result) == 768:
                self.vectorizers.append(('neuralmind-bert', self.neuralmind_service))
                print("🧠 NeralMind HuggingFace como fallback português (768d)")
            else:
                print("⚠️ NeralMind HF: teste falhou, pulando...")
        except Exception as e:
            print(f"⚠️ NeralMind HuggingFace falhou: {e}")
        
        # 3. VoyageAI (FALLBACK INTERNACIONAL)
        if os.getenv('VOYAGE_API_KEY'):
            try:
                self.voyage_service = VoyageAITextVectorizer()
                self.vectorizers.append(('voyage-ai', self.voyage_service))
                print("🚢 VoyageAI como fallback internacional")
            except Exception as e:
                print(f"⚠️ VoyageAI falhou: {e}")
        
        # 4. OpenAI (ÚLTIMO RECURSO)
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_service = OpenAITextVectorizer()
                self.vectorizers.append(('openai', self.openai_service))
                print("🔥 OpenAI como último recurso")
            except Exception as e:
                print(f"⚠️ OpenAI falhou: {e}")
        
        if not self.vectorizers:
            print("❌ TODOS os vetorizadores falharam! Usando MockVectorizer...")
            self.vectorizers.append(('mock', MockTextVectorizer()))
        
        print(f"✅ Sistema híbrido: {len(self.vectorizers)} vetorizadores disponíveis")
        print(f"🎯 Prioridade: {' → '.join([name for name, _ in self.vectorizers])}")
    
    def vectorize(self, text: str) -> List[float]:
        """Vetorização com cache inteligente e fallback"""
        if not text or not text.strip():
            return []
        
        # Preprocessar texto
        clean_text = self.preprocess_text(text)
        if not clean_text:
            return []
        
        # Tentar cada vetorizador na ordem de prioridade
        for model_name, vectorizer in self.vectorizers:
            # Verificar cache primeiro
            cached_embedding = self.cache_service.get_embedding_from_cache(clean_text, model_name)
            if cached_embedding:
                logger.debug(f"⚡ Cache hit para {model_name}")
                return cached_embedding
            
            # Gerar embedding
            try:
                if model_name == 'sentence-transformers':
                    embedding = vectorizer.generate_single_embedding(clean_text)
                else:
                    embedding = vectorizer.vectorize(clean_text)
                
                if embedding:
                    # Salvar no cache
                    self.cache_service.save_embedding_to_cache(clean_text, embedding, model_name)
                    logger.debug(f"✅ Sucesso com {model_name}")
                    return embedding
                    
            except Exception as e:
                logger.warning(f"❌ {model_name} falhou: {e}")
                continue
        
        logger.error("❌ Todos os vetorizadores falharam")
        return []
    
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetorização em lote com cache inteligente"""
        if not texts:
            return []
        
        # Preprocessar textos
        clean_texts = []
        for text in texts:
            clean_text = self.preprocess_text(text) if text else ""
            clean_texts.append(clean_text)
        
        # Separar textos que já estão no cache vs que precisam ser processados
        cached_embeddings = {}
        texts_to_process = []
        text_indices = {}
        
        for i, text in enumerate(clean_texts):
            if not text:
                continue
                
            # Verificar cache para cada vetorizador
            embedding_found = False
            for model_name, _ in self.vectorizers:
                cached = self.cache_service.get_embedding_from_cache(text, model_name)
                if cached:
                    cached_embeddings[i] = cached
                    embedding_found = True
                    break
            
            if not embedding_found:
                texts_to_process.append(text)
                text_indices[len(texts_to_process) - 1] = i
        
        logger.info(f"📊 Cache hits: {len(cached_embeddings)}, A processar: {len(texts_to_process)}")
        
        # Processar textos que não estão no cache
        new_embeddings = {}
        if texts_to_process:
            for model_name, vectorizer in self.vectorizers:
                try:
                    if model_name == 'sentence-transformers':
                        batch_result = vectorizer.generate_embeddings(texts_to_process)
                    else:
                        batch_result = vectorizer.batch_vectorize(texts_to_process)
                    
                    if batch_result and len(batch_result) == len(texts_to_process):
                        # Salvar novos embeddings no cache
                        for j, embedding in enumerate(batch_result):
                            original_index = text_indices[j]
                            new_embeddings[original_index] = embedding
                            
                            # Cache
                            self.cache_service.save_embedding_to_cache(
                                texts_to_process[j], embedding, model_name
                            )
                        
                        logger.info(f"✅ Lote processado com {model_name}")
                        break
                        
                except Exception as e:
                    logger.warning(f"❌ {model_name} falhou no lote: {e}")
                    continue
        
        # Combinar resultados (cache + novos)
        final_embeddings = []
        for i in range(len(clean_texts)):
            if i in cached_embeddings:
                final_embeddings.append(cached_embeddings[i])
            elif i in new_embeddings:
                final_embeddings.append(new_embeddings[i])
            else:
                final_embeddings.append([])  # Texto vazio ou falha
        
        return final_embeddings


class VoyageAITextVectorizer(BaseTextVectorizer):
    """Vetorizador usando VoyageAI API"""
    
    def __init__(self):
        import voyageai
        self.client = voyageai.Client(api_key=os.getenv('VOYAGE_API_KEY'))
        self.model = "voyage-3-large"
    
    def vectorize(self, text: str) -> List[float]:
        """Vetoriza um único texto"""
        try:
            clean_text = self.preprocess_text(text)
            if not clean_text:
                return []
            
            result = self.client.embed([clean_text], model=self.model)
            return result.embeddings[0] if result.embeddings else []
        except Exception as e:
            logger.error(f"Erro VoyageAI: {e}")
            return []
    
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetoriza múltiplos textos"""
        try:
            clean_texts = [self.preprocess_text(text) for text in texts if text]
            if not clean_texts:
                return []
            
            result = self.client.embed(clean_texts, model=self.model)
            return result.embeddings if result.embeddings else []
        except Exception as e:
            logger.error(f"Erro VoyageAI batch: {e}")
            return []


class OpenAITextVectorizer(BaseTextVectorizer):
    """Vetorizador usando OpenAI embeddings"""
    
    def __init__(self):
        import openai
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = "text-embedding-3-small"
    
    def vectorize(self, text: str) -> List[float]:
        """Vetoriza um único texto"""
        try:
            clean_text = self.preprocess_text(text)
            if not clean_text:
                return []
            
            response = self.client.embeddings.create(
                model=self.model,
                input=clean_text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro OpenAI: {e}")
            return []
    
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetoriza múltiplos textos"""
        try:
            clean_texts = [self.preprocess_text(text) for text in texts if text]
            if not clean_texts:
                return []
            
            response = self.client.embeddings.create(
                model=self.model,
                input=clean_texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Erro OpenAI batch: {e}")
            return []


class MockTextVectorizer(BaseTextVectorizer):
    """Vetorizador mock para testes"""
    
    def __init__(self):
        self.dimension = 384  # Dimensão padrão
    
    def vectorize(self, text: str) -> List[float]:
        """Gera embedding mock baseado no hash do texto"""
        try:
            clean_text = self.preprocess_text(text)
            if not clean_text:
                return []
            
            # Gerar vetor mock baseado no hash do texto
            import hashlib
            hash_bytes = hashlib.md5(clean_text.encode()).digest()
            
            # Converter para floats normalizados
            vector = []
            for i in range(self.dimension):
                byte_index = i % len(hash_bytes)
                normalized_val = (hash_bytes[byte_index] / 255.0) - 0.5  # -0.5 a 0.5
                vector.append(normalized_val)
            
            return vector
        except Exception as e:
            logger.error(f"Erro MockVectorizer: {e}")
            return []
    
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetoriza múltiplos textos"""
        return [self.vectorize(text) for text in texts]




def calculate_cosine_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calcula similaridade cosseno entre dois embeddings"""
    try:
        if not embedding1 or not embedding2:
            return 0.0
        
        # Converter para arrays numpy
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calcular similaridade cosseno
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
        
    except Exception as e:
        logger.error(f"Erro no cálculo de similaridade: {e}")
        return 0.0


def calculate_enhanced_similarity(embedding1: List[float], embedding2: List[float], 
                                text1: str, text2: str) -> tuple[float, str]:
    """
    Similaridade aprimorada com análise contextual
    Retorna (score, justificativa)
    """
    try:
        # Similaridade base
        base_similarity = calculate_cosine_similarity(embedding1, embedding2)
        
        if base_similarity < 0.3:
            return base_similarity, "Similaridade baixa - contextos diferentes"
        
        # Análise de palavras-chave comuns
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Palavras-chave técnicas importantes
        tech_keywords = [
            'software', 'sistema', 'tecnologia', 'informática', 'dados',
            'desenvolvimento', 'manutenção', 'suporte', 'consultoria',
            'impressora', 'equipamento', 'hardware', 'infraestrutura'
        ]
        
        common_tech_words = []
        for keyword in tech_keywords:
            if keyword in text1_lower and keyword in text2_lower:
                common_tech_words.append(keyword)
        
        # Ajustar score baseado em palavras-chave
        if common_tech_words:
            boost = min(0.1, len(common_tech_words) * 0.02)
            adjusted_score = min(1.0, base_similarity + boost)
            justificativa = f"Similaridade: {base_similarity:.3f} + boost técnico ({', '.join(common_tech_words[:3])})"
        else:
            adjusted_score = base_similarity
            justificativa = f"Similaridade semântica: {base_similarity:.3f}"
        
        return adjusted_score, justificativa
        
    except Exception as e:
        logger.error(f"Erro na similaridade aprimorada: {e}")
        return base_similarity if 'base_similarity' in locals() else 0.0, "Erro no cálculo"