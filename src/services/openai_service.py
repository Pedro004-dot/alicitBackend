"""
OpenAI Service
Serviço para integração com a API da OpenAI para enriquecimento de buscas.
"""
import os
import openai
from typing import List
import logging

# Configurar o logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Serviço para interagir com a OpenAI.
    Adaptado para um ambiente síncrono (Flask).
    """
    
    def __init__(self):
        """
        Inicializa o cliente da OpenAI.
        A API key é lida da variável de ambiente OPENAI_API_KEY.
        """
        api_key = os.getenv('OPENAI_API_KEY')

        # 🔄 Fallback: tentar carregar automaticamente o config.env da raiz do backend
        if not api_key:
            try:
                from pathlib import Path
                from dotenv import load_dotenv

                project_root = Path(__file__).parent.parent.parent  # .../backend/src -> ../..
                env_path = project_root / 'config.env'

                if env_path.exists():
                    load_dotenv(env_path)
                    api_key = os.getenv('OPENAI_API_KEY')
                    logger.info(f"🔄 OPENAI_API_KEY carregada via fallback de {env_path}")
            except Exception as e:
                logger.warning(f"⚠️ Fallback load_dotenv falhou: {e}")

        if not api_key:
            logger.error("❌ A variável de ambiente OPENAI_API_KEY não foi definida.")
            raise ValueError("API key da OpenAI não encontrada.")
            
        self.client = openai.OpenAI(api_key=api_key)
    
    def gerar_sinonimos(self, palavra_chave: str, max_sinonimos: int = 5) -> List[str]:
        """
        Gera sinônimos e termos relevantes para a palavra-chave usando a API da OpenAI.
        
        Args:
            palavra_chave: A palavra ou termo principal para o qual gerar sinônimos.
            max_sinonimos: O número máximo de sinônimos a serem gerados.
            
        Returns:
            Uma lista de sinônimos, incluindo a palavra-chave original.
        """
        try:
            prompt = f"""
            Gere até {max_sinonimos} sinônimos ou termos diretamente relacionados para a palavra-chave '{palavra_chave}'.
            O contexto é de licitações e compras governamentais no Brasil.
            Foque em termos que seriam usados em editais.

            Sua resposta deve ser apenas uma lista de palavras separadas por vírgula, sem numeração, explicações ou qualquer outro texto.
            Exemplo para 'computador': desktop, microcomputador, PC, estação de trabalho, all-in-one
            """
            
            logger.info(f"Gerando sinônimos para '{palavra_chave}'...")
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um assistente especialista em terminologia de licitações públicas no Brasil e retorna apenas listas de palavras separadas por vírgula."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=100
            )
            
            sinonimos_text = response.choices[0].message.content.strip()
            
            # Limpa e formata a lista de sinônimos
            sinonimos = [s.strip() for s in sinonimos_text.split(',') if s.strip()]
            
            # Garante que a palavra original esteja na lista, preferencialmente no início
            palavra_chave_lower = palavra_chave.lower()
            sinonimos_lower = [s.lower() for s in sinonimos]
            
            if palavra_chave_lower in sinonimos_lower:
                # Remove a duplicata para reinserir no início
                sinonimos = [s for s in sinonimos if s.lower() != palavra_chave_lower]
            
            sinonimos.insert(0, palavra_chave)
            
            final_list = sinonimos[:max_sinonimos + 1]
            
            logger.info(f"✅ Sinônimos gerados para '{palavra_chave}': {final_list}")
            return final_list
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sinônimos para '{palavra_chave}': {str(e)}")
            # Em caso de qualquer erro, retorna apenas a palavra-chave original para não quebrar a busca
            return [palavra_chave]

# Exemplo de uso (para teste)
if __name__ == '__main__':
    # Para testar, defina a variável de ambiente: export OPENAI_API_KEY='sua_chave_aqui'
    try:
        service = OpenAIService()
        
        palavra1 = "software de gestão"
        sinonimos1 = service.gerar_sinonimos(palavra1)
        print(f"Palavra: {palavra1}\nSinônimos: {sinonimos1}\n")
        
        palavra2 = "cadeira de escritório"
        sinonimos2 = service.gerar_sinonimos(palavra2, max_sinonimos=3)
        print(f"Palavra: {palavra2}\nSinônimos: {sinonimos2}\n")
        
    except ValueError as e:
        print(e)
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}") 