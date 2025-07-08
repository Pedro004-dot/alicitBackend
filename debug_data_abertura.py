#!/usr/bin/env python3

"""
🔍 Debug específico para Data de Abertura PNCP

Verifica quais campos relacionados a datas estão disponíveis na API v1 do PNCP
e por que a data de abertura não está sendo extraída.
"""

import os
import sys
import logging
import json
import requests

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_data_abertura():
    """🔍 Debug específico para campos de data na API PNCP"""
    
    print("🔍 DEBUG: CAMPOS DE DATA NA API PNCP v1")
    print("=" * 50)
    
    # ID da licitação que sabemos que existe
    test_pncp_id = "04892707000100-1-000246/2024"
    
    # Extrair componentes
    def parse_numero_controle_pncp(numero_controle: str):
        try:
            if '/' in numero_controle:
                parte_principal, ano_final = numero_controle.split('/')
                partes = parte_principal.split('-')
                
                if len(partes) >= 3:
                    cnpj = partes[0]
                    sequencial = partes[2]
                    ano = ano_final
                    return cnpj, ano, sequencial
            return None, None, None
        except:
            return None, None, None
    
    cnpj, ano, sequencial = parse_numero_controle_pncp(test_pncp_id)
    
    if not all([cnpj, ano, sequencial]):
        print(f"❌ Falha ao extrair componentes de: {test_pncp_id}")
        return
    
    print(f"📋 CNPJ: {cnpj}")
    print(f"📋 ANO: {ano}")  
    print(f"📋 SEQUENCIAL: {sequencial}")
    print()
    
    # URL da API v1 CORRIGIDA
    api_v1_base = "https://pncp.gov.br/api/consulta/v1"  # 🔧 URL CORRIGIDA
    url_detalhes = f"{api_v1_base}/orgaos/{cnpj}/compras/{ano}/{sequencial}"
    
    try:
        print(f"🌐 URL: {url_detalhes}")
        print()
        
        response = requests.get(url_detalhes, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Buscar todos os campos relacionados a data
        print("📅 CAMPOS RELACIONADOS A DATA ENCONTRADOS:")
        print("-" * 40)
        
        campos_data = []
        for key, value in data.items():
            if any(palavra in key.lower() for palavra in ['data', 'date', 'prazo', 'abertura', 'proposta', 'recebimento', 'encerr', 'final']):
                campos_data.append((key, value))
                
        if campos_data:
            for campo, valor in campos_data:
                print(f"   🗓️  {campo:35} = {valor}")
        else:
            print("   ❌ Nenhum campo de data encontrado!")
        
        print()
        print("📋 TODOS OS CAMPOS DISPONÍVEIS:")
        print("-" * 30)
        for i, key in enumerate(sorted(data.keys())):
            print(f"   {i+1:2d}. {key}")
        
        print()
        print("🔍 DADOS COMPLETOS (sample):")
        print("-" * 20)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000] + "...")
        
    except Exception as e:
        print(f"❌ Erro ao buscar dados: {e}")

if __name__ == "__main__":
    debug_data_abertura() 