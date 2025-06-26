# 🚀 Guia Postman - Nova Estratégia Thiago Implementada

## ✅ **Resumo das Mudanças**

- **POST** `/api/licitacoes/buscar` agora usa **as mesmas funções** do GET
- **✅ Múltiplos estados:** `["SP", "RJ", "MG"]` via array JSON
- **✅ Múltiplas cidades:** `["São Paulo", "Rio de Janeiro"]` via array JSON  
- **✅ Estratégia Thiago:** Busca ampla + Filtro local rigoroso
- **✅ Sinônimos locais:** Gerados via OpenAI (não enviados para API)

---

## 🔧 **Configuração do Postman**

### **Base URL:**
```
http://localhost:5000/api/licitacoes/buscar
```

### **Headers:**
```
Content-Type: application/json
```

---

## 📋 **Exemplos de Teste**

### **1. 🧪 Teste Básico - Termo Simples**

**Método:** `POST`
**Body (JSON):**
```json
{
    "palavra_chave": "medicamento",
    "estados": ["SP"],
    "usar_sinonimos": false,
    "threshold_relevancia": 0.5
}
```

**Resultado esperado:** 5-10 licitações de medicamentos em SP

---

### **2. 🌍 Teste Múltiplos Estados**

**Método:** `POST`
**Body (JSON):**
```json
{
    "palavra_chave": "limpeza",
    "estados": ["SP", "RJ", "MG"],
    "modalidades": ["pregao_eletronico"],
    "threshold_relevancia": 0.4
}
```

**Resultado esperado:** Licitações de limpeza em 3 estados

---

### **3. 🏙️ Teste Múltiplas Cidades (Busca Inteligente)**

**Método:** `POST`
**Body (JSON):**
```json
{
    "palavra_chave": "seguranca",
    "estados": ["SP"],
    "cidades": ["São Paulo", "Campinas", "Santos"],
    "valor_minimo": 50000,
    "usar_sinonimos": true
}
```

**Resultado esperado:** Ativa busca inteligente com múltiplas páginas

---

### **4. 🔍 Teste Múltiplos Termos**

**Método:** `POST`
**Body (JSON):**
```json
{
    "palavras_busca": ["sistema", "software", "informatica"],
    "estados": ["SP", "RJ"],
    "modalidades": ["pregao_eletronico", "concorrencia"],
    "threshold_relevancia": 0.3
}
```

**Resultado esperado:** Licitações de TI com threshold baixo

---

### **5. ⚡ Teste Completo com Todos os Filtros**

**Método:** `POST`
**Body (JSON):**
```json
{
    "palavra_chave": "material",
    "estados": ["SP", "MG", "RJ"],
    "cidades": ["São Paulo", "Belo Horizonte"],
    "modalidades": ["pregao_eletronico"],
    "valor_minimo": 10000,
    "valor_maximo": 500000,
    "usar_sinonimos": true,
    "threshold_relevancia": 0.6,
    "pagina": 1,
    "itens_por_pagina": 20
}
```

**Resultado esperado:** Busca complexa com todos os filtros

---

## 📊 **Campos da Resposta**

### **Estrutura da Resposta:**
```json
{
    "success": true,
    "message": "Busca realizada com sucesso. Total de 15 licitações encontradas.",
    "data": {
        "data": [...],           // Array de licitações
        "metadados": {
            "totalRegistros": 15,
            "totalPaginas": 1,
            "pagina": 1,
            "estrategia_busca": {
                "tipo": "Thiago Melhorada",
                "busca_ampla_api": true,
                "filtro_local_rigoroso": true,
                "threshold_relevancia": 0.6,
                "sinonimos_locais": true
            },
            "filtros_ativos": {
                "estados": ["SP", "RJ"],
                "modalidades": ["pregao_eletronico"],
                "cidades": ["São Paulo"]
            }
        }
    },
    "metodo": "POST com Nova Estratégia Thiago",
    "filtros_aplicados": {...},
    "palavras_buscadas": ["medicamento"]
}
```

### **Campos Importantes:**
- **`data.data[]`**: Array com as licitações encontradas
- **`data.metadados.totalRegistros`**: Total de resultados
- **`data.metadados.estrategia_busca`**: Info sobre a estratégia aplicada
- **`palavras_buscadas`**: Termos efetivamente buscados
- **`filtros_aplicados`**: Filtros que foram aplicados

---

## 🚨 **Troubleshooting**

### **❌ Erro: "Campo palavra_chave ou palavras_busca é obrigatório"**
**Solução:** Incluir pelo menos um dos campos:
```json
{
    "palavra_chave": "termo"
    // OU
    "palavras_busca": ["termo1", "termo2"]
}
```

### **❌ Erro 503: "Erro de comunicação com o PNCP"**
**Solução:** PNCP pode estar offline. Tentar novamente em alguns minutos.

### **⚠️ Poucos resultados encontrados**
**Soluções:**
1. Reduzir `threshold_relevancia` (ex: 0.3 em vez de 0.6)
2. Habilitar sinônimos: `"usar_sinonimos": true`
3. Usar termos mais genéricos: "material", "servico", "aquisicao"

---

## 🎯 **Comparação GET vs POST**

### **GET** `/api/licitacoes/buscar?palavras_busca=medicamento&estados=SP,RJ`
- ✅ Rápido para testes simples
- ✅ URL visível no navegador
- ❌ Limitado para filtros complexos

### **POST** `/api/licitacoes/buscar`
- ✅ Aceita filtros complexos via JSON
- ✅ Arrays nativos para múltiplos valores
- ✅ Mais controle sobre threshold e sinônimos
- ✅ **Mesma função interna do GET**

---

## 🔧 **Dicas de Performance**

1. **Para buscas rápidas:** Use `threshold_relevancia: 0.3`
2. **Para resultados precisos:** Use `threshold_relevancia: 0.7`
3. **Para máxima cobertura:** Habilite `usar_sinonimos: true`
4. **Com filtro de cidade:** Sistema ativa busca inteligente automaticamente

---

## 🎉 **Resultado Esperado**

Com essas mudanças, você deve ver:

- ✅ **Taxa de aprovação:** 5-30% (antes era 0%)
- ✅ **Múltiplos estados:** Funcionando via array JSON
- ✅ **Múltiplas cidades:** Ativa busca inteligente 
- ✅ **Sinônimos:** Gerados localmente via OpenAI
- ✅ **Logs detalhados:** Mostra processo de filtro rigoroso

**A estratégia Thiago está funcionando! 🚀** 