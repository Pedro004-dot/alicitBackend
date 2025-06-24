"""
Supabase Persistence Service
Serviço para persistir licitações e itens do PNCP no banco de dados Supabase
"""
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import os
import json
import re

# Importar Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    logging.warning("⚠️ Supabase client não encontrado. Execute: pip install supabase")
    Client = None

logger = logging.getLogger(__name__)

class SupabasePersistenceService:
    """Serviço para persistir dados do PNCP no Supabase"""
    
    def __init__(self):
        """Inicializa conexão com Supabase"""
        self.supabase = None
        self._initialize_supabase()
    
    def _initialize_supabase(self):
        """Inicializa cliente Supabase"""
        try:
            # Tentar diferentes nomes de variáveis de ambiente
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or 
                           os.getenv('SUPABASE_ANON_KEY') or 
                           os.getenv('SUPABASE_SERVICE_KEY'))
            
            if not supabase_url or not supabase_key:
                logger.warning("⚠️ Credenciais do Supabase não configuradas")
                logger.warning(f"   SUPABASE_URL: {'✅' if supabase_url else '❌'}")
                logger.warning(f"   SUPABASE_ANON_KEY: {'✅' if os.getenv('SUPABASE_ANON_KEY') else '❌'}")
                logger.warning(f"   SUPABASE_SERVICE_KEY: {'✅' if os.getenv('SUPABASE_SERVICE_KEY') else '❌'}")
                return
            
            if Client is None:
                logger.warning("⚠️ Cliente Supabase não disponível. Execute: pip install supabase")
                return
            
            self.supabase = create_client(supabase_url, supabase_key)
            logger.info("✅ Conexão com Supabase estabelecida")
            logger.info(f"   URL: {supabase_url}")
            logger.info(f"   Key: {supabase_key[:20]}...")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com Supabase: {e}")
            self.supabase = None
    
    def save_licitacoes(
        self, 
        licitacoes: List[Dict[str, Any]], 
        include_items: bool = True,
        search_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Salva lista de licitações no Supabase com seus itens
        
        Args:
            licitacoes: Lista de licitações encontradas
            include_items: Se deve salvar itens detalhados
            search_metadata: Metadados da busca realizada
            
        Returns:
            Estatísticas do processo de salvamento
        """
        if not self.supabase:
            logger.warning("⚠️ Supabase não disponível - dados não persistidos")
            return {
                'error': 'Supabase não disponível',
                'licitacoes_salvas': 0,
                'itens_salvos': 0,
                'duplicatas_ignoradas': 0
            }
        
        stats = {
            'licitacoes_salvas': 0,
            'licitacoes_atualizadas': 0,
            'itens_salvos': 0,
            'duplicatas_ignoradas': 0,
            'erros': []
        }
        
        try:
            logger.info(f"💾 Iniciando salvamento de {len(licitacoes)} licitações no Supabase")
            
            for licitacao in licitacoes:
                try:
                    # Preparar dados da licitação
                    licitacao_data = self._prepare_licitacao_data(licitacao)
                    
                    # Verificar se licitação já existe
                    existing = self._check_existing_licitacao(licitacao_data['pncp_id'])
                    
                    if existing:
                        # Atualizar licitação existente
                        saved_licitacao = self._update_licitacao(existing['id'], licitacao_data)
                        stats['licitacoes_atualizadas'] += 1
                    else:
                        # Inserir nova licitação
                        saved_licitacao = self._insert_licitacao(licitacao_data)
                        stats['licitacoes_salvas'] += 1
                    
                    # Salvar itens se disponíveis e solicitado
                    if include_items and saved_licitacao and licitacao.get('itens_detalhados'):
                        itens_salvos = self._save_licitacao_items(
                            saved_licitacao['id'],
                            licitacao['itens_detalhados']
                        )
                        stats['itens_salvos'] += itens_salvos
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao salvar licitação {licitacao.get('pncp_id', 'N/A')}: {e}")
                    stats['erros'].append({
                        'pncp_id': licitacao.get('pncp_id', 'N/A'),
                        'erro': str(e)
                    })
            
            # Salvar metadados da busca se fornecidos
            if search_metadata:
                self._save_search_metadata(search_metadata, stats)
            
            logger.info(f"✅ Salvamento concluído: {stats['licitacoes_salvas']} novas, "
                       f"{stats['licitacoes_atualizadas']} atualizadas, {stats['itens_salvos']} itens")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Erro geral no salvamento: {e}")
            stats['erros'].append({'erro_geral': str(e)})
            return stats
    
    def _prepare_licitacao_data(self, licitacao: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados da licitação para inserção no Supabase"""
        api_data = licitacao.get('api_data', {})
        
        # Extrair dados do número de controle PNCP se disponível
        numero_controle = licitacao.get('pncp_id', '') or api_data.get('numeroControlePNCP', '')
        orgao_cnpj, ano_compra, sequencial_compra = self._parse_numero_controle(numero_controle)
        
        # Usar dados diretos da licitação formatada (mais confiáveis)
        orgao_cnpj = licitacao.get('orgao_cnpj') or orgao_cnpj
        ano_compra = licitacao.get('ano_compra') or ano_compra
        sequencial_compra = licitacao.get('sequencial_compra') or sequencial_compra
        
        # Preparar dados principais usando o mapeamento correto
        licitacao_data = {
            'pncp_id': licitacao.get('pncp_id', ''),
            'orgao_cnpj': orgao_cnpj,
            'ano_compra': ano_compra,
            'sequencial_compra': sequencial_compra,
            'objeto_compra': licitacao.get('objeto_compra', ''),
            'link_sistema_origem': licitacao.get('link_sistema_origem') or api_data.get('linkSistemaOrigem'),
            'data_publicacao': self._parse_date(licitacao.get('data_publicacao')),
            'data_publicacao_pncp': self._parse_datetime(licitacao.get('data_publicacao_pncp')),
            'data_inclusao': self._parse_datetime(licitacao.get('data_inclusao')),
            'data_abertura_proposta': self._parse_datetime(
                licitacao.get('data_inicio_lances') or 
                licitacao.get('data_abertura_proposta') or
                api_data.get('dataAberturaProposta')
            ),
            'data_encerramento_proposta': self._parse_datetime(
                licitacao.get('data_encerramento_proposta') or
                api_data.get('dataEncerramentoProposta')
            ),
            'data_atualizacao': self._parse_datetime(licitacao.get('data_atualizacao')),
            'valor_total_estimado': licitacao.get('valor_total_estimado', 0),
            'valor_total_homologado': licitacao.get('valor_total_homologado', 0),
            'uf': licitacao.get('uf', ''),
            'modalidade_nome': licitacao.get('modalidade_nome', ''),
            'modalidade_id': licitacao.get('codigo_modalidade'),
            'situacao_compra_nome': licitacao.get('situacao', ''),
            'situacao_compra_id': licitacao.get('situacao_id'),
            
            # CAMPOS QUE ESTAVAM FALTANDO
            'numero_controle_pncp': numero_controle,
            'numero_compra': licitacao.get('numero_compra', ''),
            'processo': licitacao.get('processo', ''),
            'modo_disputa_nome': licitacao.get('modo_disputa', ''),
            'modo_disputa_id': licitacao.get('modo_disputa_id'),
            'srp': licitacao.get('srp', False),
            'informacao_complementar': licitacao.get('informacao_complementar') or api_data.get('informacaoComplementar'),
            
            # DADOS DO ÓRGÃO E UNIDADE
            'razao_social': licitacao.get('orgao_razao_social') or api_data.get('orgaoEntidade', {}).get('razaoSocial'),
            'nome_unidade': licitacao.get('unidade_nome') or api_data.get('unidadeOrgao', {}).get('nomeUnidade'),
            'municipio_nome': licitacao.get('municipio', ''),
            'uf_nome': self._get_uf_name(licitacao.get('uf', '')),
            'codigo_unidade': licitacao.get('unidade_compra', ''),
            
            # METADADOS DO SISTEMA
            'status': 'coletada',
            'data_ultima_sincronizacao': datetime.now().isoformat(),
            'possui_itens': len(licitacao.get('itens_detalhados', [])) > 0,
            
            # DADOS COMPLETOS PARA AUDITORIA
            'dados_api_completos': {
                'pncp_api': api_data,
                'busca_metadata': {
                    'keyword_score': licitacao.get('keyword_score', 0),
                    'item_score': licitacao.get('item_score', 0),
                    'total_score': licitacao.get('total_score', 0),
                    'relevance_score': licitacao.get('relevance_score', 0),
                    'data_importacao': licitacao.get('data_importacao'),
                    'fonte_dados': licitacao.get('fonte_dados'),
                    'total_itens': licitacao.get('total_itens', 0),
                    'matched_keywords': licitacao.get('matched_keywords', [])
                },
                'licitacao_original': licitacao  # Backup completo da licitação formatada
            }
        }
        
        logger.debug(f"📋 Licitação preparada para Supabase: {licitacao_data['pncp_id']}")
        logger.debug(f"   📝 Objeto: {licitacao_data['objeto_compra'][:50]}...")
        logger.debug(f"   🏢 Órgão: {licitacao_data['razao_social']}")
        logger.debug(f"   📅 Data abertura: {licitacao_data['data_abertura_proposta']}")
        logger.debug(f"   📅 Data encerramento: {licitacao_data['data_encerramento_proposta']}")
        logger.debug(f"   🔢 Processo: {licitacao_data['processo']}")
        logger.debug(f"   🆔 Número compra: {licitacao_data['numero_compra']}")
        
        return licitacao_data
    
    def _parse_numero_controle(self, numero_controle: str) -> Tuple[str, int, int]:
        """Extrai CNPJ, ano e sequencial do número de controle PNCP"""
        if not numero_controle:
            # Retornar valores padrão seguros para evitar NOT NULL constraint
            return '', datetime.now().year, 1
        
        try:
            # Formato: CNPJ-1-SEQUENCIAL/ANO
            # Exemplo: 09069709000118-1-000094/2025
            parts = numero_controle.split('-')
            if len(parts) >= 3:
                cnpj = parts[0].strip()
                ano_seq = parts[2].split('/')
                if len(ano_seq) == 2:
                    sequencial = int(ano_seq[0].lstrip('0') or '1')  # Remove zeros à esquerda
                    ano = int(ano_seq[1])
                    return cnpj, ano, sequencial
                    
            # Tentar formato alternativo se não funcionou
            # Algumas APIs podem retornar diferentes formatos
            if '/' in numero_controle:
                # Tentar extrair ano do final
                parts = numero_controle.split('/')
                if len(parts) >= 2:
                    try:
                        ano = int(parts[-1])
                        # Tentar extrair CNPJ do início
                        cnpj_part = parts[0].split('-')[0] if '-' in parts[0] else ''
                        # Tentar extrair sequencial
                        seq_match = re.search(r'-(\d+)$', parts[0])
                        sequencial = int(seq_match.group(1)) if seq_match else 1
                        return cnpj_part, ano, sequencial
                    except ValueError:
                        pass
                        
        except (ValueError, IndexError) as e:
            logger.warning(f"⚠️ Erro ao parsear número de controle '{numero_controle}': {e}")
        
        # Fallback: extrair CNPJ se possível e usar valores padrão
        cnpj = numero_controle.split('-')[0] if '-' in numero_controle else ''
        return cnpj, datetime.now().year, 1
    
    def _extract_year_from_date(self, date_str: Optional[str]) -> Optional[int]:
        """Extrai ano de uma string de data"""
        if not date_str:
            return None
        
        try:
            # Tentar diferentes formatos de data
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                try:
                    year = datetime.strptime(date_str[:len(fmt)], fmt).year
                    # Validar se o ano é razoável (entre 2020 e 2030)
                    if 2020 <= year <= 2030:
                        return year
                except ValueError:
                    continue
            
            # Tentar extrair ano diretamente
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                year = int(year_match.group(1))
                # Validar se o ano é razoável
                if 2020 <= year <= 2030:
                    return year
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair ano de '{date_str}': {e}")
        
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Converte string de data para formato date do PostgreSQL"""
        if not date_str:
            return None
        
        try:
            # Tentar diferentes formatos
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                try:
                    dt = datetime.strptime(date_str[:len(fmt)], fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
        except Exception:
            pass
        
        return None
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[str]:
        """Converte string para formato datetime com timezone"""
        if not datetime_str:
            return None
        
        try:
            datetime_str = str(datetime_str).strip()
            
            # Se já está no formato ISO com timezone, retornar como está
            if ('Z' in datetime_str or 
                ('+' in datetime_str and ':' in datetime_str[-6:]) or 
                ('-' in datetime_str and ':' in datetime_str[-6:])):
                return datetime_str
            
            # Tentar diferentes formatos e adicionar timezone UTC se necessário
            formats_to_try = [
                '%Y-%m-%dT%H:%M:%S.%f',       # 2024-01-15T09:00:00.000
                '%Y-%m-%dT%H:%M:%S',          # 2024-01-15T09:00:00
                '%Y-%m-%d %H:%M:%S.%f',       # 2024-01-15 09:00:00.000
                '%Y-%m-%d %H:%M:%S',          # 2024-01-15 09:00:00
                '%Y-%m-%dT%H:%M',             # 2024-01-15T09:00
                '%Y-%m-%d %H:%M',             # 2024-01-15 09:00
            ]
            
            for fmt in formats_to_try:
                try:
                    # Truncar string para coincidir com o formato se necessário
                    test_str = datetime_str
                    if fmt == '%Y-%m-%dT%H:%M:%S' and len(datetime_str) > 19:
                        # Se tem microsegundos, remover para testar formato simples
                        test_str = datetime_str[:19]
                    elif fmt == '%Y-%m-%d %H:%M:%S' and len(datetime_str) > 19:
                        # Converter T para espaço e truncar
                        test_str = datetime_str.replace('T', ' ')[:19]
                    elif fmt == '%Y-%m-%dT%H:%M' and len(datetime_str) > 16:
                        test_str = datetime_str[:16]
                    elif fmt == '%Y-%m-%d %H:%M' and len(datetime_str) > 16:
                        test_str = datetime_str.replace('T', ' ')[:16]
                    
                    dt = datetime.strptime(test_str, fmt)
                    return dt.isoformat() + 'Z'  # Adicionar timezone UTC
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear datetime '{datetime_str}': {e}")
        
        return None
    
    def _get_uf_name(self, uf_code: str) -> str:
        """Converte código UF para nome completo"""
        uf_map = {
            'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas',
            'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
            'GO': 'Goiás', 'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul',
            'MG': 'Minas Gerais', 'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná',
            'PE': 'Pernambuco', 'PI': 'Piauí', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte',
            'RS': 'Rio Grande do Sul', 'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina',
            'SP': 'São Paulo', 'SE': 'Sergipe', 'TO': 'Tocantins'
        }
        return uf_map.get(uf_code.upper(), uf_code)
    
    def _check_existing_licitacao(self, pncp_id: str) -> Optional[Dict[str, Any]]:
        """Verifica se licitação já existe no banco"""
        try:
            result = self.supabase.table('licitacoes').select('id, pncp_id').eq('pncp_id', pncp_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar licitação existente {pncp_id}: {e}")
            return None
    
    def _insert_licitacao(self, licitacao_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insere nova licitação no banco"""
        try:
            result = self.supabase.table('licitacoes').insert(licitacao_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Erro ao inserir licitação {licitacao_data.get('pncp_id')}: {e}")
            raise
    
    def _update_licitacao(self, licitacao_id: str, licitacao_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Atualiza licitação existente"""
        try:
            # Adicionar timestamp de atualização
            licitacao_data['updated_at'] = datetime.now().isoformat()
            licitacao_data['data_ultima_sincronizacao'] = datetime.now().isoformat()
            
            result = self.supabase.table('licitacoes').update(licitacao_data).eq('id', licitacao_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar licitação {licitacao_id}: {e}")
            raise
    
    def _save_licitacao_items(self, licitacao_id: str, itens: List[Dict[str, Any]]) -> int:
        """Salva itens de uma licitação"""
        if not itens:
            return 0
        
        try:
            # Primeiro, remover itens existentes para esta licitação
            self.supabase.table('licitacao_itens').delete().eq('licitacao_id', licitacao_id).execute()
            
            # Preparar dados dos itens
            itens_data = []
            for i, item in enumerate(itens):
                item_data = self._prepare_item_data(licitacao_id, i + 1, item)
                itens_data.append(item_data)
            
            # Inserir novos itens em lotes
            batch_size = 100
            total_saved = 0
            
            for i in range(0, len(itens_data), batch_size):
                batch = itens_data[i:i + batch_size]
                result = self.supabase.table('licitacao_itens').insert(batch).execute()
                total_saved += len(result.data) if result.data else 0
            
            return total_saved
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar itens da licitação {licitacao_id}: {e}")
            return 0
    
    def _prepare_item_data(self, licitacao_id: str, numero_item: int, item: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara dados de um item para inserção"""
        return {
            'licitacao_id': licitacao_id,
            'numero_item': numero_item,
            'descricao': item.get('descricaoItem', item.get('descricao', '')),
            'quantidade': item.get('quantidade'),
            'unidade_medida': item.get('unidadeMedida'),
            'valor_unitario_estimado': item.get('valorUnitarioEstimado'),
            'valor_total': item.get('valorTotal'),
            'material_ou_servico': item.get('materialOuServico'),
            'criterio_julgamento_nome': item.get('criterioJulgamento'),
            'situacao_item': item.get('situacaoItem'),
            'codigo_produto_servico': item.get('codigoProdutoServico'),
            'especificacao_tecnica': item.get('descricaoDetalhada'),
            'beneficio_micro_epp': item.get('beneficioMicroEpp', False),
            'beneficio_local': item.get('beneficioLocal', False),
            'dados_api_completos': item  # Backup completo do item
        }
    
    def _save_search_metadata(self, search_metadata: Dict[str, Any], stats: Dict[str, Any]):
        """Salva metadados da busca realizada"""
        try:
            search_data = {
                'keywords': ' '.join(search_metadata.get('keywords_used', [])),
                'data_inicio': search_metadata.get('date_range', '').split(' a ')[0] if ' a ' in search_metadata.get('date_range', '') else None,
                'data_fim': search_metadata.get('date_range', '').split(' a ')[1] if ' a ' in search_metadata.get('date_range', '') else None,
                'modalidade': search_metadata.get('modalidade', 'pregao_eletronico'),
                'max_pages': search_metadata.get('total_pages_searched', 0),
                'total_api_results': search_metadata.get('total_api_results', 0),
                'total_filtered_results': search_metadata.get('total_filtered_results', 0),
                'search_metadata': {
                    **search_metadata,
                    'persistence_stats': stats
                },
                'status': 'completed' if not stats.get('erros') else 'completed_with_errors'
            }
            
            self.supabase.table('pncp_searches').insert(search_data).execute()
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao salvar metadados da busca: {e}")
    
    def get_saved_licitacoes_count(self, days: int = 30) -> int:
        """Retorna quantidade de licitações salvas nos últimos N dias"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            result = self.supabase.table('licitacoes').select('id', count='exact').gte('created_at', cutoff_date).execute()
            return result.count or 0
        except Exception as e:
            logger.error(f"❌ Erro ao contar licitações: {e}")
            return 0
    
    def get_recent_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna buscas recentes realizadas"""
        try:
            result = self.supabase.table('pncp_searches').select('*').order('created_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico: {e}")
            return []

    def _format_licitacao_for_database(self, licitacao_data):
        """
        Formatar dados da licitação para inserção no banco
        """
        try:
            # Usar os dados da API se disponíveis
            api_data = licitacao_data.get('api_data', {})
            
            # Extrair dados do órgão e unidade
            orgao_entidade = api_data.get('orgaoEntidade', {})
            unidade_orgao = api_data.get('unidadeOrgao', {})
            
            # Calcular campos derivados
            razao_social = orgao_entidade.get('razaoSocial', '')
            nome_unidade = unidade_orgao.get('nomeUnidade', '')
            municipio_nome = unidade_orgao.get('municipio', {}).get('nome', '')
            uf_nome = unidade_orgao.get('uf', {}).get('nome', '')
            codigo_ibge = unidade_orgao.get('municipio', {}).get('codigoIBGE', '')
            codigo_unidade = unidade_orgao.get('codigoUnidade', '')
            
            # UF de 2 caracteres
            uf = licitacao_data.get('uf', '')
            if len(uf) > 2:
                uf = uf[:2]  # Cortar para 2 caracteres
            
            formatted_data = {
                'pncp_id': licitacao_data['pncp_id'],
                'orgao_cnpj': licitacao_data.get('orgao_cnpj', ''),
                'ano_compra': licitacao_data.get('ano_compra', 2025),
                'sequencial_compra': licitacao_data.get('sequencial_compra', 0),
                'objeto_compra': licitacao_data.get('objeto_compra', ''),
                'link_sistema_origem': licitacao_data.get('link_sistema_origem'),
                'data_publicacao': self._parse_date(licitacao_data.get('data_publicacao')),
                'data_publicacao_pncp': self._parse_datetime(licitacao_data.get('data_publicacao_pncp')),
                'data_inclusao': self._parse_datetime(licitacao_data.get('data_inclusao')),
                'data_abertura_proposta': self._parse_datetime(
                    licitacao_data.get('data_inicio_lances') or 
                    licitacao_data.get('data_abertura_proposta') or
                    api_data.get('dataAberturaProposta')
                ),
                'data_encerramento_proposta': self._parse_datetime(
                    licitacao_data.get('data_encerramento_proposta') or
                    api_data.get('dataEncerramentoProposta')
                ),
                'data_atualizacao': self._parse_datetime(licitacao_data.get('data_atualizacao')),
                'valor_total_estimado': self._safe_decimal(licitacao_data.get('valor_total_estimado', 0)),
                'uf': uf,
                'status': 'coletada',
                'modalidade_nome': licitacao_data.get('modalidade_nome', ''),
                'modalidade_id': licitacao_data.get('modalidade_id'),
                'situacao_compra_nome': licitacao_data.get('situacao', ''),
                'situacao_compra_id': licitacao_data.get('situacao_id'),
                'processo': licitacao_data.get('processo', ''),
                'numero_compra': licitacao_data.get('numero_compra', ''),
                'numero_controle_pncp': licitacao_data.get('numero_controle_pncp', ''),
                'informacao_complementar': licitacao_data.get('informacao_complementar', ''),
                'justificativa_presencial': licitacao_data.get('justificativa_presencial', ''),
                'link_processo_eletronico': licitacao_data.get('link_processo_eletronico', ''),
                'srp': licitacao_data.get('srp', False),
                'modo_disputa_id': licitacao_data.get('modo_disputa_id'),
                'modo_disputa_nome': licitacao_data.get('modo_disputa_nome', ''),
                'orgao_entidade': orgao_entidade,
                'unidade_orgao': unidade_orgao,
                'unidade_sub_rogada': api_data.get('unidadeSubRogada'),
                'orgao_sub_rogado': api_data.get('orgaoSubRogado'),
                'amparo_legal': api_data.get('amparoLegal'),
                'tipo_instrumento_convocatorio_codigo': api_data.get('tipoInstrumentoConvocatorioCodigo'),
                'tipo_instrumento_convocatorio_nome': api_data.get('tipoInstrumentoConvocatorioNome', ''),
                'dados_api_completos': api_data,
                'possui_itens': len(licitacao_data.get('itens_detalhados', [])) > 0,
                'data_ultima_sincronizacao': datetime.now().isoformat(),
                
                # Campos calculados/extraídos
                'razao_social': razao_social,
                'uf_nome': uf_nome,
                'nome_unidade': nome_unidade,
                'municipio_nome': municipio_nome,
                'codigo_ibge': codigo_ibge,
                'codigo_unidade': codigo_unidade,
                'status_rag': 'pendente'
            }
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"❌ Erro ao formatar licitação {licitacao_data.get('pncp_id', 'UNKNOWN')}: {str(e)}")
            raise 