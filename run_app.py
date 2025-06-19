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
    
    # Obter caminhos do projeto
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    
    # Adicionar AMBOS os diretórios ao Python path
    # Isso permite tanto imports relativos quanto absolutos
    paths_to_add = [str(project_root), str(src_path)]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    print(f"🐍 PYTHONPATH configurado:")
    print(f"   📁 Projeto: {project_root}")
    print(f"   📁 Src: {src_path}")
    
    # Importar e executar a aplicação
    try:
        from app import main as app_main
        app_main()
    except KeyboardInterrupt:
        print("\n🛑 Aplicação interrompida pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 