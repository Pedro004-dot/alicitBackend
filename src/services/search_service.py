"""
Search Service
Lógica de negócio para busca unificada (Local + PNCP)
Reutiliza services existentes para manter DRY
"""
import logging
import time
from typing import Dict, Any, List, Optional
from services.bid_service import BidService
from services.pncp_search_service import PNCPSearchService
from repositories.bid_repository import BidRepository
from config.database import db_manager

logger = logging.getLogger(__name__)

class SearchService:
    """
    Service para busca unificada
    PADRONIZADO: Usa services/repositories existentes
    """
    
    def __init__(self):
        self.bid_service = BidService()
        self.pncp_service = PNCPSearchService()
        self.bid_repository = BidRepository(db_manager)
    
    def perform_unified_search(
        self, 
        keywords: str, 
        search_pncp: bool = True,
        filters: Optional[Dict] = None,
        pncp_options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Executa busca unificada combinando local e PNCP
        
        Args:
            keywords: Palavras-chave para busca
            search_pncp: Se deve buscar também no PNCP
            filters: Filtros para aplicar (UF, valor, etc.)
            pncp_options: Opções específicas para busca PNCP
        """
        try:
            start_time = time.time()
            filters = filters or {}
            pncp_options = pncp_options or {}
            
            # 1. Busca local (sempre executa)
            logger.info(f"🔍 Executando busca local para: {keywords}")
            local_results = self._perform_local_search(keywords, filters)
            
            # 2. Busca PNCP (se solicitado)
            pncp_results = []
            pncp_metadata = {}
            
            if search_pncp:
                logger.info(f"🌐 Executando busca PNCP para: {keywords}")
                pncp_results, pncp_metadata = self._perform_pncp_search(keywords, filters, pncp_options)
            
            # 3. Combinar resultados
            combined_results = self._combine_results(local_results, pncp_results)
            
            # 4. Calcular estatísticas
            end_time = time.time()
            search_time_ms = int((end_time - start_time) * 1000)
            
            return {
                'success': True,
                'data': {
                    'local_results': local_results,
                    'pncp_results': pncp_results,
                    'combined_results': combined_results,
                    'summary': {
                        'total_local': len(local_results),
                        'total_pncp': len(pncp_results),
                        'total_combined': len(combined_results),
                        'search_time_ms': search_time_ms,
                        'searched_pncp': search_pncp
                    },
                    'metadata': {
                        'local_metadata': {},
                        'pncp_metadata': pncp_metadata
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na busca unificada: {e}")
            return {
                'success': False,
                'message': f'Erro na busca: {str(e)}'
            }
    
    def _perform_local_search(self, keywords: str, filters: Dict) -> List[Dict]:
        """Executa busca no banco local"""
        try:
            # Usar o repository para busca por palavras-chave
            results = self.bid_repository.search_by_keywords(keywords, filters)
            
            # Adicionar marcador de origem
            formatted_results = []
            for bid in results:
                bid_data = dict(bid) if hasattr(bid, '__dict__') else dict(bid)
                bid_data['source'] = 'local'
                bid_data['source_label'] = 'Banco Local'
                formatted_results.append(bid_data)
            
            logger.info(f"✅ Busca local: {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erro na busca local: {e}")
            return []
    
    def _perform_pncp_search(self, keywords: str, filters: Dict, options: Dict) -> tuple[List[Dict], Dict]:
        """Executa busca na API PNCP"""
        try:
            # Preparar filtros PNCP no formato correto
            pncp_filters = {}
            
            if filters:
                if filters.get('uf'):
                    pncp_filters['uf'] = filters['uf']
                
                if filters.get('valor_min'):
                    pncp_filters['valor_min'] = str(filters['valor_min'])
                
                if filters.get('valor_max'):
                    pncp_filters['valor_max'] = str(filters['valor_max'])
                
                if filters.get('modalidades') and filters['modalidades'] != ['todas']:
                    pncp_filters['modalidades'] = filters['modalidades']
            
            # Executar busca usando o método correto do service existente
            results, metadata = self.pncp_service.search_by_keywords_advanced(
                keywords=keywords,
                filtros=pncp_filters,
                max_pages=options.get('max_pages', 3),
                include_items=options.get('include_items', True),
                save_results=options.get('save_results', True)
            )
            
            # Adicionar marcador de origem
            for bid in results:
                bid['source'] = 'pncp'
                bid['source_label'] = 'PNCP'
            
            logger.info(f"✅ Busca PNCP: {len(results)} resultados")
            return results, metadata
                
        except Exception as e:
            logger.error(f"Erro na busca PNCP: {e}")
            return [], {}
    
    def _combine_results(self, local_results: List[Dict], pncp_results: List[Dict]) -> List[Dict]:
        """Combina resultados evitando duplicatas"""
        combined = []
        
        # Adicionar resultados locais
        combined.extend(local_results)
        
        # Adicionar resultados PNCP, evitando duplicatas por pncp_id
        existing_pncp_ids = {r.get('pncp_id') for r in combined if r.get('pncp_id')}
        
        for bid in pncp_results:
            pncp_id = bid.get('pncp_id')
            if pncp_id and pncp_id not in existing_pncp_ids:
                combined.append(bid)
                existing_pncp_ids.add(pncp_id)
        
        # Ordenar por relevância: 1) local primeiro, 2) score PNCP, 3) data recente
        def sort_key(item):
            source_priority = 0 if item.get('source') == 'local' else 1
            score = item.get('total_score', 0)  # Score PNCP
            return (source_priority, -score)
        
        combined.sort(key=sort_key)
        
        logger.info(f"🔄 Resultados combinados: {len(combined)} total")
        return combined
    
    def get_search_suggestions(self) -> Dict[str, Any]:
        """Gera sugestões de busca baseadas em dados existentes"""
        try:
            # Buscar palavras-chave mais comuns em objetos de licitação
            common_keywords = self.bid_repository.get_common_keywords(limit=20)
            
            # Categorizar sugestões
            suggestions = {
                'populares': common_keywords[:10],
                'tecnologia': [
                    'computadores', 'notebooks', 'softwares', 'sistemas',
                    'equipamentos informática', 'servidores', 'licenças'
                ],
                'servicos': [
                    'consultoria', 'treinamento', 'suporte técnico',
                    'manutenção', 'desenvolvimento', 'segurança'
                ],
                'materiais': [
                    'móveis', 'veículos', 'equipamentos', 'materiais construção',
                    'medicamentos', 'alimentação', 'combustível'
                ]
            }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erro ao gerar sugestões: {e}")
            return {
                'populares': [],
                'tecnologia': ['computadores', 'softwares'],
                'servicos': ['consultoria', 'treinamento'],
                'materiais': ['equipamentos', 'veículos']
            } 