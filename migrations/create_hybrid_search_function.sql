-- Migração: Criar função hybrid_search para busca híbrida semântica + textual
-- Data: 2024-01-XX
-- Descrição: Função que combina busca vetorial (pgvector) com busca textual (ts_rank)

-- Primeiro, remover função existente se ela existe
DROP FUNCTION IF EXISTS hybrid_search(vector,text,uuid,integer,double precision,double precision);

CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector,
    query_text text,
    target_licitacao_id uuid,
    limit_results integer,
    semantic_weight double precision,
    text_weight double precision
)
RETURNS TABLE (
    chunk_id uuid,
    chunk_text text,
    semantic_score double precision,
    text_score double precision,
    hybrid_score double precision,
    metadata_chunk jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.chunk_text,
        (1 - (dc.embedding <=> query_embedding))::double precision as semantic_score,
        ts_rank(to_tsvector('portuguese', dc.chunk_text), plainto_tsquery('portuguese', query_text))::double precision as text_score,
        (semantic_weight * (1 - (dc.embedding <=> query_embedding)) + 
         text_weight * ts_rank(to_tsvector('portuguese', dc.chunk_text), plainto_tsquery('portuguese', query_text)))::double precision as hybrid_score,
        dc.metadata_chunk
    FROM documentos_chunks dc
    WHERE dc.licitacao_id = target_licitacao_id
    ORDER BY hybrid_score DESC
    LIMIT limit_results;
END;
$$ LANGUAGE plpgsql;

-- Comentário para documentação
COMMENT ON FUNCTION hybrid_search IS 'Função de busca híbrida que combina similaridade semântica (pgvector) com busca textual (ts_rank) para recuperar chunks de documentos relevantes'; 