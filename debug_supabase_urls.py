#!/usr/bin/env python3
"""
Script de Debug - URLs do Supabase Storage

Diagnostica problemas com URLs de documentos no Supabase Storage
"""

import os
import sys
import requests
import logging
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from config.database import DatabaseManager
from core.unified_document_processor import UnifiedDocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_supabase_urls():
    """Debug das URLs do Supabase"""
    try:
        print("🔍 DEBUGGING SUPABASE STORAGE URLs")
        print("="*60)
        
        # 1. Inicializar processador
        print("1️⃣ Inicializando processador...")
        db_manager = DatabaseManager()
        processor = UnifiedDocumentProcessor(db_manager)
        
        # 2. Testar licitação específica
        licitacao_id = "d0fdad57-83ed-417e-a552-f70e6eedb70d"
        print(f"2️⃣ Obtendo documentos da licitação: {licitacao_id}")
        
        documentos = processor.obter_documentos_licitacao(licitacao_id)
        print(f"📄 Encontrados {len(documentos)} documentos")
        
        # 3. Analisar cada documento
        for i, doc in enumerate(documentos, 1):
            print(f"\n📄 DOCUMENTO {i}/{len(documentos)}")
            print(f"   ID: {doc['id']}")
            print(f"   Título: {doc['titulo']}")
            print(f"   Tipo: {doc['tipo_arquivo']}")
            print(f"   Tamanho: {doc['tamanho_arquivo']} bytes")
            
            # URL atual
            url_atual = doc['arquivo_nuvem_url']
            print(f"   URL: {url_atual}")
            
            # Testar URL
            print("   🧪 Testando URL...")
            try:
                response = requests.head(url_atual, timeout=10)
                if response.status_code == 200:
                    print("   ✅ URL funcionando")
                else:
                    print(f"   ❌ URL com erro: {response.status_code}")
                    
                    # Tentar alternativas
                    print("   🔧 Tentando URLs alternativas...")
                    
                    # Extrair path do metadata
                    metadata = doc.get('metadata_arquivo', {})
                    cloud_path = metadata.get('cloud_path')
                    
                    if cloud_path:
                        # URL sem query params
                        url_clean = processor.supabase.storage.from_(processor.bucket_name).get_public_url(cloud_path)
                        print(f"   🔄 URL limpa: {url_clean}")
                        
                        response_clean = requests.head(url_clean, timeout=10)
                        print(f"   🧪 Status URL limpa: {response_clean.status_code}")
                        
                        if response_clean.status_code == 200:
                            print("   ✅ URL limpa funciona! Atualizando...")
                            # Atualizar URL no banco
                            _atualizar_url_documento(db_manager, doc['id'], url_clean)
                    else:
                        print("   ❌ Não há cloud_path no metadata")
                        
            except Exception as e:
                print(f"   ❌ Erro ao testar URL: {e}")
        
        # 4. Listar arquivos no bucket diretamente
        print(f"\n4️⃣ Listando arquivos no bucket para licitação...")
        try:
            files = processor.supabase.storage.from_(processor.bucket_name).list(f"licitacoes/{licitacao_id}")
            print(f"📁 Encontrados {len(files)} arquivos no storage:")
            
            for file in files:
                file_name = file.get('name', 'N/A')
                file_size = file.get('metadata', {}).get('size', 'N/A')
                file_updated = file.get('updated_at', 'N/A')
                
                print(f"   📄 {file_name} ({file_size} bytes) - {file_updated}")
                
                # Gerar URL correta
                full_path = f"licitacoes/{licitacao_id}/{file_name}"
                correct_url = processor.supabase.storage.from_(processor.bucket_name).get_public_url(full_path)
                print(f"      URL: {correct_url}")
                
                # Testar URL
                try:
                    test_response = requests.head(correct_url, timeout=5)
                    status_icon = "✅" if test_response.status_code == 200 else "❌"
                    print(f"      {status_icon} Status: {test_response.status_code}")
                except Exception as e:
                    print(f"      ❌ Erro: {e}")
        
        except Exception as e:
            print(f"❌ Erro ao listar arquivos: {e}")
        
        print("\n🎯 DEBUGGING CONCLUÍDO")
        
    except Exception as e:
        print(f"❌ Erro no debugging: {e}")
        import traceback
        traceback.print_exc()

def _atualizar_url_documento(db_manager, documento_id: str, nova_url: str):
    """Atualiza URL de um documento no banco"""
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE documentos_licitacao 
                    SET arquivo_nuvem_url = %s, updated_at = NOW()
                    WHERE id = %s
                """, (nova_url, documento_id))
                conn.commit()
                print(f"   ✅ URL atualizada no banco para documento {documento_id}")
    except Exception as e:
        print(f"   ❌ Erro ao atualizar URL: {e}")

if __name__ == "__main__":
    debug_supabase_urls() 