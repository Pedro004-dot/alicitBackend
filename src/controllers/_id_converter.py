import re
import logging
from config.database import DatabaseManager

logger = logging.getLogger(__name__)

def convert_pncp_to_uuid(id_value: str) -> str:
    """
    Verifica se um ID é um UUID. Se não for, assume que é um pncp_id,
    busca no banco de dados e retorna o UUID correspondente.
    """
    if not id_value:
        raise ValueError("ID não pode ser nulo ou vazio")

    # Padrão para UUID
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    
    # Se já for um UUID, retorne diretamente
    if uuid_pattern.match(id_value):
        logger.debug(f"ID '{id_value}' já é um UUID. Nenhuma conversão necessária.")
        return id_value

    # Se não for um UUID, trate como pncp_id e busque o UUID no banco
    logger.warning(f"⚠️ Recebido ID '{id_value}' que não é UUID. Tentando converter de pncp_id...")
    
    db_manager = DatabaseManager()
    with db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM licitacoes WHERE numero_controle_pncp = %s", (id_value,))
            result = cursor.fetchone()
            
            if result:
                uuid_licitacao_id = result[0]
                logger.info(f"✅ Convertido pncp_id '{id_value}' para UUID: {uuid_licitacao_id}")
                return uuid_licitacao_id
            else:
                logger.error(f"❌ Licitação não encontrada no banco para pncp_id: {id_value}")
                return None 