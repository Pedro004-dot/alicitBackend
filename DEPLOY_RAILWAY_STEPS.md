# 🚂 Deploy no Railway - Passo a Passo

## 📋 **Pré-requisitos:**
- [ ] Conta no Railway (railway.app)
- [ ] Projeto já conectado ao GitHub
- [ ] Banco Supabase funcionando
- [ ] OpenAI API Key

## 🚀 **Passos para Deploy:**

### 1️⃣ **Configurar Banco de Dados (Já feito)**
```bash
# ✅ Seus dados Supabase (substitua pelos valores reais):
DATABASE_URL=postgresql://postgres.xxx:senha@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsXXX...
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsXXX...
```

### 2️⃣ **Adicionar Redis (Recomendado)**
1. No Railway Dashboard:
   - Clique em **"Add Service"**
   - Selecione **"Redis"**
   - ✅ A variável `REDIS_URL` será criada automaticamente

### 3️⃣ **Configurar Variáveis de Ambiente**
No Railway → Settings → Environment Variables, adicione:

#### 🚨 **OBRIGATÓRIAS:**
```bash
SECRET_KEY=sua-chave-secreta-super-forte-production-2024
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
```

#### 🔧 **CORS (Para conectar com frontend):**
```bash
CORS_ORIGINS=https://alicit-front.vercel.app,https://alicit-saas.vercel.app
```

### 4️⃣ **Deploy Automático**
- ✅ O Railway detecta o `railway.toml`
- ✅ Usa `Dockerfile.railway` otimizado
- ✅ Build e deploy automáticos após commit

### 5️⃣ **Verificar Deploy**
1. **Health Check:** `https://seu-app.railway.app/health`
2. **API Test:** `https://seu-app.railway.app/unified-search/health`
3. **Logs:** Railway Dashboard → Deploy Logs

## 🔧 **Configurações Opcionais:**

### 📧 **Email (Para autenticação):**
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
FROM_EMAIL=noreply@alicit.com
FRONTEND_URL=https://alicit-front.vercel.app
```

### 🚀 **APIs Externas (Para embeddings avançados):**
```bash
VOYAGE_API_KEY=pa-xxxxxxxxxx
HUGGINGFACE_API_KEY=hf_xxxxxxxxxx
```

## 🎯 **URLs Importantes:**

| Serviço | URL | Status |
|---------|-----|--------|
| API Health | `/health` | 200 OK |
| Search API | `/unified-search/search` | Funcional |
| Auth API | `/auth/health` | Funcional |
| Redis Status | `/system/cache-info` | Opcional |

## 🚨 **Resolução de Problemas:**

### ❌ **Deploy Failed:**
1. Check logs no Railway Dashboard
2. Verificar se todas as variáveis obrigatórias estão configuradas
3. Verificar se o Dockerfile.railway existe

### ❌ **API 500 Error:**
1. Verificar DATABASE_URL
2. Verificar SUPABASE credentials
3. Check logs: `railway logs`

### ❌ **CORS Error:**
1. Verificar CORS_ORIGINS
2. Adicionar URL do frontend
3. Teste com Postman primeiro

### ⚠️ **Redis Não Conecta:**
- Não é problema crítico
- Sistema funciona sem cache
- Para adicionar: Railway → Add Service → Redis

## ✅ **Deploy Bem-Sucedido:**
```json
{
  "status": "healthy",
  "message": "API funcionando corretamente",
  "environment": "production",
  "database": "healthy",
  "endpoints": 64,
  "version": "1.0.0"
}
```

## 🔄 **Comandos Úteis:**

```bash
# Ver logs em tempo real
railway logs

# Conectar ao projeto
railway link

# Deploy manual (se necessário)
railway up

# Status dos serviços
railway status
```

---
**🎉 Pronto! Seu backend está no ar no Railway!** 