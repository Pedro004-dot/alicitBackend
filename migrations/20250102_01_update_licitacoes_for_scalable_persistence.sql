-- ============================================================================
-- 🏗️ MIGRAÇÃO: Sistema de Persistência Escalável v2.0
-- Atualização da tabela licitacoes existente para suportar múltiplos providers
-- ============================================================================

-- 1. Verificar e criar tabela de log de migrações
CREATE TABLE IF NOT EXISTS migration_log (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

-- 2. Adicionar novos campos necessários (apenas se não existirem)
DO $$
BEGIN
    -- external_id: ID único do provider externo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'external_id') THEN
        ALTER TABLE licitacoes ADD COLUMN external_id VARCHAR(255);
        RAISE NOTICE 'Campo external_id adicionado';
    END IF;

    -- currency_code: Código da moeda (BRL)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'currency_code') THEN
        ALTER TABLE licitacoes ADD COLUMN currency_code VARCHAR(10) DEFAULT 'BRL';
        RAISE NOTICE 'Campo currency_code adicionado';
    END IF;

    -- country_code: Código do país (BR)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'country_code') THEN
        ALTER TABLE licitacoes ADD COLUMN country_code VARCHAR(10) DEFAULT 'BR';
        RAISE NOTICE 'Campo country_code adicionado';
    END IF;

    -- municipality: Nome do município
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'municipality') THEN
        ALTER TABLE licitacoes ADD COLUMN municipality VARCHAR(255);
        RAISE NOTICE 'Campo municipality adicionado';
    END IF;

    -- subcategory: Subcategoria da licitação
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'subcategory') THEN
        ALTER TABLE licitacoes ADD COLUMN subcategory VARCHAR(255);
        RAISE NOTICE 'Campo subcategory adicionado';
    END IF;

    -- procurement_method: Método de compra
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procurement_method') THEN
        ALTER TABLE licitacoes ADD COLUMN procurement_method VARCHAR(255);
        RAISE NOTICE 'Campo procurement_method adicionado';
    END IF;

    -- contracting_authority: Autoridade contratante
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'contracting_authority') THEN
        ALTER TABLE licitacoes ADD COLUMN contracting_authority VARCHAR(500);
        RAISE NOTICE 'Campo contracting_authority adicionado';
    END IF;

    -- procuring_entity_id: ID da entidade contratante
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procuring_entity_id') THEN
        ALTER TABLE licitacoes ADD COLUMN procuring_entity_id VARCHAR(255);
        RAISE NOTICE 'Campo procuring_entity_id adicionado';
    END IF;

    -- procuring_entity_name: Nome da entidade contratante
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'procuring_entity_name') THEN
        ALTER TABLE licitacoes ADD COLUMN procuring_entity_name VARCHAR(500);
        RAISE NOTICE 'Campo procuring_entity_name adicionado';
    END IF;

    -- contact_info: Informações de contato (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'contact_info') THEN
        ALTER TABLE licitacoes ADD COLUMN contact_info JSONB;
        RAISE NOTICE 'Campo contact_info adicionado';
    END IF;

    -- documents: Documentos relacionados (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'documents') THEN
        ALTER TABLE licitacoes ADD COLUMN documents JSONB;
        RAISE NOTICE 'Campo documents adicionado';
    END IF;

    -- additional_info: Informações adicionais (JSONB)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'licitacoes' AND column_name = 'additional_info') THEN
        ALTER TABLE licitacoes ADD COLUMN additional_info JSONB;
        RAISE NOTICE 'Campo additional_info adicionado';
    END IF;

END $$;

-- 3. Preencher external_id para registros PNCP existentes
UPDATE licitacoes 
SET external_id = pncp_id 
WHERE provider_name = 'pncp' AND external_id IS NULL;

-- 4. Criar constraint única para (provider_name, external_id)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint 
                   WHERE conname = 'unique_provider_external_id') THEN
        ALTER TABLE licitacoes 
        ADD CONSTRAINT unique_provider_external_id 
        UNIQUE (provider_name, external_id);
        RAISE NOTICE 'Constraint única (provider_name, external_id) criada';
    END IF;
END $$;

-- 5. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_licitacoes_provider_name 
ON licitacoes (provider_name);

CREATE INDEX IF NOT EXISTS idx_licitacoes_external_id 
ON licitacoes (external_id);

CREATE INDEX IF NOT EXISTS idx_licitacoes_provider_external 
ON licitacoes (provider_name, external_id);

CREATE INDEX IF NOT EXISTS idx_licitacoes_municipality 
ON licitacoes (municipality);

CREATE INDEX IF NOT EXISTS idx_licitacoes_procurement_method 
ON licitacoes (procurement_method);

-- 6. Registrar migração
INSERT INTO migration_log (migration_name, description) 
VALUES (
    '20250102_01_update_licitacoes_for_scalable_persistence',
    'Atualização da tabela licitacoes para suportar sistema escalável com múltiplos providers'
) ON CONFLICT (migration_name) DO NOTHING;

-- 7. Verificação final
DO $$
DECLARE
    record_count INTEGER;
    provider_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO record_count FROM licitacoes;
    SELECT COUNT(DISTINCT provider_name) INTO provider_count FROM licitacoes;
    
    RAISE NOTICE '✅ Migração concluída com sucesso!';
    RAISE NOTICE '📊 Total de licitações: %', record_count;
    RAISE NOTICE '🏭 Providers ativos: %', provider_count;
    RAISE NOTICE '🚀 Sistema escalável pronto para novos providers!';
END $$; 