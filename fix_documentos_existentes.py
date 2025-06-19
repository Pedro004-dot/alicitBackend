#!/usr/bin/env python3
"""
Script para Corrigir Documentos Existentes

Corrige URLs problemáticas e sincroniza storage com banco
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from config.database import DatabaseManager
from core.unified_document_processor import UnifiedDocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def corrigir_documentos():
    """Corrige todos os problemas de documentos"""
    try:
        print("🔧 CORREÇÃO DE DOCUMENTOS EXISTENTES")
        print("="*60)
        
        # 1. Inicializar processador
        print("1️⃣ Inicializando processador...")
        db_manager = DatabaseManager()
        processor = UnifiedDocumentProcessor(db_manager)
        
        # 2. Licitação específica para teste
        licitacao_id = "d0fdad57-83ed-417e-a552-f70e6eedb70d"
        
        print(f"2️⃣ Corrigindo URLs problemáticas para licitação: {licitacao_id}")
        resultado_urls = processor.corrigir_urls_documentos(licitacao_id)
        
        if resultado_urls['success']:
            print(f"✅ URLs corrigidas: {resultado_urls['documentos_corrigidos']}")
        else:
            print(f"❌ Erro ao corrigir URLs: {resultado_urls['error']}")
        
        print(f"3️⃣ Sincronizando documentos storage ↔ banco...")
        resultado_sync = processor.sincronizar_documentos_storage(licitacao_id)
        
        if resultado_sync['success']:
            print(f"✅ Sincronização OK")
            print(f"   📁 Arquivos no storage: {resultado_sync.get('arquivos_storage', 'N/A')}")
            print(f"   💾 Documentos no banco (antes): {resultado_sync.get('documentos_banco_antes', 'N/A')}")
            print(f"   ➕ Arquivos adicionados: {resultado_sync.get('arquivos_adicionados', 'N/A')}")
        else:
            print(f"❌ Erro na sincronização: {resultado_sync['error']}")
        
        print(f"4️⃣ Verificando resultado final...")
        documentos_finais = processor.obter_documentos_licitacao(licitacao_id)
        print(f"📄 Total de documentos no banco: {len(documentos_finais)}")
        
        for i, doc in enumerate(documentos_finais, 1):
            url = doc['arquivo_nuvem_url']
            status_url = "✅" if not url.endswith('?') else "❌"
            print(f"   {i}. {doc['titulo']} {status_url}")
            print(f"      URL: {url}")
        
        print("\n🎯 CORREÇÃO CONCLUÍDA!")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na correção: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    corrigir_documentos() 