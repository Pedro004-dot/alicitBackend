"""
Match Service
Lógica de negócio para operações com matches
Usa repository padronizado para acesso a dados
"""
import logging
from typing import List, Dict, Any, Optional
from repositories.match_repository import MatchRepository
from config.database import db_manager

logger = logging.getLogger(__name__)

class MatchService:
    """
    Service para lógica de negócio de matches
    PADRONIZADO: Usa MatchRepository para acesso a dados
    """
    
    def __init__(self):
        self.match_repo = MatchRepository(db_manager)
    
    def get_all_matches(self, limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obter todos os matches com formatação para frontend
        Se user_id for fornecido, filtra apenas matches das empresas do usuário
        """
        try:
            if user_id:
                matches = self.match_repo.find_matches_with_details(limit=limit, user_id=user_id)
            else:
                matches = self.match_repo.find_matches_with_details(limit=limit)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches: {e}")
            return []
    
    def get_match_by_id(self, match_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Buscar match por ID com formatação, validando propriedade se user_id fornecido"""
        try:
            if user_id:
                match = self.match_repo.find_by_id_and_user(match_id, user_id)
            else:
                match = self.match_repo.find_by_id(match_id)
                
            if match:
                return self._format_match_for_frontend(match)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar match {match_id}: {e}")
            return None
    
    def get_matches_by_company(self, company_id: str, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obter matches de uma empresa específica com detalhes
        Se user_id fornecido, valida se a empresa pertence ao usuário
        """
        try:
            matches = self.match_repo.find_matches_by_company_with_details(company_id, limit, user_id=user_id)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches da empresa {company_id}: {e}")
            return []
    
    def get_matches_by_licitacao(self, licitacao_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obter matches de uma licitação específica com detalhes
        """
        try:
            matches = self.match_repo.find_matches_by_licitacao_with_details(licitacao_id, limit)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches da licitação {licitacao_id}: {e}")
            return []
    
    def get_high_score_matches(self, min_score: float = 0.8, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Buscar matches com score alto
        Se user_id fornecido, filtra apenas matches das empresas do usuário
        """
        try:
            matches = self.match_repo.find_high_score_matches(min_score, limit, user_id=user_id)
            return self._format_matches_for_frontend(matches)
        except Exception as e:
            logger.error(f"Erro ao buscar matches com score alto: {e}")
            return []
    
    def create_match(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Criar novo match com validação de negócio
        """
        try:
            # Validações de negócio
            self._validate_match_data(match_data)
            
            # Verificar se match já existe
            existing = self.match_repo.find_potential_matches(
                match_data['empresa_id'], 
                match_data['licitacao_id']
            )
            
            if existing:
                return {
                    'success': False,
                    'message': 'Match já existe entre esta empresa e licitação',
                    'data': None
                }
            
            # Criar match
            created_match = self.match_repo.create(match_data)
            
            logger.info(f"Match criado: {created_match['id']}")
            
            return {
                'success': True,
                'message': 'Match criado com sucesso',
                'data': self._format_match_for_frontend(created_match)
            }
            
        except ValueError as e:
            logger.warning(f"Erro de validação ao criar match: {e}")
            return {
                'success': False,
                'message': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Erro ao criar match: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def update_match(self, match_id: str, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualizar match existente com validação
        """
        try:
            # Verificar se match existe
            if not self.match_repo.exists(match_id):
                return {
                    'success': False,
                    'message': 'Match não encontrado',
                    'data': None
                }
            
            # Validar score se fornecido
            if 'score_similaridade' in match_data:
                score = match_data['score_similaridade']
                if not isinstance(score, (int, float)) or score < 0 or score > 1:
                    return {
                        'success': False,
                        'message': 'Score deve ser um número entre 0 e 1',
                        'data': None
                    }
            
            # Atualizar match
            updated_match = self.match_repo.update(match_id, match_data)
            
            if updated_match:
                logger.info(f"Match atualizado: {match_id}")
                return {
                    'success': True,
                    'message': 'Match atualizado com sucesso',
                    'data': self._format_match_for_frontend(updated_match)
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao atualizar match',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao atualizar match {match_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def delete_match(self, match_id: str) -> Dict[str, Any]:
        """
        Deletar match
        """
        try:
            # Verificar se match existe
            match = self.match_repo.find_by_id(match_id)
            if not match:
                return {
                    'success': False,
                    'message': 'Match não encontrado',
                    'data': None
                }
            
            # Deletar match
            success = self.match_repo.delete(match_id)
            
            if success:
                logger.info(f"Match deletado: {match_id}")
                return {
                    'success': True,
                    'message': 'Match deletado com sucesso',
                    'data': None
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao deletar match',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao deletar match {match_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def get_matches_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas completas dos matches"""
        try:
            return self.match_repo.get_matches_statistics()
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de matches: {e}")
            return {}
    
    def get_companies_with_matches_summary(self) -> List[Dict[str, Any]]:
        """Buscar empresas com resumo de matches"""
        try:
            return self.match_repo.get_companies_with_matches_summary()
        except Exception as e:
            logger.error(f"Erro ao buscar resumo de empresas com matches: {e}")
            return []
    
    def find_duplicate_matches(self) -> List[Dict[str, Any]]:
        """Identificar matches duplicados"""
        try:
            return self.match_repo.find_duplicate_matches()
        except Exception as e:
            logger.error(f"Erro ao buscar matches duplicados: {e}")
            return []
    
    def bulk_create_matches(self, matches_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Criar múltiplos matches em lote com validação
        """
        try:
            # Validar todos os matches antes de inserir
            validated_matches = []
            errors = []
            
            for i, match_data in enumerate(matches_data):
                try:
                    self._validate_match_data(match_data)
                    validated_matches.append(match_data)
                except Exception as e:
                    errors.append(f"Match {i+1}: {str(e)}")
            
            if errors:
                return {
                    'success': False,
                    'message': 'Erros de validação encontrados',
                    'data': {'errors': errors}
                }
            
            # Inserir matches em lote
            created_ids = self.match_repo.bulk_create_matches(validated_matches)
            
            logger.info(f"Importação em lote: {len(created_ids)} matches criados")
            
            return {
                'success': True,
                'message': f'{len(created_ids)} matches criados com sucesso',
                'data': {
                    'total_created': len(created_ids),
                    'match_ids': created_ids
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na criação em lote de matches: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def search_matches(self, search_filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Buscar matches com filtros avançados
        """
        try:
            # Processar filtros de score
            if 'min_score' in search_filters and 'max_score' in search_filters:
                matches = self.match_repo.find_by_score_range(
                    search_filters['min_score'],
                    search_filters['max_score'],
                    limit
                )
            elif 'min_score' in search_filters:
                matches = self.match_repo.find_high_score_matches(
                    search_filters['min_score'],
                    limit
                )
            else:
                # Usar filtros simples
                matches = self.match_repo.find_by_filters(search_filters, limit)
            
            return self._format_matches_for_frontend(matches)
            
        except Exception as e:
            logger.error(f"Erro ao buscar matches com filtros: {e}")
            return []
    
    def _validate_match_data(self, data: Dict[str, Any]):
        """Validações de negócio para dados de match"""
        required_fields = ['empresa_id', 'licitacao_id', 'score_similaridade']
        
        for field in required_fields:
            if not data.get(field):
                raise ValueError(f'Campo obrigatório ausente: {field}')
        
        # Validar score
        score = data.get('score_similaridade')
        if not isinstance(score, (int, float)) or score < 0 or score > 1:
            raise ValueError('Score de similaridade deve ser um número entre 0 e 1')
    
    def _format_match_for_frontend(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """Formatar match individual para frontend"""
        return {
            'id': str(match['id']),
            'empresa_id': str(match['empresa_id']),
            'licitacao_id': str(match['licitacao_id']),
            'score_similaridade': float(match.get('score_similaridade', 0)),
            'criterios_match': match.get('criterios_match', {}),
            'keywords_match': match.get('keywords_match', []),
            'created_at': match.get('created_at').isoformat() if match.get('created_at') else None,
            'updated_at': match.get('updated_at').isoformat() if match.get('updated_at') else None,
            # Campos extras se vierem do join
            'empresa_nome': match.get('nome_fantasia'),
            'empresa_cnpj': match.get('cnpj'),
            'licitacao_objeto': match.get('objeto_compra'),
            'licitacao_valor': float(match.get('valor_total_estimado', 0)) if match.get('valor_total_estimado') else None,
            'licitacao_uf': match.get('uf'),
            'licitacao_modalidade': match.get('modalidade_nome')
        }
    
    def _format_matches_for_frontend(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formatar lista de matches para frontend"""
        return [self._format_match_for_frontend(match) for match in matches]
    
    def reevaluate_recent_matches_with_llm(self, days_back: int = 7, limit: int = 10, update_existing: bool = False) -> Dict[str, Any]:
        """
        Reavaliar matches recentes com validação LLM
        
        Args:
            days_back: Quantos dias atrás buscar matches
            limit: Limite de matches para processar
            update_existing: Se True, atualiza matches existentes; se False, apenas valida
        """
        try:
            from config.llm_config import LLMConfig
            from matching.pncp_api import get_db_connection
            from datetime import datetime, timedelta
            import logging
            
            logger.info(f"🤖 Iniciando reavaliação LLM dos últimos {days_back} dias")
            
            # Inicializar validador LLM
            llm_validator = LLMConfig.create_validator()
            
            # Buscar matches recentes com dados completos
            matches_with_details = self.match_repo.find_recent_matches_with_full_details(limit, days_back)
            
            if not matches_with_details:
                return {
                    'matches': [],
                    'llm_validated_count': 0,
                    'llm_approved_count': 0,
                    'llm_rejected_count': 0,
                    'updated_matches': 0,
                    'message': f'Nenhum match encontrado nos últimos {days_back} dias'
                }
            
            validated_matches = []
            llm_validated_count = 0
            llm_approved_count = 0
            llm_rejected_count = 0
            updated_matches = 0
            
            logger.info(f"📊 Processando {len(matches_with_details)} matches com LLM...")
            
            for match in matches_with_details:
                try:
                    # Dados necessários para validação LLM
                    empresa_nome = match.get('empresa_nome', '')
                    empresa_descricao = match.get('empresa_descricao', '')
                    empresa_produtos = match.get('empresa_produtos', '')
                    licitacao_objeto = match.get('licitacao_objeto', '')
                    pncp_id = match.get('licitacao_pncp_id', '')
                    current_score = float(match.get('score_similaridade', 0))
                    
                    # Buscar itens da licitação se disponível
                    licitacao_itens = []
                    if match.get('licitacao_id'):
                        from matching.pncp_api import get_bid_items_from_db
                        licitacao_itens = get_bid_items_from_db(match['licitacao_id'])
                    
                    # Executar validação LLM
                    validation = llm_validator.validate_match(
                        empresa_nome=empresa_nome,
                        empresa_descricao=empresa_descricao,
                        empresa_produtos=empresa_produtos,
                        licitacao_objeto=licitacao_objeto,
                        pncp_id=pncp_id,
                        similarity_score=current_score,
                        licitacao_itens=licitacao_itens
                    )
                    
                    llm_validated_count += 1
                    
                    # Adicionar informações de validação LLM ao match
                    match_with_llm = match.copy()
                    match_with_llm['llm_validation'] = {
                        'is_valid': validation['is_valid'],
                        'confidence': validation['confidence'],
                        'reasoning': validation['reasoning'],
                        'original_score': current_score,
                        'validated_at': datetime.now().isoformat()
                    }
                    
                    if validation['is_valid']:
                        llm_approved_count += 1
                        match_with_llm['llm_status'] = 'approved'
                        
                        # Atualizar match existente se solicitado
                        if update_existing and validation['confidence'] != current_score:
                            self.match_repo.update_score(match['match_id'], validation['confidence'])
                            updated_matches += 1
                            match_with_llm['score_similaridade'] = validation['confidence']
                            match_with_llm['updated'] = True
                            
                    else:
                        llm_rejected_count += 1
                        match_with_llm['llm_status'] = 'rejected'
                        
                        # Log do match rejeitado
                        logger.warning(f"🚫 Match rejeitado pelo LLM: {empresa_nome} x {licitacao_objeto[:50]}...")
                    
                    validated_matches.append(match_with_llm)
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao validar match {match.get('match_id', 'unknown')}: {e}")
                    # Adicionar match sem validação LLM em caso de erro
                    match_with_error = match.copy()
                    match_with_error['llm_validation'] = {
                        'error': str(e),
                        'is_valid': None,
                        'validated_at': datetime.now().isoformat()
                    }
                    validated_matches.append(match_with_error)
            
            # Ordenar por score LLM (se disponível) ou score original
            validated_matches.sort(
                key=lambda x: x.get('llm_validation', {}).get('confidence', x.get('score_similaridade', 0)),
                reverse=True
            )
            
            logger.info(f"✅ Reavaliação LLM concluída:")
            logger.info(f"   📊 Total validado: {llm_validated_count}")
            logger.info(f"   ✅ Aprovados: {llm_approved_count}")
            logger.info(f"   ❌ Rejeitados: {llm_rejected_count}")
            if update_existing:
                logger.info(f"   🔄 Atualizados: {updated_matches}")
            
            return {
                'matches': validated_matches,
                'llm_validated_count': llm_validated_count,
                'llm_approved_count': llm_approved_count,
                'llm_rejected_count': llm_rejected_count,
                'updated_matches': updated_matches,
                'period_days': days_back,
                'approval_rate': round((llm_approved_count / llm_validated_count * 100), 1) if llm_validated_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na reavaliação LLM de matches recentes: {e}")
            return {
                'matches': [],
                'llm_validated_count': 0,
                'llm_approved_count': 0,
                'llm_rejected_count': 0,
                'updated_matches': 0,
                'error': str(e)
            }
    
    def reevaluate_bids_by_date(self, target_date: str, enable_llm: bool = True, limit: int = 50) -> Dict[str, Any]:
        """
        Reavaliar licitações de uma data específica contra todas as empresas
        
        Args:
            target_date: Data no formato YYYY-MM-DD
            enable_llm: Se True, usa validação LLM para os matches
            limit: Limite de licitações para processar
        """
        try:
            from config.llm_config import LLMConfig
            from matching.pncp_api import get_db_connection, get_all_companies_from_db, save_match_to_db, get_bid_items_from_db
            from matching.vectorizers import BrazilianTextVectorizer
            from matching.vectorizers import calculate_enhanced_similarity
            from services.embedding_cache_service import EmbeddingCacheService
            from config.database import db_manager
            from datetime import datetime
            import logging
            
            logger.info(f"🤖 Iniciando reavaliação de licitações da data {target_date}")
            
            # Validar formato da data
            try:
                datetime.strptime(target_date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Data deve estar no formato YYYY-MM-DD")
            
            # Buscar licitações da data específica
            licitacoes_query = """
                SELECT 
                    l.id,
                    l.pncp_id,
                    l.objeto_compra,
                    l.valor_total_estimado,
                    l.uf,
                    l.created_at,
                    l.modalidade_nome,
                    l.razao_social as orgao_nome
                FROM licitacoes l
                WHERE DATE(l.created_at) = %s
                ORDER BY l.created_at DESC
                LIMIT %s
            """
            
            with db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(licitacoes_query, (target_date, limit))
                    licitacoes = [dict(row) for row in cursor.fetchall()]
            
            if not licitacoes:
                return {
                    'matches': [],
                    'total_bids_found': 0,
                    'total_bids_processed': 0,
                    'llm_validated_count': 0,
                    'llm_approved_count': 0,
                    'llm_rejected_count': 0,
                    'message': f'Nenhuma licitação encontrada para a data {target_date}'
                }
            
            logger.info(f"📊 Encontradas {len(licitacoes)} licitações para a data {target_date}")
            
            # Buscar empresas
            companies = get_all_companies_from_db()
            if not companies:
                raise ValueError("Nenhuma empresa encontrada no sistema")
            
            logger.info(f"🏢 Carregadas {len(companies)} empresas para matching")
            
            # Inicializar vectorizer e cache
            vectorizer = BrazilianTextVectorizer()
            cache_service = EmbeddingCacheService(db_manager)
            
            # Vetorizar empresas com cache
            self._vectorize_companies_with_cache(companies, cache_service, vectorizer)
            
            # Inicializar validador LLM se habilitado
            llm_validator = None
            if enable_llm:
                llm_validator = LLMConfig.create_validator()
                logger.info(f"🤖 Validador LLM configurado")
            
            # Processar licitações
            all_matches = []
            llm_validated_count = 0
            llm_approved_count = 0
            llm_rejected_count = 0
            processed_count = 0
            
            SIMILARITY_THRESHOLD = 0.65  # Threshold para matching inicial
            
            for i, licitacao in enumerate(licitacoes, 1):
                logger.info(f"[{i}/{len(licitacoes)}] 🔍 Processando licitação: {licitacao['pncp_id']}")
                
                objeto_compra = licitacao.get('objeto_compra', '')
                if not objeto_compra:
                    continue
                
                processed_count += 1
                
                # Vetorizar objeto da licitação
                bid_embedding = None
                if objeto_compra in cache_service.batch_get_embeddings_from_cache([objeto_compra]):
                    bid_embedding = cache_service.batch_get_embeddings_from_cache([objeto_compra])[objeto_compra]
                else:
                    bid_embedding = vectorizer.vectorize(objeto_compra)
                    if bid_embedding:
                        cache_service.save_embedding_to_cache(objeto_compra, bid_embedding)
                
                if not bid_embedding:
                    logger.warning(f"❌ Erro ao vetorizar licitação {licitacao['pncp_id']}")
                    continue
                
                # Buscar itens da licitação
                licitacao_itens = get_bid_items_from_db(licitacao['id'])
                
                # Calcular similaridade com todas as empresas
                for company in companies:
                    if not company.get("embedding"):
                        continue
                    
                    score, justificativa = calculate_enhanced_similarity(
                        bid_embedding,
                        company["embedding"],
                        objeto_compra,
                        company["descricao_servicos_produtos"]
                    )
                    
                    if score >= SIMILARITY_THRESHOLD:
                        should_accept_match = False
                        final_score = score
                        final_justificativa = justificativa
                        
                        if llm_validator:
                            # Validação LLM
                            validation = llm_validator.validate_match(
                                empresa_nome=company['nome'],
                                empresa_descricao=company['descricao_servicos_produtos'],
                                empresa_produtos=company.get('produtos'),
                                licitacao_objeto=objeto_compra,
                                pncp_id=licitacao['pncp_id'],
                                similarity_score=score,
                                licitacao_itens=licitacao_itens
                            )
                            
                            llm_validated_count += 1
                            
                            if validation['is_valid']:
                                llm_approved_count += 1
                                should_accept_match = True
                                final_score = validation['confidence']
                                final_justificativa += f" | LLM: {validation['reasoning'][:100]}..."
                            else:
                                llm_rejected_count += 1
                                should_accept_match = False
                        else:
                            # Sem LLM, usar threshold mais alto
                            should_accept_match = score >= 0.85
                        
                        if should_accept_match:
                            # Salvar match no banco
                            save_match_to_db(
                                licitacao['pncp_id'], 
                                company["id"], 
                                final_score, 
                                "llm_approved" if llm_validator else "objeto_completo",
                                final_justificativa
                            )
                            
                            # Adicionar ao resultado
                            match_data = {
                                'licitacao': {
                                    'id': licitacao['id'],
                                    'pncp_id': licitacao['pncp_id'],
                                    'objeto_compra': objeto_compra,
                                    'valor_total_estimado': licitacao.get('valor_total_estimado'),
                                    'uf': licitacao.get('uf'),
                                    'orgao_nome': licitacao.get('orgao_nome')
                                },
                                'empresa': {
                                    'id': company['id'],
                                    'nome': company['nome'],
                                    'cnpj': company.get('cnpj'),
                                    'descricao': company['descricao_servicos_produtos']
                                },
                                'match_info': {
                                    'score': final_score,
                                    'justificativa': final_justificativa,
                                    'llm_validated': llm_validator is not None
                                }
                            }
                            all_matches.append(match_data)
                            
                            logger.info(f"✅ Match salvo: {company['nome']} x {licitacao['pncp_id']} (Score: {final_score:.3f})")
            
            # Ordenar matches por score
            all_matches.sort(key=lambda x: x['match_info']['score'], reverse=True)
            
            logger.info(f"✅ Processamento concluído:")
            logger.info(f"   📊 Licitações processadas: {processed_count}")
            logger.info(f"   🎯 Matches encontrados: {len(all_matches)}")
            if enable_llm:
                logger.info(f"   🤖 LLM validações: {llm_validated_count}")
                logger.info(f"   ✅ LLM aprovados: {llm_approved_count}")
                logger.info(f"   ❌ LLM rejeitados: {llm_rejected_count}")
            
            return {
                'matches': all_matches,
                'total_bids_found': len(licitacoes),
                'total_bids_processed': processed_count,
                'llm_validated_count': llm_validated_count,
                'llm_approved_count': llm_approved_count,
                'llm_rejected_count': llm_rejected_count,
                'target_date': target_date,
                'approval_rate': round((llm_approved_count / llm_validated_count * 100), 1) if llm_validated_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na reavaliação de licitações por data: {e}")
            return {
                'matches': [],
                'total_bids_found': 0,
                'total_bids_processed': 0,
                'llm_validated_count': 0,
                'llm_approved_count': 0,
                'llm_rejected_count': 0,
                'error': str(e)
            }
    
    def _vectorize_companies_with_cache(self, companies, cache_service, vectorizer):
        """Vetorizar empresas usando cache Redis"""
        company_texts = [company["descricao_servicos_produtos"] for company in companies]
        
        # Buscar embeddings em lote do Redis
        cached_embeddings = cache_service.batch_get_embeddings_from_cache(company_texts)
        
        # Processar empresas que não estão no cache
        texts_to_generate = []
        companies_to_update = []
        
        for company in companies:
            texto_empresa = company["descricao_servicos_produtos"]
            
            if texto_empresa in cached_embeddings:
                company["embedding"] = cached_embeddings[texto_empresa]
            else:
                texts_to_generate.append(texto_empresa)
                companies_to_update.append(company)
        
        # Gerar embeddings faltantes
        if texts_to_generate:
            new_embeddings = vectorizer.batch_vectorize(texts_to_generate)
            
            if new_embeddings:
                # Salvar novos embeddings no cache
                texts_and_embeddings = list(zip(texts_to_generate, new_embeddings))
                cache_service.batch_save_embeddings_to_cache(texts_and_embeddings)
                
                # Atribuir aos objetos empresa
                for i, company in enumerate(companies_to_update):
                    if i < len(new_embeddings):
                        company["embedding"] = new_embeddings[i] 