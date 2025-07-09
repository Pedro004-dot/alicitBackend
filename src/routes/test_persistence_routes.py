"""
🏗️ ROTAS DE TESTE PARA SISTEMA DE PERSISTÊNCIA ESCALÁVEL
Valida DataMappers, PersistenceService e integração PNCP + ComprasNet
"""

import logging
from flask import Blueprint, jsonify, current_app, request
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def create_test_persistence_routes() -> Blueprint:
    """Criar blueprint com rotas de teste para o sistema de persistência"""
    
    # Verificar se está em modo de desenvolvimento
    debug_mode = True  # Para desenvolvimento sempre ativo
    
    if not debug_mode:
        logger.info("Test persistence routes disabled in production")
        return None
    
    logger.info("Test persistence routes enabled")
    test_bp = Blueprint('test_persistence', __name__, url_prefix='/api/test/persistence')
    
    @test_bp.route('/test-quick-fix')
    def test_quick_fix():
        """Teste rápido para verificar se a correção do provider_name funcionou"""
        try:
            # Import tardio para evitar dependência circular
            from adapters.pncp_adapter import PNCPAdapter
            from adapters.mappers.pncp_data_mapper import PNCPDataMapper
            
            # Testar PNCPAdapter
            pncp_config = {
                'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
                'timeout': 30,
                'max_results': 1000
            }
            adapter = PNCPAdapter(pncp_config)
            provider_name = adapter.get_provider_name()
            
            # Testar PNCPDataMapper
            mapper = PNCPDataMapper()
            mapper_provider = mapper.provider_name()
            
            # Criar OpportunityData de teste
            licitacao_teste = {
                'numeroControlePNCP': 'test-12345',
                'objetoCompra': 'Teste de licitação para validação',
                'modalidadeNome': 'Pregão Eletrônico',
                'orgaoEntidade': {
                    'razaoSocial': 'Órgão de Teste',
                    'cnpj': '12345678000190'
                },
                'unidadeOrgao': {
                    'ufSigla': 'SP',
                    'municipioNome': 'São Paulo',
                    'nomeUnidade': 'Unidade de Teste'
                }
            }
            
            # Converter para OpportunityData
            opportunity_data = adapter._convert_to_opportunity_data(licitacao_teste)
            
            # Testar se PersistenceService aceita agora
            try:
                from services.persistence_service import PersistenceService
                from config.database import get_db_manager
                
                db_manager = get_db_manager()
                persistence_service = PersistenceService()
                
                # Tentar salvar
                save_result = persistence_service.save_opportunity(opportunity_data)
                persistence_test = "success" if save_result else "failed"
                persistence_error = None
                
            except Exception as pe:
                persistence_test = "error"
                persistence_error = str(pe)
            
            return jsonify({
                'status': 'success',
                'adapter_provider_name': provider_name,
                'mapper_provider_name': mapper_provider,
                'provider_names_match': provider_name == mapper_provider,
                'opportunity_has_provider_name': hasattr(opportunity_data, 'provider_name'),
                'opportunity_provider_name': getattr(opportunity_data, 'provider_name', None),
                'persistence_test': persistence_test,
                'persistence_error': persistence_error,
                'correction_status': 'Provider name consistency fixed' if provider_name == mapper_provider else 'Still inconsistent'
            })
            
        except Exception as e:
            logger.error(f"Erro no teste rápido: {e}")
            return jsonify({'error': str(e)}), 500
    
    @test_bp.route('/debug-persistence')
    def debug_persistence():
        """Diagnóstico detalhado do sistema de persistência"""
        try:
            # Import tardio
            from adapters.pncp_adapter import PNCPAdapter
            from interfaces.data_mapper import DataMapperRegistry
            from services.persistence_service import PersistenceService
            
            # 1. Testar adapter
            pncp_config = {
                'api_base_url': 'https://pncp.gov.br/api/consulta/v1',
                'timeout': 30,
                'max_results': 1000
            }
            adapter = PNCPAdapter(pncp_config)
            adapter_provider = adapter.get_provider_name()
            
            # 2. Testar registry
            registry = DataMapperRegistry()
            registered_mappers = registry.list_providers()
            
            # 3. Testar se mapper existe
            mapper_exists = registry.has_mapper(adapter_provider)
            mapper_instance = registry.get_mapper(adapter_provider) if mapper_exists else None
            
            # 4. Criar dados de teste
            licitacao_teste = {
                'numeroControlePNCP': 'debug-test-456',
                'objetoCompra': 'Teste detalhado do sistema de persistência',
                'modalidadeNome': 'Pregão Eletrônico',
                'orgaoEntidade': {
                    'razaoSocial': 'Órgão Debug',
                    'cnpj': '98765432000111'
                },
                'unidadeOrgao': {
                    'ufSigla': 'RJ',
                    'municipioNome': 'Rio de Janeiro',
                    'nomeUnidade': 'Unidade Debug'
                }
            }
            
            # 5. Converter para OpportunityData
            opportunity_data = adapter._convert_to_opportunity_data(licitacao_teste)
            
            # 6. Validar dados
            validation_result = None
            validation_error = None
            
            if mapper_instance:
                try:
                    validation_result = mapper_instance.validate_data(opportunity_data)
                except Exception as ve:
                    validation_error = str(ve)
            
            # 7. Tentar conversão para banco
            database_conversion = None
            conversion_error = None
            
            if mapper_instance and validation_result:
                try:
                    db_opportunity = mapper_instance.opportunity_to_database(opportunity_data)
                    database_conversion = "success"
                except Exception as ce:
                    database_conversion = "failed"
                    conversion_error = str(ce)
            
            # 8. Tentar salvar
            save_result = None
            save_error = None
            
            try:
                persistence_service = PersistenceService()
                save_result = persistence_service.save_opportunity(opportunity_data)
            except Exception as se:
                save_error = str(se)
            
            return jsonify({
                'adapter': {
                    'provider_name': adapter_provider,
                    'class': adapter.__class__.__name__
                },
                'registry': {
                    'registered_mappers': registered_mappers,
                    'mapper_exists_for_adapter': mapper_exists,
                    'mapper_class': mapper_instance.__class__.__name__ if mapper_instance else None
                },
                'opportunity_data': {
                    'external_id': opportunity_data.external_id,
                    'has_provider_name': hasattr(opportunity_data, 'provider_name'),
                    'provider_name': getattr(opportunity_data, 'provider_name', None),
                    'title': opportunity_data.title
                },
                'validation': {
                    'result': validation_result,
                    'error': validation_error
                },
                'database_conversion': {
                    'result': database_conversion,
                    'error': conversion_error
                },
                'persistence': {
                    'save_result': save_result,
                    'save_error': save_error
                },
                'diagnosis': 'Diagnóstico completo do fluxo de persistência'
            })
            
        except Exception as e:
            logger.error(f"Erro no diagnóstico: {e}")
            return jsonify({'error': str(e)}), 500
    
    # 🌐 NOVO: Teste específico para ComprasNet
    @test_bp.route('/test-comprasnet')
    def test_comprasnet():
        """Teste específico do ComprasNetAdapter e ComprasNetDataMapper"""
        try:
            # Import dos componentes do ComprasNet
            from adapters.comprasnet_adapter import ComprasNetAdapter
            from adapters.mappers.comprasnet_data_mapper import ComprasNetDataMapper
            from interfaces.data_mapper import DataMapperRegistry
            from services.persistence_service import PersistenceService
            
            # 1. Testar ComprasNetAdapter
            adapter = ComprasNetAdapter()
            adapter_provider = adapter.get_provider_name()
            
            # 2. Testar ComprasNetDataMapper
            mapper = ComprasNetDataMapper()
            mapper_provider = mapper.provider_name()
            
            # 3. Verificar registro no registry
            from interfaces.data_mapper import data_mapper_registry
            mapper_registered = data_mapper_registry.has_mapper(adapter_provider)
            
            # 4. Fazer busca real no ComprasNet
            search_query = "software"  # Termo que geralmente retorna resultados
            search_filters = {"uf": "DF"}  # Filtrar por Distrito Federal para reduzir resultados
            
            # 5. Buscar licitações reais
            opportunities = adapter.search_opportunities(search_query, search_filters)
            
            # 6. Usar primeira licitação encontrada ou criar dados de fallback
            if opportunities:
                opportunity_data = opportunities[0]
                search_result = f"Encontradas {len(opportunities)} licitações reais"
                logger.info(f"✅ ComprasNet retornou dados reais: {opportunity_data.title}")
            else:
                # Fallback: criar dados básicos se não encontrou nada
                from interfaces.procurement_data_source import OpportunityData
                from datetime import datetime, timedelta
                
                opportunity_data = OpportunityData(
                    external_id="comprasnet_fallback_test",
                    title="Teste ComprasNet - Fallback",
                    description="Dados de fallback para teste quando ComprasNet não retorna resultados",
                    estimated_value=0.0,
                    currency_code='BRL',
                    country_code='BR',
                    region_code='DF',
                    municipality='Brasília',
                    publication_date=datetime.now().strftime('%Y-%m-%d'),
                    submission_deadline=(datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                    procuring_entity_name="Teste - Fallback",
                    provider_specific_data={"fonte": "ComprasNet", "fallback": True}
                )
                opportunity_data.provider_name = adapter.get_provider_name()
                search_result = "Nenhuma licitação encontrada - usando dados de fallback"
            
            # 7. Validar dados
            validation_result = mapper.validate_data(opportunity_data)
            
            # 8. Converter para banco
            database_conversion = None
            conversion_error = None
            
            try:
                db_opportunity = mapper.opportunity_to_database(opportunity_data)
                database_conversion = "success"
            except Exception as ce:
                database_conversion = "failed"
                conversion_error = str(ce)
            
            # 9. Tentar salvar via PersistenceService
            save_result = None
            save_error = None
            
            try:
                persistence_service = PersistenceService()
                save_result = persistence_service.save_opportunity(opportunity_data)
            except Exception as se:
                save_error = str(se)
            
            return jsonify({
                'status': 'success',
                'search_info': {
                    'query': search_query,
                    'filters': search_filters,
                    'result': search_result,
                    'total_found': len(opportunities) if opportunities else 0
                },
                'comprasnet_adapter': {
                    'provider_name': adapter_provider,
                    'class': adapter.__class__.__name__
                },
                'comprasnet_mapper': {
                    'provider_name': mapper_provider,
                    'class': mapper.__class__.__name__,
                    'registered': mapper_registered
                },
                'provider_names_match': adapter_provider == mapper_provider,
                'opportunity_data': {
                    'external_id': opportunity_data.external_id if opportunity_data else None,
                    'title': opportunity_data.title if opportunity_data else None,
                    'provider_name': getattr(opportunity_data, 'provider_name', None) if opportunity_data else None,
                    'is_real_data': len(opportunities) > 0 if opportunities else False
                },
                'validation': {
                    'result': validation_result if opportunity_data else False
                },
                'database_conversion': {
                    'result': database_conversion,
                    'error': conversion_error
                },
                'persistence': {
                    'save_result': save_result,
                    'save_error': save_error
                },
                'test_conclusion': 'ComprasNet integration test completed with real data scraping'
            })
            
        except Exception as e:
            logger.error(f"Erro no teste ComprasNet: {e}")
            return jsonify({'error': str(e)}), 500
    
    @test_bp.route('/comprasnet-full-test', methods=['POST'])
    def test_comprasnet_full():
        """
        🧪 TESTE COMPLETO COMPRASNET
        Testa toda a cadeia: busca → salvamento → busca de itens → verificação no banco
        """
        try:
            data = request.get_json() or {}
            query = data.get('query', 'software')
            max_results = data.get('max_results', 2)
            
            logger.info(f"🧪 Iniciando teste completo ComprasNet com query: '{query}'")
            
            # ✅ ETAPA 1: Buscar licitações no ComprasNet
            logger.info("📋 ETAPA 1: Buscando licitações no ComprasNet...")
            
            from adapters.comprasnet_adapter import ComprasNetAdapter
            adapter = ComprasNetAdapter()
            
            # Buscar oportunidades
            opportunities = adapter.search_opportunities(query, {
                'max_results': max_results
            })
            
            step1_result = {
                'found_opportunities': len(opportunities),
                'opportunities': []
            }
            
            if not opportunities:
                return jsonify({
                    'success': False,
                    'message': 'Nenhuma licitação encontrada no ComprasNet',
                    'step1': step1_result
                }), 200
            
            # Preparar dados das oportunidades
            for opp in opportunities[:max_results]:
                opp_data = {
                    'external_id': opp.external_id,
                    'title': opp.title[:100] + '...' if len(opp.title) > 100 else opp.title,
                    'entity': opp.procuring_entity_name,
                    'estimated_value': opp.estimated_value,
                    'provider': opp.provider_name
                }
                step1_result['opportunities'].append(opp_data)
            
            logger.info(f"✅ ETAPA 1 concluída: {len(opportunities)} licitações encontradas")
            
            # ✅ ETAPA 2: Verificar salvamento automático
            logger.info("💾 ETAPA 2: Verificando salvamento no banco de dados...")
            
            step2_result = {
                'persistence_service_active': bool(adapter.persistence_service),
                'saved_opportunities': []
            }
            
            from services.persistence_service import get_persistence_service
            persistence_service = get_persistence_service()
            
            # Verificar se as licitações foram salvas
            saved_count = 0
            for opp in opportunities[:max_results]:
                saved_opp = persistence_service.get_opportunity('comprasnet', opp.external_id)
                if saved_opp:
                    saved_count += 1
                    step2_result['saved_opportunities'].append({
                        'external_id': saved_opp.external_id,
                        'saved_at': saved_opp.created_at.isoformat() if saved_opp.created_at else 'N/A',
                        'title': saved_opp.title[:50] + '...' if len(saved_opp.title) > 50 else saved_opp.title
                    })
            
            step2_result['saved_count'] = saved_count
            step2_result['success'] = saved_count > 0
            
            logger.info(f"✅ ETAPA 2 concluída: {saved_count}/{len(opportunities)} licitações salvas")
            
            # ✅ ETAPA 3: Testar busca de itens
            logger.info("🔍 ETAPA 3: Testando busca de itens das licitações...")
            
            step3_result = {
                'items_extraction_tests': []
            }
            
            # Testar busca de itens para cada licitação
            for opp in opportunities[:min(2, len(opportunities))]:  # Testar apenas as primeiras 2
                logger.info(f"🔍 Buscando itens para: {opp.external_id}")
                
                try:
                    items = adapter.get_opportunity_items(opp.external_id)
                    
                    test_result = {
                        'licitacao_id': opp.external_id,
                        'licitacao_title': opp.title[:50] + '...' if len(opp.title) > 50 else opp.title,
                        'items_found': len(items),
                        'success': len(items) > 0,
                        'items_sample': []
                    }
                    
                    # Adicionar amostra de itens
                    for item in items[:3]:  # Máximo 3 itens de exemplo
                        test_result['items_sample'].append({
                            'item_number': item.get('item_number', 'N/A'),
                            'description': item.get('description', '')[:100] + '...' if len(item.get('description', '')) > 100 else item.get('description', ''),
                            'quantity': item.get('quantity', 0),
                            'unit': item.get('unit', 'N/A'),
                            'category': item.get('category', 'N/A')
                        })
                    
                    step3_result['items_extraction_tests'].append(test_result)
                    
                except Exception as e:
                    step3_result['items_extraction_tests'].append({
                        'licitacao_id': opp.external_id,
                        'success': False,
                        'error': str(e)
                    })
            
            total_items = sum(test['items_found'] for test in step3_result['items_extraction_tests'] if test.get('items_found'))
            step3_result['total_items_found'] = total_items
            step3_result['success'] = total_items > 0
            
            logger.info(f"✅ ETAPA 3 concluída: {total_items} itens encontrados no total")
            
            # ✅ ETAPA 4: Verificar dados específicos do ComprasNet
            logger.info("🔧 ETAPA 4: Verificando dados específicos do ComprasNet...")
            
            step4_result = {
                'provider_metadata': adapter.get_provider_metadata(),
                'supported_filters': adapter.get_supported_filters(),
                'openai_service_active': bool(adapter.openai_service),
                'cache_status': adapter._is_cache_valid(),
                'adapter_config': {
                    'max_pages': adapter.max_pages,
                    'max_results': adapter.max_results,
                    'timeout': adapter.timeout
                }
            }
            
            logger.info("✅ ETAPA 4 concluída: Metadados coletados")
            
            # 📊 RESULTADO FINAL
            overall_success = (
                step1_result['found_opportunities'] > 0 and
                step2_result['success'] and
                step3_result['success']
            )
            
            result = {
                'success': overall_success,
                'message': f"Teste completo ComprasNet {'✅ APROVADO' if overall_success else '❌ FALHOU'}",
                'summary': {
                    'licitacoes_encontradas': step1_result['found_opportunities'],
                    'licitacoes_salvas': step2_result['saved_count'],
                    'itens_encontrados': step3_result['total_items_found'],
                    'sinônimos_ativo': step4_result['openai_service_active']
                },
                'details': {
                    'step1_search': step1_result,
                    'step2_persistence': step2_result,
                    'step3_items': step3_result,
                    'step4_metadata': step4_result
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"🎯 TESTE COMPLETO FINALIZADO: {'✅ SUCESSO' if overall_success else '❌ FALHA'}")
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no teste completo ComprasNet: {e}")
            import traceback
            return jsonify({
                'success': False,
                'message': f'Erro no teste: {str(e)}',
                'error_details': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }), 500

    @test_bp.route('/comprasnet-items-test/<external_id>', methods=['GET'])
    def test_comprasnet_items_specific(external_id):
        """
        🔍 TESTE ESPECÍFICO DE ITENS
        Testa busca de itens para uma licitação específica do ComprasNet
        """
        try:
            logger.info(f"🔍 Testando busca de itens para licitação: {external_id}")
            
            from adapters.comprasnet_adapter import ComprasNetAdapter
            adapter = ComprasNetAdapter()
            
            # Buscar itens
            items = adapter.get_opportunity_items(external_id)
            
            # Preparar resultado detalhado
            result = {
                'success': len(items) > 0,
                'external_id': external_id,
                'items_found': len(items),
                'items': []
            }
            
            # Adicionar todos os itens encontrados
            for item in items:
                result['items'].append({
                    'item_number': item.get('item_number', 'N/A'),
                    'description': item.get('description', ''),
                    'quantity': item.get('quantity', 0),
                    'unit': item.get('unit', 'N/A'),
                    'external_id': item.get('external_id', ''),
                    'category': item.get('category', 'N/A'),
                    'material': item.get('material', 'N/A'),
                    'size': item.get('size', 'N/A'),
                    'sterility': item.get('sterility', 'N/A')
                })
            
            # Metadados do teste
            result['metadata'] = {
                'adapter_provider': adapter.get_provider_name(),
                'cache_valid': adapter._is_cache_valid(),
                'persistence_active': bool(adapter.persistence_service),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Teste de itens concluído: {len(items)} itens encontrados")
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"❌ Erro no teste de itens: {e}")
            return jsonify({
                'success': False,
                'external_id': external_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500
    
    @test_bp.route('/status')
    def get_status():
        """Status geral do sistema de persistência"""
        try:
            from interfaces.data_mapper import data_mapper_registry
            
            registered_providers = data_mapper_registry.list_providers()
            
            return jsonify({
                'status': 'active',
                'message': 'Sistema de persistência escalável ativo',
                'registered_mappers': registered_providers,
                'total_mappers': len(registered_providers),
                'supported_providers': ['pncp', 'comprasnet'],
                'architecture': 'Scalable persistence with Strategy Pattern'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @test_bp.route('/mappers')
    def list_mappers():
        """Lista todos os mappers registrados"""
        try:
            from interfaces.data_mapper import data_mapper_registry
            
            registered_providers = data_mapper_registry.list_providers()
            
            mapper_details = {}
            for provider in registered_providers:
                try:
                    mapper = data_mapper_registry.get_mapper(provider)
                    mapper_details[provider] = {
                        'class': mapper.__class__.__name__,
                        'module': mapper.__class__.__module__,
                        'provider_name': mapper.provider_name()
                    }
                except Exception as e:
                    mapper_details[provider] = {'error': str(e)}
            
            return jsonify({
                'registered_providers': registered_providers,
                'mapper_details': mapper_details,
                'total': len(registered_providers)
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @test_bp.route('/database-stats')
    def database_stats():
        """Estatísticas do banco de dados"""
        try:
            from config.database import get_db_manager
            
            db_manager = get_db_manager()
            
            # Query para estatísticas por provider (usando campos corretos da tabela licitacoes)
            query = """
            SELECT 
                provider_name,
                COUNT(*) as total_opportunities,
                COUNT(DISTINCT razao_social) as unique_entities,
                AVG(valor_total_estimado) as avg_value,
                MAX(updated_at) as last_update
            FROM licitacoes 
            WHERE provider_name IS NOT NULL
            GROUP BY provider_name
            ORDER BY total_opportunities DESC
            """
            
            result = db_manager.execute_query(query)
            
            return jsonify({
                'database_stats': result,
                'query_executed': query,
                'status': 'success'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return test_bp 