-- Primeiro: Adicionar novos campos
ALTER TABLE users
    ADD COLUMN verification_code VARCHAR(6),
    ADD COLUMN verification_code_expires_at TIMESTAMP;

-- Segundo: Limpar verificações pendentes
-- (usuários precisarão solicitar novo código)
UPDATE users 
SET verification_code = NULL,
    verification_code_expires_at = NULL
WHERE email_verification_token IS NOT NULL 
  AND email_verified = false;

-- Terceiro: Remover campos antigos
ALTER TABLE users
    DROP COLUMN email_verification_token,
    DROP COLUMN email_verification_expires_at; 