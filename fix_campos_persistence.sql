-- ============================================================================
-- 🔧 CORREÇÃO RÁPIDA: Campos faltantes para Persistência Escalável
-- ============================================================================

-- Verificar e adicionar campos essenciais para o sistema de persistência
DO $$
BEGIN
    -- external_id: ID único do provider externo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'external_id') THEN
        ALTER TABLE licitacoes ADD COLUMN external_id VARCHAR(255);
        RAISE NOTICE '✅ Campo external_id adicionado';
    ELSE
        RAISE NOTICE '✅ Campo external_id já existe';
    END IF;

    -- contracting_authority: Autoridade contratante  
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'contracting_authority') THEN
        ALTER TABLE licitacoes ADD COLUMN contracting_authority VARCHAR(500);
        RAISE NOTICE '✅ Campo contracting_authority adicionado';
    ELSE
        RAISE NOTICE '✅ Campo contracting_authority já existe';
    END IF;

    -- procuring_entity_id: ID da entidade contratante
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procuring_entity_id') THEN
        ALTER TABLE licitacoes ADD COLUMN procuring_entity_id VARCHAR(255);
        RAISE NOTICE '✅ Campo procuring_entity_id adicionado';
    ELSE
        RAISE NOTICE '✅ Campo procuring_entity_id já existe';
    END IF;

    -- procuring_entity_name: Nome da entidade contratante
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procuring_entity_name') THEN
        ALTER TABLE licitacoes ADD COLUMN procuring_entity_name VARCHAR(500);
        RAISE NOTICE '✅ Campo procuring_entity_name adicionado';
    ELSE
        RAISE NOTICE '✅ Campo procuring_entity_name já existe';
    END IF;

    -- contact_info: Informações de contato (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'contact_info') THEN
        ALTER TABLE licitacoes ADD COLUMN contact_info JSONB;
        RAISE NOTICE '✅ Campo contact_info adicionado';
    ELSE
        RAISE NOTICE '✅ Campo contact_info já existe';
    END IF;

    -- documents: Documentos relacionados (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'documents') THEN
        ALTER TABLE licitacoes ADD COLUMN documents JSONB;
        RAISE NOTICE '✅ Campo documents adicionado';
    ELSE
        RAISE NOTICE '✅ Campo documents já existe';
    END IF;

    -- currency_code: Código da moeda
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'currency_code') THEN
        ALTER TABLE licitacoes ADD COLUMN currency_code VARCHAR(10) DEFAULT 'BRL';
        RAISE NOTICE '✅ Campo currency_code adicionado';
    ELSE
        RAISE NOTICE '✅ Campo currency_code já existe';
    END IF;

    -- country_code: Código do país
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'country_code') THEN
        ALTER TABLE licitacoes ADD COLUMN country_code VARCHAR(10) DEFAULT 'BR';
        RAISE NOTICE '✅ Campo country_code adicionado';
    ELSE
        RAISE NOTICE '✅ Campo country_code já existe';
    END IF;

    -- municipality: Nome do município
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'municipality') THEN
        ALTER TABLE licitacoes ADD COLUMN municipality VARCHAR(255);
        RAISE NOTICE '✅ Campo municipality adicionado';
    ELSE
        RAISE NOTICE '✅ Campo municipality já existe';
    END IF;

    -- procurement_method: Método de compra
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procurement_method') THEN
        ALTER TABLE licitacoes ADD COLUMN procurement_method VARCHAR(255);
        RAISE NOTICE '✅ Campo procurement_method adicionado';
    ELSE
        RAISE NOTICE '✅ Campo procurement_method já existe';
    END IF;

    -- additional_info: Informações adicionais (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'additional_info') THEN
        ALTER TABLE licitacoes ADD COLUMN additional_info JSONB;
        RAISE NOTICE '✅ Campo additional_info adicionado';
    ELSE
        RAISE NOTICE '✅ Campo additional_info já existe';
    END IF;

END $$;

-- Preencher external_id para registros PNCP existentes (se ainda não foi feito)
UPDATE licitacoes 
SET external_id = pncp_id 
WHERE provider_name = 'pncp' 
  AND external_id IS NULL 
  AND pncp_id IS NOT NULL;

-- Criar constraint única se não existir
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint 
                   WHERE conname = 'unique_provider_external_id') THEN
        ALTER TABLE licitacoes 
        ADD CONSTRAINT unique_provider_external_id 
        UNIQUE (provider_name, external_id);
        RAISE NOTICE '✅ Constraint única (provider_name, external_id) criada';
    ELSE
        RAISE NOTICE '✅ Constraint única já existe';
    END IF;
END $$;

-- Criar índices se não existirem
CREATE INDEX IF NOT EXISTS idx_licitacoes_provider_name 
ON licitacoes (provider_name);

CREATE INDEX IF NOT EXISTS idx_licitacoes_external_id 
ON licitacoes (external_id);

CREATE INDEX IF NOT EXISTS idx_licitacoes_municipality 
ON licitacoes (municipality);

CREATE INDEX IF NOT EXISTS idx_licitacoes_procurement_method 
ON licitacoes (procurement_method);

SELECT 'Script de correção executado com sucesso!' as resultado; 