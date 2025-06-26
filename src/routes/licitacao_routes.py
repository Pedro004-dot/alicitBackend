"""
Rotas para Busca de Licitações
Define os endpoints da API para o novo fluxo de busca de licitações.
"""
from flask import Blueprint
from controllers.licitacao_controller import LicitacaoController

# Cria um Blueprint para agrupar as rotas de licitação.
# O prefixo '/api/licitacoes' será adicionado a todas as rotas definidas aqui.
licitacao_routes = Blueprint('licitacoes', __name__, url_prefix='/api/licitacoes')

# Instancia o controller que contém a lógica de manipulação das requisições.
licitacao_controller = LicitacaoController()

@licitacao_routes.route('/buscar', methods=['POST'])
def buscar_licitacoes():
    """
    POST /api/licitacoes/buscar
    Endpoint principal para busca avançada de licitações com NOVA ESTRATÉGIA THIAGO.

    ✅ NOVA IMPLEMENTAÇÃO: Agora usa as MESMAS FUNÇÕES do GET para máxima consistência.
    ✅ ESTRATÉGIA: Busca ampla na API + Filtro rigoroso local + Sinônimos locais
    
    Corpo da Requisição (JSON):
    {
        // === CAMPOS DE BUSCA (pelo menos um obrigatório) ===
        "palavra_chave": "string",              // Termo único de busca
        "palavras_busca": ["termo1", "termo2"], // OU lista de múltiplos termos
        
        // === FILTROS GEOGRÁFICOS (arrays JSON) ===
        "estados": ["SP", "RJ", "MG"],          // ✅ Múltiplos estados (array)
        "cidades": ["São Paulo", "Rio de Janeiro"], // ✅ Múltiplas cidades (array)
        
        // === FILTROS DE LICITAÇÃO ===
        "modalidades": ["pregao_eletronico", "concorrencia"], // Múltiplas modalidades
        "valor_minimo": 10000,                  // Valor mínimo em reais
        "valor_maximo": 500000,                 // Valor máximo em reais
        
        // === PARÂMETROS DA ESTRATÉGIA THIAGO ===
        "usar_sinonimos": true,                 // Expandir busca com sinônimos locais
        "threshold_relevancia": 0.6,            // Rigor do filtro (0.0 a 1.0)
        
        // === PAGINAÇÃO (opcional - pode vir via query string) ===
        "pagina": 1,                           // Página atual
        "itens_por_pagina": 50                 // Itens por página
    }

    Query Params (alternativa para paginação):
    - ?pagina=1
    - ?itens_por_pagina=50

    Exemplos de Uso:
    
    1. Busca simples:
    {
        "palavra_chave": "limpeza",
        "estados": ["SP", "RJ"]
    }
    
    2. Busca múltipla com filtros:
    {
        "palavras_busca": ["sistema", "software"],
        "estados": ["SP", "MG", "RJ"],
        "cidades": ["São Paulo", "Belo Horizonte"],
        "modalidades": ["pregao_eletronico"],
        "valor_minimo": 50000,
        "usar_sinonimos": true,
        "threshold_relevancia": 0.5
    }

    Resposta de Sucesso (200 OK):
    {
        "success": true,
        "message": "Busca realizada com sucesso. Total de 123 licitações encontradas.",
        "data": {
            "data": [...],              // Array de licitações
            "metadados": {              // Metadados da busca
                "totalRegistros": 123,
                "totalPaginas": 3,
                "pagina": 1,
                "estrategia_busca": {
                    "tipo": "Thiago Melhorada",
                    "busca_ampla_api": true,
                    "filtro_local_rigoroso": true
                }
            }
        },
        "metodo": "POST com Nova Estratégia Thiago",
        "filtros_aplicados": {...},
        "palavras_buscadas": [...]
    }

    ⚡ Performance: Busca inteligente com múltiplas páginas quando filtro de cidade é usado.
    🎯 Relevância: Sistema de score rigoroso com threshold configurável.
    🔍 Sinônimos: Geração local via OpenAI (não envia para API do PNCP).
    """
    # Delega toda a lógica para o método 'buscar' do controller.
    return licitacao_controller.buscar()

@licitacao_routes.route('/buscar', methods=['GET'])
def buscar_licitacoes_get():
    """
    GET /api/licitacoes/buscar
    Endpoint de busca de licitações que aceita parâmetros via query string.
    
    Query Parameters:
    - palavras_busca: string (obrigatório) - Termos de busca
    - pagina: int (opcional, padrão: 1) - Página atual
    - itens_por_pagina: int (opcional, padrão: 50) - Itens por página
    - estados: string (opcional) - UFs separadas por vírgula (ex: "SP,RJ,MG")
    - cidades: string (opcional) - Cidades separadas por vírgula
    - modalidades: string (opcional) - Modalidades separadas por vírgula
    - valor_minimo: float (opcional) - Valor mínimo da licitação
    - valor_maximo: float (opcional) - Valor máximo da licitação
    
    Exemplo: /api/licitacoes/buscar?palavras_busca=software&estados=SP,RJ&modalidades=pregao_eletronico
    """
    return licitacao_controller.buscar_get() 