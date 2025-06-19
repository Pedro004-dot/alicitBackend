#!/usr/bin/env python3
"""
Script para Corrigir URLs Manualmente

Correção simples e direta das URLs com problema
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar src ao path
sys.path.append(str(Path(__file__).parent / "src"))

from config.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def corrigir_urls_manual():
    """Corrige URLs problemáticas manualmente"""
    try:
        print("🔧 CORREÇÃO MANUAL DE URLs")
        print("="*50)
        
        db_manager = DatabaseManager()
        licitacao_id = "d0fdad57-83ed-417e-a552-f70e6eedb70d"
        
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # 1. Buscar TODOS os documentos primeiro
                cursor.execute("""
                    SELECT id, titulo, arquivo_nuvem_url 
                    FROM documentos_licitacao 
                    WHERE licitacao_id = %s
                """, (licitacao_id,))
                
                todos_docs = cursor.fetchall()
                print(f"🔍 Encontrados {len(todos_docs)} documentos total")
                
                # 2. Filtrar e corrigir URLs problemáticas
                docs_corrigidos = 0
                
                for doc_id, titulo, url_atual in todos_docs:
                    print(f"\n📄 Verificando: {titulo}")
                    print(f"   URL atual: {url_atual}")
                    
                    if url_atual and url_atual.endswith('?'):
                        url_nova = url_atual[:-1]  # Remove o ? do final
                        
                        cursor.execute("""
                            UPDATE documentos_licitacao 
                            SET arquivo_nuvem_url = %s, updated_at = NOW()
                            WHERE id = %s
                        """, (url_nova, doc_id))
                        
                        print(f"   ✅ CORRIGIDO!")
                        print(f"   URL nova: {url_nova}")
                        docs_corrigidos += 1
                    else:
                        print(f"   ✅ URL já está OK")
                
                conn.commit()
                print(f"\n🎉 {docs_corrigidos} URLs corrigidas!")
                
                # 3. Verificar resultado final
                cursor.execute("""
                    SELECT titulo, arquivo_nuvem_url 
                    FROM documentos_licitacao 
                    WHERE licitacao_id = %s
                    ORDER BY titulo
                """, (licitacao_id,))
                
                docs_finais = cursor.fetchall()
                print(f"\n📄 RESULTADO FINAL - {len(docs_finais)} documentos:")
                
                for titulo, url in docs_finais:
                    status = "✅" if not (url and url.endswith('?')) else "❌"
                    print(f"   {status} {titulo}")
                    if len(url) > 100:
                        print(f"      {url[:100]}...")
                    else:
                        print(f"      {url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    corrigir_urls_manual() 