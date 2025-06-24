# 🚀 **ALICIT BACKEND - ENDPOINTS DISPONÍVEIS**

## 📡 **URL Base Railway**
```
https://alicit-backend-production-XXXX.up.railway.app
```

## 🔐 **CORS Configurado Para:**
- `https://alicit-front.vercel.app` (Frontend Principal)
- `https://alicit-saas.vercel.app` (Backup/Staging)
- `http://localhost:3000` (Desenvolvimento)
- `http://localhost:3001` (Desenvolvimento Alternativo)

---

## 📋 **RESUMO DE ENDPOINTS (78 TOTAL)**

### 🔐 **Autenticação (/api/auth/*) - 15 endpoints**
- `POST /api/auth/register` - Cadastro de usuário
- `POST /api/auth/verify-email` - Verificar email
- `POST /api/auth/resend-verification` - Reenviar verificação
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/auth/logout-all` - Logout de todos dispositivos
- `POST /api/auth/forgot-password` - Esqueci senha
- `POST /api/auth/verify-password-code` - Verificar código
- `POST /api/auth/reset-password` - Resetar senha
- `GET /api/auth/me` - Dados do usuário logado
- `PUT /api/auth/me` - Atualizar perfil
- `POST /api/auth/change-password` - Alterar senha
- `POST /api/auth/verify-token` - Verificar token
- `POST /api/auth/refresh-token` - Renovar token
- `GET /api/auth/sessions` - Listar sessões ativas

### 🏢 **Empresas (/api/companies/*) - 10 endpoints**
- `GET /api/companies/` - Listar empresas
- `POST /api/companies/` - Criar empresa
- `GET /api/companies/<id>` - Buscar empresa por ID
- `PUT /api/companies/<id>` - Atualizar empresa
- `DELETE /api/companies/<id>` - Deletar empresa
- `GET /api/companies/all` - Todas as empresas
- `GET /api/companies/profile` - Perfil da empresa
- `GET /api/companies/statistics` - Estatísticas
- `GET /api/companies/health` - Health check
- `GET /api/companies/matches` - Matches da empresa

### 📄 **Licitações (/api/bids/*) - 20 endpoints**
- `GET /api/bids/` - Listar licitações
- `GET /api/bids/detail` - Detalhes de licitação
- `GET /api/bids/items` - Itens de licitação
- `GET /api/bids/documents` - Documentos
- `GET /api/bids/test-storage` - Teste de storage
- `GET /api/bids/recent` - Licitações recentes
- `GET /api/bids/status/<status>` - Por status
- `GET /api/bids/active` - Licitações ativas
- `GET /api/bids/srp-opportunities` - Oportunidades SRP
- `GET /api/bids/active-proposals` - Propostas ativas
- `GET /api/bids/materials-opportunities` - Oportunidades de materiais
- `GET /api/bids/services-opportunities` - Oportunidades de serviços
- `GET /api/bids/me-epp-opportunities` - Oportunidades MEI/EPP
- `GET /api/bids/search-by-ncm/<ncm>` - Busca por NCM
- `GET /api/bids/disputa-mode/<mode_id>` - Por modo de disputa
- `GET /api/bids/enhanced-statistics` - Estatísticas avançadas
- `GET /api/bids/<pncp_id>` - Licitação específica
- `GET /api/bids/<pncp_id>/items` - Itens específicos
- `GET /api/bids/detailed` - Licitações detalhadas
- `GET /api/bids/uf/<uf>` - Por UF
- `GET /api/bids/statistics` - Estatísticas gerais

### 🎯 **Matches (/api/matches/*) - 11 endpoints**
- `GET /api/matches/` - Listar matches
- `GET /api/matches/<match_id>` - Match específico
- `GET /api/matches/by-company` - Por empresa
- `GET /api/matches/company/<company_id>` - Matches de empresa
- `GET /api/matches/all` - Todos os matches
- `GET /api/matches/recent` - Matches recentes
- `GET /api/matches/statistics` - Estatísticas
- `GET /api/matches/grouped` - Matches agrupados
- `GET /api/matches/bid/<bid_id>` - Matches de licitação
- `GET /api/matches/score` - Por score
- `GET /api/matches/high-quality` - Alta qualidade

### 🎯 **Quality Matches (/api/quality-matches/*) - 5 endpoints**
- `POST /api/quality-matches/test-levels` - Testar níveis
- `POST /api/quality-matches/run-with-quality` - Executar com qualidade
- `POST /api/quality-matches/analyze-company` - Analisar empresa
- `GET /api/quality-matches/presets` - Presets disponíveis
- `POST /api/quality-matches/test-llm-validation` - Teste LLM

### 🔍 **PNCP (/api/pncp/*) - 4 endpoints**
- `POST /api/pncp/search/advanced` - Busca avançada
- `GET /api/pncp/licitacao/<pncp_id>/itens` - Itens por PNCP ID
- `POST /api/pncp/licitacao/<pncp_id>/itens/refresh` - Atualizar itens
- `GET /api/pncp/info` - Informações da API

### 🔍 **Busca Unificada (/api/search/*) - 2 endpoints**
- `POST /api/search/unified` - Busca unificada
- `GET /api/search/suggestions` - Sugestões de busca

### 🤖 **RAG/Chat (/api/rag/*) - 5 endpoints**
- `POST /api/rag/analisarDocumentos` - Analisar documentos
- `POST /api/rag/query` - Fazer pergunta
- `GET /api/rag/status` - Status do sistema
- `POST /api/rag/cache/invalidate` - Invalidar cache
- `POST /api/rag/reprocessar` - Reprocessar documentos

### ⚙️ **Sistema (/api/status/*, /api/config/*) - 7 endpoints**
- `GET /api/health` - Health check principal
- `GET /api/healthz` - Health check Railway
- `GET /api/status` - Status da aplicação
- `GET /api/status/daily-bids` - Licitações diárias
- `GET /api/status/reevaluate` - Status reavaliação
- `GET /api/config/options` - Opções de configuração
- `POST /api/search-new-bids` - Buscar novas licitações
- `POST /api/reevaluate-bids` - Reavaliar licitações

---

## 🛡️ **Autenticação**
- **JWT Bearer Token** nos headers: `Authorization: Bearer <token>`
- **Refresh Token** para renovação automática
- **Múltiplas sessões** com controle individual

## 📊 **Recursos Principais**
- ✅ **Busca Inteligente** com IA
- ✅ **Matching Automatizado** empresa-licitação
- ✅ **Análise de Qualidade** com LLM
- ✅ **RAG/Chat** para análise de documentos
- ✅ **Cache Redis** para performance
- ✅ **Integração PNCP** oficial
- ✅ **Processamento ML** com PyTorch
- ✅ **Storage Supabase** para documentos

## 🔧 **Tecnologias**
- **Backend**: Flask + Gunicorn
- **Database**: PostgreSQL (Supabase)
- **Cache**: Redis
- **ML**: PyTorch + sentence-transformers
- **Storage**: Supabase Storage
- **Deploy**: Railway + Docker

---

✅ **Status**: Produção no Railway
🌐 **CORS**: Configurado para frontends Vercel
🔒 **Segurança**: JWT + Rate Limiting
⚡ **Performance**: Redis Cache + ML otimizado 