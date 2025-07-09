"""
🌐 ComprasNet Data Mapper
Mapper específico para conversão de dados do ComprasNet
Implementa BaseDataMapper para persistência escalável
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from interfaces.data_mapper import BaseDataMapper, DatabaseOpportunity, OpportunityData

logger = logging.getLogger(__name__)

class ComprasNetDataMapper(BaseDataMapper):
    """
    Mapper específico para dados do ComprasNet
    Converte OpportunityData do ComprasNet para formato de banco padronizado
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("🚫 ComprasNetDataMapper inicializado - SALVAMENTO AUTOMÁTICO DESATIVADO")
    
    @property
    def provider_name(self) -> str:
        """Nome do provider - deve corresponder ao ComprasNetAdapter"""
        return "comprasnet"
    
    def should_auto_save(self) -> bool:
        """
        🚫 SALVAMENTO AUTOMÁTICO DESATIVADO
        
        Returns:
            bool: False - nunca salvar automaticamente
        """
        return False
    
    def opportunity_to_database(self, opportunity: OpportunityData) -> DatabaseOpportunity:
        """
        Converte OpportunityData do ComprasNet para DatabaseOpportunity
        
        Args:
            opportunity: Dados da oportunidade do ComprasNet
            
        Returns:
            DatabaseOpportunity: Dados formatados para banco
        """
        try:
            # 🔧 VALIDAÇÃO E SANITIZAÇÃO DE DADOS
            
            # External ID obrigatório
            external_id = str(opportunity.external_id or '').strip()
            if not external_id:
                raise ValueError("External ID não pode estar vazio")
            
            # Título obrigatório e limitado
            title = str(opportunity.title or '').strip()[:500]  # Limitar a 500 chars
            if not title:
                title = f"Licitação ComprasNet {external_id}"
            
            # Descrição limitada
            description = str(opportunity.description or '').strip()[:1000] if opportunity.description else None
            
            # Valor estimado com validação
            estimated_value = None
            if opportunity.estimated_value is not None:
                try:
                    estimated_value = float(opportunity.estimated_value)
                    # Limitar valor máximo para evitar overflow no banco
                    if estimated_value > 999999999999.99:
                        estimated_value = 999999999999.99
                    elif estimated_value < 0:
                        estimated_value = 0.0
                except (ValueError, TypeError):
                    estimated_value = None
                    self.logger.warning(f"Valor estimado inválido para {external_id}: {opportunity.estimated_value}")
            
            # Códigos padronizados
            currency_code = str(opportunity.currency_code or 'BRL').upper()[:3]
            country_code = str(opportunity.country_code or 'BR').upper()[:2]
            region_code = str(opportunity.region_code or '').upper()[:2] if opportunity.region_code else None
            municipality = str(opportunity.municipality or '').strip()[:255] if opportunity.municipality else None
            
            # Datas com validação
            publication_date = self._validate_date(opportunity.publication_date)
            submission_deadline = self._validate_date(opportunity.submission_deadline)
            opening_date = self._validate_date(opportunity.opening_date)
            
            # 📊 DADOS ESPECÍFICOS DO COMPRASNET
            provider_data = opportunity.provider_specific_data or {}
            
            # Categorias e métodos
            category = self._extract_category(provider_data)
            subcategory = self._extract_subcategory(provider_data)
            procurement_method = self._extract_procurement_method(provider_data)
            
            # Status padronizado
            status = 'active'  # ComprasNet sempre retorna licitações ativas
            
            # Entidades
            procuring_entity_id = str(provider_data.get('uasg', '')).strip()[:50] if provider_data.get('uasg') else None
            procuring_entity_name = str(opportunity.procuring_entity_name or '').strip()[:255] if opportunity.procuring_entity_name else None
            contracting_authority = procuring_entity_name
            
            # Informações de contato (ComprasNet não fornece estruturado)
            contact_info = self._build_contact_info(provider_data)
            
            # Documentos (ComprasNet não fornece documentos estruturados)
            documents = []
            
            # Informações adicionais com metadados robustos
            additional_info = self._build_additional_info(opportunity, provider_data)
            
            # 🏗️ MONTAR DATABASE OPPORTUNITY
            db_opportunity = DatabaseOpportunity(
                provider_name=self.provider_name,
                external_id=external_id,
                title=title,
                description=description,
                estimated_value=estimated_value,
                currency_code=currency_code,
                country_code=country_code,
                region_code=region_code,
                municipality=municipality,
                publication_date=publication_date,
                submission_deadline=submission_deadline,
                opening_date=opening_date,
                category=category,
                subcategory=subcategory,
                procurement_method=procurement_method,
                status=status,
                source_url=str(opportunity.source_url or '').strip()[:500] if opportunity.source_url else None,
                procuring_entity_id=procuring_entity_id,
                procuring_entity_name=procuring_entity_name,
                contracting_authority=contracting_authority,
                contact_info=contact_info,
                documents=documents,
                additional_info=additional_info
            )
            
            self.logger.debug(f"✅ ComprasNet opportunity {external_id} convertida para banco")
            return db_opportunity
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conversão de opportunity {getattr(opportunity, 'external_id', 'N/A')}: {e}")
            raise e
    
    def database_to_opportunity(self, db_data: Dict[str, Any]) -> OpportunityData:
        """
        Converte dados do banco para OpportunityData
        
        Args:
            db_data: Dicionário com dados do banco
            
        Returns:
            OpportunityData: Estrutura padronizada do provider
        """
        try:
            # Extrair informações adicionais
            additional_info = db_data.get('additional_info', {})
            
            # Criar OpportunityData a partir dos dados do banco
            opportunity = OpportunityData(
                external_id=db_data['external_id'],
                title=db_data['title'],
                description=db_data.get('description'),
                estimated_value=db_data.get('estimated_value'),
                currency_code=db_data.get('currency_code', 'BRL'),
                country_code=db_data.get('country_code', 'BR'),
                region_code=db_data.get('region_code'),
                municipality=db_data.get('municipality'),
                publication_date=db_data.get('publication_date'),
                submission_deadline=db_data.get('submission_deadline'),
                opening_date=db_data.get('opening_date'),
                procuring_entity_name=db_data.get('procuring_entity_name'),
                procuring_entity_id=db_data.get('procuring_entity_id'),
                source_url=db_data.get('source_url'),
                provider_specific_data=additional_info
            )
            
            # Adicionar provider_name
            opportunity.provider_name = self.provider_name
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conversão do banco para opportunity: {e}")
            raise e
    
    def validate_data(self, opportunity: OpportunityData) -> bool:
        """
        Valida se os dados estão no formato correto para o ComprasNet
        
        Args:
            opportunity: Dados a serem validados
            
        Returns:
            bool: True se válidos, False caso contrário
        """
        try:
            # Validações obrigatórias
            if not opportunity.external_id:
                self.logger.error("External ID é obrigatório")
                return False
            
            if not opportunity.title:
                self.logger.error("Título é obrigatório")
                return False
            
            # Validar provider_name
            if hasattr(opportunity, 'provider_name') and opportunity.provider_name != self.provider_name:
                self.logger.error(f"Provider name incorreto: esperado '{self.provider_name}', recebido '{opportunity.provider_name}'")
                return False
            
            # Validar valor estimado se presente
            if opportunity.estimated_value is not None:
                try:
                    float(opportunity.estimated_value)
                except (ValueError, TypeError):
                    self.logger.error(f"Valor estimado inválido: {opportunity.estimated_value}")
                    return False
            
            # Validar datas se presentes
            for date_field, date_value in [
                ('publication_date', opportunity.publication_date),
                ('submission_deadline', opportunity.submission_deadline),
                ('opening_date', opportunity.opening_date)
            ]:
                if date_value and not self._validate_date(date_value):
                    self.logger.error(f"Data inválida em {date_field}: {date_value}")
                return False
            
            self.logger.debug(f"✅ Dados válidos para opportunity {opportunity.external_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro na validação: {e}")
            return False 
    
    # 🔧 MÉTODOS AUXILIARES PRIVADOS
    
    def _validate_date(self, date_str: Optional[str]) -> Optional[str]:
        """Valida e normaliza formato de data"""
        if not date_str:
            return None
        
        try:
            # Tentar parsing de diferentes formatos
            date_str = str(date_str).strip()
            
            # Formato ISO (YYYY-MM-DD)
            if '-' in date_str and len(date_str) >= 10:
                datetime.strptime(date_str[:10], '%Y-%m-%d')
                return date_str[:10]
            
            # Formato brasileiro (DD/MM/YYYY)
            if '/' in date_str and len(date_str) >= 10:
                dt = datetime.strptime(date_str[:10], '%d/%m/%Y')
                return dt.strftime('%Y-%m-%d')
            
            return None
            
        except (ValueError, TypeError):
            return None
    
    def _extract_category(self, provider_data: Dict[str, Any]) -> Optional[str]:
        """Extrai categoria da licitação"""
        modality = provider_data.get('modality', '')
        if 'PREGAO' in str(modality).upper():
            return 'Pregão'
        elif 'CONCORRENCIA' in str(modality).upper():
            return 'Concorrência'
        elif 'TOMADA' in str(modality).upper():
            return 'Tomada de Preços'
        return 'Outros'
    
    def _extract_subcategory(self, provider_data: Dict[str, Any]) -> Optional[str]:
        """Extrai subcategoria da licitação"""
        modality = provider_data.get('modality', '')
        if 'ELETRONICO' in str(modality).upper():
            return 'Eletrônico'
        elif 'PRESENCIAL' in str(modality).upper():
            return 'Presencial'
        return None
    
    def _extract_procurement_method(self, provider_data: Dict[str, Any]) -> Optional[str]:
        """Extrai método de contratação"""
        return provider_data.get('modality', 'Pregão Eletrônico')[:255]
    
    def _build_contact_info(self, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Constrói informações de contato"""
        contact_info = {}
        
        if provider_data.get('telefone'):
            contact_info['telefone'] = str(provider_data['telefone']).strip()[:50]
        
        if provider_data.get('endereco'):
            contact_info['endereco'] = str(provider_data['endereco']).strip()[:500]
        
        return contact_info
    
    def _build_additional_info(self, opportunity: OpportunityData, provider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Constrói informações adicionais com metadados robustos"""
        additional_info = {
            # Metadados do sistema
            'fonte_original': 'ComprasNet',
            'scraping_version': provider_data.get('scraping_version', '2.0'),
            'extraction_timestamp': provider_data.get('extraction_timestamp'),
            
            # 🚫 Controle de salvamento
            'auto_save_disabled': True,
            'save_policy': 'on_user_access_only',
            'conversion_timestamp': datetime.now().isoformat(),
            
            # Dados específicos do ComprasNet
            'numero_licitacao': provider_data.get('numero', ''),
            'modalidade': provider_data.get('modality', ''),
            'modprp': provider_data.get('modprp', ''),
            'uasg': provider_data.get('uasg', ''),
            'uf_sigla': provider_data.get('uf_sigla', ''),
            'localizacao': provider_data.get('endereco', ''),
            'telefone': provider_data.get('telefone', ''),
            'edital_info': provider_data.get('edital_info', ''),
            'bid_params': provider_data.get('bid_params'),
            'block_number': provider_data.get('block_number'),
            
            # URLs e referências
            'url_consulta': opportunity.source_url or '',
            'source_url': provider_data.get('source_url', ''),
            
            # Dados de auditoria
            'raw_text_preview': str(provider_data.get('raw_text', ''))[:1000] if provider_data.get('raw_text') else '',
            'observacoes': 'Dados extraídos via scraping do ComprasNet - NÃO salvos automaticamente',
            'processamento_timestamp': datetime.now().isoformat()
        }
        
        # Filtrar valores None e vazios
        return {k: v for k, v in additional_info.items() if v is not None and v != ''} 