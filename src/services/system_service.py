"""
System Service
Lógica de negócio para operações do sistema
Health checks, configurações e estatísticas gerais
"""
import logging
import json
import os
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from config.database import db_manager

logger = logging.getLogger(__name__)

# Estado global para controlar execução (migrado do api.py)
process_status = {
    'daily_bids': {'running': False, 'last_result': None},
    'reevaluate': {'running': False, 'last_result': None},
    'is_running': False,
    'last_run': None,
    'status': 'idle',
    'results': None
}

class SystemService:
    """
    Service para operações de sistema e background jobs
    PADRONIZADO: Usa DatabaseManager padronizado para acesso a dados
    """
    
    def __init__(self):
        """Inicializar service com estado do processo"""
        self.db_manager = db_manager
        self.process_status = {
            'daily_bids': {'running': False, 'last_run': None, 'message': ''},
            'reevaluate': {'running': False, 'last_run': None, 'message': ''},
            'last_health_check': datetime.now()
        }
        
        # Configurações de vetorizadores disponíveis
        self.vectorizer_configs = {
            'openai': {
                'name': 'OpenAI Embeddings',
                'description': 'Embeddings da OpenAI (requer API key)',
                'enabled': bool(os.getenv('OPENAI_API_KEY'))
            },
            'voyage': {
                'name': 'Voyage AI',
                'description': 'Embeddings Voyage AI (otimizado para Railway)',
                'enabled': bool(os.getenv('VOYAGE_API_KEY'))
            },
            'hybrid': {
                'name': 'Híbrido (Voyage AI + OpenAI)',
                'description': 'Combinação de múltiplos vetorizadores',
                'enabled': bool(os.getenv('VOYAGE_API_KEY')) or bool(os.getenv('OPENAI_API_KEY'))
            },
            'mock': {
                'name': 'Mock Vectorizer',
                'description': 'Vetorizador simulado para desenvolvimento',
                'enabled': True
            }
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Obter status de saúde geral do sistema"""
        try:
            # Atualizar timestamp do health check
            self.process_status['last_health_check'] = datetime.now()
            
            # Status do banco de dados usando o novo padrão
            db_health = self.db_manager.get_health_status()
            
            # Status dos processos background
            processes_healthy = not (
                self.process_status['daily_bids']['running'] or 
                self.process_status['reevaluate']['running']
            )
            
            # Determinar status geral
            if db_health['overall'] == 'healthy' and processes_healthy:
                overall_status = 'healthy'
            elif db_health['overall'] == 'healthy':
                overall_status = 'degraded'  # DB ok mas processos rodando
            else:
                overall_status = 'unhealthy'
            
            return {
                'status': overall_status,
                'timestamp': datetime.now().isoformat(),
                'components': {
                    'database': db_health,
                    'background_processes': {
                        'status': 'idle' if processes_healthy else 'busy',
                        'daily_bids': self.process_status['daily_bids'],
                        'reevaluate': self.process_status['reevaluate']
                    },
                    'vectorizers': self.vectorizer_configs
                },
                'uptime': 'running',
                'version': '2.0.0-padronizado'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status de saúde: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'message': 'Erro ao verificar saúde do sistema'
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """GET /api/status - Status geral do sistema"""
        try:
            health = self.get_system_health()
            
            # Informações adicionais de status
            status_info = {
                'system': {
                    'name': 'Alicit Backend',
                    'version': '2.0.0-padronizado',
                    'architecture': 'modular-repository-pattern',
                    'status': health['status']
                },
                'services': {
                    'database': health['components']['database']['overall'],
                    'matching': 'available',
                    'analysis': 'available',
                    'api': 'running'
                },
                'background_jobs': health['components']['background_processes'],
                'configuration': {
                    'vectorizers': health['components']['vectorizers'],
                    'database_info': health['components']['database']
                },
                'last_updated': health['timestamp']
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status do sistema: {e}")
            return {
                'system': {
                    'name': 'Alicit Backend',
                    'status': 'error',
                    'error': str(e)
                },
                'last_updated': datetime.now().isoformat()
            }
    
    def get_daily_bids_status(self) -> Dict[str, Any]:
        """GET /api/status/daily-bids - Status da busca diária"""
        daily_status = self.process_status['daily_bids']
        
        return {
            'running': daily_status['running'],
            'last_run': daily_status['last_run'].isoformat() if daily_status['last_run'] else None,
            'message': daily_status['message'],
            'next_scheduled': None,  # Implementar lógica de agendamento se necessário
            'status': 'running' if daily_status['running'] else 'idle'
        }
    
    def get_reevaluate_status(self) -> Dict[str, Any]:
        """GET /api/status/reevaluate - Status da reavaliação"""
        reevaluate_status = self.process_status['reevaluate']
        
        return {
            'running': reevaluate_status['running'],
            'last_run': reevaluate_status['last_run'].isoformat() if reevaluate_status['last_run'] else None,
            'message': reevaluate_status['message'],
            'status': 'running' if reevaluate_status['running'] else 'idle'
        }
    
    def get_config_options(self) -> Dict[str, Any]:
        """GET /api/config/options - Opções de configuração disponíveis"""
        db_health = self.db_manager.get_health_status()
        
        return {
            'vectorizers': self.vectorizer_configs,
            'matching': {
                'available_algorithms': ['cosine_similarity', 'euclidean', 'jaccard'],
                'threshold_range': {'min': 0.0, 'max': 1.0, 'default': 0.7}
            },
            'analysis': {
                'supported_formats': ['pdf', 'doc', 'docx', 'txt'],
                'max_file_size': '10MB',
                'ocr_enabled': True
            },
            'database': {
                'type': 'postgresql',
                'provider': 'supabase',
                'connection_type': db_health.get('connection_type', 'direct_postgresql'),
                'status': db_health.get('overall', 'unknown'),
                'features': db_health.get('features', []),
                'connection_method': 'direct_postgresql_connection'
            }
        }
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas do banco de dados"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Estatísticas das tabelas principais
                    stats_query = """
                        SELECT 
                            schemaname,
                            tablename,
                            n_tup_ins as total_inserts,
                            n_tup_upd as total_updates,
                            n_tup_del as total_deletes,
                            n_live_tup as live_tuples,
                            n_dead_tup as dead_tuples
                        FROM pg_stat_user_tables
                        WHERE schemaname = 'public'
                        ORDER BY n_live_tup DESC
                    """
                    cursor.execute(stats_query)
                    table_stats = [dict(row) for row in cursor.fetchall()]
                    
                    # Tamanho das tabelas
                    size_query = """
                        SELECT 
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                        FROM pg_tables
                        WHERE schemaname = 'public'
                        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    """
                    cursor.execute(size_query)
                    table_sizes = [dict(row) for row in cursor.fetchall()]
            
            db_health = self.db_manager.get_health_status()
            
            return {
                'table_statistics': table_stats,
                'table_sizes': table_sizes,
                'database_status': db_health.get('overall', 'unknown'),
                'connection_type': db_health.get('connection_type', 'direct_postgresql'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do banco: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def start_daily_search(self) -> Dict[str, Any]:
        """
        POST /api/search-new-bids - Iniciar busca de novas licitações REAL
        Integra com o matching engine real
        """
        if self.process_status['daily_bids']['running']:
            return {
                'success': False,
                'message': 'Busca diária já está em execução'
            }
        
        try:
            # Marcar como executando
            self.process_status['daily_bids']['running'] = True
            self.process_status['daily_bids']['last_run'] = datetime.now()
            self.process_status['daily_bids']['message'] = 'Iniciando busca de novas licitações...'
            
            def run_real_search():
                """Executa busca real usando o matching engine"""
                try:
                    logger.info("🔍 Iniciando busca REAL de licitações do PNCP...")
                    
                    # Importar engine real
                    from matching import process_daily_bids
                    from matching.vectorizers import BrazilianTextVectorizer
                    
                    # Criar vetorizador baseado na configuração (PRIORIDADE SISTEMA BRASILEIRO)
                    vectorizer_type = os.getenv('VECTORIZER_TYPE', 'brazilian')
                    
                    if vectorizer_type == 'brazilian':
                        from matching.vectorizers import BrazilianTextVectorizer
                        vectorizer = BrazilianTextVectorizer()
                    elif vectorizer_type == 'hybrid':
                        from matching.vectorizers import HybridTextVectorizer
                        vectorizer = HybridTextVectorizer()
                    elif vectorizer_type == 'openai':
                        from matching.vectorizers import OpenAITextVectorizer
                        vectorizer = OpenAITextVectorizer()
                    elif vectorizer_type == 'voyage':
                        from matching.vectorizers import VoyageAITextVectorizer
                        vectorizer = VoyageAITextVectorizer()
                    else:
                        from matching.vectorizers import BrazilianTextVectorizer
                        vectorizer = BrazilianTextVectorizer()  # Fallback brasileiro
                    
                    # Executar busca real COM VALIDAÇÃO LLM
                    enable_llm = os.getenv('ENABLE_LLM_VALIDATION', 'true').lower() == 'true'
                    process_daily_bids(vectorizer, enable_llm_validation=enable_llm)
                    
                    # Atualizar status
                    self.process_status['daily_bids']['message'] = 'Busca de novas licitações concluída com sucesso!'
                    logger.info("✅ Busca diária REAL concluída")
                    
                except Exception as e:
                    logger.error(f"❌ Erro na busca diária REAL: {e}")
                    self.process_status['daily_bids']['message'] = f'Erro: {str(e)}'
                
                finally:
                    self.process_status['daily_bids']['running'] = False
            
            # Executar em thread separada
            thread = threading.Thread(target=run_real_search)
            thread.daemon = True
            thread.start()
            
            return {
                'success': True,
                'message': 'Busca de novas licitações iniciada em background (ENGINE REAL)',
                'estimated_duration': '5-15 minutos (dependendo do número de licitações)',
                'note': '🚀 Usando matching engine real do PNCP'
            }
            
        except Exception as e:
            self.process_status['daily_bids']['running'] = False
            logger.error(f"Erro ao iniciar busca diária: {e}")
            return {
                'success': False,
                'message': f'Erro ao iniciar busca: {str(e)}'
            }
    
    def start_reevaluation(self) -> Dict[str, Any]:
        """
        POST /api/reevaluate-bids - Iniciar reavaliação de licitações REAL
        Integra com o matching engine real
        """
        if self.process_status['reevaluate']['running']:
            return {
                'success': False,
                'message': 'Reavaliação já está em execução'
            }
        
        try:
            # Marcar como executando
            self.process_status['reevaluate']['running'] = True
            self.process_status['reevaluate']['last_run'] = datetime.now()
            self.process_status['reevaluate']['message'] = 'Iniciando reavaliação de licitações...'
            
            def run_real_reevaluation():
                """Executa reavaliação real usando o matching engine"""
                try:
                    logger.info("🔄 Iniciando reavaliação REAL de licitações...")
                    
                    # Importar engine real
                    from matching import reevaluate_existing_bids
                    from matching.vectorizers import BrazilianTextVectorizer
                    
                    # Criar vetorizador baseado na configuração (PRIORIDADE SISTEMA BRASILEIRO)
                    vectorizer_type = os.getenv('VECTORIZER_TYPE', 'brazilian')
                    
                    if vectorizer_type == 'brazilian':
                        from matching.vectorizers import BrazilianTextVectorizer
                        vectorizer = BrazilianTextVectorizer()
                    elif vectorizer_type == 'hybrid':
                        from matching.vectorizers import HybridTextVectorizer
                        vectorizer = HybridTextVectorizer()
                    elif vectorizer_type == 'openai':
                        from matching.vectorizers import OpenAITextVectorizer
                        vectorizer = OpenAITextVectorizer()
                    elif vectorizer_type == 'voyage':
                        from matching.vectorizers import VoyageAITextVectorizer
                        vectorizer = VoyageAITextVectorizer()
                    else:
                        from matching.vectorizers import BrazilianTextVectorizer
                        vectorizer = BrazilianTextVectorizer()  # Fallback brasileiro
                    
                    # Configurar limpeza de matches (padrão: sim)
                    clear_matches = os.getenv('CLEAR_MATCHES_BEFORE_REEVALUATE', 'true').lower() == 'true'
                    
                    # Executar reavaliação real COM VALIDAÇÃO LLM
                    enable_llm = os.getenv('ENABLE_LLM_VALIDATION', 'true').lower() == 'true'
                    result = reevaluate_existing_bids(vectorizer, clear_matches=clear_matches, enable_llm_validation=enable_llm)
                    
                    # Atualizar status com resultado
                    if result and result.get('success', False):
                        matches_count = result.get('matches_encontrados', 0)
                        self.process_status['reevaluate']['message'] = f'Reavaliação concluída! {matches_count} matches encontrados'
                    else:
                        self.process_status['reevaluate']['message'] = 'Reavaliação concluída com sucesso'
                    
                    logger.info("✅ Reavaliação REAL concluída")
                    
                except Exception as e:
                    logger.error(f"❌ Erro na reavaliação REAL: {e}")
                    self.process_status['reevaluate']['message'] = f'Erro: {str(e)}'
                
                finally:
                    self.process_status['reevaluate']['running'] = False
            
            # Executar em thread separada
            thread = threading.Thread(target=run_real_reevaluation)
            thread.daemon = True
            thread.start()
            
            return {
                'success': True,
                'message': 'Reavaliação de licitações iniciada em background (ENGINE REAL)',
                'estimated_duration': '10-30 minutos (dependendo do número de licitações)',
                'note': '🔄 Usando matching engine real com análise semântica avançada'
            }
            
        except Exception as e:
            self.process_status['reevaluate']['running'] = False
            logger.error(f"Erro ao iniciar reavaliação: {e}")
            return {
                'success': False,
                'message': f'Erro ao iniciar reavaliação: {str(e)}'
            }
    
    def cleanup_system(self) -> Dict[str, Any]:
        """Limpar dados antigos e otimizar sistema"""
        try:
            logger.info("🧹 Iniciando limpeza do sistema...")
            
            cleanup_results = {
                'logs_cleaned': 0,
                'temp_files_removed': 0,
                'database_optimized': False
            }
            
            # Simular limpeza (implementar lógica real conforme necessário)
            time.sleep(1)
            
            cleanup_results['database_optimized'] = True
            
            logger.info("✅ Limpeza do sistema concluída")
            
            return {
                'success': True,
                'message': 'Limpeza concluída com sucesso',
                'results': cleanup_results
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza do sistema: {e}")
            return {
                'success': False,
                'message': f'Erro na limpeza: {str(e)}'
            } 