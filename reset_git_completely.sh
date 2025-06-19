#!/bin/bash

# ===============================================
# SCRIPT PARA RESETAR COMPLETAMENTE O GIT
# Remove todo histórico e recomeça do zero
# ===============================================

echo "🔥 RESETANDO GIT COMPLETAMENTE..."
echo "================================="

# 1. Parar qualquer operação git em andamento
echo "🛑 Parando operações git..."
git reset --hard HEAD 2>/dev/null || true

# 2. Remover completamente o .git
echo "🗑️ Removendo .git completamente..."
rm -rf .git

# 3. Inicializar novo repositório
echo "🆕 Criando novo repositório git..."
git init

# 4. Configurar remote
echo "🔗 Configurando remote..."
git remote add origin https://github.com/Pedro004-dot/alicitBackend.git

# 5. Adicionar todos os arquivos (respeitando .gitignore)
echo "📁 Adicionando arquivos..."
git add .

# 6. Fazer commit inicial
echo "💾 Fazendo commit inicial..."
git commit -m "feat: Railway deployment setup with sentence-transformers

- Complete ML dependencies for sentence-transformers
- PyTorch CPU-only installation 
- Optimized Dockerfile for Railway
- Updated requirements and configurations
- Clean repository without large model files"

# 7. Tentar push
echo "🚀 Fazendo push..."
git push origin main --force

echo ""
echo "✅ RESET COMPLETO!"
echo "🎯 Repositório limpo e atualizado" 