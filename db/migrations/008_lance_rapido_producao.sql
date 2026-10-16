-- Lance Rápido: produção de Shorts por notícia (factory.news-short), resumo diário por esporte
-- (factory.news-recap) e publicação própria (factory.publish · Lance Rápido). Só mescla chaves novas.
-- Continua em modo prévia (news.preview = true) até o canal do YouTube e a credencial existirem.
UPDATE channels SET config = config
  || jsonb_build_object('news', (config->'news') || '{"script_model": "gpt-5.4-mini", "max_shorts_per_day": 10, "end_card": ["Segue o Lance Rápido", "notícia rápida todo dia"]}'::jsonb)
  || jsonb_build_object('recap', COALESCE(config->'recap', '{}'::jsonb) || '{"min_stories": 3, "max_stories": 8, "rate": "+5%"}'::jsonb)
  || jsonb_build_object('format', (config->'format') || '{"compilation": "daily_per_sport"}'::jsonb)
  || jsonb_build_object('visual', (config->'visual') || jsonb_build_object('style_block',
       '[STYLE] bold modern sports broadcast illustration, dynamic diagonal composition, stadium lights, high contrast, saturated colors, generic players seen from behind or in silhouette, no faces, square composition'))
  || jsonb_build_object('youtube', (config->'youtube') || '{"publish_workflow_id": "0886FbEVwRzq2z4h"}'::jsonb),
  updated_at = now()
WHERE slug = 'lance-rapido';

SELECT config->'youtube'->>'publish_workflow_id' AS publish, config->'news'->>'script_model' AS modelo,
       config->'news'->>'preview' AS previa, config->'recap' AS resumo
FROM channels WHERE slug = 'lance-rapido';
