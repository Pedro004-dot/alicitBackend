"""
🏗️ Inicializador de DataMappers
Auto-registro de mappers para arquitetura escalável
"""

import logging

logger = logging.getLogger(__name__)

def initialize_mappers():
    """
    Inicializa e registra todos os DataMappers disponíveis
    """
    try:
        from interfaces.data_mapper import data_mapper_registry
        
        # Registrar PNCPDataMapper
        try:
            from .pncp_data_mapper import PNCPDataMapper
            data_mapper_registry.register_mapper("pncp", PNCPDataMapper())
            logger.info("✅ PNCPDataMapper registrado na instância global")
        except ImportError as e:
            logger.warning(f"⚠️ Não foi possível registrar PNCPDataMapper: {e}")
        
        # 🌐 NOVO: Registrar ComprasNetDataMapper
        try:
            from .comprasnet_data_mapper import ComprasNetDataMapper
            data_mapper_registry.register_mapper("comprasnet", ComprasNetDataMapper())
            logger.info("✅ ComprasNetDataMapper registrado na instância global")
        except ImportError as e:
            logger.warning(f"⚠️ Não foi possível registrar ComprasNetDataMapper: {e}")
        
        # Listar mappers registrados
        registered = data_mapper_registry.list_providers()
        logger.info(f"🏗️ DataMappers registrados: {registered}")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização de DataMappers: {e}")

# Auto-registro na importação do módulo
initialize_mappers() 