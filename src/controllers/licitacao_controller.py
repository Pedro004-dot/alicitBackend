"""
Licitacao Controller
Controller para lidar com as requisições HTTP relacionadas à busca de licitações.
"""
import logging
from flask import request, jsonify
from typing import Dict, Any, Tuple

# Importar o serviço principal
from services.licitacao_service import LicitacaoService
from middleware.error_handler import log_endpoint_access

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicitacaoController:
    """
    Controller que recebe as requisições da API para busca de licitações,
    valida os dados e chama o serviço correspondente.
    """

    def __init__(self):
        """Inicializa o controller e uma instância do serviço de licitação."""
        self.licitacao_service = LicitacaoService()

    @log_endpoint_access
    def buscar(self) -> Tuple[Dict[str, Any], int]:
        """
        Manipula a requisição POST para /api/licitacoes/buscar.
        
        NOVA ESTRATÉGIA: Usa as MESMAS FUNÇÕES do GET, mas recebe dados via body JSON.
        
        Body JSON aceita:
        {
            "palavra_chave": "string",              // OBRIGATÓRIO - termo de busca
            "palavras_busca": ["termo1", "termo2"], // ALTERNATIVA - lista de termos
            "estados": ["SP", "RJ", "MG"],          // OPCIONAL - múltiplos estados
            "cidades": ["São Paulo", "Rio"],        // OPCIONAL - múltiplas cidades  
            "modalidades": ["pregao_eletronico"],   // OPCIONAL - múltiplas modalidades
            "valor_minimo": 10000,                  // OPCIONAL - valor mínimo
            "valor_maximo": 500000,                 // OPCIONAL - valor máximo
            "usar_sinonimos": true,                 // OPCIONAL - expandir com sinônimos
            "threshold_relevancia": 0.6             // OPCIONAL - threshold de relevância
        }
        """
        try:
            # 1. Extrair dados do body JSON
            body_data = request.get_json()
            if not body_data:
                return jsonify({
                    'success': False,
                    'message': 'Corpo da requisição não pode ser vazio e deve ser um JSON válido.'
                }), 400

            # 2. Extrair palavra-chave ou palavras_busca
            palavra_chave = body_data.get('palavra_chave')
            palavras_busca_raw = body_data.get('palavras_busca', [])
            
            # Determinar palavras de busca finais
            if palavra_chave:
                # Se tem palavra_chave, converter para lista
                palavras_busca = [palavra_chave]
            elif palavras_busca_raw and isinstance(palavras_busca_raw, list):
                # Se tem palavras_busca como lista, usar diretamente
                palavras_busca = [p.strip() for p in palavras_busca_raw if p.strip()]
            elif palavras_busca_raw and isinstance(palavras_busca_raw, str):
                # Se palavras_busca é string, separar por espaços
                palavras_busca = palavras_busca_raw.split()
            else:
                return jsonify({
                    'success': False,
                    'message': 'Campo "palavra_chave" ou "palavras_busca" é obrigatório.'
                }), 400

            if not palavras_busca:
                return jsonify({
                    'success': False,
                    'message': 'Pelo menos um termo de busca deve ser fornecido.'
                }), 400

            # 3. Extrair parâmetros de paginação (query string tem prioridade)
            pagina = request.args.get('pagina', body_data.get('pagina', 1))
            if isinstance(pagina, str):
                pagina = int(pagina)
            
            itens_por_pagina = request.args.get('itens_por_pagina', body_data.get('itens_por_pagina', 500))  # ✅ AUMENTADO: padrão 500
            if isinstance(itens_por_pagina, str):
                itens_por_pagina = int(itens_por_pagina)

            # 4. Construir filtros do body JSON (mesma lógica do GET)
            filtros = {}
            
            # ✅ Estados (array direto do JSON)
            estados = body_data.get('estados', [])
            if estados and isinstance(estados, list):
                filtros['estados'] = [estado.strip() for estado in estados if estado.strip()]
            elif estados and isinstance(estados, str):
                # Fallback: se vier como string, separar por vírgula
                filtros['estados'] = [estado.strip() for estado in estados.split(',') if estado.strip()]
            
            # ✅ Cidades (array direto do JSON)
            cidades = body_data.get('cidades', [])
            if cidades and isinstance(cidades, list):
                filtros['cidades'] = [cidade.strip() for cidade in cidades if cidade.strip()]
            elif cidades and isinstance(cidades, str):
                # Fallback: se vier como string, separar por vírgula
                filtros['cidades'] = [cidade.strip() for cidade in cidades.split(',') if cidade.strip()]
            
            # ✅ Modalidades (array direto do JSON)
            modalidades = body_data.get('modalidades', [])
            if modalidades and isinstance(modalidades, list):
                filtros['modalidades'] = [modalidade.strip() for modalidade in modalidades if modalidade.strip()]
            elif modalidades and isinstance(modalidades, str):
                # Fallback: se vier como string, separar por vírgula
                filtros['modalidades'] = [modalidade.strip() for modalidade in modalidades.split(',') if modalidade.strip()]
            
            # ✅ Valores mínimo e máximo
            if 'valor_minimo' in body_data and body_data['valor_minimo'] is not None:
                filtros['valor_minimo'] = float(body_data['valor_minimo'])
                
            if 'valor_maximo' in body_data and body_data['valor_maximo'] is not None:
                filtros['valor_maximo'] = float(body_data['valor_maximo'])

            # ✅ Parâmetros específicos da estratégia Thiago
            if 'usar_sinonimos' in body_data:
                filtros['usar_sinonimos'] = bool(body_data['usar_sinonimos'])
                
            if 'threshold_relevancia' in body_data:
                filtros['threshold_relevancia'] = float(body_data['threshold_relevancia'])

            logger.info(f"🎯 Requisição POST (Nova Estratégia) - Palavras: {palavras_busca}, Filtros: {filtros}, Página: {pagina}")

            # 5. 🔄 NOVO: Utilizar método principal do serviço para geração de sinônimos
            # Preparar filtros para o serviço (inclui palavra_chave)
            filtros['palavra_chave'] = palavra_chave or ' '.join(palavras_busca)

            resultado_busca = self.licitacao_service.buscar_licitacoes(
                filtros,
                pagina,
                itens_por_pagina
            )

            total_registros = resultado_busca.get('total', 0)

            return jsonify({
                'success': True,
                'message': f"Busca realizada com sucesso. Total de {total_registros} licitações encontradas.",
                'data': resultado_busca,
                'metodo': 'POST com Nova Estratégia Thiago',
                'filtros_aplicados': filtros,
                'palavras_buscadas': resultado_busca.get('palavras_utilizadas', [])
            }), 200

        except ValueError as e:
            # Erros de validação de dados
            logger.warning(f"Erro de dados na requisição POST: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 400
            
        except ConnectionError as e:
            # Erros de conexão com APIs externas
            logger.error(f"Erro de conexão: {str(e)}")
            return jsonify({'success': False, 'message': f"Erro de comunicação com o PNCP: {e}"}), 503

        except Exception as e:
            # Outros erros inesperados no servidor
            logger.error(f"Erro inesperado no POST buscar: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Ocorreu um erro interno no servidor.'
            }), 500

    @log_endpoint_access
    def buscar_get(self) -> Tuple[Dict[str, Any], int]:
        """
        Manipula a requisição GET para /api/licitacoes/buscar.
        Extrai os filtros dos query parameters, chama o serviço e retorna a resposta formatada.
        """
        try:
            # 1. Extrair parâmetros da query string
            palavras_busca = request.args.get('palavras_busca')
            if not palavras_busca:
                return jsonify({
                    'success': False,
                    'message': 'O parâmetro "palavras_busca" é obrigatório.'
                }), 400

            # 2. Extrair outros parâmetros opcionais
            pagina = request.args.get('pagina', default=1, type=int)
            itens_por_pagina = request.args.get('itens_por_pagina', default=500, type=int)  # ✅ AUMENTADO: padrão 500
            
            # Construir filtros a partir dos query parameters
            filtros = {}
            
            # Estados (separados por vírgula)
            estados_param = request.args.get('estados')
            if estados_param:
                filtros['estados'] = [estado.strip() for estado in estados_param.split(',') if estado.strip()]
            
            # Cidades (separadas por vírgula)
            cidades_param = request.args.get('cidades')
            if cidades_param:
                filtros['cidades'] = [cidade.strip() for cidade in cidades_param.split(',') if cidade.strip()]
            
            # Modalidades (separadas por vírgula)
            modalidades_param = request.args.get('modalidades')
            if modalidades_param:
                filtros['modalidades'] = [modalidade.strip() for modalidade in modalidades_param.split(',') if modalidade.strip()]
            
            # Valores mínimo e máximo
            valor_minimo = request.args.get('valor_minimo', type=float)
            if valor_minimo is not None:
                filtros['valor_minimo'] = valor_minimo
                
            valor_maximo = request.args.get('valor_maximo', type=float)
            if valor_maximo is not None:
                filtros['valor_maximo'] = valor_maximo

            logger.info(f"Requisição GET de busca recebida. Palavras: '{palavras_busca}', Filtros: {filtros}, Página: {pagina}")

            # 3. Chamar o serviço usando o repositório PNCP diretamente
            resultado_busca = self.licitacao_service.buscar_licitacoes_pncp_simples(
                filtros,
                palavras_busca.split(),
                pagina,
                itens_por_pagina
            )

            # 4. Formatar e retornar a resposta de sucesso
            return jsonify({
                'success': True,
                'message': f"Busca realizada com sucesso. Total de {resultado_busca['metadados']['totalRegistros']} licitações encontradas.",
                'data': resultado_busca
            }), 200

        except ValueError as e:
            # Erros de validação de dados
            logger.warning(f"Erro de dados na requisição GET: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 400
            
        except ConnectionError as e:
            # Erros de conexão com APIs externas
            logger.error(f"Erro de conexão: {str(e)}")
            return jsonify({'success': False, 'message': f"Erro de comunicação com o PNCP: {e}"}), 503

        except Exception as e:
            # Outros erros inesperados no servidor
            logger.error(f"Erro inesperado no buscar_get: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Ocorreu um erro interno no servidor.'
            }), 500 