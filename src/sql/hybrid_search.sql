CREATE OR REPLACE FUNCTION hybrid_search(
    query_embedding vector(1024),
    query_text text,
    licitacao_id_param uuid,
    limit_param integer DEFAULT 12,
    semantic_weight float DEFAULT 0.7,
    text_weight float DEFAULT 0.3
) RETURNS TABLE (
    chunk_id uuid,
    similarity_score float,
    text_score float,
    hybrid_score float
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_scores AS (
        SELECT 
            id,
            1 - (embedding <=> query_embedding) as semantic_score
        FROM documentos_chunks
        WHERE licitacao_id = licitacao_id_param
        AND embedding IS NOT NULL
    ),
    text_scores AS (
        SELECT 
            id,
            ts_rank_cd(to_tsvector('portuguese', chunk_text), plainto_tsquery('portuguese', query_text)) as text_score
        FROM documentos_chunks
        WHERE licitacao_id = licitacao_id_param
    )
    SELECT 
        s.id as chunk_id,
        s.semantic_score as similarity_score,
        COALESCE(t.text_score, 0) as text_score,
        (s.semantic_score * semantic_weight + COALESCE(t.text_score, 0) * text_weight) as hybrid_score
    FROM semantic_scores s
    LEFT JOIN text_scores t ON t.id = s.id
    ORDER BY hybrid_score DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql; 