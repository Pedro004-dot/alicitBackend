#!/usr/bin/env python3
"""
Módulo para integração com API do PNCP e operações de banco de dados
"""

import os
import psycopg2
from psycopg2.extras import DictCursor
import datetime
from typing import List, Dict, Any, Tuple
import requests
import time
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# --- Configurações da API PNCP ---
PNCP_BASE_URL_PUBLICACAO = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
PNCP_BASE_URL_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/itens"
PNCP_PAGE_SIZE = 50  # Quantidade de licitações por página
PNCP_MAX_PAGES = 10  # 🔥 AUMENTADO: Mais páginas para busca semanal

# --- Estados brasileiros ---
ESTADOS_BRASIL = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO"
]


def get_db_connection():
    """Conecta ao banco Supabase usando DATABASE_URL"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL não encontrada nas variáveis de ambiente")
    
    return psycopg2.connect(database_url)


def get_all_companies_from_db() -> List[Dict[str, Any]]:
    """Busca todas as empresas do banco de dados"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT id, nome_fantasia, razao_social, cnpj, 
                       descricao_servicos_produtos, setor_atuacao, produtos
                FROM empresas
                ORDER BY nome_fantasia
            """)
            companies = []
            for row in cursor.fetchall():
                # 🔀 CORREÇÃO: Parse correto do campo produtos (JSON -> Lista Python)
                produtos = row['produtos']
                if isinstance(produtos, str):
                    try:
                        import json
                        produtos = json.loads(produtos)
                    except (json.JSONDecodeError, TypeError):
                        produtos = []
                elif produtos is None:
                    produtos = []
                # Se já é uma lista (comportamento esperado do psycopg2 com jsonb), manter como está
                
                companies.append({
                    'id': str(row['id']),
                    'nome': row['nome_fantasia'],
                    'razao_social': row['razao_social'],
                    'cnpj': row['cnpj'],
                    'descricao_servicos_produtos': row['descricao_servicos_produtos'],
                    'setor_atuacao': row['setor_atuacao'],
                    'produtos': produtos  # 🔀 Agora garantidamente uma lista Python
                })
            return companies
    except Exception as e:
        logger.error(f"Erro ao buscar empresas: {e}")
        return []
    finally:
        conn.close()


def get_processed_bid_ids() -> set:
    """Retorna conjunto de IDs de licitações já processadas"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT pncp_id FROM licitacoes")
            return {row[0] for row in cursor.fetchall()}
    finally:
        conn.close()


def fetch_bids_from_pncp(start_date: str, end_date: str, uf: str, page: int) -> Tuple[List[Dict], bool]:
    """
    Busca licitações na API do PNCP para um UF e página específicos.
    Retorna a lista de licitações e um booleano indicando se há mais páginas.
    """
    params = {
        "dataInicial": start_date,
        "dataFinal": end_date,
        "uf": uf,
        "pagina": page,
        "quantidade": PNCP_PAGE_SIZE,
        "codigoModalidadeContratacao": 6  # Pregão eletrônico
    }
    
    try:
        print(f"🔍 Buscando licitações em {uf}, página {page}...")
        response = requests.get(PNCP_BASE_URL_PUBLICACAO, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        bids = data.get("data", [])
        has_more_pages = len(bids) == PNCP_PAGE_SIZE
        print(f"   ✅ Encontradas {len(bids)} licitações em {uf}")
        return bids, has_more_pages
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao buscar licitações do PNCP ({uf}, página {page}): {e}")
        return [], False


def fetch_bid_items_from_pncp(licitacao: Dict) -> List[Dict]:
    """
    Busca os itens detalhados de uma licitação específica.
    """
    orgao_cnpj = licitacao["orgaoEntidade"]["cnpj"]
    ano_compra = licitacao["anoCompra"]
    sequencial_compra = licitacao["sequencialCompra"]

    url = PNCP_BASE_URL_ITENS.format(
        cnpj=orgao_cnpj,
        anoCompra=ano_compra,
        sequencialCompra=sequencial_compra
    )
    
    try:
        print(f"   📋 Buscando itens para licitação {licitacao['numeroControlePNCP']}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        items = response.json()
        print(f"      ✅ {len(items)} itens encontrados")
        return items
    except requests.exceptions.RequestException as e:
        print(f"      ❌ Erro ao buscar itens da licitação {licitacao['numeroControlePNCP']}: {e}")
        return []


def save_bid_to_db(bid: Dict) -> str:
    """Salva uma licitação no banco de dados e retorna o ID"""
    
    # ===== LOG DEBUG: ESTRUTURA RECEBIDA DA API =====
    print(f"\n🔍 === DEBUG: DADOS RECEBIDOS DA API ===")
    print(f"📋 PNCP ID: {bid.get('numeroControlePNCP')}")
    print(f"🏢 Órgão CNPJ: {bid.get('orgaoEntidade', {}).get('cnpj') if bid.get('orgaoEntidade') else 'N/A'}")
    print(f"📍 UF: {bid.get('unidadeOrgao', {}).get('ufSigla') if bid.get('unidadeOrgao') else 'N/A'}")
    print(f"💰 Valor Total Estimado: {bid.get('valorTotalEstimado')}")
    print(f"💸 Valor Total Homologado: {bid.get('valorTotalHomologado')}")
    print(f"🏷️ SRP (Registro de Preços): {bid.get('srp')}")
    print(f"🔗 Link Sistema Origem: {bid.get('linkSistemaOrigem')}")
    print(f"📅 Data Abertura Proposta: {bid.get('dataAberturaProposta')}")
    print(f"⏰ Data Encerramento Proposta: {bid.get('dataEncerramentoProposta')}")
    print(f"🎯 Modo Disputa: {bid.get('modoDisputaNome')} (ID: {bid.get('modoDisputaId')})")
    print(f"📄 Processo: {bid.get('processo')}")
    print(f"🔢 Número Compra: {bid.get('numeroCompra')}")
    
    # Validar e limitar valor total estimado
    valor_total = bid.get("valorTotalEstimado")
    if valor_total is not None:
        try:
            valor_total = float(valor_total)
            # Limitar a 999 bilhões (limite do DECIMAL(15,2))
            if valor_total > 999999999999.99:
                valor_total = 999999999999.99
            elif valor_total < 0:
                valor_total = 0
        except (ValueError, TypeError):
            valor_total = None

    # Validar e limitar valor total homologado
    valor_homologado = bid.get("valorTotalHomologado")
    if valor_homologado is not None:
        try:
            valor_homologado = float(valor_homologado)
            if valor_homologado > 999999999999.99:
                valor_homologado = 999999999999.99
            elif valor_homologado < 0:
                valor_homologado = 0
        except (ValueError, TypeError):
            valor_homologado = None
    
    # Extrair campos aninhados corretamente
    orgao_cnpj = bid.get("orgaoEntidade", {}).get("cnpj") if bid.get("orgaoEntidade") else None
    razao_social = bid.get("orgaoEntidade", {}).get("razaoSocial") if bid.get("orgaoEntidade") else None
    
    # Extrair dados da unidadeOrgao
    unidade_orgao = bid.get("unidadeOrgao", {}) if bid.get("unidadeOrgao") else {}
    uf_sigla = unidade_orgao.get("ufSigla")
    uf_nome = unidade_orgao.get("ufNome")
    nome_unidade = unidade_orgao.get("nomeUnidade")
    municipio_nome = unidade_orgao.get("municipioNome")
    codigo_ibge = unidade_orgao.get("codigoIbge")
    codigo_unidade = unidade_orgao.get("codigoUnidade")
    
    print(f"✅ Valores processados:")
    print(f"   💰 Valor Total (processado): {valor_total}")
    print(f"   💸 Valor Homologado (processado): {valor_homologado}")
    print(f"   🏢 CNPJ (extraído): {orgao_cnpj}")
    print(f"   🏛️ Razão Social (extraído): {razao_social}")
    print(f"   📍 UF Sigla (extraído): {uf_sigla}")
    print(f"   🌎 UF Nome (extraído): {uf_nome}")
    print(f"   🏢 Nome Unidade (extraído): {nome_unidade}")
    print(f"   🏙️ Município (extraído): {municipio_nome}")
    print(f"   🆔 Código IBGE (extraído): {codigo_ibge}")
    print(f"   📋 Objeto: {bid.get('objetoCompra', '')[:100]}...")
    print(f"===========================================\n")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO licitacoes (
                    pncp_id, orgao_cnpj, ano_compra, sequencial_compra,
                    objeto_compra, link_sistema_origem, data_publicacao,
                    valor_total_estimado, uf, status,
                    numero_controle_pncp, numero_compra, processo,
                    valor_total_homologado, data_abertura_proposta, data_encerramento_proposta,
                    modo_disputa_id, modo_disputa_nome, srp, 
                    link_processo_eletronico, justificativa_presencial, razao_social,
                    uf_nome, nome_unidade, municipio_nome, codigo_ibge, codigo_unidade
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (pncp_id) DO UPDATE SET
                    updated_at = NOW(),
                    numero_controle_pncp = EXCLUDED.numero_controle_pncp,
                    numero_compra = EXCLUDED.numero_compra,
                    processo = EXCLUDED.processo,
                    valor_total_homologado = EXCLUDED.valor_total_homologado,
                    data_abertura_proposta = EXCLUDED.data_abertura_proposta,
                    data_encerramento_proposta = EXCLUDED.data_encerramento_proposta,
                    modo_disputa_id = EXCLUDED.modo_disputa_id,
                    modo_disputa_nome = EXCLUDED.modo_disputa_nome,
                    srp = EXCLUDED.srp,
                    link_processo_eletronico = EXCLUDED.link_processo_eletronico,
                    justificativa_presencial = EXCLUDED.justificativa_presencial,
                    razao_social = EXCLUDED.razao_social,
                    uf_nome = EXCLUDED.uf_nome,
                    nome_unidade = EXCLUDED.nome_unidade,
                    municipio_nome = EXCLUDED.municipio_nome,
                    codigo_ibge = EXCLUDED.codigo_ibge,
                    codigo_unidade = EXCLUDED.codigo_unidade
                RETURNING id
            """, (
                bid["numeroControlePNCP"],
                orgao_cnpj,  # Usando variável extraída corretamente
                bid["anoCompra"],
                bid["sequencialCompra"],
                bid["objetoCompra"],
                bid.get("linkSistemaOrigem", ""),
                bid.get("dataPublicacaoPncp"),  # Corrigido: era "dataPublicacao"
                valor_total,
                uf_sigla,  # Usando variável extraída corretamente
                "coletada",
                # Novos campos da API
                bid.get("numeroControlePNCP"),  # Mesmo que pncp_id, mas vamos manter separado
                bid.get("numeroCompra"),
                bid.get("processo"),
                valor_homologado,
                bid.get("dataAberturaProposta"),
                bid.get("dataEncerramentoProposta"),
                bid.get("modoDisputaId"),
                bid.get("modoDisputaNome"),
                bid.get("srp"),  # Booleano - Sistema de Registro de Preços
                bid.get("linkProcessoEletronico"),
                bid.get("justificativaPresencial"),
                razao_social,  # Nova razão social extraída
                # Novos campos da unidadeOrgao
                uf_nome,
                nome_unidade,
                municipio_nome,
                codigo_ibge,
                codigo_unidade
            ))
            result = cursor.fetchone()
            conn.commit()
            return str(result[0])
    finally:
        conn.close()


def save_bid_items_to_db(licitacao_id: str, items: List[Dict]):
    """Salva os itens de uma licitação no banco"""
    if not items:
        return
    
    # ===== LOG DEBUG: ESTRUTURA DOS ITENS DA API 2 =====
    print(f"\n📦 === DEBUG: ITENS RECEBIDOS DA API 2 ===")
    print(f"🆔 Licitação ID: {licitacao_id}")
    print(f"📊 Total de itens: {len(items)}")
    
    if items:
        # Mostrar primeiro item como exemplo
        primeiro_item = items[0]
        print(f"\n📋 Exemplo - Primeiro item:")
        print(f"   🔢 Número: {primeiro_item.get('numeroItem')}")
        print(f"   📝 Descrição: {primeiro_item.get('descricao', '')[:50]}...")
        print(f"   🏷️ Material/Serviço: {primeiro_item.get('materialOuServico')} ({primeiro_item.get('materialOuServicoNome')})")
        print(f"   💰 Valor Unitário: {primeiro_item.get('valorUnitarioEstimado')}")
        print(f"   📏 Quantidade: {primeiro_item.get('quantidade')}")
        print(f"   📐 Unidade: {primeiro_item.get('unidadeMedida')}")
        print(f"   🔍 NCM/NBS: {primeiro_item.get('ncmNbsCodigo')}")
        print(f"   ⚖️ Critério Julgamento: {primeiro_item.get('criterioJulgamentoNome')} (ID: {primeiro_item.get('criterioJulgamentoId')})")
        print(f"   🎯 Tipo Benefício: {primeiro_item.get('tipoBeneficioNome')} (ID: {primeiro_item.get('tipoBeneficio')})")
        print(f"   📊 Situação Item: {primeiro_item.get('situacaoCompraItemNome')} (ID: {primeiro_item.get('situacaoCompraItem')})")
    print(f"==========================================\n")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for i, item in enumerate(items, 1):
                # ===== VALIDAÇÕES DE VALORES =====
                
                # Validar e limitar valor unitário estimado
                valor_unitario = item.get("valorUnitarioEstimado", 0)
                try:
                    valor_unitario = float(valor_unitario) if valor_unitario is not None else 0
                    # Limitar a 999 bilhões (limite do DECIMAL(15,2))
                    if valor_unitario > 999999999999.99:
                        valor_unitario = 999999999999.99
                    elif valor_unitario < 0:
                        valor_unitario = 0
                except (ValueError, TypeError):
                    valor_unitario = 0
                
                # Validar quantidade
                quantidade = item.get("quantidade", 0)
                try:
                    quantidade = float(quantidade) if quantidade is not None else 0
                    if quantidade < 0:
                        quantidade = 0
                except (ValueError, TypeError):
                    quantidade = 0

                # Validar percentual de margem preferencial
                percentual_margem = item.get("percentualMargemPreferenciaNormal")
                if percentual_margem is not None:
                    try:
                        percentual_margem = float(percentual_margem)
                        if percentual_margem < 0 or percentual_margem > 100:
                            percentual_margem = None
                    except (ValueError, TypeError):
                        percentual_margem = None

                # ===== LOG DEBUG PARA ITEM INDIVIDUAL =====
                print(f"      📦 Item {item.get('numeroItem', i)}:")
                print(f"         📝 {item.get('descricao', '')[:40]}...")
                print(f"         🏷️  {item.get('materialOuServico')} - {item.get('materialOuServicoNome')}")
                print(f"         🔍 NCM: {item.get('ncmNbsCodigo')}")
                print(f"         ⚖️  Critério: {item.get('criterioJulgamentoNome')} (ID: {item.get('criterioJulgamentoId')})")
                print(f"         🎯 Benefício: {item.get('tipoBeneficioNome')} (ID: {item.get('tipoBeneficio')})")
                print(f"         📊 Status: {item.get('situacaoCompraItemNome')} (ID: {item.get('situacaoCompraItem')})")
                print(f"         💰 Valor unitário: {valor_unitario}")
                
                cursor.execute("""
                    INSERT INTO licitacao_itens (
                        licitacao_id, numero_item, descricao, quantidade,
                        unidade_medida, valor_unitario_estimado,
                        material_ou_servico, ncm_nbs_codigo,
                        criterio_julgamento_id, criterio_julgamento_nome,
                        tipo_beneficio_id, tipo_beneficio_nome,
                        situacao_item_id, situacao_item_nome,
                        aplicabilidade_margem_preferencia, percentual_margem_preferencia,
                        tem_resultado
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (licitacao_id, numero_item) DO UPDATE SET
                        material_ou_servico = EXCLUDED.material_ou_servico,
                        ncm_nbs_codigo = EXCLUDED.ncm_nbs_codigo,
                        criterio_julgamento_id = EXCLUDED.criterio_julgamento_id,
                        criterio_julgamento_nome = EXCLUDED.criterio_julgamento_nome,
                        tipo_beneficio_id = EXCLUDED.tipo_beneficio_id,
                        tipo_beneficio_nome = EXCLUDED.tipo_beneficio_nome,
                        situacao_item_id = EXCLUDED.situacao_item_id,
                        situacao_item_nome = EXCLUDED.situacao_item_nome,
                        aplicabilidade_margem_preferencia = EXCLUDED.aplicabilidade_margem_preferencia,
                        percentual_margem_preferencia = EXCLUDED.percentual_margem_preferencia,
                        tem_resultado = EXCLUDED.tem_resultado,
                        updated_at = NOW()
                """, (
                    licitacao_id,
                    item.get("numeroItem", i),
                    item.get("descricao", ""),
                    quantidade,
                    item.get("unidadeMedida", ""),
                    valor_unitario,
                    # Novos campos da API 2
                    item.get("materialOuServico"),  # 'M' ou 'S'
                    item.get("ncmNbsCodigo"),  # Código NCM/NBS
                    item.get("criterioJulgamentoId"),  # ID do critério
                    item.get("criterioJulgamentoNome"),  # Nome do critério
                    item.get("tipoBeneficio"),  # ID do tipo de benefício
                    item.get("tipoBeneficioNome"),  # Nome do tipo de benefício
                    item.get("situacaoCompraItem"),  # ID da situação
                    item.get("situacaoCompraItemNome"),  # Nome da situação
                    item.get("aplicabilidadeMargemPreferenciaNormal", False),  # Booleano
                    percentual_margem,  # Percentual validado
                    item.get("temResultado", False)  # Booleano
                ))
            conn.commit()
    finally:
        conn.close()


def save_match_to_db(licitacao_id: str, empresa_id: str, score: float, match_type: str, justificativa: str = ""):
    """Salva um match no banco de dados"""
    # Converter score para float Python nativo se for numpy
    if hasattr(score, 'item'):
        score = float(score.item())
    else:
        score = float(score)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO matches (
                    licitacao_id, empresa_id, score_similaridade, 
                    match_type, justificativa_match
                ) VALUES (
                    (SELECT id FROM licitacoes WHERE pncp_id = %s), 
                    %s, %s, %s, %s
                )
            """, (licitacao_id, empresa_id, score, match_type, justificativa))
            conn.commit()
            print(f"      ✅ Match salvo: Score {score:.3f} - {match_type}")
            if justificativa:
                print(f"         💡 Justificativa: {justificativa}")
    finally:
        conn.close()


def update_bid_status(pncp_id: str, status: str):
    """Atualiza o status de uma licitação"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE licitacoes 
                SET status = %s, updated_at = NOW() 
                WHERE pncp_id = %s
            """, (status, pncp_id))
            conn.commit()
    finally:
        conn.close()


def get_existing_bids_from_db() -> List[Dict[str, Any]]:
    """Busca todas as licitações já armazenadas no banco de dados"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    l.id, l.pncp_id, l.objeto_compra, l.uf, l.valor_total_estimado,
                    l.data_publicacao, l.status, l.created_at
                FROM licitacoes l
                ORDER BY l.created_at DESC
            """)
            bids = []
            for row in cursor.fetchall():
                bids.append({
                    'id': str(row['id']),
                    'pncp_id': row['pncp_id'],
                    'objeto_compra': row['objeto_compra'],
                    'uf': row['uf'],
                    'valor_total_estimado': row['valor_total_estimado'],
                    'data_publicacao': row['data_publicacao'],
                    'status': row['status'],
                    'created_at': row['created_at']
                })
            return bids
    finally:
        conn.close()


def get_bid_items_from_db(licitacao_id: str) -> List[Dict[str, Any]]:
    """Busca os itens de uma licitação específica do banco"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("""
                SELECT numero_item, descricao, quantidade, unidade_medida, valor_unitario_estimado
                FROM licitacao_itens
                WHERE licitacao_id = %s
                ORDER BY numero_item
            """, (licitacao_id,))
            items = []
            for row in cursor.fetchall():
                items.append({
                    'numeroItem': row['numero_item'],
                    'descricao': row['descricao'],
                    'quantidade': row['quantidade'],
                    'unidadeMedida': row['unidade_medida'],
                    'valorUnitarioEstimado': row['valor_unitario_estimado']
                })
            return items
    finally:
        conn.close()


def clear_existing_matches():
    """Remove todos os matches existentes para permitir reavaliação"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM matches")
            conn.commit()
            print("🗑️  Matches anteriores limpos do banco")
    finally:
        conn.close() 