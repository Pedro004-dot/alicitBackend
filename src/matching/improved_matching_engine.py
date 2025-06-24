#!/usr/bin/env python3
"""
🎯 ENGINE DE MATCHING DE ALTA QUALIDADE
Versão melhorada do matching_engine.py com análise de qualidade integrada
"""

import os
import datetime
from typing import Dict, Any, List, Tuple
import time
from psycopg2.extras import DictCursor

from services.embedding_cache_service import EmbeddingCacheService
from services.deduplication_service import DeduplicationService
from config.database import db_manager

from .improved_vectorizers import (
    get_vectorizer_for_quality_level,
    calculate_improved_similarity
)
from .improved_matching_config import get_quality_config
from .llm_match_validator import LLMMatchValidator
from .pncp_api import (
    get_db_connection, get_all_companies_from_db, get_processed_bid_ids,
    fetch_bids_from_pncp, fetch_bid_items_from_pncp, save_bid_to_db,
    save_bid_items_to_db, save_match_to_db, update_bid_status,
    get_existing_bids_from_db, get_bid_items_from_db, clear_existing_matches,
    ESTADOS_BRASIL, PNCP_MAX_PAGES
)

def run_quality_matching(quality_level: str = "high", clear_existing: bool = True, 
                        vectorizer_type: str = "brazilian", enable_llm_validation: bool = True) -> Dict[str, Any]:
    """
    🎯 MATCHING DE ALTA QUALIDADE
    
    Executa matching usando configurações de qualidade melhoradas
    
    Args:
        quality_level: Nível de qualidade ("maximum", "high", "medium", "permissive")
        clear_existing: Se deve limpar matches existentes
        vectorizer_type: Tipo de vectorizer ("brazilian", "hybrid", etc.)
    
    Returns:
        Dict com estatísticas do processo
    """
    print("🎯 INICIANDO MATCHING DE ALTA QUALIDADE COM VALIDAÇÃO LLM")
    print(f"📊 Nível: {quality_level.upper()}")
    print(f"🔧 Vectorizer: {vectorizer_type}")
    print(f"🤖 Validação LLM: {'ATIVADA' if enable_llm_validation else 'DESATIVADA'}")
    print("=" * 80)
    
    # Obter configurações de qualidade
    config = get_quality_config(quality_level)
    print(f"🔧 Configuração carregada:")
    print(f"   📊 Threshold Fase 1: {config['threshold_phase1']}")
    print(f"   📊 Threshold Fase 2: {config['threshold_phase2']}")
    print(f"   🚫 Blacklist: {len(config['blacklist_terms'])} termos")
    print(f"   ✅ Whitelist: {len(config['whitelist_terms'])} termos")
    
    # Inicializar vectorizer de alta qualidade
    vectorizer = get_vectorizer_for_quality_level(quality_level, vectorizer_type)
    
    # Inicializar validador LLM
    llm_validator = None
    if enable_llm_validation:
        llm_validator = LLMMatchValidator()
        print(f"🤖 Validador LLM configurado (threshold: {llm_validator.HIGH_SCORE_THRESHOLD:.1%})")
    
    # Cache otimizado Redis local
    cache_service = EmbeddingCacheService(db_manager)
    dedup_service = DeduplicationService(db_manager, cache_service)
    
    # Limpar matches existentes se solicitado
    if clear_existing:
        print("\n🗑️ Limpando matches existentes...")
        clear_existing_matches()
        print("   ✅ Matches anteriores removidos")
    
    # 1. Carregar empresas
    print("\n🏢 Carregando empresas do banco...")
    companies = get_all_companies_from_db()
    print(f"   ✅ {len(companies)} empresas carregadas")
    
    if not companies:
        return {
            'success': False,
            'error': 'Nenhuma empresa encontrada no banco',
            'stats': {}
        }
    
    # 2. Vetorizar empresas com cache Redis
    print("🔢 Vetorizando descrições das empresas...")
    _vectorize_companies_with_quality_cache(companies, cache_service, vectorizer)
    
    # 3. Carregar licitações existentes
    print(f"\n📄 Carregando licitações do banco...")
    existing_bids = get_existing_bids_from_db()
    print(f"   ✅ {len(existing_bids)} licitações encontradas")
    
    if not existing_bids:
        return {
            'success': False,
            'error': 'Nenhuma licitação encontrada no banco',
            'stats': {}
        }
    
    # 4. Processar matching com qualidade
    print(f"\n⚡ Iniciando matching de ALTA QUALIDADE...")
    
    # Pré-carregar embeddings de licitações
    bid_texts = [bid['objeto_compra'] for bid in existing_bids if bid['objeto_compra']]
    cached_bid_embeddings = cache_service.batch_get_embeddings_from_cache(bid_texts)
    redis_cache_hits = len(cached_bid_embeddings)
    
    print(f"   ⚡ Cache Redis: {redis_cache_hits}/{len(bid_texts)} embeddings encontrados")
    
    # Estatísticas do processo
    stats = {
        'total_bids_processed': 0,
        'bids_with_matches': 0,
        'bids_without_matches': 0,
        'matches_phase1_only': 0,
        'matches_phase2': 0,
        'total_matches_found': 0,
        'vectorization_failed': 0,
        'quality_rejected': 0,
        'quality_accepted': 0,
        'llm_validations_count': 0,
        'llm_approved': 0,
        'llm_rejected': 0,
        'matches_saved': 0,
        'average_score': 0.0,
        'config_used': config,
        'cache_efficiency': f"{redis_cache_hits}/{len(bid_texts)}",
        'llm_validation_enabled': enable_llm_validation
    }
    
    total_scores = []
    
    for i, bid in enumerate(existing_bids, 1):
        objeto_compra = bid['objeto_compra']
        pncp_id = bid['pncp_id']
        
        print(f"\n[{i}/{len(existing_bids)}] 🔍 Processando: {pncp_id}")
        print(f"   📝 Objeto: {objeto_compra[:100]}...")
        
        if not objeto_compra:
            print("   ⚠️ Objeto da compra vazio, pulando...")
            continue
        
        # Obter embedding (cache ou gerar novo)
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
            stats['vectorization_failed'] += 1
            continue
        
        stats['total_bids_processed'] += 1
        
        # FASE 1: Matching com análise de qualidade
        potential_matches = []
        print("   🔍 FASE 1 - Análise semântica de ALTA QUALIDADE:")
        
        for company in companies:
            if not company.get("embedding"):
                continue
            
            # Usar análise de qualidade melhorada
            score, justificativa, analysis = calculate_improved_similarity(
                bid_embedding, 
                company["embedding"], 
                objeto_compra, 
                company["descricao_servicos_produtos"],
                quality_level=quality_level,
                return_analysis=True
            )
            
            print(f"      🏢 {company['nome']}: Score = {score:.3f} | Qualidade = {analysis.get('quality_category', 'N/A')}")
            
            # Usar threshold da configuração de qualidade
            if score >= config['threshold_phase1']:
                if analysis.get('should_accept', True):
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
                        
                        stats['llm_validations_count'] += 1
                        
                        if validation['is_valid']:
                            print(f"         🎯 LLM APROVOU! Confiança: {validation['confidence']:.1%}")
                            final_score = validation['confidence']
                            final_justificativa += f" | LLM: {validation['reasoning'][:100]}..."
                            stats['llm_approved'] += 1
                        else:
                            print(f"         🚫 LLM REJEITOU: {validation['reasoning'][:80]}...")
                            should_accept_match = False
                            stats['llm_rejected'] += 1
                    
                    if should_accept_match:
                        potential_matches.append((company, final_score, final_justificativa, analysis))
                        stats['quality_accepted'] += 1
                        print(f"         ✅ MATCH DE QUALIDADE ACEITO!")
                    else:
                        stats['quality_rejected'] += 1
                        print(f"         ❌ Rejeitado pela validação LLM")
                else:
                    stats['quality_rejected'] += 1
                    print(f"         ❌ Rejeitado por baixa qualidade")
            else:
                print(f"         📊 Score abaixo do threshold ({config['threshold_phase1']:.3f})")
        
        if potential_matches:
            print(f"   🎯 {len(potential_matches)} matches de qualidade encontrados!")
            stats['bids_with_matches'] += 1
            
            # Buscar itens da licitação
            items = get_bid_items_from_db(bid['id'])
            
            # FASE 2: Refinamento com itens (se disponível)
            if items:
                _process_quality_phase2_matching(
                    items, potential_matches, pncp_id, cache_service, 
                    vectorizer, stats, config, quality_level
                )
            else:
                _process_quality_phase1_only_matching(potential_matches, pncp_id, stats)
                
            # Coletar scores para estatísticas
            for _, score, _, _ in potential_matches:
                total_scores.append(score)
                
            stats['total_matches_found'] += len(potential_matches)
        else:
            print("   ❌ Nenhum match de qualidade encontrado")
            stats['bids_without_matches'] += 1
        
        # Mostrar progresso a cada 50 licitações
        if i % 50 == 0:
            print(f"\n📊 PROGRESSO [{i}/{len(existing_bids)}]:")
            print(f"   🎯 Matches encontrados: {stats['total_matches_found']}")
            print(f"   ✅ Taxa de sucesso: {(stats['bids_with_matches']/stats['total_bids_processed']*100):.1f}%")
    
    # Calcular estatísticas finais
    if total_scores:
        stats['average_score'] = sum(total_scores) / len(total_scores)
    
    # Obter estatísticas do cache
    cache_stats = cache_service.get_cache_stats()
    
    # Relatório final
    _print_quality_final_report(stats, quality_level, cache_stats)
    
    return {
        'success': True,
        'message': f'Matching de alta qualidade concluído com nível {quality_level}',
        'stats': stats
    }


def _vectorize_companies_with_quality_cache(companies, cache_service, vectorizer):
    """Vetorizar empresas usando cache otimizado para qualidade"""
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
            texts_to_generate.append(texto_empresa)
            companies_to_update.append(company)
    
    print(f"   ⚡ Cache Redis hits: {cache_hits}/{len(companies)} empresas")
    
    # Gerar embeddings faltantes
    if texts_to_generate:
        print(f"   🔄 Gerando {len(texts_to_generate)} novos embeddings...")
        
        new_embeddings = vectorizer.batch_vectorize(texts_to_generate)
        
        if new_embeddings:
            # Salvar no cache em lote
            texts_and_embeddings = list(zip(texts_to_generate, new_embeddings))
            cache_service.batch_save_embeddings_to_cache(texts_and_embeddings)
            
            # Atribuir aos objetos empresa
            for i, company in enumerate(companies_to_update):
                if i < len(new_embeddings):
                    company["embedding"] = new_embeddings[i]
                else:
                    company["embedding"] = []
    
    companies_with_embeddings = sum(1 for c in companies if c.get("embedding"))
    print(f"   ✅ {companies_with_embeddings}/{len(companies)} empresas vetorizadas")


def _process_quality_phase2_matching(items, potential_matches, pncp_id, cache_service, 
                                    vectorizer, stats, config, quality_level):
    """Processa Fase 2 com análise de qualidade"""
    item_descriptions = [item.get("descricao", "") for item in items]
    
    # Buscar embeddings dos itens em lote
    cached_item_embeddings = cache_service.batch_get_embeddings_from_cache(item_descriptions)
    
    # Gerar embeddings faltantes
    texts_to_generate = [desc for desc in item_descriptions if desc not in cached_item_embeddings]
    
    if texts_to_generate:
        new_embeddings = vectorizer.batch_vectorize(texts_to_generate)
        if new_embeddings:
            texts_and_embeddings = list(zip(texts_to_generate, new_embeddings))
            cache_service.batch_save_embeddings_to_cache(texts_and_embeddings)
            
            for text, emb in zip(texts_to_generate, new_embeddings):
                cached_item_embeddings[text] = emb
    
    # Processar matches com análise de qualidade
    for company, score_fase1, justificativa_fase1, analysis_fase1 in potential_matches:
        item_matches = 0
        total_item_score = 0.0
        
        for desc in item_descriptions:
            if desc not in cached_item_embeddings:
                continue
                
            item_embedding = cached_item_embeddings[desc]
            
            # Usar análise de qualidade melhorada para itens
            item_score, item_justificativa, item_analysis = calculate_improved_similarity(
                item_embedding, 
                company["embedding"],
                desc,
                company["descricao_servicos_produtos"],
                quality_level=quality_level,
                return_analysis=True
            )
            
            if item_score >= config['threshold_phase2'] and item_analysis.get('should_accept', True):
                item_matches += 1
                total_item_score += item_score
        
        if item_matches > 0:
            final_score = (score_fase1 + (total_item_score / item_matches)) / 2
            combined_justificativa = f"Fase 1: {justificativa_fase1} | Fase 2: {item_matches} itens de qualidade"
            
            save_match_to_db(pncp_id, company["id"], final_score, "objeto_e_itens", combined_justificativa)
            stats['matches_phase2'] += 1
            
            print(f"      🎯 MATCH FINAL DE QUALIDADE! {company['nome']} - Score: {final_score:.3f}")


def _process_quality_phase1_only_matching(potential_matches, pncp_id, stats):
    """Processa matches apenas da Fase 1 com qualidade"""
    for company, score, justificativa, analysis in potential_matches:
        save_match_to_db(pncp_id, company["id"], score, "objeto_completo", 
                        f"Qualidade {analysis.get('quality_category', 'N/A')}: {justificativa}")
        stats['matches_phase1_only'] += 1
        print(f"      🎯 MATCH DE QUALIDADE! {company['nome']} - Score: {score:.3f}")


def _print_quality_final_report(stats: Dict[str, Any], quality_level: str, cache_stats: Dict[str, Any]):
    """Imprime relatório final detalhado de qualidade"""
    print(f"\n" + "="*80)
    print(f"🎉 MATCHING DE ALTA QUALIDADE CONCLUÍDO!")
    print(f"📊 NÍVEL: {quality_level.upper()}")
    print(f"="*80)
    
    print(f"📊 ESTATÍSTICAS DETALHADAS:")
    print(f"   🔍 Licitações processadas: {stats['total_bids_processed']}")
    print(f"   ❌ Falhas na vetorização: {stats['vectorization_failed']}")
    print(f"   🎯 Licitações com matches: {stats['bids_with_matches']}")
    print(f"   ❌ Licitações sem matches: {stats['bids_without_matches']}")
    print(f"   📋 Matches apenas Fase 1: {stats['matches_phase1_only']}")
    print(f"   🔬 Matches com Fase 2: {stats['matches_phase2']}")
    print(f"   🎯 Total de matches: {stats['total_matches_found']}")
    print(f"   ✅ Aceitos por qualidade: {stats['quality_accepted']}")
    print(f"   ❌ Rejeitados por qualidade: {stats['quality_rejected']}")
    
    # Estatísticas LLM
    if stats.get('llm_validation_enabled') and stats.get('llm_validations_count', 0) > 0:
        print(f"\n🤖 VALIDAÇÕES LLM:")
        print(f"   🔍 Total analisados: {stats['llm_validations_count']}")
        print(f"   ✅ Aprovados pelo LLM: {stats['llm_approved']}")
        print(f"   🚫 Rejeitados pelo LLM: {stats['llm_rejected']}")
        llm_approval_rate = (stats['llm_approved'] / stats['llm_validations_count'] * 100) if stats['llm_validations_count'] > 0 else 0
        print(f"   📈 Taxa de aprovação LLM: {llm_approval_rate:.1f}%")
    
    if stats['total_bids_processed'] > 0:
        taxa_sucesso = (stats['bids_with_matches'] / stats['total_bids_processed']) * 100
        print(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    if stats['average_score'] > 0:
        print(f"   🎯 Score médio: {stats['average_score']:.3f}")
    
    print(f"\n📊 CACHE REDIS:")
    print(f"   ⚡ Eficiência: {stats['cache_efficiency']}")
    if cache_stats.get('status') == 'active':
        print(f"   📈 Total embeddings: {cache_stats['cache_stats']['match_keys']}")
        print(f"   🎯 Performance: {cache_stats['performance']['cache_efficiency']}")
    
    print(f"\n🎯 CONFIGURAÇÃO UTILIZADA:")
    config = stats['config_used']
    print(f"   📊 Threshold Fase 1: {config['threshold_phase1']}")
    print(f"   📊 Threshold Fase 2: {config['threshold_phase2']}")
    print(f"   🚫 Termos blacklist: {len(config['blacklist_terms'])}")
    print(f"   ✅ Termos whitelist: {len(config['whitelist_terms'])}")
    
    print(f"\n🚀 Sistema de matching de alta qualidade finalizado!") 