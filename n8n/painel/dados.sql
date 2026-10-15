SELECT
 (SELECT COALESCE(json_agg(x ORDER BY x.slug), '[]') FROM (
   SELECT c.slug, c.name, c.active, c.config->'schedule' AS schedule, c.config->>'language' AS language,
     (SELECT count(*) FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued')::int AS queued,
     (SELECT t.title FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued' ORDER BY t.priority, t.created_at LIMIT 1) AS next_topic
   FROM channels c) x) AS channels,
 (SELECT COALESCE(json_agg(x ORDER BY x.created_at DESC), '[]') FROM (
   SELECT v.id, upper(left(v.id::text, 4)) AS code, c.slug, c.name AS channel, v.status, v.created_at, v.updated_at, v.error,
     v.duration_s::float AS duration_s,
     COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title', t.title) AS title, t.title AS topic,
     (v.spec->'usage'->>'cost_usd')::float AS cost_usd,
     v.spec->'publishing'->>'youtube_id' AS youtube_id,
     (SELECT min(p.publish_at) FROM publications p WHERE p.video_id = v.id AND p.kind = 'long') AS publish_at
   FROM videos v JOIN channels c ON c.id = v.channel_id LEFT JOIN topics t ON t.id = v.topic_id
   WHERE v.created_at > now() - interval '45 days' ORDER BY v.created_at DESC LIMIT 80) x) AS videos,
 (SELECT COALESCE(json_agg(x ORDER BY x.publish_at), '[]') FROM (
   SELECT p.kind, p.publish_at, p.external_id, p.status, c.name AS channel, c.slug,
     COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title') AS title
   FROM publications p JOIN videos v ON v.id = p.video_id JOIN channels c ON c.id = v.channel_id
   WHERE p.status <> 'failed' AND p.publish_at > now() - interval '1 day' AND p.publish_at < now() + interval '21 days') x) AS calendar,
 (SELECT COALESCE(json_agg(x ORDER BY x.views DESC NULLS LAST), '[]') FROM (
   SELECT p.external_id, p.kind, c.name AS channel, COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title') AS title,
     p.publish_at, m.views, m.likes, m.comments, m.date,
     m.views - COALESCE((SELECT m2.views FROM metrics m2 WHERE m2.publication_id = p.id AND m2.date <= m.date - 7
                         ORDER BY m2.date DESC LIMIT 1), 0) AS views_7d
   FROM publications p JOIN videos v ON v.id = p.video_id JOIN channels c ON c.id = v.channel_id
   JOIN LATERAL (SELECT * FROM metrics mm WHERE mm.publication_id = p.id ORDER BY mm.date DESC LIMIT 1) m ON true
   WHERE p.external_id IS NOT NULL ORDER BY m.views DESC NULLS LAST LIMIT 60) x) AS performance,
 (SELECT COALESCE(json_agg(x ORDER BY x.month, x.slug), '[]') FROM (
   SELECT to_char(date_trunc('month', v.created_at AT TIME ZONE 'America/Sao_Paulo'), 'YYYY-MM') AS month, c.slug, c.name AS channel,
     COALESCE(sum((v.spec->'usage'->>'cost_usd')::numeric), 0)::float AS cost_usd,
     count(*) FILTER (WHERE v.spec ? 'usage')::int AS with_cost, count(*)::int AS videos
   FROM videos v JOIN channels c ON c.id = v.channel_id
   WHERE v.created_at > now() - interval '6 months' GROUP BY 1, 2, 3) x) AS costs,
 (SELECT COALESCE(sum(jsonb_array_length(b->'shots')), 0)::int FROM videos v, jsonb_array_elements(v.spec->'blocks') b
   WHERE v.updated_at >= date_trunc('day', now()) AND v.status NOT IN ('scripting', 'voicing', 'imaging', 'failed')) AS images_today_est,
 now() AS generated_at;
