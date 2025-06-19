# Embedding service module - VoyageAI Integration
import numpy as np
import requests
import os
import logging
from typing import List, Optional
import time

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Serviço de embeddings usando VoyageAI - Otimizado para Railway"""
    
    def __init__(self, model_name: str = "voyage-3-large"):
        self.model_name = model_name
        self.api_key = os.getenv('VOYAGE_API_KEY')
        self.embedding_dim = 1024  # Dimensão do voyage-3-large
        
        if not self.api_key:
            logger.error("❌ VOYAGE_API_KEY não encontrada nas variáveis de ambiente")
            logger.error("💡 Configure a chave da VoyageAI para usar embeddings")
            self.api_key = None
        else:
            logger.info(f"✅ VoyageAI configurado: {model_name} ({self.embedding_dim} dims)")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 128) -> Optional[List[List[float]]]:
        """Gera embeddings para uma lista de textos usando VoyageAI - Otimizado para conta paga"""
        
        if not self.api_key:
            logger.error("❌ VoyageAI API key não configurada. Não é possível gerar embeddings.")
            return None
            
        try:
            logger.info(f"🔄 Gerando embeddings VoyageAI para {len(texts)} textos")
            
            # Com conta paga: 300 RPM e 1M TPM - sem necessidade de rate limiting agressivo
            all_embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_num = (i // batch_size) + 1
                batch_texts = texts[i:i + batch_size]
                
                logger.info(f"📦 Processando batch {batch_num}/{total_batches} ({len(batch_texts)} textos)")
                
                # Preparar payload
                payload = {
                    "input": batch_texts,
                    "model": self.model_name,
                    "input_type": "document"  # Para documentos
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Fazer requisição com retry simples
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = requests.post(
                            "https://api.voyageai.com/v1/embeddings",
                            json=payload,
                            headers=headers,
                            timeout=60
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            batch_embeddings = [item["embedding"] for item in data["data"]]
                            all_embeddings.extend(batch_embeddings)
                            
                            logger.info(f"✅ Batch {batch_num}: {len(batch_embeddings)} embeddings processados")
                            break
                            
                        elif response.status_code == 429:
                            # Rate limit - aguardar um pouco mais
                            wait_time = 2 ** attempt  # Backoff exponencial: 1s, 2s, 4s
                            logger.warning(f"⚠️ Rate limit no batch {batch_num}, aguardando {wait_time}s...")
                            time.sleep(wait_time)
                            
                        else:
                            logger.error(f"❌ Erro na API VoyageAI: {response.status_code} - {response.text}")
                            if attempt == max_retries - 1:
                                return None
                            time.sleep(1)
                            
                    except Exception as e:
                        logger.error(f"❌ Erro na requisição (tentativa {attempt + 1}): {e}")
                        if attempt == max_retries - 1:
                            return None
                        time.sleep(1)
                
                # Pequeno delay apenas se necessário (conta paga tem 300 RPM = 5 req/s)
                # Sem delay para máxima velocidade
            
            logger.info(f"🎉 {len(all_embeddings)} embeddings VoyageAI gerados com sucesso")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"❌ Erro geral ao gerar embeddings: {e}")
            return None
    
    def generate_single_embedding(self, text: str) -> Optional[List[float]]:
        """Gera embedding para um único texto"""
        result = self.generate_embeddings([text])
        return result[0] if result else None
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calcula similaridade cosseno entre dois embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular similaridade: {e}")
            return 0.0


# Classe de fallback para compatibilidade (caso alguém ainda importe SentenceTransformer)
class SentenceTransformerFallback:
    """Fallback para manter compatibilidade com código legado"""
    
    def __init__(self, *args, **kwargs):
        logger.warning("⚠️  SentenceTransformer foi substituído por VoyageAI")
        logger.warning("💡 Use EmbeddingService() em vez de SentenceTransformer()")
        self.embedding_service = EmbeddingService()
    
    def encode(self, texts, **kwargs):
        """Método de compatibilidade"""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.embedding_service.generate_embeddings(texts)
        return np.array(embeddings) if embeddings else np.array([])


# Para compatibilidade com imports antigos
SentenceTransformer = SentenceTransformerFallback 