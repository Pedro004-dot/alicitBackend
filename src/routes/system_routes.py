"""
Rotas para operações de sistema
"""
from flask import Blueprint, request, jsonify
from controllers.system_controller import SystemController
import logging
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

# Criar blueprint para sistema
system_routes = Blueprint('system', __name__)

# Instanciar controller
controller = SystemController()

# ====== ROTAS DE SISTEMA ======

@system_routes.route('/api/health', methods=['GET'])
def health_check():
    """
    GET /api/health - Health check do sistema
    
    DESCRIÇÃO:
    - Verificação geral de saúde de toda a aplicação
    - Testa conectividade com banco de dados, APIs externas
    - Usado para monitoramento automático e alertas
    
    RETORNA:
    - Status geral do sistema (healthy/degraded/unhealthy)
    - Detalhes de cada componente (database, supabase, etc.)
    - Timestamp da verificação e tempo de resposta
    - Versão da aplicação e informações do ambiente
    """
    return controller.health_check()

@system_routes.route('/api/status', methods=['GET'])
def get_system_status():
    """
    GET /api/status - Status geral do sistema
    
    DESCRIÇÃO:
    - Informações detalhadas sobre o estado atual do sistema
    - Inclui estatísticas de uso, performance e recursos
    - Usado para dashboards administrativos
    
    RETORNA:
    - Estatísticas de uso da aplicação
    - Informações sobre processos em execução
    - Métricas de performance e memória
    - Status dos serviços dependentes
    """
    return controller.get_system_status()

@system_routes.route('/api/status/daily-bids', methods=['GET'])
def get_daily_bids_status():
    """
    GET /api/status/daily-bids - Status da busca diária
    
    DESCRIÇÃO:
    - Monitora o processo automático de busca diária de licitações
    - Usado pelo frontend para mostrar status em tempo real
    - Inclui informações sobre última execução e próxima
    
    RETORNA:
    - Status atual do processo (running/idle/error)
    - Timestamp da última execução bem-sucedida
    - Quantidade de licitações encontradas na última busca
    - Próxima execução programada
    """
    return controller.get_daily_bids_status()

@system_routes.route('/api/status/reevaluate', methods=['GET'])
def get_reevaluate_status():
    """
    GET /api/status/reevaluate - Status da reavaliação
    
    DESCRIÇÃO:
    - Monitora o processo de reavaliação de matches existentes
    - Usado pelo frontend para acompanhar progresso em tempo real
    - Mostra estatísticas de reprocessamento de dados
    
    RETORNA:
    - Status atual da reavaliação (running/idle/error)
    - Progresso atual (% concluído, registros processados)
    - Timestamp de início e estimativa de conclusão
    - Estatísticas de matches atualizados
    """
    return controller.get_reevaluate_status()

@system_routes.route('/api/config/options', methods=['GET'])
def get_config_options():
    """
    GET /api/config/options - Opções de configuração do sistema
    
    DESCRIÇÃO:
    - Lista todas as configurações disponíveis do sistema
    - Usado para interface administrativa de configuração
    - Inclui valores atuais e opções disponíveis
    
    RETORNA:
    - Configurações de busca automática (frequência, filtros)
    - Parâmetros do algoritmo de matching
    - Configurações de notificações e alertas
    - Limites de API e timeouts
    """
    return controller.get_config_options()

@system_routes.route('/api/search-new-bids', methods=['POST'], strict_slashes=False)
def search_new_bids():
    """
    POST /api/search-new-bids - Iniciar busca de novas licitações
    
    DESCRIÇÃO:
    - Inicia manualmente o processo de busca de novas licitações
    - Usado pelo frontend no botão "Buscar Novas Licitações"
    - Processo assíncrono que roda em background
    
    PARÂMETROS (Body JSON):
    - force: Forçar nova busca mesmo se já executada hoje
    - filters: Filtros específicos para a busca (opcional)
    - limit: Limite de registros a buscar (opcional)
    
    RETORNA:
    - Confirmação de início do processo
    - ID do processo para acompanhamento
    - Estimativa de tempo de execução
    """
    return controller.search_new_bids()

# 🔥 NOVA ROTA: Busca semanal com validação LLM QWEN
@system_routes.route('/api/search-weekly-bids', methods=['POST', 'GET'], strict_slashes=False)
def search_weekly_bids():
    """
    POST/GET /api/search-weekly-bids - Buscar licitações da última semana com QWEN LLM
    
    DESCRIÇÃO:
    - Busca licitações dos últimos 7 dias no PNCP
    - Usa modelo QWEN 2.5:7B para validação de matches
    - APENAS matches aprovados pelo LLM são salvos no Supabase
    - Processo otimizado com cache Redis local
    
    PARÂMETROS (Body JSON - todos opcionais):
    {
        "vectorizer": "brazilian",     // tipo de vetorizador (brazilian, hybrid, openai)
        "clear_matches": true,         // limpar matches existentes antes
        "enable_llm": true,           // validação LLM (padrão: true)
        "max_pages": 10               // limite de páginas por UF
    }
    
    RETORNA:
    {
        "success": true,
        "process_id": "weekly_search_20250125_143022",
        "message": "Busca semanal iniciada com validação LLM QWEN",
        "config": {
            "period": "últimos 7 dias",
            "llm_model": "qwen2.5:7b",
            "vectorizer": "brazilian",
            "estimated_duration": "15-30 minutos"
        }
    }
    """
    try:
        # Lidar com GET e POST
        if request.method == 'GET':
            data = {
                'vectorizer': request.args.get('vectorizer', 'brazilian'),
                'clear_matches': request.args.get('clear_matches', 'false').lower() == 'true',
                'enable_llm': request.args.get('enable_llm', 'true').lower() == 'true',
                'max_pages': int(request.args.get('max_pages', '10'))
            }
        else:
            # POST - Tentar múltiplas formas de obter dados da requisição
            data = {}
            
            # Primeira tentativa: JSON normal
            try:
                data = request.get_json() or {}
            except Exception:
                # Segunda tentativa: forçar parsing JSON
                try:
                    data = request.get_json(force=True) or {}
                except Exception:
                    # Terceira tentativa: dados do form
                    try:
                        if request.form:
                            data = request.form.to_dict()
                        elif request.data:
                            import json
                            data = json.loads(request.data.decode('utf-8'))
                        else:
                            data = {}
                    except Exception:
                        # Usar dados padrão se tudo falhar
                        data = {}
        
        logger.info(f"📡 {request.method} - Dados recebidos na requisição: {data}")
        
        vectorizer_type = data.get('vectorizer', 'brazilian')
        clear_matches = data.get('clear_matches', False)
        enable_llm = data.get('enable_llm', True)
        max_pages = data.get('max_pages', 10)
        
        # Validar vectorizer_type
        valid_vectorizers = ['brazilian', 'hybrid', 'openai', 'voyage', 'mock']
        if vectorizer_type not in valid_vectorizers:
            return jsonify({
                'success': False,
                'error': f'vectorizer deve ser um de: {valid_vectorizers}'
            }), 400
        
        # Gerar ID único do processo
        from datetime import datetime
        process_id = f"weekly_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Executar em background
        def run_weekly_search():
            try:
                logger.info(f"🚀 Iniciando busca semanal com processo ID: {process_id}")
                
                # Importar e configurar vectorizer
                if vectorizer_type == "brazilian":
                    from matching.vectorizers import BrazilianTextVectorizer
                    vectorizer = BrazilianTextVectorizer()
                elif vectorizer_type == "hybrid":
                    from matching.vectorizers import HybridTextVectorizer
                    vectorizer = HybridTextVectorizer()
                elif vectorizer_type == "openai":
                    from matching.vectorizers import OpenAITextVectorizer
                    vectorizer = OpenAITextVectorizer()
                elif vectorizer_type == "voyage":
                    from matching.vectorizers import VoyageAITextVectorizer
                    vectorizer = VoyageAITextVectorizer()
                else:  # mock
                    from matching.vectorizers import MockTextVectorizer
                    vectorizer = MockTextVectorizer()
                
                # Atualizar limite de páginas se especificado
                if max_pages != 10:
                    from matching.pncp_api import PNCP_MAX_PAGES
                    import matching.pncp_api as pncp_api
                    pncp_api.PNCP_MAX_PAGES = max_pages
                    logger.info(f"📄 Limite de páginas ajustado para: {max_pages}")
                
                # Executar busca semanal
                from matching.matching_engine import process_daily_bids
                
                logger.info(f"🔍 Iniciando busca de licitações da última semana...")
                logger.info(f"🤖 Validação LLM: {'ATIVADA (QWEN 2.5:7B)' if enable_llm else 'DESATIVADA'}")
                logger.info(f"🔧 Vectorizador: {vectorizer_type}")
                
                # Executar o processo (já modificado para buscar última semana)
                result = process_daily_bids(vectorizer, enable_llm_validation=enable_llm)
                
                logger.info(f"✅ Busca semanal concluída para processo {process_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro na busca semanal {process_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Iniciar thread
        thread = threading.Thread(target=run_weekly_search)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'process_id': process_id,
            'message': 'Busca semanal iniciada com validação LLM QWEN',
            'config': {
                'period': 'últimos 7 dias',
                'llm_model': 'qwen2.5:7b' if enable_llm else 'desativado',
                'vectorizer': vectorizer_type,
                'clear_matches': clear_matches,
                'max_pages_per_uf': max_pages,
                'estimated_duration': '15-30 minutos',
                'cache': 'Redis local ativado'
            },
            'monitoring': {
                'status_endpoint': f'/api/status/weekly-search/{process_id}',
                'logs': 'Verifique logs do servidor para progresso detalhado'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar busca semanal: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@system_routes.route('/api/reevaluate-bids', methods=['POST'], strict_slashes=False)
def reevaluate_bids():
    """
    POST /api/reevaluate-bids - Reavaliação de licitações existentes
    
    DESCRIÇÃO:
    - Inicia processo de reavaliação de matches existentes
    - Usado pelo frontend no botão "Reavaliar Matches"
    - Recalcula scores de compatibilidade com novos critérios
    
    PARÂMETROS (Body JSON):
    - company_ids: IDs específicos de empresas (opcional)
    - bid_ids: IDs específicos de licitações (opcional)
    - recalculate_all: Reprocessar todos os matches
    
    RETORNA:
    - Confirmação de início da reavaliação
    - ID do processo para monitoramento
    - Quantidade estimada de registros a processar
    """
    return controller.reevaluate_bids()

# 🧪 NOVA ROTA: Reprocessar licitações existentes para testar o fix
@system_routes.route('/api/reprocess-existing-bids', methods=['POST', 'GET'], strict_slashes=False)
def reprocess_existing_bids():
    """
    POST/GET /api/reprocess-existing-bids - Reprocessar licitações existentes com QWEN LLM
    
    DESCRIÇÃO:
    - Reprocessa licitações já existentes no banco com validação LLM
    - Usado para testar correções no sistema de matching
    - Limpa matches anteriores e reprocessa com as novas regras
    
    PARÂMETROS (opcional):
    - clear_matches: bool (default: true) - Limpar matches anteriores
    - enable_llm: bool (default: true) - Usar validação LLM QWEN
    - vectorizer: str (default: brazilian) - Tipo de vetorizador
    
    RETORNA:
    - process_id: ID único do processo para monitoramento
    - success: true se iniciado com sucesso
    - config: configurações utilizadas
    """
    try:
        # Lidar com GET e POST
        if request.method == 'GET':
            data = {
                'vectorizer': request.args.get('vectorizer', 'brazilian'),
                'clear_matches': request.args.get('clear_matches', 'true').lower() == 'true',
                'enable_llm': request.args.get('enable_llm', 'true').lower() == 'true'
            }
        else:
            # POST - Tentar múltiplas formas de obter dados da requisição
            data = {}
            
            # Primeira tentativa: JSON normal
            try:
                data = request.get_json() or {}
            except Exception:
                # Segunda tentativa: forçar parsing JSON
                try:
                    data = request.get_json(force=True) or {}
                except Exception:
                    # Terceira tentativa: dados do form
                    try:
                        if request.form:
                            data = request.form.to_dict()
                        elif request.data:
                            import json
                            data = json.loads(request.data.decode('utf-8'))
                        else:
                            data = {}
                    except Exception:
                        # Usar dados padrão se tudo falhar
                        data = {}
        
        logger.info(f"📡 {request.method} - Dados recebidos na requisição: {data}")
        
        vectorizer_type = data.get('vectorizer', 'brazilian')
        clear_matches = data.get('clear_matches', True)
        enable_llm = data.get('enable_llm', True)
        
        # Gerar ID único para o processo
        process_id = f"reprocess_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Configurar vectorizador (usar imports corretos)
        if vectorizer_type == 'brazilian':
            from matching.vectorizers import BrazilianTextVectorizer
            vectorizer = BrazilianTextVectorizer()
        elif vectorizer_type == 'sentence_transformer':
            from services.sentence_transformer_service import SentenceTransformerService
            vectorizer = SentenceTransformerService()
        else:
            # Default para brazilian
            from matching.vectorizers import BrazilianTextVectorizer
            vectorizer = BrazilianTextVectorizer()
        
        # Log de início
        logger.info(f"🔄 Iniciando reprocessamento de licitações existentes...")
        logger.info(f"🤖 Validação LLM: {'ATIVADA (QWEN 2.5:7B)' if enable_llm else 'DESATIVADA'}")
        logger.info(f"🔧 Vectorizador: {vectorizer_type}")
        
        # Executar reprocessamento em background
        def background_reprocess():
            try:
                from matching.matching_engine import reevaluate_existing_bids
                reevaluate_existing_bids(
                    vectorizer=vectorizer,
                    clear_matches=clear_matches,
                    enable_llm_validation=enable_llm
                )
                logger.info(f"✅ Reprocessamento concluído para processo {process_id}")
            except Exception as e:
                logger.error(f"❌ Erro no reprocessamento {process_id}: {e}")
        
        # Iniciar processo em background
        thread = threading.Thread(target=background_reprocess)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Reprocessamento iniciado com validação LLM QWEN',
            'process_id': process_id,
            'config': {
                'vectorizer': vectorizer_type,
                'clear_matches': clear_matches,
                'llm_model': 'qwen2.5:7b',
                'cache': 'Redis local ativado'
            },
            'monitoring': {
                'logs': 'Verifique logs do servidor para progresso detalhado',
                'status_endpoint': f'/api/status/reprocess/{process_id}'
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar reprocessamento: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Erro ao iniciar reprocessamento'
        }), 500

@system_routes.route('/api/reeval-by-date-range', methods=['POST'])
def reeval_by_date_range():
    """
    🗓️ REAVALIAÇÃO POR INTERVALO DE DATAS
    
    Busca licitações em um intervalo específico de datas e executa matching
    com validação LLM QWEN 2.5:7B
    
    Body JSON:
    {
        "data_inicio": "2025-06-17",  // Formato: YYYY-MM-DD
        "data_fim": "2025-06-24",     // Formato: YYYY-MM-DD
        "clear_matches": true,        // Opcional: limpar matches existentes
        "enable_llm": true,           // Opcional: ativar validação LLM
        "limit": 200                  // Opcional: máximo de licitações
    }
    """
    try:
        data = request.get_json() or {}
        
        # Validar parâmetros obrigatórios
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        
        if not data_inicio or not data_fim:
            return jsonify({
                "success": False,
                "error": "Parâmetros obrigatórios: data_inicio e data_fim (formato: YYYY-MM-DD)"
            }), 400
        
        # Parâmetros opcionais
        clear_matches = data.get('clear_matches', True)
        enable_llm = data.get('enable_llm', True)
        limit = data.get('limit', 200)
        
        # Converter para boolean de forma segura
        if isinstance(clear_matches, str):
            clear_matches = clear_matches.lower() in ['true', '1', 'yes']
        if isinstance(enable_llm, str):
            enable_llm = enable_llm.lower() in ['true', '1', 'yes']
            
        logger.info("📅 INICIANDO REAVALIAÇÃO POR INTERVALO DE DATAS")
        logger.info(f"   📊 Intervalo: {data_inicio} até {data_fim}")
        logger.info(f"   📋 Parâmetros: clear_matches={clear_matches}, enable_llm={enable_llm}, limit={limit}")
        
        # Start background task
        thread = threading.Thread(
            target=run_date_range_reeval_matching,
            args=(data_inicio, data_fim, clear_matches, enable_llm, limit),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            "success": True,
            "message": f"Reavaliação de licitações de {data_inicio} até {data_fim} iniciada em background",
            "details": {
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "limit": limit,
                "llm_enabled": enable_llm,
                "clear_matches": clear_matches,
                "model": "QWEN 2.5:7B"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro na reavaliação por data: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def run_date_range_reeval_matching(data_inicio: str, data_fim: str, clear_matches: bool = True, enable_llm: bool = True, limit: int = 200):
    """
    📅 EXECUTAR REAVALIAÇÃO POR INTERVALO DE DATAS
    
    Busca licitações em um intervalo específico e executa matching
    """
    try:
        # Usar conexão direta com PostgreSQL em vez do Supabase API
        from config.database import db_manager
        import time
        
        logger.info("🚀 INICIANDO REAVALIAÇÃO POR INTERVALO DE DATAS")
        logger.info(f"   📅 Período: {data_inicio} até {data_fim}")
        logger.info(f"   📊 Limite: {limit} licitações")
        
        # 1. Buscar licitações do intervalo usando conexão direta PostgreSQL
        logger.info("📊 Buscando licitações do período...")
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Query para buscar licitações no intervalo
                query = """
                    SELECT id, pncp_id, objeto_compra, uf, valor_total_estimado, created_at, data_publicacao
                    FROM licitacoes 
                    WHERE DATE(created_at) >= %s 
                      AND DATE(created_at) <= %s
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                
                cursor.execute(query, (data_inicio, data_fim, limit))
                licitacoes_raw = cursor.fetchall()
                
                # Converter para formato de dict
                columns = [desc[0] for desc in cursor.description]
                licitacoes = [dict(zip(columns, row)) for row in licitacoes_raw]
        
        logger.info(f"✅ Encontradas {len(licitacoes)} licitações no período especificado")
        
        if not licitacoes:
            logger.warning(f"⚠️ Nenhuma licitação encontrada entre {data_inicio} e {data_fim}")
            return
        
        # 2. Limpar matches existentes se solicitado
        if clear_matches:
            logger.info("🧹 Limpando matches existentes das licitações do período...")
            licitacao_ids = [lic['id'] for lic in licitacoes]
            
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Deletar matches em lotes
                    for i in range(0, len(licitacao_ids), 50):
                        batch_ids = licitacao_ids[i:i+50]
                        placeholders = ','.join(['%s'] * len(batch_ids))
                        delete_query = f"DELETE FROM matches WHERE licitacao_id IN ({placeholders})"
                        cursor.execute(delete_query, batch_ids)
                        logger.info(f"   🗑️ Limpeza lote {i//50 + 1}: {len(batch_ids)} IDs")
                    
                    conn.commit()
            
            logger.info("✅ Limpeza de matches concluída")
        
        # 3. Executar matching usando sistema existente
        from matching.matching_engine import reevaluate_existing_bids
        from matching.vectorizers import BrazilianTextVectorizer
        
        logger.info("🇧🇷 Configurando vectorizer brasileiro...")
        vectorizer = BrazilianTextVectorizer()
        
        logger.info(f"🎯 Processando {len(licitacoes)} licitações com QWEN 2.5:7B")
        
        # 4. Executar reavaliação
        logger.info("🔄 Iniciando reavaliação com sistema otimizado...")
        tempo_inicio = time.time()
        
        resultado = reevaluate_existing_bids(
            vectorizer=vectorizer,
            clear_matches=False,  # Já limpamos acima
            enable_llm_validation=enable_llm
        )
        
        # 5. Relatório final
        tempo_total = time.time() - tempo_inicio
        
        logger.info(f"\n🎉 REAVALIAÇÃO POR PERÍODO CONCLUÍDA!")
        logger.info("=" * 60)
        logger.info(f"📅 Período: {data_inicio} até {data_fim}")
        
        if resultado:
            estatisticas = resultado.get('estatisticas', {})
            matches_encontrados = resultado.get('matches_encontrados', 0)
            
            logger.info(f"📊 ESTATÍSTICAS FINAIS:")
            logger.info(f"   📋 Licitações processadas: {estatisticas.get('total_processadas', 0)}")
            logger.info(f"   ✅ Total de matches: {matches_encontrados}")
            logger.info(f"   🦙 Matches aprovados por LLM: {estatisticas.get('llm_approved', 0)}")
            logger.info(f"   ❌ Matches rejeitados: {estatisticas.get('llm_rejected', 0)}")
            logger.info(f"   ⏱️  Tempo total: {tempo_total:.1f}s")
        else:
            logger.info(f"📊 Processamento concluído em {tempo_total:.1f}s")
            
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO na reavaliação por período: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Blueprint para exposição
def register_system_routes(app):
    """
    FUNÇÃO: register_system_routes - Registrar rotas de sistema no app Flask
    
    DESCRIÇÃO:
    - Função utilitária para registrar todas as rotas de sistema
    - Inclui logging detalhado dos endpoints registrados
    - Usado durante a inicialização da aplicação
    
    PARÂMETROS:
    - app: Instância do Flask para registrar as rotas
    
    FUNCIONALIDADE:
    - Registra o blueprint system_routes
    - Gera logs informativos sobre os endpoints
    - Confirma sucesso do registro
    """
    app.register_blueprint(system_routes)
    
    # Log dos endpoints registrados
    logger.info("✅ Sistema: 7 endpoints registrados")
    logger.info("  - GET /api/health (health check)")
    logger.info("  - GET /api/status (status geral)")
    logger.info("  - GET /api/status/daily-bids (status busca)")
    logger.info("  - GET /api/status/reevaluate (status reavaliação)")
    logger.info("  - GET /api/config/options (opções config)")
    logger.info("  - POST /api/search-new-bids (buscar licitações)")
    logger.info("  - POST /api/reevaluate-bids (reavaliar licitações)") 