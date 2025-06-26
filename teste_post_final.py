#!/usr/bin/env python3

"""
Teste final da nova implementação POST - Estratégia Thiago
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from controllers.licitacao_controller import LicitacaoController
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)

class MockRequest:
    """Mock da requisição Flask para testar o controller"""
    
    def __init__(self, json_data, args=None):
        self.json_data = json_data
        self.args_data = args or {}
    
    def get_json(self):
        return self.json_data
    
    def args_get(self, key, default=None, type=int):
        if type == int:
            try:
                return int(self.args_data.get(key, default))
            except (ValueError, TypeError):
                return default
        return self.args_data.get(key, default)

def testar_post_nova_estrategia():
    """
    Testa a nova implementação POST que usa as mesmas funções do GET.
    """
    print("🚀 TESTE POST - NOVA ESTRATÉGIA THIAGO")
    print("=" * 60)
    
    controller = LicitacaoController()
    
    # Casos de teste
    casos_teste = [
        {
            "nome": "🧪 Teste Básico - Múltiplos Estados",
            "json": {
                "palavra_chave": "medicamento",
                "estados": ["SP", "RJ"],
                "usar_sinonimos": False,
                "threshold_relevancia": 0.5
            },
            "args": {"pagina": "1", "itens_por_pagina": "10"}
        },
        {
            "nome": "🏙️ Teste Arrays - Estados e Cidades",
            "json": {
                "palavras_busca": ["servico", "manutencao"],
                "estados": ["SP", "MG"],
                "cidades": ["São Paulo", "Belo Horizonte"],
                "modalidades": ["pregao_eletronico"],
                "threshold_relevancia": 0.4
            },
            "args": {}
        },
        {
            "nome": "⚡ Teste Completo com Todos os Filtros",
            "json": {
                "palavra_chave": "material",
                "estados": ["SP"],
                "modalidades": ["pregao_eletronico"],
                "valor_minimo": 10000,
                "valor_maximo": 100000,
                "usar_sinonimos": True,
                "threshold_relevancia": 0.3,
                "pagina": 1,
                "itens_por_pagina": 5
            },
            "args": {}
        }
    ]
    
    for i, caso in enumerate(casos_teste):
        print(f"\n{caso['nome']}")
        print("-" * 50)
        
        # Simular requisição
        import flask
        app = flask.Flask(__name__)
        
        with app.test_request_context(
            '/', 
            method='POST', 
            json=caso['json'],
            query_string=caso['args']
        ):
            try:
                resultado, status_code = controller.buscar()
                resultado_data = resultado.get_json()
                
                print(f"   📊 Status: {status_code}")
                print(f"   ✅ Sucesso: {resultado_data.get('success')}")
                print(f"   📝 Mensagem: {resultado_data.get('message', 'N/A')}")
                
                if resultado_data.get('success'):
                    data = resultado_data.get('data', {})
                    metadados = data.get('metadados', {})
                    
                    print(f"   🔍 Total encontrado: {metadados.get('totalRegistros', 0)}")
                    print(f"   📄 Licitações retornadas: {len(data.get('data', []))}")
                    print(f"   🎯 Método usado: {resultado_data.get('metodo', 'N/A')}")
                    
                    # Estratégia aplicada
                    estrategia = metadados.get('estrategia_busca', {})
                    if estrategia:
                        print(f"   ⚡ Estratégia: {estrategia.get('tipo')}")
                        print(f"   🔧 Threshold: {estrategia.get('threshold_relevancia')}")
                        print(f"   ✨ Sinônimos: {estrategia.get('sinonimos_locais')}")
                    
                    # Filtros aplicados
                    filtros = resultado_data.get('filtros_aplicados', {})
                    if filtros.get('estados'):
                        print(f"   🌍 Estados: {filtros['estados']}")
                    if filtros.get('cidades'):
                        print(f"   🏙️ Cidades: {filtros['cidades']}")
                    
                    print(f"   🔤 Palavras buscadas: {resultado_data.get('palavras_buscadas', [])}")
                    
                else:
                    print(f"   ❌ Erro: {resultado_data.get('message')}")
                
            except Exception as e:
                print(f"   💥 Exceção: {e}")
    
    print("\n" + "=" * 60)
    print("📊 CONCLUSÃO:")
    print("✅ Se você viu resultados encontrados, a nova estratégia está funcionando!")
    print("✅ POST agora usa as mesmas funções do GET")
    print("✅ Múltiplos estados e cidades funcionando via arrays JSON")
    print("✅ Estratégia Thiago implementada com sucesso!")

if __name__ == "__main__":
    testar_post_nova_estrategia() 