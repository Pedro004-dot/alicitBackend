# Sistema de Autenticação Modular

A estrutura de autenticação foi refatorada para ser mais modular, organizada e fácil de manter.

## Nova Estrutura

### Services (backend/src/services/auth/)

**BaseAuthService** - Funcionalidades comuns:
- Validações (email, senha, dados de registro)
- Hash de senhas com bcrypt
- Geração de tokens seguros
- Geração e verificação de JWT
- Consultas comuns ao banco de dados
- Gestão de trial subscription

**RegisterService** - Registro e verificação:
- `register_user()` - Registrar novo usuário + trial automático
- `verify_email()` - Verificar email com token
- `resend_verification_email()` - Reenviar email de verificação

**LoginService** - Login e tokens:
- `login_user()` - Login com validações de segurança
- `verify_token()` - Verificar validade do JWT
- `refresh_token()` - Renovar token JWT
- Controle de tentativas de login e bloqueio

**LogoutService** - Logout e sessões:
- `logout_session()` - Logout de sessão específica
- `logout_all_sessions()` - Logout de todas as sessões
- `get_user_sessions()` - Listar sessões ativas
- `revoke_session()` - Revogar sessão específica
- `cleanup_expired_sessions()` - Limpeza automática

**PasswordService** - Recuperação e alteração:
- `request_password_reset()` - Solicitar reset por email
- `reset_password()` - Reset com token
- `change_password()` - Alterar senha logado

**ProfileService** - Perfil e dados:
- `get_user_profile()` - Perfil completo + subscription + empresas
- `update_user_profile()` - Atualizar dados do perfil
- `get_user_subscription_details()` - Detalhes da subscription

### Controllers (backend/src/controllers/auth/)

**BaseAuthController** - Funcionalidades comuns:
- Tratamento padronizado de exceções
- Extração de dados JSON
- Informações de dispositivo
- Respostas padronizadas (sucesso/erro)

**RegisterController** - Endpoints de registro:
- `POST /api/auth/register`
- `POST /api/auth/verify-email`
- `POST /api/auth/resend-verification`

**LoginController** - Endpoints de login:
- `POST /api/auth/login`
- `POST /api/auth/verify-token`
- `POST /api/auth/refresh-token`

**LogoutController** - Endpoints de logout:
- `POST /api/auth/logout`
- `POST /api/auth/logout-all`
- `GET /api/auth/sessions`
- `DELETE /api/auth/sessions/<id>`

**PasswordController** - Endpoints de senha:
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/change-password`

**ProfileController** - Endpoints de perfil:
- `GET /api/auth/me`
- `PUT /api/auth/me`
- `GET /api/auth/subscription`

## Arquivos Unificados

### AuthService Unificado (auth_service_unified.py)
Agrega todos os services específicos em uma única interface, mantendo a mesma API externa.

### AuthController Unificado (auth_controller_unified.py)
Agrega todos os controllers específicos em uma única interface.

## Compatibilidade

### Arquivos de Compatibilidade
- `auth_service.py` - Wrapper que herda do service unificado
- `auth_controller.py` - Wrapper que herda do controller unificado

Estes arquivos mantêm compatibilidade total com código existente.

## Vantagens da Nova Estrutura

1. **Modularidade**: Cada funcionalidade em arquivo separado
2. **Responsabilidade única**: Cada service/controller tem escopo bem definido
3. **Facilidade de manutenção**: Mudanças localizadas
4. **Reutilização**: Base services/controllers podem ser reutilizados
5. **Testes**: Mais fácil testar funcionalidades específicas
6. **Legibilidade**: Código mais organizado e fácil de entender
7. **Compatibilidade**: Código existente continua funcionando sem alterações

## Exemplo de Uso

### Usando Services Específicos (Nova Abordagem)
```python
from services.auth import LoginService, LogoutService

login_service = LoginService()
logout_service = LogoutService()

# Login
result = login_service.login_user(email, password, device_info, ip)

# Logout
logout_service.logout_session(jti)
```

### Usando Service Unificado (Compatibilidade)
```python
from services.auth_service import AuthService

auth_service = AuthService()

# Login
result = auth_service.login_user(email, password, device_info, ip)

# Logout
auth_service.logout_session(jti)
```

Ambas as abordagens funcionam identicamente.

## Considerações de Segurança

Todas as funcionalidades de segurança foram mantidas:
- Hash bcrypt de senhas
- JWT com expiração
- Rate limiting de login
- Controle de sessões
- Tokens seguros para reset/verificação
- Não exposição de dados sensíveis 