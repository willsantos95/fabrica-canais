-- Conteúdo pronto por tema e escolha da IA por canal.
--
-- topics.prepared: roteiro e/ou shotlist escritos fora da fábrica (ex.: pelo Claude, na conversa).
--   {"script": {...mesmo JSON que a IA devolveria dentro de <json>...</json>},
--    "shotlist": {...idem...}, "author": "claude", "prepared_at": "..."}
--   Quando existe, o factory.produce usa e pula a IA daquela etapa (custo zero).
-- channels.config.llm: ordem dos provedores, ex.: {"order": ["prepared","gemini","openai"]}
--   prepared = texto pronto do tema; gemini = plano grátis do Google; openai = pago.
BEGIN;

ALTER TABLE topics ADD COLUMN IF NOT EXISTS prepared jsonb;

-- temas com conteúdo pronto saem primeiro (já estão pagos, ou melhor, de graça)
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
  ORDER BY (t.prepared IS NULL), t.priority, t.created_at
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

-- canais de vídeo longo: pronto → Gemini grátis → OpenAI; notícias: Gemini grátis → OpenAI
UPDATE channels SET config = config || jsonb_build_object('llm',
  COALESCE(config->'llm', '{}'::jsonb) || jsonb_build_object(
    'order', CASE WHEN config->'format'->>'type' = 'news_short'
                  THEN '["gemini","openai"]'::jsonb ELSE '["prepared","gemini","openai"]'::jsonb END,
    'gemini', '{"model": "gemini-3.5-flash", "search_model": "gemini-2.5-flash"}'::jsonb)),
  updated_at = now()
WHERE config->'llm' IS NULL;

COMMIT;

SELECT slug, config->'llm' AS llm FROM channels ORDER BY slug;
