# Document processor module 
import pymupdf  # PyMuPDF para extração de PDF
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    text: str
    chunk_type: str
    page_number: int
    section_title: Optional[str] = None
    token_count: int = 0
    char_count: int = 0
    metadata: Dict = None

class DocumentProcessor:
    """Processador inteligente de documentos PDF com chunking avançado"""
    
    def __init__(self):
        self.chunk_size = 800  # tokens aproximados
        self.chunk_overlap = 100
        self.min_chunk_size = 100
        
    def extract_text_from_url(self, url: str) -> Optional[str]:
        """Extrai texto completo de PDF via URL"""
        try:
            logger.info(f"📥 Baixando PDF: {url}")
            
            # 🔧 CORREÇÃO: Detectar se é URL do Supabase e usar método correto
            if 'supabase.co/storage/v1/object/public' in url:
                # É URL pública do Supabase - vamos usar signed URL
                logger.info("🔗 Detectado URL do Supabase, usando signed URL...")
                return self._extract_text_from_supabase_url(url)
            else:
                # URL externa normal
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                
                # Extrair texto usando PyMuPDF
                pdf_document = pymupdf.open(stream=response.content, filetype="pdf")
                full_text = ""
                
                for page_num in range(pdf_document.page_count):
                    page = pdf_document.load_page(page_num)
                    text = page.get_text()
                    full_text += f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"
                
                pdf_document.close()
                
                logger.info(f"✅ Texto extraído: {len(full_text)} caracteres")
                return full_text
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair texto: {e}")
            return None
    
    def _extract_text_from_supabase_url(self, public_url: str) -> Optional[str]:
        """
        🔧 NOVA FUNÇÃO: Extrai texto de PDF usando Supabase signed URL ou download direto
        """
        try:
            # Importar Supabase client
            from supabase import create_client
            import os
            
            # Configurar client Supabase
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            
            if not supabase_url or not supabase_key:
                logger.error("❌ Configurações Supabase não encontradas")
                return None
            
            supabase = create_client(supabase_url, supabase_key)
            
            # Extrair path do arquivo da URL pública
            # URL formato: https://.../storage/v1/object/public/bucket/path
            url_parts = public_url.split('/storage/v1/object/public/')
            if len(url_parts) != 2:
                logger.error(f"❌ Formato de URL inválido: {public_url}")
                return None
            
            # Separar bucket e path
            bucket_and_path = url_parts[1]
            path_parts = bucket_and_path.split('/', 1)
            if len(path_parts) != 2:
                logger.error(f"❌ Não foi possível extrair bucket/path: {bucket_and_path}")
                return None
            
            bucket_name = path_parts[0]
            file_path = path_parts[1]
            
            logger.info(f"📦 Bucket: {bucket_name}, Path: {file_path}")
            
            # Método 1: Tentar download direto (mais eficiente)
            try:
                logger.info("📥 Tentando download direto...")
                pdf_content = supabase.storage.from_(bucket_name).download(file_path)
                
                if pdf_content:
                    logger.info(f"✅ Download direto OK: {len(pdf_content)} bytes")
                    return self._extract_text_from_bytes(pdf_content)
                    
            except Exception as e:
                logger.warning(f"⚠️ Download direto falhou: {e}")
            
            # Método 2: Usar signed URL
            try:
                logger.info("🔗 Criando signed URL...")
                signed_result = supabase.storage.from_(bucket_name).create_signed_url(
                    file_path, 
                    expires_in=3600  # 1 hora
                )
                
                if signed_result and signed_result.get('signedURL'):
                    signed_url = signed_result['signedURL']
                    logger.info("📥 Baixando via signed URL...")
                    
                    response = requests.get(signed_url, timeout=60)
                    response.raise_for_status()
                    
                    logger.info(f"✅ Download via signed URL OK: {len(response.content)} bytes")
                    return self._extract_text_from_bytes(response.content)
                    
            except Exception as e:
                logger.error(f"❌ Signed URL falhou: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar URL Supabase: {e}")
            return None
    
    def _extract_text_from_bytes(self, pdf_content: bytes) -> Optional[str]:
        """
        🔧 NOVA FUNÇÃO: Extrai texto de conteúdo PDF em bytes
        """
        try:
            # Extrair texto usando PyMuPDF
            pdf_document = pymupdf.open(stream=pdf_content, filetype="pdf")
            full_text = ""
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                text = page.get_text()
                full_text += f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"
            
            pdf_document.close()
            
            logger.info(f"✅ Texto extraído: {len(full_text)} caracteres")
            return full_text
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair texto do PDF: {e}")
            return None
    
    def create_intelligent_chunks(self, text: str, documento_id: str) -> List[DocumentChunk]:
        """Cria chunks inteligentes baseados na estrutura do documento"""
        try:
            chunks = []
            
            # 1. Dividir por páginas primeiro
            pages = self._split_by_pages(text)
            
            for page_num, page_text in enumerate(pages):
                # 2. Detectar estrutura da página
                sections = self._detect_document_structure(page_text)
                
                # 3. Processar cada seção
                for section in sections:
                    section_chunks = self._create_section_chunks(
                        section, page_num + 1
                    )
                    chunks.extend(section_chunks)
            
            # 4. Aplicar overlap entre chunks adjacentes
            chunks = self._apply_chunk_overlap(chunks)
            
            # 5. Filtrar chunks muito pequenos
            chunks = [c for c in chunks if c.char_count >= self.min_chunk_size]
            
            logger.info(f"✅ Criados {len(chunks)} chunks inteligentes")
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar chunks: {e}")
            return []
    
    def _split_by_pages(self, text: str) -> List[str]:
        """Divide texto por páginas"""
        page_pattern = r'--- PÁGINA \d+ ---'
        pages = re.split(page_pattern, text)
        return [page.strip() for page in pages if page.strip()]
    
    def _detect_document_structure(self, page_text: str) -> List[Dict]:
        """Detecta estrutura do documento (títulos, parágrafos, listas, etc.)"""
        sections = []
        current_section = None
        
        lines = page_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detectar tipo de linha
            line_type = self._classify_line(line)
            
            # Agrupar linhas em seções
            if line_type in ['title', 'subtitle'] or (
                current_section and len(current_section['text']) > 1000
            ):
                # Iniciar nova seção
                if current_section:
                    sections.append(current_section)
                
                current_section = {
                    'text': line,
                    'type': line_type,
                    'title': line if line_type in ['title', 'subtitle'] else None
                }
            else:
                # Adicionar à seção atual
                if current_section:
                    current_section['text'] += f"\n{line}"
                else:
                    current_section = {
                        'text': line,
                        'type': line_type,
                        'title': None
                    }
        
        # Adicionar última seção
        if current_section:
            sections.append(current_section)
        
        return sections
    
    def _classify_line(self, line: str) -> str:
        """Classifica o tipo de linha do documento"""
        line_upper = line.upper()
        
        # Títulos (MAIÚSCULAS, números, etc.)
        if (len(line) < 100 and 
            (line_upper == line or 
             re.match(r'^\d+\.?\s+[A-Z]', line) or
             re.match(r'^[IVX]+\.?\s+[A-Z]', line))):
            return 'title'
        
        # Subtítulos
        elif (len(line) < 80 and 
              (re.match(r'^\d+\.\d+', line) or
               line.endswith(':'))):
            return 'subtitle'
        
        # Listas
        elif re.match(r'^[a-z]\)|^\d+\)|^-|^•|^\*', line):
            return 'list'
        
        # Tabelas (linhas com múltiplos separadores)
        elif len(re.findall(r'\s{3,}|\t|:', line)) >= 2:
            return 'table'
        
        # Parágrafo normal
        else:
            return 'paragraph'
    
    def _create_section_chunks(self, section: Dict, page_number: int) -> List[DocumentChunk]:
        """Cria chunks de uma seção específica"""
        chunks = []
        text = section['text']
        section_type = section['type']
        section_title = section.get('title')
        
        # Se seção é pequena, criar um chunk único
        if len(text) <= self.chunk_size * 4:  # 4 chars ≈ 1 token
            chunk = DocumentChunk(
                text=text,
                chunk_type=section_type,
                page_number=page_number,
                section_title=section_title,
                char_count=len(text),
                token_count=len(text) // 4,  # Aproximação
                metadata={'section_complete': True}
            )
            chunks.append(chunk)
        else:
            # Dividir seção em chunks menores
            sentences = self._split_into_sentences(text)
            current_chunk_text = ""
            
            for sentence in sentences:
                # Verificar se adicionar a frase excede o tamanho
                if len(current_chunk_text + sentence) > self.chunk_size * 4:
                    # Salvar chunk atual
                    if current_chunk_text.strip():
                        chunk = DocumentChunk(
                            text=current_chunk_text.strip(),
                            chunk_type=section_type,
                            page_number=page_number,
                            section_title=section_title,
                            char_count=len(current_chunk_text),
                            token_count=len(current_chunk_text) // 4,
                            metadata={'section_complete': False}
                        )
                        chunks.append(chunk)
                    
                    current_chunk_text = sentence
                else:
                    current_chunk_text += sentence
            
            # Adicionar último chunk
            if current_chunk_text.strip():
                chunk = DocumentChunk(
                    text=current_chunk_text.strip(),
                    chunk_type=section_type,
                    page_number=page_number,
                    section_title=section_title,
                    char_count=len(current_chunk_text),
                    token_count=len(current_chunk_text) // 4,
                    metadata={'section_complete': False}
                )
                chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divide texto em frases"""
        # Padrão para dividir frases em português
        sentence_pattern = r'[.!?]+\s+'
        sentences = re.split(sentence_pattern, text)
        
        # Recolocar pontuação
        result = []
        for i, sentence in enumerate(sentences[:-1]):
            # Encontrar a pontuação que foi removida
            next_start = sum(len(s) for s in sentences[:i+1]) + i
            if next_start < len(text):
                punct_match = re.match(r'[.!?]+', text[next_start:])
                if punct_match:
                    sentence += punct_match.group()
            result.append(sentence + ' ')
        
        # Adicionar última frase
        if sentences[-1].strip():
            result.append(sentences[-1])
        
        return result
    
    def _apply_chunk_overlap(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Aplica overlap entre chunks adjacentes"""
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.text
            
            # Adicionar contexto do chunk anterior
            if i > 0:
                prev_chunk = chunks[i-1]
                prev_words = prev_chunk.text.split()
                overlap_words = prev_words[-self.chunk_overlap//4:]  # Aproximação
                chunk_text = ' '.join(overlap_words) + ' ' + chunk_text
            
            # Criar chunk com overlap
            new_chunk = DocumentChunk(
                text=chunk_text,
                chunk_type=chunk.chunk_type,
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                char_count=len(chunk_text),
                token_count=len(chunk_text) // 4,
                metadata={
                    **(chunk.metadata or {}),
                    'has_overlap': i > 0
                }
            )
            overlapped_chunks.append(new_chunk)
        
        return overlapped_chunks 