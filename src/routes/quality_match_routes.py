"""
🎯 ROTAS PARA MATCHING DE ALTA QUALIDADE
Endpoints para testar e configurar diferentes níveis de qualidade
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Criar blueprint
quality_match_routes = Blueprint('quality_matches', __name__, url_prefix='/api/quality-matches')

@quality_match_routes.route('/test-levels', methods=['POST'])
def test_quality_levels():
    """
    POST /api/quality-matches/test-levels
    
    Testa diferentes níveis de qualidade de matching
    
    Body JSON:
    {
        "bid_text": "Desenvolvimento de sistema web...",
        "company_text": "Empresa especializada em...",
        "levels": ["maximum", "high", "medium", "permissive"]  // opcional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'bid_text' not in data or 'company_text' not in data:
            return jsonify({
                'success': False,
                'error': 'bid_text e company_text são obrigatórios'
            }), 400
        
        bid_text = data['bid_text']
        company_text = data['company_text']
        test_levels = data.get('levels', ['maximum', 'high', 'medium', 'permissive'])
        
        from matching.improved_vectorizers import (
            get_vectorizer_for_quality_level,
            calculate_improved_similarity
        )
        
        results = {}
        
        for level in test_levels:
            try:
                vectorizer = get_vectorizer_for_quality_level(level)
                
                # Gerar embeddings
                bid_embedding = vectorizer.vectorize(bid_text)
                company_embedding = vectorizer.vectorize(company_text)
                
                if not bid_embedding or not company_embedding:
                    results[level] = {
                        'error': 'Falha ao gerar embeddings',
                        'success': False
                    }
                    continue
                
                # Calcular similaridade
                score, justification, analysis = calculate_improved_similarity(
                    bid_embedding, 
                    company_embedding, 
                    bid_text, 
                    company_text,
                    vectorizer.quality_preset
                )
                
                results[level] = {
                    'success': True,
                    'score': score,
                    'quality_category': analysis['quality_category'],
                    'should_accept': analysis['should_accept'],
                    'avg_specificity': analysis['avg_specificity'],
                    'bid_category': analysis['bid_analysis']['category'],
                    'company_category': analysis['company_analysis']['category'],
                    'quality_adjustments': analysis['quality_adjustments'],
                    'justification': justification.replace('\n', ' ').strip()
                }
                
            except Exception as e:
                results[level] = {
                    'error': str(e),
                    'success': False
                }
        
        return jsonify({
            'success': True,
            'data': {
                'bid_text': bid_text[:100] + '...' if len(bid_text) > 100 else bid_text,
                'company_text': company_text[:100] + '...' if len(company_text) > 100 else company_text,
                'results_by_level': results
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao testar níveis de qualidade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quality_match_routes.route('/run-with-quality', methods=['POST'])
def run_matching_with_quality():
    """
    POST /api/quality-matches/run-with-quality
    
    Executa reavaliação usando nível de qualidade específico
    
    Body JSON:
    {
        "quality_level": "high",  // maximum, high, medium, permissive
        "clear_existing": true,   // opcional, padrão true
        "limit": 100             // opcional, limitar número de licitações
    }
    """
    try:
        data = request.get_json() or {}
        
        quality_level = data.get('quality_level', 'high')
        clear_existing = data.get('clear_existing', True)
        limit = data.get('limit')
        
        # Validar quality_level
        valid_levels = ['maximum', 'high', 'medium', 'permissive']
        if quality_level not in valid_levels:
            return jsonify({
                'success': False,
                'error': f'quality_level deve ser um de: {valid_levels}'
            }), 400
        
        # Executar em background
        import threading
        from matching.improved_matching_engine import run_quality_matching
        
        def run_background():
            try:
                result = run_quality_matching(
                    quality_level=quality_level,
                    clear_existing=clear_existing,
                    vectorizer_type="brazilian",
                    enable_llm_validation=True  # ✅ Validação LLM ativada por padrão
                )
                logger.info(f"✅ Matching de qualidade concluído: {result}")
            except Exception as e:
                logger.error(f"❌ Erro no matching de qualidade: {e}")
        
        thread = threading.Thread(target=run_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': f'Matching de qualidade iniciado com nível {quality_level}',
            'quality_level': quality_level,
            'clear_existing': clear_existing,
            'limit': limit,
            'estimated_duration': '10-30 minutos'
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao iniciar matching de qualidade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quality_match_routes.route('/analyze-company', methods=['POST'])
def analyze_company_quality():
    """
    POST /api/quality-matches/analyze-company
    
    Analisa a qualidade das descrições das empresas
    
    Body JSON:
    {
        "company_ids": [1, 2, 3],  // opcional, se não informado analisa todas
        "min_specificity": 0.5     // opcional, score mínimo de especificidade
    }
    """
    try:
        from config.database import db_manager
        from matching.improved_matching_config import QualityMatchingConfig
        
        data = request.get_json() or {}
        company_ids = data.get('company_ids')
        min_specificity = data.get('min_specificity', 0.0)
        
        # Buscar empresas
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            if company_ids:
                placeholders = ','.join(['%s'] * len(company_ids))
                query = f"""
                    SELECT id, nome, descricao_servicos_produtos 
                    FROM empresas 
                    WHERE id IN ({placeholders})
                """
                cursor.execute(query, company_ids)
            else:
                query = """
                    SELECT id, nome, descricao_servicos_produtos 
                    FROM empresas 
                    WHERE descricao_servicos_produtos IS NOT NULL 
                    AND descricao_servicos_produtos != ''
                """
                cursor.execute(query)
            
            companies = cursor.fetchall()
        
        # Analisar qualidade
        config = QualityMatchingConfig()
        analysis_results = []
        
        for company in companies:
            company_id, nome, descricao = company
            
            if not descricao:
                continue
            
            specificity_score = config.calculate_specificity_score(descricao)
            
            if specificity_score >= min_specificity:
                analysis_results.append({
                    'id': company_id,
                    'nome': nome,
                    'specificity_score': specificity_score,
                    'quality_category': config.get_match_quality_category(specificity_score),
                    'description_length': len(descricao),
                    'description_preview': descricao[:100] + '...' if len(descricao) > 100 else descricao
                })
        
        # Ordenar por score de especificidade
        analysis_results.sort(key=lambda x: x['specificity_score'], reverse=True)
        
        # Estatísticas
        scores = [r['specificity_score'] for r in analysis_results]
        stats = {
            'total_analyzed': len(analysis_results),
            'avg_specificity': sum(scores) / len(scores) if scores else 0,
            'high_quality_count': len([s for s in scores if s >= 0.7]),
            'medium_quality_count': len([s for s in scores if 0.5 <= s < 0.7]),
            'low_quality_count': len([s for s in scores if s < 0.5])
        }
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': stats,
                'companies': analysis_results[:50],  # Limitar a 50 para não sobrecarregar
                'total_companies': len(analysis_results)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao analisar qualidade das empresas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quality_match_routes.route('/presets', methods=['GET'])
def get_quality_presets():
    """
    GET /api/quality-matches/presets
    
    Lista os presets de qualidade disponíveis
    """
    try:
        from matching.improved_matching_config import QUALITY_PRESETS
        
        return jsonify({
            'success': True,
            'data': {
                'presets': QUALITY_PRESETS,
                'recommendation': {
                    'conservative': 'Para máxima qualidade, poucos matches',
                    'balanced': 'Equilibrio ideal entre qualidade e quantidade',
                    'aggressive': 'Mais matches, qualidade moderada',
                    'ultra_selective': 'Apenas matches perfeitos'
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quality_match_routes.route('/test-llm-validation', methods=['POST'])
def test_llm_validation():
    """
    POST /api/quality-matches/test-llm-validation
    
    Testa validação LLM em matches reais de alta qualidade
    
    Body JSON:
    {
        "min_score": 0.8,          // score mínimo para testar
        "limit": 10               // número máximo de matches para testar
    }
    """
    try:
        from config.database import db_manager
        from matching.llm_match_validator import LLMMatchValidator
        
        data = request.get_json() or {}
        min_score = data.get('min_score', 0.80)
        limit = data.get('limit', 10)
        
        # Buscar matches de alta qualidade
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    m.score_similaridade,
                    m.justificativa_match,
                    e.nome_fantasia as empresa_nome,
                    e.descricao_servicos_produtos as empresa_descricao,
                    l.objeto_compra as licitacao_objeto,
                    l.pncp_id as licitacao_pncp_id
                FROM matches m
                JOIN empresas e ON m.empresa_id = e.id  
                JOIN licitacoes l ON m.licitacao_id = l.id
                WHERE m.score_similaridade >= %s
                ORDER BY m.score_similaridade DESC
                LIMIT %s
            """
            
            cursor.execute(query, (min_score, limit))
            matches = cursor.fetchall()
        
        if not matches:
            return jsonify({
                'success': True,
                'message': f'Nenhum match encontrado com score >= {min_score:.1%}',
                'data': {
                    'tested_matches': [],
                    'summary': {
                        'total_tested': 0,
                        'llm_approved': 0,
                        'llm_rejected': 0,
                        'approval_rate': 0
                    }
                }
            }), 200
        
        # Inicializar validador LLM
        validator = LLMMatchValidator()
        
        # Testar cada match
        tested_matches = []
        llm_approved = 0
        llm_rejected = 0
        
        for match in matches:
            score, justificativa, empresa_nome, empresa_descricao, licitacao_objeto, pncp_id = match
            
            # Executar validação LLM
            validation = validator.validate_match(
                empresa_nome=empresa_nome,
                empresa_descricao=empresa_descricao,
                licitacao_objeto=licitacao_objeto,
                pncp_id=pncp_id,
                similarity_score=float(score)
            )
            
            if validation['is_valid']:
                llm_approved += 1
            else:
                llm_rejected += 1
            
            tested_matches.append({
                'original_score': float(score),
                'empresa_nome': empresa_nome,
                'licitacao_pncp_id': pncp_id,
                'empresa_descricao': empresa_descricao[:100] + '...' if len(empresa_descricao) > 100 else empresa_descricao,
                'licitacao_objeto': licitacao_objeto[:100] + '...' if len(licitacao_objeto) > 100 else licitacao_objeto,
                'llm_validation': validation
            })
        
        # Calcular estatísticas
        total_tested = len(tested_matches)
        approval_rate = (llm_approved / total_tested * 100) if total_tested > 0 else 0
        
        return jsonify({
            'success': True,
            'message': f'Validação LLM concluída para {total_tested} matches',
            'data': {
                'tested_matches': tested_matches,
                'summary': {
                    'total_tested': total_tested,
                    'llm_approved': llm_approved,
                    'llm_rejected': llm_rejected,
                    'approval_rate': approval_rate,
                    'min_score_tested': min_score
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erro ao testar validação LLM: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500 