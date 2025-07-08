# Estratégia de Cache Redis - Busca Diária + Filtros de Usuários

## 🎯 **ARQUITETURA DE CACHE**

### **1. Processo Diário (Background)**
```bash
# Cron Job - Executar 1x por dia (ex: 06:00)
python scripts/daily_fetch_all_bids.py
```

**O que faz:**
- ✅ Busca **20.000 licitações** de todos os UFs do PNCP
- ✅ Salva no **Redis com chave estruturada**
- ✅ Cache dura **24 horas** (renovado diariamente)
- ✅ **Compressão automática** para datasets >1MB

### **2. Estrutura das Chaves Redis**

```python
# ESTRUTURA ATUAL (correta)
"pncp_search_v2:{hash_params}"          # Dados normais
"pncp_search_v2:{hash_params}:gz"       # Dados comprimidos (>1MB)

# DADOS ARMAZENADOS
{
    "data": [
        {
            "numeroControlePNCP": "unique_id",
            "objetoCompra": "texto_da_licitacao",
            "municipio": "cidade",
            "uf": "estado",
            "valorEstimado": 50000,
            "dataPublicacao": "2025-01-07",
            # ... todos os campos da licitação
        }
    ],
    "total": 20000,
    "cached_at": "2025-01-07T10:30:00",
    "strategy": "daily_comprehensive_fetch"
}
```

### **3. Busca de Usuários (Real-time)**

**Quando usuário busca por "equipamento médico" + "MG":**

1. **Frontend chama:** `/api/search/unified?keywords=equipamento médico&region_code=MG`

2. **Backend faz:**
   ```python
   # 1. Busca TODO o dataset do Redis (20K licitações)
   cached_data = redis.get("pncp_search_v2:all_bids")
   
   # 2. Aplica filtros EM MEMÓRIA (muito rápido!)
   filtered_results = []
   for licitacao in cached_data['data']:
       # Filtro por estado
       if licitacao['uf'] == 'MG':
           # Filtro por palavras-chave (com sinônimos)
           if search_keywords_match(licitacao['objetoCompra'], expanded_keywords):
               filtered_results.append(licitacao)
   
   # 3. Retorna resultados filtrados
   return filtered_results
   ```

### **4. Redis NÃO é Baseado em Colunas**

❌ **Redis não trabalha com colunas** como SQL
✅ **Redis é chave-valor:** cada chave armazena um JSON completo

**Vantagens desta abordagem:**
- 🚀 **Busca ultra-rápida:** dados já em memória
- 🔍 **Filtros flexíveis:** qualquer combinação
- 📊 **Expansão de sinônimos:** aplicada em tempo real
- 💾 **Cache inteligente:** compressão automática

## 🔧 **IMPLEMENTAÇÃO DETALHADA**

### **Serviços Envolvidos:**

1. **Daily Fetch Service** (background)
2. **UnifiedSearchService** (filtros + sinônimos)  
3. **Redis Cache** (armazenamento comprimido)
4. **Synonym Service** (expansão de termos)

### **Fluxo Completo:**

```
[CRON JOB] → [PNCP API] → [Redis Cache] ← [User Search] ← [Frontend]
     ↓            ↓           ↓              ↑              ↑
  Busca 20K    Comprime    Cache 24h    Filtros rápidos   UI amigável
  licitações    dados      em Redis     com sinônimos     para usuário
``` 