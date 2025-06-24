import os
import time
import io
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio

# Imports padrão
import PyPDF2
import pymupdf

# Imports para MarkItDown
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    print("⚠️  MarkItDown não instalado. Execute: pip install markitdown[all]")

# Imports para Dockling (comentado para teste inicial)
# try:
#     from docling.document_converter import DocumentConverter
#     DOCKLING_AVAILABLE = True
# except ImportError:
#     DOCKLING_AVAILABLE = False
#     print("⚠️  Dockling não instalado. Execute: pip install docling")

DOCKLING_AVAILABLE = False  # Forçar False para testar MarkItDown primeiro

logger = logging.getLogger(__name__)

class AdvancedTextExtractor:
    """
    Extrator de texto avançado com múltiplas engines:
    1. MarkItDown (Microsoft) - Principal
    2. DocKling - Alternativa (comentada para teste)
    3. PyMuPDF - Fallback
    4. PyPDF2 - Último recurso
    """
    
    def __init__(self):
        self.temp_dir = Path('./storage/temp/text_extraction')
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar extractors disponíveis
        self.extractors = {
            'markitdown': {
                'available': MARKITDOWN_AVAILABLE,
                'instance': None,
                'priority': 1
            },
            # 'dockling': {
            #     'available': DOCKLING_AVAILABLE,
            #     'instance': None,
            #     'priority': 2
            # },
            'pymupdf': {
                'available': True,
                'instance': None,
                'priority': 3
            },
            'pypdf2': {
                'available': True,
                'instance': None,
                'priority': 4
            }
        }
        
        # Inicializar extractors
        self._init_extractors()
    
    def _init_extractors(self):
        """Inicializa os extractors disponíveis"""
        try:
            # Inicializar MarkItDown
            if MARKITDOWN_AVAILABLE:
                try:
                    self.extractors['markitdown']['instance'] = MarkItDown()
                    logger.info("✅ MarkItDown inicializado com sucesso")
                except Exception as e:
                    logger.error(f"❌ Erro ao inicializar MarkItDown: {e}")
                    self.extractors['markitdown']['available'] = False
            
            # # Inicializar DocKling (comentado)
            # if DOCKLING_AVAILABLE:
            #     try:
            #         self.extractors['dockling']['instance'] = DocumentConverter()
            #         logger.info("✅ DocKling inicializado com sucesso")
            #     except Exception as e:
            #         logger.error(f"❌ Erro ao inicializar DocKling: {e}")
            #         self.extractors['dockling']['available'] = False
            
            # Registrar status
            available_extractors = [name for name, config in self.extractors.items() if config['available']]
            logger.info(f"🔧 Extractors disponíveis: {', '.join(available_extractors)}")
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização de extractors: {e}")
    
    def extract_text_from_bytes(self, pdf_content: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
        """
        Extrai texto de PDF usando a melhor engine disponível
        
        Returns:
            Dict com: text, extractor_used, extraction_time, success, error (se houver)
        """
        start_time = time.time()
        
        # Ordenar extractors por prioridade
        sorted_extractors = sorted(
            [(name, config) for name, config in self.extractors.items() if config['available']], 
            key=lambda x: x[1]['priority']
        )
        
        logger.info(f"📄 Extraindo texto de PDF ({len(pdf_content)} bytes) - {len(sorted_extractors)} engines disponíveis")
        
        for extractor_name, config in sorted_extractors:
            try:
                logger.info(f"🔄 Tentando extrator: {extractor_name}")
                
                if extractor_name == 'markitdown':
                    result = self._extract_with_markitdown(pdf_content, filename)
                # elif extractor_name == 'dockling':
                #     result = self._extract_with_dockling(pdf_content, filename)
                elif extractor_name == 'pymupdf':
                    result = self._extract_with_pymupdf(pdf_content)
                elif extractor_name == 'pypdf2':
                    result = self._extract_with_pypdf2(pdf_content)
                else:
                    continue
                
                if result['success'] and result['text'].strip():
                    extraction_time = time.time() - start_time
                    logger.info(f"✅ Sucesso com {extractor_name} em {extraction_time:.2f}s - {len(result['text'])} chars")
                    
                    return {
                        'text': result['text'],
                        'extractor_used': extractor_name,
                        'extraction_time': extraction_time,
                        'success': True,
                        'char_count': len(result['text']),
                        'page_count': result.get('page_count', 0),
                        'metadata': result.get('metadata', {})
                    }
                else:
                    logger.warning(f"⚠️ {extractor_name} falhou ou retornou texto vazio")
                    
            except Exception as e:
                logger.error(f"❌ Erro com {extractor_name}: {e}")
                continue
        
        # Se chegou aqui, todos falharam
        extraction_time = time.time() - start_time
        logger.error(f"❌ Todos os extractors falharam em {extraction_time:.2f}s")
        
        return {
            'text': '',
            'extractor_used': None,
            'extraction_time': extraction_time,
            'success': False,
            'error': 'Todos os extractors de texto falharam'
        }
    
    def _extract_with_markitdown(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
        """Extrai texto usando MarkItDown"""
        try:
            markitdown = self.extractors['markitdown']['instance']
            if not markitdown:
                return {'success': False, 'error': 'MarkItDown não inicializado'}
            
            # Salvar PDF temporariamente (MarkItDown trabalha com arquivos)
            temp_pdf = self.temp_dir / f"markitdown_{int(time.time())}_{filename}"
            
            try:
                with open(temp_pdf, 'wb') as f:
                    f.write(pdf_content)
                
                # Extrair usando MarkItDown
                logger.info(f"🔄 MarkItDown processando: {temp_pdf.name}")
                result = markitdown.convert(str(temp_pdf))
                
                if result and hasattr(result, 'text_content') and result.text_content:
                    text = result.text_content.strip()
                    
                    # Obter metadados se disponível
                    metadata = {}
                    if hasattr(result, 'metadata'):
                        metadata = result.metadata or {}
                    
                    logger.info(f"✅ MarkItDown extraiu {len(text)} caracteres")
                    
                    return {
                        'success': True,
                        'text': text,
                        'metadata': {
                            'engine': 'markitdown',
                            'markitdown_metadata': metadata
                        }
                    }
                else:
                    return {'success': False, 'error': 'MarkItDown retornou resultado vazio'}
                    
            finally:
                # Limpar arquivo temporário
                if temp_pdf.exists():
                    temp_pdf.unlink()
                    
        except Exception as e:
            logger.error(f"❌ Erro MarkItDown: {e}")
            return {'success': False, 'error': str(e)}
    
    # def _extract_with_dockling(self, pdf_content: bytes, filename: str) -> Dict[str, Any]:
    #     """Extrai texto usando DocKling"""
    #     try:
    #         converter = self.extractors['dockling']['instance']
    #         if not converter:
    #             return {'success': False, 'error': 'DocKling não inicializado'}
    #         
    #         # Salvar PDF temporariamente
    #         temp_pdf = self.temp_dir / f"dockling_{int(time.time())}_{filename}"
    #         
    #         try:
    #             with open(temp_pdf, 'wb') as f:
    #                 f.write(pdf_content)
    #             
    #             # Converter usando DocKling
    #             logger.info(f"🔄 DocKling processando: {temp_pdf.name}")
    #             result = converter.convert(str(temp_pdf))
    #             
    #             if result and hasattr(result, 'document'):
    #                 text = result.document.export_to_markdown()
    #                 
    #                 if text and text.strip():
    #                     logger.info(f"✅ DocKling extraiu {len(text)} caracteres")
    #                     
    #                     return {
    #                         'success': True,
    #                         'text': text.strip(),
    #                         'page_count': getattr(result.document, 'page_count', 0),
    #                         'metadata': {
    #                             'engine': 'dockling',
    #                             'dockling_metadata': getattr(result, 'metadata', {})
    #                         }
    #                     }
    #             
    #             return {'success': False, 'error': 'DocKling retornou resultado vazio'}
    #             
    #         finally:
    #             # Limpar arquivo temporário
    #             if temp_pdf.exists():
    #                 temp_pdf.unlink()
    #                 
    #     except Exception as e:
    #         logger.error(f"❌ Erro DocKling: {e}")
    #         return {'success': False, 'error': str(e)}
    
    def _extract_with_pymupdf(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extrai texto usando PyMuPDF"""
        try:
            # Abrir PDF do conteúdo em bytes
            pdf_document = pymupdf.open(stream=pdf_content, filetype="pdf")
            
            full_text = ""
            page_count = pdf_document.page_count
            
            for page_num in range(page_count):
                page = pdf_document.load_page(page_num)
                text = page.get_text()
                full_text += f"\n--- PÁGINA {page_num + 1} ---\n{text}\n"
            
            pdf_document.close()
            
            if full_text.strip():
                logger.info(f"✅ PyMuPDF extraiu {len(full_text)} caracteres de {page_count} páginas")
                
                return {
                    'success': True,
                    'text': full_text.strip(),
                    'page_count': page_count,
                    'metadata': {
                        'engine': 'pymupdf',
                        'pages_processed': page_count
                    }
                }
            else:
                return {'success': False, 'error': 'PyMuPDF retornou texto vazio'}
                
        except Exception as e:
            logger.error(f"❌ Erro PyMuPDF: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extrai texto usando PyPDF2 (último recurso)"""
        try:
            pdf_file = io.BytesIO(pdf_content)
            reader = PyPDF2.PdfReader(pdf_file)
            
            full_text = ""
            page_count = len(reader.pages)
            
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                full_text += f"\n--- PÁGINA {i + 1} ---\n{text}\n"
            
            if full_text.strip():
                logger.info(f"✅ PyPDF2 extraiu {len(full_text)} caracteres de {page_count} páginas")
                
                return {
                    'success': True,
                    'text': full_text.strip(),
                    'page_count': page_count,
                    'metadata': {
                        'engine': 'pypdf2',
                        'pages_processed': page_count
                    }
                }
            else:
                return {'success': False, 'error': 'PyPDF2 retornou texto vazio'}
                
        except Exception as e:
            logger.error(f"❌ Erro PyPDF2: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_extractor_status(self) -> Dict[str, Any]:
        """Retorna status dos extractors"""
        status = {
            'available_extractors': [],
            'unavailable_extractors': [],
            'primary_extractor': None,
            'total_available': 0
        }
        
        for name, config in self.extractors.items():
            if config['available']:
                status['available_extractors'].append({
                    'name': name,
                    'priority': config['priority'],
                    'initialized': config['instance'] is not None
                })
            else:
                status['unavailable_extractors'].append(name)
        
        # Ordenar por prioridade
        status['available_extractors'].sort(key=lambda x: x['priority'])
        status['total_available'] = len(status['available_extractors'])
        
        if status['available_extractors']:
            status['primary_extractor'] = status['available_extractors'][0]['name']
        
        return status
    
    def extract_text_preview(self, pdf_content: bytes, max_chars: int = 1000) -> str:
        """Extrai preview do texto usando o melhor extractor disponível"""
        result = self.extract_text_from_bytes(pdf_content)
        
        if result['success'] and result['text']:
            preview = result['text'][:max_chars]
            if len(result['text']) > max_chars:
                preview += "..."
            return preview
        
        return ""
    
    def cleanup_temp_files(self):
        """Limpa arquivos temporários antigos"""
        try:
            current_time = time.time()
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    # Arquivos mais velhos que 1 hora
                    if current_time - temp_file.stat().st_mtime > 3600:
                        temp_file.unlink()
                        logger.debug(f"🗑️ Arquivo temporário removido: {temp_file.name}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar arquivos temporários: {e}") 