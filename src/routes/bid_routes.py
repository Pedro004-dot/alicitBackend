"""
Rotas para operações com licitações
"""
from flask import Blueprint
from controllers.bid_controller import BidController

# Criar blueprint para licitações
bid_routes = Blueprint('bids', __name__, url_prefix='/api/bids')

# Instanciar controller
controller = BidController()

# ====== ROTAS UTILIZADAS PELO FRONTEND ======

@bid_routes.route('/', methods=['GET'], strict_slashes=False)
def get_bids():
    """
    GET /api/bids - Listar licitações com paginação
    
    DESCRIÇÃO:
    - Lista todas as licitações cadastradas no sistema
    - Usado pelo frontend para popular a tabela principal
    - Suporte a paginação e filtros básicos
    
    PARÂMETROS (Query):
    - page: Número da página (opcional)
    - limit: Itens por página (opcional)
    - status: Filtro por status (opcional)
    
    RETORNA:
    - Array de licitações com dados básicos
    - Metadados de paginação (total, páginas)
    """
    return controller.get_all_bids()

@bid_routes.route('/detail', methods=['GET'])
def get_bid_detail():
    """
    GET /api/bids/detail?pncp_id=<id> - Obter detalhes de licitação específica
    
    DESCRIÇÃO:
    - Retorna informações completas de uma licitação específica
    - Usado pelo frontend no modal de detalhes
    - Inclui descrição, valores, prazos e documentos
    
    PARÂMETROS (Query):
    - pncp_id: ID único da licitação no PNCP (obrigatório)
    
    RETORNA:
    - Dados completos da licitação
    - Informações do órgão e modalidade
    """
    return controller.get_bid_detail_by_query()

@bid_routes.route('/items', methods=['GET', 'POST'])
def get_bid_items():
    """
    GET /api/bids/items?pncp_id=<id> - Buscar itens de licitações (somente consulta)
    POST /api/bids/items?pncp_id=<id> - Buscar itens e garantir que a licitação e seus itens sejam salvos no banco.
    
    DESCRIÇÃO:
    - Lista todos os itens de uma licitação específica.
    - O método POST recebe o objeto da licitação no corpo para garantir que os dados mais atualizados (do frontend)
      sejam usados para criar ou atualizar a licitação no banco antes de buscar e salvar os itens.
    - O método GET apenas consulta os itens sem garantir o salvamento.
    
    PARÂMETROS (Query):
    - pncp_id: ID único da licitação no PNCP (obrigatório para GET e POST)
    
    CORPO (Body JSON para POST):
    - Objeto completo da licitação, como visto no frontend.
    
    RETORNA:
    - Array de itens com detalhes completos.
    - No caso de POST, a operação de salvamento ocorre no backend.
    """
    return controller.get_bid_items_by_query()

@bid_routes.route('/items-multi', methods=['POST'])
def buscar_itens_multi_provider():
    """
    POST /api/bids/items-multi
    Recebe uma lista de licitações (ou external_ids) e retorna os itens de cada uma, multi-provider.
    Corpo: { licitacoes: [ ... ] }
    Retorna: { success: bool, data: [ {licitacao, itens} ], message: str }
    """
    from controllers.bid_controller import BidController
    controller = BidController()
    return controller.buscar_itens_multi_provider()

@bid_routes.route('/documents', methods=['GET'])
def get_bid_documents():
    """
    GET /api/bids/documents?licitacao_id=<id> - Buscar documentos de uma licitação no Supabase Storage
    
    DESCRIÇÃO:
    - Lista todos os documentos armazenados no Supabase Storage para uma licitação específica
    - Usado pelo frontend para visualizar documentos na página de análise
    - Inclui nome, URL pública, tipo e metadados dos arquivos
    
    PARÂMETROS (Query):
    - licitacao_id: ID da licitação (obrigatório)
    
    RETORNA:
    - Array de documentos com URLs públicas para visualização
    - Metadados como tamanho, tipo e datas de criação/atualização
    """
    return controller.get_bid_documents()

@bid_routes.route('/test-storage', methods=['GET'])
def test_supabase_connection():
    """
    GET /api/bids/test-storage - Testar conectividade com Supabase Storage
    
    DESCRIÇÃO:
    - Testa a conectividade com o Supabase Storage
    - Lista buckets disponíveis e verifica se o bucket alvo existe
    - Usado para debug e verificação de configuração
    
    RETORNA:
    - Status da conectividade
    - Lista de buckets disponíveis
    - Verificação do bucket específico
    """
    return controller.test_supabase_connection()

@bid_routes.route('/recent', methods=['GET'])
def get_recent_bids():
    """
    GET /api/bids/recent - Buscar licitações mais recentes
    
    DESCRIÇÃO:
    - Retorna as licitações mais recentemente cadastradas
    - Usado pelo frontend na página de busca
    - Ordenadas por data de publicação descrescente
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 20)
    
    RETORNA:
    - Array de licitações ordenadas por data
    - Dados básicos para visualização rápida
    """
    return controller.get_recent_bids()

@bid_routes.route('/status/<string:status>', methods=['GET'])
def get_bids_by_status(status):
    """
    GET /api/bids/status/<status> - Buscar licitações por status
    
    DESCRIÇÃO:
    - Filtra licitações por status específico
    - Usado pelo frontend para busca filtrada
    - Status comuns: "aberta", "fechada", "suspensa", etc.
    
    PARÂMETROS:
    - status: Status da licitação (ex: "aberta", "fechada")
    
    RETORNA:
    - Array de licitações com o status especificado
    - Ordenadas por relevância e data
    """
    return controller.get_bids_by_status(status)

@bid_routes.route('/active', methods=['GET'])
def get_active_bids():
    """
    GET /api/bids/active - Buscar licitações ativas (ainda abertas para propostas)
    
    DESCRIÇÃO:
    - Filtra licitações onde data_encerramento_proposta > data atual
    - Usado pelo frontend na página Home para mostrar oportunidades ativas
    - Permite filtro por data mínima de encerramento
    
    PARÂMETROS (Query):
    - after: Data mínima para filtro (formato ISO: YYYY-MM-DD) (opcional)
    - limit: Quantidade máxima de registros (opcional, padrão: 100)
    
    RETORNA:
    - Array de licitações ainda abertas para propostas
    - Total de licitações ativas
    - Ordenadas por data de encerramento mais próxima
    """
    return controller.get_active_bids()

# ====== NOVAS ROTAS PARA PREPARAÇÃO AUTOMÁTICA DE ANÁLISE ======

@bid_routes.route('/prepare-analysis', methods=['POST'])
def prepare_analysis():
    """
    POST /api/bids/prepare-analysis - Iniciar preparação automática de análise
    
    DESCRIÇÃO:
    - Inicia o processo de download e processamento de documentos
    - Utiliza o UnifiedDocumentProcessor para baixar e extrair texto
    - Usado pelo frontend para preparação automática do ambiente
    
    PARÂMETROS (Body JSON):
    - licitacao_id: ID UUID da licitação (obrigatório)
    - pncp_id: ID do PNCP da licitação (obrigatório)
    
    RETORNA:
    - Status de início do processamento
    - ID do processo para monitoramento
    """
    return controller.prepare_analysis()

@bid_routes.route('/preparation-status', methods=['GET'])
def get_preparation_status():
    """
    GET /api/bids/preparation-status?licitacao_id=<id> - Status da preparação automática
    
    DESCRIÇÃO:
    - Verifica o status do processamento de documentos
    - Usado pelo frontend para polling durante preparação
    - Retorna progresso e etapa atual do processamento
    
    PARÂMETROS (Query):
    - licitacao_id: ID da licitação (obrigatório)
    
    RETORNA:
    - Status do processamento (preparing/completed/error)
    - Informações de progresso e etapa atual
    - Lista de documentos processados
    """
    return controller.get_preparation_status()

# ====== NOVAS ROTAS DE OPORTUNIDADES DE NEGÓCIO ======

@bid_routes.route('/srp-opportunities', methods=['GET'])
def get_srp_opportunities():
    """
    GET /api/bids/srp-opportunities - Oportunidades SRP (Sistema de Registro de Preços)
    
    DESCRIÇÃO:
    - Busca licitações marcadas como SRP (srp = true)
    - Oportunidades de contratos válidos por até 1 ano
    - Alto valor estratégico para fornecedores
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 50)
    
    RETORNA:
    - Array de licitações SRP com alertas estratégicos
    - Campos calculados: dias_até_deadline, urgency_level
    """
    return controller.get_srp_opportunities()

@bid_routes.route('/active-proposals', methods=['GET'])
def get_active_proposals():
    """
    GET /api/bids/active-proposals - Propostas com prazos ATIVOS (timing crítico)
    
    DESCRIÇÃO:
    - Licitações onde data_encerramento_proposta > agora
    - Foco em urgência: <24h (🚨), <3 dias (⚠️)
    - Ação imediata necessária para participação
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 50)
    
    RETORNA:
    - Array de licitações abertas ordenadas por urgência
    - Alertas de timing crítico e contagem regressiva
    """
    return controller.get_active_proposals()

@bid_routes.route('/materials-opportunities', methods=['GET'])
def get_materials_opportunities():
    """
    GET /api/bids/materials-opportunities - Oportunidades de MATERIAIS/PRODUTOS
    
    DESCRIÇÃO:
    - Itens classificados como 'M' (Material) na API PNCP
    - Segmentação para empresas que fornecem produtos físicos
    - Exclusão de serviços (material_ou_servico = 'M')
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 100)
    
    RETORNA:
    - Array de itens de materiais com dados da licitação pai
    - Valores unitários e informações de fornecimento
    """
    return controller.get_materials_opportunities()

@bid_routes.route('/services-opportunities', methods=['GET'])
def get_services_opportunities():
    """
    GET /api/bids/services-opportunities - Oportunidades de SERVIÇOS
    
    DESCRIÇÃO:
    - Itens classificados como 'S' (Serviço) na API PNCP
    - Segmentação para empresas prestadoras de serviços
    - Exclusão de materiais (material_ou_servico = 'S')
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 100)
    
    RETORNA:
    - Array de itens de serviços com dados da licitação pai
    - Especificações técnicas e valores de prestação
    """
    return controller.get_services_opportunities()

@bid_routes.route('/me-epp-opportunities', methods=['GET'])
def get_me_epp_opportunities():
    """
    GET /api/bids/me-epp-opportunities - Oportunidades EXCLUSIVAS ME/EPP
    
    DESCRIÇÃO:
    - Itens com beneficio_micro_epp = true
    - Reservados para Micro e Pequenas Empresas
    - Competição reduzida, alta taxa de sucesso
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 50)
    
    RETORNA:
    - Array de itens exclusivos ME/EPP
    - Dados estratégicos para pequenas empresas
    """
    return controller.get_me_epp_opportunities()

@bid_routes.route('/search-by-ncm/<string:ncm_code>', methods=['GET'])
def search_by_ncm_code(ncm_code):
    """
    GET /api/bids/search-by-ncm/<ncm_code> - Busca por código NCM específico
    
    DESCRIÇÃO:
    - Busca ultra-precisa por código NCM/NBS
    - Ideal para empresas especializadas em produtos específicos
    - Máxima relevância para fornecedores de nicho
    
    PARÂMETROS:
    - ncm_code: Código NCM exato (ex: "84714100")
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 50)
    
    RETORNA:
    - Array de itens com NCM exato
    - Oportunidades ultra-específicas para especialistas
    """
    return controller.search_by_ncm_code(ncm_code)

@bid_routes.route('/disputa-mode/<int:mode_id>', methods=['GET'])
def get_bids_by_disputa_mode(mode_id):
    """
    GET /api/bids/disputa-mode/<mode_id> - Licitações por modo de disputa
    
    DESCRIÇÃO:
    - Filtra por modo_disputa_id da API PNCP
    - 1=Aberto, 2=Fechado, 3=Aberto-Fechado
    - Estratégia diferenciada por tipo de disputa
    
    PARÂMETROS:
    - mode_id: ID do modo de disputa (1, 2, ou 3)
    
    PARÂMETROS (Query):
    - limit: Quantidade máxima de registros (opcional, padrão: 50)
    
    RETORNA:
    - Array de licitações do modo específico
    - Informações sobre estratégia de participação
    """
    return controller.get_bids_by_disputa_mode(mode_id)

@bid_routes.route('/enhanced-statistics', methods=['GET'])
def get_enhanced_statistics():
    """
    GET /api/bids/enhanced-statistics - Estatísticas com insights de negócio
    
    DESCRIÇÃO:
    - Utiliza todos os novos campos das APIs PNCP
    - Análises de SRP, propostas ativas, distribuição ME/EPP
    - Dashboard executivo com KPIs estratégicos
    
    RETORNA:
    - Estatísticas agregadas por tipo de oportunidade
    - Insights automatizados para tomada de decisão
    - Análises de tendências e oportunidades de mercado
    """
    return controller.get_enhanced_statistics()

# ====== ROTAS ADMINISTRATIVAS (PARA MANUTENÇÃO) ======

@bid_routes.route('/<pncp_id>', methods=['GET'])
def get_bid_by_pncp_id(pncp_id):
    """
    GET /api/bids/<pncp_id> - Obter licitação específica por PNCP ID
    
    DESCRIÇÃO:
    - Busca uma licitação usando o ID do PNCP como parâmetro de rota
    - Alternativa à rota /detail para casos específicos
    - Usado para integrações diretas com o PNCP
    
    PARÂMETROS:
    - pncp_id: ID único da licitação no PNCP
    
    RETORNA:
    - Dados completos da licitação
    - Mesmo formato da rota /detail
    """
    return controller.get_bid_detail(pncp_id)

@bid_routes.route('/<pncp_id>/items', methods=['GET'])
def get_bid_items_by_pncp_id(pncp_id):
    """
    GET /api/bids/<pncp_id>/items - Buscar itens por PNCP ID (DEPRECIADO - usar /items?pncp_id= no lugar)
    
    DESCRIÇÃO:
    - Legacy: Buscar itens de licitação específica usando path parameter
    - AVISO: Esta rota está deprecated, use /api/bids/items?pncp_id= no lugar
    - Mantida para compatibilidade com versões antigas do frontend
    
    PARÂMETROS:
    - pncp_id: ID único da licitação no PNCP
    
    RETORNA:
    - Array de itens com detalhes completos
    """
    return controller.get_bid_items_by_pncp_id(pncp_id)

@bid_routes.route('/<provider>/<external_id>/items', methods=['GET'])
def get_bid_items_by_provider(provider, external_id):
    """
    GET /api/bids/<provider>/<external_id>/items - Buscar itens por provider e ID externo
    
    DESCRIÇÃO:
    - Busca itens de licitação para qualquer provider (PNCP, ComprasNet, etc)
    - Suporta diferentes sources de dados de licitação
    - Usado pelo frontend para buscar itens de diferentes provedores
    
    PARÂMETROS:
    - provider: Nome do provedor (pncp, comprasnet)
    - external_id: ID externo da licitação no provedor específico
    
    RETORNA:
    - Array de itens com detalhes completos
    - Erro 404 se provider não suportado ou licitação não encontrada
    """
    return controller.get_bid_items_by_provider(provider, external_id)

@bid_routes.route('/detailed', methods=['GET'])
def get_detailed_bids():
    """
    GET /api/bids/detailed - Obter licitações com informações detalhadas
    
    DESCRIÇÃO:
    - Lista licitações com informações completas
    - Inclui dados de órgão, modalidade e itens resumidos
    - Usado para relatórios e análises administrativas
    
    PARÂMETROS (Query):
    - page: Número da página (opcional)
    - limit: Itens por página (opcional)
    
    RETORNA:
    - Array de licitações com dados expandidos
    - Informações agregadas dos itens
    """
    return controller.get_detailed_bids()

@bid_routes.route('/uf/<string:uf>', methods=['GET'])
def get_bids_by_uf(uf):
    """
    GET /api/bids/uf/<uf> - Buscar licitações por UF
    
    DESCRIÇÃO:
    - Filtra licitações por Unidade Federativa (estado)
    - Usado para análises regionais e relatórios
    - UF deve seguir padrão de 2 letras (ex: SP, RJ, MG)
    
    PARÂMETROS:
    - uf: Sigla da Unidade Federativa (2 letras)
    
    RETORNA:
    - Array de licitações do estado especificado
    - Ordenadas por data de publicação
    """
    return controller.get_bids_by_uf(uf)

@bid_routes.route('/statistics', methods=['GET'])
def get_bid_statistics():
    """
    GET /api/bids/statistics - Obter estatísticas das licitações
    
    DESCRIÇÃO:
    - Gera estatísticas agregadas das licitações
    - Inclui totais por status, valores médios, distribuição por órgão
    - Usado para dashboards administrativos e relatórios
    
    RETORNA:
    - Dados estatísticos consolidados
    - Métricas de desempenho do sistema
    """
    return controller.get_bid_statistics()

@bid_routes.route('/cleanup-preparation', methods=['DELETE'])
def cleanup_preparation():
    """
    DELETE /api/bids/cleanup-preparation?licitacao_id=<id> - Limpar preparação falhada
    
    DESCRIÇÃO:
    - Remove arquivos temporários e dados de processamento incompleto
    - Permite nova tentativa de preparação automática
    - Usado quando há erro no processamento de documentos
    
    PARÂMETROS (Query String):
    - licitacao_id: ID UUID da licitação (obrigatório)
    
    RETORNA:
    - Status da limpeza e arquivos removidos
    """
    return controller.cleanup_preparation()

 