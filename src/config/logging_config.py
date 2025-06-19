import logging
import os
from pathlib import Path

def setup_logging():
    # Criar pasta de logs
    Path("logs").mkdir(exist_ok=True)
    
    # Configurar formato
    logging.basicConfig(
        level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/rag.log'),
            logging.StreamHandler()
        ]
    ) 