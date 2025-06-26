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
        """Gera resposta usando OpenAI com fallback automático: gpt-4o-mini -> gpt-4o"""
        try:
            logger.info("🤖 Gerando resposta com OpenAI (4o-mini -> 4o fallback)...")
            
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

            ### 1. PRECISÃO DOCUMENTAL COM REFERÊNCIAS OBRIGATÓRIAS
            - Use EXCLUSIVAMENTE informações do contexto fornecido
            - 🔥 OBRIGATÓRIO: SEMPRE cite a fonte específica no formato: **[Arquivo: nome_do_arquivo.pdf, Página: X]**
            - Para cada informação mencionada, indique EXATAMENTE onde ela está
            - Quando usar trechos específicos, identifique como "conforme trecho X" onde X é o número do trecho
            - Para valores: identifique se são estimados, máximos ou de referência E cite a fonte
            - Destaque prazos, datas e condições temporais críticas COM suas respectivas fontes

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

            ### 4. ESTILO DA RESPOSTA COM REFERÊNCIAS
            - **Seja Conversacional e Direto:** Inicie sua resposta de forma natural, indo direto ao ponto da pergunta. Evite introduções robóticas.
            - **Destaque o Essencial:** Use **negrito** para destacar informações críticas como valores, prazos, nomes e objetos. Isso ajuda na leitura rápida.
            - **Organize com Clareza:** Após a resposta direta, se houver mais detalhes, organize-os em uma lista simples (usando hífens `-`) para facilitar a compreensão. Não use títulos ou seções com `#`.
            - **🔥 EXEMPLO CORRETO DE RESPOSTA COM REFERÊNCIAS:**
                - Pergunta do usuário: "Qual o objeto?"
                - Sua resposta ideal:
                    O objeto da licitação é a **aquisição parcelada de itens de higiene e limpeza** **[Arquivo: edital.pdf, Página: 1]**.
                    
                    Os principais pontos são:
                    - **Finalidade:** Garantir a manutenção da salubridade e segurança para alunos da Rede Municipal de Ensino e outras entidades **[Arquivo: edital.pdf, Página: 2]**.
                    - **Entidades atendidas:** Administração Municipal, Fundo de Saúde, Fundo de Assistência Social e SAMAE **[Arquivo: termo_referencia.pdf, Página: 3]**.
                    - **Localidade:** Município de **Jacinto Machado/SC** **[Arquivo: edital.pdf, Página: 1]**.

            ### 5. QUANDO NÃO SOUBER
            Seja transparente: "Esta informação não está disponível nos documentos fornecidos. Recomendo consultar [documento específico] ou contatar o órgão licitante."

            ### 6. FORMATO OBRIGATÓRIO DE REFERÊNCIAS
            - Para CADA informação citada, use: **[Arquivo: nome_exato_do_arquivo.pdf, Página: X]**
            - Se a informação vem de múltiplos trechos, liste todas as fontes
            - Se não conseguir identificar a página, use: **[Arquivo: nome_do_arquivo.pdf, Página: não identificada]**
            - NUNCA omita as referências de fonte

            ## FOCO NOS RESULTADOS:
            Sua análise deve permitir que a empresa tome decisões informadas sobre:
            - Viabilidade de participação
            - Estratégia de proposta técnica e comercial  
            - Cronograma de preparação
            - Recursos necessários para habilitação
            
            ⚠️ LEMBRE-SE: Toda informação DEVE ter sua fonte citada no formato obrigatório especificado acima.
            """
            
            user_prompt = f"""
            CONTEXTO DOS DOCUMENTOS:
            {context_text}
            
            PERGUNTA: {query}
            
            Responda de forma completa e estruturada, citando as fontes específicas do documento.
            """
            
            # 🎯 TENTATIVA 1: gpt-4o-mini (modelo primário)
            start_time = time.time()
            model_used = "gpt-4o-mini"
            
            try:
                logger.info("🚀 Tentando gpt-4o-mini (modelo primário)...")
                response = self._make_openai_request(system_prompt, user_prompt, model_used)
                logger.info("✅ gpt-4o-mini respondeu com sucesso!")
                
            except Exception as e:
                logger.warning(f"⚠️ gpt-4o-mini falhou: {e}")
                logger.info("🔄 Fazendo fallback para gpt-4o...")
                
                # 🎯 TENTATIVA 2: gpt-4o (fallback)
                model_used = "gpt-4o"
                try:
                    response = self._make_openai_request(system_prompt, user_prompt, model_used)
                    logger.info("✅ gpt-4o (fallback) respondeu com sucesso!")
                    
                except Exception as e2:
                    logger.error(f"❌ gpt-4o também falhou: {e2}")
                    logger.info("🔄 Tentando gpt-3.5-turbo como último recurso...")
                    
                    # 🎯 TENTATIVA 3: gpt-3.5-turbo (último recurso)
                    model_used = "gpt-3.5-turbo"
                    response = self._make_openai_request(system_prompt, user_prompt, model_used)
                    logger.info("✅ gpt-3.5-turbo (último recurso) respondeu!")
            
            response_time = time.time() - start_time
            
            # Extrair resposta
            answer = response.choices[0].message.content
            
            # Calcular custos aproximados baseado no modelo usado
            input_tokens = len(user_prompt.split()) * 1.3  # Aproximação
            output_tokens = len(answer.split()) * 1.3
            cost = self._calculate_cost(model_used, input_tokens, output_tokens)
            
            result = {
                'answer': answer,
                'chunks_used': len(context_chunks),
                'response_time': round(response_time, 2),
                'cost_usd': round(cost, 6),
                'model': model_used,
                'sources': self._extract_sources(context_chunks)
            }
            
            logger.info(f"✅ Resposta gerada em {response_time:.2f}s usando {model_used}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Todos os modelos falharam: {e}")
            return {
                'answer': f"Erro ao gerar resposta: {str(e)}",
                'error': True
            }
    
    def _make_openai_request(self, system_prompt: str, user_prompt: str, model: str):
        """Faz requisição para OpenAI com modelo específico"""
        return self.openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Baixa para respostas mais determinísticas
            max_tokens=1500
        )
    
    def _calculate_cost(self, model: str, input_tokens: float, output_tokens: float) -> float:
        """Calcula custo baseado no modelo usado"""
        # Preços por 1K tokens (janeiro 2025)
        pricing = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
        
        if model in pricing:
            rates = pricing[model]
            return (input_tokens * rates["input"] / 1000) + (output_tokens * rates["output"] / 1000)
        else:
            # Fallback para gpt-3.5-turbo pricing
            return (input_tokens * 0.0015 / 1000) + (output_tokens * 0.002 / 1000)
    
    def _build_context(self, chunks: List[Dict], licitacao_info: Optional[Dict] = None) -> str:
        """Constrói contexto para o LLM com referências de arquivo"""
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
        
        # Adicionar chunks do documento COM nome do arquivo
        for i, chunk in enumerate(chunks, 1):
            # Extrair nome do arquivo do campo document_title ou tentar deduzir
            arquivo_nome = chunk.get('document_title', 'documento_nao_identificado.pdf')
            
            # Se não tem document_title, tentar pegar do metadata ou usar fallback
            if arquivo_nome == 'documento_nao_identificado.pdf':
                arquivo_nome = chunk.get('metadata', {}).get('filename', 'documento_nao_identificado.pdf')
            
            # Garantir que termine com .pdf se não especificado
            if not arquivo_nome.endswith(('.pdf', '.doc', '.docx')):
                arquivo_nome += '.pdf'
            
            context_parts.append(f"""
            TRECHO {i}:
            - Arquivo: {arquivo_nome}
            - Página: {chunk.get('page_number', 'não identificada')}
            - Conteúdo:
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