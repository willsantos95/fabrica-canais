-- Legenda queimada no vídeo longo (estilo canais de animação: uma palavra por vez, grande, centro-baixo).
-- O worker lê channels.config.captions na montagem. Sem "burn": true, o vídeo sai como antes (só o .srt).
-- Opções: mode "word" | "group", group, font, size (% da altura), bottom (% da altura), color, highlight,
-- outline, uppercase. Os Shorts continuam com a legenda vertical própria (cortados da versão sem legenda).
BEGIN;

UPDATE channels
SET config = config || jsonb_build_object('captions',
      COALESCE(config->'captions', '{}'::jsonb)
      || '{"burn": true, "mode": "word", "font": "Inter", "size": 8.5, "bottom": 12, "color": "#FFFFFF", "outline": 6, "uppercase": true}'::jsonb),
    updated_at = now()
WHERE slug IN ('career-levels', 'deu-tudo-errado');

COMMIT;

SELECT slug, config->'captions' AS captions FROM channels ORDER BY slug;
