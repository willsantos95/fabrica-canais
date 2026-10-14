-- Fábrica de Canais — schema inicial (Fase 0)
-- Requer Postgres 15+ com a extensão pgvector disponível.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Tipos
-- ---------------------------------------------------------------------------
CREATE TYPE topic_status AS ENUM ('queued', 'in_production', 'done', 'discarded');

CREATE TYPE video_status AS ENUM (
  'scripting', 'voicing', 'imaging', 'motion', 'assembling', 'derivatives',
  'awaiting_approval', 'scheduled', 'published', 'failed', 'rejected'
);

CREATE TYPE motion_mode AS ENUM ('ai', 'kenburns', 'template');

CREATE TYPE asset_kind AS ENUM ('audio', 'image', 'clip', 'final', 'short', 'thumb', 'srt', 'spec', 'preview');

CREATE TYPE job_status AS ENUM ('queued', 'running', 'succeeded', 'failed');

CREATE TYPE approval_decision AS ENUM ('approved', 'rejected');

CREATE TYPE publication_kind AS ENUM ('long', 'short');

CREATE TYPE publication_status AS ENUM ('uploading', 'scheduled', 'published', 'failed');

-- ---------------------------------------------------------------------------
-- Tabelas
-- ---------------------------------------------------------------------------
CREATE TABLE channels (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug        text NOT NULL UNIQUE,
  name        text NOT NULL,
  config      jsonb NOT NULL,
  active      boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE topics (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id  uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  title       text NOT NULL,
  notes       text,
  priority    integer NOT NULL DEFAULT 100,          -- menor = antes
  status      topic_status NOT NULL DEFAULT 'queued',
  source      text NOT NULL DEFAULT 'manual',        -- manual | analytics | agent
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel_id, title)
);
CREATE INDEX topics_queue_idx ON topics (channel_id, status, priority, created_at);

CREATE TABLE videos (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id        uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  topic_id          uuid REFERENCES topics(id) ON DELETE SET NULL,
  status            video_status NOT NULL DEFAULT 'scripting',
  spec              jsonb,
  script_embedding  vector(1536),
  duration_s        numeric(8,2),
  error             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX videos_channel_status_idx ON videos (channel_id, status);
CREATE INDEX videos_embedding_idx ON videos USING hnsw (script_embedding vector_cosine_ops);

CREATE TABLE shots (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id     uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  shot_id      text NOT NULL,                  -- ex.: b01-s01
  "order"      integer NOT NULL,
  motion_mode  motion_mode NOT NULL DEFAULT 'kenburns',
  is_hook      boolean NOT NULL DEFAULT false,
  image_url    text,
  clip_url     text,
  start_s      numeric(8,3),
  end_s        numeric(8,3),
  UNIQUE (video_id, shot_id)
);

CREATE TABLE assets (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  kind        asset_kind NOT NULL,
  url         text NOT NULL,
  provider    text,
  cost_usd    numeric(10,4) NOT NULL DEFAULT 0,
  meta        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX assets_video_idx ON assets (video_id, kind);

CREATE TABLE jobs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id         uuid REFERENCES videos(id) ON DELETE CASCADE,
  stage            text NOT NULL,              -- script | voice | visuals | assemble | shorts | thumbnail | publish ...
  provider         text,
  attempt          integer NOT NULL DEFAULT 1,
  status           job_status NOT NULL DEFAULT 'queued',
  idempotency_key  text UNIQUE,
  error            text,
  started_at       timestamptz,
  finished_at      timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_video_idx ON jobs (video_id, stage);

CREATE TABLE checks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  stage       text NOT NULL,
  name        text NOT NULL,
  passed      boolean NOT NULL,
  detail      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX checks_video_idx ON checks (video_id, stage);

CREATE TABLE approvals (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id    uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  decision    approval_decision NOT NULL,
  reason      text,
  decided_by  text,
  decided_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE publications (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id     uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  platform     text NOT NULL DEFAULT 'youtube',
  external_id  text,
  kind         publication_kind NOT NULL,
  publish_at   timestamptz,
  status       publication_status NOT NULL DEFAULT 'uploading',
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX publications_video_idx ON publications (video_id);

CREATE TABLE metrics (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  publication_id       uuid NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
  date                 date NOT NULL,
  views                integer,
  avg_view_duration_s  numeric(8,2),
  retention_curve      jsonb,
  UNIQUE (publication_id, date)
);

-- ---------------------------------------------------------------------------
-- updated_at automático
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER channels_updated_at BEFORE UPDATE ON channels
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER videos_updated_at BEFORE UPDATE ON videos
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Funções usadas pelo n8n
-- ---------------------------------------------------------------------------

-- Pega o próximo tema da fila de um canal e já o marca como em produção,
-- de forma segura contra duas execuções simultâneas.
CREATE OR REPLACE FUNCTION claim_next_topic(p_channel_slug text)
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
  INSERT INTO videos (channel_id, topic_id) VALUES (v_channel, v_topic) RETURNING id INTO v_video;

  RETURN QUERY SELECT v_topic, v_video, v_title;
END;
$$ LANGUAGE plpgsql;

-- Roteiros do mesmo canal mais parecidos com um embedding (checagem anti-repetição).
CREATE OR REPLACE FUNCTION similar_scripts(p_channel uuid, p_embedding vector(1536), p_limit integer DEFAULT 5)
RETURNS TABLE (video_id uuid, title text, similarity double precision) AS $$
  SELECT v.id, t.title, 1 - (v.script_embedding <=> p_embedding)
  FROM videos v
  LEFT JOIN topics t ON t.id = v.topic_id
  WHERE v.channel_id = p_channel
    AND v.script_embedding IS NOT NULL
    AND v.status NOT IN ('failed', 'rejected')
  ORDER BY v.script_embedding <=> p_embedding
  LIMIT p_limit;
$$ LANGUAGE sql STABLE;

-- Custo total por vídeo.
CREATE OR REPLACE VIEW video_costs AS
SELECT v.id AS video_id, c.slug AS channel, t.title,
       COALESCE(SUM(a.cost_usd), 0) AS cost_usd,
       COUNT(a.id) AS assets
FROM videos v
JOIN channels c ON c.id = v.channel_id
LEFT JOIN topics t ON t.id = v.topic_id
LEFT JOIN assets a ON a.video_id = v.id
GROUP BY v.id, c.slug, t.title;

COMMIT;
