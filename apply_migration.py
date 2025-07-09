#!/usr/bin/env python3
"""
Script para aplicar migração do sistema de persistência escalável
"""
import sys
import os

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        print("🔄 Aplicando migração para sistema escalável...")
        
        # Importar após configurar path
        from config.database import get_db_manager
        
        # Conectar ao banco
        db_manager = get_db_manager()
        print("✅ Conectado ao banco de dados")
        
        # Ler arquivo de migração
        migration_file = 'migrations/20250102_01_update_licitacoes_for_scalable_persistence.sql'
        
        if not os.path.exists(migration_file):
            print(f"❌ Arquivo de migração não encontrado: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        print(f"📄 Lendo migração: {migration_file}")
        
        # Verificar se já foi aplicada
        try:
            result = db_manager.execute_query(
                "SELECT 1 FROM migration_log WHERE migration_name = %s",
                ['20250102_01_update_licitacoes_for_scalable_persistence']
            )
            
            if result:
                print("⚠️ Migração já foi aplicada anteriormente")
                return True
                
        except Exception:
            # Tabela migration_log não existe, criar
            print("📦 Criando tabela migration_log...")
            create_log_table = """
            CREATE TABLE IF NOT EXISTS migration_log (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                description TEXT
            );
            """
            db_manager.execute_query(create_log_table)
            print("✅ Tabela migration_log criada")
        
        # Aplicar migração
        print("🚀 Executando migração...")
        db_manager.execute_query(migration_sql)
        
        print("✅ Migração aplicada com sucesso!")
        
        # Verificar campos criados
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'licitacoes' 
        AND column_name IN ('provider_name', 'external_id', 'contact_info', 'documents')
        ORDER BY column_name;
        """
        
        columns = db_manager.execute_query(check_query)
        if isinstance(columns, list) and columns:
            print(f"🔍 Campos verificados: {[col['column_name'] for col in columns]}")
        else:
            print(f"🔍 Resultado da verificação: {columns}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 