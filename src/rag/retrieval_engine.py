# Retrieval engine module 

import openai
import logging
from typing import List, Dict, Any, Optional
import time
import numpy as np

logger = logging.getLogger(__name__)

class RetrievalEngine:
    """Engine de retrieval com reranking"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
        # Modelo de reranking
        self.reranker = None
        self._load_reranker()
    
    def _load_reranker(self):
        """Reranking desabilitado - usando apenas similaridade semântica"""
        logger.info("⚠️  Reranking com CrossEncoder desabilitado (removido sentence-transformers)")
        logger.info("💡 Usando apenas scores de similaridade semântica para ordenação")
        self.reranker = None
    
    def rerank_chunks(self, query: str, chunks: List[Dict], top_k: int = 8) -> List[Dict]:
        """Ordena chunks por similaridade semântica (reranking desabilitado)"""
        try:
            logger.info(f"🔄 Ordenando {len(chunks)} chunks por similaridade semântica")
            
            # Usar score de similaridade existente como score final
            for chunk in chunks:
                original_score = chunk.get('hybrid_score', chunk.get('similarity_score', 0))
                chunk['final_score'] = original_score
                chunk['rerank_score'] = None  # Reranking desabilitado
            
            # Ordenar por score de similaridade
            sorted_chunks = sorted(chunks, key=lambda x: x['final_score'], reverse=True)
            
            logger.info(f"✅ Chunks ordenados por similaridade, retornando top {top_k}")
            return sorted_chunks[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Erro na ordenação: {e}")
            return chunks[:top_k]
    
    def generate_response(self, query: str, context_chunks: List[Dict], 
                         licitacao_info: Optional[Dict] = None) -> Dict[str, Any]:
        """Gera resposta usando OpenAI GPT-4"""
        try:
            logger.info("🤖 Gerando resposta com GPT-4...")
            
            # Construir contexto
            context_text = self._build_context(context_chunks, licitacao_info)
            
            # Prompt otimizado para licitações
            system_prompt = """Você é um especialista sênior em licitações públicas brasileiras com 15+ anos de experiência em análise de editais, participação em concorrências e assessoria jurídica licitatória.
            ## SEU PAPEL:
            Analisar documentos licitatórios e fornecer insights estratégicos para maximizar as chances de sucesso em licitações públicas.

            ## CONHECIMENTO ESPECIALIZADO:
            - Lei 8.666/93, Lei 14.133/21 (Nova Lei de Licitações), Decreto 10.024/19
            - Modalidades: Pregão, Concorrência, Tomada de Preços, Convite, RDC, Diálogo Competitivo
            - Habilitação técnica, econômico-financeira, jurídica e regularidade fiscal
            - Critérios de julgamento, impugnações, recursos administrativos
            - Análise de riscos contratuais e cláusulas restritivas

            ## INSTRUÇÕES DE ANÁLISE:

            ### 1. PRECISÃO DOCUMENTAL
            - Use EXCLUSIVAMENTE informações do contexto fornecido
            - Cite SEMPRE: página, seção, item, subitem ou cláusula específica
            - Para valores: identifique se são estimados, máximos ou de referência
            - Destaque prazos, datas e condições temporais críticas

            ### 2. ANÁLISE ESTRATÉGICA
            - Identifique requisitos obrigatórios vs desejáveis
            - Destaque potenciais impedimentos ou dificuldades
            - Sinalize cláusulas que podem restringir competitividade
            - Avalie complexidade técnica e exigências específicas

            ### 3. ALERTAS CRÍTICOS
            - Marque com ⚠️ ALERTA quando identificar:
            * Exigências possivelmente restritivas ou desproporcionais
            * Prazos apertados ou incompatíveis
            * Contradições entre documentos
            * Critérios subjetivos de julgamento
            * Cláusulas que favoreçam empresa específica

            ### 4. FORMATAÇÃO ESTRUTURADA
            - Destaque informações críticas em **negrito**
            - Liste requisitos em bullet points
            - Separe análise técnica de análise comercial
            - Seja claro e objetivo, não seja redundante
            - Sua estrutura deve ser como uma resposta de um especialista em licitações, com títulos, subtítulos, listas, etc.

            ### 5. QUANDO NÃO SOUBER
            Seja transparente: "Esta informação não está disponível nos documentos fornecidos. Recomendo consultar [documento específico] ou contatar o órgão licitante."

            ## FOCO NOS RESULTADOS:
            Sua análise deve permitir que a empresa tome decisões informadas sobre:
            - Viabilidade de participação
            - Estratégia de proposta técnica e comercial  
            - Cronograma de preparação
            - Recursos necessários para habilitação
            """
            
            user_prompt = f"""
            CONTEXTO DOS DOCUMENTOS:
            {context_text}
            
            PERGUNTA: {query}
            
            Responda de forma completa e estruturada, citando as fontes específicas do documento.
            """
            
            # Fazer chamada para OpenAI
            start_time = time.time()
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Mais barato que gpt-4
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Baixa para respostas mais determinísticas
                max_tokens=1500
            )
            
            response_time = time.time() - start_time
            
            # Extrair resposta
            answer = response.choices[0].message.content
            
            # Calcular custos aproximados (preços de janeiro 2025)
            input_tokens = len(user_prompt.split()) * 1.3  # Aproximação
            output_tokens = len(answer.split()) * 1.3
            
            # GPT-4o-mini: $0.00015/1K input, $0.0006/1K output
            cost = (input_tokens * 0.00015 / 1000) + (output_tokens * 0.0006 / 1000)
            
            result = {
                'answer': answer,
                'chunks_used': len(context_chunks),
                'response_time': round(response_time, 2),
                'cost_usd': round(cost, 6),
                'model': "gpt-4o-mini",
                'sources': self._extract_sources(context_chunks)
            }
            
            logger.info(f"✅ Resposta gerada em {response_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar resposta: {e}")
            return {
                'answer': f"Erro ao gerar resposta: {str(e)}",
                'error': True
            }
    
    def _build_context(self, chunks: List[Dict], licitacao_info: Optional[Dict] = None) -> str:
        """Constrói contexto para o LLM"""
        context_parts = []
        
        # Adicionar informações da licitação se disponível
        if licitacao_info:
            context_parts.append(f"""
            INFORMAÇÕES DA LICITAÇÃO:
            - Objeto: {licitacao_info.get('objeto_compra', 'N/A')}
            - Modalidade: {licitacao_info.get('modalidade_nome', 'N/A')}
            - Valor Total Estimado: R$ {licitacao_info.get('valor_total_estimado', 'N/A')}
            - Órgão: {licitacao_info.get('orgao_entidade', 'N/A')}
            - UF: {licitacao_info.get('uf', 'N/A')}
            """)
        
        # Adicionar chunks do documento
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"""
            TRECHO {i} (Página {chunk.get('page_number', 'N/A')}):
            {chunk['text']}
            """)
        
        return "\n".join(context_parts)
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """Extrai informações de fonte dos chunks"""
        sources = []
        for chunk in chunks:
            source = {
                'page_number': chunk.get('page_number'),
                'chunk_type': chunk.get('chunk_type'),
                'section_title': chunk.get('section_title'),
                'score': chunk.get('final_score', chunk.get('hybrid_score', 0))
            }
            sources.append(source)
        
        return sources 