#!/usr/bin/env python3
"""
🧪 Teste do novo parser HTML do ComprasNet
Valida a extração de dados usando tags HTML ao invés de regex
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from adapters.comprasnet_adapter import ComprasNetAdapter
from bs4 import BeautifulSoup
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_html_parser():
    """Testar o parser HTML com dados reais do ComprasNet"""
    
    # Sample HTML baseado no exemplo fornecido
    sample_html = """
    <form method="post" name="Form1">
        <a name="F1">&nbsp;</a>
        <table border="0" width="100%" class="td" cellpadding="1" cellspacing="1">
            <tbody>
                <tr class="mensagem"><td>1</td></tr>
                <tr bgcolor="#FFFFFF" class="tex3">
                    <td>
                        <b>MINISTÉRIO DA SAÚDE<br>FUNDAÇÃO OSWALDO CRUZ<br>Instituto de Tecnologia em Imunobiologicos Bio Manguinhos<br>Código da UASG: 254445<br></b>
                        <br>
                        <b>Pregão Eletrônico Nº 90169/2025<span class="mensagem"> - (Lei Nº 14.133/2021)</span></b>
                        <br>
                        <b>Objeto:</b>&nbsp;Objeto: Pregão Eletrônico -  Aquisição de itens da marca ABB.
                        <br>
                        <b>Edital a partir de:</b>&nbsp;10/07/2025 das 08:00 às 12:00 Hs e das 13:00 às 17:59 Hs
                        <br>
                        <b>Endereço:</b>&nbsp;Avenida Brasil, 4365 - Manguinhos - Rio de Janeiro (RJ)
                        <br>
                        <b>Telefone:</b>&nbsp;(0xx21) 38829334
                        <br>
                        <b>Fax:</b>&nbsp;(0xx21)               
                        <br>
                        <b>Entrega da Proposta:</b>&nbsp;10/07/2025 às 08:00Hs
                        <br><br>
                        <input type="hidden" name="origem" value="2">
                        <a href="#F1" name="hist_eventos" class="legenda" onclick="javascript:visualizarHistoricoEventos(document.Form1,'?coduasg=254445&amp;modprp=5&amp;numprp=901692025');" title="Visualizar histórico de eventos publicados para a licitação">Histórico de eventos publicados...</a>
                        <br><br>
                        <input type="button" name="itens" value="Itens e Download" class="texField2" onclick="javascript:VisualizarItens(document.Form1,'?coduasg=254445&amp;modprp=5&amp;numprp=901692025');" onmouseover="window.status='Itens da Licitação e Download do Edital';return true;" title="Clique para ver os itens ou para fazer o Download do Edital">
                    </td>
                </tr>
            </tbody>
        </table>
    </form>
    
    <form method="post" name="Form2">
        <a name="F2">&nbsp;</a>
        <table border="0" width="100%" class="td" cellpadding="1" cellspacing="1">
            <tbody>
                <tr class="mensagem"><td>2</td></tr>
                <tr bgcolor="#FFFFFF" class="tex3">
                    <td>
                        <b>MINISTÉRIO DA SAÚDE<br>Núcleo Estadual no Rio de Janeiro/MS<br>Instituto Nacional de Traumato-Ortopedia<br>Código da UASG: 250057<br></b>
                        <br>
                        <b>Pregão Eletrônico Nº 90077/2025<span class="mensagem"> - (Lei Nº 14.133/2021)</span></b>
                        <br>
                        <b>Objeto:</b>&nbsp;Objeto: Pregão Eletrônico -  AQUISIÇÃO DE IMPLANTES ORTOPÉDICOS (Sistema  Fixação  Coluna  Vertebral)
                        <br>
                        <b>Edital a partir de:</b>&nbsp;10/07/2025 das 10:00 às 12:00 Hs e das 13:00 às 16:00 Hs
                        <br>
                        <b>Endereço:</b>&nbsp;Av. Brasil, Nº 500, Sao Cristovao - Rio de Janeiro (RJ)
                        <br>
                        <b>Telefone:</b>&nbsp;         
                        <br>
                        <b>Fax:</b>&nbsp;               
                        <br>
                        <b>Entrega da Proposta:</b>&nbsp;10/07/2025 às 10:00Hs
                        <br><br>
                        <input type="hidden" name="origem" value="2">
                        <a href="#F2" name="hist_eventos" class="legenda" onclick="javascript:visualizarHistoricoEventos(document.Form2,'?coduasg=250057&amp;modprp=5&amp;numprp=900772025');" title="Visualizar histórico de eventos publicados para a licitação">Histórico de eventos publicados...</a>
                        <br><br>
                        <input type="button" name="itens" value="Itens e Download" class="texField2" onclick="javascript:VisualizarItens(document.Form2,'?coduasg=250057&amp;modprp=5&amp;numprp=900772025');" onmouseover="window.status='Itens da Licitação e Download do Edital';return true;" title="Clique para ver os itens ou para fazer o Download do Edital">
                    </td>
                </tr>
            </tbody>
        </table>
    </form>
    """
    
    print("🧪 Testando novo parser HTML do ComprasNet...")
    print("="*60)
    
    # Inicializar adapter
    adapter = ComprasNetAdapter()
    
    # Criar soup do HTML de exemplo
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Testar o novo parser
    licitacao_data_list = adapter._find_advanced_licitacao_blocks(soup)
    
    print(f"📊 Licitações encontradas: {len(licitacao_data_list)}")
    print("="*60)
    
    for i, licitacao_data in enumerate(licitacao_data_list, 1):
        print(f"\n🏛️ LICITAÇÃO {i}:")
        print(f"   🆔 ID: {licitacao_data.get('external_id', 'N/A')}")
        print(f"   🏢 Entidade: {licitacao_data.get('entity_name', 'N/A')}")
        print(f"   📋 UASG: {licitacao_data.get('uasg', 'N/A')}")
        print(f"   📄 Pregão: {licitacao_data.get('pregao_numero', 'N/A')}/{licitacao_data.get('pregao_ano', 'N/A')}")
        print(f"   🎯 Objeto: {licitacao_data.get('object_description', 'N/A')[:100]}...")
        print(f"   📅 Edital: {licitacao_data.get('edital_date_str', 'N/A')}")
        print(f"   ⏰ Entrega: {licitacao_data.get('entrega_date_str', 'N/A')}")
        print(f"   📍 Endereço: {licitacao_data.get('endereco', 'N/A')}")
        print(f"   🏙️ Cidade/UF: {licitacao_data.get('cidade', 'N/A')}/{licitacao_data.get('uf', 'N/A')}")
        print(f"   📞 Telefone: {licitacao_data.get('telefone', 'N/A')}")
        print(f"   🔗 Histórico: {licitacao_data.get('historico_link', 'N/A')}")
        print(f"   📦 Itens: {licitacao_data.get('itens_link', 'N/A')}")
        print(f"   🔧 Params: {licitacao_data.get('bid_params', 'N/A')}")
        print(f"   📊 Datas: {licitacao_data.get('dates', 'N/A')}")
        print(f"   ⚙️ Método: {licitacao_data.get('extraction_method', 'N/A')}")
        print(f"   🕐 Extraído: {licitacao_data.get('extracted_at', 'N/A')}")
        
        # Mostrar primeiros 200 chars do HTML raw
        raw_html = licitacao_data.get('raw_html', '')
        if raw_html:
            print(f"   🔍 HTML (200 chars): {raw_html[:200]}...")
    
    print("\n" + "="*60)
    print("✅ Teste concluído!")
    
    # Validar se os dados essenciais foram extraídos
    if licitacao_data_list:
        success_count = 0
        for licitacao in licitacao_data_list:
            if (licitacao.get('external_id') and 
                licitacao.get('entity_name') and 
                licitacao.get('uasg') and 
                licitacao.get('object_description')):
                success_count += 1
        
        print(f"📈 Taxa de sucesso: {success_count}/{len(licitacao_data_list)} ({success_count/len(licitacao_data_list)*100:.1f}%)")
        
        if success_count == len(licitacao_data_list):
            print("🎉 TODOS os dados essenciais foram extraídos com sucesso!")
        else:
            print(f"⚠️ {len(licitacao_data_list) - success_count} licitações com dados incompletos")
    else:
        print("❌ Nenhuma licitação foi extraída")

if __name__ == "__main__":
    test_html_parser()