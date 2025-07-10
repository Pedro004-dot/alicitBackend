#!/usr/bin/env python3
"""
🧪 Teste simplificado do novo parser HTML do ComprasNet
Valida a extração de dados usando tags HTML ao invés de regex
"""

import sys
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

def parse_html_licitacao_data(data_cell, form_name: str, block_number: int) -> Optional[Dict[str, Any]]:
    """
    🎯 MÉTODO NOVO: Parse estruturado baseado em tags HTML
    Extrai dados diretamente da estrutura HTML do ComprasNet
    """
    try:
        # Extrair texto limpo da célula
        cell_text = data_cell.get_text(separator='\n', strip=True)
        
        # Também processar HTML para extrair links e elementos estruturados
        cell_html = str(data_cell)
        
        # 1️⃣ EXTRAIR ENTIDADE/ORGANIZAÇÃO: Primeiras linhas em <b>
        organization_lines = []
        bold_tags = data_cell.find_all('b')
        
        # Pegar apenas o primeiro <b> que contém a organização
        first_bold = bold_tags[0] if bold_tags else None
        if first_bold:
            # O primeiro <b> contém as linhas organizacionais separadas por <br>
            org_text = first_bold.get_text(separator='\n', strip=True)
            org_lines = [line.strip() for line in org_text.split('\n') if line.strip()]
            
            # Filtrar linhas que contêm "Código da UASG"
            org_lines_filtered = [line for line in org_lines if 'Código da UASG' not in line]
            
            if org_lines_filtered:
                # Se há múltiplas linhas, pegar a última (entidade específica)
                entity_name = org_lines_filtered[-1]
                # Também extrair ministério e órgão para hierarquia
                ministry = org_lines_filtered[0] if len(org_lines_filtered) >= 1 else ""
                organ = org_lines_filtered[1] if len(org_lines_filtered) >= 2 else ""
            else:
                entity_name = "Entidade não identificada"
                ministry = ""
                organ = ""
        else:
            entity_name = "Entidade não identificada"
            ministry = ""
            organ = ""
        
        # 2️⃣ EXTRAIR CÓDIGO UASG
        uasg_match = re.search(r'Código da UASG\s*:?\s*(\d+)', cell_text, re.IGNORECASE)
        uasg = uasg_match.group(1) if uasg_match else ''
        
        # 3️⃣ EXTRAIR NÚMERO DO PREGÃO
        pregao_match = re.search(r'Pregão Eletrônico Nº\s*(\d+)/(\d+)', cell_text, re.IGNORECASE)
        
        # Construir external_id
        if pregao_match and uasg:
            pregao_num = pregao_match.group(1)
            pregao_ano = pregao_match.group(2)
            external_id = f"comprasnet_{uasg}_{pregao_num}_{pregao_ano}"
        else:
            external_id = f"comprasnet_{form_name}_{block_number}_{int(datetime.now().timestamp())}"
        
        # 4️⃣ EXTRAIR OBJETO
        objeto_match = re.search(r'Objeto\s*:\s*(.+?)(?=\nEdital|\nEndereço|\nTelefone|\nEntrega|$)', cell_text, re.IGNORECASE | re.DOTALL)
        if objeto_match:
            objeto = objeto_match.group(1).strip()
            # Limpar "Objeto: " duplicado se existir
            objeto = re.sub(r'^Objeto\s*:\s*', '', objeto, flags=re.IGNORECASE)
        else:
            objeto = f"Pregão Eletrônico ComprasNet #{block_number}"
        
        # 5️⃣ EXTRAIR DATAS
        # Data do edital (publicação)
        edital_match = re.search(r'Edital a partir de\s*:\s*(.+?)(?=\n|$)', cell_text, re.IGNORECASE)
        edital_date_str = edital_match.group(1).strip() if edital_match else ''
        
        # Data de entrega da proposta (encerramento)
        entrega_match = re.search(r'Entrega da Proposta\s*:\s*(.+?)(?=\n|$)', cell_text, re.IGNORECASE)
        entrega_date_str = entrega_match.group(1).strip() if entrega_match else ''
        
        # Processar datas estruturadas
        publication_date = None
        closing_date = None
        opening_date = None
        
        # Extrair data de publicação (mesmo que edital)
        if edital_date_str:
            # Regex para extrair primeira data do formato DD/MM/YYYY
            pub_date_match = re.search(r'(\d{2}/\d{2}/\d{4})', edital_date_str)
            if pub_date_match:
                publication_date = pub_date_match.group(1)
                opening_date = publication_date  # Data de abertura = data de publicação
        
        # Extrair data de encerramento
        if entrega_date_str:
            # Regex para extrair data do formato DD/MM/YYYY
            close_date_match = re.search(r'(\d{2}/\d{2}/\d{4})', entrega_date_str)
            if close_date_match:
                closing_date = close_date_match.group(1)
        
        # 6️⃣ EXTRAIR ENDEREÇO E UF
        endereco_match = re.search(r'Endereço\s*:\s*(.+?)(?=\nTelefone|\nFax|\nEntrega|$)', cell_text, re.IGNORECASE | re.DOTALL)
        endereco = endereco_match.group(1).strip() if endereco_match else ""
        
        # Extrair UF do endereço - padrão: - CIDADE (UF)
        # Buscar o padrão no final do endereço
        uf_match = re.search(r'-\s*([A-ZÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙÃÕÇ][A-Za-záéíóúâêîôûàèìòùãõç\s]+?)\s*\(([A-Z]{2})\)\s*$', endereco)
        if uf_match:
            cidade = uf_match.group(1).strip()
            uf_sigla = uf_match.group(2)
        else:
            # Fallback: buscar apenas (UF) no final
            uf_fallback = re.search(r'\(([A-Z]{2})\)\s*$', endereco)
            if uf_fallback:
                uf_sigla = uf_fallback.group(1)
                # Tentar extrair cidade da parte anterior ao (UF)
                # Buscar padrão - espaços - CIDADE - espaços - (UF)
                cidade_match = re.search(r'-\s*([A-ZÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙÃÕÇ][A-Za-záéíóúâêîôûàèìòùãõç\s]*?)\s*\([A-Z]{2}\)', endereco)
                if cidade_match:
                    cidade = cidade_match.group(1).strip()
                else:
                    # Se não encontrar, buscar qualquer palavra maiúscula antes do (UF)
                    cidade_alt = re.search(r'([A-ZÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙÃÕÇ]+)\s*\([A-Z]{2}\)', endereco)
                    cidade = cidade_alt.group(1).strip() if cidade_alt else ""
            else:
                cidade = ""
                uf_sigla = ""
        
        # 7️⃣ EXTRAIR TELEFONE
        telefone_match = re.search(r'Telefone\s*:\s*(.+?)(?=\nFax|\nEntrega|$)', cell_text, re.IGNORECASE)
        telefone = telefone_match.group(1).strip() if telefone_match else ""
        
        # 8️⃣ EXTRAIR PARÂMETROS PARA BUSCA DE ITENS
        bid_params = None
        if uasg and pregao_match:
            numprp = f"{pregao_match.group(1)}{pregao_match.group(2)}"
            bid_params = {
                'coduasg': uasg,
                'modprp': '5',  # Pregão Eletrônico
                'numprp': numprp,
                'ano': pregao_match.group(2)
            }
        
        # 9️⃣ EXTRAIR LINKS DO HISTÓRICO E ITENS
        historico_link = None
        itens_link = None
        
        # Buscar link do histórico
        historico_a = data_cell.find('a', string=re.compile(r'Histórico de eventos', re.IGNORECASE))
        if historico_a and historico_a.get('onclick'):
            onclick_text = historico_a.get('onclick')
            link_match = re.search(r"'([^']+)'", onclick_text)
            if link_match:
                historico_link = link_match.group(1)
        
        # Buscar botão de itens
        itens_button = data_cell.find('input', {'value': 'Itens e Download'})
        if itens_button and itens_button.get('onclick'):
            onclick_text = itens_button.get('onclick')
            link_match = re.search(r"'([^']+)'", onclick_text)
            if link_match:
                itens_link = link_match.group(1)
        
        # 📋 CONSTRUIR DADOS ESTRUTURADOS
        raw_data = {
            # IDs e identificadores únicos
            'external_id': external_id,
            'uasg': uasg,
            'pregao_numero': pregao_match.group(1) if pregao_match else '',
            'pregao_ano': pregao_match.group(2) if pregao_match else '',
            
            # Informações organizacionais
            'ministry': ministry,                    # Ministério/Governo
            'organ': organ,                         # Órgão/Secretaria
            'entity_name': entity_name,             # Entidade específica
            
            # Dados da licitação
            'object_description': objeto,
            'modality': 'PREGAO_ELETRONICO',
            'status': 'PUBLISHED',
            
            # Localização
            'endereco': endereco,
            'cidade': cidade,
            'uf': uf_sigla,                        # Estado (importante para filtros)
            'telefone': telefone,
            
            # Datas importantes (formato YYYY-MM-DD)
            'publication_date': publication_date,    # Data de publicação
            'opening_date': opening_date,           # Data de abertura (mesmo que publicação)
            'closing_date': closing_date,           # Data de fechamento/entrega
            
            # Datas em formato original (para debug)
            'edital_date_str': edital_date_str,     # Data de publicação original
            'entrega_date_str': entrega_date_str,   # Data de fechamento original
            
            # Links e parâmetros
            'bid_params': bid_params,
            'historico_link': historico_link,
            'itens_link': itens_link,
            
            # Metadados
            'form_name': form_name,
            'extracted_at': datetime.now().isoformat(),
            'extraction_method': 'html_parser',
            'raw_html': cell_html[:1000]  # Primeiros 1000 chars do HTML para debug
        }
        
        return raw_data
        
    except Exception as e:
        print(f"❌ Erro no parse HTML da licitação: {e}")
        return None

def find_advanced_licitacao_blocks(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    🔍 MÉTODO AVANÇADO: Encontrar blocos de licitações usando parser HTML baseado em tags
    Parser HTML direto das estruturas <form> para máxima precisão
    """
    try:
        print("🔍 Buscando licitações usando parser HTML baseado em tags...")
        
        # Buscar todos os forms que contêm licitações
        form_blocks = soup.find_all('form', {'method': 'post'})
        print(f"📋 Forms encontrados: {len(form_blocks)}")
        
        licitacao_data_list = []
        
        for i, form in enumerate(form_blocks):
            try:
                # Cada form representa uma licitação
                form_name = form.get('name', f'Form{i+1}')
                print(f"🔍 Processando form {i+1}: {form_name}")
                
                # Buscar a tabela dentro do form que contém os dados
                table = form.find('table', {'class': 'td'})
                if not table:
                    print(f"⚠️ Form {i+1}: Tabela com class 'td' não encontrada")
                    # Debug: mostrar todas as tabelas encontradas
                    all_tables = form.find_all('table')
                    print(f"   Debug: {len(all_tables)} tabelas encontradas no form")
                    for j, t in enumerate(all_tables):
                        print(f"   Tabela {j}: classes={t.get('class', [])}")
                    continue
                
                # Buscar a célula com classe 'tex3' que contém os dados da licitação
                # Primeira tentativa: buscar por classe tex3 na célula
                data_cell = table.find('td', {'class': 'tex3'})
                
                # Segunda tentativa: buscar por tr com classe tex3 e pegar sua célula
                if not data_cell:
                    tr_tex3 = table.find('tr', {'class': 'tex3'})
                    if tr_tex3:
                        data_cell = tr_tex3.find('td')
                
                # Terceira tentativa: buscar pela segunda célula (que geralmente tem os dados)
                if not data_cell:
                    all_cells = table.find_all('td')
                    if len(all_cells) >= 2:
                        # A segunda célula geralmente tem os dados da licitação
                        data_cell = all_cells[1]
                        print(f"✅ Form {i+1}: Usando segunda célula como dados")
                    else:
                        print(f"⚠️ Form {i+1}: Não há células suficientes")
                        continue
                
                print(f"✅ Form {i+1}: Célula de dados encontrada")
                
                # Extrair dados estruturados do HTML
                licitacao_data = parse_html_licitacao_data(data_cell, form_name, i+1)
                
                if licitacao_data:
                    licitacao_data_list.append(licitacao_data)
                    print(f"✅ Licitação {i+1} extraída via HTML: {licitacao_data.get('external_id', 'N/A')}")
                else:
                    print(f"⚠️ Form {i+1}: Dados não extraídos")
                
            except Exception as e:
                print(f"⚠️ Erro ao processar form {i+1}: {e}")
                continue
        
        print(f"🎯 Parser HTML encontrou {len(licitacao_data_list)} licitações válidas")
        return licitacao_data_list
        
    except Exception as e:
        print(f"❌ Erro no parser HTML: {e}")
        return []

def test_html_parser():
    """Testar o parser HTML com dados reais do ComprasNet"""
    
    # Sample HTML baseado no exemplo real fornecido
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
                        <input type="button" name="itens" value="Itens e Download" class="texField2" onclick="javascript:VisualizarItens(document.Form1,'?coduasg=254445&amp;modprp=5&amp;numprp=901692025');" onmouseover="window.status='Itens da Licitação e Download do Edital';return true;" title="Clique para ver os itens ou fazer o Download do Edital">
                    </td>
                </tr>
            </tbody>
        </table>
    </form>
    
    <form method="post" name="Form9">
        <a name="F9">&nbsp;</a>
        <table border="0" width="100%" class="td" cellpadding="1" cellspacing="1">
            <tbody>
                <tr class="mensagem"><td>9</td></tr>
                <tr bgcolor="#FFFFFF" class="tex3">
                    <td>
                        <b>GOVERNO DO DISTRITO FEDERAL - GDF<br>Secretaria de Estado de Saúde do Distrito Federal<br>Código da UASG: 926119<br></b>
                        <br>
                        <b>Pregão Eletrônico Nº 90139/2025<span class="mensagem"> - (Lei Nº 14.133/2021)</span></b>
                        <br>
                        <b>Objeto:</b>&nbsp;Objeto: Pregão Eletrônico -  Aquisição de insumos necessários para a realização da técnica de MAC-ELISA empregada no diagnóstico sorológico de dengue, zika, chikungunya, febre amarela, agravos esses que se constituem em sérios problemas de saúde pública em sistema de registro de preços, conforme especificações e quantitativos constantes no Anexo I do Edital.
                        <br>
                        <b>Edital a partir de:</b>&nbsp;10/07/2025 das 08:00 às 12:00 Hs e das 13:00 às 17:59 Hs
                        <br>
                        <b>Endereço:</b>&nbsp;Srtvn Qd 701, Conj c Ed. Po 700                                                      -                                          - BRASÍLIA                                 (DF)
                        <br>
                        <b>Telefone:</b>&nbsp;         
                        <br>
                        <b>Fax:</b>&nbsp;               
                        <br>
                        <b>Entrega da Proposta:</b>&nbsp;10/07/2025 às 08:00Hs
                        <br><br>
                        <input type="hidden" name="origem" value="2">
                        <a href="#F9" name="hist_eventos" class="legenda" onclick="javascript:visualizarHistoricoEventos(document.Form9,'?coduasg=926119&amp;modprp=5&amp;numprp=901392025');" title="Visualizar histórico de eventos publicados para a licitação">Histórico de eventos publicados...</a>
                        <br><br>
                        <input type="button" name="itens" value="Itens e Download" class="texField2" onclick="javascript:VisualizarItens(document.Form9,'?coduasg=926119&amp;modprp=5&amp;numprp=901392025');" onmouseover="window.status='Itens da Licitação e Download do Edital';return true;" title="Clique para ver os itens ou fazer o Download do Edital">
                    </td>
                </tr>
            </tbody>
        </table>
    </form>
    """
    
    print("🧪 Testando novo parser HTML do ComprasNet...")
    print("="*60)
    
    # Criar soup do HTML de exemplo
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Testar o novo parser
    licitacao_data_list = find_advanced_licitacao_blocks(soup)
    
    print(f"📊 Licitações encontradas: {len(licitacao_data_list)}")
    print("="*60)
    
    for i, licitacao_data in enumerate(licitacao_data_list, 1):
        print(f"\n🏛️ LICITAÇÃO {i}:")
        print(f"   🆔 ID: {licitacao_data.get('external_id', 'N/A')}")
        print(f"   🏛️ Ministério: {licitacao_data.get('ministry', 'N/A')}")
        print(f"   🏢 Órgão: {licitacao_data.get('organ', 'N/A')}")
        print(f"   🏭 Entidade: {licitacao_data.get('entity_name', 'N/A')}")
        print(f"   📋 UASG: {licitacao_data.get('uasg', 'N/A')}")
        print(f"   📄 Pregão: {licitacao_data.get('pregao_numero', 'N/A')}/{licitacao_data.get('pregao_ano', 'N/A')}")
        print(f"   🎯 Objeto: {licitacao_data.get('object_description', 'N/A')[:100]}...")
        print(f"   📅 Publicação: {licitacao_data.get('publication_date', 'N/A')}")
        print(f"   🚀 Abertura: {licitacao_data.get('opening_date', 'N/A')}")
        print(f"   ⏰ Encerramento: {licitacao_data.get('closing_date', 'N/A')}")
        print(f"   📍 Endereço: {licitacao_data.get('endereco', 'N/A')}")
        print(f"   🏙️ Cidade/UF: {licitacao_data.get('cidade', 'N/A')}/{licitacao_data.get('uf', 'N/A')}")
        print(f"   📞 Telefone: {licitacao_data.get('telefone', 'N/A')}")
        print(f"   🔗 Histórico: {licitacao_data.get('historico_link', 'N/A')}")
        print(f"   📦 Itens: {licitacao_data.get('itens_link', 'N/A')}")
        print(f"   🔧 Params: {licitacao_data.get('bid_params', 'N/A')}")
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