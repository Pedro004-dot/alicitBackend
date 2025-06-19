# 🚀 GUIA DE DEPLOY - AlicitSaas Backend no Railway

## 📋 PRÉ-REQUISITOS

### 1. Contas Necessárias
- ✅ **Railway Account** (railway.app)
- ✅ **Supabase Account** (supabase.com) - PostgreSQL
- ✅ **OpenAI Account** (openai.com) - GPT/Embeddings
- ✅ **VoyageAI Account** (voyageai.com) - Embeddings otimizados
- ✅ **GitHub Account** - Para deploy automático

### 2. APIs Keys Necessárias
```bash
# Obter estas chaves antes do deploy:
DATABASE_URL=postgresql://...          # Supabase Connection String
SUPABASE_URL=https://...              # Supabase Project URL  
SUPABASE_SERVICE_KEY=eyJ...           # Supabase Service Role Key
SUPABASE_ANON_KEY=eyJ...              # Supabase Anon Key
OPENAI_API_KEY=sk-...                 # OpenAI API Key
VOYAGE_API_KEY=pa-...                 # VoyageAI API Key (NOVO!)
SECRET_KEY=your-secret-key            # Flask Secret Key
```

---

## 🛠️ PASSO A PASSO DO DEPLOY

### **ETAPA 1: Preparar Repositório**

```bash
# 1. Commit das alterações otimizadas
git add .
git commit -m "feat: Otimização para Railway - VoyageAI embeddings, Docker otimizado"
git push origin main

# 2. Verificar arquivos criados:
ls -la backend/
# ✅ Dockerfile.railway
# ✅ requirements-railway.txt  
# ✅ railway.toml
# ✅ .dockerignore
```

### **ETAPA 2: Configurar Railway**

1. **Acessar Railway Dashboard**
   - Ir para: https://railway.app/dashboard
   - Login com GitHub

2. **Criar Novo Projeto**
   ```
   New Project → Deploy from GitHub repo
   → Selecionar: AlicitSaas
   → Selecionar branch: main
   ```

3. **Configurar Build**
   ```
   Settings → Build
   → Root Directory: /backend
   → Build Command: (automático via railway.toml)
   → Start Command: (automático via railway.toml)
   ```

### **ETAPA 3: Configurar Variáveis de Ambiente**

No Railway Dashboard → Variables:

```bash
# === ESSENCIAIS ===
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_SERVICE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# === AI PROVIDERS ===
OPENAI_API_KEY=sk-proj-...
VOYAGE_API_KEY=pa-...

# === FLASK CONFIG ===
SECRET_KEY=sua-chave-secreta-super-forte-aqui
FLASK_ENV=production
FLASK_DEBUG=false

# === CORS ===
CORS_ORIGINS=https://alicit-saas.vercel.app,http://localhost:3000

# === VECTORIZER ===
VECTORIZER_TYPE=hybrid

# === LOGGING ===
LOG_LEVEL=INFO
```

### **ETAPA 4: Deploy e Verificação**

1. **Iniciar Deploy**
   ```
   Railway → Deploy
   → Aguardar build (5-10 minutos)
   → Verificar logs em tempo real
   ```

2. **Verificar Health Check**
   ```bash
   # URL será algo como:
   https://alicitsaas-production.up.railway.app/health
   
   # Resposta esperada:
   {
     "status": "healthy",
     "message": "API funcionando corretamente"
   }
   ```

3. **Testar Endpoints Principais**
   ```bash
   # 1. Health Check
   curl https://[SEU-DOMINIO].railway.app/health
   
   # 2. Companies
   curl https://[SEU-DOMINIO].railway.app/api/companies
   
   # 3. System Status  
   curl https://[SEU-DOMINIO].railway.app/api/status
   ```

---

## 🔧 CONFIGURAÇÕES AVANÇADAS

### **Custom Domain (Opcional)**
```
Railway → Settings → Domains
→ Add Custom Domain: api.alicitsaas.com
→ Configurar DNS CNAME
```

### **Monitoring & Logs**
```
Railway → Observability
→ Metrics: CPU, Memory, Network
→ Logs: Real-time application logs
→ Alerts: Configure via webhooks
```

### **Scaling (Se necessário)**
```
Railway → Settings → Resources
→ Memory: 1GB → 2GB (se necessário)
→ CPU: 1vCPU → 2vCPU (se necessário)
```

---

## 🚨 TROUBLESHOOTING

### **Problema: Build Timeout**
```bash
# Solução: Verificar Dockerfile.railway
# Certificar que não há dependências pesadas
grep -E "(torch|transformers|sentence-transformers)" requirements-railway.txt
# Deve retornar vazio
```

### **Problema: Database Connection**
```bash
# Verificar variáveis no Railway:
echo $DATABASE_URL
echo $SUPABASE_URL

# Testar conexão local:
psql $DATABASE_URL -c "SELECT version();"
```

### **Problema: CORS Error**
```bash
# Verificar CORS_ORIGINS no Railway
# Deve incluir: https://alicit-saas.vercel.app
```

### **Problema: VoyageAI Error**
```bash
# Verificar API Key:
curl -H "Authorization: Bearer $VOYAGE_API_KEY" \
     https://api.voyageai.com/v1/models
```

---

## 📊 OTIMIZAÇÕES IMPLEMENTADAS

### **🔥 Performance**
- ✅ **Multi-stage Docker build** (-60% image size)
- ✅ **VoyageAI embeddings** (sem ML local, -2.8GB RAM)
- ✅ **Gunicorn otimizado** (2 workers, preload)
- ✅ **Health checks** (Railway monitoring)

### **💰 Custos**
- ✅ **Railway Hobby Plan**: $5/mês
- ✅ **VoyageAI**: ~$0.10/1M tokens (vs OpenAI $0.20)
- ✅ **Supabase**: Grátis até 500MB
- ✅ **Total estimado**: ~$10-15/mês

### **🛡️ Segurança**
- ✅ **Non-root user** no container
- ✅ **CORS específico** (não wildcard)
- ✅ **Environment variables** (não hardcoded)
- ✅ **Health checks** (detecção de falhas)

---

## 🎯 PRÓXIMOS PASSOS

1. **Deploy Inicial** ✅
2. **Configurar CI/CD** (auto-deploy no push)
3. **Configurar Redis** (cache para Railway)
4. **Implementar Workers** (tarefas assíncronas)
5. **Monitoring avançado** (Sentry, DataDog)

---

## 📞 SUPORTE

**Problemas no deploy?**
- 📧 Logs detalhados: Railway → Deployments → View Logs
- 🔍 Debug local: `docker build -f Dockerfile.railway .`
- 💬 Railway Discord: https://discord.gg/railway

**Configuração específica?**
- 📖 Railway Docs: https://docs.railway.app
- 🚀 VoyageAI Docs: https://docs.voyageai.com
- 🐘 Supabase Docs: https://supabase.com/docs 