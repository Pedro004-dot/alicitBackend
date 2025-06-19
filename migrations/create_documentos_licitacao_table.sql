-- Migração: Criar tabela unificada para documentos de licitação
-- Data: 2024-01-XX
-- Descrição: Tabela simplificada que armazena todos os documentos (editais + anexos) em uma estrutura única

-- Criar tabela documentos_licitacao
CREATE TABLE IF NOT EXISTS documentos_licitacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    licitacao_id UUID NOT NULL,
    titulo VARCHAR(500) NOT NULL,
    arquivo_nuvem_url TEXT NOT NULL,
    tipo_arquivo VARCHAR(100),
    tamanho_arquivo BIGINT,
    hash_arquivo VARCHAR(64),
    texto_preview TEXT,
    metadata_arquivo JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_documentos_licitacao_licitacao_id ON documentos_licitacao(licitacao_id);
CREATE INDEX IF NOT EXISTS idx_documentos_licitacao_hash ON documentos_licitacao(hash_arquivo);
CREATE INDEX IF NOT EXISTS idx_documentos_licitacao_created_at ON documentos_licitacao(created_at);

-- Criar índice GIN para busca no JSONB
CREATE INDEX IF NOT EXISTS idx_documentos_licitacao_metadata_gin ON documentos_licitacao USING GIN(metadata_arquivo);

-- Adicionar foreign key (opcional, se existir tabela licitacoes)
-- ALTER TABLE documentos_licitacao 
-- ADD CONSTRAINT fk_documentos_licitacao_licitacao_id 
-- FOREIGN KEY (licitacao_id) REFERENCES licitacoes(id) ON DELETE CASCADE;

-- Comentários para documentação
COMMENT ON TABLE documentos_licitacao IS 'Tabela unificada para todos os documentos de licitações (editais, anexos, etc.)';
COMMENT ON COLUMN documentos_licitacao.id IS 'Identificador único do documento';
COMMENT ON COLUMN documentos_licitacao.licitacao_id IS 'ID da licitação a qual o documento pertence';
COMMENT ON COLUMN documentos_licitacao.titulo IS 'Título/nome original do documento';
COMMENT ON COLUMN documentos_licitacao.arquivo_nuvem_url IS 'URL do arquivo no storage da nuvem (Supabase)';
COMMENT ON COLUMN documentos_licitacao.tipo_arquivo IS 'MIME type do arquivo (application/pdf, etc.)';
COMMENT ON COLUMN documentos_licitacao.tamanho_arquivo IS 'Tamanho do arquivo em bytes';
COMMENT ON COLUMN documentos_licitacao.hash_arquivo IS 'Hash SHA-256 do conteúdo do arquivo para verificação de integridade';
COMMENT ON COLUMN documentos_licitacao.texto_preview IS 'Preview do texto extraído (útil para PDFs)';
COMMENT ON COLUMN documentos_licitacao.metadata_arquivo IS 'Metadados adicionais em formato JSON (extensão, origem, etc.)';

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_documentos_licitacao_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar updated_at
CREATE TRIGGER documentos_licitacao_updated_at_trigger
    BEFORE UPDATE ON documentos_licitacao
    FOR EACH ROW
    EXECUTE FUNCTION update_documentos_licitacao_updated_at(); 