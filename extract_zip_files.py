#!/usr/bin/env python3
"""
Script para extrair arquivos ZIP que foram salvos como .bin
e salvar os documentos corretamente no banco
"""

import os
import psycopg2
from psycopg2.extras import DictCursor
import zipfile
from pathlib import Path
import shutil
import uuid
import hashlib
import json
from datetime import datetime

def get_db_connection():
    """Conecta ao banco Supabase usando config.env"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Carregar do config.env se não estiver nas env vars
        try:
            with open('config.env', 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        database_url = line.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            raise ValueError("Arquivo config.env não encontrado")
    
    if not database_url:
        raise ValueError("DATABASE_URL não encontrada")
    
    return psycopg2.connect(database_url)

def extract_zip_files():
    """Extrai arquivos ZIP disfarçados de .bin"""
    conn = get_db_connection()
    storage_path = Path('./storage/documents')
    
    try:
        with conn.cursor(cursor_factory=DictCursor) as cursor:
            # Buscar editais com status pendente e arquivos .bin
            cursor.execute("""
                SELECT id, licitacao_id, titulo, arquivo_local, status_processamento
                FROM editais 
                WHERE status_processamento = 'pendente' 
                AND arquivo_local LIKE '%.bin'
            """)
            
            editais_bin = cursor.fetchall()
            
            print(f"Encontrados {len(editais_bin)} editais .bin pendentes")
            
            for edital in editais_bin:
                arquivo_bin = edital['arquivo_local']
                licitacao_id = edital['licitacao_id']
                print(f"\nProcessando ZIP: {arquivo_bin}")
                
                if not os.path.exists(arquivo_bin):
                    print(f"Arquivo não encontrado: {arquivo_bin}")
                    continue
                
                try:
                    # Verificar se é um ZIP
                    with open(arquivo_bin, 'rb') as f:
                        header = f.read(4)
                        
                    if header[:2] != b'PK':
                        print(f"Arquivo não é ZIP: {arquivo_bin}")
                        continue
                    
                    # Renomear para .zip temporariamente
                    arquivo_zip = arquivo_bin.replace('.bin', '.zip')
                    shutil.copy2(arquivo_bin, arquivo_zip)
                    
                    # Extrair conteúdo do ZIP
                    extract_dir = storage_path / f"extracted_{edital['id']}"
                    extract_dir.mkdir(exist_ok=True)
                    
                    documentos_extraidos = []
                    
                    with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        print(f"Arquivos no ZIP: {len(file_list)}")
                        
                        for file_name in file_list:
                            if file_name.endswith('/'):
                                continue  # Skip directories
                                
                            print(f"  Extraindo: {file_name}")
                            
                            # Extrair arquivo
                            extracted_path = extract_dir / file_name.replace('/', '_')
                            
                            with zip_ref.open(file_name) as source:
                                with open(extracted_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)
                            
                            # Calcular hash
                            with open(extracted_path, 'rb') as f:
                                file_content = f.read()
                                file_hash = hashlib.sha256(file_content).hexdigest()
                            
                            # Determinar tipo de documento
                            tipo_documento = 'edital_principal' if any(term in file_name.lower() for term in 
                                                                     ['edital', 'aviso', 'pregao', 'licitacao', 'chamada']) else 'anexo'
                            
                            documento = {
                                'id': str(uuid.uuid4()),
                                'licitacao_id': licitacao_id,
                                'titulo': file_name,
                                'arquivo_local': str(extracted_path),
                                'tipo_documento': tipo_documento,
                                'tamanho_arquivo': len(file_content),
                                'hash_arquivo': file_hash,
                                'status_processamento': 'processado',
                                'metadata_extracao': {
                                    'fonte': 'ZIP_PNCP',
                                    'zip_original': arquivo_bin,
                                    'extraido_de': file_name,
                                    'data_extracao': datetime.now().isoformat()
                                }
                            }
                            
                            documentos_extraidos.append(documento)
                    
                    # Deletar o edital .bin original e salvar os documentos extraídos
                    cursor.execute("DELETE FROM editais WHERE id = %s", (edital['id'],))
                    
                    # Salvar documentos extraídos
                    for doc in documentos_extraidos:
                        cursor.execute("""
                            INSERT INTO editais (
                                id, licitacao_id, titulo, arquivo_local, tipo_documento,
                                tamanho_arquivo, hash_arquivo, status_processamento, 
                                metadata_extracao, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            doc['id'], doc['licitacao_id'], doc['titulo'], doc['arquivo_local'],
                            doc['tipo_documento'], doc['tamanho_arquivo'], doc['hash_arquivo'],
                            doc['status_processamento'], json.dumps(doc['metadata_extracao']), 
                            datetime.now()
                        ))
                    
                    print(f"✅ Extraídos {len(documentos_extraidos)} documentos!")
                    
                    # Limpar arquivos temporários
                    os.remove(arquivo_zip)
                    os.remove(arquivo_bin)
                    
                except Exception as e:
                    print(f"❌ Erro ao processar {arquivo_bin}: {e}")
                    conn.rollback()
                    # Continue para o próximo arquivo em caso de erro
                    continue
            
            conn.commit()
            print(f"\n🎉 Processamento concluído!")
            
    except Exception as e:
        print(f"Erro geral: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    # Configurar variáveis de ambiente
    os.environ.setdefault('DATABASE_URL', 'postgresql://postgres.hdlowzlkwrboqfzjewom:WOxaFvYM6EzCGJmC@aws-0-sa-east-1.pooler.supabase.com:6543/postgres')
    
    extract_zip_files() 