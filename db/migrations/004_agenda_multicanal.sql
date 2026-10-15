-- Agenda multicanal (factory.scheduler) — 10 vídeos por semana no total:
--   Career Levels ............ seg, qua, sex, dom às 01h (4/semana)
--   História do cotidiano .... ter, qui, sáb às 02h     (3/semana, seed 005)
--   Regras curiosas .......... ter, qui, dom às 03h     (3/semana, seed 005)
-- No máximo 2 vídeos no mesmo dia (~110 imagens, dentro da cota grátis da Cloudflare).
--
-- Só acrescenta/atualiza chaves: o resto do config (approval.to, textos etc.) fica como está.
BEGIN;

UPDATE channels
SET config = config
  || jsonb_build_object('schedule', COALESCE(config->'schedule', '{}'::jsonb) || jsonb_build_object(
       'timezone', 'America/Sao_Paulo',
       'production_days', jsonb_build_array('mon', 'wed', 'fri', 'sun'),
       'production_hour', 1,
       'min_queued_topics', 5))
  || jsonb_build_object('youtube', COALESCE(config->'youtube', '{}'::jsonb) || jsonb_build_object(
       'publish_workflow_id', 'y3zthNcqybMcQEl0'))
WHERE slug = 'career-levels';

-- Fila do Career Levels para ~2 meses (4/semana). Idempotente.
INSERT INTO topics (channel_id, title, priority, source)
SELECT (SELECT id FROM channels WHERE slug = 'career-levels'), 'Every Level of ' || p || '''s Career', 100 + 10 * n, 'manual'
FROM unnest(ARRAY['a Police Officer', 'a Pharmacist', 'an Accountant', 'a Data Scientist', 'a Mechanic', 'a Plumber',
                  'a Flight Attendant', 'a Dentist', 'a Real Estate Agent', 'a Truck Driver', 'an Investment Banker',
                  'a Paramedic', 'a Veterinarian', 'a Product Manager', 'a Graphic Designer', 'a Welder',
                  'a Physical Therapist', 'a Marketing Manager', 'a Construction Worker', 'a Hotel Manager',
                  'a Cybersecurity Analyst', 'a Journalist']) WITH ORDINALITY AS x(p, n)
ON CONFLICT (channel_id, title) DO NOTHING;

COMMIT;

-- Limpeza feita em 15/10 depois dos testes manuais (já aplicada no banco):
-- vídeos presos em voicing/imaging -> failed; temas Chef, Nurse, Pilot, Lawyer, Firefighter e Architect
-- voltaram para 'queued' (o roteiro estava fixado no de Software Engineer); Software Engineer -> 'done'.

-- Conferir:
-- SELECT slug, active, config->'schedule' AS schedule, config->'youtube'->>'publish_workflow_id' AS publish,
--        (SELECT count(*) FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued') AS temas_na_fila
-- FROM channels c ORDER BY slug;
