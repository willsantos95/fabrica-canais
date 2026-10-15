-- Métricas públicas do YouTube (factory.metrics) e índices usados pelo painel.
BEGIN;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS likes integer;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS comments integer;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
CREATE INDEX IF NOT EXISTS publications_external_idx ON publications (external_id);
CREATE INDEX IF NOT EXISTS metrics_pub_date_idx ON metrics (publication_id, date DESC);
CREATE INDEX IF NOT EXISTS videos_created_idx ON videos (created_at DESC);
COMMIT;
