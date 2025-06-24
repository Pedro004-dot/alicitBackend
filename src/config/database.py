"""
Database configuration and manager for Supabase PostgreSQL
Versão simplificada baseada no que funcionava no api.py
"""

import os
import logging
import psycopg2
from contextlib import contextmanager
from typing import Dict, Any
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv('config.env')

logger = logging.getLogger(__name__)

def get_db_connection():
    """
    Conecta ao banco Supabase usando DATABASE_URL
    MESMA IMPLEMENTAÇÃO QUE FUNCIONAVA NO api.py
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Fallback: construir URL a partir das variáveis individuais
        host = os.getenv('DATABASE_HOST', 'db.hdlowzlkwrboqfzjewom.supabase.co')
        password = os.getenv('SUPABASE_DB_PASSWORD', 'TmzdMGDLyBDjNWdz')
        database_url = f"postgresql://postgres:{password}@{host}:5432/postgres"
        logger.info(f"🔄 Construindo DATABASE_URL a partir das variáveis: postgresql://postgres:***@{host}:5432/postgres")
    else:
        logger.info("✅ Usando DATABASE_URL do ambiente")
    
    try:
        conn = psycopg2.connect(database_url, cursor_factory=DictCursor)
        logger.info("✅ Conexão PostgreSQL estabelecida com sucesso")
        return conn
    except Exception as e:
        logger.error(f"❌ Erro ao conectar PostgreSQL: {e}")
        raise e

class DatabaseManager:
    """
    Gerenciador simplificado de banco de dados
    Usa a mesma abordagem que funcionava no api.py
    """
    
    def __init__(self):
        """Inicializar manager simples"""
        logger.info("🔄 Inicializando DatabaseManager simplificado...")
        self._test_connection()
    
    def _test_connection(self):
        """Testar conectividade inicial"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1, current_database(), version()")
                    result = cursor.fetchone()
                    logger.info(f"✅ Teste inicial OK - DB: {result[1]}")
        except Exception as e:
            logger.error(f"❌ Teste inicial falhou: {e}")
            raise e
    
    @contextmanager
    def get_connection(self):
        """
        Context manager para conexões
        Cria nova conexão a cada chamada (sem pool)
        """
        conn = None
        try:
            conn = get_db_connection()
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro na conexão: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    @contextmanager 
    def get_transaction(self):
        """Context manager para transações explícitas"""
        with self.get_connection() as conn:
            try:
                conn.autocommit = False
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Verificar status de saúde do banco"""
        status = {
            'database_url': 'postgresql://postgres:***@db.hdlowzlkwrboqfzjewom.supabase.co:5432/postgres',
            'connections': {},
            'connection_type': 'direct_postgresql',
            'features': ['direct_connection', 'no_pool', 'dict_cursor']
        }
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1, current_database(), version()")
                    result = cursor.fetchone()
            
            status['connections']['postgresql'] = {
                'status': 'healthy',
                'database': result[1] if result else 'unknown',
                'features': ['direct_connection', 'no_pool', 'dict_cursor']
            }
            status['overall'] = 'healthy'
        except Exception as e:
            status['connections']['postgresql'] = {
                'status': 'error',
                'error': str(e)
            }
            status['overall'] = 'unhealthy'
        
        return status
    
    def close_pool(self):
        """Compatibilidade - não há pool para fechar"""
        logger.info("💡 DatabaseManager simplificado - sem pool para fechar")
    
    def execute_query(self, query: str, params=None, fetch_one=False, fetch_all=False):
        """
        Executar query SQL com parâmetros
        
        Args:
            query: SQL query para executar
            params: Parâmetros para a query (dict ou tuple)
            fetch_one: Se deve retornar apenas um resultado
            fetch_all: Se deve retornar todos os resultados
            
        Returns:
            Resultado da query ou None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    if fetch_one:
                        return cursor.fetchone()
                    elif fetch_all:
                        return cursor.fetchall()
                    else:
                        # Para INSERT/UPDATE/DELETE, retornar número de linhas afetadas
                        return cursor.rowcount
                        
        except Exception as e:
            logger.error(f"❌ Erro ao executar query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise e

# Instância global do DatabaseManager (compatibilidade)
# Inicializar com lazy loading
class LazyDBManager:
    """Wrapper para inicialização lazy do DatabaseManager"""
    def __init__(self):
        self._instance = None
    
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = DatabaseManager()
        return getattr(self._instance, name)

db_manager = LazyDBManager()

def get_db_manager():
    """Obter instância do DatabaseManager com lazy loading"""
    if hasattr(db_manager, '_instance') and db_manager._instance is None:
        db_manager._instance = DatabaseManager()
    return db_manager 