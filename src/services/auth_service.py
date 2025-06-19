"""
Service para operações de autenticação (COMPATIBILITY LAYER)
Mantém compatibilidade com código existente importando o service unificado
"""
import logging
from services.auth_service_unified import AuthService as UnifiedAuthService

logger = logging.getLogger(__name__)

class AuthService(UnifiedAuthService):
    """Service de autenticação (mantido para compatibilidade)
    
    Este arquivo existe apenas para manter compatibilidade com código existente.
    Toda funcionalidade foi movida para serviços modulares em services/auth/
    """
    
    def __init__(self):
        """Inicializar usando o service unificado"""
        super().__init__() 