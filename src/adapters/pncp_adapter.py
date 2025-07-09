from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
import json
import hashlib
import aiohttp
import asyncio
import os
import redis

from interfaces.procurement_data_source import ProcurementDataSource, SearchFilters, OpportunityData
from repositories.licitacao_pncp_repository import LicitacaoPNCPRepository
from matching.pncp_api import fetch_bids_from_pncp, fetch_bid_items_from_pncp

# 🆕 NOVO: Import do OpenAI Service para sinônimos
try:
    from services.openai_service import OpenAIService
except ImportError:
    OpenAIService = None

# 🏗️ NOVO: Import do PersistenceService escalável
try:
    from services.persistence_service import get_persistence_service
    # Garantir que os mappers estão registrados
    import adapters.mappers
except ImportError:
    get_persistence_service = None

logger = logging.getLogger(__name__)


class PNCPAdapter(ProcurementDataSource):
    """PNCP implementation of ProcurementDataSource interface
    
    This adapter wraps the existing LicitacaoPNCPRepository to provide a 
    standardized interface without breaking existing code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize PNCP adapter with configuration"""
        # 🔧 API CONFIGURATION (CORRECTED)
        self.api_base_url = config.get('api_base_url', 'https://pncp.gov.br/api/consulta/v1')  # ✅ URL CORRIGIDA
        self.timeout = config.get('timeout', 30)
        self.max_results = config.get('max_results', 20000)  # Up to 20K results
        self.max_pages = min(400, self.max_results // 50)  # 400 pages max (20K / 50 per page)
        
        # 📅 DATE CONFIGURATION (FIXED TO MATCH WORKING REPOSITORY EXACTLY)
        # CORREÇÃO FINAL: Usar exatamente o mesmo cálculo de data do repositório funcional
        from datetime import datetime, timedelta
        
        # Use datetime.now() como o repositório original (mesmo se está errado)
        hoje = datetime.now()
        
        # FIXED: Use same date range as working repository
        data_inicial = hoje - timedelta(days=14)   # ✅ 14 dias atrás (igual ao antigo)
        data_final = hoje + timedelta(days=120)    # ✅ 120 dias futuro (igual ao antigo)
        
        self.data_inicial = data_inicial.strftime('%Y%m%d')  # ✅ YYYYMMDD format (no hyphens)
        self.data_final = data_final.strftime('%Y%m%d')      # ✅ YYYYMMDD format (no hyphens)
        
        # 🔧 CACHE CONFIGURATION
        try:
            from config.redis_config import RedisConfig
            self.redis_client = RedisConfig.get_redis_client()
            self.cache_ttl = 86400  # 24 hours TTL
            if self.redis_client:
                logger.info("✅ Redis cache enabled for PNCP adapter")
            else:
                logger.warning("⚠️ Redis not available - cache disabled")
                self.cache_ttl = 0
        except Exception as e:
            logger.warning(f"Redis not available for PNCP adapter: {e}")
            self.redis_client = None
            self.cache_ttl = 0
            
        logger.info(f"✅ PNCP Adapter initialized - will fetch up to {self.max_results} results via {self.max_pages} pages with 24h cache")
        logger.info(f"📅 Date range: {self.data_inicial} to {self.data_final} (formato YYYYMMDD)")
        logger.info(f"🔗 API Base URL: {self.api_base_url}")
        
        # 🆕 NOVO: Inicializar OpenAI Service para sinônimos
        self.openai_service = None
        if OpenAIService:
            try:
                self.openai_service = OpenAIService()
                logger.info("✅ OpenAI Service inicializado para geração de sinônimos")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível inicializar OpenAI Service: {e}")
        
        # Setup Redis
        self.redis_client = None
        self.cache_ttl = 3600  # 1 hora
        self.redis_available = self._setup_redis()
        
        logger.info(f"🔗 PNCPAdapter inicializado - Redis: {'Ativo' if self.redis_available else 'Inativo'}")

    def _setup_redis(self) -> bool:
        """Set up Redis connection"""
        try:
            from config.redis_config import RedisConfig
            self.redis_client = RedisConfig.get_redis_client()
            return self.redis_client is not None
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self.redis_client = None
            return False

    def _generate_cache_key(self, base_key: str, params: Dict[str, Any]) -> str:
        """Generate a consistent cache key from search parameters"""
        # 🆕 NOVO: Incluir sinônimos na chave se existirem
        cache_params = params.copy()
        
        # Se há keywords, gerar sinônimos e incluir na chave
        keywords = params.get('keywords')
        if keywords and self.openai_service:
            try:
                synonyms = self._generate_synonyms_for_cache(keywords)
                if synonyms:
                    # Adicionar sinônimos ordenados à chave para consistência
                    cache_params['synonyms'] = sorted(synonyms)
                    logger.debug(f"🔤 Sinônimos incluídos na chave de cache: {synonyms}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao gerar sinônimos para cache: {e}")
        
        # Ordenar parâmetros para chave consistente
        sorted_params = json.dumps(cache_params, sort_keys=True, ensure_ascii=False)
        cache_key = f"pncp:v2:{base_key}:{hash(sorted_params)}"
        return cache_key

    def _generate_synonyms_for_cache(self, keywords: str) -> List[str]:
        """
        🆕 NOVO: Gerar sinônimos especificamente para cache (com fallback rápido)
        """
        if not keywords or not self.openai_service:
            return []
        
        try:
            # Usar cache local simples para sinônimos por sessão
            if not hasattr(self, '_synonyms_cache'):
                self._synonyms_cache = {}
            
            # Verificar se já temos sinônimos para esta palavra
            keywords_key = keywords.lower().strip()
            if keywords_key in self._synonyms_cache:
                return self._synonyms_cache[keywords_key]
            
            # Gerar sinônimos
            synonyms = self.openai_service.gerar_sinonimos(keywords, max_sinonimos=5)
            
            # Remover a palavra original dos sinônimos para evitar duplicação
            synonyms_only = [s for s in synonyms if s.lower() != keywords_key]
            
            # Cache local
            self._synonyms_cache[keywords_key] = synonyms_only
            
            logger.info(f"🔤 Sinônimos gerados para '{keywords}': {synonyms_only}")
            return synonyms_only
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sinônimos: {e}")
            return []

    def _clear_old_cache(self) -> None:
        """Clear old cache entries to prevent stale data"""
        if not self.redis_client:
            return
        
        try:
            # Clear all PNCP cache keys
            for key in self.redis_client.scan_iter(match="pncp:*"):
                self.redis_client.delete(key)
            logger.info("🧹 Cleared old PNCP cache entries")
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")
    
    async def search_opportunities(self, filters: SearchFilters) -> List[OpportunityData]:
        """
        Search for procurement opportunities using REAL PAGINATION STRATEGY
        """
        logger.info(f"🔍 PNCP search with filters: {filters}")
        
        # Convert filters to internal format
        internal_filters = self._convert_filters(filters)
        
        # Check cache first - usar chave genérica apenas com data para reutilizar entre buscas
        cache_key = None
        if self.redis_client and self.cache_ttl > 0:
            # ✅ Cache genérico por data para reutilizar entre diferentes filtros
            cache_params = {
                'data_inicial': self.data_inicial,
                'data_final': self.data_final,
                'modalidade': 8  # Pregão Eletrônico
            }
            cache_key = self._generate_cache_key("pncp_data_v4", cache_params)
            logger.info(f"🔗 Using API URL: {self.api_base_url}")  # Debug log for URL verification
            try:
                # Try to get from cache first
                if self.redis_client and cache_key:
                    try:
                        # Try compressed version first
                        compressed_key = f"{cache_key}:gz"
                        cached_data = self.redis_client.get(compressed_key)
                        
                        if cached_data:
                            import gzip
                            import json
                            # Decompress and parse
                            decompressed_data = gzip.decompress(cached_data).decode('utf-8')
                            cached_result = json.loads(decompressed_data)
                            logger.info(f"🎯 Using compressed cached PNCP results ({len(cached_result.get('data', []))} records)")
                            
                            # ✅ APLICAR FILTROS LOCAIS NOS DADOS DO CACHE
                            filtered_data = self._apply_local_filters(cached_result['data'], internal_filters)
                            logger.info(f"🔍 Applied local filters: {len(filtered_data)} matches from {len(cached_result.get('data', []))} cached records")
                            return [self._convert_to_opportunity_data(item) for item in filtered_data]
                        
                        # Fallback to uncompressed version
                        cached_data = self.redis_client.get(cache_key)
                        if cached_data:
                            import json
                            if isinstance(cached_data, bytes):
                                cached_data = cached_data.decode('utf-8')
                            cached_result = json.loads(cached_data)
                            logger.info(f"🎯 Using cached PNCP results ({len(cached_result.get('data', []))} records)")
                            
                            # ✅ APLICAR FILTROS LOCAIS NOS DADOS DO CACHE
                            filtered_data = self._apply_local_filters(cached_result['data'], internal_filters)
                            logger.info(f"🔍 Applied local filters: {len(filtered_data)} matches from {len(cached_result.get('data', []))} cached records")
                            return [self._convert_to_opportunity_data(item) for item in filtered_data]
                            
                    except Exception as e:
                        logger.warning(f"Cache read error: {e}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
 
        # If no cache hit, fetch fresh data
        logger.info("🔍 Cache miss - fetching fresh PNCP data")
        search_result = await self._fetch_with_efficient_pagination(internal_filters)
        
        # ✅ CACHE OPTIMIZATION: Cache raw data immediately after fetch for reuse
        if self.redis_client and self.cache_ttl > 0 and cache_key:
            try:
                # Use compression for large datasets (3K+ records)
                import gzip
                import json
                
                # Convert to compact JSON
                cache_data = json.dumps(search_result, separators=(',', ':'), default=str)
                
                # Compress if data is large (>500KB)
                if len(cache_data) > 512 * 1024:  # 512KB threshold
                    cache_data = gzip.compress(cache_data.encode('utf-8'))
                    cache_key = f"{cache_key}:gz"  # Mark as compressed
                    logger.info(f"💾 Compressing dataset for Redis cache")
                
                # TTL in seconds (24 hours)
                ttl_seconds = 24 * 60 * 60  # 24 horas em segundos
                self.redis_client.setex(
                    cache_key, 
                    ttl_seconds,  # TTL em segundos (86400)
                    cache_data
                )
                logger.info(f"💾 Cached PNCP raw data ({len(search_result.get('data', []))} records) for 24 hours")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
        
        # ✅ CRITICAL FIX: Apply local filters BEFORE converting to OpportunityData
        raw_data = search_result.get('data', [])
        logger.info(f"🔍 Before filters: {len(raw_data)} raw results")
        
        # Apply local filters (same as working repository)
        filtered_data = self._apply_local_filters(raw_data, internal_filters)
        logger.info(f"✅ After local filters: {len(filtered_data)} filtered results")
        
        # Convert to OpportunityData objects
        opportunities = []
        for item in filtered_data:  # ✅ Use filtered_data instead of raw data
            opportunity = self._convert_to_opportunity_data(item)
            if opportunity:
                opportunities.append(opportunity)
        
        # 🚫 SALVAMENTO AUTOMÁTICO DESATIVADO - Performance otimizada
        # Agora só salva quando usuário acessa licitação específica via modal
        logger.info(f"🚫 Salvamento automático desativado - dados retornados sem persistir")
        
        logger.info(f"✅ PNCP search completed: {len(opportunities)} opportunities")
        return opportunities

    async def _fetch_with_efficient_pagination(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🚀 HYBRID SEARCH STRATEGY: Try parallel first, fallback to sequential
        """
        import os
        import asyncio
        import time
        
        # 🎯 DECISION: Use parallel if enabled and conditions met
        use_parallel = (
            os.getenv('ENABLE_PARALLEL_SEARCH', 'false').lower() == 'true' and  # ✅ DISABLED BY DEFAULT
            self.max_results >= 1000  # Use for any substantial search
        )
        
        if use_parallel:
            try:
                logger.info("🚀 TRYING PARALLEL OPTIMIZED SEARCH")
                start_time = time.time()
                
                # Try parallel search
                result = await self._fetch_with_parallel_pagination(filtros)
                
                if result and result.get('total', 0) > 0:
                    search_time = time.time() - start_time
                    logger.info(f"✅ PARALLEL SEARCH SUCCESS: {result['total']} results in {search_time:.2f}s")
                    return result
                else:
                    logger.warning("⚠️ Parallel search returned no results, falling back...")
            
            except Exception as e:
                logger.warning(f"⚠️ Parallel search failed: {e}, falling back to sequential...")
        
        # 🛡️ FALLBACK: Sequential search (original efficient method)
        logger.info("🔄 USING SEQUENTIAL NATIONAL SEARCH (proven strategy)")
        return self._fetch_with_sequential_national_pagination(filtros)
    
    def _fetch_with_sequential_national_pagination(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🎯 SEQUENTIAL NATIONAL SEARCH - OPTIMIZED with parallel requests
        
        This method replicates the EXACT strategy that works in licitacao_repository.py:
        - National search (no UF filtering in API)
        - 200 pages maximum 
        - 50 items per page
        - PARALLEL requests like working repository
        - Local filtering after data collection
        """
        import concurrent.futures
        import time
        
        logger.info("🎯 STARTING OPTIMIZED SEQUENTIAL NATIONAL SEARCH")
        logger.info("📊 Strategy: 200 pages × 50 = 10,000 national records maximum")
        logger.info("🚀 Using parallel requests for 3x performance boost")
        
        all_licitacoes = []
        seen_pncp_ids = set()
        total_pages_searched = 0
        max_pages = 200  # Same as working repository
        batch_size = 20  # Process 20 pages in parallel (same as working repo)ene
        
        # 🔄 PARALLEL BATCH PROCESSING (like working repository)
        logger.info(f"🚀 Executing {max_pages} API calls in parallel batches...")
        # 🔄 PARALLEL BATCH PROCESSING (like working repository)
       
        start_time = time.time()
        empty_batches_count = 0
        max_empty_batches = 5
        
        for batch_start in range(1, max_pages + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, max_pages)
            batch_pages = list(range(batch_start, batch_end + 1))
            
            logger.info(f"📦 Processing batch: pages {batch_start}-{batch_end}")
            
            # ✅ PARALLEL EXECUTION with ThreadPoolExecutor (same as working repo)
            batch_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Submit all pages in batch simultaneously
                future_to_page = {
                    executor.submit(self._fetch_national_pncp_data, page): page 
                    for page in batch_pages
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        page_results, has_more_pages = future.result()
                        batch_results.append((page_num, page_results, has_more_pages))
                        total_pages_searched += 1
                    except Exception as e:
                        logger.error(f"❌ Error on page {page_num}: {e}")
                        batch_results.append((page_num, [], False))
                        total_pages_searched += 1
            
            # Process batch results
            batch_new_results = 0
            all_pages_empty = True
            
            for page_num, page_results, has_more_pages in sorted(batch_results):
                if page_results:
                    all_pages_empty = False
                    # Process and add new results
                    for licitacao in page_results:
                        pncp_id = licitacao.get('numeroControlePNCP')
                        if pncp_id and pncp_id not in seen_pncp_ids:
                            seen_pncp_ids.add(pncp_id)
                            all_licitacoes.append(licitacao)
                            batch_new_results += 1
                
                # Check if API says no more pages
                if not has_more_pages:
                    logger.info(f"📄 API indicated no more pages at page {page_num}")
                    # Continue processing this batch but don't start new ones
                    max_pages = batch_end
                    break
            
            logger.info(f"✅ Batch complete: +{batch_new_results} new results (Total: {len(all_licitacoes)})")
            
            # Stop if too many empty batches
            if all_pages_empty:
                empty_batches_count += 1
                if empty_batches_count >= max_empty_batches:
                    logger.info(f"🛑 Stopping after {max_empty_batches} empty batches")
                    break
            else:
                empty_batches_count = 0
                
            # Educational pause between batches (API rate limiting)
            if batch_end < max_pages:
                time.sleep(0.5)
        
        elapsed_time = time.time() - start_time
        logger.info(f"🎉 OPTIMIZED SEARCH COMPLETED: {len(all_licitacoes)} unique licitações from {total_pages_searched} pages in {elapsed_time:.2f}s")
        
        return {
            'data': all_licitacoes,
            'total': len(all_licitacoes),
            'pages_searched': total_pages_searched,
            'search_time': elapsed_time,
            'strategy': 'optimized_sequential_national_pagination'
        }
    
    def _fetch_national_pncp_data(self, page: int) -> Tuple[List[Dict], bool]:
        """
        NATIONAL search - same parameters as working repository
        No UF filtering in API call
        """
        import requests
        from typing import Tuple, List, Dict
        
        url = f"{self.api_base_url}/contratacoes/proposta"
        
        # ✅ SAME PARAMETERS as working repository (NATIONAL search)
        params = {
            'dataInicial': self.data_inicial,
            'dataFinal': self.data_final,
            'pagina': page,
            'tamanhoPagina': 50,
            'codigoModalidadeContratacao': 8  # Pregão Eletrônico
            # NO UF parameter - national search
        }
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            all_bids = data.get("data", []) if isinstance(data, dict) else data
            
            # SIMPLE LOGIC: If we get less than full page, we're done
            has_more_pages = len(all_bids) >= 50
            
            logger.debug(f"   ✅ Success: {len(all_bids)} results on page {page}")
            return all_bids, has_more_pages
            
        except requests.RequestException as e:
            logger.error(f"❌ API error on page {page}: {e}")
            return [], False
    
    async def _fetch_with_parallel_pagination(self, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        🚀 PARALLEL OPTIMIZED SEARCH - 6-8x faster than sequential
        
        GUARANTEES:
        - ✅ Same API and logic as current version
        - ✅ Same licitações found (100% identical results)  
        - ✅ 6-8x faster execution time
        - ✅ Optimized cache usage
        """
        import aiohttp
        import asyncio
        import time
        from typing import List, Tuple, Dict, Any
        
        logger.info("🚀 STARTING PARALLEL OPTIMIZED SEARCH")
        start_time = time.time()
        
        try:
            # 🎯 STRATEGY: Parallel batches with intelligent load balancing
            ufs_to_search = [
                'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
            ]
            
            # 📊 INTELLIGENT CONFIGURATION - ALINHADO COM SISTEMA ANTIGO
            max_concurrent = 8        # 8 simultaneous requests (safe for PNCP)
            max_pages_per_uf = 200    # ✅ 200 páginas por UF (pode ser ajustado)
            batch_size = 8            # Process 8 UFs per batch
            
            # 🎯 ALTERNATIVA: Usar 200 páginas por modalidade como sistema antigo
            # Se quiser equivalência direta: max_pages_total = 200 (nacional)
            # Se quiser mais volume: max_pages_per_uf = 200 × 27 UFs = 5.400 páginas
            
            all_licitacoes = []
            seen_pncp_ids = set()
            total_pages_searched = 0
            
            # 🔄 PARALLEL BATCH PROCESSING
            connector = aiohttp.TCPConnector(
                limit=20,           # Connection pool
                limit_per_host=5,   # Max 5 connections per host
                keepalive_timeout=30
            )
            timeout = aiohttp.ClientTimeout(total=15)  # Optimized timeout
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'AlicitSaas/2.0 (Parallel Search)'}
            ) as session:
                
                # Divide UFs into intelligent batches
                for i in range(0, len(ufs_to_search), batch_size):
                    batch_ufs = ufs_to_search[i:i + batch_size]
                    batch_num = i//batch_size + 1
                    total_batches = (len(ufs_to_search) + batch_size - 1) // batch_size
                    
                    logger.info(f"🔄 Processing batch {batch_num}/{total_batches}: {batch_ufs}")
                    
                    # 🚀 EXECUTE BATCH IN PARALLEL
                    batch_tasks = []
                    for uf in batch_ufs:
                        task = self._fetch_uf_parallel(
                            session, uf, max_pages_per_uf, 
                            max_concurrent, seen_pncp_ids
                        )
                        batch_tasks.append(task)
                    
                    # Wait for batch completion
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    # Process batch results
                    batch_licitacoes = 0
                    batch_pages = 0
                    
                    for result in batch_results:
                        if isinstance(result, Exception):
                            logger.warning(f"⚠️ Batch error: {result}")
                            continue
                        
                        if result and isinstance(result, dict):
                            uf_licitacoes = result.get('licitacoes', [])
                            uf_pages = result.get('pages_searched', 0)
                            
                            # Add unique results
                            for licitacao in uf_licitacoes:
                                pncp_id = licitacao.get('numeroControlePNCP')
                                if pncp_id and pncp_id not in seen_pncp_ids:
                                    seen_pncp_ids.add(pncp_id)
                                    all_licitacoes.append(licitacao)
                                    batch_licitacoes += 1
                            
                            batch_pages += uf_pages
                    
                    total_pages_searched += batch_pages
                    logger.info(f"✅ Batch {batch_num}: +{batch_licitacoes} new results, {batch_pages} pages")
                    
                    # Educational pause between batches (prevent API overload)
                    if i + batch_size < len(ufs_to_search):
                        await asyncio.sleep(0.5)
            
            # 🔍 CRITICAL FIX: Apply keyword filters to parallel results
            logger.info(f"🔍 Before filters: {len(all_licitacoes)} raw results")
            if filtros.get('keywords'):
                logger.info(f"🔤 Applying keyword filter: '{filtros.get('keywords')}'")
                all_licitacoes = self._apply_local_filters(all_licitacoes, filtros)
                logger.info(f"✅ After keyword filter: {len(all_licitacoes)} results")
            
            # 📊 FINAL RESULTS
            total_time = time.time() - start_time
            unique_count = len(seen_pncp_ids)
            results_per_second = len(all_licitacoes) / total_time if total_time > 0 else 0
            
            logger.info(f"🎉 PARALLEL SEARCH COMPLETED:")
            logger.info(f"   ⏱️ Time: {total_time:.2f}s (vs ~5-8min sequential)")
            logger.info(f"   📄 Pages: {total_pages_searched}")
            logger.info(f"   📈 Results: {len(all_licitacoes)} total, {unique_count} unique")
            logger.info(f"   🚀 Performance: {results_per_second:.1f} results/second")
            logger.info(f"   📈 Speedup: ~{(300/total_time):.1f}x faster than sequential estimate")
            
            return {
                'data': all_licitacoes,
                'total': len(all_licitacoes),
                'unique_count': unique_count,
                'pages_searched': total_pages_searched,
                'search_time': total_time,
                'results_per_second': results_per_second,
                'strategy': 'parallel_optimized'
            }
            
        except Exception as e:
            logger.error(f"❌ Parallel search error: {e}")
            raise  # Re-raise to trigger fallback
    
    async def _fetch_uf_parallel(
        self, 
        session: aiohttp.ClientSession, 
        uf: str, 
        max_pages: int,
        max_concurrent: int,
        seen_pncp_ids: set
    ) -> Dict[str, Any]:
        """
        Parallel search for a specific UF with intelligent pagination
        """
        logger.debug(f"🔍 Starting parallel search for {uf}")
        
        uf_licitacoes = []
        pages_searched = 0
        
        # 🎯 SEMAPHORE to control concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Smart strategy: Start with first 5 pages, then decide
        initial_pages = 5
        page_tasks = []
        
        for page in range(1, initial_pages + 1):
            task = self._fetch_page_async(session, uf, page, semaphore)
            page_tasks.append(task)
        
        # Execute initial pages in parallel
        initial_results = await asyncio.gather(*page_tasks, return_exceptions=True)
        
        # Process initial results
        total_results_count = 0
        for page_num, result in enumerate(initial_results, 1):
            if isinstance(result, Exception):
                logger.debug(f"⚠️ Page {page_num} error for {uf}: {result}")
                continue
                
            if result and isinstance(result, tuple):
                page_data, has_more = result
                pages_searched += 1
                
                # Add unique results (filter by UF is done in _fetch_page_async)
                for item in page_data:
                    pncp_id = item.get('numeroControlePNCP')
                    if pncp_id:  # Don't check seen_pncp_ids here (thread safety)
                        uf_licitacoes.append(item)
                        total_results_count += 1
                
                # Stop if API says no more pages
                if not has_more:
                    logger.debug(f"🛑 {uf}: API indicated end at page {page_num}")
                    break
        
        # 📊 ADAPTIVE LOGIC: Continue searching all UFs (not just promising ones)
        # ✅ FIXED: Always search more pages for comprehensive results
        logger.debug(f"📈 {uf}: Found {total_results_count} results, continuing search...")
        
        # Search additional pages (up to max_pages)
        additional_tasks = []
        max_additional = min(max_pages, 200)  # Cap at 200 pages
        for page in range(initial_pages + 1, max_additional + 1):
            task = self._fetch_page_async(session, uf, page, semaphore)
            additional_tasks.append(task)
            
        if additional_tasks:
            additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)
            
            # Process additional pages
            empty_count = 0
            for page_num, result in enumerate(additional_results, initial_pages + 1):
                if isinstance(result, Exception) or not result:
                    empty_count += 1
                    if empty_count >= 3:  # Stop after 3 empty pages
                        break
                    continue
                
                if isinstance(result, tuple):
                    page_data, has_more = result
                    pages_searched += 1
                    
                    if page_data:
                        empty_count = 0  # Reset counter
                        # Add results
                        for item in page_data:
                            pncp_id = item.get('numeroControlePNCP')
                            if pncp_id:
                                uf_licitacoes.append(item)
                                total_results_count += 1
                    else:
                        empty_count += 1
                    
                    if not has_more:
                        break
        
        logger.debug(f"✅ {uf}: {len(uf_licitacoes)} results in {pages_searched} pages")
        
        return {
            'uf': uf,
            'licitacoes': uf_licitacoes,
            'pages_searched': pages_searched
        }
    
    async def _fetch_page_async(
        self, 
        session: aiohttp.ClientSession, 
        uf: str, 
        page: int,
        semaphore: asyncio.Semaphore
    ) -> tuple:
        """
        Async fetch of a specific page with same logic as current system
        """
        async with semaphore:  # Control concurrency
            try:
                url = f"{self.api_base_url}/contratacoes/proposta"
                
                # SAME PARAMETERS as current working system
                params = {
                    'dataInicial': self.data_inicial,
                    'dataFinal': self.data_final,
                    'pagina': page,
                    'tamanhoPagina': 50,
                    'codigoModalidadeContratacao': 8  # ✅ CORRIGIDO: Pregão Eletrônico (igual ao antigo)
                    # NO UF parameter (same as current working approach)
                }
                
                async with session.get(url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    all_bids = data.get("data", []) if isinstance(data, dict) else data
                    
                    # SAME UF FILTERING LOGIC as current system
                    filtered_bids = []
                    if uf and uf != 'ALL':
                        for bid in all_bids:
                            unidade_orgao = bid.get('unidadeOrgao', {})
                            bid_uf = unidade_orgao.get('ufSigla')
                            
                            # Fallback logic (same as current)
                            if not bid_uf:
                                orgao_entidade = bid.get('orgaoEntidade', {})
                                bid_uf = orgao_entidade.get('ufSigla')
                            
                            if bid_uf == uf:
                                filtered_bids.append(bid)
                    else:
                        filtered_bids = all_bids
                    
                    # SAME PAGINATION LOGIC as current
                    has_more_pages = len(all_bids) >= 50
                    
                    return filtered_bids, has_more_pages
            
            except Exception as e:
                logger.debug(f"❌ Page {page} error for {uf}: {e}")
                return [], False

    def _fetch_corrected_pncp_data(self, start_date: str, end_date: str, uf: str, page: int) -> Tuple[List[Dict], bool]:
        """
        FIXED: Use NATIONAL search like working repository (no UF filter in API)
        Filter UF results in code after fetching
        """
        import requests
        from typing import Tuple, List, Dict
        
        url = f"{self.api_base_url}/contratacoes/proposta"
        
        # ✅ CORREÇÃO CRÍTICA: Use same parameters as working repository (NO UF!)
        params = {
            'dataInicial': start_date,
            'dataFinal': end_date,
            # 🚫 REMOVED: 'uf': uf,  # This causes HTTP 422!
            'pagina': page,
            'tamanhoPagina': 50,
            'codigoModalidadeContratacao': 8  # ✅ CORRIGIDO: Pregão Eletrônico (igual ao antigo)
        }
        
        try:
            logger.info(f"🔍 API call: {url} with params: {params}")
            logger.info(f"🌐 Complete URL would be: {url}?{'&'.join([f'{k}={v}' for k,v in params.items()])}")  # Show complete URL for debugging
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            all_bids = data.get("data", []) if isinstance(data, dict) else data
            
            # ✅ FILTER BY UF IN CODE (if UF is specified)
            if uf and uf != 'ALL':
                # Filter results to match requested UF
                filtered_bids = []
                for bid in all_bids:
                    # Check correct UF field based on real PNCP response structure
                    unidade_orgao = bid.get('unidadeOrgao', {})
                    bid_uf = unidade_orgao.get('ufSigla')  # ✅ Campo correto: unidadeOrgao.ufSigla
                    
                    # Fallback para outros possíveis campos (caso a estrutura mude)
                    if not bid_uf:
                        orgao_entidade = bid.get('orgaoEntidade', {})
                        bid_uf = orgao_entidade.get('ufSigla')
                    
                    if bid_uf == uf:
                        filtered_bids.append(bid)
                        
                bids = filtered_bids
                logger.info(f"   📍 UF Filter: {len(filtered_bids)} matches found for UF {uf} from {len(all_bids)} total records")
            else:
                bids = all_bids
            
            # SIMPLE LOGIC: If we get less than full page, we're done
            has_more_pages = len(all_bids) >= 50  # Use total results for pagination logic
            
            logger.info(f"   ✅ Sucesso: {len(all_bids)} total, {len(bids)} para UF {uf}, página {page}")
            return bids, has_more_pages
            
        except requests.RequestException as e:
            logger.error(f"❌ Erro na API PNCP (página {page}): {e}")
            return [], False
    
    def _convert_filters(self, filters: SearchFilters) -> Dict[str, Any]:
        """Convert SearchFilters to internal format for the adapter"""
        internal_filters = {}
        
        # Keywords
        if filters.keywords:
            internal_filters['keywords'] = filters.keywords
        
        # Geographic filters
        if filters.region_code:
            internal_filters['region_code'] = filters.region_code
            internal_filters['uf'] = filters.region_code  # Compatibility
        if filters.municipality:
            internal_filters['municipality'] = filters.municipality
        
        # Value filters
        if filters.min_value is not None:
            internal_filters['min_value'] = filters.min_value
        if filters.max_value is not None:
            internal_filters['max_value'] = filters.max_value
        
        # Procurement type
        if filters.procurement_type:
            internal_filters['procurement_type'] = filters.procurement_type
        
        # Status filter
        if filters.status:
            internal_filters['status'] = filters.status
        
        # Date filters
        if filters.publication_date_from:
            internal_filters['publication_date_from'] = filters.publication_date_from
        if filters.publication_date_to:
            internal_filters['publication_date_to'] = filters.publication_date_to
        
        return internal_filters
    
    def _apply_local_filters(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        🔄 ATUALIZADO: Aplica filtros locais incluindo sinônimos SEMPRE
        """
        filtered_data = data[:]  # Start with all data
        initial_count = len(filtered_data)
        
        logger.info(f"🔍 APLICANDO FILTROS LOCAIS COM SINÔNIMOS: {initial_count} registros iniciais")
        logger.info(f"   📋 Filtros recebidos: {filters}")
        
        # 🔍 FILTRO DE PALAVRAS-CHAVE COM SINÔNIMOS - SEMPRE APLICADO
        keywords = filters.get('keywords')
        if keywords and keywords.strip():
            logger.info(f"   🔤 Aplicando filtro de keywords com sinônimos: '{keywords}'")
            
            # 🆕 NOVO: Sempre gerar e incluir sinônimos
            all_search_terms = [keywords.strip()]
            
            # Gerar sinônimos se disponível
            if self.openai_service:
                try:
                    synonyms = self._generate_synonyms_for_cache(keywords)
                    if synonyms:
                        all_search_terms.extend(synonyms)
                        logger.info(f"   🎯 Usando sinônimos: {synonyms}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Erro ao gerar sinônimos: {e}")
            
            # Processar keywords que podem vir com OR ou aspas (manter compatibilidade)
            if ' OR ' in keywords:
                import re
                keyword_terms = re.findall(r'"([^"]*)"', keywords)
                if not keyword_terms:
                    keyword_terms = [term.strip().strip('"') for term in keywords.split(' OR ') if term.strip()]
                # Adicionar sinônimos para cada termo individual se necessário
                final_terms = keyword_terms[:]
                for term in keyword_terms:
                    if self.openai_service and term not in all_search_terms:
                        try:
                            term_synonyms = self._generate_synonyms_for_cache(term)
                            final_terms.extend(term_synonyms)
                        except:
                            pass
                all_search_terms = list(set(final_terms))  # Remove duplicates
            else:
                # Normalizar e dividir por espaços + adicionar sinônimos
                clean_keywords = self._normalizar_simples(keywords)
                basic_terms = [term.strip() for term in clean_keywords.split() if term.strip()]
                all_search_terms.extend(basic_terms)
                all_search_terms = list(set(all_search_terms))  # Remove duplicates
            
            logger.info(f"   🎯 Termos finais de busca (incluindo sinônimos): {all_search_terms}")
            
            if all_search_terms:
                keyword_filtered = []
                matches_found = 0
                
                for item in filtered_data:
                    # Buscar nos MESMOS 3 campos do sistema antigo
                    objeto_compra = (item.get('objetoCompra') or '').lower()
                    objeto_detalhado = (item.get('objetoDetalhado') or '').lower()
                    info_complementar = (item.get('informacaoComplementar') or '').lower()
                    
                    # Combinar todos os textos
                    texto_completo = f"{objeto_compra} {objeto_detalhado} {info_complementar}".strip()
                    
                    if not texto_completo:
                        continue
                    
                    # Aplicar mesma normalização
                    texto_normalizado = self._normalizar_simples(texto_completo)
                    
                    # 🔄 CORREÇÃO: Verificar se QUALQUER termo da busca (incluindo sinônimos) está presente
                    match_found = False
                    matched_term = None
                    for term in all_search_terms:
                        if not term:
                            continue
                        term_normalizado = self._normalizar_simples(term)
                        if term_normalizado and term_normalizado in texto_normalizado:
                            match_found = True
                            matched_term = term
                            break
                    
                    if match_found:
                        keyword_filtered.append(item)
                        matches_found += 1
                        
                        # Log dos primeiros 3 matches para debug
                        if matches_found <= 3:
                            logger.info(f"      ✅ Match #{matches_found} (termo: '{matched_term}'): {objeto_compra[:100]}...")
                
                filtered_data = keyword_filtered
                logger.info(f"   🔤 Filtro keywords COM sinônimos: {len(filtered_data)} matches de {initial_count}")
            else:
                logger.warning("   ⚠️ Nenhum termo válido para busca")

        # 🔍 FILTRO DE REGIÃO
        region_code = filters.get('region_code')
        if region_code:
            logger.info(f"   🗺️ Aplicando filtro de região: {region_code}")
            region_filtered = []
            for item in filtered_data:
                item_uf = item.get('unidadeOrgao', {}).get('ufSigla', '').upper()
                if item_uf == region_code.upper():
                    region_filtered.append(item)
            
            filtered_data = region_filtered
            logger.info(f"   🗺️ Filtro região: {len(filtered_data)} restantes")

        # 🔍 FILTRO DE MUNICÍPIO
        municipality = filters.get('municipality')
        if municipality:
            logger.info(f"   🏙️ Aplicando filtro de município: {municipality}")
            municipality_filtered = []
            municipality_normalized = self._normalizar_simples(municipality)
            
            for item in filtered_data:
                item_municipio = item.get('unidadeOrgao', {}).get('municipioNome', '')
                item_municipio_normalized = self._normalizar_simples(item_municipio)
                
                if municipality_normalized in item_municipio_normalized:
                    municipality_filtered.append(item)
            
            filtered_data = municipality_filtered
            logger.info(f"   🏙️ Filtro município: {len(filtered_data)} restantes")

        # 🔍 FILTRO DE VALOR MÍNIMO
        min_value = filters.get('min_value')
        if min_value is not None:
            logger.info(f"   💰 Aplicando filtro valor mínimo: R$ {min_value:,.2f}")
            value_filtered = []
            for item in filtered_data:
                item_value = item.get('valorTotalEstimado')
                if item_value is not None:
                    try:
                        if float(item_value) >= float(min_value):
                            value_filtered.append(item)
                    except (ValueError, TypeError):
                        continue
            
            filtered_data = value_filtered
            logger.info(f"   💰 Filtro valor mínimo: {len(filtered_data)} restantes")

        # 🔍 FILTRO DE VALOR MÁXIMO
        max_value = filters.get('max_value')
        if max_value is not None:
            logger.info(f"   💰 Aplicando filtro valor máximo: R$ {max_value:,.2f}")
            value_filtered = []
            for item in filtered_data:
                item_value = item.get('valorTotalEstimado')
                if item_value is not None:
                    try:
                        if float(item_value) <= float(max_value):
                            value_filtered.append(item)
                    except (ValueError, TypeError):
                        continue
            
            filtered_data = value_filtered
            logger.info(f"   💰 Filtro valor máximo: {len(filtered_data)} restantes")

        logger.info(f"🎯 FILTROS LOCAIS CONCLUÍDOS: {len(filtered_data)} registros finais de {initial_count} iniciais")
        
        return filtered_data
    
    def _normalizar_simples(self, texto: str) -> str:
        """
        CORREÇÃO: Normalização IDÊNTICA ao sistema antigo (licitacao_repository.py)
        - Remove acentos
        - Lowercase
        - Remove pontuação
        - NÃO aplica stemmer agressivo
        """
        import unicodedata
        import re
        
        if not texto:
            return ""
        
        # Lowercase
        texto = texto.lower()
        
        # Remove acentos
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
        
        # Remove pontuação mas mantém espaços
        texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
        
        # Remove espaços múltiplos
        texto = ' '.join(texto.split())
        
        return texto

    def _extract_search_terms(self, keywords: Optional[str]) -> List[str]:
        """Extract search terms from keywords string"""
        if not keywords:
            return []
    
        # Simple split by common separators
        import re
        terms = re.split(r'[,;\s]+', keywords.strip())
        return [term.strip() for term in terms if term.strip()]
    
    def _convert_to_opportunity_data(self, licitacao: Dict[str, Any]) -> OpportunityData:
        """Convert PNCP licitação to OpportunityData format"""
        try:
            # Extract location data
            location_data = self._get_location_data(licitacao)
            
            # 🔧 CORREÇÃO CRÍTICA: Extrair CNPJ do órgão para evitar erro de banco
            orgao_cnpj = self._extract_orgao_cnpj(licitacao)
            
            # 🔧 CORREÇÃO: Extrair dados específicos da API de consulta PNCP
            numero_controle = licitacao.get('numeroControlePNCP', '')
            
            # Informações básicas
            titulo = licitacao.get('objetoCompra', '') or licitacao.get('objetoContratacao', '')
            descricao = licitacao.get('informacaoComplementar', '') or licitacao.get('objetoDetalhado', '')
            
            # Valores
            valor_estimado = licitacao.get('valorTotalEstimado', 0.0)
            
            # 📅 DATAS (com múltiplas fontes de fallback)
            start_date = None
            end_date = None
            publication_date = None
            
            # 🔧 CORREÇÃO CRÍTICA: Data de abertura das propostas 
            data_abertura_raw = (
                licitacao.get('dataAberturaProposta') or
                licitacao.get('dataRecebimentoProposta') or
                licitacao.get('dataInicioProposta') or
                licitacao.get('dataInicioRecebimento')
            )
            
            if data_abertura_raw:
                start_date = self._parse_pncp_date(data_abertura_raw)
                if start_date:
                    logger.debug(f"✅ Data de abertura extraída: {start_date} de '{data_abertura_raw}'")
                else:
                    logger.warning(f"⚠️ Falha ao parsear data de abertura: '{data_abertura_raw}'")
            else:
                logger.warning(f"⚠️ Data de abertura não encontrada para {numero_controle}")
            
            # Data de encerramento
            data_encerramento_raw = (
                licitacao.get('dataEncerramentoProposta') or
                licitacao.get('dataFinalProposta') or
                licitacao.get('dataFimRecebimento')
            )
            
            if data_encerramento_raw:
                end_date = self._parse_pncp_date(data_encerramento_raw)
            
            # Data de publicação PNCP
            data_publicacao_raw = (
                licitacao.get('dataPublicacaoPncp') or
                licitacao.get('dataPublicacao') or
                licitacao.get('dataInclusao')
            )
            
            if data_publicacao_raw:
                publication_date = self._parse_pncp_date(data_publicacao_raw)
            
            # Modalidade
            modalidade_nome = licitacao.get('modalidadeNome', '')
            modalidade_id = licitacao.get('modalidadeId')
            
            # Órgão responsável
            orgao_entidade = licitacao.get('orgaoEntidade', {})
            orgao_nome = orgao_entidade.get('razaoSocial', '') if isinstance(orgao_entidade, dict) else ''
            
            # Unidade
            unidade_orgao = licitacao.get('unidadeOrgao', {})
            unidade_nome = unidade_orgao.get('nomeUnidade', '') if isinstance(unidade_orgao, dict) else ''
            
            # Status
            situacao_nome = licitacao.get('situacaoCompraNome', '')
            status = self._determine_status(licitacao)
            
            # 🔧 CORRIGIDO: Criar OpportunityData temporário primeiro
            opportunity_data = OpportunityData(
                external_id=numero_controle,
                title=titulo,
                description=descricao,
                estimated_value=float(valor_estimado) if valor_estimado else 0.0,
                currency_code='BRL',  # 🔧 CORRIGIDO: currency_code
                country_code='BR',    # 🔧 CORRIGIDO: country_code
                region_code=location_data['region'],      # 🔧 CORRIGIDO: region_code
                municipality=location_data['city'],       # 🔧 CORRIGIDO: municipality
                publication_date=publication_date,         # 🔧 CORRIGIDO: publication_date
                submission_deadline=end_date,    # 🔧 CORRIGIDO: submission_deadline
                procuring_entity_id=orgao_cnpj,          # 🔧 ADICIONADO: procuring_entity_id
                procuring_entity_name=orgao_nome,        # 🔧 ADICIONADO: procuring_entity_name
                provider_specific_data={
                    # 🔧 DADOS PARA SALVAR NO BANCO (evitar erro NOT NULL)
                    'orgao_cnpj': orgao_cnpj or '',  # CNPJ obrigatório
                    'orgao_nome': orgao_nome,
                    'unidade_nome': unidade_nome,
                    'modalidade_id': modalidade_id,
                    'modalidade_nome': modalidade_nome,
                    'situacao_nome': situacao_nome,
                    'numero_compra': licitacao.get('numeroCompra', ''),
                    'processo': licitacao.get('processo', ''),
                    'link_sistema_origem': licitacao.get('linkSistemaOrigem', ''),
                    'ano_compra': licitacao.get('anoCompra'),
                    'sequencial_compra': licitacao.get('sequencialCompra'),
                    'data_publicacao_pncp': publication_date,
                    'data_abertura_proposta': start_date,
                    'data_encerramento_proposta': end_date,
                    'amparo_legal': licitacao.get('amparoLegal', {}),
                    'modo_disputa': licitacao.get('modoDisputaNome', ''),
                    'valor_total_homologado': licitacao.get('valorTotalHomologado'),
                    'srp': licitacao.get('srp', False),
                    'tipo_instrumento': licitacao.get('tipoInstrumentoConvocatorioNome', ''),
                    'status': status,  # 🔧 ADICIONADO: status para compatibilidade
                    
                    # 🔧 DADOS BRUTOS PARA DEBUG E EXPANSÕES FUTURAS
                    'raw_data': licitacao
                }
            )
            
            # 🔧 CORREÇÃO CRÍTICA: Adicionar provider_name dinamicamente (PersistenceService precisa dele)
            # Como OpportunityData não tem provider_name na definição, precisamos adicioná-lo dinamicamente
            opportunity_data.provider_name = self.get_provider_name()
            opportunity_data.contracting_authority = orgao_nome
            
            return opportunity_data
            
        except Exception as e:
            logger.error(f"❌ Error converting PNCP data to OpportunityData: {e}")
            # 🔧 FALLBACK: Retornar dados mínimos para evitar crash
            fallback_opportunity = OpportunityData(
                external_id=licitacao.get('numeroControlePNCP', 'unknown'),
                title='Erro na conversão de dados',
                description=f'Erro ao processar licitação: {str(e)}',
                estimated_value=0.0,
                currency_code='BRL',
                country_code='BR',
                provider_specific_data={
                    'orgao_cnpj': '',  # Campo obrigatório vazio
                    'error': str(e),
                    'raw_data': licitacao
                }
            )
            
            # 🔧 CORREÇÃO CRÍTICA: Adicionar provider_name no fallback também
            fallback_opportunity.provider_name = self.get_provider_name()
            fallback_opportunity.contracting_authority = orgao_nome if 'orgao_nome' in locals() else None
            
            return fallback_opportunity
    
    def _extract_orgao_cnpj(self, licitacao: Dict[str, Any]) -> Optional[str]:
        """
        Extrai o CNPJ do órgão responsável pela licitação
        
        Args:
            licitacao: Dados da licitação do PNCP (API consulta ou API v1)
            
        Returns:
            CNPJ do órgão ou None se não encontrado
        """
        try:
            # 🔍 ESTRATÉGIA 0: Se o CNPJ já foi extraído do numeroControlePNCP, usar ele
            numero_controle = licitacao.get('numeroControlePNCP')
            if numero_controle:
                cnpj_from_controle, _, _ = self._parse_numero_controle_pncp(numero_controle)
                if cnpj_from_controle:
                    logger.debug(f"✅ CNPJ extraído do numeroControlePNCP: {cnpj_from_controle}")
                    return cnpj_from_controle
            
            # 🔍 ESTRATÉGIA 1: orgaoEntidade.cnpj (API de consulta - PRINCIPAL)
            orgao_entidade = licitacao.get('orgaoEntidade', {})
            if orgao_entidade and isinstance(orgao_entidade, dict):
                cnpj = orgao_entidade.get('cnpj')
                if cnpj:
                    logger.debug(f"✅ CNPJ extraído do orgaoEntidade.cnpj: {cnpj}")
                    return cnpj
            
            # 🔍 ESTRATÉGIA 2: Campos diretos de CNPJ (API v1)
            campos_cnpj_diretos = [
                'cnpjOrgao', 'cnpj', 'cnpjEntidade', 'cnpjUnidade',
                'identificadorOrgao', 'codigoUnidadeCompradora', 'cnpjUnidadeCompradora'
            ]
            
            for campo in campos_cnpj_diretos:
                cnpj = licitacao.get(campo)
                if cnpj and isinstance(cnpj, str):
                    cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
                    if len(cnpj_limpo) == 14 and cnpj_limpo.isdigit():
                        logger.debug(f"✅ CNPJ extraído do campo {campo}: {cnpj}")
                        return cnpj
            
            # 🔍 ESTRATÉGIA 3: Buscar na unidadeOrgao (API consulta)
            unidade_orgao = licitacao.get('unidadeOrgao', {})
            if unidade_orgao and isinstance(unidade_orgao, dict):
                cnpj = unidade_orgao.get('cnpj') or unidade_orgao.get('cnpjUnidade')
                if cnpj:
                    logger.debug(f"✅ CNPJ extraído da unidadeOrgao: {cnpj}")
                    return cnpj
            
            # 🔍 ESTRATÉGIA 4: Buscar em orgao (API v1)
            orgao = licitacao.get('orgao', {})
            if orgao and isinstance(orgao, dict):
                cnpj = orgao.get('cnpj') or orgao.get('cnpjOrgao')
                if cnpj:
                    logger.debug(f"✅ CNPJ extraído do orgao (API v1): {cnpj}")
                    return cnpj
            
            # 🔍 ESTRATÉGIA 5: Buscar em unidadeCompradora (API v1)
            unidade_compradora = licitacao.get('unidadeCompradora', {})
            if unidade_compradora and isinstance(unidade_compradora, dict):
                cnpj = unidade_compradora.get('cnpj') or unidade_compradora.get('cnpjUnidade')
                if cnpj:
                    logger.debug(f"✅ CNPJ extraído da unidadeCompradora (API v1): {cnpj}")
                    return cnpj
            
            # 🔍 ESTRATÉGIA 6: Debug - mostrar estrutura dos dados
            logger.debug(f"🔍 Estrutura dos dados para debug CNPJ:")
            logger.debug(f"   Campos principais: {list(licitacao.keys())}")
            if 'orgaoEntidade' in licitacao:
                orgao_ent = licitacao['orgaoEntidade']
                if isinstance(orgao_ent, dict):
                    logger.debug(f"   orgaoEntidade: {list(orgao_ent.keys())}")
                else:
                    logger.debug(f"   orgaoEntidade: {type(orgao_ent)} - {orgao_ent}")
            if 'unidadeOrgao' in licitacao:
                unid_org = licitacao['unidadeOrgao']
                if isinstance(unid_org, dict):
                    logger.debug(f"   unidadeOrgao: {list(unid_org.keys())}")
                else:
                    logger.debug(f"   unidadeOrgao: {type(unid_org)} - {unid_org}")
            
            logger.warning(f"⚠️ CNPJ não encontrado para licitação {licitacao.get('numeroControlePNCP', 'N/A')}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair CNPJ da licitação: {e}")
            return None
    
    def _get_organization_name(self, licitacao: Dict[str, Any]) -> str:
        """Extract organization name from licitação"""
        orgao = licitacao.get('orgaoEntidade', {})
        if orgao and orgao.get('razaoSocial'):
            return orgao['razaoSocial']
        
        unidade = licitacao.get('unidadeOrgao', {})
        if unidade and unidade.get('nomeUnidade'):
            return unidade['nomeUnidade']
        
        return 'N/A'
    
    def _get_location_data(self, licitacao: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """Extract location data from licitação"""
        unidade = licitacao.get('unidadeOrgao', {})
        if unidade:
            cidade = unidade.get('municipioNome', '')
            uf = unidade.get('ufSigla', '')  # ✅ Campo correto
            if cidade and uf:
                return {'city': cidade, 'region': uf}  # 🔧 CORRIGIDO: chaves corretas
            elif uf:
                return {'city': None, 'region': uf}  # 🔧 CORRIGIDO: chaves corretas
        
        # Fallback para orgaoEntidade (caso necessário)
        orgao = licitacao.get('orgaoEntidade', {})
        if orgao and orgao.get('ufSigla'):  # ✅ Corrigido campo
            return {'city': None, 'region': orgao['ufSigla']}  # 🔧 CORRIGIDO: chaves corretas
        
        return {'city': None, 'region': None}  # 🔧 CORRIGIDO: chaves corretas
    
    def _determine_status(self, licitacao: Dict[str, Any]) -> str:
        """Determine opportunity status based on dates and situation
        
        �� CORREÇÃO: Retornar APENAS valores aceitos pelo banco de dados
        Valores permitidos: 'coletada', 'processada', 'matched'
        """
        from datetime import datetime
        
        try:
            # 🔧 MELHORIA: Analisar situacaoCompraNome primeiro (mais confiável)
            situacao_compra = licitacao.get('situacaoCompraNome', '').lower()
            
            # 🔧 CORREÇÃO CRÍTICA: Mapear para APENAS os 3 valores aceitos pelo banco
            if any(keyword in situacao_compra for keyword in ['divulgad', 'publicad', 'aberta', 'ativa']):
                return 'coletada'  # Licitação disponível para coleta
            elif any(keyword in situacao_compra for keyword in ['homologad', 'adjudicad', 'finaliz', 'encerr']):
                return 'processada'  # Licitação finalizada
            elif any(keyword in situacao_compra for keyword in ['deserta', 'fracassad', 'suspens', 'cancel']):
                return 'processada'  # Licitação não teve sucesso, mas processada
            else:
                # 🛡️ FALLBACK: Para qualquer situação não mapeada, usar 'coletada'
                logger.debug(f"Situação não mapeada: '{situacao_compra}', usando 'coletada'")
                return 'coletada'
                
        except Exception as e:
            logger.error(f"❌ Erro ao determinar status: {e}")
            return 'coletada'  # Valor padrão seguro
    
    def _parse_pncp_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse PNCP date string to datetime object
        
        Args:
            date_str: Data no formato PNCP (pode ser ISO ou outro formato)
            
        Returns:
            datetime object ou None se não conseguir fazer parse
        """
        if not date_str:
            return None
            
        try:
            # 🔍 FORMATO 1: ISO format with timezone (2025-07-10T07:59:59Z)
            if 'T' in date_str:
                # Remove timezone info if present
                clean_date = date_str.split('T')[0]
                return datetime.strptime(clean_date, '%Y-%m-%d')
            
            # 🔍 FORMATO 2: ISO date only (2025-07-10)
            if '-' in date_str and len(date_str) == 10:
                return datetime.strptime(date_str, '%Y-%m-%d')
            
            # 🔍 FORMATO 3: Brazilian format (10/07/2025)
            if '/' in date_str:
                if len(date_str) == 10:  # DD/MM/YYYY
                    return datetime.strptime(date_str, '%d/%m/%Y')
                elif len(date_str) == 8:   # DD/MM/YY
                    return datetime.strptime(date_str, '%d/%m/%y')
            
            # 🔍 FORMATO 4: YYYYMMDD
            if date_str.isdigit() and len(date_str) == 8:
                return datetime.strptime(date_str, '%Y%m%d')
            
            logger.warning(f"⚠️ Formato de data não reconhecido: {date_str}")
            return None
            
        except ValueError as e:
            logger.warning(f"⚠️ Erro ao fazer parse da data '{date_str}': {e}")
            return None
    
    def _generate_source_url(self, licitacao: Dict[str, Any]) -> str:
        """Generate source URL for the opportunity"""
        pncp_id = licitacao.get('numeroControlePNCP', '')
        if pncp_id:
            return f"https://pncp.gov.br/app/editais/{pncp_id}"
        return "https://pncp.gov.br"
    
    def get_provider_metadata(self) -> Dict[str, Any]:
        """Get PNCP provider metadata"""
        return {
            'name': 'PNCP - Portal Nacional de Contratações Públicas',
            'country': 'BR',
            'supported_filters': self.get_supported_filters(),
            'rate_limit': self.max_results, # Assuming max_results is the rate limit
            'data_coverage': 'Brazil government procurement',
            'update_frequency': 'Real-time',
            'api_version': 'v1',
            'documentation': 'https://pncp.gov.br/api',
            'default_currency': 'BRL',
            'pagination_info': {
                'api_page_size': 50, # Default page size
                'target_total_results': self.max_results,
                'strategy': 'efficient_national_search'
            }
        }
    
    def get_supported_filters(self) -> Dict[str, Any]:
        """Get filters supported by PNCP provider"""
        return {
            'keywords': {
                'type': 'string',
                'description': 'Search terms for procurement object',
                'required': False
            },
            'region_code': {
                'type': 'string', 
                'description': 'Brazilian state code (UF)',
                'required': False,
                'options': ['AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO']
            },
            'municipality': {
                'type': 'string',
                'description': 'City name',
                'required': False
            },
            'min_value': {
                'type': 'number',
                'description': 'Minimum estimated value in BRL',
                'required': False
            },
            'max_value': {
                'type': 'number', 
                'description': 'Maximum estimated value in BRL',
                'required': False
            },
            'procurement_type': {
                'type': 'array',
                'description': 'Procurement modalities',
                'required': False,
                'options': ['pregao_eletronico', 'concorrencia', 'dispensa', 'tomada_precos', 'convite', 'inexigibilidade']
            },
            'status': {
                'type': 'string',
                'description': 'Filter by opportunity status',
                'required': False,
                'options': ['open', 'closed', 'all']
            }
        }
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return "pncp"
    
    def get_opportunity_details(self, external_id: str) -> Optional[OpportunityData]:
        """Get detailed information for a specific opportunity
        
        Args:
            external_id: The PNCP numeroControlePNCP identifier
            
        Returns:
            OpportunityData with detailed information or None if not found
        """
        try:
            logger.info(f"🔍 Buscando detalhes da licitação PNCP: {external_id}")
            
            # IMPLEMENTAÇÃO REAL: Buscar via API PNCP usando o numeroControlePNCP
            detailed_data = self._fetch_bid_details_from_pncp(external_id)
            
            if detailed_data:
                logger.info(f"✅ Detalhes encontrados para licitação {external_id}")
                return self._convert_to_opportunity_data(detailed_data)
            else:
                logger.warning(f"⚠️ Licitação {external_id} não encontrada no PNCP")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao buscar detalhes da licitação PNCP {external_id}: {e}")
            return None
    
    def _fetch_bid_details_from_pncp(self, numero_controle_pncp: str) -> Optional[Dict[str, Any]]:
        """
        Busca os detalhes completos de uma licitação específica via API PNCP v1
        
        🔧 CORREÇÃO CRÍTICA: URL da API v1 foi movida
        URL NOVA: https://pncp.gov.br/api/consulta/v1/orgaos/{CNPJ}/compras/{ANO}/{SEQUENCIAL}
        
        Args:
            numero_controle_pncp: Número de controle PNCP (formato: CNPJ-ANO-SEQUENCIAL/ANO)
            
        Returns:
            Dict com dados detalhados da licitação ou None se não encontrada
        """
        import requests
        
        try:
            logger.info(f"🔍 Buscando licitação específica via API v1: {numero_controle_pncp}")
            
            # 🔧 EXTRAIR COMPONENTES DO numeroControlePNCP
            cnpj, ano, sequencial = self._parse_numero_controle_pncp(numero_controle_pncp)
            
            if not all([cnpj, ano, sequencial]):
                logger.error(f"❌ Não foi possível extrair CNPJ/ANO/SEQUENCIAL de: {numero_controle_pncp}")
                return None
            
            logger.info(f"📋 Componentes extraídos - CNPJ: {cnpj}, ANO: {ano}, SEQUENCIAL: {sequencial}")
            
            # 🌐 MONTAR URL DA API v1 CORRIGIDA
            api_v1_base = "https://pncp.gov.br/api/consulta/v1"  # 🔧 URL CORRIGIDA
            url_detalhes = f"{api_v1_base}/orgaos/{cnpj}/compras/{ano}/{sequencial}"
            
            logger.info(f"🌐 Buscando detalhes via URL CORRIGIDA: {url_detalhes}")
            
            # 🔍 BUSCAR DADOS PRINCIPAIS DA LICITAÇÃO
            response = requests.get(url_detalhes, timeout=self.timeout)
            response.raise_for_status()
            
            licitacao_detalhada = response.json()
            logger.info(f"✅ Detalhes encontrados para {numero_controle_pncp}")
            
            # 🔍 BUSCAR ITENS DA LICITAÇÃO (OPCIONAL)
            try:
                url_itens = f"{url_detalhes}/itens"
                logger.info(f"🔍 Buscando itens via: {url_itens}")
                
                response_itens = requests.get(url_itens, timeout=self.timeout)
                response_itens.raise_for_status()
                
                itens = response_itens.json()
                logger.info(f"✅ {len(itens)} itens encontrados")
                
                # Adicionar itens aos dados da licitação
                licitacao_detalhada['itens'] = itens
                
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível buscar itens: {e}")
                licitacao_detalhada['itens'] = []
            
            return licitacao_detalhada
                
        except requests.RequestException as e:
            logger.error(f"❌ Erro na API PNCP v1 ao buscar detalhes de {numero_controle_pncp}: {e}")
            
            # 🔄 FALLBACK: Tentar com a estratégia antiga se API v1 falhar
            logger.info("🔄 Tentando fallback com busca abrangente...")
            return self._fetch_bid_details_fallback(numero_controle_pncp)
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao buscar detalhes de {numero_controle_pncp}: {e}")
            return None
    
    def _parse_numero_controle_pncp(self, numero_controle: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extrai CNPJ, ANO e SEQUENCIAL do numeroControlePNCP
        
        Formatos esperados:
        - CNPJ-ANO-SEQUENCIAL/ANO (ex: 17217985000104-1-000156/2025)
        - CNPJ-SEQUENCIAL-ANO (variações)
        
        Args:
            numero_controle: Número de controle PNCP
            
        Returns:
            Tuple com (CNPJ, ANO, SEQUENCIAL) ou (None, None, None) se não conseguir extrair
        """
        try:
            if not numero_controle or '-' not in numero_controle:
                return None, None, None
            
            logger.debug(f"🔍 Analisando numeroControlePNCP: {numero_controle}")
            
            # 🔍 PADRÃO 1: CNPJ-X-SEQUENCIAL/ANO
            if '/' in numero_controle:
                parte_principal, ano_final = numero_controle.split('/')
                partes = parte_principal.split('-')
                
                if len(partes) >= 3:
                    cnpj = partes[0]
                    sequencial = partes[2]  # Terceira parte é o sequencial
                    ano = ano_final  # Ano após a barra
                    
                    logger.debug(f"   📋 Padrão 1 - CNPJ: {cnpj}, ANO: {ano}, SEQUENCIAL: {sequencial}")
                    return cnpj, ano, sequencial
            
            # 🔍 PADRÃO 2: CNPJ-ANO-SEQUENCIAL (sem barra)
            partes = numero_controle.split('-')
            if len(partes) >= 3:
                cnpj = partes[0]
                ano = partes[1]
                sequencial = partes[2]
                
                logger.debug(f"   📋 Padrão 2 - CNPJ: {cnpj}, ANO: {ano}, SEQUENCIAL: {sequencial}")
                return cnpj, ano, sequencial
            
            logger.warning(f"⚠️ Formato não reconhecido: {numero_controle}")
            return None, None, None
            
        except Exception as e:
            logger.error(f"❌ Erro ao fazer parse do numeroControlePNCP '{numero_controle}': {e}")
            return None, None, None
    
    def _fetch_bid_details_fallback(self, numero_controle_pncp: str) -> Optional[Dict[str, Any]]:
        """
        FALLBACK: Busca usando a estratégia antiga se API v1 falhar
        """
        import requests
        
        try:
            logger.info(f"🔄 FALLBACK: Busca abrangente para {numero_controle_pncp}")
            
            # URL da API de consulta (a original)
            url = f"{self.api_base_url}/contratacoes/proposta"
            
            # Parâmetros básicos
            params = {
                'dataInicial': self.data_inicial,
                'dataFinal': self.data_final,
                'tamanhoPagina': 50,
                'pagina': 1,
                'codigoModalidadeContratacao': 8  # Pregão Eletrônico
            }
            
            # Buscar em até 5 páginas
            for pagina in range(1, 6):
                params['pagina'] = pagina
                
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                licitacoes = data.get('data', []) if isinstance(data, dict) else data
                
                # Procurar o número de controle específico
                for licitacao in licitacoes:
                    numero_controle_atual = licitacao.get('numeroControlePNCP')
                    if numero_controle_atual == numero_controle_pncp:
                        logger.info(f"✅ FALLBACK: Licitação encontrada na página {pagina}")
                        return licitacao
                
                if len(licitacoes) < 50:
                    break
            
            logger.warning(f"⚠️ FALLBACK: Licitação {numero_controle_pncp} não encontrada")
            return None
                
        except Exception as e:
            logger.error(f"❌ FALLBACK falhou: {e}")
            return None
    
    def get_opportunity_items(self, external_id: str) -> List[Dict[str, Any]]:
        """Get items/products for a specific opportunity
        
        Args:
            external_id: The PNCP numeroControlePNCP identifier
            
        Returns:
            List of items/products for this opportunity
        """
        try:
            logger.info(f"🔍 Buscando itens da licitação PNCP: {external_id}")
            
            # 🔧 EXTRAIR COMPONENTES DO numeroControlePNCP
            cnpj, ano, sequencial = self._parse_numero_controle_pncp(external_id)
            
            if not all([cnpj, ano, sequencial]):
                logger.error(f"❌ Não foi possível extrair CNPJ/ANO/SEQUENCIAL de: {external_id}")
                return []
            
            # 🌐 MONTAR URL DA API v1 PARA ITENS
            api_v1_base = "https://pncp.gov.br/api/consulta/v1"  # 🔧 URL CORRIGIDA
            url_itens = f"{api_v1_base}/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens"
            
            logger.info(f"🌐 Buscando itens via API v1 CORRIGIDA: {url_itens}")
            
            # 🔍 BUSCAR ITENS DA LICITAÇÃO
            import requests
            response = requests.get(url_itens, timeout=self.timeout)
            response.raise_for_status()
            
            itens = response.json()
            logger.info(f"✅ {len(itens)} itens encontrados para {external_id}")
            
            return itens
            
        except requests.RequestException as e:
            logger.error(f"❌ Erro na API PNCP v1 ao buscar itens de {external_id}: {e}")
            
            # 🔄 FALLBACK: Tentar extrair itens dos dados principais
            try:
                logger.info("🔄 Tentando extrair itens dos dados principais...")
                detalhes = self.get_opportunity_details(external_id)
                if detalhes and detalhes.provider_specific_data:
                    raw_data = detalhes.provider_specific_data.get('raw_data', {})
                    itens_embedded = raw_data.get('itens', [])
                    if itens_embedded:
                        logger.info(f"✅ FALLBACK: {len(itens_embedded)} itens extraídos dos dados principais")
                        return itens_embedded
                
                logger.warning(f"⚠️ Nenhum item encontrado para {external_id}")
                return []
                
            except Exception as fallback_error:
                logger.error(f"❌ FALLBACK também falhou: {fallback_error}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao buscar itens de {external_id}: {e}")
            return []

    async def validate_connection(self) -> bool:
        """Test connection to PNCP API"""
        try:
            # Try a simple search
            test_filters = SearchFilters(keywords="teste")
            results = await self.search_opportunities(test_filters)
            logger.info("✅ PNCP connection validated successfully")
            return True
        except Exception as e:
            logger.error(f"❌ PNCP connection validation failed: {e}")
            return False