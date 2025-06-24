# Exemplos de Teste - Filtros PNCP

## Endpoint para Testes
```
POST http://localhost:5001/api/pncp/search/advanced
Content-Type: application/json
```

## 1. Busca SEM Filtros (Básica)

**Descrição:** Busca simples usando apenas palavras-chave, sem nenhum filtro aplicado.

```json
{
  "keywords": "desenvolvimento software sistema"
}
```

**O que esperar:**
- Busca em todas as modalidades
- Período padrão (últimos 90 dias)
- Máximo 10 páginas
- Filtros aplicados: {}
- Resultados diversos de diferentes modalidades e regiões

---

## 2. Busca COM Filtros Avançados

**Descrição:** Busca com múltiplos filtros para refinar os resultados.

```json
{
  "keywords": "serviços consultoria",
  "filtros": {
    "modalidade": "pregao_eletronico",
    "valor_min": 50000,
    "valor_max": 1000000,
    "situacao": "divulgada",
    "uf": "SP",
    "categoria": "servicos",
    "srp": true,
    "beneficio_mei_epp": true
  },
  "data_inicio": "20250301",
  "data_fim": "20250630",
  "max_pages": 5
}
```

**O que esperar:**
- Apenas pregões eletrônicos
- Valores entre R$ 50.000 e R$ 1.000.000
- Situação "Divulgada no PNCP"
- Apenas do estado de São Paulo
- Categoria "Serviços"
- Apenas com SRP (Sistema de Registro de Preços)
- Apenas com benefícios para ME/EPP
- Período específico: março a junho de 2025

---

## 3. Busca COM Filtros Geográficos

**Descrição:** Busca focada em uma região específica com filtros de valor.

```json
{
  "keywords": "serviços",
  "filtros": {
    "modalidade": "todas",
    "uf": "RS",
    "municipio": "Porto Alegre",
    "valor_min": 100000,
    "situacao": "divulgada"
  },
  "max_pages": 3
}
```

**O que esperar:**
- Todas as modalidades
- Apenas do Rio Grande do Sul
- Preferencialmente de Porto Alegre
- Valores acima de R$ 100.000
- Situação "Divulgada no PNCP"

---

## 4. Busca COM Filtros de Modalidade Específica

**Descrição:** Busca focada em uma modalidade específica com filtros de prazo.

```json
{
  "keywords": "obras construção",
  "filtros": {
    "modalidade": "concorrencia",
    "valor_min": 500000,
    "categoria": "obras",
    "situacao": "divulgada"
  },
  "data_inicio": "20250101",
  "data_fim": "20250631",
  "include_items": true,
  "max_pages": 5
}
```

**O que esperar:**
- Apenas modalidade "Concorrência"
- Valores acima de R$ 500.000
- Categoria "Obras"
- Itens detalhados incluídos
- Período: todo o primeiro semestre de 2025

---

## 5. Busca COM Filtros de Benefícios ME/EPP

**Descrição:** Busca específica para empresas de pequeno porte.

```json
{
  "keywords": "serviços",
  "filtros": {
    "modalidade": "pregao_eletronico",
    "beneficio_mei_epp": true,
    "valor_max": 200000,
    "situacao": "divulgada"
  },
  "max_pages": 5
}
```

**O que esperar:**
- Apenas pregões eletrônicos
- Apenas licitações com benefícios para ME/EPP
- Valores até R$ 200.000
- Focado em pequenas empresas

---

## Endpoint para Consultar Filtros Disponíveis

```
GET http://localhost:5001/api/pncp/filters
```

Este endpoint retorna todos os filtros disponíveis no sistema com suas opções.

---

## Como Interpretar os Resultados

### Metadata Importante:
- `total_api_results`: Total de resultados da API PNCP
- `total_filtered_results`: Total após aplicar filtros
- `filtros_aplicados`: Quais filtros foram efetivamente aplicados
- `search_type`: Tipo de busca (advanced)
- `date_range`: Período de busca utilizado

### Campos dos Resultados:
- `total_score`: Score de relevância (soma de keyword_score + item_score)
- `keyword_score`: Score baseado nas palavras-chave
- `item_score`: Score baseado nos itens da licitação
- `relevance_score`: Score adicional de relevância

### Comparação Entre Testes:
1. **Sem filtros**: Deve retornar mais resultados, diversificados
2. **Com filtros**: Deve retornar menos resultados, mais precisos
3. **Filtros geográficos**: Deve focar na região especificada
4. **Filtros de modalidade**: Deve focar no tipo de licitação
5. **Filtros ME/EPP**: Deve focar em oportunidades para pequenas empresas

---

## Dicas de Teste:

1. **Compare os números:** Observe como `total_filtered_results` muda com diferentes filtros
2. **Verifique a aplicação:** Confirme se os filtros em `filtros_aplicados` correspondem ao enviado
3. **Analise os scores:** Resultados com scores mais altos são mais relevantes
4. **Teste combinações:** Experimente diferentes combinações de filtros
5. **Validação geográfica:** Verifique se os resultados realmente correspondem à UF/município filtrado 