-- Liga cada vídeo à execução do n8n que o produz (usado pelo workflow de erro).
ALTER TABLE videos ADD COLUMN IF NOT EXISTS n8n_execution_id text;
CREATE INDEX IF NOT EXISTS videos_execution_idx ON videos (n8n_execution_id);

-- claim_next_topic passa a receber o id da execução e gravá-lo no vídeo criado.
-- (Gravar num UPDATE da mesma consulta não funciona: o snapshot não enxerga a linha
-- recém-inserida pela função.)
DROP FUNCTION IF EXISTS claim_next_topic(text);

CREATE OR REPLACE FUNCTION claim_next_topic(p_channel_slug text, p_execution_id text DEFAULT NULL)
RETURNS TABLE (topic_id uuid, video_id uuid, title text) AS $$
DECLARE
  v_channel uuid;
  v_topic   uuid;
  v_title   text;
  v_video   uuid;
BEGIN
  SELECT c.id INTO v_channel FROM channels c WHERE c.slug = p_channel_slug AND c.active;
  IF v_channel IS NULL THEN
    RETURN;
  END IF;

  SELECT t.id, t.title INTO v_topic, v_title
  FROM topics t
  WHERE t.channel_id = v_channel AND t.status = 'queued'
  ORDER BY t.priority, t.created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED;

  IF v_topic IS NULL THEN
    RETURN;
  END IF;

  UPDATE topics SET status = 'in_production' WHERE id = v_topic;
  INSERT INTO videos (channel_id, topic_id, n8n_execution_id)
  VALUES (v_channel, v_topic, p_execution_id)
  RETURNING id INTO v_video;

  RETURN QUERY SELECT v_topic, v_video, v_title;
END;
$$ LANGUAGE plpgsql;
