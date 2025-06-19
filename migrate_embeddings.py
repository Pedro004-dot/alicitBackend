#!/usr/bin/env python3
"""
Script de migração para ajustar dimensões do cache de embeddings
De 384 para 768 dimensões (NeralMind BERT)
"""

import sys
import os

# Adicionar src ao path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def migrate_embedding_dimensions():
    print("🔄 MIGRAÇÃO: Ajustando cache para 768 dimensões")
    print("=" * 60)
    
    # Carregar variáveis de ambiente
    from dotenv import load_dotenv
    load_dotenv('config.env')
    
    try:
        from src.config.database import db_manager
        
        print("🔧 Conectando ao banco...")
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verificar tabela atual
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'embedding_cache' 
                    AND column_name = 'embedding'
                """)
                
                result = cursor.fetchone()
                if result:
                    print(f"📊 Tabela existente encontrada: {result}")
                    
                    # Remover tabela antiga
                    print("🗑️ Removendo tabela antiga...")
                    cursor.execute('DROP TABLE IF EXISTS embedding_cache CASCADE;')
                    print("✅ Tabela antiga removida")
                else:
                    print("💡 Tabela não existe, criando nova...")
                
                # Criar tabela com 768 dimensões
                print("🆕 Criando tabela com 768 dimensões...")
                cursor.execute("""
                    CREATE TABLE embedding_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        text_hash VARCHAR(64) UNIQUE NOT NULL,
                        text_preview TEXT,
                        embedding VECTOR(768),
                        model_name VARCHAR(100),
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        accessed_at TIMESTAMPTZ DEFAULT NOW(),
                        access_count INTEGER DEFAULT 1
                    );
                """)
                
                # Criar índices
                print("🔗 Criando índices...")
                cursor.execute('CREATE INDEX idx_embedding_cache_hash ON embedding_cache (text_hash);')
                cursor.execute('CREATE INDEX idx_embedding_cache_model ON embedding_cache (model_name);')
                
                # Criar tabela de processamento se não existir
                print("🔄 Verificando tabela de processamento...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processamento_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        resource_type VARCHAR(50) NOT NULL,
                        resource_id VARCHAR(255) NOT NULL,
                        process_hash VARCHAR(64) NOT NULL,
                        status VARCHAR(20) DEFAULT 'completed',
                        metadata JSONB,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        
                        UNIQUE(resource_type, resource_id, process_hash)
                    );
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_processamento_cache_resource 
                    ON processamento_cache (resource_type, resource_id);
                """)
                
                conn.commit()
                print("✅ Migração concluída com sucesso!")
                
                # Verificar resultado
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_name = 'embedding_cache'
                    ORDER BY ordinal_position
                """)
                
                columns = cursor.fetchall()
                print("\n📋 Estrutura da tabela atualizada:")
                for col in columns:
                    print(f"   {col[0]}: {col[1]}")
                
                return True
                
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False

if __name__ == "__main__":
    success = migrate_embedding_dimensions()
    
    if success:
        print("\n🎉 MIGRAÇÃO COMPLETA!")
        print("✅ Cache configurado para 768 dimensões")
        print("✅ Compatível com NeralMind BERT")
        print("\n🚀 Sistema pronto para usar SentenceTransformers!")
        sys.exit(0)
    else:
        print("\n❌ MIGRAÇÃO FALHOU")
        sys.exit(1) 