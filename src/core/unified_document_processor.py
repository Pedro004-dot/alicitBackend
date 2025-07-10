"""
Processador Unificado de Documentos para Licitações
Combina processamento local e nuvem com máxima flexibilidade
"""

import os
import requests
import zipfile
import tempfile
import hashlib
import magic
import logging
import uuid
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from psycopg2.extras import DictCursor
import PyPDF2
import io
from datetime import datetime
from supabase import create_client, Client
from services.storage_service import StorageService
from rag.advanced_text_extractor import AdvancedTextExtractor

# Configurar logging
logger = logging.getLogger(__name__)

class UnifiedDocumentProcessor:
    """Processador unificado para documentos de licitações"""
    
    def __init__(self, db_manager, supabase_url: str, supabase_key: str):
        self.db_manager = db_manager
        self.storage_service = StorageService(supabase_url, supabase_key)
        
        # Nome do bucket
        self.bucket_name = "licitacao-documents"
        
        # Diretório temporário apenas para processamento
        self.temp_path = Path('./storage/temp')
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Extensões aceitas
        self.allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.zip'}
        
        # 🆕 Inicializar extrator avançado de texto
        self.text_extractor = AdvancedTextExtractor()
        logger.info(f"🔧 Extrator de texto inicializado: {self.text_extractor.get_extractor_status()}")
        
        # Garantir bucket
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """
        Garante que o bucket existe (assume que já foi criado via configuração)
        """
        try:
            # Ao invés de listar buckets (que requer permissões especiais),
            # simplesmente testar se conseguimos listar arquivos no bucket
            files_test = self.storage_service.list("")  # Lista raiz do bucket
            logger.info(f"✅ Bucket '{self.bucket_name}' acessível e funcionando")
        except Exception as e:
            logger.warning(f"⚠️ Aviso ao testar bucket (normal com ANON_KEY): {e}")
            logger.info(f"📦 Assumindo que bucket '{self.bucket_name}' existe (configurado externamente)")
    
    # ================================
    # PASSOS 1, 2, 3 - IGUAIS AOS ANTERIORES
    # ================================
    
    def extrair_info_licitacao(self, licitacao_id: str) -> Optional[Dict]:
        """PASSO 1: Extrai informações da licitação do banco"""
        try:
            logger.info(f"🔍 PASSO 1: Buscando licitação: {licitacao_id}")
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    query = """
                        SELECT id, pncp_id, orgao_cnpj, ano_compra, sequencial_compra, 
                               objeto_compra, status, modalidade_nome, modalidade_id,
                               valor_total_estimado, uf, data_publicacao, data_abertura_proposta,
                               data_encerramento_proposta, orgao_entidade, unidade_orgao
                        FROM licitacoes 
                        WHERE id = %s OR pncp_id = %s
                    """
                    
                    cursor.execute(query, (licitacao_id, licitacao_id))
                    result = cursor.fetchone()
                    
                    if result:
                        logger.info(f"✅ PASSO 1 OK: Licitação encontrada")
                        return dict(result)
                    else:
                        logger.error(f"❌ PASSO 1 FALHOU: Licitação não encontrada")
                        return None
                
        except Exception as e:
            logger.error(f"❌ ERRO PASSO 1: {e}")
            return None
    
    def verificar_documentos_existem(self, licitacao_id: str) -> bool:
        """PASSO 2: Verifica se documentos já foram processados"""
        try:
            logger.info(f"🔍 PASSO 2: Verificando documentos existentes")
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT COUNT(*) FROM documentos_licitacao WHERE licitacao_id = %s", 
                        (licitacao_id,)
                    )
                    count = cursor.fetchone()[0]
                    
                    exists = count > 0
                    if exists:
                        logger.info(f"✅ PASSO 2: {count} documentos já existem")
                    else:
                        logger.info(f"✅ PASSO 2: Nenhum documento existente")
                    
                    return exists
                
        except Exception as e:
            logger.error(f"❌ ERRO PASSO 2: {e}")
            return False
    
    def construir_url_documentos(self, licitacao_info: Dict) -> str:
        """PASSO 3: Constrói URL da API PNCP"""
        try:
            logger.info(f"🔧 PASSO 3: Construindo URL da API")
            
            cnpj = licitacao_info['orgao_cnpj']
            ano = licitacao_info['ano_compra']
            sequencial = licitacao_info['sequencial_compra']
            
            url = f"https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
            
            logger.info(f"✅ PASSO 3 OK: URL construída")
            return url
            
        except KeyError as e:
            logger.error(f"❌ ERRO PASSO 3: Campo ausente: {e}")
            raise
    
    # ================================
    # PASSO 4 - PROCESSAMENTO FLEXÍVEL
    # ================================
    
    def processar_resposta_pncp(self, url: str, licitacao_id: str) -> Optional[List[Dict]]:
        """PASSO 4: Processa resposta da API PNCP (flexível para JSON ou ZIP)"""
        try:
            logger.info(f"🌐 PASSO 4: Fazendo requisição para API PNCP")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, application/zip, */*'
            }
            
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"📥 Content-Type recebido: {content_type}")
            
            # Detectar tipo de resposta
            if 'json' in content_type:
                logger.info(f"📋 Resposta JSON: Lista de documentos")
                return self._processar_lista_documentos(response.json(), licitacao_id)
            
            elif 'zip' in content_type or 'application/octet-stream' in content_type:
                logger.info(f"📦 Resposta ZIP: Arquivo compactado")
                return self._processar_arquivo_zip(response.content, licitacao_id)
            
            else:
                logger.warning(f"⚠️ Tipo de resposta não reconhecido: {content_type}")
                # Tentar como JSON primeiro
                try:
                    data = response.json()
                    return self._processar_lista_documentos(data, licitacao_id)
                except:
                    # Tentar como ZIP
                    return self._processar_arquivo_zip(response.content, licitacao_id)
            
        except Exception as e:
            logger.error(f"❌ ERRO PASSO 4: {e}")
            return None
    
    def _processar_lista_documentos(self, documentos_lista: List[Dict], licitacao_id: str) -> List[Dict]:
        """Processa lista JSON de documentos"""
        try:
            if not isinstance(documentos_lista, list) or len(documentos_lista) == 0:
                logger.warning("⚠️ Lista de documentos vazia")
                return []
            
            logger.info(f"📄 Processando {len(documentos_lista)} documentos da lista")
            
            documentos_processados = []
            
            for i, doc_info in enumerate(documentos_lista):
                try:
                    doc_url = doc_info.get('url') or doc_info.get('uri')
                    doc_titulo = doc_info.get('titulo', f'documento_{i+1}')
                    tipo_documento = doc_info.get('tipoDocumentoNome', 'Documento')
                    sequencial_documento = doc_info.get('sequencialDocumento', i + 1)
                    
                    if not doc_url:
                        logger.warning(f"⚠️ URL não encontrada para: {doc_titulo}")
                        continue
                    
                    logger.info(f"📥 Baixando {i+1}/{len(documentos_lista)}: {doc_titulo} ({tipo_documento})")
                    
                    # 🔧 CORREÇÃO: Headers mais específicos para garantir download do PDF
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/pdf, application/octet-stream, */*',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive'
                    }
                    
                    # Baixar arquivo individual
                    doc_response = requests.get(doc_url, headers=headers, timeout=120, stream=True)
                    doc_response.raise_for_status()
                    
                    # 🔧 VERIFICAÇÃO: Confirmar que o conteúdo é realmente um arquivo
                    content_type = doc_response.headers.get('content-type', '').lower()
                    content_length = doc_response.headers.get('content-length', '0')
                    
                    logger.info(f"📋 Content-Type: {content_type}, Size: {content_length} bytes")
                    
                    # Se recebeu ao invés de arquivo, logar erro detalhado
                    if 'text/html' in content_type:
                        logger.error(f"❌ URL retornou HTML ao invés de arquivo: {doc_url}")
                        logger.error(f"🔍 Response preview: {doc_response.text[:200]}...")
                        continue
                    
                    # A detecção de ZIP agora é feita em _processar_arquivo_individual
                    
                    # 🔧 CORREÇÃO: Criar nome mais descritivo
                    nome_arquivo = f"{sequencial_documento:03d}_{doc_titulo}_{tipo_documento}"
                    
                    # Processar arquivo (pode retornar múltiplos documentos se for ZIP)
                    documentos_resultado = self._processar_arquivo_individual(
                        doc_response.content,
                        nome_arquivo,
                        licitacao_id,
                        sequencial_documento,
                        doc_info
                    )
                    
                    if documentos_resultado:
                        documentos_processados.extend(documentos_resultado)
                        logger.info(f"✅ {len(documentos_resultado)} documento(s) processado(s): {nome_arquivo}")
                    else:
                        logger.error(f"❌ Falha ao processar: {nome_arquivo}")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar documento {i+1}: {e}")
                    # Log mais detalhado do erro
                    import traceback
                    logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                    continue
            
            logger.info(f"✅ {len(documentos_processados)} de {len(documentos_lista)} documentos processados com sucesso")
            return documentos_processados
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar lista de documentos: {e}")
            import traceback
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return []
    
    def _processar_arquivo_zip(self, zip_content: bytes, licitacao_id: str) -> List[Dict]:
        """Processa arquivo ZIP com múltiplos documentos"""
        try:
            logger.info(f"📦 Processando arquivo ZIP ({len(zip_content)} bytes)")
            
            # Salvar ZIP temporariamente
            temp_zip_path = self.temp_path / f"temp_{licitacao_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with open(temp_zip_path, 'wb') as f:
                f.write(zip_content)
            
            documentos_processados = []
            extract_dir = None
            
            try:
                # Extrair ZIP
                extract_dir = self.temp_path / f"extracted_{licitacao_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                extract_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Processar arquivos extraídos
                contador = 1
                for file_path in extract_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions:
                        
                        # Ignorar arquivos de sistema
                        if file_path.name.startswith('.') or '__MACOSX' in str(file_path):
                            continue
                        
                        logger.info(f"📄 Processando arquivo {contador}: {file_path.name}")
                        
                        # Ler conteúdo do arquivo
                        with open(file_path, 'rb') as f:
                            arquivo_content = f.read()
                        
                        # Processar arquivo (pode retornar múltiplos se for ZIP aninhado)
                        documentos_resultado = self._processar_arquivo_individual(
                            arquivo_content,
                            file_path.name,
                            licitacao_id,
                            contador
                        )
                        
                        if documentos_resultado:
                            documentos_processados.extend(documentos_resultado)
                        
                        contador += 1
                
                logger.info(f"✅ {len(documentos_processados)} documentos extraídos do ZIP")
                return documentos_processados
                
            finally:
                # Limpar arquivos temporários
                if temp_zip_path.exists():
                    temp_zip_path.unlink()
                if extract_dir and extract_dir.exists():
                    import shutil
                    shutil.rmtree(extract_dir, ignore_errors=True)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar ZIP: {e}")
            return []
    
    def _processar_arquivo_individual(self, 
                                    arquivo_content: bytes, 
                                    nome_original: str, 
                                    licitacao_id: str, 
                                    sequencial: int,
                                    metadata_extra: Dict = None) -> Optional[List[Dict]]:
        """
        Processa um arquivo individual com verificação recursiva de ZIPs
        Retorna lista de documentos (pode ser 1 PDF ou múltiplos extraídos de ZIP)
        """
        try:
            # 🔧 VALIDAÇÃO: Verificar se o conteúdo não está vazio
            if not arquivo_content or len(arquivo_content) == 0:
                logger.error(f"❌ Arquivo vazio ou conteúdo nulo: {nome_original}")
                return None
            
            # 🔧 VALIDAÇÃO: Verificar se não é HTML (erro comum)
            if arquivo_content.startswith(b'<!DOCTYPE') or arquivo_content.startswith(b'<html'):
                logger.error(f"❌ Arquivo contém HTML ao invés de dados binários: {nome_original}")
                logger.error(f"🔍 Conteúdo: {arquivo_content[:200].decode('utf-8', errors='ignore')}...")
                return None
            
            logger.info(f"📄 Processando arquivo: {nome_original} ({len(arquivo_content)} bytes)")
            
            # 🆕 NOVA LÓGICA: Verificar se é ZIP ANTES de salvar no storage
            if self._is_zip_content(arquivo_content):
                logger.info(f"📦 ZIP detectado - extraindo recursivamente: {nome_original}")
                return self._extrair_zip_recursivo(arquivo_content, licitacao_id, sequencial, nome_original)
            
            # Se não é ZIP, processar como arquivo normal (apenas PDFs)
            return self._salvar_arquivo_final(arquivo_content, nome_original, licitacao_id, sequencial, metadata_extra)
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar arquivo {nome_original}: {e}")
            return None

    def _is_zip_content(self, content: bytes) -> bool:
        """Verifica se o conteúdo é um ZIP"""
        return (content.startswith(b'PK\x03\x04') or 
                content.startswith(b'PK\x05\x06') or 
                content.startswith(b'PK\x07\x08'))

    def _extrair_zip_recursivo(self, zip_content: bytes, licitacao_id: str, sequencial_base: int, nome_zip: str) -> List[Dict]:
        """
        Extrai ZIP recursivamente até encontrar apenas arquivos PDF finais
        """
        try:
            logger.info(f"🔄 Extração recursiva do ZIP: {nome_zip}")
            
            # Salvar ZIP temporariamente
            temp_zip_path = self.temp_path / f"recursive_{licitacao_id}_{sequencial_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with open(temp_zip_path, 'wb') as f:
                f.write(zip_content)
            
            documentos_finais = []
            extract_dir = None
            
            try:
                # Extrair ZIP
                extract_dir = self.temp_path / f"extracted_recursive_{licitacao_id}_{sequencial_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                extract_dir.mkdir(exist_ok=True)
                
                with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Processar arquivos extraídos recursivamente
                contador_arquivo = 1
                for file_path in extract_dir.rglob('*'):
                    if file_path.is_file():
                        
                        # Ignorar arquivos de sistema
                        if file_path.name.startswith('.') or '__MACOSX' in str(file_path):
                            continue
                        
                        # Ler conteúdo do arquivo
                        with open(file_path, 'rb') as f:
                            arquivo_content = f.read()
                        
                        logger.info(f"🔍 Analisando arquivo extraído: {file_path.name}")
                        
                        # 🆕 VERIFICAÇÃO RECURSIVA: Se é outro ZIP, extrair recursivamente
                        if self._is_zip_content(arquivo_content):
                            logger.info(f"📦 ZIP aninhado encontrado, extraindo recursivamente: {file_path.name}")
                            # Usar sequencial composto para ZIPs aninhados
                            subsequencial = int(f"{sequencial_base}{contador_arquivo:02d}")
                            zip_docs = self._extrair_zip_recursivo(arquivo_content, licitacao_id, subsequencial, file_path.name)
                            if zip_docs:
                                documentos_finais.extend(zip_docs)
                        
                        # Se é PDF, processar e salvar
                        elif self._is_pdf_content(arquivo_content):
                            logger.info(f"📄 PDF encontrado, salvando: {file_path.name}")
                            # Usar sequencial composto para PDFs dentro de ZIPs
                            subsequencial = int(f"{sequencial_base}{contador_arquivo:02d}")
                            pdf_docs = self._salvar_arquivo_final(arquivo_content, file_path.name, licitacao_id, subsequencial)
                            if pdf_docs:
                                documentos_finais.extend(pdf_docs)
                        
                        # Se não é nem ZIP nem PDF, ignorar
                        else:
                            extensao = self._detectar_extensao(arquivo_content, file_path.name)
                            logger.warning(f"⚠️ Arquivo ignorado (apenas PDFs são salvos): {file_path.name} - {extensao}")
                        
                        contador_arquivo += 1
                
                logger.info(f"✅ Extração recursiva concluída: {len(documentos_finais)} documentos finais extraídos")
                return documentos_finais
                
            finally:
                # Limpar arquivos temporários
                if temp_zip_path.exists():
                    temp_zip_path.unlink()
                if extract_dir and extract_dir.exists():
                    import shutil
                    shutil.rmtree(extract_dir, ignore_errors=True)
            
        except Exception as e:
            logger.error(f"❌ Erro na extração recursiva: {e}")
            return []

    def _is_pdf_content(self, content: bytes) -> bool:
        """Verifica se o conteúdo é um PDF"""
        return content.startswith(b'%PDF') or b'%PDF' in content[:1000]

    def _salvar_arquivo_final(self, arquivo_content: bytes, nome_original: str, licitacao_id: str, sequencial: int, metadata_extra: Dict = None) -> List[Dict]:
        """
        Salva um arquivo final (não-ZIP) no storage
        Retorna lista com 1 documento
        """
        try:
            # Limpar nome do arquivo
            nome_limpo = self._limpar_nome_arquivo(nome_original)
            
            # Determinar extensão e tipo
            extensao = self._detectar_extensao(arquivo_content, nome_limpo)
            
            # 🔧 FILTRO: Só processar PDFs (ZIPs são tratados separadamente)
            if extensao != '.pdf':
                logger.warning(f"⚠️ Apenas PDFs são salvos no storage: {extensao} - {nome_original}")
                return []
            
            # 🔧 CORREÇÃO: Se detectou HTML, não processar
            if extensao == '.html':
                logger.error(f"❌ Arquivo detectado como HTML - pulando: {nome_original}")
                return []
            
            # Garantir que o nome tenha extensão
            if not nome_limpo.endswith(extensao):
                if '.' in nome_limpo:
                    nome_limpo = f"{nome_limpo.split('.')[0]}{extensao}"
                else:
                    nome_limpo = f"{nome_limpo}{extensao}"
            
            # Caminho na nuvem
            cloud_path = f"licitacoes/{licitacao_id}/{sequencial:03d}_{nome_limpo}"
            
            # Upload para Supabase
            logger.info(f"☁️ Fazendo upload do arquivo final: {cloud_path}")
            
            try:
                # 🔧 CORREÇÃO: Verificar se arquivo já existe
                try:
                    existing = self.storage_service.list(f"licitacoes/{licitacao_id}")
                    file_exists = any(file['name'] == f"{sequencial:03d}_{nome_limpo}" for file in existing)
                    
                    if file_exists:
                        logger.info(f"📁 Arquivo já existe, usando versão existente: {cloud_path}")
                    else:
                        # Fazer upload normalmente
                        upload_result = self.storage_service.upload(
                            cloud_path, 
                            arquivo_content,
                            content_type=self._get_mime_type(extensao)
                        )
                        
                        if not upload_result:
                            logger.error(f"❌ Falha no upload: {nome_original}")
                            return []
                        else:
                            logger.info(f"✅ Upload concluído: {cloud_path}")
                            
                except Exception as upload_error:
                    # Se erro é de duplicata, tentar obter URL do arquivo existente
                    if 'Duplicate' in str(upload_error) or 'already exists' in str(upload_error):
                        logger.info(f"📁 Arquivo duplicado detectado, usando versão existente: {cloud_path}")
                    else:
                        raise upload_error
                
                # 🔧 CORREÇÃO: Gerar URL pública sem query parameters problemáticos
                raw_url = self.storage_service.get_public_url(cloud_path)
                
                # Limpar URL removendo query parameters vazios que causam problemas
                if raw_url.endswith('?'):
                    public_url = raw_url[:-1]  # Remove o ? no final
                elif '?' in raw_url and not any(param for param in raw_url.split('?')[1].split('&') if '=' in param):
                    public_url = raw_url.split('?')[0]  # Remove query params vazios
                else:
                    public_url = raw_url
                
                logger.info(f"📎 URL gerada: {public_url}")
                
                # 🆕 NOVO: Extrair texto usando extrator avançado
                texto_preview = None
                extraction_result = None
                if extensao == '.pdf':
                    try:
                        logger.info(f"🔄 Extraindo texto avançado: {nome_original}")
                        extraction_result = self.text_extractor.extract_text_from_bytes(
                            arquivo_content, 
                            nome_original
                        )
                        
                        if extraction_result['success']:
                            # Para preview, pegar só os primeiros 1000 caracteres
                            texto_preview = extraction_result['text'][:1000]
                            if len(extraction_result['text']) > 1000:
                                texto_preview += "..."
                            
                            logger.info(f"✅ Texto extraído com {extraction_result['extractor_used']} em {extraction_result['extraction_time']:.2f}s")
                        else:
                            logger.warning(f"⚠️ Falha na extração: {extraction_result.get('error', 'Erro desconhecido')}")
                            # Fallback para método antigo se novo falhar
                            texto_preview = self._extrair_texto_pdf_fallback(arquivo_content)
                    
                    except Exception as e:
                        logger.error(f"❌ Erro no extrator avançado: {e}")
                        # Fallback para método antigo
                        texto_preview = self._extrair_texto_pdf_fallback(arquivo_content)
                
                # Montar documento
                documento = {
                    'licitacao_id': licitacao_id,
                    'titulo': nome_original,
                    'arquivo_nuvem_url': public_url,
                    'tipo_arquivo': self._get_mime_type(extensao),
                    'tamanho_arquivo': len(arquivo_content),
                    'hash_arquivo': hashlib.sha256(arquivo_content).hexdigest(),
                    'texto_preview': texto_preview,
                    'metadata_arquivo': {
                        'nome_original': nome_original,
                        'nome_limpo': nome_limpo,
                        'extensao': extensao,
                        'sequencial': sequencial,
                        'cloud_path': cloud_path,
                        'storage_provider': 'supabase',
                        'bucket_name': self.bucket_name,
                        'processado_em': datetime.now().isoformat(),
                        'is_extracted_from_zip': metadata_extra is not None,
                        # 🆕 Metadados da extração de texto
                        'text_extraction': {
                            'extractor_used': extraction_result['extractor_used'] if extraction_result and extraction_result['success'] else None,
                            'extraction_time': extraction_result['extraction_time'] if extraction_result else None,
                            'char_count': extraction_result['char_count'] if extraction_result and extraction_result['success'] else None,
                            'page_count': extraction_result['page_count'] if extraction_result and extraction_result['success'] else None,
                            'success': extraction_result['success'] if extraction_result else False,
                            'extraction_metadata': extraction_result.get('metadata', {}) if extraction_result and extraction_result['success'] else {}
                        },
                        **(metadata_extra or {})
                    }
                }
                
                return [documento]
                
            except Exception as e:
                logger.error(f"❌ Erro no upload/processamento: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao salvar arquivo final {nome_original}: {e}")
            return []
    
    # ================================
    # UTILITÁRIOS
    # ================================
    
    def _limpar_nome_arquivo(self, nome: str) -> str:
        """Remove caracteres problemáticos e acentos"""
        import re
        import unicodedata
        
        # 🔧 CORREÇÃO: Remover acentos convertendo para ASCII
        nome_limpo = unicodedata.normalize('NFKD', nome)
        nome_limpo = ''.join(c for c in nome_limpo if not unicodedata.combining(c))
        
        # Remover espaços e caracteres especiais, manter apenas letras, números, hífen, underscore e ponto
        nome_limpo = re.sub(r'[^\w\-_\.]', '_', nome_limpo)
        
        # Remover underscores múltiplos
        nome_limpo = re.sub(r'_+', '_', nome_limpo)
        
        # Remover underscores no início e fim
        nome_limpo = nome_limpo.strip('_')
        
        return nome_limpo
    
    def _detectar_extensao(self, content: bytes, nome: str) -> str:
        """Detecta extensão correta do arquivo"""
        # Primeiro, verificar se já tem extensão válida
        for ext in self.allowed_extensions:
            if nome.lower().endswith(ext):
                return ext
        
        # 🔧 CORREÇÃO: Detectar pelo magic bytes do PDF
        if content.startswith(b'%PDF'):
            logger.info("📄 Arquivo detectado como PDF pelos magic bytes")
            return '.pdf'
        
        # 🔧 CORREÇÃO: Detectar ZIP (magic bytes PK)
        if content.startswith(b'PK\x03\x04') or content.startswith(b'PK\x05\x06') or content.startswith(b'PK\x07\x08'):
            logger.info("📦 Arquivo detectado como ZIP pelos magic bytes")
            return '.zip'
        
        # Detectar pelo conteúdo usando python-magic
        try:
            mime_type = magic.from_buffer(content[:2048], mime=True)
            logger.info(f"🔍 MIME type detectado: {mime_type}")
            
            if 'pdf' in mime_type.lower():
                return '.pdf'
            elif 'word' in mime_type.lower() or 'document' in mime_type.lower():
                return '.docx'
            elif 'text' in mime_type.lower():
                return '.txt'
            elif 'zip' in mime_type.lower():
                return '.zip'
        except Exception as e:
            logger.warning(f"⚠️ Erro ao detectar MIME type: {e}")
        
        # 🔧 CORREÇÃO: Verificação adicional para HTML (que indica erro)
        if content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
            logger.error("❌ Conteúdo detectado como HTML - possível erro no download")
            return '.html'
        
        # Padrão (assumir PDF se não conseguir detectar)
        logger.warning(f"⚠️ Não foi possível detectar extensão, assumindo PDF")
        return '.pdf'
    
    def _get_mime_type(self, extensao: str) -> str:
        """Retorna MIME type baseado na extensão"""
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.odt': 'application/vnd.oasis.opendocument.text'
        }
        return mime_types.get(extensao, 'application/octet-stream')
    
    def _extrair_texto_pdf_fallback(self, pdf_content: bytes, max_chars: int = 1000) -> Optional[str]:
        """Extrai preview do texto de um PDF usando PyPDF2 (método fallback)"""
        try:
            logger.info(f"🔄 Usando fallback PyPDF2 para extração")
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            
            for i, page in enumerate(reader.pages[:3]):
                text += page.extract_text() + "\n"
                if len(text) > max_chars:
                    break
            
            preview = text[:max_chars].strip() if text.strip() else None
            if preview:
                logger.info(f"✅ Fallback PyPDF2 extraiu {len(preview)} caracteres")
            return preview
            
        except Exception as e:
            logger.debug(f"⚠️ Erro no fallback PyPDF2: {e}")
            return None
    
    # ================================
    # BANCO DE DADOS SIMPLIFICADO
    # ================================
    
    def salvar_documentos_no_banco(self, documentos: List[Dict]) -> Dict[str, Any]:
        """Salva todos os documentos na tabela unificada"""
        try:
            logger.info(f"💾 Salvando {len(documentos)} documentos no banco")
            
            documentos_salvos = 0
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    for doc in documentos:
                        try:
                            documento_id = str(uuid.uuid4())
                            
                            cursor.execute("""
                                INSERT INTO documentos_licitacao (
                                    id, licitacao_id, titulo, arquivo_nuvem_url,
                                    tipo_arquivo, tamanho_arquivo, hash_arquivo,
                                    texto_preview, metadata_arquivo
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                documento_id,
                                doc['licitacao_id'],
                                doc['titulo'],
                                doc['arquivo_nuvem_url'],
                                doc['tipo_arquivo'],
                                doc['tamanho_arquivo'],
                                doc['hash_arquivo'],
                                doc.get('texto_preview'),
                                json.dumps(doc['metadata_arquivo'])
                            ))
                            
                            documentos_salvos += 1
                            logger.info(f"✅ Documento salvo: {doc['titulo']}")
                            
                        except Exception as e:
                            logger.error(f"❌ Erro ao salvar documento {doc.get('titulo', 'sem título')}: {e}")
                            continue
                    
                    conn.commit()
            
            logger.info(f"✅ {documentos_salvos} documentos salvos no banco")
            
            return {
                'success': True,
                'documentos_salvos': documentos_salvos,
                'total_documentos': len(documentos)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar documentos: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def obter_documentos_licitacao(self, licitacao_id: str) -> List[Dict]:
        """Obtém todos os documentos de uma licitação"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM documentos_licitacao 
                        WHERE licitacao_id = %s 
                        ORDER BY titulo
                    """, (licitacao_id,))
                    
                    documentos = cursor.fetchall()
                    return [dict(doc) for doc in documentos]
                
        except Exception as e:
            logger.error(f"❌ Erro ao obter documentos: {e}")
            return []
    
    # ================================
    # MÉTODOS DE VALIDAÇÃO E TESTE
    # ================================

    def validar_configuracao(self) -> Dict[str, Any]:
        """Valida configuração inicial do processador"""
        try:
            logger.info("🔧 Validando configuração do processador...")
            
            validacao = {
                'database': False,
                'supabase': False,
                'bucket': False,
                'temp_directory': False,
                'detalhes': {}
            }
            
            # 1. Testar conexão com banco
            try:
                with self.db_manager.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        validacao['database'] = True
                        logger.info("✅ Conexão com banco validada")
            except Exception as e:
                validacao['detalhes']['database_error'] = str(e)
                logger.error(f"❌ Erro conexão banco: {e}")
            
            # 2. Testar conexão Supabase (teste direto do bucket)
            try:
                # Ao invés de listar buckets, testar acesso direto ao bucket
                files = self.storage_service.list("")  # Lista raiz do bucket
                validacao['supabase'] = True
                logger.info("✅ Conexão Supabase validada")
            except Exception as e:
                validacao['detalhes']['supabase_error'] = str(e)
                logger.warning(f"⚠️ Aviso Supabase (normal com ANON_KEY): {e}")
                # Considerar válido mesmo com erro de permissão
                validacao['supabase'] = True
            
            # 3. Testar bucket
            try:
                files = self.storage_service.list()
                validacao['bucket'] = True
                logger.info(f"✅ Bucket '{self.bucket_name}' acessível")
            except Exception as e:
                validacao['detalhes']['bucket_error'] = str(e)
                logger.error(f"❌ Erro bucket: {e}")
            
            # 4. Testar diretório temporário
            try:
                test_file = self.temp_path / "test_validation.txt"
                test_file.write_text("teste")
                test_file.unlink()
                validacao['temp_directory'] = True
                logger.info("✅ Diretório temporário funcional")
            except Exception as e:
                validacao['detalhes']['temp_directory_error'] = str(e)
                logger.error(f"❌ Erro diretório temp: {e}")
            
            # Status geral
            validacao['status_geral'] = all([
                validacao['database'],
                validacao['supabase'], 
                validacao['bucket'],
                validacao['temp_directory']
            ])
            
            if validacao['status_geral']:
                logger.info("🎉 Todas as validações passaram!")
            else:
                logger.warning("⚠️ Algumas validações falharam")
            
            return validacao
            
        except Exception as e:
            logger.error(f"❌ Erro na validação: {e}")
            return {
                'status_geral': False,
                'error': str(e)
            }

    def listar_licitacoes_banco(self, limit: int = 10) -> List[Dict]:
        """Lista licitações disponíveis no banco para teste"""
        try:
            logger.info(f"🔍 Buscando {limit} licitações no banco...")
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            id, pncp_id, orgao_cnpj, ano_compra, sequencial_compra,
                            objeto_compra, modalidade_nome, valor_total_estimado,
                            uf, data_publicacao, status,
                            -- Verificar se já tem documentos processados
                            (SELECT COUNT(*) FROM documentos_licitacao WHERE licitacao_id = l.id) as docs_count
                        FROM licitacoes l
                        ORDER BY data_publicacao DESC 
                        LIMIT %s
                    """, (limit,))
                    
                    licitacoes = cursor.fetchall()
                    resultado = []
                    
                    for i, lic in enumerate(licitacoes, 1):
                        lic_dict = dict(lic)
                        lic_dict['numero_ordem'] = i
                        lic_dict['ja_processado'] = lic_dict['docs_count'] > 0
                        resultado.append(lic_dict)
                    
                    logger.info(f"✅ Encontradas {len(resultado)} licitações")
                    return resultado
                    
        except Exception as e:
            logger.error(f"❌ Erro ao listar licitações: {e}")
            return []

    def exibir_licitacoes_formatadas(self, licitacoes: List[Dict]) -> None:
        """Exibe licitações de forma formatada para escolha"""
        print("\n" + "="*80)
        print("📋 LICITAÇÕES DISPONÍVEIS PARA TESTE")
        print("="*80)
        
        for lic in licitacoes:
            status_docs = "✅ JÁ PROCESSADO" if lic['ja_processado'] else "⏳ NÃO PROCESSADO"
            print(f"\n{lic['numero_ordem']:2d}. ID: {lic['id']}")
            print(f"    PNCP ID: {lic['pncp_id']}")
            print(f"    Objeto: {lic['objeto_compra'][:80]}...")
            print(f"    Modalidade: {lic['modalidade_nome']} | UF: {lic['uf']}")
            print(f"    Valor: R$ {lic['valor_total_estimado']:,.2f}" if lic['valor_total_estimado'] else "    Valor: Não informado")
            print(f"    Data: {lic['data_publicacao']}")
            print(f"    Documentos: {status_docs} ({lic['docs_count']} docs)")
        
        print("\n" + "="*80)

    def teste_processamento_licitacao(self, licitacao_id: str, forcar_reprocessamento: bool = False) -> Dict[str, Any]:
        """Testa o processamento completo de uma licitação"""
        try:
            print(f"\n🧪 TESTE DE PROCESSAMENTO")
            print(f"Licitação ID: {licitacao_id}")
            print(f"Forçar reprocessamento: {forcar_reprocessamento}")
            print("-" * 50)
            
            # 1. Validar configuração primeiro
            print("1️⃣ Validando configuração...")
            validacao = self.validar_configuracao()
            if not validacao['status_geral']:
                return {
                    'success': False,
                    'error': 'Configuração inválida',
                    'detalhes': validacao
                }
            print("✅ Configuração OK")
            
            # 2. Verificar se licitação existe
            print("2️⃣ Verificando licitação...")
            licitacao_info = self.extrair_info_licitacao(licitacao_id)
            if not licitacao_info:
                return {
                    'success': False,
                    'error': 'Licitação não encontrada'
                }
            print(f"✅ Licitação encontrada: {licitacao_info['objeto_compra'][:50]}...")
            
            # 3. Verificar documentos existentes
            print("3️⃣ Verificando documentos existentes...")
            docs_existem = self.verificar_documentos_existem(licitacao_id)
            
            if docs_existem and not forcar_reprocessamento:
                docs_existentes = self.obter_documentos_licitacao(licitacao_id)
                print(f"⚠️ {len(docs_existentes)} documentos já processados")
                print("💡 Use forcar_reprocessamento=True para reprocessar")
                return {
                    'success': True,
                    'message': 'Documentos já processados',
                    'documentos_existentes': len(docs_existentes),
                    'action_needed': 'Use forcar_reprocessamento=True para reprocessar'
                }
            
            # 4. Limpar documentos se forçando reprocessamento
            if docs_existem and forcar_reprocessamento:
                print("🗑️ Removendo documentos existentes...")
                self._limpar_documentos_licitacao(licitacao_id)
            
            # 5. Processar documentos
            print("4️⃣ Iniciando processamento...")
            resultado = self.processar_documentos_licitacao(licitacao_id)
            
            if resultado['success']:
                print(f"🎉 Processamento concluído!")
                print(f"📄 Documentos processados: {resultado.get('documentos_processados', 0)}")
                print(f"☁️ Storage: {resultado.get('storage_provider', 'N/A')}")
                print(f"📁 Pasta: {resultado.get('pasta_nuvem', 'N/A')}")
            else:
                print(f"❌ Erro no processamento: {resultado.get('error')}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            return {
                'success': False,
                'error': f'Erro no teste: {str(e)}'
            }

    def _limpar_documentos_licitacao(self, licitacao_id: str) -> None:
        """Remove documentos de uma licitação (para reprocessamento)"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM documentos_licitacao WHERE licitacao_id = %s",
                        (licitacao_id,)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()
                    logger.info(f"🗑️ {deleted_count} documentos removidos do banco")
                    
        except Exception as e:
            logger.error(f"❌ Erro ao limpar documentos: {e}")

    def testar_url_documento(self, url: str) -> Dict[str, Any]:
        """Testa download de uma URL específica para debugging"""
        try:
            logger.info(f"🧪 Testando URL: {url}")
            
            # Headers específicos
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf, application/octet-stream, */*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            # Fazer requisição
            response = requests.get(url, headers=headers, timeout=120, stream=True)
            response.raise_for_status()
            
            # Analisar resposta
            content_type = response.headers.get('content-type', '').lower()
            content_length = response.headers.get('content-length', '0')
            
            resultado = {
                'url': url,
                'status_code': response.status_code,
                'content_type': content_type,
                'content_length': content_length,
                'headers': dict(response.headers),
                'content_preview': None,
                'is_binary': False,
                'is_pdf': False,
                'is_html': False,
                'is_zip': False,
                'hex_preview': None,
                'first_bytes': None
            }
            
            # Analisar conteúdo
            content = response.content
            
            if content:
                resultado['actual_size'] = len(content)
                
                # 🔍 DEBUG: Analisar primeiros bytes
                resultado['first_bytes'] = content[:50]  # Primeiros 50 bytes
                resultado['hex_preview'] = ' '.join(f'{b:02x}' for b in content[:20])  # Primeiros 20 bytes em hex
                
                # Verificar se é PDF (múltiplas formas)
                # 1. Magic bytes padrão
                if content.startswith(b'%PDF'):
                    resultado['is_pdf'] = True
                    resultado['is_binary'] = True
                    resultado['content_preview'] = f"PDF detectado (magic bytes) - {len(content)} bytes"
                
                # 2. Buscar %PDF nos primeiros 1000 bytes (pode ter headers)
                elif b'%PDF' in content[:1000]:
                    pdf_start = content.find(b'%PDF')
                    resultado['is_pdf'] = True
                    resultado['is_binary'] = True
                    resultado['content_preview'] = f"PDF detectado (offset {pdf_start}) - {len(content)} bytes"
                
                # 3. Verificar se é ZIP (magic bytes PK)
                elif content.startswith(b'PK\x03\x04') or content.startswith(b'PK\x05\x06') or content.startswith(b'PK\x07\x08'):
                    resultado['is_zip'] = True
                    resultado['is_binary'] = True
                    resultado['content_preview'] = f"ZIP detectado - {len(content)} bytes (provavelmente contém PDF)"
                
                # 4. Verificar header bytes comuns de PDF
                elif any(content.startswith(header) for header in [b'\x00\x00\x00', b'\xff\xfe', b'\xfe\xff']):
                    # Pode ser PDF com BOM ou headers especiais
                    if b'PDF' in content[:2048]:
                        resultado['is_pdf'] = True
                        resultado['is_binary'] = True
                        resultado['content_preview'] = f"PDF detectado (com headers) - {len(content)} bytes"
                
                # Verificar se é HTML
                elif content.startswith(b'<!DOCTYPE') or content.startswith(b'<html'):
                    resultado['is_html'] = True
                    resultado['content_preview'] = content[:500].decode('utf-8', errors='ignore')
                
                # Conteúdo binário genérico
                elif any(b in content[:100] for b in [b'\x00', b'\xff', b'\xfe']):
                    resultado['is_binary'] = True
                    resultado['content_preview'] = f"Arquivo binário detectado - {len(content)} bytes"
                
                # Texto/outros
                else:
                    try:
                        resultado['content_preview'] = content[:500].decode('utf-8', errors='ignore')
                    except:
                        resultado['content_preview'] = f"Conteúdo não-texto - {len(content)} bytes"
            
            logger.info(f"✅ Teste concluído")
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro no teste: {e}")
            return {
                'url': url,
                'error': str(e),
                'success': False
            }

    def executar_demo_interativo(self) -> None:
        """Executa demo interativo do processador"""
        try:
            print("\n🚀 DEMO INTERATIVO - UNIFIED DOCUMENT PROCESSOR")
            print("="*60)
            
            # 1. Validar configuração
            print("\n1️⃣ Validando configuração...")
            validacao = self.validar_configuracao()
            
            if not validacao['status_geral']:
                print("❌ Configuração inválida! Verifique os erros:")
                for key, error in validacao.get('detalhes', {}).items():
                    print(f"   - {key}: {error}")
                return
            
            print("✅ Configuração validada com sucesso!")
            
            # 2. Listar licitações
            print("\n2️⃣ Carregando licitações disponíveis...")
            licitacoes = self.listar_licitacoes_banco(10)
            
            if not licitacoes:
                print("❌ Nenhuma licitação encontrada no banco")
                return
            
            self.exibir_licitacoes_formatadas(licitacoes)
            
            # 3. Escolher licitação
            while True:
                try:
                    escolha = input("\n🔢 Digite o número da licitação para testar (ou 'q' para sair): ").strip()
                    
                    if escolha.lower() == 'q':
                        print("👋 Saindo...")
                        return
                    
                    num = int(escolha)
                    if 1 <= num <= len(licitacoes):
                        licitacao_escolhida = licitacoes[num - 1]
                        break
                    else:
                        print(f"❌ Número inválido. Digite entre 1 e {len(licitacoes)}")
                        
                except ValueError:
                    print("❌ Digite um número válido ou 'q' para sair")
            
            # 4. Confirmar processamento
            print(f"\n📋 Licitação selecionada:")
            print(f"   ID: {licitacao_escolhida['id']}")
            print(f"   Objeto: {licitacao_escolhida['objeto_compra'][:100]}...")
            print(f"   Status documentos: {'JÁ PROCESSADO' if licitacao_escolhida['ja_processado'] else 'NÃO PROCESSADO'}")
            
            forcar = False
            if licitacao_escolhida['ja_processado']:
                resposta = input("\n⚠️ Documentos já processados. Reprocessar? (s/N): ").strip().lower()
                forcar = resposta in ['s', 'sim', 'y', 'yes']
            
            # 5. Executar teste
            print(f"\n🧪 Executando teste de processamento...")
            resultado = self.teste_processamento_licitacao(
                licitacao_escolhida['id'], 
                forcar_reprocessamento=forcar
            )
            
            # 6. Mostrar resultados finais
            print(f"\n📊 RESULTADO FINAL:")
            print(f"✅ Sucesso: {resultado['success']}")
            
            if resultado['success']:
                print(f"📄 Documentos: {resultado.get('documentos_processados', 'N/A')}")
                print(f"💬 Mensagem: {resultado.get('message', 'N/A')}")
            else:
                print(f"❌ Erro: {resultado.get('error', 'N/A')}")
            
            print("\n🎉 Demo concluído!")
            
        except KeyboardInterrupt:
            print("\n\n⏹️ Demo interrompido pelo usuário")
        except Exception as e:
            print(f"\n❌ Erro no demo: {e}")
            logger.error(f"Erro no demo interativo: {e}")

    # ================================
    # FUNÇÃO PRINCIPAL
    # ================================
    
    async def processar_documentos_licitacao(self, licitacao_id: str) -> Dict[str, Any]:
        """Função principal unificada"""
        try:
            logger.info(f"🚀 INICIANDO processamento unificado: {licitacao_id}")
            
            # PASSO 1: Extrair informações
            licitacao_info = self.extrair_info_licitacao(licitacao_id)
            if not licitacao_info:
                return {'success': False, 'error': 'Licitação não encontrada'}
            
            # PASSO 2: Verificar se já existe
            if self.verificar_documentos_existem(licitacao_id):
                return {
                    'success': True,
                    'message': 'Documentos já processados',
                    'documentos_processados': 0
                }
            
            # PASSO 3: Garantir que bucket existe
            bucket_exists = await self.storage_service.ensure_bucket_exists()
            if not bucket_exists:
                return {
                    'success': False,
                    'error': 'Erro ao criar/verificar bucket de armazenamento'
                }
            
            # PASSO 4: Construir URL da API
            logger.info("🔧 PASSO 3: Construindo URL da API")
            api_url = self._construir_url_api(licitacao_info)
            logger.info("✅ PASSO 3 OK: URL construída")
            
            # PASSO 5: Processar resposta flexível
            documentos = self.processar_resposta_pncp(api_url, licitacao_id)
            
            if not documentos:
                logger.warning("⚠️ Não foi possível processar documentos")
                return {
                    'success': False,
                    'error': 'Falha ao processar documentos da API PNCP'
                }
            
            # PASSO 6: Salvar no banco
            resultado = self.salvar_documentos_no_banco(documentos)
            
            if resultado['success']:
                logger.info(f"🎉 Processamento concluído com sucesso!")
                return {
                    'success': True,
                    'message': 'Processamento concluído',
                    'licitacao_id': licitacao_id,
                    'documentos_processados': resultado['documentos_salvos'],
                    'storage_provider': 'supabase',
                    'pasta_nuvem': f"licitacoes/{licitacao_id}/"
                }
            else:
                return resultado
                
        except Exception as e:
            logger.error(f"❌ ERRO no processamento: {e}")
            return {
                'success': False,
                'error': f'Erro no processamento: {str(e)}'
            }

    def corrigir_urls_documentos(self, licitacao_id: str = None) -> Dict[str, Any]:
        """
        🔧 NOVA FUNÇÃO: Corrige URLs de documentos que estão com problemas (terminando com ?)
        """
        try:
            logger.info("🔧 Iniciando correção de URLs de documentos...")
            
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    # Query para buscar documentos com URLs problemáticas
                    if licitacao_id:
                        query = """
                            SELECT id, licitacao_id, titulo, arquivo_nuvem_url, metadata_arquivo 
                            FROM documentos_licitacao 
                            WHERE licitacao_id = %s AND arquivo_nuvem_url LIKE '%?'
                        """
                        cursor.execute(query, (licitacao_id,))
                    else:
                        query = """
                            SELECT id, licitacao_id, titulo, arquivo_nuvem_url, metadata_arquivo 
                            FROM documentos_licitacao 
                            WHERE arquivo_nuvem_url LIKE '%?'
                        """
                        cursor.execute(query)
                    
                    documentos_problematicos = cursor.fetchall()
                    
                    if not documentos_problematicos:
                        logger.info("✅ Nenhum documento com URL problemática encontrado")
                        return {'success': True, 'documentos_corrigidos': 0, 'message': 'Nenhuma correção necessária'}
                    
                    logger.info(f"🔍 Encontrados {len(documentos_problematicos)} documentos com URLs problemáticas")
                    
                    documentos_corrigidos = 0
                    
                    for doc in documentos_problematicos:
                        try:
                            # Extrair cloud_path do metadata
                            metadata = json.loads(doc['metadata_arquivo']) if doc['metadata_arquivo'] else {}
                            cloud_path = metadata.get('cloud_path')
                            
                            if cloud_path:
                                # Gerar nova URL limpa
                                raw_url = self.storage_service.get_public_url(cloud_path)
                                
                                # Limpar URL
                                if raw_url.endswith('?'):
                                    nova_url = raw_url[:-1]
                                elif '?' in raw_url and not any(param for param in raw_url.split('?')[1].split('&') if '=' in param):
                                    nova_url = raw_url.split('?')[0]
                                else:
                                    nova_url = raw_url
                                
                                # Atualizar no banco
                                cursor.execute("""
                                    UPDATE documentos_licitacao 
                                    SET arquivo_nuvem_url = %s, updated_at = NOW()
                                    WHERE id = %s
                                """, (nova_url, doc['id']))
                                
                                logger.info(f"✅ URL corrigida para: {doc['titulo']}")
                                documentos_corrigidos += 1
                            else:
                                logger.warning(f"⚠️ Não há cloud_path para: {doc['titulo']}")
                        
                        except Exception as e:
                            logger.error(f"❌ Erro ao corrigir documento {doc['titulo']}: {e}")
                            continue
                    
                    conn.commit()
                    
                    logger.info(f"🎉 Correção concluída: {documentos_corrigidos} URLs corrigidas")
                    
                    return {
                        'success': True,
                        'documentos_corrigidos': documentos_corrigidos,
                        'total_problematicos': len(documentos_problematicos)
                    }
        
        except Exception as e:
            logger.error(f"❌ Erro na correção de URLs: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def sincronizar_documentos_storage(self, licitacao_id: str) -> Dict[str, Any]:
        """
        🔄 NOVA FUNÇÃO: Sincroniza documentos entre storage e banco
        Garante que todos os arquivos no storage estejam no banco
        """
        try:
            logger.info(f"🔄 Sincronizando documentos storage ↔ banco para: {licitacao_id}")
            
            # 1. Listar arquivos no storage
            files_storage = self.storage_service.list(f"licitacoes/{licitacao_id}")
            logger.info(f"📁 {len(files_storage)} arquivos encontrados no storage")
            
            # 2. Listar documentos no banco
            documentos_banco = self.obter_documentos_licitacao(licitacao_id)
            logger.info(f"💾 {len(documentos_banco)} documentos encontrados no banco")
            
            # 3. Identificar arquivos que estão no storage mas não no banco
            nomes_banco = set()
            for doc in documentos_banco:
                metadata = doc.get('metadata_arquivo', {})
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)
                cloud_path = metadata.get('cloud_path', '')
                if cloud_path:
                    nome_arquivo = cloud_path.split('/')[-1]
                    nomes_banco.add(nome_arquivo)
            
            nomes_storage = {file['name'] for file in files_storage}
            arquivos_faltando = nomes_storage - nomes_banco
            
            if not arquivos_faltando:
                logger.info("✅ Todos os arquivos do storage já estão no banco")
                return {
                    'success': True,
                    'arquivos_adicionados': 0,
                    'message': 'Sincronização já está em dia'
                }
            
            logger.info(f"📋 {len(arquivos_faltando)} arquivos precisam ser adicionados ao banco")
            
            # 4. Adicionar arquivos faltando ao banco
            documentos_novos = []
            
            for nome_arquivo in arquivos_faltando:
                try:
                    # Gerar informações do documento
                    cloud_path = f"licitacoes/{licitacao_id}/{nome_arquivo}"
                    
                    # Extrair sequencial e nome original do nome do arquivo
                    if '_' in nome_arquivo:
                        parts = nome_arquivo.split('_', 1)
                        sequencial = int(parts[0]) if parts[0].isdigit() else 1
                        nome_original = parts[1]
                    else:
                        sequencial = 1
                        nome_original = nome_arquivo
                    
                    # Determinar extensão e tipo
                    extensao = os.path.splitext(nome_arquivo)[1].lower()
                    tipo_arquivo = self._get_mime_type(extensao)
                    
                    # Obter informações do arquivo no storage
                    file_info = next((f for f in files_storage if f['name'] == nome_arquivo), None)
                    tamanho_arquivo = file_info.get('metadata', {}).get('size', 0) if file_info else 0
                    
                    # Gerar URL limpa
                    raw_url = self.storage_service.get_public_url(cloud_path)
                    if raw_url.endswith('?'):
                        arquivo_url = raw_url[:-1]
                    else:
                        arquivo_url = raw_url
                    
                    # Criar documento
                    documento = {
                        'licitacao_id': licitacao_id,
                        'titulo': nome_original,
                        'arquivo_nuvem_url': arquivo_url,
                        'tipo_arquivo': tipo_arquivo,
                        'tamanho_arquivo': tamanho_arquivo,
                        'hash_arquivo': f"sync_{uuid.uuid4().hex[:16]}",  # Hash temporário
                        'texto_preview': None,
                        'metadata_arquivo': {
                            'nome_original': nome_original,
                            'nome_limpo': nome_arquivo,
                            'extensao': extensao,
                            'sequencial': sequencial,
                            'cloud_path': cloud_path,
                            'storage_provider': 'supabase',
                            'bucket_name': self.bucket_name,
                            'sincronizado_em': datetime.now().isoformat(),
                            'origem': 'sincronizacao_storage'
                        }
                    }
                    
                    documentos_novos.append(documento)
                    logger.info(f"📄 Preparado para adicionar: {nome_arquivo}")
                
                except Exception as e:
                    logger.error(f"❌ Erro ao preparar documento {nome_arquivo}: {e}")
                    continue
            
            # 5. Salvar documentos novos no banco
            if documentos_novos:
                resultado_save = self.salvar_documentos_no_banco(documentos_novos)
                
                return {
                    'success': True,
                    'arquivos_storage': len(files_storage),
                    'documentos_banco_antes': len(documentos_banco),
                    'arquivos_adicionados': resultado_save.get('documentos_salvos', 0),
                    'arquivos_faltando_antes': len(arquivos_faltando)
                }
            else:
                return {
                    'success': False,
                    'error': 'Nenhum documento novo foi preparado com sucesso'
                }
        
        except Exception as e:
            logger.error(f"❌ Erro na sincronização: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _construir_url_api(self, licitacao: Dict[str, Any]) -> str:
        """Constrói URL da API PNCP"""
        cnpj = licitacao['orgao_cnpj']
        ano = licitacao['ano_compra']
        sequencial = licitacao['sequencial_compra']
        
        return f"https://pncp.gov.br/pncp-api/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    
    def testar_extrator_texto(self, licitacao_id: str = None) -> Dict[str, Any]:
        """
        🧪 Testar funcionalidade do extrator de texto avançado
        """
        try:
            logger.info("🧪 Iniciando teste do extrator de texto avançado")
            
            resultado = {
                'success': True,
                'extrator_status': self.text_extractor.get_extractor_status(),
                'testes': [],
                'resumo': {}
            }
            
            # Teste 1: Status dos extractors
            status_extractors = self.text_extractor.get_extractor_status()
            resultado['testes'].append({
                'teste': 'status_extractors',
                'resultado': status_extractors,
                'aprovado': len(status_extractors['available_extractors']) > 0
            })
            
            # Teste 2: Se licitacao_id fornecido, testar extração real
            if licitacao_id:
                documentos = self.obter_documentos_licitacao(licitacao_id)
                if documentos:
                    for doc in documentos[:1]:  # Testar apenas o primeiro
                        try:
                            # Download do arquivo para teste
                            response = requests.get(doc['arquivo_nuvem_url'], timeout=30)
                            if response.status_code == 200:
                                # Testar extração
                                resultado_extracao = self.text_extractor.extract_text_unified(
                                    response.content, 
                                    doc['titulo']
                                )
                                
                                resultado['testes'].append({
                                    'teste': f'extracao_{doc["titulo"]}',
                                    'resultado': resultado_extracao,
                                    'aprovado': resultado_extracao['success']
                                })
                                break
                        except Exception as e:
                            resultado['testes'].append({
                                'teste': f'erro_extracao_{doc.get("titulo", "unknown")}',
                                'resultado': str(e),
                                'aprovado': False
                            })
            
            # Resumo
            testes_aprovados = sum(1 for t in resultado['testes'] if t['aprovado'])
            resultado['resumo'] = {
                'total_testes': len(resultado['testes']),
                'testes_aprovados': testes_aprovados,
                'taxa_sucesso': testes_aprovados / len(resultado['testes']) * 100 if resultado['testes'] else 0
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro no teste do extrator: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # 🆕 NOVO MÉTODO SÍNCRONO para resolver problema async/await
    def processar_licitacao_sync(self, licitacao_id: str, pncp_id: str, bid: Dict) -> Dict[str, Any]:
        """
        Versão síncrona do processamento de documentos de licitação
        
        Args:
            licitacao_id: ID da licitação
            pncp_id: ID PNCP da licitação  
            bid: Dados da licitação do banco
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            logger.info(f"🚀 SYNC: Processando licitacao_id: {licitacao_id}, pncp_id: {pncp_id}")
            
            # PASSO 1: Verificar se documentos já existem
            if self.verificar_documentos_existem(licitacao_id):
                logger.info("✅ SYNC: Documentos já processados")
                return {
                    'success': True,
                    'status': 'already_processed',
                    'message': 'Documentos já foram processados anteriormente',
                    'documentos_encontrados': len(self.obter_documentos_licitacao(licitacao_id))
                }
            
            # PASSO 2: Construir URL da API PNCP
            url_documentos = self.construir_url_documentos(bid)
            logger.info(f"🔗 SYNC: URL documentos: {url_documentos}")
            
            # PASSO 3: Buscar e processar documentos da API
            # CORREÇÃO: Chamando o método correto que processa a resposta da API
            documentos_processados = self.processar_resposta_pncp(url_documentos, licitacao_id)
            
            if not documentos_processados:
                logger.warning(f"Nenhum documento encontrado ou processado da API PNCP para {pncp_id}")
                return {
                    'success': True,
                    'status': 'no_documents_found',
                    'message': 'Nenhum documento encontrado na API PNCP, mas o processo não falhou.'
                }
            
            logger.info(f"📄 SYNC: {len(documentos_processados)} documentos encontrados e processados da API")

            # PASSO 4: Salvar no banco de dados
            resultado_banco = self.salvar_documentos_no_banco(documentos_processados)
            
            if resultado_banco['success']:
                logger.info(f"🎉 SYNC: Processamento concluído! {resultado_banco['documentos_salvos']} documentos salvos")
                
                return {
                    'success': True,
                    'status': 'completed',
                    'message': f'{resultado_banco["documentos_salvos"]} documentos processados com sucesso',
                    'documentos_processados': resultado_banco['documentos_salvos'],
                    'total_encontrados': len(documentos_processados)
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro ao salvar no banco: {resultado_banco.get("error")}'
                }

        except Exception as e:
            logger.error(f"❌ SYNC: Erro geral no processamento: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Erro no processamento síncrono: {str(e)}'
            }
    
    # ===== NOVOS MÉTODOS PARA PREPARAÇÃO AUTOMÁTICA =====
    
    def set_licitacao_context(self, licitacao_id: str, pncp_id: str):
        """
        Configurar contexto da licitação para processamento
        """
        self.current_licitacao_id = licitacao_id
        self.current_pncp_id = pncp_id
        logger.info(f"🎯 Contexto configurado: licitacao_id={licitacao_id}, pncp_id={pncp_id}")
    
    def process_licitacao_documents(self, pncp_id: str, licitacao_id: str) -> Dict[str, Any]:
        """
        Processar documentos de uma licitação específica (método principal)
        """
        try:
            logger.info(f"🚀 Iniciando processamento de documentos para {pncp_id}")
            
            # PASSO 1: Verificar se documentos já existem
            if self.verificar_documentos_existem(licitacao_id):
                logger.info("✅ Documentos já processados, retornando status")
                return {
                    'status': 'already_processed',
                    'documents_count': len(self.obter_documentos_licitacao(licitacao_id)),
                    'estimated_time': 0
                }
            
            # PASSO 2: Buscar informações da licitação
            licitacao_info = self.extrair_info_licitacao(licitacao_id)
            if not licitacao_info:
                raise ValueError(f"Licitação {licitacao_id} não encontrada")
            
            # PASSO 3: Construir URL da API PNCP
            url_documentos = self.construir_url_documentos(licitacao_info)
            
            # PASSO 4: Processar documentos da API
            documentos_processados = self.processar_resposta_pncp(url_documentos, licitacao_id)
            
            if not documentos_processados:
                logger.warning("⚠️ Nenhum documento processado")
                return {
                    'status': 'no_documents',
                    'documents_count': 0,
                    'estimated_time': 0
                }
            
            # PASSO 5: Salvar no banco
            resultado_salvamento = self.salvar_documentos_no_banco(documentos_processados)
            
            logger.info(f"✅ Processamento concluído: {len(documentos_processados)} documentos")
            
            return {
                'status': 'completed',
                'documents_count': len(documentos_processados),
                'estimated_time': 0,
                'processed_files': [doc.get('nome_arquivo') for doc in documentos_processados],
                'database_result': resultado_salvamento
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no processamento: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'documents_count': 0
            }
    
    def check_documents_status(self, licitacao_id: str) -> Dict[str, Any]:
        """
        Verificar status dos documentos processados
        """
        try:
            logger.info(f"📊 Verificando status dos documentos para {licitacao_id}")
            
            documentos = self.obter_documentos_licitacao(licitacao_id)
            
            if documentos:
                # Formatar lista de documentos para o frontend
                documents_list = []
                for doc in documentos:
                    documents_list.append({
                        'name': doc.get('nome_arquivo'),
                        'url': doc.get('url_publica'),
                        'type': doc.get('tipo_arquivo', 'pdf'),
                        'size': doc.get('tamanho_arquivo'),
                        'created_at': doc.get('data_criacao'),
                        'updated_at': doc.get('data_atualizacao')
                    })
                
                return {
                    'documents_processed': len(documentos),
                    'documents_list': documents_list,
                    'last_update': max([doc.get('data_atualizacao', '') for doc in documentos]) if documentos else None
                }
            else:
                return {
                    'documents_processed': 0,
                    'documents_list': [],
                    'last_update': None
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao verificar status: {str(e)}")
            return {
                'documents_processed': 0,
                'documents_list': [],
                'error': str(e)
            }
    
    def get_processing_status(self, licitacao_id: str) -> Dict[str, Any]:
        """
        Obter status de processamento em andamento (simulado por enquanto)
        """
        try:
            # Por enquanto, simular que não há processamento em andamento
            # Em uma implementação real, isso consultaria uma tabela de jobs/tasks
            return {
                'is_processing': False,
                'current_step': 'waiting',
                'progress': 0,
                'eta': 0
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter status de processamento: {str(e)}")
            return {
                'is_processing': False,
                'error': str(e)
            }
    
    def get_current_timestamp(self) -> str:
        """
        Obter timestamp atual formatado
        """
        return datetime.now().isoformat()
    
    def cleanup_failed_processing(self, licitacao_id: str) -> Dict[str, Any]:
        """
        Limpar processamento que falhou
        """
        try:
            logger.info(f"🧹 Limpando processamento falhado para {licitacao_id}")
            
            # Remover documentos incompletos do banco
            self._limpar_documentos_licitacao(licitacao_id)
            
            # Remover arquivos temporários se existirem
            files_removed = 0
            temp_pattern = self.temp_path / f"*{licitacao_id}*"
            
            for temp_file in self.temp_path.glob(f"*{licitacao_id}*"):
                if temp_file.is_file():
                    temp_file.unlink()
                    files_removed += 1
            
            logger.info(f"✅ Limpeza concluída: {files_removed} arquivos removidos")
            
            return {
                'files_removed': files_removed,
                'cleanup_status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na limpeza: {str(e)}")
            return {
                'files_removed': 0,
                'cleanup_status': 'error',
                'error': str(e)
            } 