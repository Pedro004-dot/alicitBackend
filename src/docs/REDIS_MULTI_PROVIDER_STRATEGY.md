# Estratégia Redis Multi-Provider

## 🎯 **RECOMENDAÇÃO: REDIS UNIFICADO COM NAMESPACES**

### **❌ NÃO Recomendado: Redis Separado por Provider**
```bash
# Problemas desta abordagem:
redis-pncp.com:6379        # Redis para PNCP
redis-comprasnet.com:6379  # Redis para ComprasNet
redis-govbr.com:6379       # Redis para Gov.br

# Desvantagens:
- ❌ Custo multiplicado (3x Redis servers)
- ❌ Complexidade de configuração
- ❌ Impossível comparar dados entre providers
- ❌ Backup fragmentado
- ❌ Monitoramento complexo
```

### **✅ RECOMENDADO: Redis Unificado com Namespaces**
```bash
# Uma única instância Redis com chaves organizadas:
redis.alicit.com:6379

# Estrutura de chaves por provider:
pncp:search_v2:{hash}              # Cache de busca PNCP
pncp:daily_fetch:{date}            # Dados diários PNCP  
pncp:embeddings:{hash}             # Embeddings PNCP

comprasnet:search_v2:{hash}        # Cache de busca ComprasNet
comprasnet:daily_fetch:{date}      # Dados diários ComprasNet
comprasnet:embeddings:{hash}       # Embeddings ComprasNet

govbr:search_v2:{hash}             # Cache de busca Gov.br
govbr:daily_fetch:{date}           # Dados diários Gov.br
govbr:embeddings:{hash}            # Embeddings Gov.br

# Chaves unificadas (cross-provider):
unified:deduplication:{hash}       # Deduplicação entre providers
unified:search_combined:{hash}     # Resultados combinados
unified:synonyms:{term}            # Cache de sinônimos globais
```

## 🏗️ **IMPLEMENTAÇÃO DA ESTRATÉGIA**

### **1. Provider-Specific Cache Classes:**

```python
# adapters/pncp_adapter.py
class PNCPAdapter(ProcurementDataSource):
    def __init__(self, config):
        self.cache_prefix = "pncp:"  # Namespace específico
        self.redis_client = get_redis_client()
    
    def _generate_cache_key(self, operation: str, params: Dict) -> str:
        """Gera chave com namespace do provider"""
        base_key = f"{self.cache_prefix}{operation}"
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        return f"{base_key}:{params_hash}"
    
    def search_opportunities(self, filters):
        # Cache específico do PNCP
        cache_key = self._generate_cache_key("search_v2", filters.__dict__)
        # ... resto da implementação

# adapters/comprasnet_adapter.py  
class ComprasNetAdapter(ProcurementDataSource):
    def __init__(self, config):
        self.cache_prefix = "comprasnet:"  # Namespace específico
        self.redis_client = get_redis_client()
    
    def _generate_cache_key(self, operation: str, params: Dict) -> str:
        base_key = f"{self.cache_prefix}{operation}"
        params_hash = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
        return f"{base_key}:{params_hash}"
```

### **2. Unified Cache Manager:**

```python
# services/cache/unified_cache_manager.py
class UnifiedCacheManager:
    """Gerencia cache entre múltiplos providers"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.unified_prefix = "unified:"
    
    def cache_combined_search(self, filters: SearchFilters, results: Dict[str, List]) -> str:
        """Cacheia resultado combinado de múltiplos providers"""
        cache_key = f"{self.unified_prefix}search_combined:{self._hash_filters(filters)}"
        
        cache_data = {
            'filters': filters.__dict__,
            'providers': list(results.keys()),
            'total_results': sum(len(provider_results) for provider_results in results.values()),
            'data': results,
            'cached_at': datetime.now().isoformat(),
            'ttl_hours': 24
        }
        
        # Comprimir se necessário (>1MB)
        serialized = json.dumps(cache_data, separators=(',', ':'), default=str)
        if len(serialized) > 1024 * 1024:
            import gzip
            serialized = gzip.compress(serialized.encode('utf-8'))
            cache_key = f"{cache_key}:gz"
        
        self.redis_client.setex(cache_key, timedelta(hours=24), serialized)
        return cache_key
    
    def get_combined_search(self, filters: SearchFilters) -> Optional[Dict]:
        """Recupera resultado combinado do cache"""
        base_key = f"{self.unified_prefix}search_combined:{self._hash_filters(filters)}"
        
        # Tentar versão comprimida primeiro
        compressed_key = f"{base_key}:gz"
        cached_data = self.redis_client.get(compressed_key)
        
        if cached_data:
            import gzip
            decompressed = gzip.decompress(cached_data).decode('utf-8')
            return json.loads(decompressed)
        
        # Fallback para versão normal
        cached_data = self.redis_client.get(base_key)
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    def invalidate_provider_cache(self, provider_name: str):
        """Invalida todo o cache de um provider específico"""
        pattern = f"{provider_name}:*"
        keys = self.redis_client.keys(pattern)
        if keys:
            deleted = self.redis_client.delete(*keys)
            logger.info(f"🧹 Invalidated {deleted} cache keys for provider {provider_name}")
    
    def get_cache_stats_by_provider(self) -> Dict[str, Dict]:
        """Estatísticas de cache por provider"""
        providers = ['pncp', 'comprasnet', 'govbr']
        stats = {}
        
        for provider in providers:
            pattern = f"{provider}:*"
            keys = self.redis_client.keys(pattern)
            
            total_size = 0
            key_count = len(keys)
            
            if keys:
                # Calcular tamanho total (sample de 10 chaves para performance)
                sample_keys = keys[:10] if len(keys) > 10 else keys
                for key in sample_keys:
                    try:
                        size = self.redis_client.memory_usage(key)
                        if size:
                            total_size += size
                    except:
                        continue
                
                # Estimar tamanho total
                if sample_keys:
                    avg_size = total_size / len(sample_keys)
                    estimated_total = avg_size * key_count
                else:
                    estimated_total = 0
            
            stats[provider] = {
                'key_count': key_count,
                'estimated_size_mb': estimated_total / 1024 / 1024,
                'last_updated': datetime.now().isoformat()
            }
        
        return stats
```

### **3. Daily Fetch per Provider:**

```python
# scripts/daily_fetch_all_providers.py
import asyncio
from datetime import datetime

async def fetch_provider_data(provider_name: str):
    """Busca dados diários de um provider específico"""
    try:
        logger.info(f"🔍 Starting daily fetch for {provider_name}")
        
        # Criar adapter específico
        factory = DataSourceFactory()
        provider = factory.create(provider_name)
        
        # Buscar dados com filtros amplos
        filters = SearchFilters(
            # Busca ampla para capturar máximo de dados
            publication_date_from=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            publication_date_to=datetime.now().strftime('%Y-%m-%d')
        )
        
        opportunities = provider.search_opportunities(filters)
        
        # Cache com namespace do provider
        cache_key = f"{provider_name}:daily_fetch:{datetime.now().strftime('%Y-%m-%d')}"
        cache_data = {
            'provider': provider_name,
            'fetch_date': datetime.now().isoformat(),
            'total_opportunities': len(opportunities),
            'data': [provider._opportunity_to_dict(opp) for opp in opportunities]
        }
        
        # Salvar no Redis
        redis_client = get_redis_client()
        redis_client.setex(cache_key, timedelta(hours=25), json.dumps(cache_data, default=str))
        
        logger.info(f"✅ {provider_name}: {len(opportunities)} opportunities cached")
        return len(opportunities)
        
    except Exception as e:
        logger.error(f"❌ Error fetching {provider_name}: {e}")
        return 0

async def daily_fetch_all_providers():
    """Busca dados de todos os providers em paralelo"""
    providers = ['pncp', 'comprasnet', 'govbr']  # Providers ativos
    
    logger.info(f"🚀 Starting daily fetch for {len(providers)} providers")
    
    # Executar em paralelo para otimizar tempo
    tasks = [fetch_provider_data(provider) for provider in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Compilar estatísticas
    total_opportunities = 0
    successful_providers = 0
    
    for i, result in enumerate(results):
        provider = providers[i]
        if isinstance(result, Exception):
            logger.error(f"❌ {provider} failed: {result}")
        else:
            total_opportunities += result
            successful_providers += 1
            logger.info(f"✅ {provider}: {result} opportunities")
    
    logger.info(f"📊 Daily fetch completed: {total_opportunities} total opportunities from {successful_providers}/{len(providers)} providers")

if __name__ == "__main__":
    asyncio.run(daily_fetch_all_providers())
```

## 📊 **MONITORAMENTO E GESTÃO**

### **1. Cache Health Dashboard:**

```python
# routes/cache_admin_routes.py
@app.route('/admin/cache/stats')
def cache_stats():
    """Endpoint para monitorar cache de todos os providers"""
    manager = UnifiedCacheManager()
    
    return jsonify({
        'provider_stats': manager.get_cache_stats_by_provider(),
        'unified_stats': {
            'combined_searches': len(redis_client.keys('unified:search_combined:*')),
            'deduplication_cache': len(redis_client.keys('unified:deduplication:*')),
            'synonyms_cache': len(redis_client.keys('unified:synonyms:*'))
        },
        'redis_info': redis_client.info()
    })

@app.route('/admin/cache/invalidate/<provider>')
def invalidate_provider_cache(provider):
    """Invalidar cache de um provider específico"""
    manager = UnifiedCacheManager()
    manager.invalidate_provider_cache(provider)
    return jsonify({'success': True, 'message': f'Cache invalidated for {provider}'})
```

### **2. Configuração Redis Otimizada:**

```python
# config/redis_config.py
class RedisMultiProviderConfig:
    
    @staticmethod
    def get_redis_config():
        return {
            # Configuração otimizada para múltiplos providers
            'maxmemory': '2gb',
            'maxmemory-policy': 'allkeys-lru',  # Remove chaves menos usadas
            'save': '900 1 300 10 60 10000',    # Backup automático
            'databases': 16,                     # Múltiplos DBs se necessário
            
            # Compressão para economizar espaço
            'hash-max-ziplist-entries': 512,
            'hash-max-ziplist-value': 64,
            'list-max-ziplist-size': -2,
            'set-max-intset-entries': 512,
            'zset-max-ziplist-entries': 128,
            'zset-max-ziplist-value': 64,
        }
```

## ✅ **VANTAGENS DA ESTRATÉGIA UNIFICADA**

### **1. Operacionais:**
- ✅ **Custo reduzido:** 1 Redis em vez de N Redis
- ✅ **Backup unificado:** Uma única estratégia de backup
- ✅ **Monitoramento central:** Dashboard único
- ✅ **Configuração simplificada:** Menos infraestrutura

### **2. Técnicas:**
- ✅ **Cross-provider queries:** Comparar dados entre providers
- ✅ **Deduplicação global:** Eliminar duplicatas entre providers
- ✅ **Cache combinado:** Resultados unificados cacheados
- ✅ **Namespace isolation:** Providers não interferem entre si

### **3. Escalabilidade:**
- ✅ **Adição fácil de providers:** Só criar novo namespace
- ✅ **Redis Cluster ready:** Pode escalar horizontalmente
- ✅ **Particionamento lógico:** Por provider ou por funcionalidade
- ✅ **TTL independente:** Cada provider pode ter políticas diferentes

## 🔧 **IMPLEMENTAÇÃO RECOMENDADA**

```bash
# 1. Single Redis Instance (Production)
redis-server --maxmemory 4gb --maxmemory-policy allkeys-lru

# 2. Namespace Structure
pncp:*                    # PNCP specific data
comprasnet:*              # ComprasNet specific data  
govbr:*                   # Gov.br specific data
unified:*                 # Cross-provider data

# 3. Daily Fetch Schedule (crontab)
0 6 * * * /usr/bin/python3 /app/scripts/daily_fetch_all_providers.py

# 4. Cache Cleanup (weekly)
0 2 * * 0 /usr/bin/python3 /app/scripts/cleanup_old_cache.py
```

**Conclusão:** Redis unificado com namespaces é a **estratégia mais eficiente e econômica** para múltiplos providers! 