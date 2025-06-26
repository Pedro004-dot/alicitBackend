#!/usr/bin/env python3
"""
Debug específico das datas de encerramento das licitações.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from repositories.licitacao_repository import LicitacaoPNCPRepository
import asyncio
from datetime import datetime

async def debug_datas():
    """
    Debug das datas de encerramento.
    """
    print("📅 DEBUG: Analisando datas de encerramento")
    print("=" * 60)
    
    repo = LicitacaoPNCPRepository()
    
    # Buscar dados da API
    filtros = {
        "estados": ["SP"],
        "modalidades": ["pregao_eletronico"]
    }
    
    params = repo._construir_parametros(filtros, [], 1, 5)
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao", params=params) as response:
            if response.status == 200:
                data = await response.json()
                licitacoes_raw = data.get('data', [])
                print(f"✅ API retornou {len(licitacoes_raw)} licitações")
            else:
                print(f"❌ Erro na API: {response.status}")
                return
    
    data_atual = datetime.now()
    print(f"📅 Data atual: {data_atual.strftime('%d/%m/%Y %H:%M')}")
    print()
    
    for i, lic in enumerate(licitacoes_raw):
        print(f"--- LICITAÇÃO {i+1} ---")
        numero_controle = lic.get('numeroControlePNCP', 'N/A')
        objeto_compra = lic.get('objetoCompra', '')[:60] + "..."
        
        print(f"🆔 ID: {numero_controle}")
        print(f"📝 Objeto: {objeto_compra}")
        
        # Verificar todas as datas disponíveis
        campos_data = [
            'dataPublicacaoPncp',
            'dataAberturaProposta', 
            'dataEncerramentoProposta',
            'dataAberturaSessaoPublica',
            'dataEncerramentoSessaoPublica'
        ]
        
        for campo in campos_data:
            valor = lic.get(campo)
            if valor:
                try:
                    if isinstance(valor, str):
                        data_clean = valor.split('T')[0] if 'T' in valor else valor
                        data_dt = datetime.strptime(data_clean, '%Y-%m-%d')
                        status = "✅ ATIVA" if data_dt.date() > data_atual.date() else "❌ EXPIRADA"
                        print(f"   📅 {campo}: {data_dt.strftime('%d/%m/%Y')} {status}")
                    else:
                        print(f"   📅 {campo}: {valor} (formato não string)")
                except Exception as e:
                    print(f"   ❌ {campo}: {valor} (erro: {e})")
            else:
                print(f"   📅 {campo}: N/A")
        
        # Testar especificamente dataEncerramentoProposta
        data_encerramento = lic.get('dataEncerramentoProposta')
        if data_encerramento:
            try:
                if isinstance(data_encerramento, str):
                    data_clean = data_encerramento.split('T')[0] if 'T' in data_encerramento else data_encerramento
                    data_encerramento_dt = datetime.strptime(data_clean, '%Y-%m-%d')
                    
                    if data_encerramento_dt.date() <= data_atual.date():
                        print(f"   🚫 REJEITADA por prazo: {data_encerramento_dt.strftime('%d/%m/%Y')} <= {data_atual.strftime('%d/%m/%Y')}")
                    else:
                        print(f"   ✅ APROVADA por prazo: {data_encerramento_dt.strftime('%d/%m/%Y')} > {data_atual.strftime('%d/%m/%Y')}")
            except Exception as e:
                print(f"   ❌ Erro ao processar data: {e}")
        else:
            print(f"   ⚠️ Sem dataEncerramentoProposta - seria APROVADA")
        
        print()

if __name__ == "__main__":
    asyncio.run(debug_datas()) 