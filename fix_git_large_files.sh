#!/bin/bash

# ===============================================
# SCRIPT PARA CORRIGIR ARQUIVOS GRANDES NO GIT
# Remove modelos ML do histórico do repositório
# ===============================================

echo "🔧 REMOVENDO ARQUIVOS GRANDES DO GIT..."
echo "========================================"

# 1. Remover arquivos grandes do index se estiverem staged
echo "📂 Removendo cache/ do staging area..."
git rm -r --cached cache/ 2>/dev/null || echo "   (cache/ não estava no staging)"

# 2. Remover do histórico usando git filter-branch
echo "🗑️ Removendo do histórico do git..."
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch -r cache/' \
--prune-empty --tag-name-filter cat -- --all

# 3. Limpar referências
echo "🧹 Limpando referências..."
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 4. Verificar se ainda há arquivos grandes
echo "🔍 Verificando arquivos grandes restantes..."
find . -size +50M -not -path "./venv/*" -not -path "./.git/*" 2>/dev/null | head -10

echo ""
echo "✅ LIMPEZA CONCLUÍDA!"
echo "💡 Agora você pode fazer:"
echo "   git add ."
echo "   git commit -m 'fix: remove ML cache from repository'"
echo "   git push origin main --force"
echo ""
echo "⚠️ AVISO: Use --force com cuidado em repositórios compartilhados!" 