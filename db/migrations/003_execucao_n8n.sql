-- Liga cada vídeo à execução do n8n que o produz (usado pelo workflow de erro).
ALTER TABLE videos ADD COLUMN IF NOT EXISTS n8n_execution_id text;
CREATE INDEX IF NOT EXISTS videos_execution_idx ON videos (n8n_execution_id);
