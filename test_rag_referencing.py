#!/usr/bin/env python3
"""
🧪 Teste das Referências do RAG
Verifica se o sistema agora inclui corretamente:
- Nome do arquivo
- Número da página  
- Referências específicas nas respostas
"""

import os
import sys
import logging

# Adicionar o diretório src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.db_manager import DatabaseManager
from services.rag_service import RAGService
from core.unified_document_processor import UnifiedDocumentProcessor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_rag_referencing():
    """Testa se as referências estão funcionando"""
    try:
        print("🧪 TESTE DE REFERÊNCIAS DO RAG")
        print("=" * 50)
        
        # Configurar serviços
        db_manager = DatabaseManager()
        
        # URLs e chaves do ambiente
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not all([supabase_url, supabase_key, openai_api_key]):
            print("❌ Variáveis de ambiente necessárias não encontradas")
            return
        
        # Inicializar serviços
        unified_processor = UnifiedDocumentProcessor(db_manager, supabase_url, supabase_key)
        rag_service = RAGService(db_manager, unified_processor, openai_api_key)
        
        # ID da licitação de teste
        licitacao_id = "ccebcceb-866b-481a-8d35-2e7854e2d073"
        
        print(f"🎯 Testando licitação: {licitacao_id}")
        print()
        
        # Teste 1: Pergunta sobre PAC
        print("1️⃣ TESTE: Pergunta sobre PAC (deveria encontrar agora)")
        print("-" * 40)
        
        query1 = "A licitação está incluída no PAC?"
        resultado1 = rag_service.process_or_query(licitacao_id, query1)
        
        if resultado1['success']:
            print(f"✅ Resposta gerada com sucesso!")
            print(f"📄 Chunks usados: {resultado1.get('chunks_used', 0)}")
            print(f"⏱️ Tempo: {resultado1.get('processing_time', 'N/A')}s")
            print(f"🤖 Modelo: {resultado1.get('model', 'N/A')}")
            print()
            print("📝 RESPOSTA:")
            print(resultado1['answer'])
            print()
            print("📊 FONTES:")
            for i, source in enumerate(resultado1.get('sources', []), 1):
                print(f"   {i}. Página: {source.get('page_number', 'N/A')}, Score: {source.get('score', 'N/A'):.3f}")
        else:
            print(f"❌ Erro: {resultado1.get('error')}")
        
        print("\n" + "=" * 50)
        
        # Teste 2: Pergunta sobre objeto
        print("2️⃣ TESTE: Pergunta sobre objeto da licitação")
        print("-" * 40)
        
        query2 = "Qual o objeto desta licitação?"
        resultado2 = rag_service.process_or_query(licitacao_id, query2)
        
        if resultado2['success']:
            print(f"✅ Resposta gerada com sucesso!")
            print(f"📄 Chunks usados: {resultado2.get('chunks_used', 0)}")
            print()
            print("📝 RESPOSTA:")
            print(resultado2['answer'])
        else:
            print(f"❌ Erro: {resultado2.get('error')}")
        
        print("\n" + "=" * 50)
        
        # Teste 3: Análise das referências
        print("3️⃣ ANÁLISE: Verificando se referências estão presentes")
        print("-" * 40)
        
        for i, (query, resultado) in enumerate([(query1, resultado1), (query2, resultado2)], 1):
            print(f"\nTeste {i}: {query}")
            
            if resultado['success']:
                resposta = resultado['answer']
                
                # Verificar se tem referências no formato esperado
                tem_referencia_arquivo = '[Arquivo:' in resposta
                tem_referencia_pagina = 'Página:' in resposta
                tem_trecho = 'trecho' in resposta.lower()
                
                print(f"   📄 Referência de arquivo: {'✅' if tem_referencia_arquivo else '❌'}")
                print(f"   📃 Referência de página: {'✅' if tem_referencia_pagina else '❌'}")
                print(f"   📝 Menciona trechos: {'✅' if tem_trecho else '❌'}")
                
                if tem_referencia_arquivo and tem_referencia_pagina:
                    print(f"   🎉 SUCESSO: Referências completas encontradas!")
                else:
                    print(f"   ⚠️ ATENÇÃO: Referências incompletas")
            else:
                print(f"   ❌ Teste falhou")
        
        print("\n🏁 TESTE CONCLUÍDO!")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        logger.error(f"Erro no teste de referências: {e}")

if __name__ == "__main__":
    test_rag_referencing() 