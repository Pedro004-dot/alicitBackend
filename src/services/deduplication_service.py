# src/services/deduplication_service.py
import hashlib
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class DeduplicationService:
    """Serviço para evitar processamento duplicado"""
    
    def __init__(self, db_manager, cache_service):
        self.db_manager = db_manager
        self.cache_service = cache_service
    
    def should_process_licitacao(self, licitacao_id: str, licitacao_data: Dict[str, Any]) -> bool:
        """Verifica se licitação deve ser processada"""
        # Criar hash dos dados importantes da licitação
        process_data = {
            'objeto_compra': licitacao_data.get('objeto_compra', ''),
            'pncp_id': licitacao_data.get('pncp_id', ''),
            'data_publicacao': str(licitacao_data.get('data_publicacao', '')),
            'process_type': 'matching'
        }
        
        return not self.cache_service.is_resource_processed('licitacao', licitacao_id, process_data)
    
    def mark_licitacao_processed(self, licitacao_id: str, licitacao_data: Dict[str, Any]):
        """Marca licitação como processada"""
        process_data = {
            'objeto_compra': licitacao_data.get('objeto_compra', ''),
            'pncp_id': licitacao_data.get('pncp_id', ''),
            'data_publicacao': str(licitacao_data.get('data_publicacao', '')),
            'process_type': 'matching'
        }
        
        self.cache_service.mark_resource_processed('licitacao', licitacao_id, process_data)
    
    def should_process_rag_document(self, documento_id: str, documento_data: Dict[str, Any]) -> bool:
        """Verifica se documento RAG deve ser processado"""
        process_data = {
            'arquivo_url': documento_data.get('arquivo_nuvem_url', ''),
            'tamanho_arquivo': documento_data.get('tamanho_arquivo', 0),
            'hash_arquivo': documento_data.get('hash_arquivo', ''),
            'process_type': 'rag_vectorization'
        }
        
        return not self.cache_service.is_resource_processed('documento', documento_id, process_data)
    
    def mark_rag_document_processed(self, documento_id: str, documento_data: Dict[str, Any]):
        """Marca documento RAG como processado"""
        process_data = {
            'arquivo_url': documento_data.get('arquivo_nuvem_url', ''),
            'tamanho_arquivo': documento_data.get('tamanho_arquivo', 0),
            'hash_arquivo': documento_data.get('hash_arquivo', ''),
            'process_type': 'rag_vectorization'
        }
        
        self.cache_service.mark_resource_processed('documento', documento_id, process_data)