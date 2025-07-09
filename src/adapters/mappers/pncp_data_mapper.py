"""
DataMapper específico para PNCP
Implementa conversões otimizadas entre OpportunityData e formato do banco
🚫 SALVAMENTO AUTOMÁTICO DESATIVADO - Só salva quando usuário acessa licitação
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from interfaces.data_mapper import BaseDataMapper, DatabaseOpportunity
from interfaces.procurement_data_source import OpportunityData


class PNCPDataMapper(BaseDataMapper):
    """
    Mapper específico para dados do PNCP
    
    🚫 SALVAMENTO AUTOMÁTICO DESATIVADO
    - Busca e converte dados sem salvar automaticamente
    - Só persiste quando usuário acessar especificamente uma licitação
    - Evita consumo excessivo de recursos e banco inflado
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚫 PNCPDataMapper inicializado - SALVAMENTO AUTOMÁTICO DESATIVADO")
    
    def provider_name(self) -> str:
        return "pncp"
    
    def should_auto_save(self) -> bool:
        """
        🚫 SALVAMENTO AUTOMÁTICO DESATIVADO
        
        Returns:
            bool: False - nunca salvar automaticamente
        """
        return False
    
    def opportunity_to_database(self, opportunity: OpportunityData) -> DatabaseOpportunity:
        """
        🔄 Converte OpportunityData do PNCP para formato do banco
        
        ⚠️ IMPORTANTE: Esta conversão é feita mas NÃO É SALVA automaticamente.
        O salvamento só ocorre quando o usuário acessar especificamente a licitação.
        
        Args:
            opportunity: Dados da oportunidade do PNCP
            
        Returns:
            DatabaseOpportunity: Dados formatados (mas não salvos)
        """
        try:
            # Log importante sobre não salvamento
            self.logger.debug(f"🔄 Convertendo PNCP {opportunity.external_id} (NÃO será salvo automaticamente)")
            
            # Extrair informações adicionais específicas do PNCP
            additional_info = opportunity.additional_info or {}
            
            # Processar informações do órgão (específico PNCP)
            contracting_authority = self._extract_contracting_authority(opportunity, additional_info)
            
            # Processar contato (específico PNCP)
            contact_info = self._extract_contact_info(opportunity, additional_info)
            
            # Processar documentos (específico PNCP)
            documents = self._extract_documents(opportunity, additional_info)
            
            # Processar datas específicas do PNCP
            publication_date = self._format_pncp_date(opportunity.publication_date)
            submission_deadline = self._format_pncp_date(opportunity.submission_deadline)
            opening_date = self._format_pncp_date(opportunity.opening_date)
            
            # Processar categoria específica do PNCP
            category, subcategory = self._extract_pncp_categories(opportunity, additional_info)
            
            # Preparar informações adicionais do PNCP
            pncp_additional_info = self._prepare_pncp_additional_info(opportunity, additional_info)
            
            db_opportunity = DatabaseOpportunity(
                # Identificação
                external_id=opportunity.external_id,
                provider_name=self.provider_name(),
                title=opportunity.title,
                description=opportunity.description,
                
                # Valores financeiros
                estimated_value=self._clean_monetary_value(opportunity.estimated_value),
                currency_code=opportunity.currency_code,
                
                # Localização
                country_code=opportunity.country_code,
                region_code=opportunity.region_code,
                municipality=opportunity.municipality,
                
                # Temporal
                publication_date=publication_date,
                submission_deadline=submission_deadline,
                opening_date=opening_date,
                
                # Classificação
                category=category,
                subcategory=subcategory,
                procurement_method=self._map_procurement_method(opportunity, additional_info),
                
                # Status e organização
                status=self._map_opportunity_status(opportunity.status),
                contracting_authority=contracting_authority,
                contact_info=contact_info,
                
                # Metadados
                source_url=opportunity.source_url,
                documents=documents,
                additional_info=pncp_additional_info,
                
                # Auditoria
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            self.logger.debug(f"✅ PNCP opportunity {opportunity.external_id} convertida (pronta para salvamento sob demanda)")
            return db_opportunity
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conversão PNCP opportunity: {e}")
            raise
    
    def database_to_opportunity(self, db_data: Dict[str, Any]) -> OpportunityData:
        """
        Converte dados do banco para OpportunityData do PNCP
        """
        try:
            # Reconstruir additional_info específico do PNCP
            additional_info = db_data.get('additional_info', {})
            
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
                category=db_data.get('category'),
                status=db_data.get('status', 'active'),
                source_url=db_data.get('source_url'),
                provider_name=self.provider_name(),
                contracting_authority=db_data.get('contracting_authority'),
                contact_info=db_data.get('contact_info'),
                documents=db_data.get('documents'),
                additional_info=additional_info
            )
            
            self.logger.debug(f"✅ Convertido dados do banco para PNCP opportunity {db_data['external_id']}")
            return opportunity
            
        except Exception as e:
            self.logger.error(f"❌ Erro na conversão do banco para PNCP opportunity: {e}")
            raise
    
    def validate_data(self, opportunity: OpportunityData) -> bool:
        """
        Valida dados específicos do PNCP
        """
        try:
            # Validações obrigatórias para PNCP
            if not opportunity.external_id:
                self.logger.warning("PNCP opportunity missing external_id")
                return False
            
            if not opportunity.title:
                self.logger.warning(f"PNCP opportunity {opportunity.external_id} missing title")
                return False
            
            # Validação de formato do ID do PNCP
            # O numeroControlePNCP pode conter hífens, barras e letras. Aceitamos qualquer string não vazia.
            # Se precisar de validações adicionais, implementar regex aqui.
            
            # Validação de provider_name
            if opportunity.provider_name and opportunity.provider_name != self.provider_name():
                self.logger.warning(f"Provider name mismatch: expected {self.provider_name()}, got {opportunity.provider_name}")
                return False
            
            # Validações opcionais mas recomendadas
            if opportunity.estimated_value is not None and opportunity.estimated_value < 0:
                self.logger.warning(f"PNCP opportunity {opportunity.external_id} has negative estimated_value")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating PNCP opportunity: {e}")
            return False
    
    def _extract_contracting_authority(self, opportunity: OpportunityData, additional_info: Dict) -> Optional[str]:
        """Extrai e formata órgão contratante específico do PNCP"""
        # Priorizar contracting_authority direto
        if opportunity.contracting_authority:
            return opportunity.contracting_authority
        
        # Buscar em additional_info
        auth_fields = ['orgao', 'unidadeOrgao', 'razaoSocial', 'nomeOrgao']
        for field in auth_fields:
            if field in additional_info and additional_info[field]:
                return str(additional_info[field])
        
        return None
    
    def _extract_contact_info(self, opportunity: OpportunityData, additional_info: Dict) -> Optional[Dict[str, Any]]:
        """Extrai informações de contato específicas do PNCP"""
        contact = {}
        
        # Informações diretas
        if opportunity.contact_info:
            contact.update(opportunity.contact_info)
        
        # Informações específicas do PNCP em additional_info
        contact_fields = {
            'email': ['email', 'emailContato'],
            'telefone': ['telefone', 'fone'],
            'endereco': ['endereco', 'enderecoCompleto'],
            'responsavel': ['responsavel', 'nomeResponsavel']
        }
        
        for key, fields in contact_fields.items():
            for field in fields:
                if field in additional_info and additional_info[field]:
                    contact[key] = additional_info[field]
                    break
        
        return contact if contact else None
    
    def _extract_documents(self, opportunity: OpportunityData, additional_info: Dict) -> Optional[List[Dict[str, Any]]]:
        """Extrai documentos específicos do PNCP"""
        documents = []
        
        # Documentos diretos
        if opportunity.documents:
            documents.extend(opportunity.documents)
        
        # Documentos específicos do PNCP
        if 'documentos' in additional_info:
            pncp_docs = additional_info['documentos']
            if isinstance(pncp_docs, list):
                documents.extend(pncp_docs)
        
        return documents if documents else None
    
    def _format_pncp_date(self, date_value: Optional[str]) -> Optional[str]:
        """Formata datas específicas do PNCP para ISO format"""
        if not date_value:
            return None
        
        try:
            # Se já está no formato ISO, retornar
            if 'T' in date_value:
                return date_value
            
            # Tentar formatos comuns do PNCP
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_value, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # Se não conseguiu converter, retornar original
            return date_value
            
        except Exception:
            return date_value
    
    def _clean_monetary_value(self, value: Optional[float]) -> Optional[float]:
        """Limpa e valida valores monetários do PNCP"""
        if value is None:
            return None
        
        try:
            cleaned_value = float(value)
            return cleaned_value if cleaned_value >= 0 else None
        except (ValueError, TypeError):
            return None
    
    def _extract_pncp_categories(self, opportunity: OpportunityData, additional_info: Dict) -> tuple:
        """Extrai categorias específicas do PNCP"""
        category = opportunity.category
        subcategory = None
        
        # Buscar em additional_info campos específicos do PNCP
        if 'codigoSubGrupo' in additional_info:
            subcategory = additional_info['codigoSubGrupo']
        
        if 'nomeGrupo' in additional_info and not category:
            category = additional_info['nomeGrupo']
        
        return category, subcategory
    
    def _map_procurement_method(self, opportunity: OpportunityData, additional_info: Dict) -> Optional[str]:
        """Mapeia método de contratação específico do PNCP"""
        # Buscar em campos específicos do PNCP
        method_fields = ['modalidade', 'tipoContratacao', 'procedimento']
        
        for field in method_fields:
            if field in additional_info and additional_info[field]:
                return str(additional_info[field])
        
        return None
    
    def _map_opportunity_status(self, status: Optional[str]) -> str:
        """Mapeia status do PNCP para formato padronizado"""
        if not status:
            return 'active'
        
        status_lower = status.lower()
        
        # Mapeamento específico do PNCP
        status_mapping = {
            'em andamento': 'active',
            'publicado': 'active',
            'encerrado': 'closed',
            'cancelado': 'cancelled',
            'suspenso': 'suspended',
            'homologado': 'awarded'
        }
        
        return status_mapping.get(status_lower, status)
    
    def _prepare_pncp_additional_info(self, opportunity: OpportunityData, additional_info: Dict) -> Dict[str, Any]:
        """Prepara informações adicionais específicas do PNCP"""
        pncp_info = self.prepare_additional_info(opportunity)
        
        # Adicionar timestamp de não-salvamento
        pncp_info['auto_save_disabled'] = True
        pncp_info['save_policy'] = 'on_user_access_only'
        pncp_info['conversion_timestamp'] = datetime.now().isoformat()
        
        # Adicionar campos específicos do PNCP que devem ser preservados
        pncp_specific_fields = [
            'numeroControlePNCP', 'linkSistemaOrigem', 'codigoSubGrupo',
            'nomeGrupo', 'modalidade', 'situacao', 'orgao', 'unidadeOrgao'
        ]
        
        for field in pncp_specific_fields:
            if field in additional_info:
                pncp_info[f'pncp_{field}'] = additional_info[field]
        
        return pncp_info 