#!/usr/bin/env python3
"""
Sistema principal de matching de licitações usando API real do PNCP
Busca licitações do dia atual em todos os estados brasileiros e faz matching semântico
VERSÃO OTIMIZADA: Cache apenas Redis LOCAL para máxima performance
"""

import os
import datetime
from typing import Dict, Any
import time
from psycopg2.extras import DictCursor

from services.embedding_cache_service import EmbeddingCacheService
from services.deduplication_service import DeduplicationService
from config.database import db_manager

from .vectorizers import (
    BaseTextVectorizer, BrazilianTextVectorizer, OpenAITextVectorizer, VoyageAITextVectorizer,
    HybridTextVectorizer, MockTextVectorizer, calculate_enhanced_similarity
)
from .llm_match_validator import LLMMatchValidator
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


def process_daily_bids(vectorizer: BaseTextVectorizer, enable_llm_validation: bool = True):
    """
    VERSÃO REDIS LOCAL: Cache otimizado apenas com Redis local + Validação LLM
    """
    print("🚀 Iniciando busca de licitações com CACHE REDIS LOCAL + VALIDAÇÃO LLM...")
    print(f"🔧 Vectorizador: {type(vectorizer).__name__}")
    print(f"📊 Thresholds: Fase 1 = {SIMILARITY_THRESHOLD_PHASE1} | Fase 2 = {SIMILARITY_THRESHOLD_PHASE2}")
    print(f"🤖 Validação LLM: {'ATIVADA' if enable_llm_validation else 'DESATIVADA'}")
    
    # 🔥 NOVO: Cache apenas Redis local
    cache_service = EmbeddingCacheService(db_manager)
    dedup_service = DeduplicationService(db_manager, cache_service)
    
    # 🤖 Inicializar validador LLM
    llm_validator = None
    if enable_llm_validation:
        llm_validator = LLMMatchValidator()
        print(f"🤖 Validador LLM configurado (threshold: {llm_validator.HIGH_SCORE_THRESHOLD:.1%})")
    
    # Data de hoje
    today = datetime.date.today()
    date_str = today.strftime("%Y%m%d")
    
    print(f"📅 Buscando licitações do dia: {today.strftime('%d/%m/%Y')}")
    
    # 1. Carregar empresas 
    print("\n🏢 Carregando empresas do banco...")
    companies = get_all_companies_from_db()
    print(f"   ✅ {len(companies)} empresas carregadas")
    if not companies:
        print("❌ Nenhuma empresa encontrada no banco. Cadastre empresas primeiro.")
        return

    # 🔥 OTIMIZAÇÃO: Vetorizar empresas com cache em lote
    print("🔢 Vetorizando descrições das empresas com CACHE REDIS LOCAL...")
    _vectorize_companies_with_cache(companies, cache_service, vectorizer)
        
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
    
    # 3. Filtrar licitações já processadas
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
    
    print(f"📊 Licitações filtradas: {len(truly_new_bids)} novas, {skipped_count} já processadas")
    
    if not truly_new_bids:
        print("✅ Nenhuma licitação nova para processar hoje.")
        return
    
    # 4. 🔥 OTIMIZAÇÃO: Processar licitações com cache em lote Redis
    print(f"\n⚡ Processando {len(truly_new_bids)} licitações com CACHE REDIS LOCAL...")
    matches_encontrados = 0
    redis_cache_hits = 0
    estatisticas = {
        'total_processadas': 0,
        'com_matches': 0,
        'sem_matches': 0,
        'matches_fase1_apenas': 0,
        'matches_fase2': 0,
        'llm_validations_count': 0,
        'llm_approved': 0,
        'llm_rejected': 0
    }
    
    # 🔥 PRÉ-CACHE: Buscar embeddings de todas as licitações em lote
    bid_texts = [bid.get("objetoCompra", "") for bid in truly_new_bids if bid.get("objetoCompra")]
    cached_bid_embeddings = cache_service.batch_get_embeddings_from_cache(bid_texts)
    redis_cache_hits = len(cached_bid_embeddings)
    
    print(f"   ⚡ Cache Redis: {redis_cache_hits}/{len(bid_texts)} embeddings encontrados")
    
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
        
        # 🔥 CACHE: Usar embedding do cache ou gerar novo
        if objeto_compra in cached_bid_embeddings:
            bid_embedding = cached_bid_embeddings[objeto_compra]
            print(f"   ⚡ Embedding do cache Redis")
        else:
            bid_embedding = vectorizer.vectorize(objeto_compra)
            if bid_embedding:
                cache_service.save_embedding_to_cache(objeto_compra, bid_embedding)
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
                continue
            
            score, justificativa = calculate_enhanced_similarity(
                bid_embedding, 
                company["embedding"], 
                objeto_compra, 
                company["descricao_servicos_produtos"]
            )
            
            print(f"      🏢 {company['nome']}: Score = {score:.3f}")
            
            if score >= SIMILARITY_THRESHOLD_PHASE1:
                # 🤖 VALIDAÇÃO LLM PARA SCORES ALTOS
                should_accept_match = True
                final_score = score
                final_justificativa = justificativa
                
                if llm_validator and llm_validator.should_validate_with_llm(score):
                    print(f"         🤖 VALIDAÇÃO LLM (score {score:.1%} > {llm_validator.HIGH_SCORE_THRESHOLD:.1%})")
                    
                    validation = llm_validator.validate_match(
                        empresa_nome=company['nome'],
                        empresa_descricao=company['descricao_servicos_produtos'],
                        licitacao_objeto=objeto_compra,
                        pncp_id=pncp_id,
                        similarity_score=score
                    )
                    
                    estatisticas['llm_validations_count'] += 1
                    
                    if validation['is_valid']:
                        print(f"         🎯 LLM APROVOU! Confiança: {validation['confidence']:.1%}")
                        final_score = validation['confidence']
                        final_justificativa += f" | LLM: {validation['reasoning'][:100]}..."
                        estatisticas['llm_approved'] += 1
                    else:
                        print(f"         🚫 LLM REJEITOU: {validation['reasoning'][:80]}...")
                        should_accept_match = False
                        estatisticas['llm_rejected'] += 1
                
                if should_accept_match:
                    potential_matches.append((company, final_score, final_justificativa))
                    print(f"         ✅ POTENCIAL MATCH ACEITO!")
                else:
                    print(f"         ❌ Rejeitado pela validação LLM")
        
        if potential_matches:
            print(f"   🎯 {len(potential_matches)} potenciais matches encontrados!")
            estatisticas['com_matches'] += 1
            
            # FASE 2: Refinamento com itens (se disponível)
            if items:
                print(f"   📋 {len(items)} itens encontrados. Iniciando FASE 2...")
                _process_phase2_matching(items, potential_matches, pncp_id, cache_service, vectorizer, estatisticas)
            else:
                print("   📋 Sem itens - usando apenas Fase 1")
                _process_phase1_only_matching(potential_matches, pncp_id, estatisticas)
                
            matches_encontrados += len(potential_matches)
        else:
            print("   ❌ Nenhum potencial match na Fase 1")
            estatisticas['sem_matches'] += 1
        
        # Marcar como processada
        licitacao_data = {
            'objeto_compra': objeto_compra,
            'pncp_id': pncp_id,
            'data_publicacao': bid.get("dataPublicacaoPncp", "")
        }
        dedup_service.mark_licitacao_processed(pncp_id, licitacao_data)
        update_bid_status(pncp_id, "processada")
        
        time.sleep(0.1)  # Pausa menor devido ao cache otimizado
    
    # Relatório final
    print(f"\n📊 ESTATÍSTICAS REDIS CACHE:")
    print(f"   ⚡ Cache hits Redis: {redis_cache_hits}/{len(bid_texts)}")
    
    # Exibir stats do cache
    cache_stats = cache_service.get_cache_stats()
    if cache_stats.get('status') == 'active':
        print(f"   📈 Total embeddings em cache: {cache_stats['cache_stats']['match_keys']}")
        print(f"   🎯 Eficiência do cache: {cache_stats['performance']['cache_efficiency']}")
    
    _print_final_report(matches_encontrados, estatisticas)


def _vectorize_companies_with_cache(companies, cache_service, vectorizer):
    """🔥 OTIMIZAÇÃO: Vetorizar empresas usando cache em lote Redis"""
    company_texts = [company["descricao_servicos_produtos"] for company in companies]
    
    # Buscar embeddings em lote do Redis
    cached_embeddings = cache_service.batch_get_embeddings_from_cache(company_texts)
    cache_hits = len(cached_embeddings)
    
    # Processar empresas que não estão no cache
    texts_to_generate = []
    companies_to_update = []
    
    for i, company in enumerate(companies):
        texto_empresa = company["descricao_servicos_produtos"]
        
        if texto_empresa in cached_embeddings:
            company["embedding"] = cached_embeddings[texto_empresa]
        else:
            # Marcar para gerar embedding
            texts_to_generate.append(texto_empresa)
            companies_to_update.append(company)
    
    print(f"   ⚡ Cache Redis hits: {cache_hits}/{len(companies)} empresas")
    
    # Gerar embeddings faltantes em lote
    if texts_to_generate:
        print(f"   🔄 Gerando {len(texts_to_generate)} novos embeddings...")
        
        new_embeddings = vectorizer.batch_vectorize(texts_to_generate)
        
        if new_embeddings:
            # Salvar novos embeddings no cache em lote
            texts_and_embeddings = list(zip(texts_to_generate, new_embeddings))
            cache_service.batch_save_embeddings_to_cache(texts_and_embeddings)
            
            # Atribuir aos objetos empresa
            for i, company in enumerate(companies_to_update):
                if i < len(new_embeddings):
                    company["embedding"] = new_embeddings[i]
                else:
                    company["embedding"] = []
    
    # Verificar quantas empresas ficaram com embedding
    companies_with_embeddings = sum(1 for c in companies if c.get("embedding"))
    print(f"   ✅ {companies_with_embeddings}/{len(companies)} empresas vetorizadas")


def _process_phase2_matching(items, potential_matches, pncp_id, cache_service, vectorizer, estatisticas):
    """Processa Fase 2 com otimização de cache"""
    item_descriptions = [item.get("descricao", "") for item in items]
    
    # 🔥 OTIMIZAÇÃO: Buscar embeddings dos itens em lote do cache
    cached_item_embeddings = cache_service.batch_get_embeddings_from_cache(item_descriptions)
    
    # Gerar embeddings faltantes
    texts_to_generate = [desc for desc in item_descriptions if desc not in cached_item_embeddings]
    
    if texts_to_generate:
        new_embeddings = vectorizer.batch_vectorize(texts_to_generate)
        if new_embeddings:
            # Salvar no cache em lote
            texts_and_embeddings = list(zip(texts_to_generate, new_embeddings))
            cache_service.batch_save_embeddings_to_cache(texts_and_embeddings)
            
            # Adicionar aos embeddings cached
            for text, emb in zip(texts_to_generate, new_embeddings):
                cached_item_embeddings[text] = emb
    
    # Processar matches com embeddings otimizados
    for company, score_fase1, justificativa_fase1 in potential_matches:
        item_matches = 0
        total_item_score = 0.0
        
        for desc in item_descriptions:
            if desc not in cached_item_embeddings:
                continue
                
            item_embedding = cached_item_embeddings[desc]
            item_score, item_justificativa = calculate_enhanced_similarity(
                item_embedding, 
                company["embedding"],
                desc,
                company["descricao_servicos_produtos"]
            )
            
            if item_score >= SIMILARITY_THRESHOLD_PHASE2:
                item_matches += 1
                total_item_score += item_score
        
        if item_matches > 0:
            final_score = (score_fase1 + (total_item_score / item_matches)) / 2
            combined_justificativa = f"Fase 1: {justificativa_fase1} | Fase 2: {item_matches} itens matched"
            
            save_match_to_db(pncp_id, company["id"], final_score, "objeto_e_itens", combined_justificativa)
            estatisticas['matches_fase2'] += 1
            
            print(f"      🎯 MATCH FINAL! {company['nome']} - Score: {final_score:.3f}")


def _process_phase1_only_matching(potential_matches, pncp_id, estatisticas):
    """Processa matches apenas da Fase 1"""
    for company, score, justificativa in potential_matches:
        save_match_to_db(pncp_id, company["id"], score, "objeto_completo", 
                        f"Apenas Fase 1: {justificativa}")
        estatisticas['matches_fase1_apenas'] += 1
        print(f"      🎯 MATCH! {company['nome']} - Score: {score:.3f}")


def reevaluate_existing_bids(vectorizer: BaseTextVectorizer, clear_matches: bool = True, enable_llm_validation: bool = True):
    """
    Reavalia todas as licitações existentes no banco contra as empresas cadastradas
    VERSÃO REDIS LOCAL: Cache otimizado apenas com Redis local + Validação LLM
    """
    print("=" * 80)
    print("🔄 REAVALIAÇÃO COM CACHE REDIS LOCAL + VALIDAÇÃO LLM")
    print("=" * 80)
    print(f"🔧 Vectorizador: {type(vectorizer).__name__}")
    print(f"📊 Thresholds: Fase 1 = {SIMILARITY_THRESHOLD_PHASE1} | Fase 2 = {SIMILARITY_THRESHOLD_PHASE2}")
    print(f"🤖 Validação LLM: {'ATIVADA' if enable_llm_validation else 'DESATIVADA'}")
    
    # 🔥 Cache apenas Redis local
    cache_service = EmbeddingCacheService(db_manager)
    
    # 🤖 Inicializar validador LLM
    llm_validator = None
    if enable_llm_validation:
        llm_validator = LLMMatchValidator()
        print(f"🤖 Validador LLM configurado (threshold: {llm_validator.HIGH_SCORE_THRESHOLD:.1%})")
    
    if clear_matches:
        clear_existing_matches()

    # 1. Carregar empresas e vetorizar com cache Redis
    print("\n🏢 Carregando empresas do banco...")
    companies = get_all_companies_from_db()
    print(f"   ✅ {len(companies)} empresas carregadas")
    
    if not companies:
        print("❌ Nenhuma empresa encontrada no banco. Cadastre empresas primeiro.")
        return
    
    # 🔥 OTIMIZAÇÃO: Vetorizar empresas com cache em lote
    _vectorize_companies_with_cache(companies, cache_service, vectorizer)
    
    # 2. Carregar licitações existentes
    print(f"\n📄 Carregando licitações do banco...")
    existing_bids = get_existing_bids_from_db()
    print(f"   ✅ {len(existing_bids)} licitações encontradas")
    
    if not existing_bids:
        print("❌ Nenhuma licitação encontrada no banco.")
        return
    
    # 3. 🔥 OTIMIZAÇÃO: Processar licitações com cache em lote Redis
    print(f"\n⚡ Iniciando reavaliação com CACHE REDIS LOCAL...")
    
    # Pré-carregar embeddings de licitações em lote
    bid_texts = [bid['objeto_compra'] for bid in existing_bids if bid['objeto_compra']]
    cached_bid_embeddings = cache_service.batch_get_embeddings_from_cache(bid_texts)
    redis_cache_hits = len(cached_bid_embeddings)
    
    print(f"   ⚡ Cache Redis: {redis_cache_hits}/{len(bid_texts)} embeddings de licitações encontrados")
    
    matches_encontrados = 0
    estatisticas = {
        'total_processadas': 0,
        'com_matches': 0,
        'sem_matches': 0,
        'matches_fase1_apenas': 0,
        'matches_fase2': 0,
        'vetorizacao_falhou': 0,
        'llm_validations_count': 0,
        'llm_approved': 0,
        'llm_rejected': 0
    }
    
    for i, bid in enumerate(existing_bids, 1):
        objeto_compra = bid['objeto_compra']
        pncp_id = bid['pncp_id']
        
        print(f"\n[{i}/{len(existing_bids)}] 🔍 Reavaliando: {pncp_id}")
        print(f"   📝 Objeto: {objeto_compra[:100]}...")
        
        if not objeto_compra:
            print("   ⚠️  Objeto da compra vazio, pulando...")
            continue
        
        # 🔥 CACHE: Usar embedding do cache ou gerar novo
        if objeto_compra in cached_bid_embeddings:
            bid_embedding = cached_bid_embeddings[objeto_compra]
            print(f"   ⚡ Embedding do cache Redis")
        else:
            bid_embedding = vectorizer.vectorize(objeto_compra)
            if bid_embedding:
                cache_service.save_embedding_to_cache(objeto_compra, bid_embedding)
                print(f"   🆕 Novo embedding gerado")
        
        if not bid_embedding:
            print("   ❌ Erro ao vetorizar objeto da compra")
            estatisticas['vetorizacao_falhou'] += 1
            continue
        
        estatisticas['total_processadas'] += 1
        
        # FASE 1: Matching do objeto completo
        potential_matches = []
        for company in companies:
            if not company.get("embedding"):
                continue
            
            score, justificativa = calculate_enhanced_similarity(
                bid_embedding, 
                company["embedding"], 
                objeto_compra, 
                company["descricao_servicos_produtos"]
            )
            
            if score >= SIMILARITY_THRESHOLD_PHASE1:
                # 🤖 VALIDAÇÃO LLM PARA SCORES ALTOS
                should_accept_match = True
                final_score = score
                final_justificativa = justificativa
                
                if llm_validator and llm_validator.should_validate_with_llm(score):
                    validation = llm_validator.validate_match(
                        empresa_nome=company['nome'],
                        empresa_descricao=company['descricao_servicos_produtos'],
                        licitacao_objeto=objeto_compra,
                        pncp_id=pncp_id,
                        similarity_score=score
                    )
                    
                    estatisticas['llm_validations_count'] += 1
                    
                    if validation['is_valid']:
                        final_score = validation['confidence']
                        final_justificativa += f" | LLM: {validation['reasoning'][:100]}..."
                        estatisticas['llm_approved'] += 1
                    else:
                        should_accept_match = False
                        estatisticas['llm_rejected'] += 1
                
                if should_accept_match:
                    potential_matches.append((company, final_score, final_justificativa))
        
        if potential_matches:
            estatisticas['com_matches'] += 1
            
            # Buscar itens da licitação
            items = get_bid_items_from_db(bid['id'])
            
            # FASE 2: Refinamento com itens (se disponível)
            if items:
                _process_phase2_matching(items, potential_matches, pncp_id, cache_service, vectorizer, estatisticas)
            else:
                _process_phase1_only_matching(potential_matches, pncp_id, estatisticas)
                
            matches_encontrados += len(potential_matches)
        else:
            estatisticas['sem_matches'] += 1
        
        print("-" * 60)
    
    # Relatório final com estatísticas de cache Redis
    print(f"\n📊 ESTATÍSTICAS REDIS CACHE:")
    print(f"   ⚡ Cache hits Redis: {redis_cache_hits}/{len(bid_texts)}")
    
    # Exibir stats do cache
    cache_stats = cache_service.get_cache_stats()
    if cache_stats.get('status') == 'active':
        print(f"   📈 Total embeddings em cache: {cache_stats['cache_stats']['match_keys']}")
        print(f"   🎯 Eficiência do cache: {cache_stats['performance']['cache_efficiency']}")
        print(f"   💾 Memória Redis: {cache_stats['redis_info']['memory_used']}")
    
    result = _print_detailed_final_report(matches_encontrados, estatisticas)
    
    print(f"🚀 Processo de reavaliação finalizado com Redis LOCAL!")
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
    if estatisticas.get('llm_validations_count', 0) > 0:
        print(f"   🤖 Validações LLM: {estatisticas['llm_validations_count']}")
        print(f"   ✅ LLM aprovados: {estatisticas['llm_approved']}")
        print(f"   ❌ LLM rejeitados: {estatisticas['llm_rejected']}")
    
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
    if estatisticas.get('llm_validations_count', 0) > 0:
        print(f"   🤖 Validações LLM: {estatisticas['llm_validations_count']}")
        print(f"   ✅ LLM aprovados: {estatisticas['llm_approved']}")
        print(f"   ❌ LLM rejeitados: {estatisticas['llm_rejected']}")
        if estatisticas['llm_validations_count'] > 0:
            taxa_aprovacao_llm = (estatisticas['llm_approved'] / estatisticas['llm_validations_count']) * 100
            print(f"   📈 Taxa aprovação LLM: {taxa_aprovacao_llm:.1f}%")
    
    if estatisticas['total_processadas'] > 0:
        taxa_sucesso = (estatisticas['com_matches'] / estatisticas['total_processadas']) * 100
        print(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    return {
        'matches_encontrados': matches_encontrados,
        'estatisticas': estatisticas
    }


if __name__ == "__main__":
    print("=" * 80)
    print("🇧🇷 SISTEMA DE MATCHING BRASILEIRO - LICITAÇÕES PNCP")
    print("=" * 80)
    
    # Menu de configuração do vectorizer
    print("\n🔧 Escolha o sistema de vetorização:")
    print("1. 🇧🇷 Sistema Brasileiro (NeralMind BERT) - RECOMENDADO")
    print("2. Sistema Híbrido (Brasileiro + fallbacks internacionais)")
    print("3. VoyageAI (internacional)")
    print("4. OpenAI Embeddings (internacional)")
    print("5. MockTextVectorizer (apenas para teste)")
    
    vectorizer_choice = input("\nEscolha o vetorizador (1-5, padrão: 1): ").strip() or "1"
    
    # Configurar vectorizer
    try:
        if vectorizer_choice == "1":
            print("\n🇧🇷 Inicializando Sistema Brasileiro...")
            vectorizer = BrazilianTextVectorizer()
        elif vectorizer_choice == "2":
            print("\n🔥 Inicializando Sistema Híbrido (Brasileiro + Internacional)...")
            vectorizer = HybridTextVectorizer()
        elif vectorizer_choice == "3":
            print("\n🚢 Inicializando VoyageAI...")
            vectorizer = VoyageAITextVectorizer()
        elif vectorizer_choice == "4":
            print("\n🔥 Inicializando OpenAI Embeddings...")
            vectorizer = OpenAITextVectorizer()
        elif vectorizer_choice == "5":
            print("\n🧪 Inicializando MockTextVectorizer...")
            vectorizer = MockTextVectorizer()
        else:
            print(f"\n❌ Opção inválida '{vectorizer_choice}'. Usando Sistema Brasileiro...")
            vectorizer = BrazilianTextVectorizer()
    except Exception as e:
        print(f"\n❌ Erro ao inicializar vetorizador: {e}")
        print("🔄 Tentando fallback para Sistema Brasileiro...")
        try:
            vectorizer = BrazilianTextVectorizer()
        except Exception as e2:
            print(f"🔄 Fallback final: MockTextVectorizer...")
            try:
                vectorizer = MockTextVectorizer()
            except Exception as e3:
                print(f"❌ Erro crítico: {e3}")
                exit(1)
    
    # Menu de operações
    print("\n📋 Operações disponíveis:")
    print("1. Buscar novas licitações do PNCP (process_daily_bids)")
    print("2. Reavaliar licitações existentes no banco (reevaluate_existing_bids)")
    print("3. Teste rápido de vetorização")
    print("4. Limpar cache Redis")
    
    opcao = input("\nEscolha uma operação (1-4, padrão: 2): ").strip() or "2"
    
    try:
        if opcao == "1":
            print("\n🌐 Executando busca de novas licitações...")
            process_daily_bids(vectorizer)
        elif opcao == "2":
            print("\n🔄 Executando reavaliação de licitações existentes...")
            result = reevaluate_existing_bids(vectorizer, clear_matches=True)
            
            if result:
                print(f"\n📈 RESULTADO FINAL:")
                print(f"   🎯 Matches encontrados: {result['matches_encontrados']}")
                print(f"   📊 Taxa de sucesso: {result['estatisticas']['com_matches']/result['estatisticas']['total_processadas']*100 if result['estatisticas']['total_processadas'] > 0 else 0:.1f}%")
        elif opcao == "3":
            print("\n🧪 Executando teste rápido de vetorização...")
            
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
                
                # Teste de cache
                cache_service = EmbeddingCacheService(db_manager)
                cache_service.batch_save_embeddings_to_cache(list(zip(test_texts, embeddings)))
                print(f"   💾 Embeddings salvos no cache Redis")
                
                # Testar recuperação do cache
                cached = cache_service.batch_get_embeddings_from_cache(test_texts)
                print(f"   ⚡ Cache test: {len(cached)}/{len(test_texts)} recuperados")
            else:
                print("   ❌ Falha na vetorização")
        elif opcao == "4":
            print("\n🧹 Limpando cache Redis...")
            cache_service = EmbeddingCacheService(db_manager)
            deleted = cache_service.clear_cache()
            print(f"   🗑️ {deleted} entradas removidas do cache")
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