#!/usr/bin/env python3
"""
🎯 VETORIZADORES MELHORADOS PARA MATCHING DE ALTA QUALIDADE
Sistema brasileiro aprimorado com análise semântica mais rigorosa
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
import re

from .vectorizers import BrazilianTextVectorizer, calculate_enhanced_similarity
from .improved_matching_config import (
    QualityMatchingConfig, 
    GENERIC_TERMS_BLACKLIST,
    SPECIFIC_TERMS_WHITELIST,
    CATEGORY_THRESHOLDS
)

logger = logging.getLogger(__name__)

class ImprovedBrazilianTextVectorizer(BrazilianTextVectorizer):
    """
    🇧🇷 Vetorizador brasileiro melhorado com análise de qualidade
    Baseado no BrazilianTextVectorizer mas com filtros de qualidade mais rigorosos
    """
    
    def __init__(self, quality_preset: str = 'balanced'):
        """
        Inicializa vetorizador melhorado
        
        Args:
            quality_preset: 'conservative', 'balanced', 'aggressive', 'ultra_selective'
        """
        super().__init__()
        self.quality_preset = quality_preset
        self.quality_config = QualityMatchingConfig()
        logger.info(f"🎯 Vetorizador brasileiro melhorado inicializado - Preset: {quality_preset}")
    
    def preprocess_text_with_quality_analysis(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Preprocessa texto com análise de qualidade
        
        Returns:
            Tuple[texto_processado, análise_qualidade]
        """
        # Preprocessamento padrão
        processed_text = self.preprocess_text(text)
        
        # Análise de qualidade
        quality_analysis = {
            'specificity_score': self.quality_config.calculate_specificity_score(text),
            'category': self._detect_business_category(text),
            'has_generic_terms': any(term in text.lower() for term in GENERIC_TERMS_BLACKLIST),
            'has_specific_terms': any(term in text.lower() for term in SPECIFIC_TERMS_WHITELIST),
            'text_length': len(text),
            'complexity_indicators': self._count_complexity_indicators(text)
        }
        
        logger.debug(f"📊 Análise qualidade: {quality_analysis['specificity_score']:.2f} - {quality_analysis['category']}")
        
        return processed_text, quality_analysis
    
    def _detect_business_category(self, text: str) -> str:
        """Detecta categoria de negócio do texto"""
        text_lower = text.lower()
        
        for category, config in CATEGORY_THRESHOLDS.items():
            keyword_matches = sum(1 for keyword in config['keywords'] if keyword in text_lower)
            if keyword_matches >= 1:  # Pelo menos 1 keyword da categoria
                return category
        
        return 'geral'
    
    def _count_complexity_indicators(self, text: str) -> Dict[str, int]:
        """Conta indicadores de complexidade/especificidade"""
        text_lower = text.lower()
        
        return {
            'technical_terms': len(re.findall(r'\b(técnic[oa]|especializ[oa]|certificad[oa]|qualificad[oa])\b', text_lower)),
            'requirements': len(re.findall(r'\b(requisito|exigência|obrigatório|necessário)\b', text_lower)),
            'numbers': len(re.findall(r'\d+', text)),
            'regulations': len(re.findall(r'\b(NBR|ISO|ABNT|Lei|Decreto|Portaria)\s*\d*', text)),
            'experience_mentions': len(re.findall(r'\b\d+\s*(anos?|meses?)\b', text_lower))
        }

def calculate_improved_similarity(
    bid_embedding: List[float], 
    company_embedding: List[float], 
    bid_text: str, 
    company_text: str,
    quality_level: str = 'high',
    return_analysis: bool = False
) -> Tuple[float, str, Dict[str, Any]]:
    """
    🎯 CÁLCULO OTIMIZADO PARA MATCHES CERTEIROS - NÍVEL HIGH
    
    Implementa análise rigorosa para garantir apenas matches de alta qualidade
    Otimizado para 45-55% de taxa de match com máxima precisão
    
    Args:
        quality_level: Nível de qualidade ('maximum', 'high', 'medium', 'permissive')
        return_analysis: Se deve retornar análise detalhada
    
    Returns:
        Tuple[score, justificativa, análise_detalhada]
    """
    from .improved_matching_config import get_quality_config, QualityMatchingConfig
    
    # Obter configuração específica do nível
    config = get_quality_config(quality_level)
    quality_config = QualityMatchingConfig()
    
    # Análise de qualidade dos textos
    vectorizer = ImprovedBrazilianTextVectorizer('balanced')  # Usar preset balanceado
    
    # Preprocessar e analisar textos
    _, bid_analysis = vectorizer.preprocess_text_with_quality_analysis(bid_text)
    _, company_analysis = vectorizer.preprocess_text_with_quality_analysis(company_text)
    
    # Calcular similaridade base usando o método original
    base_score, base_justification = calculate_enhanced_similarity(
        bid_embedding, company_embedding, bid_text, company_text
    )
    
    # 🎯 FILTROS RIGOROSOS PARA NÍVEL HIGH
    quality_adjustments = []
    adjusted_score = base_score
    
    # 1. VERIFICAÇÃO DE ESPECIFICIDADE MÍNIMA (CRÍTICO PARA NÍVEL HIGH)
    avg_specificity = (bid_analysis['specificity_score'] + company_analysis['specificity_score']) / 2
    
    if avg_specificity < config.get('min_specificity', 0.5):
        # Nível high exige especificidade mínima de 0.5
        adjusted_score *= config.get('penalty_multiplier', 0.8)
        quality_adjustments.append("❌ Textos muito genéricos")
    elif avg_specificity > 0.7:
        adjusted_score *= 1.1  # Bonificar textos altamente específicos
        quality_adjustments.append("✅ Textos específicos")
    
    # 2. CATEGORIA DE NEGÓCIO (IMPORTANTE PARA PRECISÃO)
    if bid_analysis['category'] == company_analysis['category'] and bid_analysis['category'] != 'geral':
        adjusted_score *= 1.15  # Bonificar fortemente mesma categoria
        quality_adjustments.append(f"✅ Mesma categoria: {bid_analysis['category']}")
    elif bid_analysis['category'] == 'geral' or company_analysis['category'] == 'geral':
        adjusted_score *= 0.9  # Penalizar categoria muito genérica
    
    # 3. FILTRO DE BLACKLIST RIGOROSO
    bid_lower = bid_text.lower()
    company_lower = company_text.lower()
    
    blacklist_hits = 0
    for term in config['blacklist_terms']:
        if term in bid_lower or term in company_lower:
            blacklist_hits += 1
    
    if blacklist_hits > 2:  # Muitos termos genéricos
        adjusted_score *= 0.75  # Penalização severa
        quality_adjustments.append("⚠️ Muitos termos genéricos")
    elif blacklist_hits == 0:
        adjusted_score *= 1.05  # Bonificar ausência de termos genéricos
    
    # 4. BOOST PARA TERMOS TÉCNICOS (NÍVEL HIGH)
    if quality_level == 'high' and 'quality_boost' in config:
        boost_applied = False
        for keyword, boost_value in config['quality_boost'].items():
            if keyword in bid_lower or keyword in company_lower:
                adjusted_score += boost_value
                boost_applied = True
        
        if boost_applied:
            quality_adjustments.append("✅ Termos específicos presentes")
    
    # 5. VERIFICAÇÃO DE COMPLEXIDADE TÉCNICA
    bid_complexity = sum(bid_analysis['complexity_indicators'].values())
    company_complexity = sum(company_analysis['complexity_indicators'].values())
    
    if bid_complexity >= 3 and company_complexity >= 2:
        adjusted_score *= 1.08  # Bonificar alta complexidade
        quality_adjustments.append("✅ Alta complexidade técnica")
    elif bid_complexity == 0 and company_complexity == 0:
        adjusted_score *= 0.85  # Penalizar baixa complexidade
        quality_adjustments.append("⚠️ Baixa complexidade técnica")
    
    # 6. VERIFICAÇÃO ESPECIAL PARA PALAVRAS-CHAVE TÉCNICAS
    tech_keywords = ['desenvolvimento', 'sistema', 'software', 'tecnologia', 'especializado']
    bid_tech_score = sum(1 for keyword in tech_keywords if keyword in bid_lower)
    company_tech_score = sum(1 for keyword in tech_keywords if keyword in company_lower)
    
    if bid_tech_score >= 2 and company_tech_score >= 2:
        # Ambos têm perfil técnico forte
        original_similarity = base_score
        # Aplicar boost técnico como mostrado no exemplo anterior
        boost_message = f"Similaridade: {original_similarity:.3f} + boost técnico ({tech_keywords[0]})"
        adjusted_score = min(adjusted_score * 1.1, 1.0)  # Boost técnico
        base_justification = boost_message
    
    # Garantir que score não exceda 1.0
    adjusted_score = min(adjusted_score, 1.0)
    
    # 🎯 DECISÃO FINAL PARA NÍVEL HIGH
    should_accept = (
        adjusted_score >= config['threshold_phase1'] and
        avg_specificity >= config.get('min_specificity', 0.5) and
        blacklist_hits <= 2
    )
    
    # Construir categoria de qualidade
    if adjusted_score >= 0.90:
        quality_category = "EXCELENTE"
    elif adjusted_score >= 0.80:
        quality_category = "MUITO_BOM"
    elif adjusted_score >= 0.70:
        quality_category = "BOM"
    elif adjusted_score >= 0.60:
        quality_category = "REGULAR"
    else:
        quality_category = "BAIXO"
    
    # Justificativa melhorada e mais clara
    improved_justification = f"""🎯 ANÁLISE MELHORADA: Score base: {base_score:.3f} → Score ajustado: {adjusted_score:.3f} Qualidade: {quality_category}

📊 Especificidade:
• Licitação: {bid_analysis['specificity_score']:.2f} ({bid_analysis['category']})
• Empresa: {company_analysis['specificity_score']:.2f} ({company_analysis['category']})

🔧 Ajustes aplicados:
{chr(10).join(quality_adjustments) if quality_adjustments else '• Nenhum ajuste aplicado'}

{base_justification}""".strip()
    
    # Análise detalhada
    detailed_analysis = {
        'base_score': base_score,
        'adjusted_score': adjusted_score,
        'quality_category': quality_category,
        'should_accept': should_accept,
        'bid_analysis': bid_analysis,
        'company_analysis': company_analysis,
        'quality_adjustments': quality_adjustments,
        'avg_specificity': avg_specificity,
        'bid_category': bid_analysis['category'],
        'company_category': company_analysis['category'],
        'config_used': config
    }
    
    if return_analysis:
        return adjusted_score, improved_justification, detailed_analysis
    else:
        return adjusted_score, improved_justification

class QualityFilteredBrazilianVectorizer(ImprovedBrazilianTextVectorizer):
    """
    🎯 Vetorizador com filtro automático de qualidade
    Só retorna matches que passam pelos critérios de qualidade
    """
    
    def __init__(self, quality_preset: str = 'conservative'):
        """
        Inicializa com preset conservador por padrão para máxima qualidade
        """
        super().__init__(quality_preset)
        logger.info(f"🛡️ Vetorizador com filtro de qualidade inicializado - Preset: {quality_preset}")
    
    def calculate_filtered_similarity(
        self, 
        bid_embedding: List[float], 
        company_embedding: List[float], 
        bid_text: str, 
        company_text: str
    ) -> Optional[Tuple[float, str, Dict[str, Any]]]:
        """
        Calcula similaridade e retorna apenas se passar pelos filtros de qualidade
        
        Returns:
            None se não passar nos filtros, ou (score, justificativa, análise) se passar
        """
        score, justification, analysis = calculate_improved_similarity(
            bid_embedding, company_embedding, bid_text, company_text, self.quality_preset
        )
        
        if analysis['should_accept']:
            logger.debug(f"✅ Match aceito: {score:.3f} - {analysis['quality_category']}")
            return score, justification, analysis
        else:
            logger.debug(f"❌ Match rejeitado: {score:.3f} - Baixa qualidade")
            return None

def get_vectorizer_for_quality_level(quality_level: str, vectorizer_type: str = "brazilian") -> ImprovedBrazilianTextVectorizer:
    """
    Factory function para criar vetorizador baseado no nível de qualidade desejado
    
    Args:
        quality_level: 'maximum', 'high', 'medium', 'permissive'
        vectorizer_type: 'brazilian', 'hybrid', etc. (sempre retorna brasileiro otimizado)
    """
    preset_mapping = {
        'maximum': 'ultra_selective',
        'high': 'conservative', 
        'medium': 'balanced',
        'permissive': 'aggressive'
    }
    
    preset = preset_mapping.get(quality_level, 'balanced')
    
    # Para nível high, usar vectorizer brasileiro otimizado
    if quality_level == 'high':
        return ImprovedBrazilianTextVectorizer('balanced')  # Preset balanceado para high
    elif quality_level == 'maximum':
        return QualityFilteredBrazilianVectorizer(preset)
    else:
        return ImprovedBrazilianTextVectorizer(preset) 