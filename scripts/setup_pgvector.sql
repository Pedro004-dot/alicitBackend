-- Script de configuração do pgvector para Sistema RAG
-- Execute como superuser do PostgreSQL
-- Exemplo: psql -U postgres -d seu_banco < setup_pgvector.sql

-- 1. Instalar extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Verificar instalação
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Criar tabela de chunks RAG (redundante, mas como backup)
CREATE TABLE IF NOT EXISTS rag_chunks (
    id VARCHAR(255) PRIMARY KEY,
    hash_conteudo VARCHAR(64) UNIQUE NOT NULL,
    documento_id VARCHAR(255) NOT NULL,
    documento_titulo TEXT NOT NULL,
    texto TEXT NOT NULL,
    ordem INTEGER NOT NULL,
    secao VARCHAR(100) NOT NULL,
    tipo_conteudo VARCHAR(100) NOT NULL,
    metadata JSONB NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_rag_chunks_documento 
ON rag_chunks(documento_id);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_hash 
ON rag_chunks(hash_conteudo);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_secao 
ON rag_chunks(secao);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_tipo 
ON rag_chunks(tipo_conteudo);

-- 5. Criar índice vetorial para busca por similaridade
-- IMPORTANTE: Execute apenas após inserir alguns dados
-- CREATE INDEX idx_rag_chunks_embedding 
-- ON rag_chunks USING ivfflat (embedding vector_cosine_ops) 
-- WITH (lists = 100);

-- 6. Tabela para logs de análise RAG
CREATE TABLE IF NOT EXISTS rag_analysis_logs (
    id SERIAL PRIMARY KEY,
    documento_id VARCHAR(255) NOT NULL,
    documento_titulo TEXT NOT NULL,
    tipo_analise VARCHAR(50) NOT NULL, -- 'RAG', 'FALLBACK_SIMPLES'
    tempo_processamento FLOAT NOT NULL,
    num_chunks INTEGER NOT NULL,
    contexto_tokens INTEGER NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    query_utilizada TEXT,
    sucesso BOOLEAN NOT NULL,
    erro_msg TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7. Índices para logs
CREATE INDEX IF NOT EXISTS idx_rag_logs_documento 
ON rag_analysis_logs(documento_id);

CREATE INDEX IF NOT EXISTS idx_rag_logs_created 
ON rag_analysis_logs(created_at);

-- 8. Função para limpar cache antigo automaticamente
CREATE OR REPLACE FUNCTION limpar_cache_rag_antigo()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM rag_chunks 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO rag_analysis_logs (
        documento_id, documento_titulo, tipo_analise, 
        tempo_processamento, num_chunks, contexto_tokens, 
        cache_hit, sucesso, erro_msg
    ) VALUES (
        'SYSTEM', 'Cache Cleanup', 'MAINTENANCE',
        0, deleted_count, 0, false, true, 
        'Limpeza automática: ' || deleted_count || ' chunks removidos'
    );
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 9. Configurar limpeza automática (opcional)
-- Executar a cada 24 horas
-- SELECT cron.schedule('cleanup-rag-cache', '0 2 * * *', 'SELECT limpar_cache_rag_antigo();');

-- 10. Verificar configuração
SELECT 
    'pgvector instalado' as status,
    version() as postgres_version,
    (SELECT version FROM pg_available_extensions WHERE name = 'vector') as pgvector_version;

COMMENT ON TABLE rag_chunks IS 'Cache de chunks vetorizados para sistema RAG de análise de licitações';
COMMENT ON TABLE rag_analysis_logs IS 'Logs de análises realizadas pelo sistema RAG';

-- Finalização
\echo 'Configuração do pgvector concluída!'
\echo 'Lembre-se de:'
\echo '1. Instalar sentence-transformers: pip install sentence-transformers'
\echo '2. Criar índice vetorial após inserir dados: CREATE INDEX idx_rag_chunks_embedding ON rag_chunks USING ivfflat (embedding vector_cosine_ops);'
\echo '3. Configurar chaves de API necessárias no ambiente' 