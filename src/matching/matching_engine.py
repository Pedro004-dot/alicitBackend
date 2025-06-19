#!/usr/bin/env python3
"""
Sistema principal de matching de licitações usando API real do PNCP
Busca licitações do dia atual em todos os estados brasileiros e faz matching semântico
"""

import os
import datetime
from typing import Dict, Any
import time
from psycopg2.extras import DictCursor

from src.services.embedding_cache_service import EmbeddingCacheService
from src.services.deduplication_service import DeduplicationService
from src.config.database import db_manager

from .vectorizers import (
    BaseTextVectorizer, OpenAITextVectorizer, VoyageAITextVectorizer,
    HybridTextVectorizer, MockTextVectorizer, calculate_enhanced_similarity
)
from .pncp_api import (
    get_db_connection, get_all_companies_from_db, get_processed_bid_ids,
    fetch_bids_from_pncp, fetch_bid_items_from_pncp, save_bid_to_db,
    save_bid_items_to_db, save_match_to_db, update_bid_status,
    get_existing_bids_from_db, get_bid_items_from_db, clear_existing_matches,
    ESTADOS_BRASIL, PNCP_MAX_PAGES
)

# --- Configurações do Matching ---
SIMILARITY_THRESHOLD_PHASE1 = float(os.getenv('SIMILARITY_THRESHOLD_PHASE1', '0.65'))
SIMILARITY_THRESHOLD_PHASE2 = float(os.getenv('SIMILARITY_THRESHOLD_PHASE2', '0.70'))


def process_daily_bids(vectorizer: BaseTextVectorizer):
    """
    VERSÃO ATUALIZADA: Evita reprocessamento e usa cache inteligente
    """
    print("🚀 Iniciando busca de licitações com ANTI-DUPLICATAS...")
    print(f"🔧 Vectorizador: {type(vectorizer).__name__}")
    print(f"📊 Thresholds: Fase 1 = {SIMILARITY_THRESHOLD_PHASE1} | Fase 2 = {SIMILARITY_THRESHOLD_PHASE2}")
    
    # 🆕 NOVO: Inicializar serviços de cache e deduplicação
    cache_service = EmbeddingCacheService(db_manager)
    dedup_service = DeduplicationService(db_manager, cache_service)
    
    # Data de hoje
    today = datetime.date.today()
    date_str = today.strftime("%Y%m%d")
    
    print(f"📅 Buscando licitações do dia: {today.strftime('%d/%m/%Y')}")
    
    # 1. Carregar empresas e vetorizar
    print("\n🏢 Carregando empresas do banco...")
    companies = get_all_companies_from_db()
    print(f"   ✅ {len(companies)} empresas carregadas")
    if not companies:
        print("❌ Nenhuma empresa encontrada no banco. Cadastre empresas primeiro.")
        return

    # 🆕 NOVO: Vetorizar com cache
    print("🔢 Vetorizando descrições das empresas com CACHE...")
    company_embeddings = []
    cache_hits = 0
    
    for company in companies:
        texto_empresa = company["descricao_servicos_produtos"]
        
        # Tentar buscar no cache primeiro
        cached_embedding = cache_service.get_embedding_from_cache(texto_empresa, "sentence-transformers")
        
        if cached_embedding:
            company_embeddings.append(cached_embedding)
            cache_hits += 1
        else:
            # Gerar novo embedding
            embedding = vectorizer.vectorize(texto_empresa)
            company_embeddings.append(embedding)
            
            # Salvar no cache
            if embedding:
                cache_service.save_embedding_to_cache(texto_empresa, embedding, "sentence-transformers")
    
    print(f"   ⚡ Cache hits: {cache_hits}/{len(companies)} empresas")
        
    # Associar embeddings às empresas
    for i, company in enumerate(companies):
        company["embedding"] = company_embeddings[i] if i < len(company_embeddings) else []
        
    # 2. Buscar licitações do PNCP
    print(f"\n🌐 Buscando licitações do PNCP para todos os estados...")
    processed_bid_ids = get_processed_bid_ids()
    new_bids = []
    total_found = 0
    
    for uf in ESTADOS_BRASIL:
        page = 1
        uf_bids = 0
        
        while page <= PNCP_MAX_PAGES:
            bids, has_more_pages = fetch_bids_from_pncp(date_str, date_str, uf, page)
            
            if not bids:
                break
            
            for bid in bids:
                pncp_id = bid["numeroControlePNCP"]
                if pncp_id not in processed_bid_ids:
                    new_bids.append(bid)
                    uf_bids += 1
                    total_found += 1
            
            if not has_more_pages:
                break
            
            page += 1
            time.sleep(0.5)  # Pausa para não sobrecarregar a API
        
        if uf_bids > 0:
            print(f"   📍 {uf}: {uf_bids} novas licitações")
    
    print(f"\n🎯 Total de novas licitações encontradas: {total_found}")
    
    # 3. 🆕 NOVO: Filtrar licitações já processadas
    print(f"\n🔍 Verificando duplicatas...")
    truly_new_bids = []
    skipped_count = 0
    
    for bid in new_bids:
        licitacao_data = {
            'objeto_compra': bid.get("objetoCompra", ""),
            'pncp_id': bid["numeroControlePNCP"],
            'data_publicacao': bid.get("dataPublicacaoPncp", "")
        }
        
        if dedup_service.should_process_licitacao(bid["numeroControlePNCP"], licitacao_data):
            truly_new_bids.append(bid)
        else:
            skipped_count += 1
            print(f"   ⏭️ Licitação já processada: {bid['numeroControlePNCP']}")
    
    print(f"📊 Licitações filtradas: {len(truly_new_bids)} novas, {skipped_count} já processadas")
    
    if not truly_new_bids:
        print("✅ Nenhuma licitação nova para processar hoje.")
        return
    
    # 4. 🆕 NOVO: Processar licitações com cache de embeddings
    print(f"\n⚡ Processando {len(truly_new_bids)} licitações com CACHE...")
    matches_encontrados = 0
    embedding_cache_hits = 0
    estatisticas = {
        'total_processadas': 0,
        'com_matches': 0,
        'sem_matches': 0,
        'matches_fase1_apenas': 0,
        'matches_fase2': 0
    }
    
    for i, bid in enumerate(truly_new_bids, 1):
        pncp_id = bid["numeroControlePNCP"]
        objeto_compra = bid.get("objetoCompra", "")
        
        print(f"\n[{i}/{len(truly_new_bids)}] 🔍 Processando: {pncp_id}")
        print(f"   📝 Objeto: {objeto_compra[:100]}...")
        
        if not objeto_compra:
            print("   ⚠️  Objeto da compra vazio, pulando...")
            continue
        
        # Salvar licitação no banco
        licitacao_id = save_bid_to_db(bid)
        
        # Buscar itens da licitação
        items = fetch_bid_items_from_pncp(bid)
        if items:
            save_bid_items_to_db(licitacao_id, items)
        
        # 🆕 NOVO: Vetorizar com cache
        cached_bid_embedding = cache_service.get_embedding_from_cache(objeto_compra, "sentence-transformers")
        
        if cached_bid_embedding:
            bid_embedding = cached_bid_embedding
            embedding_cache_hits += 1
            print(f"   ⚡ Embedding encontrado no cache")
        else:
            bid_embedding = vectorizer.vectorize(objeto_compra)
            if bid_embedding:
                cache_service.save_embedding_to_cache(objeto_compra, bid_embedding, "sentence-transformers")
                print(f"   🆕 Novo embedding gerado e cacheado")
        
        if not bid_embedding:
            print("   ❌ Erro ao vetorizar objeto da compra")
            continue
        
        estatisticas['total_processadas'] += 1
        
        # FASE 1: Matching do objeto completo
        potential_matches = []
        print("   🔍 FASE 1 - Análise semântica do objeto da compra:")
        
        for company in companies:
            if not company.get("embedding"):
                print(f"      ⚠️  {company['nome']}: Sem embedding, pulando...")
                continue
            
            # Usar similaridade aprimorada
            score, justificativa = calculate_enhanced_similarity(
                bid_embedding, 
                company["embedding"], 
                objeto_compra, 
                company["descricao_servicos_produtos"]
            )
            
            print(f"      🏢 {company['nome']}: Score = {score:.3f} (threshold: {SIMILARITY_THRESHOLD_PHASE1})")
            print(f"         💡 {justificativa}")
            
            if score >= SIMILARITY_THRESHOLD_PHASE1:
                potential_matches.append((company, score, justificativa))
                print(f"         ✅ POTENCIAL MATCH!")
        
        if potential_matches:
            print(f"   🎯 {len(potential_matches)} potenciais matches encontrados!")
            estatisticas['com_matches'] += 1
            
            # FASE 2: Refinamento com itens (se disponível)
            if items:
                print(f"   📋 {len(items)} itens encontrados. Iniciando FASE 2...")
                item_descriptions = [item.get("descricao", "") for item in items]
                item_embeddings = vectorizer.batch_vectorize(item_descriptions)
                
                for company, score_fase1, justificativa_fase1 in potential_matches:
                    item_matches = 0
                    total_item_score = 0.0
                    best_item_matches = []
                    
                    print(f"\n      🏢 Analisando {company['nome']} (Score Fase 1: {score_fase1:.3f})")
                    
                    for idx, item_embedding in enumerate(item_embeddings):
                        if not item_embedding:
                            continue
                        
                        item_score, item_justificativa = calculate_enhanced_similarity(
                            item_embedding, 
                            company["embedding"],
                            item_descriptions[idx],
                            company["descricao_servicos_produtos"]
                        )
                        
                        item_desc = item_descriptions[idx][:50] + "..." if len(item_descriptions[idx]) > 50 else item_descriptions[idx]
                        
                        print(f"         📋 Item {idx+1}: '{item_desc}'")
                        print(f"             📊 Score: {item_score:.3f} (threshold: {SIMILARITY_THRESHOLD_PHASE2})")
                        print(f"             💡 {item_justificativa}")
                        
                        if item_score >= SIMILARITY_THRESHOLD_PHASE2:
                            item_matches += 1
                            total_item_score += item_score
                            best_item_matches.append((item_desc, item_score))
                            print(f"             ✅ MATCH no item!")
                        else:
                            print(f"             ❌ Não passou no threshold")
                    
                    if item_matches > 0:
                        final_score = (score_fase1 + (total_item_score / item_matches)) / 2
                        
                        # Justificativa combinada
                        combined_justificativa = f"Fase 1: {justificativa_fase1} | Fase 2: {item_matches} itens matched (média: {total_item_score/item_matches:.3f})"
                        
                        save_match_to_db(pncp_id, company["id"], final_score, "objeto_e_itens", combined_justificativa)
                        matches_encontrados += 1
                        estatisticas['matches_fase2'] += 1
                        
                        print(f"\n      🎯 MATCH FINAL! {company['nome']} - Score: {final_score:.3f}")
                        print(f"         📋 Melhores itens: {', '.join([f'{desc}({score:.2f})' for desc, score in best_item_matches[:2]])}")
                    else:
                        print(f"\n      ❌ {company['nome']}: Nenhum item passou no threshold da Fase 2")
            else:
                print("   📋 Sem itens - usando apenas Fase 1")
                # Sem itens, usar apenas Fase 1
                for company, score, justificativa in potential_matches:
                    save_match_to_db(pncp_id, company["id"], score, "objeto_completo", 
                                    f"Apenas Fase 1: {justificativa}")
                    matches_encontrados += 1
                    estatisticas['matches_fase1_apenas'] += 1
                    print(f"      🎯 MATCH! {company['nome']} - Score: {score:.3f}")
        else:
            print("   ❌ Nenhum potencial match na Fase 1")
            estatisticas['sem_matches'] += 1
        
        # 🆕 NOVO: Marcar como processada
        licitacao_data = {
            'objeto_compra': objeto_compra,
            'pncp_id': pncp_id,
            'data_publicacao': bid.get("dataPublicacaoPncp", "")
        }
        dedup_service.mark_licitacao_processed(pncp_id, licitacao_data)
        
        # Atualizar status da licitação
        update_bid_status(pncp_id, "processada")
        
        # Pausa entre processamentos
        time.sleep(0.2)
    
    # Relatório final com estatísticas de cache
    print(f"\n📊 ESTATÍSTICAS FINAIS:")
    print(f"   ⚡ Embedding cache hits: {embedding_cache_hits}/{len(truly_new_bids)}")
    print(f"   🎯 Total de matches: {matches_encontrados}")
    
    # Exibir stats do cache
    cache_stats = cache_service.get_cache_stats()
    print(f"   📈 Cache stats: {cache_stats}")
    
    # Relatório final
    _print_final_report(matches_encontrados, estatisticas)


def reevaluate_existing_bids(vectorizer: BaseTextVectorizer, clear_matches: bool = True):
    """
    Reavalia todas as licitações existentes no banco contra as empresas cadastradas
    VERSÃO ATUALIZADA com cache inteligente de embeddings
    """
    print("=" * 80)
    print("🔄 REAVALIAÇÃO COM CACHE DE EMBEDDINGS")
    print("=" * 80)
    print(f"🔧 Vectorizador: {type(vectorizer).__name__}")
    print(f"📊 Thresholds: Fase 1 = {SIMILARITY_THRESHOLD_PHASE1} | Fase 2 = {SIMILARITY_THRESHOLD_PHASE2}")
    
    # 🆕 NOVO: Inicializar serviço de cache
    cache_service = EmbeddingCacheService(db_manager)
    
    if clear_matches:
        clear_existing_matches()

    # 1. Carregar empresas e vetorizar com cache
    print("\n🏢 Carregando empresas do banco...")
    companies = get_all_companies_from_db()
    print(f"   ✅ {len(companies)} empresas carregadas")
    
    if not companies:
        print("❌ Nenhuma empresa encontrada no banco. Cadastre empresas primeiro.")
        return
    
    # 🆕 NOVO: Vetorizar descrições das empresas com cache
    print("🔢 Vetorizando descrições das empresas com CACHE...")
    company_embeddings = []
    cache_hits = 0
    
    for company in companies:
        texto_empresa = company["descricao_servicos_produtos"]
        
        # Tentar buscar no cache primeiro
        cached_embedding = cache_service.get_embedding_from_cache(texto_empresa, "sentence-transformers")
        
        if cached_embedding:
            company_embeddings.append(cached_embedding)
            cache_hits += 1
            print(f"   ⚡ {company['nome']}: Cache hit")
        else:
            # Gerar novo embedding
            embedding = vectorizer.vectorize(texto_empresa)
            company_embeddings.append(embedding)
            
            # Salvar no cache
            if embedding:
                cache_service.save_embedding_to_cache(texto_empresa, embedding, "sentence-transformers")
                print(f"   🆕 {company['nome']}: Novo embedding cacheado")
            else:
                print(f"   ⚠️  {company['nome']}: Falha na vetorização")
    
    print(f"   📊 Cache hits: {cache_hits}/{len(companies)} empresas")
    
    for i, company in enumerate(companies):
        company["embedding"] = company_embeddings[i] if i < len(company_embeddings) else []
    
    # 2. Carregar licitações existentes
    print(f"\n📄 Carregando licitações do banco...")
    existing_bids = get_existing_bids_from_db()
    print(f"   ✅ {len(existing_bids)} licitações encontradas")
    
    if not existing_bids:
        print("❌ Nenhuma licitação encontrada no banco.")
        return
    
    # 3. Processar cada licitação com cache
    print(f"\n⚡ Iniciando reavaliação com CACHE DE EMBEDDINGS...")
    matches_encontrados = 0
    embedding_cache_hits = 0
    estatisticas = {
        'total_processadas': 0,
        'com_matches': 0,
        'sem_matches': 0,
        'matches_fase1_apenas': 0,
        'matches_fase2': 0,
        'vetorizacao_falhou': 0
    }
    
    for i, bid in enumerate(existing_bids, 1):
        objeto_compra = bid['objeto_compra']
        pncp_id = bid['pncp_id']
        
        print(f"\n[{i}/{len(existing_bids)}] 🔍 Reavaliando: {pncp_id}")
        print(f"   📝 Objeto: {objeto_compra[:100]}...")
        print(f"   📍 UF: {bid['uf']} | 💰 Valor: R$ {bid['valor_total_estimado'] or 'N/A'}")
        
        if not objeto_compra:
            print("   ⚠️  Objeto da compra vazio, pulando...")
            continue
        
        # 🆕 NOVO: Vetorizar objeto da compra com cache
        cached_bid_embedding = cache_service.get_embedding_from_cache(objeto_compra, "sentence-transformers")
        
        if cached_bid_embedding:
            bid_embedding = cached_bid_embedding
            embedding_cache_hits += 1
            print(f"   ⚡ Embedding encontrado no cache")
        else:
            bid_embedding = vectorizer.vectorize(objeto_compra)
            if bid_embedding:
                cache_service.save_embedding_to_cache(objeto_compra, bid_embedding, "sentence-transformers")
                print(f"   🆕 Novo embedding gerado e cacheado")
        
        if not bid_embedding:
            print("   ❌ Erro ao vetorizar objeto da compra")
            estatisticas['vetorizacao_falhou'] += 1
            continue
        
        print(f"   🔢 Embedding: {len(bid_embedding)} dimensões")
        estatisticas['total_processadas'] += 1
        
        # FASE 1: Matching do objeto completo
        potential_matches = []
        print("   🔍 FASE 1 - Análise semântica do objeto da compra:")
        
        for company in companies:
            if not company.get("embedding"):
                print(f"      ⚠️  {company['nome']}: Sem embedding, pulando...")
                continue
            
            # Usar similaridade aprimorada
            score, justificativa = calculate_enhanced_similarity(
                bid_embedding, 
                company["embedding"], 
                objeto_compra, 
                company["descricao_servicos_produtos"]
            )
            
            print(f"      🏢 {company['nome']}: Score = {score:.3f} (threshold: {SIMILARITY_THRESHOLD_PHASE1})")
            print(f"         💡 {justificativa}")
            
            if score >= SIMILARITY_THRESHOLD_PHASE1:
                potential_matches.append((company, score, justificativa))
                print(f"         ✅ POTENCIAL MATCH!")
        
        if potential_matches:
            print(f"   🎯 {len(potential_matches)} potenciais matches encontrados!")
            estatisticas['com_matches'] += 1
            
            # Buscar itens da licitação
            items = get_bid_items_from_db(bid['id'])
            
            # FASE 2: Refinamento com itens (se disponível)
            if items:
                print(f"   📋 {len(items)} itens encontrados. Iniciando FASE 2...")
                item_descriptions = [item.get("descricao", "") for item in items]
                item_embeddings = vectorizer.batch_vectorize(item_descriptions)
                
                for company, score_fase1, justificativa_fase1 in potential_matches:
                    item_matches = 0
                    total_item_score = 0.0
                    best_item_matches = []
                    
                    print(f"\n      🏢 Analisando {company['nome']} (Score Fase 1: {score_fase1:.3f})")
                    
                    for idx, item_embedding in enumerate(item_embeddings):
                        if not item_embedding:
                            continue
                        
                        item_score, item_justificativa = calculate_enhanced_similarity(
                            item_embedding, 
                            company["embedding"],
                            item_descriptions[idx],
                            company["descricao_servicos_produtos"]
                        )
                        
                        item_desc = item_descriptions[idx][:50] + "..." if len(item_descriptions[idx]) > 50 else item_descriptions[idx]
                        
                        print(f"         📋 Item {idx+1}: '{item_desc}'")
                        print(f"             📊 Score: {item_score:.3f} (threshold: {SIMILARITY_THRESHOLD_PHASE2})")
                        print(f"             💡 {item_justificativa}")
                        
                        if item_score >= SIMILARITY_THRESHOLD_PHASE2:
                            item_matches += 1
                            total_item_score += item_score
                            best_item_matches.append((item_desc, item_score))
                            print(f"             ✅ MATCH no item!")
                        else:
                            print(f"             ❌ Não passou no threshold")
                    
                    if item_matches > 0:
                        final_score = (score_fase1 + (total_item_score / item_matches)) / 2
                        
                        # Justificativa combinada
                        combined_justificativa = f"Reavaliação - Fase 1: {justificativa_fase1} | Fase 2: {item_matches} itens matched (média: {total_item_score/item_matches:.3f})"
                        
                        save_match_to_db(pncp_id, company["id"], final_score, "objeto_e_itens", combined_justificativa)
                        matches_encontrados += 1
                        estatisticas['matches_fase2'] += 1
                        
                        print(f"\n      🎯 MATCH FINAL! {company['nome']} - Score: {final_score:.3f}")
                        print(f"         📋 Melhores itens: {', '.join([f'{desc}({score:.2f})' for desc, score in best_item_matches[:2]])}")
                    else:
                        print(f"\n      ❌ {company['nome']}: Nenhum item passou no threshold da Fase 2")
            else:
                print("   📋 Sem itens - usando apenas Fase 1")
                # Sem itens, usar apenas Fase 1
                for company, score, justificativa in potential_matches:
                    save_match_to_db(pncp_id, company["id"], score, "objeto_completo", 
                                    f"Reavaliação - Apenas Fase 1: {justificativa}")
                    matches_encontrados += 1
                    estatisticas['matches_fase1_apenas'] += 1
                    print(f"      🎯 MATCH! {company['nome']} - Score: {score:.3f}")
        else:
            print("   ❌ Nenhum potencial match na Fase 1")
            estatisticas['sem_matches'] += 1
        
        print("-" * 60)
    
    # Relatório final detalhado com estatísticas de cache
    print(f"\n📊 ESTATÍSTICAS DE CACHE:")
    print(f"   ⚡ Embedding cache hits: {embedding_cache_hits}/{len(existing_bids)}")
    
    # Exibir stats do cache
    cache_stats = cache_service.get_cache_stats()
    print(f"   📈 Cache stats: {cache_stats}")
    
    result = _print_detailed_final_report(matches_encontrados, estatisticas)
    
    print(f"🚀 Processo de reavaliação finalizado com sucesso!")
    return result


def _print_final_report(matches_encontrados: int, estatisticas: Dict[str, int]):
    """Imprime relatório final resumido"""
    print(f"\n" + "="*80)
    print(f"🎉 PROCESSAMENTO CONCLUÍDO!")
    print(f"="*80)
    print(f"📊 ESTATÍSTICAS:")
    print(f"   🔍 Licitações processadas: {estatisticas['total_processadas']}")
    print(f"   🎯 Licitações com matches: {estatisticas['com_matches']}")
    print(f"   ❌ Licitações sem matches: {estatisticas['sem_matches']}")
    print(f"   📋 Matches apenas Fase 1: {estatisticas['matches_fase1_apenas']}")
    print(f"   🔬 Matches com Fase 2: {estatisticas['matches_fase2']}")
    print(f"   🎯 Total de matches: {matches_encontrados}")
    
    if estatisticas['total_processadas'] > 0:
        taxa_sucesso = (estatisticas['com_matches'] / estatisticas['total_processadas']) * 100
        print(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")


def _print_detailed_final_report(matches_encontrados: int, estatisticas: Dict[str, int]) -> Dict[str, Any]:
    """Imprime relatório final detalhado e retorna resultado"""
    print(f"\n" + "="*80)
    print(f"🎉 REAVALIAÇÃO CONCLUÍDA!")
    print(f"="*80)
    print(f"📊 ESTATÍSTICAS DETALHADAS:")
    print(f"   🔍 Licitações processadas: {estatisticas['total_processadas']}")
    print(f"   ❌ Falhas na vetorização: {estatisticas['vetorizacao_falhou']}")
    print(f"   🎯 Licitações com matches: {estatisticas['com_matches']}")
    print(f"   ❌ Licitações sem matches: {estatisticas['sem_matches']}")
    print(f"   📋 Matches apenas Fase 1: {estatisticas['matches_fase1_apenas']}")
    print(f"   🔬 Matches com Fase 2: {estatisticas['matches_fase2']}")
    print(f"   🎯 Total de matches: {matches_encontrados}")
    
    if estatisticas['total_processadas'] > 0:
        taxa_sucesso = (estatisticas['com_matches'] / estatisticas['total_processadas']) * 100
        print(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    # Mostrar resumo dos matches
    if matches_encontrados > 0:
        print(f"\n📋 Verificando matches salvos...")
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        l.pncp_id, l.objeto_compra, e.nome_fantasia,
                        m.score_similaridade, m.match_type, m.justificativa_match, m.data_match
                    FROM matches m
                    JOIN licitacoes l ON m.licitacao_id = l.id
                    JOIN empresas e ON m.empresa_id = e.id
                    ORDER BY m.score_similaridade DESC
                    LIMIT 10
                """)
                matches = cursor.fetchall()
                
                print(f"   ✅ Top 10 matches confirmados no banco:")
                for match in matches:
                    print(f"      🎯 {match['nome_fantasia']} ↔ {match['pncp_id']}")
                    print(f"         📊 Score: {match['score_similaridade']:.3f} | Tipo: {match['match_type']}")
                    print(f"         💡 {match['justificativa_match']}")
                    print(f"         📝 {match['objeto_compra'][:80]}...")
                    print()
        finally:
            conn.close()
    
    return {
        'matches_encontrados': matches_encontrados,
        'estatisticas': estatisticas
    }


if __name__ == "__main__":
    print("=" * 80)
    print("🤖 SISTEMA DE MATCHING APRIMORADO - LICITAÇÕES PNCP")
    print("=" * 80)
    
    # Menu de configuração do vectorizer
    print("\n🔧 Escolha o sistema de vetorização:")
    print("1. Sistema Híbrido (VoyageAI + OpenAI fallback) - RECOMENDADO")
    print("2. VoyageAI (otimizado para Railway)")
    print("3. OpenAI Embeddings (alta qualidade, requer API key)")
    print("4. MockTextVectorizer (básico, apenas para teste)")
    
    vectorizer_choice = input("\nEscolha o vetorizador (1-4, padrão: 1): ").strip() or "1"
    
    # Configurar vectorizer
    try:
        if vectorizer_choice == "1":
            print("\n🔥 Inicializando Sistema Híbrido...")
            vectorizer = HybridTextVectorizer()
        elif vectorizer_choice == "2":
            print("\n🔥 Inicializando VoyageAI...")
            vectorizer = VoyageAITextVectorizer()
        elif vectorizer_choice == "3":
            print("\n🔥 Inicializando OpenAI Embeddings...")
            vectorizer = OpenAITextVectorizer()
        
        else:
            print(f"\n❌ Opção inválida '{vectorizer_choice}'. Usando Sistema Híbrido...")
            vectorizer = HybridTextVectorizer()
    except Exception as e:
        print(f"\n❌ Erro ao inicializar vetorizador: {e}")
        print("🔄 Tentando fallback para MockTextVectorizer...")
        try:
            vectorizer = MockTextVectorizer()
        except Exception as e2:
            print(f"❌ Erro crítico: {e2}")
            exit(1)
    
    # Menu de operações
    print("\n📋 Operações disponíveis:")
    print("1. Buscar novas licitações do PNCP (process_daily_bids)")
    print("2. Reavaliar licitações existentes no banco (reevaluate_existing_bids)")
    print("3. Teste rápido de vetorização")
    
    opcao = input("\nEscolha uma operação (1-3, padrão: 2): ").strip() or "2"
    
    try:
        if opcao == "1":
            print("\n🌐 Executando busca de novas licitações...")
            process_daily_bids(vectorizer)
        elif opcao == "2":
            print("\n🔄 Executando reavaliação de licitações existentes...")
            result = reevaluate_existing_bids(vectorizer, clear_matches=True)
            
            # Mostrar resultados finais
            if result:
                print(f"\n📈 RESULTADO FINAL:")
                print(f"   🎯 Matches encontrados: {result['matches_encontrados']}")
                print(f"   📊 Taxa de sucesso: {result['estatisticas']['com_matches']/result['estatisticas']['total_processadas']*100 if result['estatisticas']['total_processadas'] > 0 else 0:.1f}%")
        elif opcao == "3":
            print("\n🧪 Executando teste rápido de vetorização...")
            
            # Teste com textos exemplo
            test_texts = [
                "Contratação de serviços de tecnologia da informação",
                "Aquisição de equipamentos de informática e suprimentos",
                "Serviços de manutenção de impressoras e equipamentos",
                "Fornecimento de papel A4 e material de escritório"
            ]
            
            print("   📝 Textos de teste:")
            for i, text in enumerate(test_texts, 1):
                print(f"      {i}. {text}")
            
            print("\n   🔄 Vetorizando...")
            embeddings = vectorizer.batch_vectorize(test_texts)
            
            if embeddings:
                print(f"   ✅ Sucesso! {len(embeddings)} embeddings gerados")
                print(f"   📏 Dimensões: {len(embeddings[0])} cada")
                
                # Teste de similaridade
                if len(embeddings) >= 2:
                    from .vectorizers import calculate_cosine_similarity
                    sim = calculate_cosine_similarity(embeddings[0], embeddings[1])
                    print(f"   🔍 Similaridade entre textos 1 e 2: {sim:.3f}")
                    
                    # Teste de similaridade aprimorada
                    sim_enhanced, justificativa = calculate_enhanced_similarity(
                        embeddings[0], embeddings[1], test_texts[0], test_texts[1]
                    )
                    print(f"   🔍 Similaridade aprimorada: {sim_enhanced:.3f}")
                    print(f"   💡 Justificativa: {justificativa}")
            else:
                print("   ❌ Falha na vetorização")
        else:
            print("❌ Opção inválida. Executando reavaliação por padrão...")
            reevaluate_existing_bids(vectorizer, clear_matches=True)
        
        print(f"\n✅ Processo finalizado com sucesso!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante execução: {e}")
        import traceback
        traceback.print_exc() 