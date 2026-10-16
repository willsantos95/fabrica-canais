"""Gera db/migrations/007_canal_lance_rapido.sql: tabela news_items e o canal Lance Rápido (pausado)."""
import json
from pathlib import Path

FEEDS = [
    {"sport": "futebol", "source": "ge", "url": "https://ge.globo.com/rss/ge/futebol/"},
    {"sport": "futebol", "source": "BBC Sport", "url": "https://feeds.bbci.co.uk/sport/football/rss.xml"},
    {"sport": "nba", "source": "ge", "url": "https://ge.globo.com/rss/ge/basquete/nba/"},
    {"sport": "nba", "source": "CBS Sports", "url": "https://www.cbssports.com/rss/headlines/nba/"},
    {"sport": "nfl", "source": "ge", "url": "https://ge.globo.com/rss/ge/futebol-americano/"},
    {"sport": "nfl", "source": "CBS Sports", "url": "https://www.cbssports.com/rss/headlines/nfl/"},
    {"sport": "nfl", "source": "ProFootballTalk", "url": "https://profootballtalk.nbcsports.com/feed/"},
]

CONFIG = {
    "slug": "lance-rapido",
    "name": "Lance Rápido",
    "handle": "@LanceRapido",
    "youtube_channel_id": "PREENCHER_UC...",
    "language": "pt-BR",
    "niche": "Notícias rápidas e análise de futebol, NBA e NFL em português, em Shorts e compilados semanais",
    "tone": "narrador esportivo jovem e direto, energia alta sem gritar, frases curtas, análise em uma frase, nunca inventa fatos",
    "point_of_view": "Toda notícia vem com o porquê importa: o que muda na tabela, no elenco ou na temporada.",
    "format": {"type": "news_short", "short_seconds": [40, 55], "words_per_minute": 175, "compilation": "weekly"},
    "voice": {"provider": "edge-tts", "fallback": "edge-tts", "voice_id": "", "edge_voice": "pt-BR-FranciscaNeural", "rate": "+10%"},
    "visual": {
        "style_block": "[STYLE] bold modern sports broadcast illustration, dynamic diagonal composition, stadium lights, high contrast, saturated colors, generic players seen from behind or in silhouette, no faces, 9:16 vertical",
        "negative_prompt": "real athlete faces, recognizable people, team logos, league logos, jersey numbers of real players, sponsor logos, watermark, text, gore",
        "image_provider": "cloudflare", "image_fallback": "gemini",
        "sport_colors": {"futebol": "#1DB954", "nba": "#F58426", "nfl": "#1E4FD8"},
        "brand": {"primary": "#FFD400", "secondary": "#111111", "font": "Inter", "logo_url": ""},
    },
    "audio": {"music_library": "fabrica/channels/lance-rapido/music/", "music_volume_db": -22, "loudness_lufs": -14},
    "news": {
        "feeds": FEEDS,
        "active_hours": [8, 23],
        "max_age_hours": 18,
        "min_score": 7,
        "max_topics_per_run": 3,
        "max_queue": 8,
        "topic_ttl_hours": 12,
        "scoring_model": "gpt-5.4-nano",
        "preview": True,
    },
    "schedule": {"timezone": "America/Sao_Paulo", "production_days": [], "production_hour": None, "min_queued_topics": 0,
                 "publish_mode": "on_approval"},
    "youtube": {"category_id": "17", "default_tags": ["lance rápido", "notícias esportivas", "futebol", "nba", "nfl"],
                "hashtags": ["LanceRapido"], "contains_synthetic_media": True, "made_for_kids": False,
                "publish_workflow_id": "PENDENTE"},
    "tiktok": {"hashtags": ["LanceRapido", "esportes"]},
    "texts": {"disclaimer": "Narração e artes geradas com auxílio de IA a partir das fontes citadas."},
    "prompts": {},
}

cfg = json.dumps(CONFIG, ensure_ascii=False)
assert "{{" not in cfg and "$cfg$" not in cfg
sql = f"""-- Canal "Lance Rápido" (@LanceRapido): notícias de futebol, NBA e NFL em Shorts. Gerado por channels/lance-rapido.py.
-- Entra PAUSADO. A coleta de pautas (factory.news) funciona mesmo pausado, no modo prévia (news.preview = true).
BEGIN;

CREATE TABLE IF NOT EXISTS news_items (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_id    uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
  url           text NOT NULL,
  title         text NOT NULL,
  summary       text,
  source        text,
  sport         text,
  published_at  timestamptz,
  score         integer,
  story_key     text,
  title_pt      text,
  reason        text,
  status        text NOT NULL DEFAULT 'new',   -- new | scored | queued | skipped
  topic_id      uuid REFERENCES topics(id) ON DELETE SET NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (channel_id, url)
);
CREATE INDEX IF NOT EXISTS news_items_recent_idx ON news_items (channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS news_items_story_idx ON news_items (channel_id, story_key);

INSERT INTO channels (slug, name, config, active)
VALUES ('lance-rapido', 'Lance Rápido', $cfg${cfg}$cfg$::jsonb, false)
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name,
  config = EXCLUDED.config
    || jsonb_build_object('approval', channels.config->'approval')
    || jsonb_build_object('youtube', (EXCLUDED.config->'youtube') || jsonb_build_object('publish_workflow_id',
         COALESCE(channels.config->'youtube'->'publish_workflow_id', EXCLUDED.config->'youtube'->'publish_workflow_id'))),
  updated_at = now();

UPDATE channels SET config = config || jsonb_build_object('approval',
  COALESCE((SELECT config->'approval' FROM channels WHERE slug = 'career-levels'),
           '{{"channel": "whatsapp", "to": "55DDDNUMERO", "timeout_hours": 24}}'::jsonb))
WHERE slug = 'lance-rapido' AND COALESCE(jsonb_typeof(config->'approval'), 'null') = 'null';

COMMIT;

SELECT slug, active, jsonb_array_length(config->'news'->'feeds') AS feeds, config->'approval'->>'to' IS NOT NULL AS aprovacao
FROM channels WHERE slug = 'lance-rapido';
"""
Path("db/migrations/007_canal_lance_rapido.sql").write_text(sql, "utf-8")
print("ok")
