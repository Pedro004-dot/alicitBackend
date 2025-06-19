"""
Repository para operações com sessões de usuário
Responsável apenas por acesso a dados da tabela user_sessions
"""
import logging
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class UserSessionRepository(BaseRepository):
    """Repository para gerenciar sessões de usuário"""
    
    @property
    def table_name(self) -> str:
        return "user_sessions"
    
    @property
    def primary_key(self) -> str:
        return "id"
    
    def _get_token_hash(self, token: str) -> str:
        """Gerar hash do token para busca segura"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def find_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Buscar sessão por token JWT"""
        token_hash = self._get_token_hash(token)
        query = """
            SELECT * FROM user_sessions 
            WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > %s
        """
        results = self.execute_custom_query(query, (token_hash, datetime.utcnow()))
        return results[0] if results else None
    
    def find_active_sessions_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Buscar todas as sessões ativas de um usuário"""
        query = """
            SELECT * FROM user_sessions 
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > %s
            ORDER BY created_at DESC
        """
        return self.execute_custom_query(query, (user_id, datetime.utcnow()))
    
    def create_session(self, user_id: str, token: str, device_info: str, 
                      ip_address: str, expires_at: datetime, jti: str = None) -> Dict[str, Any]:
        """Criar nova sessão"""
        import uuid
        
        token_hash = self._get_token_hash(token)
        
        # Se jti não foi fornecido, extrair do token JWT
        if not jti:
            import jwt
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                jti = decoded.get('jti')
            except:
                jti = str(uuid.uuid4())
        
        # device_info deve ser um objeto JSON
        import json
        device_info_json = device_info if isinstance(device_info, dict) else {"info": device_info}
        
        session_data = {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'jti': jti,
            'token_hash': token_hash,
            'device_info': json.dumps(device_info_json),
            'ip_address': ip_address,
            'issued_at': datetime.utcnow(),
            'expires_at': expires_at,
            'last_used_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        # Usar inserção customizada para evitar updated_at automático
        query = """
            INSERT INTO user_sessions (id, user_id, jti, token_hash, device_info, 
                                     ip_address, issued_at, expires_at, last_used_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """
        
        values = (
            session_data['id'], session_data['user_id'], session_data['jti'],
            session_data['token_hash'], session_data['device_info'], session_data['ip_address'],
            session_data['issued_at'], session_data['expires_at'], 
            session_data['last_used_at'], session_data['created_at']
        )
        
        results = self.execute_custom_query(query, values)
        return results[0] if results else None
    
    def deactivate_session(self, session_id: str) -> bool:
        """Desativar sessão específica"""
        data = {
            'revoked_at': datetime.utcnow()
        }
        result = self.update(session_id, data)
        return result is not None
    
    def deactivate_session_by_token(self, token: str) -> bool:
        """Desativar sessão por token"""
        token_hash = self._get_token_hash(token)
        query = """
            UPDATE user_sessions 
            SET revoked_at = %s 
            WHERE token_hash = %s AND revoked_at IS NULL
        """
        rows_affected = self.execute_custom_command(query, (datetime.utcnow(), token_hash))
        return rows_affected > 0
    
    def deactivate_all_user_sessions(self, user_id: str) -> int:
        """Desativar todas as sessões de um usuário"""
        query = """
            UPDATE user_sessions 
            SET revoked_at = %s 
            WHERE user_id = %s AND revoked_at IS NULL
        """
        return self.execute_custom_command(query, (datetime.utcnow(), user_id))
    
    def cleanup_expired_sessions(self) -> int:
        """Limpar sessões expiradas"""
        query = """
            UPDATE user_sessions 
            SET revoked_at = %s 
            WHERE expires_at < %s AND revoked_at IS NULL
        """
        return self.execute_custom_command(query, (datetime.utcnow(), datetime.utcnow()))
    
    def update_last_activity(self, token: str) -> bool:
        """Atualizar última atividade da sessão"""
        token_hash = self._get_token_hash(token)
        query = """
            UPDATE user_sessions 
            SET last_used_at = %s 
            WHERE token_hash = %s AND revoked_at IS NULL
        """
        rows_affected = self.execute_custom_command(query, (datetime.utcnow(), token_hash))
        return rows_affected > 0
    
    def get_session_details(self, user_id: str) -> List[Dict[str, Any]]:
        """Buscar detalhes das sessões ativas de um usuário"""
        query = """
            SELECT id, device_info, ip_address, issued_at, last_used_at, expires_at
            FROM user_sessions 
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > %s
            ORDER BY issued_at DESC
        """
        return self.execute_custom_query(query, (user_id, datetime.utcnow()))
    
    def is_token_valid(self, token: str) -> bool:
        """Verificar se token é válido (ativo e não expirado)"""
        token_hash = self._get_token_hash(token)
        query = """
            SELECT 1 FROM user_sessions 
            WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > %s
            LIMIT 1
        """
        results = self.execute_custom_query(query, (token_hash, datetime.utcnow()))
        return len(results) > 0
    
    def count_active_sessions(self, user_id: str) -> int:
        """Contar sessões ativas de um usuário"""
        query = """
            SELECT COUNT(*) as count FROM user_sessions 
            WHERE user_id = %s AND revoked_at IS NULL AND expires_at > %s
        """
        results = self.execute_custom_query(query, (user_id, datetime.utcnow()))
        return results[0]['count'] if results else 0 