#!/usr/bin/env python3
"""
Script de Diagnóstico do RAG
Verifica se todos os documentos de uma licitação estão sendo processados corretamente
"""

import os
import sys
import logging
from datetime import datetime

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

def main():
    """Função principal de diagnóstico"""
    try:
        print("🔍 DIAGNÓSTICO DO RAG - AlicitSaas")
        print("=" * 50)
        
        # Configurações
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY') 
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        if not all([supabase_url, supabase_key, openai_api_key]):
            print("❌ Variáveis de ambiente necessárias não encontradas:")
            print("   - SUPABASE_URL")
            print("   - SUPABASE_ANON_KEY") 
            print("   - OPENAI_API_KEY")
            return
        
        # Inicializar serviços
        print("🔧 Inicializando serviços...")
        db_manager = DatabaseManager()
        unified_processor = UnifiedDocumentProcessor(db_manager, supabase_url, supabase_key)
        rag_service = RAGService(db_manager, unified_processor, openai_api_key)
        
        # Solicitar ID da licitação
        licitacao_id = input("\n📋 Digite o ID da licitação para diagnóstico: ").strip()
        
        if not licitacao_id:
            print("❌ ID da licitação é obrigatório")
            return
        
        print(f"\n🔍 Executando diagnóstico para: {licitacao_id}")
        print("-" * 40)
        
        # 1. Executar diagnóstico completo
        resultado = rag_service.diagnose_licitacao_documents(licitacao_id)
        
        if not resultado['success']:
            print(f"❌ Erro no diagnóstico: {resultado['error']}")
            return
        
        # 2. Exibir resultados
        resumo = resultado['resumo']
        detalhes = resultado['documentos_detalhes']
        recomendacoes = resultado['recomendacoes']
        
        print("\n📊 RESUMO GERAL:")
        print(f"   Total de documentos: {resumo['total_documentos']}")
        print(f"   Documentos vetorizados: {resumo['documentos_vetorizados']}")
        print(f"   Documentos com problema: {resumo['documentos_com_problema']}")
        print(f"   Total de chunks gerados: {resumo['total_chunks_gerados']}")
        print(f"   Taxa de sucesso: {resumo['percentual_sucesso']}%")
        
        print("\n📄 DETALHES POR DOCUMENTO:")
        for i, doc in enumerate(detalhes, 1):
            print(f"\n{i}. {doc['titulo']}")
            print(f"   Status: {doc['status']}")
            print(f"   Chunks: {doc['chunks_count']}")
            print(f"   Tamanho: {doc['tamanho_arquivo']:,} bytes")
            print(f"   Tipo: {doc['tipo_arquivo']}")
            print(f"   URL: {doc['url_preview']}")
        
        if recomendacoes:
            print("\n💡 RECOMENDAÇÕES:")
            for rec in recomendacoes:
                print(f"   {rec}")
        
        # 3. Teste de query se tudo estiver OK
        if resumo['documentos_com_problema'] == 0 and resumo['total_chunks_gerados'] > 0:
            print("\n🤖 Sistema parece estar funcionando. Quer testar uma query? (s/N): ", end="")
            resposta = input().strip().lower()
            
            if resposta in ['s', 'sim', 'y', 'yes']:
                query = input("\n❓ Digite sua pergunta: ").strip()
                if query:
                    print("\n🔄 Processando query...")
                    resultado_query = rag_service.process_or_query(licitacao_id, query)
                    
                    if resultado_query['success']:
                        print(f"\n✅ Resposta ({resultado_query.get('processing_time', 0)}s):")
                        print(f"   {resultado_query['answer']}")
                        print(f"\n📚 Chunks utilizados: {resultado_query.get('chunks_used', 0)}")
                        print(f"💰 Custo: ${resultado_query.get('cost_usd', 0):.6f}")
                    else:
                        print(f"\n❌ Erro na query: {resultado_query['error']}")
        
        print(f"\n🎉 Diagnóstico concluído em {datetime.now().strftime('%H:%M:%S')}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ Diagnóstico interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no diagnóstico: {e}")
        logger.error(f"Erro no diagnóstico: {e}", exc_info=True)

if __name__ == "__main__":
    main() 