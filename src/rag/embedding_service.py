# Embedding service module - VoyageAI Integration
import numpy as np
import requests
import os
import logging
from typing import List, Optional
import time
import json

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Serviço de embeddings usando VoyageAI - Otimizado para Railway com fallbacks robustos"""
    
    def __init__(self, model_name: str = "voyage-3-large"):
        self.model_name = model_name
        self.api_key = os.getenv('VOYAGE_API_KEY')
        self.embedding_dim = 1024  # Dimensão do voyage-3-large
        
        # Configurações para Railway (rede mais lenta)
        self.base_timeout = 120  # Timeout aumentado para Railway
        self.max_retries = 5     # Mais tentativas
        self.backoff_base = 2    # Backoff exponencial
        
        if not self.api_key:
            logger.error("❌ VOYAGE_API_KEY não encontrada nas variáveis de ambiente")
            logger.error("💡 Configure a chave da VoyageAI para usar embeddings")
            self.api_key = None
        else:
            logger.info(f"✅ VoyageAI configurado: {model_name} ({self.embedding_dim} dims)")
            logger.info(f"🔧 Railway config: timeout={self.base_timeout}s, retries={self.max_retries}")
    
    def generate_embeddings(self, texts: List[str], batch_size: int = 64) -> Optional[List[List[float]]]:
        """Gera embeddings para uma lista de textos usando VoyageAI - Otimizado para Railway"""
        
        if not self.api_key:
            logger.error("❌ VoyageAI API key não configurada. Tentando OpenAI fallback...")
            return self._fallback_to_openai_embeddings(texts)
            
        try:
            logger.info(f"🔄 Gerando embeddings VoyageAI para {len(texts)} textos (Railway optimized)")
            
            # Reduzir batch size para Railway (rede mais limitada)
            all_embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size
            
            for i in range(0, len(texts), batch_size):
                batch_num = (i // batch_size) + 1
                batch_texts = texts[i:i + batch_size]
                
                logger.info(f"📦 Processando batch {batch_num}/{total_batches} ({len(batch_texts)} textos)")
                
                # Tentar processar o batch com retry robusto
                batch_embeddings = self._process_batch_with_retry(batch_texts, batch_num)
                
                if batch_embeddings:
                    all_embeddings.extend(batch_embeddings)
                    logger.info(f"✅ Batch {batch_num}: {len(batch_embeddings)} embeddings processados")
                else:
                    logger.error(f"❌ Batch {batch_num} falhou completamente. Tentando OpenAI fallback...")
                    # Tentar OpenAI para este batch específico
                    fallback_batch = self._fallback_to_openai_embeddings(batch_texts)
                    if fallback_batch:
                        all_embeddings.extend(fallback_batch)
                        logger.warning(f"⚠️ Batch {batch_num}: OpenAI fallback usado com sucesso")
                    else:
                        logger.error(f"❌ Batch {batch_num}: OpenAI também falhou, tentando local...")
                        # Último recurso: local
                        local_batch = self._fallback_to_local_embeddings(batch_texts)
                        if local_batch:
                            all_embeddings.extend(local_batch)
                            logger.warning(f"⚠️ Batch {batch_num}: Fallback local usado como último recurso")
                        else:
                            logger.error(f"❌ Batch {batch_num}: Todos os métodos falharam")
                            return None
                
                # Delay entre batches para não sobrecarregar Railway
                if batch_num < total_batches:
                    time.sleep(0.5)
            
            logger.info(f"🎉 {len(all_embeddings)} embeddings gerados com sucesso")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"❌ Erro geral ao gerar embeddings VoyageAI: {e}")
            logger.info("🔄 Tentando fallback completo para OpenAI...")
            fallback_result = self._fallback_to_openai_embeddings(texts)
            if fallback_result:
                return fallback_result
            
            logger.info("🔄 OpenAI também falhou, tentando local como último recurso...")
            return self._fallback_to_local_embeddings(texts)
    
    def _process_batch_with_retry(self, batch_texts: List[str], batch_num: int) -> Optional[List[List[float]]]:
        """Processa um batch com retry robusto e timeouts adaptativos"""
        
        for attempt in range(self.max_retries):
            try:
                # Timeout adaptativo: aumenta a cada tentativa
                timeout = self.base_timeout + (attempt * 30)
                
                # Preparar payload
                payload = {
                    "input": batch_texts,
                    "model": self.model_name,
                    "input_type": "document"
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Alicit-Railway/1.0"
                }
                
                logger.debug(f"🌐 Tentativa {attempt + 1}/{self.max_retries} - timeout: {timeout}s")
                
                # Usar session para reutilizar conexões
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.post(
                    "https://api.voyageai.com/v1/embeddings",
                    json=payload,
                    timeout=timeout,
                    verify=True  # Verificar SSL
                )
                
                # Verificar resposta
                if response.status_code == 200:
                    data = response.json()
                    batch_embeddings = [item["embedding"] for item in data["data"]]
                    logger.debug(f"✅ VoyageAI sucesso na tentativa {attempt + 1}")
                    return batch_embeddings
                
                elif response.status_code == 429:
                    # Rate limit - aguardar mais tempo
                    wait_time = self.backoff_base ** (attempt + 2)  # 4s, 8s, 16s, 32s, 64s
                    logger.warning(f"⚠️ Rate limit, aguardando {wait_time}s (tentativa {attempt + 1})")
                    time.sleep(wait_time)
                
                elif response.status_code in [500, 502, 503, 504]:
                    # Erros de servidor - retry com backoff
                    wait_time = self.backoff_base ** attempt  # 1s, 2s, 4s, 8s, 16s
                    logger.warning(f"⚠️ Erro servidor {response.status_code}, retry em {wait_time}s")
                    time.sleep(wait_time)
                
                else:
                    logger.error(f"❌ Erro API VoyageAI: {response.status_code}")
                    try:
                        error_data = response.json()
                        logger.error(f"📝 Detalhes: {error_data}")
                    except:
                        logger.error(f"📝 Response: {response.text[:200]}")
                    
                    # Para erros 4xx (exceto 429), não retry
                    if 400 <= response.status_code < 500 and response.status_code != 429:
                        break
                
            except requests.exceptions.Timeout:
                wait_time = self.backoff_base ** attempt
                logger.warning(f"⏱️ Timeout na tentativa {attempt + 1}, retry em {wait_time}s")
                time.sleep(wait_time)
                
            except requests.exceptions.ConnectionError as e:
                wait_time = self.backoff_base ** attempt
                logger.warning(f"🔌 Erro conexão na tentativa {attempt + 1}: {e}")
                logger.warning(f"🔄 Retry em {wait_time}s")
                time.sleep(wait_time)
                
            except requests.exceptions.SSLError as e:
                logger.error(f"🔒 Erro SSL: {e}")
                # Para SSL, tentar só mais uma vez
                if attempt < 2:
                    time.sleep(2)
                    continue
                else:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Erro inesperado na tentativa {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_base ** attempt)
        
        logger.error(f"❌ Batch {batch_num} falhou após {self.max_retries} tentativas")
        return None
    
    def _fallback_to_openai_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Fallback para embeddings OpenAI small (mais barato e rápido)"""
        try:
            logger.warning("🔄 Usando fallback para OpenAI embeddings (text-embedding-3-small)")
            
            openai_api_key = os.getenv('OPENAI_API_KEY')
            if not openai_api_key:
                logger.error("❌ OPENAI_API_KEY não encontrada. Tentando fallback local...")
                return self._fallback_to_local_embeddings(texts)
            
            import openai
            client = openai.OpenAI(api_key=openai_api_key)
            
            # Processar em batches menores para economizar tokens
            all_embeddings = []
            batch_size = 100  # OpenAI permite até 2048 inputs por request
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                logger.info(f"📦 OpenAI batch {batch_num}: {len(batch_texts)} textos")
                
                try:
                    # Usar modelo small (mais barato: $0.02/1M tokens vs $0.13/1M do large)
                    response = client.embeddings.create(
                        model="text-embedding-3-small",  # 1536 dimensões, mais barato
                        input=batch_texts,
                        encoding_format="float"
                    )
                    
                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)
                    
                    logger.info(f"✅ OpenAI batch {batch_num}: {len(batch_embeddings)} embeddings processados")
                    
                    # Rate limiting para não exceder limites
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ Erro no batch OpenAI {batch_num}: {e}")
                    return None
            
            logger.info(f"✅ OpenAI fallback gerou {len(all_embeddings)} embeddings")
            return all_embeddings
            
        except ImportError:
            logger.error("❌ Biblioteca openai não instalada. Tentando fallback local...")
            return self._fallback_to_local_embeddings(texts)
        except Exception as e:
            logger.error(f"❌ Fallback OpenAI falhou: {e}")
            logger.info("🔄 Tentando fallback local como último recurso...")
            return self._fallback_to_local_embeddings(texts)
    
    def _fallback_to_local_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Fallback para embeddings locais usando sentence-transformers (ÚLTIMO RECURSO)"""
        try:
            logger.warning("🔄 Usando fallback LOCAL para embeddings (sentence-transformers) - ÚLTIMO RECURSO")
            logger.warning("⚠️ Isso pode consumir bastante CPU/memória no Railway!")
            
            # Importar apenas quando necessário para economizar memória
            from services.sentence_transformer_service import SentenceTransformerService
            local_service = SentenceTransformerService()
            
            # Processar em batches menores para não sobrecarregar a memória
            all_embeddings = []
            batch_size = 16  # Muito menor para Railway
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = local_service.generate_embeddings(batch_texts)
                
                if batch_embeddings:
                    all_embeddings.extend(batch_embeddings)
                    logger.info(f"✅ Local batch {i//batch_size + 1}: {len(batch_embeddings)} embeddings")
                else:
                    logger.error(f"❌ Fallback local falhou no batch {i//batch_size + 1}")
                    return None
            
            logger.info(f"✅ Fallback local gerou {len(all_embeddings)} embeddings")
            logger.warning("⚠️ Considere configurar VoyageAI ou OpenAI para melhor performance")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"❌ Fallback local falhou: {e}")
            logger.error("❌ TODOS os métodos de embedding falharam!")
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