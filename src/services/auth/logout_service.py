"""
Service para operações de logout e gestão de sessões
Sistema multi-tenant com controle de sessões por dispositivo
"""
import logging
from datetime import datetime
from typing import Dict, List, Any
from .base_auth_service import BaseAuthService
from exceptions.api_exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)

class LogoutService(BaseAuthService):
    """Service para gerenciar logout e sessões de usuários"""
    
    def logout_session(self, jti: str) -> None:
        """Fazer logout de uma sessão específica"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_sessions 
                        SET revoked_at = CURRENT_TIMESTAMP
                        WHERE jti = %s AND revoked_at IS NULL
                    """, (jti,))
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"Erro ao fazer logout da sessão: {e}")
            raise DatabaseError("Erro interno ao fazer logout")
    
    def logout_all_sessions(self, user_id: str) -> Dict[str, int]:
        """Fazer logout de todas as sessões do usuário"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Contar sessões ativas
                    cur.execute("""
                        SELECT COUNT(*) FROM user_sessions 
                        WHERE user_id = %s AND revoked_at IS NULL
                    """, (user_id,))
                    sessions_count = cur.fetchone()[0]
                    
                    # Revogar todas as sessões
                    cur.execute("""
                        UPDATE user_sessions 
                        SET revoked_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND revoked_at IS NULL
                    """, (user_id,))
                    conn.commit()
            
            return {'sessions_revoked': sessions_count}
            
        except Exception as e:
            logger.error(f"Erro ao fazer logout de todas sessões: {e}")
            raise DatabaseError("Erro interno ao fazer logout")
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Listar sessões ativas do usuário"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT jti, device_info, ip_address, issued_at, 
                               last_used_at, expires_at
                        FROM user_sessions 
                        WHERE user_id = %s AND revoked_at IS NULL 
                        AND expires_at > CURRENT_TIMESTAMP
                        ORDER BY last_used_at DESC
                    """, (user_id,))
                    
                    sessions = []
                    for row in cur.fetchall():
                        # Parse device_info se for dict
                        device_info = row[1] if isinstance(row[1], dict) else {}
                        
                        sessions.append({
                            'jti': row[0],
                            'device_info': device_info,
                            'ip_address': row[2],
                            'issued_at': row[3].isoformat() if row[3] else None,
                            'last_used_at': row[4].isoformat() if row[4] else None,
                            'expires_at': row[5].isoformat() if row[5] else None,
                            'device_name': device_info.get('user_agent', 'Dispositivo desconhecido')[:100]
                        })
                    
                    return sessions
                    
        except Exception as e:
            logger.error(f"Erro ao buscar sessões do usuário: {e}")
            raise DatabaseError("Erro interno ao buscar sessões")
    
    def revoke_session(self, user_id: str, jti: str) -> bool:
        """Revogar sessão específica (diferente da atual)"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Verificar se a sessão existe e pertence ao usuário
                    cur.execute("""
                        SELECT id FROM user_sessions 
                        WHERE user_id = %s AND jti = %s AND revoked_at IS NULL
                    """, (user_id, jti))
                    
                    if not cur.fetchone():
                        return False
                    
                    # Revogar a sessão
                    cur.execute("""
                        UPDATE user_sessions 
                        SET revoked_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND jti = %s
                    """, (user_id, jti))
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Erro ao revogar sessão: {e}")
            raise DatabaseError("Erro interno ao revogar sessão")
    
    def cleanup_expired_sessions(self) -> Dict[str, int]:
        """Limpar sessões expiradas (pode ser chamado periodicamente)"""
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    # Contar sessões expiradas
                    cur.execute("""
                        SELECT COUNT(*) FROM user_sessions 
                        WHERE expires_at < CURRENT_TIMESTAMP AND revoked_at IS NULL
                    """)
                    expired_count = cur.fetchone()[0]
                    
                    # Marcar como revogadas
                    cur.execute("""
                        UPDATE user_sessions 
                        SET revoked_at = CURRENT_TIMESTAMP
                        WHERE expires_at < CURRENT_TIMESTAMP AND revoked_at IS NULL
                    """)
                    
                    conn.commit()
            
            return {'expired_sessions_cleaned': expired_count}
            
        except Exception as e:
            logger.error(f"Erro ao limpar sessões expiradas: {e}")
            raise DatabaseError("Erro interno na limpeza de sessões") 