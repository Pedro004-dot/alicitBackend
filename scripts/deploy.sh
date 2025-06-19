#!/bin/bash

echo "🚀 Script de Deploy - Alicit"
echo "=========================="

# Função para mostrar ajuda
show_help() {
    echo "Uso: ./scripts/deploy.sh [OPÇÃO]"
    echo ""
    echo "Opções:"
    echo "  backend    Deploy apenas o backend no Heroku"
    echo "  frontend   Deploy apenas o frontend na Vercel"
    echo "  both       Deploy backend e frontend"
    echo "  setup      Configurar remotes do Git"
    echo "  help       Mostrar esta ajuda"
    echo ""
}

# Função para deploy do backend
deploy_backend() {
    echo "📦 Fazendo deploy do backend no Heroku..."
    
    # Verificar se está no diretório correto
    if [ ! -f "Procfile" ]; then
        echo "❌ Erro: Execute este script da raiz do projeto"
        exit 1
    fi
    
    # Verificar se heroku remote existe
    if ! git remote | grep -q heroku; then
        echo "❌ Erro: Remote do Heroku não configurado"
        echo "💡 Execute: heroku git:remote -a seu-app-name"
        exit 1
    fi
    
    echo "🔄 Fazendo push para o Heroku..."
    git push heroku main
    
    echo "📊 Verificando logs..."
    heroku logs --tail --num 50
}

# Função para deploy do frontend
deploy_frontend() {
    echo "🌐 Fazendo deploy do frontend na Vercel..."
    
    # Navegar para o frontend
    cd frontend || {
        echo "❌ Erro: Diretório frontend não encontrado"
        exit 1
    }
    
    # Verificar se vercel está instalado
    if ! command -v vercel &> /dev/null; then
        echo "❌ Vercel CLI não encontrado"
        echo "💡 Instale com: npm i -g vercel"
        exit 1
    fi
    
    echo "🔄 Fazendo deploy na Vercel..."
    vercel --prod
    
    cd ..
}

# Função para configurar remotes
setup_remotes() {
    echo "⚙️ Configurando remotes do Git..."
    
    read -p "Digite o nome da sua app no Heroku: " heroku_app
    
    if [ -z "$heroku_app" ]; then
        echo "❌ Nome da app é obrigatório"
        exit 1
    fi
    
    echo "🔧 Adicionando remote do Heroku..."
    heroku git:remote -a "$heroku_app"
    
    echo "✅ Configuração concluída!"
    echo "💡 Agora você pode usar: ./scripts/deploy.sh backend"
}

# Processar argumentos
case $1 in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    both)
        deploy_backend
        deploy_frontend
        ;;
    setup)
        setup_remotes
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Opção inválida: $1"
        echo ""
        show_help
        exit 1
        ;;
esac

echo "✅ Deploy concluído!" 