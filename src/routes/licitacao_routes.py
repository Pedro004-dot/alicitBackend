"""
Rotas para Busca de Licitações
Define os endpoints da API para o novo fluxo de busca de licitações.
"""
from flask import Blueprint
from controllers.licitacao_controller import LicitacaoController

# Criar o blueprint
licitacao_routes = Blueprint('licitacao_routes', __name__)

# Instanciar o controller
licitacao_controller = LicitacaoController()

@licitacao_routes.route('/api/licitacoes/buscar', methods=['POST'])
def buscar():
    """
    Endpoint de busca de licitações
    ---
    tags:
      - Licitações
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            filtros:
              type: object
              properties:
                palavra_chave:
                  type: string
                  description: Termo de busca
                modalidades:
                  type: array
                  items:
                    type: string
                  description: Lista de modalidades
                estados:
                  type: array
                  items:
                    type: string
                  description: Lista de estados
                cidades:
                  type: array
                  items:
                    type: string
                  description: Lista de cidades
                valor_minimo:
                  type: number
                  description: Valor mínimo
                valor_maximo:
                  type: number
                  description: Valor máximo
            fontes:
              type: array
              items:
                type: string
              description: Lista de fontes a serem consultadas (opcional, default ["pncp"])
    responses:
      200:
        description: Busca realizada com sucesso
      400:
        description: Erro nos parâmetros da requisição
      500:
        description: Erro interno do servidor
    """
    return licitacao_controller.buscar() 