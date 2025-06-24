"""
Rotas essenciais para PNCP (Portal Nacional de Contratações Públicas)
Mantidas apenas as rotas utilizadas pelo sistema
"""
from flask import Blueprint, jsonify
from controllers.pncp_controller import PNCPController

# Criar blueprint para PNCP
pncp_routes = Blueprint('pncp', __name__, url_prefix='/api/pncp')

# Instanciar controller
controller = PNCPController()

# ====== ROTA DE BUSCA AVANÇADA (USADA PELA BUSCA UNIFICADA) ======

@pncp_routes.route('/search/advanced', methods=['POST'])
def search_by_keywords_advanced():
    """
    POST /api/pncp/search/advanced - Busca avançada PNCP (uso interno)
    
    DESCRIÇÃO:
    - Busca na API oficial do PNCP com filtros avançados
    - Usada internamente pela busca unificada (/api/search/unified)
    - Sistema de score de relevância baseado em palavras-chave
    
    NOTA: Os usuários devem usar /api/search/unified em vez desta rota diretamente
    """
    return controller.search_by_keywords_advanced()

# ====== ROTAS DE ITENS DE LICITAÇÃO ======

@pncp_routes.route('/licitacao/<path:pncp_id>/itens', methods=['GET'])
def get_licitacao_items(pncp_id):
    """
    GET /api/pncp/licitacao/{pncp_id}/itens - Busca itens de uma licitação específica
    
    DESCRIÇÃO:
    - Busca itens detalhados de uma licitação pelo número de controle PNCP
    - Primeiro verifica se os itens estão salvos no banco de dados
    - Se não encontrar, busca na API oficial do PNCP e salva automaticamente
    - Retorna informações completas dos itens: descrição, quantidade, valores, etc.
    
    PARÂMETROS:
    - pncp_id: Número de controle PNCP da licitação (formato: CNPJ-1-SEQUENCIAL/ANO)
    
    FUNCIONALIDADE:
    1. Verifica se a licitação existe no banco de dados
    2. Busca itens salvos no banco (mais rápido)
    3. Se não encontrar, busca na API do PNCP
    4. Salva os itens no banco para consultas futuras
    5. Retorna itens formatados com dados completos
    
    RETORNA:
    {
        "success": true,
        "data": {
            "licitacao": {
                "id": "123",
                "pncp_id": "12345678000123-1-456/2024",
                "objeto_compra": "Aquisição de equipamentos",
                "valor_total_estimado": 150000.00,
                ...
            },
            "itens": [
                {
                    "numero_item": 1,
                    "descricao": "Notebook Dell Inspiron 15",
                    "quantidade": 10,
                    "unidade_medida": "UNIDADE",
                    "valor_unitario_estimado": 2500.00,
                    "valor_total": 25000.00,
                    "material_ou_servico": "M",
                    "criterio_julgamento_nome": "Menor preço",
                    "situacao_item": "Ativo",
                    ...
                }
            ],
            "fonte": "banco_dados", // ou "api_pncp"
            "total_itens": 15
        },
        "message": "15 itens carregados do banco de dados"
    }
    
    CASOS DE USO:
    - Modal de detalhes da licitação no frontend
    - Análise detalhada de itens para matching
    - Verificação de compatibilidade com produtos/serviços
    - Histórico completo de licitações
    """
    return controller.get_licitacao_items(pncp_id)

@pncp_routes.route('/licitacao/<path:pncp_id>/itens/refresh', methods=['POST'])
def refresh_licitacao_items(pncp_id):
    """
    POST /api/pncp/licitacao/{pncp_id}/itens/refresh - Força atualização dos itens
    
    DESCRIÇÃO:
    - Força busca dos itens diretamente da API do PNCP
    - Ignora dados salvos no banco e busca versão mais recente
    - Atualiza os dados salvos no banco com as informações mais recentes
    - Útil quando há suspeita de dados desatualizados
    
    PARÂMETROS:
    - pncp_id: Número de controle PNCP da licitação
    
    FUNCIONALIDADE:
    1. Verifica se a licitação existe no banco
    2. Busca itens diretamente na API do PNCP (ignora cache)
    3. Substitui dados salvos no banco com versão atualizada
    4. Retorna itens atualizados
    
    CASOS DE USO:
    - Licitação foi alterada/atualizada recentemente
    - Dados incompletos ou inconsistentes no banco
    - Verificação de dados antes de decisões importantes
    - Auditoria de dados para matching crítico
    
    RETORNA:
    - Estrutura similar ao GET, mas com fonte "api_pncp_refresh"
    - Confirmação de atualização no banco
    """
    return controller.refresh_licitacao_items(pncp_id)

# ====== INFORMAÇÕES E DOCUMENTAÇÃO ======

@pncp_routes.route('/info', methods=['GET'])
def get_pncp_info():
    """
    GET /api/pncp/info - Informações sobre a integração com PNCP
    
    DESCRIÇÃO:
    - Informações sobre como funciona a busca no PNCP
    - Limitações, recomendações e boas práticas
    - Status da conexão com a API oficial
    
    RETORNA:
    - Documentação sobre o uso da API
    - Configurações atuais e limitações
    - Dicas de otimização para buscas
    """
    info = {
        'sistema': 'Integração PNCP - Portal Nacional de Contratações Públicas',
        'api_oficial': 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao',
        'funcionalidades': [
            'Busca unificada via /api/search/unified (Local + PNCP combinados)',
            'Busca de itens detalhados por licitação',
            'Cache inteligente para performance otimizada',
            'Sistema de score de relevância por palavras-chave'
        ],
        'modalidades_suportadas': [
            {'codigo': 'pregao_eletronico', 'nome': 'Pregão Eletrônico', 'api_code': 8},
            {'codigo': 'concorrencia', 'nome': 'Concorrência', 'api_code': 5},
            {'codigo': 'convite', 'nome': 'Convite', 'api_code': 6},
            {'codigo': 'tomada_precos', 'nome': 'Tomada de Preços', 'api_code': 7},
            {'codigo': 'dispensa', 'nome': 'Dispensa', 'api_code': 1},
            {'codigo': 'inexigibilidade', 'nome': 'Inexigibilidade', 'api_code': 2}
        ],
        'limitacoes': {
            'intervalo_maximo_dias': 90,
            'max_paginas_por_busca': 10,
            'max_resultados_por_pagina': 500,
            'timeout_requisicao': 30,
            'max_tentativas': 3
        },
        'recomendacoes': [
            'Use /api/search/unified para busca combinada (Local + PNCP)',
            'Palavras-chave específicas geram melhores resultados',
            'Evite intervalos muito grandes de datas',
            'O sistema já otimiza automaticamente as buscas'
        ],
        'endpoints_ativos': [
            'POST /api/search/unified - Busca unificada (recomendado)',
            'POST /api/pncp/search/advanced - Busca PNCP avançada (uso interno)',
            'GET /api/pncp/licitacao/{id}/itens - Itens de licitação',
            'POST /api/pncp/licitacao/{id}/itens/refresh - Atualizar itens',
            'GET /api/pncp/info - Esta documentação'
        ]
    }
    
    return jsonify({
        'success': True,
        'data': info,
        'message': 'Informações sobre a integração PNCP'
    }), 200 