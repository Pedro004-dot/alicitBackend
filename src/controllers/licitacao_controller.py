"""
Licitacao Controller
Controller para lidar com as requisições HTTP relacionadas à busca de licitações.
"""
import logging
from flask import request, jsonify
from typing import Dict, List, Optional

# Importar o serviço principal
from services.licitacao_service import LicitacaoService
from middleware.error_handler import log_endpoint_access
from services.search.source_registry import RegistroFontes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LicitacaoController:
    """
    Controller que recebe as requisições da API para busca de licitações,
    valida os dados e chama o serviço correspondente.
    """

    def __init__(self):
        """Inicializa o controller e uma instância do serviço de licitação."""
        self.service = LicitacaoService()
    
    def buscar(self):
        """
        Endpoint de busca de licitações
        
        Request JSON:
        {
            "filtros": {
                "palavra_chave": string,
                "modalidades": list[string],
                "estados": list[string],
                "cidades": list[string],
                "valor_minimo": number,
                "valor_maximo": number
            },
            "fontes": list[string]  # opcional, default ["pncp"]
        }
        """
        try:
            # Obtém os dados da requisição
            dados = request.get_json()
            
            if not dados:
                return jsonify({
                    "erro": "Dados da requisição não fornecidos",
                    "codigo": "DADOS_AUSENTES"
                }), 400
            
            # Extrai os filtros e fontes
            filtros = dados.get("filtros", {})
            fontes = dados.get("fontes")  # None por padrão
            
            # Valida os filtros básicos
            if not self._validar_filtros(filtros):
                return jsonify({
                    "erro": "Filtros inválidos",
                    "codigo": "FILTROS_INVALIDOS"
                }), 400
            
            # Se fontes foram especificadas, valida-as
            if fontes is not None:
                fontes_disponiveis = set(RegistroFontes.listar_fontes().keys())
                fontes_invalidas = set(fontes) - fontes_disponiveis
                
                if fontes_invalidas:
                    return jsonify({
                        "erro": f"Fontes inválidas: {', '.join(fontes_invalidas)}",
                        "fontes_disponiveis": list(fontes_disponiveis),
                        "codigo": "FONTES_INVALIDAS"
                    }), 400
            
            # Realiza a busca
            resultado = self.service.buscar_licitacoes(
                filtros=filtros,
                fontes=fontes
            )
            
            return jsonify(resultado)
            
        except Exception as e:
            return jsonify({
                "erro": str(e),
                "codigo": "ERRO_INTERNO"
            }), 500
    
    def detalhes_licitacao(self, licitacao_id):
        """
        Busca detalhes completos da licitação e seus itens pelo ID interno.
        """
        try:
            resultado = self.service.buscar_detalhes_por_id(licitacao_id)
            if resultado:
                return jsonify({"success": True, "data": resultado}), 200
            else:
                return jsonify({"success": False, "message": "Licitação não encontrada"}), 404
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500
    
    def _validar_filtros(self, filtros: Dict) -> bool:
        """
        Valida os filtros básicos da requisição
        
        Args:
            filtros: Dicionário com os filtros
            
        Returns:
            True se os filtros são válidos, False caso contrário
        """
        # Validações básicas dos filtros
        if not isinstance(filtros, dict):
            return False
        
        # Valida tipos dos campos (quando presentes)
        if "palavra_chave" in filtros and not isinstance(filtros["palavra_chave"], str):
            return False
            
        if "modalidades" in filtros and not isinstance(filtros["modalidades"], list):
            return False
            
        if "estados" in filtros and not isinstance(filtros["estados"], list):
            return False
            
        if "cidades" in filtros and not isinstance(filtros["cidades"], list):
            return False
            
        if "valor_minimo" in filtros and not isinstance(filtros["valor_minimo"], (int, float)):
            return False
            
        if "valor_maximo" in filtros and not isinstance(filtros["valor_maximo"], (int, float)):
            return False
        
        return True 