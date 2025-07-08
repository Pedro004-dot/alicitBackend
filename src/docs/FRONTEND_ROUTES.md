# Rotas do Frontend - Sistema de Busca Unificado

## 🎯 **ROTAS PRINCIPAIS PARA O FRONTEND**

### **1. BUSCA PRINCIPAL (Recomendada)**

```typescript
// ENDPOINT: /api/search/unified
// MÉTODO: GET
// USO: Busca principal do usuário

const searchOpportunities = async (filters: SearchFilters) => {
  const params = new URLSearchParams();
  
  // Filtros obrigatórios/opcionais
  if (filters.keywords) params.append('keywords', filters.keywords);
  if (filters.region_code) params.append('region_code', filters.region_code);
  if (filters.min_value) params.append('min_value', filters.min_value.toString());
  if (filters.max_value) params.append('max_value', filters.max_value.toString());
  if (filters.publication_date_from) params.append('publication_date_from', filters.publication_date_from);
  if (filters.publication_date_to) params.append('publication_date_to', filters.publication_date_to);
  
  // Paginação
  params.append('page', filters.page?.toString() || '1');
  params.append('page_size', filters.page_size?.toString() || '20');
  
  const response = await fetch(`/api/search/unified?${params}`);
  return await response.json();
};

// EXEMPLO DE CHAMADA:
const results = await searchOpportunities({
  keywords: "equipamento médico",
  region_code: "MG",
  page: 1,
  page_size: 20
});
```

### **2. BUSCA POR PROVIDER ESPECÍFICO**

```typescript
// ENDPOINT: /api/search/providers/{provider_name}
// MÉTODO: GET
// USO: Buscar apenas no PNCP ou outros providers

const searchPNCPOnly = async (filters: SearchFilters) => {
  const params = new URLSearchParams();
  // ... mesmo formato da busca unificada
  
  const response = await fetch(`/api/search/providers/pncp?${params}`);
  return await response.json();
};

// EXEMPLO:
const pncpResults = await searchPNCPOnly({
  keywords: "software",
  region_code: "SP"
});
```

### **3. TEMPLATE DE FILTROS (Para UI)**

```typescript
// ENDPOINT: /api/search/filters/template
// MÉTODO: GET
// USO: Descobrir quais filtros estão disponíveis

const getFilterTemplate = async () => {
  const response = await fetch('/api/search/filters/template');
  const data = await response.json();
  
  return {
    availableFilters: data.data.filters,
    examples: data.data.examples,
    supportedProviders: data.data.supported_providers
  };
};

// RESPOSTA EXEMPLO:
{
  "success": true,
  "data": {
    "filters": {
      "keywords": "Optional search keywords",
      "region_code": "Optional region/state code (e.g., 'MG', 'SP')",
      "min_value": "Optional minimum estimated value",
      // ... outros filtros
    },
    "examples": {
      "basic_search": {
        "keywords": "equipamentos médicos",
        "region_code": "MG"
      }
    }
  }
}
```

### **4. STATUS DOS PROVIDERS**

```typescript
// ENDPOINT: /api/search/providers
// MÉTODO: GET
// USO: Ver quais providers estão ativos/conectados

const getProviderStats = async () => {
  const response = await fetch('/api/search/providers');
  return await response.json();
};

// RESPOSTA EXEMPLO:
{
  "success": true,
  "data": {
    "summary": {
      "total_providers": 1,
      "active_providers": 1,
      "connected_providers": 1
    },
    "providers": {
      "pncp": {
        "name": "pncp",
        "enabled": true,
        "connected": true,
        "status": "healthy"
      }
    }
  }
}
```

### **5. TESTE DE SAÚDE**

```typescript
// ENDPOINT: /api/search/test
// MÉTODO: GET
// USO: Verificar se o sistema está funcionando

const testSystem = async () => {
  const response = await fetch('/api/search/test');
  return await response.json();
};
```

## 📱 **INTEGRAÇÃO RECOMENDADA PARA O FRONTEND**

### **Componente React Exemplo:**

```tsx
import React, { useState, useEffect } from 'react';

interface SearchFilters {
  keywords?: string;
  region_code?: string;
  min_value?: number;
  max_value?: number;
  page?: number;
  page_size?: number;
}

const SearchPage = () => {
  const [filters, setFilters] = useState<SearchFilters>({});
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await searchOpportunities(filters);
      setResults(response.data.opportunities);
    } catch (error) {
      console.error('Erro na busca:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <SearchForm 
        filters={filters} 
        onChange={setFilters}
        onSubmit={handleSearch}
      />
      
      {loading && <div>Buscando licitações...</div>}
      
      <ResultsList opportunities={results} />
    </div>
  );
};
```

## 🔗 **CONFIGURAÇÃO NO FRONTEND**

### **1. Base URL (environment.ts):**

```typescript
export const environment = {
  apiBaseUrl: 'http://localhost:5000',
  searchEndpoints: {
    unified: '/api/search/unified',
    providers: '/api/search/providers',
    filters: '/api/search/filters/template',
    stats: '/api/search/providers',
    test: '/api/search/test'
  }
};
```

### **2. Service Dedicado:**

```typescript
// src/services/SearchService.ts
export class SearchService {
  private baseUrl = environment.apiBaseUrl;

  async searchUnified(filters: SearchFilters) {
    // Implementação da busca unificada
  }

  async getProviderStats() {
    // Implementação para stats
  }

  async testConnection() {
    // Implementação para teste de saúde
  }
}
```

## ⚡ **PERFORMANCE E CACHE**

**Frontend Cache Strategy:**
- ✅ **React Query** para cache de resultados de busca
- ✅ **Debounce** na busca (300ms)
- ✅ **Infinite scroll** para paginação
- ✅ **Background refresh** para manter dados atualizados

**Exemplo com React Query:**

```tsx
import { useQuery } from 'react-query';

const useSearchOpportunities = (filters: SearchFilters) => {
  return useQuery(
    ['opportunities', filters],
    () => searchOpportunities(filters),
    {
      staleTime: 5 * 60 * 1000, // 5 minutos
      cacheTime: 10 * 60 * 1000, // 10 minutos
      enabled: !!filters.keywords || !!filters.region_code
    }
  );
};
``` 