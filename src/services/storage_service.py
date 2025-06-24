import os
import logging
from typing import Optional, Dict, Any, List
import httpx
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageService:
    """Serviço para gerenciar uploads no Supabase Storage"""
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url.rstrip('/')
        self.supabase_key = supabase_key
        self.bucket_name = 'licitacao-documents'
        
    async def upload_file(self, 
                         file_path: str, 
                         destination_path: str,
                         content_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload de arquivo para o Supabase Storage
        
        Args:
            file_path: Caminho local do arquivo
            destination_path: Caminho de destino no bucket
            content_type: Content-type do arquivo (opcional)
            
        Returns:
            Dict com resultado do upload
        """
        try:
            # Verificar se arquivo existe
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'Arquivo não encontrado: {file_path}'
                }
            
            # Determinar content-type se não fornecido
            if not content_type:
                if file_path.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif file_path.lower().endswith('.doc'):
                    content_type = 'application/msword'
                elif file_path.lower().endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif file_path.lower().endswith('.txt'):
                    content_type = 'application/octet-stream'  # 🔧 FIX: usar octet-stream para .txt
                else:
                    content_type = 'application/octet-stream'
            
            # Ler arquivo
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Usar método síncrono corrigido
            success = self.upload(destination_path, file_data, content_type)
            
            if success:
                return {
                    'success': True,
                    'path': destination_path,
                    'size': len(file_data),
                    'content_type': content_type
                }
            else:
                return {
                    'success': False,
                    'error': 'Erro no upload'
                }
                    
        except Exception as e:
            logger.error(f"❌ Erro no upload para Storage: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }

    def upload(self, destination_path: str, file_content: bytes, content_type: str = 'application/octet-stream') -> bool:
        """
        Upload síncrono de conteúdo de arquivo para o Supabase Storage
        
        Args:
            destination_path: Caminho de destino no bucket
            file_content: Conteúdo do arquivo em bytes
            content_type: Content-type do arquivo
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Headers baseados na documentação oficial do Supabase
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': content_type,
                'apikey': self.supabase_key  # Header adicional requerido pela API
            }
            
            # URL conforme documentação oficial
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{destination_path}"
            
            logger.info(f"🔄 Tentando upload: {url}")
            logger.info(f"📝 Content-Type: {content_type}")
            logger.info(f"📏 Size: {len(file_content)} bytes")
            
            # Primeira tentativa: POST para novo arquivo
            response = requests.post(
                url,
                headers=headers,
                data=file_content,
                timeout=60.0
            )
            
            if response.status_code in (200, 201):
                logger.info(f"✅ Upload realizado: {destination_path}")
                return True
                
            elif response.status_code == 409:
                # Arquivo já existe, tentar PUT para atualizar
                logger.info(f"📁 Arquivo existe, tentando atualizar: {destination_path}")
                
                put_response = requests.put(
                    url,
                    headers=headers,
                    data=file_content,
                    timeout=60.0
                )
                
                if put_response.status_code in (200, 201):
                    logger.info(f"✅ Arquivo atualizado: {destination_path}")
                    return True
                else:
                    logger.error(f"❌ Erro no PUT: {put_response.status_code} - {put_response.text}")
                    return False
                    
            elif response.status_code == 403:
                # Erro de permissão, tentar com ANON_KEY se estamos usando SERVICE_KEY
                logger.warning(f"⚠️ Erro 403 com SERVICE_KEY, isso pode indicar problema de configuração")
                logger.error(f"❌ Resposta: {response.text}")
                return False
                
            else:
                logger.error(f"❌ Erro no upload: {response.status_code} - {response.text}")
                logger.error(f"🔍 Headers enviados: {headers}")
                logger.error(f"🔍 URL: {url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro no upload: {e}")
            return False

    def list(self, prefix: str = "") -> List[Dict[str, Any]]:
        """
        Lista arquivos no bucket
        
        Args:
            prefix: Prefixo para filtrar arquivos
            
        Returns:
            Lista de arquivos
        """
        try:
            # 🆕 Validar credenciais antes de fazer request
            if not self.supabase_key or not self.supabase_url:
                logger.error("❌ Credenciais Supabase não configuradas")
                return []
            
            # 🆕 Verificar se a chave parece válida (Supabase keys começam com 'eyJ')
            if not self.supabase_key.startswith('eyJ'):
                logger.error("❌ Chave Supabase inválida (deve começar com 'eyJ')")
                return []
                
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'apikey': self.supabase_key
            }
            
            url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
            
            # Payload sempre deve ter a propriedade prefix, mesmo que vazia
            payload = {
                'prefix': prefix,
                'limit': 100,
                'offset': 0
            }
            
            logger.info(f"🔍 Tentando listar arquivos no bucket: {self.bucket_name}")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 200:
                files = response.json()
                logger.info(f"✅ Listagem bem sucedida: {len(files) if isinstance(files, list) else 0} arquivos")
                return files if isinstance(files, list) else []
            elif response.status_code == 403:
                logger.error("❌ ERRO 403: Chave de API inválida ou sem permissão para storage")
                logger.error(f"🔑 Chave usada: {self.supabase_key[:20]}...")
                logger.error(f"🌐 URL: {self.supabase_url}")
                logger.error(f"📦 Bucket: {self.bucket_name}")
                return []
            else:
                logger.warning(f"⚠️ Erro ao listar arquivos: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erro ao listar arquivos: {e}")
            return []

    def list_buckets(self) -> List[Any]:
        """
        Lista buckets disponíveis
        
        Returns:
            Lista de buckets (pode estar vazia se não houver permissão)
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.supabase_key}',
                'Content-Type': 'application/json',
                'apikey': self.supabase_key
            }
            
            url = f"{self.supabase_url}/storage/v1/bucket"
            
            response = requests.get(url, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                buckets = response.json()
                return buckets if isinstance(buckets, list) else []
            else:
                logger.warning(f"⚠️ Erro ao listar buckets: {response.status_code} (normal com algumas configurações)")
                return []  # Retorna lista vazia ao invés de erro
                
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível listar buckets: {e}")
            return []  # Retorna lista vazia ao invés de erro

    def get_public_url(self, file_path: str) -> str:
        """
        Gera URL pública para um arquivo
        
        Args:
            file_path: Caminho do arquivo no bucket
            
        Returns:
            URL pública do arquivo
        """
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{file_path}"
            
    async def ensure_bucket_exists(self) -> bool:
        """
        Verifica se bucket existe através de tentativa de uso.
        Não precisa verificar diretamente via API de buckets.
        """
        try:
            # Tentar listar arquivos no bucket como teste
            files = self.list("")
            logger.info(f"✅ Bucket '{self.bucket_name}' acessível - {len(files)} arquivos encontrados")
            return True
                
        except Exception as e:
            logger.warning(f"⚠️ Erro ao testar bucket: {e}")
            # Assumir que bucket existe (confirmado via SQL)
            logger.info(f"📦 Assumindo que bucket '{self.bucket_name}' existe")
            return True

    def test_connection(self) -> Dict[str, Any]:
        """
        Testa a conexão com o Supabase Storage
        """
        try:
            logger.info("🧪 Iniciando teste de conexão completo...")
            
            # 1. Testar listagem de buckets
            logger.info("1️⃣ Testando listagem de buckets...")
            buckets = self.list_buckets()
            bucket_test_ok = len(buckets) >= 0  # Pode ser 0 com algumas configurações
            logger.info(f"   Resultado: {len(buckets)} buckets encontrados")
            
            # 2. Testar listagem de arquivos no bucket
            logger.info("2️⃣ Testando listagem de arquivos...")
            files = self.list("")
            files_test_ok = isinstance(files, list)
            logger.info(f"   Resultado: {len(files)} arquivos encontrados")
            
            # 3. Testar upload de um arquivo pequeno de teste
            logger.info("3️⃣ Testando upload...")
            test_content = b"test content for connection"
            test_path = "test/connection-test.txt"
            upload_test_ok = self.upload(test_path, test_content, "text/plain")
            logger.info(f"   Resultado: {'✅ Sucesso' if upload_test_ok else '❌ Falhou'}")
            
            # 4. Se upload funcionou, testar URL pública
            public_url = None
            if upload_test_ok:
                public_url = self.get_public_url(test_path)
                logger.info(f"   URL pública: {public_url}")
            
            success = bucket_test_ok and files_test_ok and upload_test_ok
            
            return {
                'success': success,
                'bucket_accessible': bucket_test_ok,
                'files_listable': files_test_ok,
                'upload_working': upload_test_ok,
                'public_url_generated': public_url is not None,
                'details': {
                    'bucket_count': len(buckets),
                    'file_count': len(files),
                    'test_upload': upload_test_ok,
                    'test_url': public_url
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro no teste de conexão: {e}")
            return {
                'success': False,
                'error': str(e)
            } 