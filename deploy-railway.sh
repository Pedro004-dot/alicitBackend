#!/bin/bash

# ===============================================
# SCRIPT DE DEPLOY AUTOMATIZADO PARA RAILWAY
# ===============================================

set -e  # Exit on any error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
IMAGE_NAME="alicit-saas-railway"
DOCKER_USERNAME="${DOCKER_USERNAME:-seu-usuario}"  # Substitua por seu usuário
DOCKER_REPO="$DOCKER_USERNAME/$IMAGE_NAME"
VERSION="${VERSION:-latest}"

echo -e "${BLUE}🚀 Iniciando deploy do AlicitSaas para Railway...${NC}"

# 1. Verificar se Docker está rodando
echo -e "${YELLOW}📋 Verificando Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker não está rodando. Inicie o Docker Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker está rodando${NC}"

# 2. Build da imagem
echo -e "${YELLOW}🔨 Fazendo build da imagem Docker...${NC}"
docker build -f Dockerfile.railway -t $IMAGE_NAME:$VERSION .
echo -e "${GREEN}✅ Build concluído${NC}"

# 3. Tag para registry
echo -e "${YELLOW}🏷️  Criando tag para Docker Hub...${NC}"
docker tag $IMAGE_NAME:$VERSION $DOCKER_REPO:$VERSION
docker tag $IMAGE_NAME:$VERSION $DOCKER_REPO:latest
echo -e "${GREEN}✅ Tags criadas${NC}"

# 4. Login no Docker Hub (se necessário)
echo -e "${YELLOW}🔐 Verificando login no Docker Hub...${NC}"
if ! docker info | grep -q "Username"; then
    echo -e "${BLUE}🔑 Fazendo login no Docker Hub...${NC}"
    docker login
fi
echo -e "${GREEN}✅ Login verificado${NC}"

# 5. Push para Docker Hub
echo -e "${YELLOW}📤 Enviando imagem para Docker Hub...${NC}"
docker push $DOCKER_REPO:$VERSION
docker push $DOCKER_REPO:latest
echo -e "${GREEN}✅ Imagem enviada com sucesso${NC}"

# 6. Informações finais
echo -e "${BLUE}🎉 Deploy concluído!${NC}"
echo -e "${YELLOW}📋 Próximos passos:${NC}"
echo -e "1. Acesse: ${BLUE}https://railway.app${NC}"
echo -e "2. Clique em 'New Project' > 'Deploy from Docker Image'"
echo -e "3. Use a imagem: ${GREEN}$DOCKER_REPO:latest${NC}"
echo -e "4. Configure as variáveis de ambiente (veja railway-env-template.txt)"
echo -e "5. Aguarde o deploy (5-10 minutos)"
echo ""
echo -e "${GREEN}🔗 URL da imagem: $DOCKER_REPO:latest${NC}"
echo -e "${YELLOW}📄 Template de variáveis: railway-env-template.txt${NC}"

# 7. Opcional: Abrir Railway no navegador
read -p "Deseja abrir o Railway no navegador? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v open > /dev/null; then
        open https://railway.app
    elif command -v xdg-open > /dev/null; then
        xdg-open https://railway.app
    else
        echo -e "${YELLOW}Abra manualmente: https://railway.app${NC}"
    fi
fi

echo -e "${GREEN}🚀 Script concluído!${NC}" 