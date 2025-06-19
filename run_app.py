#!/usr/bin/env python3
"""
Script de entrada para o backend Alicit
Resolve problemas de imports relativos executando a aplicação como módulo
"""

import sys
import os
from pathlib import Path

def main():
    """Executar a aplicação Alicit"""
    
    # Adicionar o diretório src ao Python path
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Importar e executar a aplicação
    try:
        from app import main as app_main
        app_main()
    except KeyboardInterrupt:
        print("\n🛑 Aplicação interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 