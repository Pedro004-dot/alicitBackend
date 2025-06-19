"""
Script para consultar schema completo do Supabase
"""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuração da conexão (usando as credenciais do config.env)
DATABASE_URL = "postgresql://postgres.hdlowzlkwrboqfzjewom:ej@NP[iXPQkZhWZ@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

def get_all_tables():
    """Obter todas as tabelas do banco"""
    query = """
    SELECT 
        schemaname,
        tablename,
        tableowner
    FROM pg_tables 
    WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
    ORDER BY schemaname, tablename;
    """
    return query

def get_table_columns(schema, table):
    """Obter colunas de uma tabela específica"""
    query = f"""
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length,
        numeric_precision,
        numeric_scale
    FROM information_schema.columns 
    WHERE table_schema = '{schema}' AND table_name = '{table}'
    ORDER BY ordinal_position;
    """
    return query

def get_extensions():
    """Obter extensões instaladas"""
    query = """
    SELECT 
        extname as extension_name,
        extversion as version,
        nspname as schema
    FROM pg_extension 
    JOIN pg_namespace ON pg_extension.extnamespace = pg_namespace.oid
    ORDER BY extname;
    """
    return query

def get_storage_buckets():
    """Obter buckets de storage"""
    query = """
    SELECT 
        id,
        name,
        owner,
        created_at,
        updated_at,
        public
    FROM storage.buckets
    ORDER BY name;
    """
    return query

def main():
    try:
        print("🔍 Conectando ao Supabase PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n" + "="*60)
        print("📋 LISTANDO TODAS AS TABELAS")
        print("="*60)
        
        # Obter todas as tabelas
        cursor.execute(get_all_tables())
        tables = cursor.fetchall()
        
        all_tables_info = {}
        
        for table in tables:
            schema = table['schemaname']
            table_name = table['tablename']
            
            print(f"\n🔹 SCHEMA: {schema} | TABELA: {table_name}")
            
            if schema not in all_tables_info:
                all_tables_info[schema] = {}
                
            # Obter colunas da tabela
            cursor.execute(get_table_columns(schema, table_name))
            columns = cursor.fetchall()
            
            all_tables_info[schema][table_name] = {
                'owner': table['tableowner'],
                'columns': columns
            }
            
            print(f"   Colunas ({len(columns)}):")
            for col in columns:
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"     - {col['column_name']}: {col['data_type']} {nullable}{default}")
        
        print("\n" + "="*60)
        print("🔧 EXTENSÕES INSTALADAS")
        print("="*60)
        
        cursor.execute(get_extensions())
        extensions = cursor.fetchall()
        
        for ext in extensions:
            print(f"✅ {ext['extension_name']} v{ext['version']} (schema: {ext['schema']})")
        
        # Verificar se tem extensões vetoriais
        vector_extensions = ['vector', 'pg_vector', 'pgvector']
        has_vector = any(ext['extension_name'] in vector_extensions for ext in extensions)
        
        if has_vector:
            print("\n🎯 EXTENSÕES VETORIAIS DETECTADAS!")
            vector_exts = [ext for ext in extensions if ext['extension_name'] in vector_extensions]
            for ext in vector_exts:
                print(f"   🔸 {ext['extension_name']} v{ext['version']}")
        
        print("\n" + "="*60)
        print("🗂️ STORAGE BUCKETS")
        print("="*60)
        
        try:
            cursor.execute(get_storage_buckets())
            buckets = cursor.fetchall()
            
            if buckets:
                for bucket in buckets:
                    visibility = "PÚBLICO" if bucket['public'] else "PRIVADO"
                    print(f"📁 {bucket['name']} (ID: {bucket['id']}) - {visibility}")
                    print(f"   Owner: {bucket['owner']}")
                    print(f"   Criado: {bucket['created_at']}")
            else:
                print("❌ Nenhum bucket de storage encontrado")
        except Exception as e:
            print(f"⚠️ Erro ao consultar storage: {e}")
        
        print("\n" + "="*60)
        print("📊 RESUMO FINAL")
        print("="*60)
        
        total_tables = sum(len(tables) for tables in all_tables_info.values())
        print(f"📋 Total de schemas: {len(all_tables_info)}")
        print(f"📋 Total de tabelas: {total_tables}")
        print(f"🔧 Total de extensões: {len(extensions)}")
        print(f"🎯 Suporte vetorial: {'✅ SIM' if has_vector else '❌ NÃO'}")
        
        # Salvar em arquivo JSON para consulta
        with open('supabase_schema.json', 'w', encoding='utf-8') as f:
            json.dump({
                'tables': all_tables_info,
                'extensions': extensions,
                'buckets': buckets if 'buckets' in locals() else [],
                'summary': {
                    'total_schemas': len(all_tables_info),
                    'total_tables': total_tables,
                    'total_extensions': len(extensions),
                    'has_vector_support': has_vector
                }
            }, f, indent=2, default=str)
        
        print(f"\n💾 Schema completo salvo em: supabase_schema.json")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main() 