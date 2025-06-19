"""
Controller para operações de autenticação (COMPATIBILITY LAYER)
Mantém compatibilidade com código existente importando o controller unificado
"""
import logging
from controllers.auth_controller_unified import AuthController as UnifiedAuthController

logger = logging.getLogger(__name__)

class AuthController(UnifiedAuthController):
    """Controller de autenticação (mantido para compatibilidade)
    
    Este arquivo existe apenas para manter compatibilidade com código existente.
    Toda funcionalidade foi movida para controllers modulares em controllers/auth/
    """
    
    def __init__(self):
        """Inicializar usando o controller unificado"""
        super().__init__()
    # Todos os métodos são herdados do UnifiedAuthController 