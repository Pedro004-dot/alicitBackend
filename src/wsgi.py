#!/usr/bin/env python3
"""
WSGI entry point para Gunicorn no Railway
Configura PYTHONPATH e inicia a aplicação
"""

import sys
import os
from pathlib import Path

# Configurar PYTHONPATH para importações corretas
current_dir = Path(__file__).parent  # /app/src
project_root = current_dir.parent    # /app

# Adicionar ambos os caminhos ao PYTHONPATH
paths_to_add = [str(project_root), str(current_dir)]
for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"🐍 WSGI PYTHONPATH configurado:")
print(f"   📁 Projeto: {project_root}")
print(f"   📁 Src: {current_dir}")

# Importar e criar aplicação
from app import create_app

# Criar aplicação Flask
application = create_app()

# Alias para compatibilidade
app = application

if __name__ == "__main__":
    # Para teste local
    application.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000))) 