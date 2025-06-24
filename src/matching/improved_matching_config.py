#!/usr/bin/env python3
"""
🎯 CONFIGURAÇÃO MELHORADA PARA MATCHING DE ALTA QUALIDADE
Sistema com thresholds mais seletivos e análise semântica aprimorada
"""

import os
from typing import Dict, List, Tuple
import re

# ========== THRESHOLDS MELHORADOS ==========

# 🔥 NOVO: Thresholds mais seletivos para matches de qualidade
SIMILARITY_THRESHOLD_PHASE1_HIGH_QUALITY = 0.78  # Antes: 0.65
SIMILARITY_THRESHOLD_PHASE2_HIGH_QUALITY = 0.82  # Antes: 0.70

# 🎯 Thresholds por categoria de negócio
CATEGORY_THRESHOLDS = {
    'tecnologia_ti': {
        'phase1': 0.75,
        'phase2': 0.80,
        'keywords': ['software', 'sistema', 'desenvolvimento', 'tecnologia', 'TI', 'informática', 'programação']
    },
    'construcao_engenharia': {
        'phase1': 0.72,
        'phase2': 0.78,
        'keywords': ['construção', 'obra', 'engenharia', 'reforma', 'infraestrutura', 'pavimentação']
    },
    'saude_medicamentos': {
        'phase1': 0.80,  # Mais restritivo por ser área crítica
        'phase2': 0.85,
        'keywords': ['medicamento', 'saúde', 'hospitalar', 'médico', 'farmácia', 'equipamento médico']
    },
    'servicos_gerais': {
        'phase1': 0.70,
        'phase2': 0.75,
        'keywords': ['limpeza', 'vigilância', 'segurança', 'manutenção', 'conservação']
    },
    'fornecimento_materiais': {
        'phase1': 0.68,
        'phase2': 0.73,
        'keywords': ['fornecimento', 'aquisição', 'material', 'equipamento', 'suprimento']
    }
}

# ========== FILTROS DE QUALIDADE ==========

# 🚫 Palavras que indicam matches muito genéricos (BLACKLIST)
GENERIC_TERMS_BLACKLIST = [
    'diversos', 'vários', 'geral', 'múltiplos', 'conforme necessidade',
    'entre outros', 'demais', 'variados', 'eventuais', 'outras atividades'
]

# ✅ Indicadores de matches específicos (WHITELIST)
SPECIFIC_TERMS_WHITELIST = [
    'CNPJ', 'especializado', 'certificado', 'técnico', 'qualificado',
    'experiência comprovada', 'atestado', 'registro profissional'
]

# 🔍 Regex patterns para identificar especificidade
SPECIFICITY_PATTERNS = [
    r'\d+\s*(anos?|meses?)\s*(de\s*)?(experiência|atuação)',  # "3 anos de experiência"
    r'certificad[oa]\s+(em|para|de)',  # "certificado em"
    r'registro\s+(no|na|do|da)\s+\w+',  # "registro no CREA"
    r'norma\s+(NBR|ISO|ABNT)',  # "norma NBR 1234"
    r'capacidade\s+(mínima|de)\s+\d+',  # "capacidade mínima de 100"
]

# ========== PESOS PARA ANÁLISE SEMÂNTICA ==========

SEMANTIC_WEIGHTS = {
    'exact_match': 1.0,        # Termos exatos
    'synonym_match': 0.9,      # Sinônimos
    'category_match': 0.8,     # Mesma categoria
    'related_match': 0.6,      # Termos relacionados
    'generic_match': 0.3       # Matches genéricos
}

# ========== CONFIGURAÇÕES AVANÇADAS ==========

class QualityMatchingConfig:
    """Configuração melhorada para matching de alta qualidade"""
    
    @staticmethod
    def get_threshold_for_bid(objeto_compra: str, company_description: str) -> Tuple[float, float]:
        """
        Retorna thresholds personalizados baseados no conteúdo da licitação e empresa
        """
        objeto_lower = objeto_compra.lower()
        company_lower = company_description.lower()
        
        # Verificar categoria do negócio
        for category, config in CATEGORY_THRESHOLDS.items():
            if any(keyword in objeto_lower for keyword in config['keywords']):
                return config['phase1'], config['phase2']
        
        # Threshold padrão mais alto
        return SIMILARITY_THRESHOLD_PHASE1_HIGH_QUALITY, SIMILARITY_THRESHOLD_PHASE2_HIGH_QUALITY
    
    @staticmethod
    def calculate_specificity_score(text: str) -> float:
        """
        Calcula score de especificidade do texto (0.0 - 1.0)
        Textos mais específicos = scores mais altos
        """
        text_lower = text.lower()
        score = 0.5  # Base score
        
        # 🚫 Penalizar termos genéricos
        generic_count = sum(1 for term in GENERIC_TERMS_BLACKLIST if term in text_lower)
        score -= generic_count * 0.1
        
        # ✅ Bonificar termos específicos
        specific_count = sum(1 for term in SPECIFIC_TERMS_WHITELIST if term in text_lower)
        score += specific_count * 0.15
        
        # 🔍 Bonificar patterns de especificidade
        pattern_count = sum(1 for pattern in SPECIFICITY_PATTERNS if re.search(pattern, text_lower))
        score += pattern_count * 0.2
        
        # 📏 Considerar tamanho do texto (textos muito curtos são suspeitos)
        if len(text) < 50:
            score -= 0.2
        elif len(text) > 200:
            score += 0.1
        
        return max(0.0, min(1.0, score))
    
    @staticmethod
    def should_accept_match(score: float, objeto_compra: str, company_description: str) -> bool:
        """
        Decide se um match deve ser aceito baseado em critérios de qualidade
        """
        # Calcular especificidade
        bid_specificity = QualityMatchingConfig.calculate_specificity_score(objeto_compra)
        company_specificity = QualityMatchingConfig.calculate_specificity_score(company_description)
        
        # Threshold dinâmico baseado na especificidade
        phase1_threshold, _ = QualityMatchingConfig.get_threshold_for_bid(objeto_compra, company_description)
        
        # Ajustar threshold baseado na especificidade
        avg_specificity = (bid_specificity + company_specificity) / 2
        adjusted_threshold = phase1_threshold + (avg_specificity - 0.5) * 0.1
        
        return score >= adjusted_threshold
    
    @staticmethod
    def get_match_quality_category(score: float) -> str:
        """Categoriza a qualidade do match"""
        if score >= 0.90:
            return "EXCELENTE"
        elif score >= 0.80:
            return "MUITO_BOM"
        elif score >= 0.70:
            return "BOM"
        elif score >= 0.60:
            return "REGULAR"
        else:
            return "BAIXO"

# ========== PRESETS DE CONFIGURAÇÃO ==========

QUALITY_PRESETS = {
    'conservative': {
        'phase1_threshold': 0.80,
        'phase2_threshold': 0.85,
        'description': 'Apenas matches de alta confiança'
    },
    'balanced': {
        'phase1_threshold': 0.75,
        'phase2_threshold': 0.80,
        'description': 'Equilibrio entre quantidade e qualidade'
    },
    'aggressive': {
        'phase1_threshold': 0.70,
        'phase2_threshold': 0.75,
        'description': 'Mais matches, qualidade moderada'
    },
    'ultra_selective': {
        'phase1_threshold': 0.85,
        'phase2_threshold': 0.90,
        'description': 'Apenas matches perfeitos'
    }
}

def get_active_preset() -> str:
    """Retorna o preset ativo baseado na variável de ambiente"""
    return os.getenv('MATCHING_QUALITY_PRESET', 'balanced')

def get_preset_config(preset_name: str = None) -> Dict:
    """Retorna configuração do preset especificado"""
    if preset_name is None:
        preset_name = get_active_preset()
    
    return QUALITY_PRESETS.get(preset_name, QUALITY_PRESETS['balanced'])


# ========== CONFIGURAÇÕES POR NÍVEL DE QUALIDADE ==========

def get_quality_config(quality_level: str = "high") -> Dict:
    """
    🎯 CONFIGURAÇÃO OTIMIZADA PARA MATCHES CERTEIROS
    
    Retorna configuração específica para cada nível de qualidade
    Nível 'high' é otimizado para 45-55% de taxa de match com alta precisão
    """
    
    if quality_level == "maximum":
        # Máxima seletividade - apenas matches perfeitos (~30-40%)
        return {
            'threshold_phase1': 0.85,
            'threshold_phase2': 0.90,
            'min_specificity': 0.7,
            'blacklist_terms': GENERIC_TERMS_BLACKLIST + ['geral', 'outros', 'demais'],
            'whitelist_terms': SPECIFIC_TERMS_WHITELIST + ['especialista', 'expert', 'credenciado'],
            'category_thresholds': {k: {'phase1': v['phase1'] + 0.1, 'phase2': v['phase2'] + 0.1} 
                                  for k, v in CATEGORY_THRESHOLDS.items()},
            'description': 'Apenas matches perfeitos e altamente específicos'
        }
    
    elif quality_level == "high":
        # 🎯 CONFIGURAÇÃO OTIMIZADA PARA MATCHES CERTEIROS
        # Alta qualidade equilibrada - matches certeiros (~45-55%)
        return {
            'threshold_phase1': 0.78,  # Mais seletivo que o anterior (0.65)
            'threshold_phase2': 0.82,  # Mais seletivo que o anterior (0.70)
            'min_specificity': 0.5,    # Exige especificidade mínima
            'blacklist_terms': GENERIC_TERMS_BLACKLIST,
            'whitelist_terms': SPECIFIC_TERMS_WHITELIST,
            'category_thresholds': CATEGORY_THRESHOLDS,
            'quality_boost': {
                # Boost para matches com palavras-chave técnicas
                'tecnologia': 0.05,
                'desenvolvimento': 0.05,
                'especializado': 0.03,
                'certificado': 0.03,
                'experiência': 0.02
            },
            'penalty_multiplier': 0.8,  # Penalização para textos genéricos
            'description': 'Alta qualidade equilibrada - matches certeiros e confiáveis'
        }
    
    elif quality_level == "medium":
        # Qualidade média - mais permissivo (~60-70%)
        return {
            'threshold_phase1': 0.72,
            'threshold_phase2': 0.76,
            'min_specificity': 0.3,
            'blacklist_terms': GENERIC_TERMS_BLACKLIST[:5],  # Menos termos na blacklist
            'whitelist_terms': SPECIFIC_TERMS_WHITELIST,
            'category_thresholds': {k: {'phase1': v['phase1'] - 0.05, 'phase2': v['phase2'] - 0.05} 
                                  for k, v in CATEGORY_THRESHOLDS.items()},
            'description': 'Qualidade média com mais permissividade'
        }
    
    elif quality_level == "permissive":
        # Mais permissivo - compatibilidade com sistema anterior (~75-85%)
        return {
            'threshold_phase1': 0.65,  # Threshold original
            'threshold_phase2': 0.70,  # Threshold original
            'min_specificity': 0.2,
            'blacklist_terms': GENERIC_TERMS_BLACKLIST[:3],  # Mínimo de filtros
            'whitelist_terms': SPECIFIC_TERMS_WHITELIST,
            'category_thresholds': {k: {'phase1': v['phase1'] - 0.1, 'phase2': v['phase2'] - 0.1} 
                                  for k, v in CATEGORY_THRESHOLDS.items()},
            'description': 'Modo permissivo similar ao sistema anterior'
        }
    
    else:
        # Default para 'high' se nível inválido
        return get_quality_config("high") 