"""
Carregador de variáveis de ambiente para o projeto Alicit
"""

import os
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """Carrega as variáveis de ambiente do arquivo config.env"""
    
    # Buscar arquivo config.env na raiz do projeto
    project_root = Path(__file__).parent.parent.parent
    config_file = project_root / "config.env"
    
    if config_file.exists():
        load_dotenv(config_file)
        print(f"✅ Variáveis de ambiente carregadas de: {config_file}")
    else:
        print(f"⚠️ Arquivo config.env não encontrado em: {config_file}")
        return
    
    # Mostrar configurações importantes (sem expor senhas)
    print("🔧 Configurações carregadas:")
    print(f"  - DATABASE_URL: {'✅ Configurado' if os.getenv('DATABASE_URL') else '❌ Não configurado'}")
    print(f"  - SUPABASE_URL: {'✅ Configurado' if os.getenv('SUPABASE_URL') else '❌ Não configurado'}")
    print(f"  - SUPABASE_ANON_KEY: {'✅ Configurado' if os.getenv('SUPABASE_ANON_KEY') else '❌ Não configurado'}")
    print(f"  - OPENAI_API_KEY: {'✅ Configurado' if os.getenv('OPENAI_API_KEY') else '❌ Não configurado'}")
    print(f"  - FLASK_DEBUG: {os.getenv('FLASK_DEBUG', 'True')}")
    print(f"  - LOG_LEVEL: {os.getenv('LOG_LEVEL', 'INFO')}")

def get_env_var(key: str, default: str = None):
    """Obter variável de ambiente com fallback para valor padrão."""
    return os.getenv(key, default)

if __name__ == "__main__":
    load_environment() 