"""
Company Service
Lógica de negócio para operações com empresas
Usa repository padronizado para acesso a dados
"""
import json
import logging
from typing import List, Dict, Any, Optional
from repositories.company_repository import CompanyRepository
from config.database import db_manager

logger = logging.getLogger(__name__)

class CompanyService:
    """
    Service para lógica de negócio de empresas
    PADRONIZADO: Usa CompanyRepository para acesso a dados
    """
    
    def __init__(self):
        self.company_repo = CompanyRepository(db_manager)
    
    def get_all_companies(self, limit: Optional[int] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Buscar todas as empresas com formatação para frontend
        Se user_id for fornecido, filtra apenas empresas do usuário
        """
        try:
            if user_id:
                companies = self.company_repo.find_by_user_id(user_id, limit=limit)
            else:
                companies = self.company_repo.find_all(limit=limit)
            return self._format_companies_for_frontend(companies)
        except Exception as e:
            logger.error(f"Erro ao buscar empresas: {e}")
            return []
    
    def get_company_by_id(self, company_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Buscar empresa por ID com formatação"""
        try:
            if user_id:
                company = self.company_repo.find_by_id_and_user(company_id, user_id)
            else:
                company = self.company_repo.find_by_id(company_id)
            
            if company:
                return self._format_company_for_frontend(company)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar empresa {company_id}: {e}")
            return None
    
    def get_company_by_cnpj(self, cnpj: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Buscar empresa por CNPJ"""
        try:
            if user_id:
                company = self.company_repo.find_by_cnpj_and_user(cnpj, user_id)
            else:
                company = self.company_repo.find_by_cnpj(cnpj)
            
            if company:
                return self._format_company_for_frontend(company)
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar empresa por CNPJ {cnpj}: {e}")
            return None
    
    def search_companies_by_name(self, search_term: str, limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar empresas por nome"""
        try:
            companies = self.company_repo.search_by_name(search_term, limit, user_id=user_id)
            return self._format_companies_for_frontend(companies)
        except Exception as e:
            logger.error(f"Erro ao buscar empresas por nome '{search_term}': {e}")
            return []
    
    def search_companies_by_products(self, products: List[str], limit: int = 50, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Buscar empresas por produtos/serviços"""
        try:
            companies = self.company_repo.search_by_products(products, limit, user_id=user_id)
            return self._format_companies_for_frontend(companies)
        except Exception as e:
            logger.error(f"Erro ao buscar empresas por produtos {products}: {e}")
            return []
    
    def create_company(self, company_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Criar nova empresa com validação de negócio
        """
        try:
            # 🔀 COMPATIBILIDADE: Converter 'palavras_chave' para 'produtos' se o campo antigo for enviado
            if 'palavras_chave' in company_data:
                logger.warning("Campo 'palavras_chave' obsoleto detectado na requisição. Convertendo para 'produtos'.")
                if 'produtos' not in company_data: # Não sobrescrever se 'produtos' já existir
                    company_data['produtos'] = company_data['palavras_chave']
                del company_data['palavras_chave']

            # Validações de negócio
            self._validate_company_data(company_data)
            
            # Adicionar user_id se fornecido
            if user_id:
                company_data['user_id'] = user_id
            
            # Verificar se CNPJ já existe (se fornecido)
            if company_data.get('cnpj'):
                # Se temos user_id, verificar apenas para o usuário
                if user_id:
                    existing = self.company_repo.find_by_cnpj_and_user(company_data['cnpj'], user_id)
                else:
                    existing = self.company_repo.find_by_cnpj(company_data['cnpj'])
                
                if existing:
                    raise ValueError(f"CNPJ {company_data['cnpj']} já está cadastrado")
            
            # Processar produtos
            if 'produtos' in company_data and isinstance(company_data['produtos'], list):
                company_data['produtos'] = json.dumps(company_data['produtos'])
            
            # Criar empresa
            created_company = self.company_repo.create(company_data)
            
            logger.info(f"Empresa criada: {created_company['id']} - {created_company['nome_fantasia']}")
            
            return {
                'success': True,
                'message': 'Empresa criada com sucesso',
                'data': self._format_company_for_frontend(created_company)
            }
            
        except ValueError as e:
            logger.warning(f"Erro de validação ao criar empresa: {e}")
            return {
                'success': False,
                'message': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Erro ao criar empresa: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def update_company(self, company_id: str, company_data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Atualizar empresa existente com validação
        """
        try:
            # 🔀 COMPATIBILIDADE: Converter 'palavras_chave' para 'produtos' se o campo antigo for enviado
            if 'palavras_chave' in company_data:
                logger.warning("Campo 'palavras_chave' obsoleto detectado na requisição. Convertendo para 'produtos'.")
                if 'produtos' not in company_data: # Não sobrescrever se 'produtos' já existir
                    company_data['produtos'] = company_data['palavras_chave']
                del company_data['palavras_chave']

            # Verificar se empresa existe e pertence ao usuário
            if user_id:
                existing_company = self.company_repo.find_by_id_and_user(company_id, user_id)
                if not existing_company:
                    return {
                        'success': False,
                        'message': 'Empresa não encontrada ou não pertence ao usuário',
                        'data': None
                    }
            else:
                if not self.company_repo.exists(company_id):
                    return {
                        'success': False,
                        'message': 'Empresa não encontrada',
                        'data': None
                    }
            
            # Validações de negócio
            self._validate_company_data(company_data, is_update=True)
            
            # Verificar CNPJ duplicado (se alterado)
            if company_data.get('cnpj'):
                if user_id:
                    existing = self.company_repo.find_by_cnpj_and_user(company_data['cnpj'], user_id)
                else:
                    existing = self.company_repo.find_by_cnpj(company_data['cnpj'])
                
                if existing and existing['id'] != company_id:
                    raise ValueError(f"CNPJ {company_data['cnpj']} já está em uso por outra empresa")
            
            # Processar produtos
            if 'produtos' in company_data and isinstance(company_data['produtos'], list):
                company_data['produtos'] = json.dumps(company_data['produtos'])
            
            # Atualizar empresa
            updated_company = self.company_repo.update(company_id, company_data)
            
            if updated_company:
                logger.info(f"Empresa atualizada: {company_id}")
                return {
                    'success': True,
                    'message': 'Empresa atualizada com sucesso',
                    'data': self._format_company_for_frontend(updated_company)
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao atualizar empresa',
                    'data': None
                }
                
        except ValueError as e:
            logger.warning(f"Erro de validação ao atualizar empresa {company_id}: {e}")
            return {
                'success': False,
                'message': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Erro ao atualizar empresa {company_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def delete_company(self, company_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Deletar empresa e dependências relacionadas
        """
        try:
            # Verificar se empresa existe e pertence ao usuário
            if user_id:
                company = self.company_repo.find_by_id_and_user(company_id, user_id)
                if not company:
                    return {
                        'success': False,
                        'message': 'Empresa não encontrada ou não pertence ao usuário',
                        'data': None
                    }
            else:
                company = self.company_repo.find_by_id(company_id)
                if not company:
                    return {
                        'success': False,
                        'message': 'Empresa não encontrada',
                        'data': None
                    }
            
            # Deletar matches relacionados primeiro (cascade)
            deleted_matches = self._delete_company_matches(company_id)
            
            # Deletar empresa
            success = self.company_repo.delete(company_id)
            
            if success:
                logger.info(f"Empresa deletada: {company_id} ({deleted_matches} matches removidos)")
                return {
                    'success': True,
                    'message': 'Empresa deletada com sucesso',
                    'data': {
                        'deleted_matches': deleted_matches,
                        'company_name': company['nome_fantasia']
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'Falha ao deletar empresa',
                    'data': None
                }
                
        except Exception as e:
            logger.error(f"Erro ao deletar empresa {company_id}: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def get_companies_statistics(self) -> Dict[str, Any]:
        """Obter estatísticas das empresas"""
        try:
            return self.company_repo.get_companies_statistics()
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de empresas: {e}")
            return {}
    
    def bulk_import_companies(self, companies_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Importar múltiplas empresas em lote
        """
        try:
            # Validar todas as empresas antes de inserir
            validated_companies = []
            errors = []
            
            for i, company_data in enumerate(companies_data):
                try:
                    self._validate_company_data(company_data)
                    
                    # Processar produtos
                    if 'produtos' in company_data and isinstance(company_data['produtos'], list):
                        company_data['produtos'] = json.dumps(company_data['produtos'])
                    
                    validated_companies.append(company_data)
                except Exception as e:
                    errors.append(f"Linha {i+1}: {str(e)}")
            
            if errors:
                return {
                    'success': False,
                    'message': 'Erros de validação encontrados',
                    'data': {'errors': errors}
                }
            
            # Inserir empresas em lote
            created_ids = self.company_repo.bulk_create(validated_companies)
            
            logger.info(f"Importação em lote: {len(created_ids)} empresas criadas")
            
            return {
                'success': True,
                'message': f'{len(created_ids)} empresas importadas com sucesso',
                'data': {
                    'total_imported': len(created_ids),
                    'company_ids': created_ids
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na importação em lote: {e}")
            return {
                'success': False,
                'message': 'Erro interno do servidor',
                'data': None
            }
    
    def _validate_company_data(self, data: Dict[str, Any], is_update: bool = False):
        """Validações de negócio para dados de empresa"""
        required_fields = ['nome_fantasia', 'razao_social', 'descricao_servicos_produtos']
        
        if not is_update:  # Para criação, todos os campos são obrigatórios
            for field in required_fields:
                if not data.get(field) or not data[field].strip():
                    raise ValueError(f'Campo obrigatório ausente ou vazio: {field}')
        
        # Validação de CNPJ (se fornecido)
        cnpj = data.get('cnpj')
        if cnpj and not self._is_valid_cnpj_format(cnpj):
            raise ValueError('Formato de CNPJ inválido')
    
    def _is_valid_cnpj_format(self, cnpj: str) -> bool:
        """Validação básica do formato de CNPJ"""
        # Remove caracteres não numéricos
        cnpj_numbers = ''.join(filter(str.isdigit, cnpj))
        return len(cnpj_numbers) == 14
    
    def _delete_company_matches(self, company_id: str) -> int:
        """Deletar matches da empresa (usando query direta)"""
        try:
            command = "DELETE FROM matches WHERE empresa_id = %s"
            return self.company_repo.execute_custom_command(command, (company_id,))
        except Exception as e:
            logger.error(f"Erro ao deletar matches da empresa {company_id}: {e}")
            return 0
    
    def _format_company_for_frontend(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Formatar empresa individual para frontend"""
        # Processar produtos JSON (que podem vir como string)
        produtos = company.get('produtos')
        if isinstance(produtos, str):
            try:
                produtos = json.loads(produtos)
            except json.JSONDecodeError:
                produtos = []
        
        return {
            'id': str(company['id']),
            'nome_fantasia': company.get('nome_fantasia', ''),
            'razao_social': company.get('razao_social', ''),
            'cnpj': company.get('cnpj', ''),
            'descricao_servicos_produtos': company.get('descricao_servicos_produtos', ''),
            'produtos': produtos if produtos else [],
            'setor_atuacao': company.get('setor_atuacao', ''),
            'created_at': company.get('created_at').isoformat() if company.get('created_at') else None,
            'updated_at': company.get('updated_at').isoformat() if company.get('updated_at') else None
        }
    
    def _format_companies_for_frontend(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formatar lista de empresas para frontend"""
        return [self._format_company_for_frontend(company) for company in companies] 