#!/usr/bin/env python3
"""
Implementações de vetorização de texto para matching de licitações
Sistema multi-modal com cache inteligente e fallbacks
PRIORIDADE: Modelos 100% brasileiros especializados em licitações
"""

import os
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

from services.sentence_transformer_service import SentenceTransformerService
from services.embedding_cache_service import EmbeddingCacheService

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

class BrazilianTextVectorizer(BaseTextVectorizer):
    """
    🇧🇷 VETORIZADOR 100% BRASILEIRO para licitações
    
    Especializado em:
    - Português brasileiro (NeralMind BERT)
    - Terminologia jurídica de licitações
    - Contexto de compras públicas brasileiras
    - Siglas e termos técnicos nacionais
    
    Hierarquia nacional:
    1. 🧠 NeralMind BERT LOCAL (neuralmind/bert-base-portuguese-cased)
    2. 🚀 NeralMind via HuggingFace API (fallback)
    3. 🎯 Multilingual BERT especializado em português
    """
    
    def __init__(self, db_manager=None):
        # Importar db_manager se não fornecido
        if db_manager is None:
            from config.database import db_manager as default_db_manager
            self.db_manager = default_db_manager
        else:
            self.db_manager = db_manager
        
        # Inicializar cache brasileiro
        self.cache_service = EmbeddingCacheService(self.db_manager)
        
        # Vetorizadores brasileiros ordenados por prioridade
        self.brazilian_vectorizers = []
        
        print("🇧🇷 ===== INICIALIZANDO SISTEMA BRASILEIRO DE EMBEDDINGS =====")
        
        # 1. NeralMind BERT LOCAL (PRINCIPAL - 100% Brasileiro)
        try:
            self.neuralmind_local = SentenceTransformerService(
                model_name="neuralmind/bert-base-portuguese-cased"
            )
            self.brazilian_vectorizers.append(('neuralmind-local', self.neuralmind_local))
            print("🧠 NeralMind BERT LOCAL carregado como PRINCIPAL")
            print(f"   📊 Modelo: neuralmind/bert-base-portuguese-cased")
            print(f"   🎯 Especialização: Português brasileiro + licitações")
            print(f"   📏 Dimensões: {self.neuralmind_local.get_model_info().get('dimensions', 'N/A')}")
            print(f"   💾 Otimizado para: Railway CPU + Cache Redis")
        except Exception as e:
            print(f"⚠️ NeralMind LOCAL falhou: {e}")
            self.neuralmind_local = None
        
        # 2. NeralMind via HuggingFace API (FALLBACK BRASILEIRO)
        try:
            from services.neuralmind_embedding_service import NeuralMindEmbeddingService
            self.neuralmind_api = NeuralMindEmbeddingService()
            
            # Teste rápido e silencioso
            test_result = self.neuralmind_api.generate_single_embedding("licitação teste")
            if test_result and len(test_result) > 300:  # Qualquer dimensão válida
                self.brazilian_vectorizers.append(('neuralmind-api', self.neuralmind_api))
                print("🚀 NeralMind HuggingFace API como fallback")
                print(f"   📊 Dimensões: {len(test_result)}")
                print(f"   🎯 Especialização: Multilingual otimizado para português")
            else:
                print("⚠️ NeralMind API: teste falhou, pulando...")
        except Exception as e:
            print(f"⚠️ NeralMind API falhou: {e}")
        
        # 3. Multilingual BERT LOCAL (FALLBACK NACIONAL)
        try:
            self.multilingual_local = SentenceTransformerService(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            self.brazilian_vectorizers.append(('multilingual-local', self.multilingual_local))
            print("🌎 Multilingual BERT LOCAL como fallback nacional")
            print(f"   📏 Dimensões: {self.multilingual_local.get_model_info().get('dimensions', 'N/A')}")
        except Exception as e:
            print(f"⚠️ Multilingual LOCAL falhou: {e}")
        
        # 4. Sistema internacional apenas se NADA brasileiro funcionar
        self.international_vectorizers = []
        self._init_international_fallbacks()
        
        # Verificar se temos pelo menos um sistema brasileiro
        if not self.brazilian_vectorizers:
            print("❌ NENHUM sistema brasileiro funcionou! Usando fallback internacional...")
            self.vectorizers = self.international_vectorizers
        else:
            self.vectorizers = self.brazilian_vectorizers + self.international_vectorizers
            print(f"✅ Sistema brasileiro: {len(self.brazilian_vectorizers)} vetorizadores nacionais disponíveis")
        
        if not self.vectorizers:
            print("❌ CRÍTICO: Nenhum vetorizador funcionou! Usando MockVectorizer...")
            self.vectorizers.append(('mock', MockTextVectorizer()))
        
        print(f"🎯 Prioridade FINAL: {' → '.join([name for name, _ in self.vectorizers])}")
        print("🇧🇷 ===== SISTEMA BRASILEIRO PRONTO =====")
    
    def _init_international_fallbacks(self):
        """Inicializa fallbacks internacionais apenas se necessário"""
        # VoyageAI
        if os.getenv('VOYAGE_API_KEY'):
            try:
                self.voyage_service = VoyageAITextVectorizer()
                self.international_vectorizers.append(('voyage-ai', self.voyage_service))
                print("🚢 VoyageAI disponível como fallback internacional")
            except Exception as e:
                print(f"⚠️ VoyageAI falhou: {e}")
        
        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_service = OpenAITextVectorizer()
                self.international_vectorizers.append(('openai', self.openai_service))
                print("🔥 OpenAI disponível como último recurso")
            except Exception as e:
                print(f"⚠️ OpenAI falhou: {e}")
    
    def vectorize(self, text: str) -> List[float]:
        """Vetorização priorizando sistemas brasileiros"""
        if not text or not text.strip():
            return []
        
        # Preprocessar texto com otimizações brasileiras
        clean_text = self._preprocess_brazilian_text(text)
        if not clean_text:
            return []
        
        # Tentar cada vetorizador na ordem de prioridade (brasileiros primeiro)
        for model_name, vectorizer in self.vectorizers:
            # Verificar cache primeiro
            cached_embedding = self.cache_service.get_embedding_from_cache(clean_text, model_name)
            if cached_embedding:
                logger.debug(f"⚡ Cache hit brasileiro para {model_name}")
                return cached_embedding
            
            # Gerar embedding
            try:
                if 'local' in model_name or 'neuralmind-local' in model_name or 'multilingual-local' in model_name:
                    embedding = vectorizer.generate_single_embedding(clean_text)
                else:
                    embedding = vectorizer.vectorize(clean_text)
                
                if embedding:
                    # Salvar no cache
                    self.cache_service.save_embedding_to_cache(clean_text, embedding, model_name)
                    
                    # Log diferente para sistemas brasileiros
                    if model_name in ['neuralmind-local', 'neuralmind-api', 'multilingual-local']:
                        logger.debug(f"🇧🇷 Sucesso brasileiro com {model_name}")
                    else:
                        logger.debug(f"🌍 Fallback internacional com {model_name}")
                    
                    return embedding
                    
            except Exception as e:
                logger.warning(f"❌ {model_name} falhou: {e}")
                continue
        
        logger.error("❌ Todos os vetorizadores (brasileiros + internacionais) falharam")
        return []
    
    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vetorização em lote priorizando sistemas brasileiros"""
        if not texts:
            return []
        
        # Preprocessar textos com otimizações brasileiras
        clean_texts = []
        for text in texts:
            clean_text = self._preprocess_brazilian_text(text) if text else ""
            clean_texts.append(clean_text)
        
        # Cache inteligente (mesmo código, mas com prioridade brasileira)
        cached_embeddings = {}
        texts_to_process = []
        text_indices = {}
        
        for i, text in enumerate(clean_texts):
            if not text:
                continue
                
            # Verificar cache priorizando modelos brasileiros
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
        
        logger.info(f"📊 Cache brasileiro: {len(cached_embeddings)} hits, {len(texts_to_process)} a processar")
        
        # Processar textos priorizando sistemas brasileiros
        new_embeddings = {}
        if texts_to_process:
            for model_name, vectorizer in self.vectorizers:
                try:
                    if 'local' in model_name or 'neuralmind-local' in model_name or 'multilingual-local' in model_name:
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
                        
                        # Log especial para sistemas brasileiros
                        if model_name in ['neuralmind-local', 'neuralmind-api', 'multilingual-local']:
                            logger.info(f"🇧🇷 Lote processado com sistema brasileiro: {model_name}")
                        else:
                            logger.info(f"🌍 Lote processado com fallback internacional: {model_name}")
                        break
                        
                except Exception as e:
                    logger.warning(f"❌ {model_name} falhou no lote: {e}")
                    continue
        
        # Combinar resultados
        final_embeddings = []
        for i in range(len(clean_texts)):
            if i in cached_embeddings:
                final_embeddings.append(cached_embeddings[i])
            elif i in new_embeddings:
                final_embeddings.append(new_embeddings[i])
            else:
                final_embeddings.append([])
        
        return final_embeddings
    
    def _preprocess_brazilian_text(self, text: str) -> str:
        """Preprocessamento especializado para textos brasileiros de licitação"""
        if not text:
            return ""
        
        # Preprocessamento básico
        clean_text = self.preprocess_text(text)
        
        # Expandir siglas brasileiras comuns em licitações
        import re
        brazilian_expansions = {
            r'\bTI\b': 'TI tecnologia da informação',
            r'\bRH\b': 'RH recursos humanos',
            r'\bCFTV\b': 'CFTV circuito fechado de televisão segurança',
            r'\bGPS\b': 'GPS sistema de posicionamento global rastreamento',
            r'\bEPP\b': 'EPP empresa de pequeno porte',
            r'\bME\b': 'ME microempresa',
            r'\bSRP\b': 'SRP sistema de registro de preços',
            r'\bTCU\b': 'TCU tribunal de contas da união',
            r'\bCGU\b': 'CGU controladoria geral da união',
            r'\bPNCP\b': 'PNCP portal nacional de contratações públicas'
        }
        
        # Aplicar expansões (mantém sigla original + adiciona contexto)
        for sigla_pattern, expansao in brazilian_expansions.items():
            clean_text = re.sub(
                sigla_pattern, 
                expansao, 
                clean_text, 
                flags=re.IGNORECASE
            )
        
        return clean_text
    
    def get_brazilian_status(self) -> dict:
        """Status específico dos sistemas brasileiros"""
        brazilian_status = {}
        international_status = {}
        
        for model_name, vectorizer in self.vectorizers:
            status = {
                'available': True,
                'type': 'brazilian' if model_name in ['neuralmind-local', 'neuralmind-api', 'multilingual-local'] else 'international'
            }
            
            if hasattr(vectorizer, 'get_model_info'):
                status.update(vectorizer.get_model_info())
            
            if status['type'] == 'brazilian':
                brazilian_status[model_name] = status
            else:
                international_status[model_name] = status
        
        return {
            'brazilian_systems': brazilian_status,
            'international_fallbacks': international_status,
            'primary_system': list(brazilian_status.keys())[0] if brazilian_status else 'none',
            'total_brazilian': len(brazilian_status)
        }

# Manter HybridTextVectorizer para compatibilidade, mas agora usando BrazilianTextVectorizer como base
class HybridTextVectorizer(BrazilianTextVectorizer):
    """
    Sistema híbrido ATUALIZADO baseado no sistema brasileiro
    
    NOVA ordem de prioridade:
    1. 🇧🇷 SISTEMAS BRASILEIROS (via BrazilianTextVectorizer)
    2. 🌍 Fallbacks internacionais apenas se necessário
    
    Este é um alias para BrazilianTextVectorizer com nome mantido para compatibilidade
    """
    
    def __init__(self, db_manager=None):
        print("🔄 HybridTextVectorizer agora usa sistema 100% brasileiro como base")
        super().__init__(db_manager)

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