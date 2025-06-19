"""
Configurações específicas para ambiente de produção
"""
import os

class ProductionConfig:
    """Configurações para produção no Heroku"""
    
    # Configurações básicas do Flask
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'production-secret-key-change-this')
    
    # Configurações do Supabase (já funcionando)
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Configurações de API externa
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # Configurações do Redis para produção
    # No Heroku, você pode usar Redis To Go ou similar
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Configurações de CORS para produção
    # Você vai definir isso depois que souber a URL do frontend na Vercel
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Configurações de logging para produção
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Configurações específicas do matching
    SIMILARITY_THRESHOLD_PHASE1 = float(os.environ.get('SIMILARITY_THRESHOLD_PHASE1', 0.65))
    SIMILARITY_THRESHOLD_PHASE2 = float(os.environ.get('SIMILARITY_THRESHOLD_PHASE2', 0.70))
    
    # Configurações de performance
    PNCP_MAX_PAGES = int(os.environ.get('PNCP_MAX_PAGES', 5))
    PNCP_PAGE_SIZE = int(os.environ.get('PNCP_PAGE_SIZE', 50))
    
    # RAG configurations
    RAG_CHUNK_SIZE = int(os.environ.get('RAG_CHUNK_SIZE', 800))
    RAG_CHUNK_OVERLAP = int(os.environ.get('RAG_CHUNK_OVERLAP', 100))
    RAG_EMBEDDING_MODEL = os.environ.get('RAG_EMBEDDING_MODEL', 'voyage-3-large')
    RAG_CACHE_TTL = int(os.environ.get('RAG_CACHE_TTL', 3600))
    
    # Configurações do vetorizador
    VECTORIZER_TYPE = os.environ.get('VECTORIZER_TYPE', 'hybrid')
    CLEAR_MATCHES_BEFORE_REEVALUATE = os.environ.get('CLEAR_MATCHES_BEFORE_REEVALUATE', 'true').lower() == 'true' 