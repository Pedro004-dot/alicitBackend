"""
Módulo core - Funcionalidades centrais do sistema

Este módulo contém as classes e funções fundamentais para processamento
de documentos, incluindo extração de texto, análise de conteúdo e
manipulação de arquivos.
"""

from .unified_document_processor import UnifiedDocumentProcessor

# Mantém compatibilidade com código antigo
DocumentProcessor = UnifiedDocumentProcessor
CloudDocumentProcessor = UnifiedDocumentProcessor

__all__ = ['UnifiedDocumentProcessor', 'DocumentProcessor', 'CloudDocumentProcessor'] 