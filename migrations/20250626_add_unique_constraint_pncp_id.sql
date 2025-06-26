-- Adiciona uma restrição UNIQUE na coluna `numero_controle_pncp` da tabela `licitacoes`.
-- Isso é crucial para a lógica de "UPSERT" (INSERT ... ON CONFLICT), que previne
-- a duplicação de licitações com base no seu identificador do PNCP.
ALTER TABLE public.licitacoes ADD CONSTRAINT licitacoes_numero_controle_pncp_unique UNIQUE (numero_controle_pncp); 