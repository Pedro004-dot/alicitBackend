"""
Synonym Service - Provider-agnostic search term expansion

This utility service generates synonyms and related terms for search keywords
using various AI providers. It is designed to be reused across all search providers.
"""
import os
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SynonymService:
    """
    Service for generating search synonyms using AI providers
    
    This service provides a provider-agnostic way to expand search terms
    and can be used by any procurement data source adapter.
    """
    
    def __init__(self):
        """Initialize the synonym service with available AI providers"""
        self.openai_available = bool(os.getenv('OPENAI_API_KEY'))
        self.client = None
        
        if self.openai_available:
            try:
                import openai
                self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                logger.info("✅ SynonymService initialized with OpenAI")
            except ImportError:
                logger.warning("OpenAI library not available")
                self.openai_available = False
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.openai_available = False
        
        if not self.openai_available:
            logger.warning("⚠️ No AI providers available for synonym generation")
    
    def generate_synonyms(self, keyword: str, max_synonyms: int = 5) -> List[str]:
        """
        Generate synonyms and related terms for a keyword
        
        Args:
            keyword: The keyword to expand
            max_synonyms: Maximum number of synonyms to generate
            
        Returns:
            List of terms including the original keyword and synonyms
        """
        if not keyword or not keyword.strip():
            return []
        
        # Always include the original keyword
        result_terms = [keyword.strip()]
        
        # Try to generate synonyms using available providers
        synonyms = self._generate_with_openai(keyword, max_synonyms)
        
        if synonyms:
            # Add unique synonyms that are not already in the result
            for synonym in synonyms:
                if synonym and synonym.lower() not in [term.lower() for term in result_terms]:
                    result_terms.append(synonym)
                    if len(result_terms) >= max_synonyms + 1:  # +1 for original keyword
                        break
        
        logger.info(f"🔤 Generated {len(result_terms)} terms for '{keyword}': {result_terms}")
        return result_terms
    
    def _generate_with_openai(self, keyword: str, max_synonyms: int) -> List[str]:
        """Generate synonyms using OpenAI"""
        if not self.openai_available or not self.client:
            return []
        
        try:
            prompt = f"""
            Gere até {max_synonyms} sinônimos ou termos diretamente relacionados para a palavra-chave '{keyword}'.
            O contexto é de licitações e compras governamentais no Brasil.
            Foque em termos que seriam usados em editais públicos.

            Sua resposta deve ser apenas uma lista de palavras separadas por vírgula, sem numeração, explicações ou qualquer outro texto.
            Exemplo para 'computador': desktop, microcomputador, PC, estação de trabalho, all-in-one
            """
            
            logger.debug(f"🔤 Generating synonyms for '{keyword}' using OpenAI...")
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um assistente especialista em terminologia de licitações públicas no Brasil e retorna apenas listas de palavras separadas por vírgula."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=100
            )
            
            synonyms_text = response.choices[0].message.content.strip()
            
            # Parse and clean the synonyms
            synonyms = [s.strip() for s in synonyms_text.split(',') if s.strip()]
            
            # Remove the original keyword if it appears in synonyms
            keyword_lower = keyword.lower()
            synonyms = [s for s in synonyms if s.lower() != keyword_lower]
            
            logger.debug(f"✅ OpenAI generated {len(synonyms)} synonyms: {synonyms}")
            return synonyms[:max_synonyms]
            
        except Exception as e:
            logger.error(f"❌ Error generating synonyms with OpenAI: {e}")
            return []
    
    def expand_search_terms(self, terms: List[str], max_synonyms_per_term: int = 3) -> List[str]:
        """
        Expand a list of search terms with synonyms
        
        Args:
            terms: List of original search terms
            max_synonyms_per_term: Maximum synonyms to generate per term
            
        Returns:
            Expanded list of terms including originals and synonyms
        """
        if not terms:
            return []
        
        expanded_terms = []
        
        for term in terms:
            if term and term.strip():
                term_variants = self.generate_synonyms(term.strip(), max_synonyms_per_term)
                expanded_terms.extend(term_variants)
        
        # Remove duplicates while preserving order
        unique_terms = []
        seen = set()
        for term in expanded_terms:
            term_lower = term.lower()
            if term_lower not in seen:
                unique_terms.append(term)
                seen.add(term_lower)
        
        logger.info(f"🔤 Expanded {len(terms)} terms to {len(unique_terms)} terms")
        return unique_terms
    
    def is_available(self) -> bool:
        """Check if synonym generation is available"""
        return self.openai_available


# Create a global instance for easy importing
synonym_service = SynonymService()


def generate_synonyms(keyword: str, max_synonyms: int = 5) -> List[str]:
    """
    Convenience function for generating synonyms
    
    Args:
        keyword: The keyword to expand
        max_synonyms: Maximum number of synonyms to generate
        
    Returns:
        List of terms including the original keyword and synonyms
    """
    return synonym_service.generate_synonyms(keyword, max_synonyms)


def expand_search_terms(terms: List[str], max_synonyms_per_term: int = 3) -> List[str]:
    """
    Convenience function for expanding search terms
    
    Args:
        terms: List of original search terms
        max_synonyms_per_term: Maximum synonyms to generate per term
        
    Returns:
        Expanded list of terms including originals and synonyms
    """
    return synonym_service.expand_search_terms(terms, max_synonyms_per_term) 