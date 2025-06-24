"""
Repository para Licitações (Bids)
Migração das operações de licitação do api.py para camada de dados dedicada
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from psycopg2.extras import DictCursor
from .base_repository import BaseRepository
from datetime import datetime

logger = logging.getLogger(__name__)

class BidRepository(BaseRepository):
    """Repository para operações com licitações"""
    
    @property
    def table_name(self) -> str:
        return "licitacoes"
    
    @property 
    def primary_key(self) -> str:
        return "id"
    
    def find_all_formatted(self) -> List[Dict[str, Any]]:
        """
        Buscar todas as licitações formatadas para o frontend
        Migração do endpoint GET /api/bids do api.py linha 77-101
        """
        bids = self.find_all()
        
        formatted_bids = []
        for bid in bids:
            formatted_bids.append({
                'id': bid['id'],
                'pncp_id': bid['pncp_id'],
                'objeto_compra': bid['objeto_compra'],
                'valor_total_estimado': float(bid.get('valor_total_estimado', 0)) if bid.get('valor_total_estimado') else 0,
                'uf': bid.get('uf', ''),
                'status': bid.get('status', ''),
                'data_publicacao': bid.get('data_publicacao', ''),
                'modalidade_compra': 'Pregão Eletrônico'  # Valor padrão pois não está no BD
            })
        
        return formatted_bids
    
    def find_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar licitação por pncp_id
        Migração dos endpoints de busca específica do api.py
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(
                    "SELECT * FROM licitacoes WHERE pncp_id = %s",
                    (pncp_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                # Converter para dict e formatar dados
                bid_dict = dict(row)
                return self._format_for_json(bid_dict)
    
    def get_by_pncp_id(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma licitação pelo ID PNCP
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, pncp_id, status, created_at, updated_at
                        FROM licitacoes 
                        WHERE pncp_id = %s
                    """, (pncp_id,))
                    
                    result = cursor.fetchone()
                    if result:
                        return dict(result)
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Erro ao buscar licitação {pncp_id}: {e}")
            return None
    
    def find_by_pncp_id_with_items(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """
        Buscar licitação com seus itens incluídos
        Migração do endpoint GET /api/bids/<pncp_id> do api.py linha 1040-1100
        """
        bid = self.find_by_pncp_id(pncp_id)
        
        if not bid:
            return None
        
        # Buscar itens da licitação
        items = self.find_items_by_bid_id(bid['id'])
        bid['itens'] = items
        bid['possui_itens'] = len(items) > 0
        
        return bid
    
    def find_items_by_pncp_id(self, pncp_id: str) -> List[Dict[str, Any]]:
        """
        Buscar itens de uma licitação pelo pncp_id
        Migração dos endpoints GET /api/bids/<pncp_id>/items e /api/bids/items
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Primeiro, buscar o ID da licitação pelo pncp_id
                cursor.execute("SELECT id FROM licitacoes WHERE pncp_id = %s", (pncp_id,))
                bid = cursor.fetchone()
                
                if not bid:
                    return []
                
                return self.find_items_by_bid_id(bid['id'])
    
    def find_items_by_bid_id(self, bid_id: str) -> List[Dict[str, Any]]:
        """
        Buscar itens de uma licitação pelo ID interno
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM licitacao_itens 
                    WHERE licitacao_id = %s 
                    ORDER BY numero_item
                """, (bid_id,))
                
                items = cursor.fetchall()
                items_list = []
                
                # Converter e formatar dados
                for item in items:
                    item_dict = dict(item)
                    items_list.append(self._format_for_json(item_dict))
                
                return items_list
    
    def get_bid_items(self, pncp_id: str) -> List[Dict[str, Any]]:
        """
        Alias para find_items_by_pncp_id para compatibilidade com PNCPController
        """
        return self.find_items_by_pncp_id(pncp_id)
    
    def find_detailed_with_pagination(self, page: int = 1, per_page: int = 20, 
                                    filters: Dict[str, Any] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Buscar licitações com informações detalhadas e paginação
        Migração do endpoint GET /api/bids/detailed do api.py linha 1276-1355
        """
        # Construir filtros
        where_conditions = []
        params = []
        
        if filters:
            if filters.get('uf'):
                where_conditions.append("uf = %s")
                params.append(filters['uf'])
            
            if filters.get('modalidade_id'):
                where_conditions.append("modalidade_id = %s")
                params.append(int(filters['modalidade_id']))
            
            if filters.get('status'):
                where_conditions.append("status = %s")
                params.append(filters['status'])
        
        where_clause = ""
        if where_conditions:
            where_clause = " AND ".join(where_conditions)
        
        # Usar método de paginação da classe base
        order_by = "data_publicacao DESC, created_at DESC"
        records, pagination_meta = self.find_with_pagination(
            page=page,
            per_page=per_page,
            where_clause=where_clause,
            params=params,
            order_by=order_by
        )
        
        # Formatar registros para JSON
        formatted_records = [self._format_for_json(record) for record in records]
        
        return formatted_records, pagination_meta
    
    def count_all(self) -> int:
        """Contar total de licitações"""
        return self.count()
    
    def find_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Buscar licitações mais recentes"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM licitacoes 
                    ORDER BY data_publicacao DESC, created_at DESC
                    LIMIT %s
                """, (limit,))
                
                bids = cursor.fetchall()
                return [self._format_for_json(dict(bid)) for bid in bids]
    
    def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Buscar licitações por status"""
        bids = self.find_by_field('status', status)
        return [self._format_for_json(bid) for bid in bids]
    
    def find_by_uf(self, uf: str) -> List[Dict[str, Any]]:
        """Buscar licitações por UF"""
        bids = self.find_by_field('uf', uf)
        return [self._format_for_json(bid) for bid in bids]
    
    def search_by_keywords(self, keywords: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Buscar licitações por palavras-chave no objeto_compra
        Usado pela busca unificada
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                # Construir query base
                base_query = """
                    SELECT * FROM licitacoes 
                    WHERE objeto_compra ILIKE %s
                """
                
                params = [f'%{keywords}%']
                
                # Adicionar filtros se especificados
                conditions = []
                
                if filters:
                    if filters.get('uf'):
                        conditions.append("uf = %s")
                        params.append(filters['uf'])
                    
                    if filters.get('status'):
                        conditions.append("status = %s")
                        params.append(filters['status'])
                    
                    if filters.get('valor_min'):
                        conditions.append("valor_total_estimado >= %s")
                        params.append(float(filters['valor_min']))
                    
                    if filters.get('valor_max'):
                        conditions.append("valor_total_estimado <= %s")
                        params.append(float(filters['valor_max']))
                
                # Combinar query com condições
                if conditions:
                    base_query += " AND " + " AND ".join(conditions)
                
                # Ordenar por relevância (data mais recente primeiro)
                base_query += " ORDER BY data_publicacao DESC, created_at DESC LIMIT 100"
                
                cursor.execute(base_query, params)
                bids = cursor.fetchall()
                
                # Formatar para JSON
                formatted_bids = []
                for bid in bids:
                    bid_dict = dict(bid)
                    formatted_bid = self._format_for_json(bid_dict)
                    
                    # Adicionar indicadores para a busca unificada
                    formatted_bid['source'] = 'local'
                    formatted_bid['source_label'] = 'Banco Local'
                    
                    formatted_bids.append(formatted_bid)
                
                return formatted_bids
    
    def get_search_suggestions(self, term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Buscar sugestões de termos baseadas em objetos de licitação
        Usado para autocomplete na busca
        """
        with self.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT DISTINCT 
                        objeto_compra,
                        COUNT(*) as frequency
                    FROM licitacoes 
                    WHERE objeto_compra ILIKE %s
                    GROUP BY objeto_compra 
                    ORDER BY frequency DESC, objeto_compra
                    LIMIT %s
                """, (f'%{term}%', limit))
                
                suggestions = cursor.fetchall()
                
                return [
                    {
                        'text': suggestion['objeto_compra'],
                        'frequency': suggestion['frequency']
                    }
                    for suggestion in suggestions
                ]
    
    def get_common_keywords(self, limit: int = 20) -> List[str]:
        """
        Obter palavras-chave mais comuns nos objetos de licitação
        Usado para sugestões de busca
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    # Query para extrair palavras mais comuns (simplificada)
                    cursor.execute("""
                        SELECT 
                            UNNEST(STRING_TO_ARRAY(LOWER(objeto_compra), ' ')) as palavra,
                            COUNT(*) as frequencia
                        FROM licitacoes 
                        WHERE objeto_compra IS NOT NULL 
                          AND LENGTH(TRIM(objeto_compra)) > 0
                        GROUP BY palavra
                        HAVING LENGTH(palavra) > 3  -- Palavras com mais de 3 caracteres
                           AND palavra NOT IN ('para', 'como', 'pela', 'pelo', 'desde', 'ainda', 'mais', 'muito', 'entre')
                        ORDER BY frequencia DESC
                        LIMIT %s
                    """, (limit,))
                    
                    results = cursor.fetchall()
                    return [row['palavra'] for row in results]
                    
        except Exception as e:
            logger.error(f"Erro ao buscar palavras-chave comuns: {e}")
            return ['computadores', 'softwares', 'equipamentos', 'serviços', 'consultoria']
    
    def delete_bid_items(self, licitacao_id: str) -> bool:
        """
        Remove todos os itens de uma licitação
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM licitacao_itens WHERE licitacao_id = %s",
                        (licitacao_id,)
                    )
                    deleted_count = cursor.rowcount
                    conn.commit()
                    logger.info(f"✅ {deleted_count} itens removidos da licitação {licitacao_id}")
                    return True
        except Exception as e:
            logger.error(f"❌ Erro ao remover itens da licitação {licitacao_id}: {e}")
            return False
    
    def save_bid_items(self, licitacao_id: str, items: List[Dict[str, Any]]) -> bool:
        """
        Salva itens de uma licitação no banco
        Baseado na implementação correta do pncp_api.py que funciona
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    for i, item in enumerate(items, 1):
                        # ===== VALIDAÇÕES DE VALORES (igual ao pncp_api.py) =====
                        
                        # Validar e limitar valor unitário estimado
                        valor_unitario = item.get("valorUnitarioEstimado", 0)
                        try:
                            valor_unitario = float(valor_unitario) if valor_unitario is not None else 0
                            # Limitar a 999 bilhões (limite do DECIMAL(15,2))
                            if valor_unitario > 999999999999.99:
                                valor_unitario = 999999999999.99
                            elif valor_unitario < 0:
                                valor_unitario = 0
                        except (ValueError, TypeError):
                            valor_unitario = 0
                        
                        # Validar quantidade
                        quantidade = item.get("quantidade", 0)
                        try:
                            quantidade = float(quantidade) if quantidade is not None else 0
                            if quantidade < 0:
                                quantidade = 0
                        except (ValueError, TypeError):
                            quantidade = 0

                        # Validar percentual de margem preferencial
                        percentual_margem = item.get("percentualMargemPreferenciaNormal")
                        if percentual_margem is not None:
                            try:
                                percentual_margem = float(percentual_margem)
                                if percentual_margem < 0 or percentual_margem > 100:
                                    percentual_margem = None
                            except (ValueError, TypeError):
                                percentual_margem = None

                        # ===== INSERT IDÊNTICO AO pncp_api.py =====
                        cursor.execute("""
                            INSERT INTO licitacao_itens (
                                licitacao_id, numero_item, descricao, quantidade,
                                unidade_medida, valor_unitario_estimado,
                                material_ou_servico, ncm_nbs_codigo,
                                criterio_julgamento_id, criterio_julgamento_nome,
                                tipo_beneficio_id, tipo_beneficio_nome,
                                situacao_item_id, situacao_item_nome,
                                aplicabilidade_margem_preferencia, percentual_margem_preferencia,
                                tem_resultado
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (licitacao_id, numero_item) DO UPDATE SET
                                material_ou_servico = EXCLUDED.material_ou_servico,
                                ncm_nbs_codigo = EXCLUDED.ncm_nbs_codigo,
                                criterio_julgamento_id = EXCLUDED.criterio_julgamento_id,
                                criterio_julgamento_nome = EXCLUDED.criterio_julgamento_nome,
                                tipo_beneficio_id = EXCLUDED.tipo_beneficio_id,
                                tipo_beneficio_nome = EXCLUDED.tipo_beneficio_nome,
                                situacao_item_id = EXCLUDED.situacao_item_id,
                                situacao_item_nome = EXCLUDED.situacao_item_nome,
                                aplicabilidade_margem_preferencia = EXCLUDED.aplicabilidade_margem_preferencia,
                                percentual_margem_preferencia = EXCLUDED.percentual_margem_preferencia,
                                tem_resultado = EXCLUDED.tem_resultado,
                                updated_at = NOW()
                        """, (
                            licitacao_id,
                            item.get("numeroItem", i),              # API PNCP: numeroItem
                            item.get("descricao", ""),              # API PNCP: descricao
                            quantidade,
                            item.get("unidadeMedida", ""),          # API PNCP: unidadeMedida
                            valor_unitario,
                            # Novos campos da API PNCP
                            item.get("materialOuServico"),          # API PNCP: 'M' ou 'S'
                            item.get("ncmNbsCodigo"),               # API PNCP: ncmNbsCodigo
                            item.get("criterioJulgamentoId"),       # API PNCP: criterioJulgamentoId
                            item.get("criterioJulgamentoNome"),     # API PNCP: criterioJulgamentoNome
                            item.get("tipoBeneficio"),              # API PNCP: tipoBeneficio
                            item.get("tipoBeneficioNome"),          # API PNCP: tipoBeneficioNome
                            item.get("situacaoCompraItem"),         # API PNCP: situacaoCompraItem
                            item.get("situacaoCompraItemNome"),     # API PNCP: situacaoCompraItemNome
                            item.get("aplicabilidadeMargemPreferenciaNormal", False),  # API PNCP: booleano
                            percentual_margem,                      # Percentual validado
                            item.get("temResultado", False)        # API PNCP: temResultado booleano
                        ))
                    
                    conn.commit()
                    logger.info(f"✅ {len(items)} itens salvos para a licitação {licitacao_id}")
                    return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar itens da licitação {licitacao_id}: {e}")
            return False
    
    def save_licitacao(self, licitacao_data: Dict[str, Any]) -> Optional[str]:
        """
        Salva uma licitação completa no banco usando a mesma estrutura do pncp_api.py
        Baseado na função save_bid_to_db() que funciona corretamente
        """
        try:
            # ===== MAPEAMENTO BASEADO NO pncp_api.py =====
            
            # Extrair dados da API (estrutura do search service)
            api_data = licitacao_data.get('api_data', {})
            
            # Validar e limitar valor total estimado
            valor_total = licitacao_data.get("valor_total_estimado")
            if valor_total is not None:
                try:
                    valor_total = float(valor_total)
                    # Limitar a 999 bilhões (limite do DECIMAL(15,2))
                    if valor_total > 999999999999.99:
                        valor_total = 999999999999.99
                    elif valor_total < 0:
                        valor_total = 0
                except (ValueError, TypeError):
                    valor_total = None

            # Validar e limitar valor total homologado
            valor_homologado = licitacao_data.get("valor_total_homologado")
            if valor_homologado is not None:
                try:
                    valor_homologado = float(valor_homologado)
                    if valor_homologado > 999999999999.99:
                        valor_homologado = 999999999999.99
                    elif valor_homologado < 0:
                        valor_homologado = 0
                except (ValueError, TypeError):
                    valor_homologado = None
            
            # Extrair campos usando EXATAMENTE a mesma lógica do pncp_api.py
            pncp_id = licitacao_data.get('pncp_id', '')
            orgao_cnpj = licitacao_data.get('orgao_cnpj', '')
            razao_social = licitacao_data.get('orgao_razao_social', '')
            
            # Ano e sequencial - usar dados da API ou extrair do pncp_id
            ano_compra = licitacao_data.get('ano_compra') or self._extract_year_from_pncp_id(pncp_id)
            sequencial_compra = licitacao_data.get('sequencial_compra') or self._extract_sequential_from_pncp_id(pncp_id)
            
            # Dados de UF e unidade
            uf_sigla = licitacao_data.get('uf', '')
            uf_nome = licitacao_data.get('uf_nome', '')
            nome_unidade = licitacao_data.get('unidade_nome', '')
            municipio_nome = licitacao_data.get('municipio', '')
            codigo_ibge = licitacao_data.get('codigo_ibge')
            codigo_unidade = licitacao_data.get('unidade_compra', '')
            
            # ===== USAR EXATAMENTE OS MESMOS CAMPOS DO pncp_api.py =====
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO licitacoes (
                            pncp_id, orgao_cnpj, ano_compra, sequencial_compra,
                            objeto_compra, link_sistema_origem, data_publicacao,
                            valor_total_estimado, uf, status,
                            numero_controle_pncp, numero_compra, processo,
                            valor_total_homologado, data_abertura_proposta, data_encerramento_proposta,
                            modo_disputa_id, modo_disputa_nome, srp, 
                            link_processo_eletronico, justificativa_presencial, razao_social,
                            uf_nome, nome_unidade, municipio_nome, codigo_ibge, codigo_unidade
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (pncp_id) DO UPDATE SET
                            updated_at = NOW(),
                            numero_controle_pncp = EXCLUDED.numero_controle_pncp,
                            numero_compra = EXCLUDED.numero_compra,
                            processo = EXCLUDED.processo,
                            valor_total_homologado = EXCLUDED.valor_total_homologado,
                            data_abertura_proposta = EXCLUDED.data_abertura_proposta,
                            data_encerramento_proposta = EXCLUDED.data_encerramento_proposta,
                            modo_disputa_id = EXCLUDED.modo_disputa_id,
                            modo_disputa_nome = EXCLUDED.modo_disputa_nome,
                            srp = EXCLUDED.srp,
                            link_processo_eletronico = EXCLUDED.link_processo_eletronico,
                            justificativa_presencial = EXCLUDED.justificativa_presencial,
                            razao_social = EXCLUDED.razao_social,
                            uf_nome = EXCLUDED.uf_nome,
                            nome_unidade = EXCLUDED.nome_unidade,
                            municipio_nome = EXCLUDED.municipio_nome,
                            codigo_ibge = EXCLUDED.codigo_ibge,
                            codigo_unidade = EXCLUDED.codigo_unidade
                        RETURNING id
                    """, (
                        pncp_id,
                        orgao_cnpj,
                        ano_compra,
                        sequencial_compra,
                        licitacao_data.get('objeto_compra', ''),
                        licitacao_data.get('link_sistema_origem', ''),
                        licitacao_data.get('data_publicacao_pncp'),
                        valor_total,
                        uf_sigla,
                        "coletada",
                        # Campos extras idênticos ao pncp_api.py
                        pncp_id,  # numero_controle_pncp
                        licitacao_data.get('numero_compra', ''),
                        licitacao_data.get('processo', ''),
                        valor_homologado,
                        licitacao_data.get('data_inicio_lances'),  # data_abertura_proposta
                        licitacao_data.get('data_encerramento_proposta'),  # data_encerramento_proposta
                        licitacao_data.get('modo_disputa_id'),
                        licitacao_data.get('modo_disputa', ''),
                        licitacao_data.get('srp', False),
                        licitacao_data.get('link_processo_eletronico', ''),
                        licitacao_data.get('justificativa_presencial', ''),
                        razao_social,
                        uf_nome,
                        nome_unidade,
                        municipio_nome,
                        codigo_ibge,
                        codigo_unidade
                    ))
                    
                    result = cursor.fetchone()
                    if result:
                        licitacao_id = str(result[0])
                        logger.info(f"✅ Licitação salva: {pncp_id} -> ID {licitacao_id}")
                        return licitacao_id
                    else:
                        logger.warning(f"⚠️ Licitação não retornou ID: {pncp_id}")
                        return None
                        
        except Exception as e:
            logger.error(f"❌ Erro ao salvar licitação {licitacao_data.get('pncp_id', 'N/A')}: {e}")
            return None
    
    def _extract_year_from_pncp_id(self, pncp_id: str) -> int:
        """Extrai ano do número de controle PNCP"""
        try:
            if '/' in pncp_id:
                parts = pncp_id.split('/')
                if len(parts) >= 2:
                    return int(parts[-1])
        except (ValueError, IndexError):
            pass
        return datetime.now().year
    
    def _extract_sequential_from_pncp_id(self, pncp_id: str) -> int:
        """Extrai sequencial do número de controle PNCP"""
        try:
            if '-' in pncp_id and '/' in pncp_id:
                # Formato: CNPJ-1-SEQUENCIAL/ANO
                parts = pncp_id.split('-')
                if len(parts) >= 3:
                    seq_part = parts[2].split('/')[0]
                    return int(seq_part.lstrip('0') or '1')
        except (ValueError, IndexError):
            pass
        return 1 