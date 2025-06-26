#!/usr/bin/env python3
"""
🔧 Script para Corrigir Reprocessamento de Documentos
Identifica e corrige documentos que estão sendo reprocessados infinitamente no RAG
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
    """Função principal de correção"""
    try:
        print("🔧 CORREÇÃO DE REPROCESSAMENTO DE DOCUMENTOS")
        print("=" * 60)
        
        # Configurar serviços
        print("🔄 Inicializando serviços...")
        db_manager = DatabaseManager()
        unified_processor = UnifiedDocumentProcessor(
            db_manager, 
            os.getenv('SUPABASE_URL'), 
            os.getenv('SUPABASE_ANON_KEY')
        )
        rag_service = RAGService(
            db_manager, 
            unified_processor, 
            os.getenv('OPENAI_API_KEY')
        )
        
        # Solicitar licitação ID
        licitacao_id = input("\n📋 Digite o ID da licitação para analisar: ").strip()
        
        if not licitacao_id:
            print("❌ ID da licitação é obrigatório!")
            return
        
        print(f"\n🔍 Analisando licitação: {licitacao_id}")
        
        # 1. Executar diagnóstico completo
        print("\n1️⃣ DIAGNÓSTICO COMPLETO")
        print("-" * 30)
        diagnostico = rag_service.diagnose_licitacao_documents(licitacao_id)
        
        if not diagnostico['success']:
            print(f"❌ Erro no diagnóstico: {diagnostico['error']}")
            return
        
        resumo = diagnostico['resumo']
        print(f"📊 Total de documentos: {resumo['total_documentos']}")
        print(f"✅ Documentos vetorizados: {resumo['documentos_vetorizados']}")
        print(f"❌ Documentos com problema: {resumo['documentos_com_problema']}")
        print(f"📄 Total de chunks: {resumo['total_chunks_gerados']}")
        print(f"📈 Percentual de sucesso: {resumo['percentual_sucesso']}%")
        
        # 2. Identificar documentos problemáticos
        print("\n2️⃣ DOCUMENTOS PROBLEMÁTICOS")
        print("-" * 35)
        
        docs_problematicos = []
        docs_texto_pequeno = []
        
        for doc in diagnostico['documentos_detalhes']:
            if doc['chunks_count'] == 0:
                docs_problematicos.append(doc)
                
                # Verificar se é texto muito pequeno
                if doc['tamanho_arquivo'] < 5000:  # Menos de 5KB
                    docs_texto_pequeno.append(doc)
                    print(f"⚠️ {doc['titulo']} - Arquivo muito pequeno ({doc['tamanho_arquivo']} bytes)")
                else:
                    print(f"❌ {doc['titulo']} - Erro de processamento ({doc['tamanho_arquivo']} bytes)")
        
        if not docs_problematicos:
            print("✅ Nenhum documento problemático encontrado!")
            return
        
        # 3. Corrigir documentos com texto muito pequeno
        if docs_texto_pequeno:
            print(f"\n3️⃣ CORREÇÃO DE DOCUMENTOS COM TEXTO PEQUENO")
            print("-" * 45)
            
            resposta = input(f"🔧 Encontrados {len(docs_texto_pequeno)} documentos com texto muito pequeno.\n"
                           f"   Deseja marcá-los como processados para evitar reprocessamento? [s/N]: ").strip().lower()
            
            if resposta in ['s', 'sim', 'y', 'yes']:
                print("🔧 Corrigindo documentos com texto pequeno...")
                
                with db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        for doc in docs_texto_pequeno:
                            # Marcar como processado sem chunks
                            cursor.execute("""
                                UPDATE documentos_licitacao 
                                SET status_processamento = 'processado_sem_chunks',
                                    updated_at = NOW()
                                WHERE id = %s
                            """, (doc['id'],))
                            
                            print(f"   ✅ {doc['titulo']} - Marcado como processado")
                        
                        conn.commit()
                
                print(f"✅ {len(docs_texto_pequeno)} documentos corrigidos!")
        
        # 4. Forçar reprocessamento dos documentos restantes
        docs_para_reprocessar = [doc for doc in docs_problematicos if doc not in docs_texto_pequeno]
        
        if docs_para_reprocessar:
            print(f"\n4️⃣ REPROCESSAMENTO DE DOCUMENTOS GRANDES")
            print("-" * 40)
            
            resposta = input(f"🔄 Encontrados {len(docs_para_reprocessar)} documentos grandes com problema.\n"
                           f"   Deseja forçar o reprocessamento? [s/N]: ").strip().lower()
            
            if resposta in ['s', 'sim', 'y', 'yes']:
                print("🔄 Forçando reprocessamento...")
                
                documento_ids = [doc['id'] for doc in docs_para_reprocessar]
                resultado = rag_service.force_reprocess_documents(licitacao_id, documento_ids)
                
                if resultado['success']:
                    print(f"✅ Reprocessamento concluído!")
                    print(f"📄 Documentos processados: {resultado.get('documentos_processados', 0)}")
                    print(f"📊 Total de chunks: {resultado.get('total_chunks', 0)}")
                else:
                    print(f"❌ Erro no reprocessamento: {resultado['error']}")
        
        # 5. Diagnóstico final
        print(f"\n5️⃣ DIAGNÓSTICO FINAL")
        print("-" * 25)
        
        diagnostico_final = rag_service.diagnose_licitacao_documents(licitacao_id)
        
        if diagnostico_final['success']:
            resumo_final = diagnostico_final['resumo']
            print(f"📊 Total de documentos: {resumo_final['total_documentos']}")
            print(f"✅ Documentos vetorizados: {resumo_final['documentos_vetorizados']}")
            print(f"❌ Documentos com problema: {resumo_final['documentos_com_problema']}")
            print(f"📄 Total de chunks: {resumo_final['total_chunks_gerados']}")
            print(f"📈 Percentual de sucesso: {resumo_final['percentual_sucesso']}%")
            
            if resumo_final['documentos_com_problema'] == 0:
                print("\n🎉 TODOS OS PROBLEMAS FORAM CORRIGIDOS!")
            else:
                print(f"\n⚠️ Ainda há {resumo_final['documentos_com_problema']} documento(s) com problema.")
        
        print("\n✅ Correção concluída!")
        
    except Exception as e:
        logger.error(f"❌ Erro na correção: {e}")
        print(f"❌ Erro na correção: {e}")

if __name__ == "__main__":
    main() 