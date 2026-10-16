"""Gera o código SDK dos workflows de produção do Lance Rápido (canal de notícias):

- factory.news-short : pega a melhor pauta da fila, escreve o roteiro (modelo barato, só com as fontes),
                       renderiza o Short vertical no worker (news_short) e pede aprovação no WhatsApp
- factory.news-recap : resumo diário por esporte (horizontal, 3-6 min) a partir dos Shorts aprovados no dia
- factory.publish · Lance Rápido : publica na hora (público) e põe na playlist do esporte;
                       tem um gatilho manual "Criar playlists" que cria as playlists e grava os ids na config

A aprovação é a mesma do factory.approval (1 #CÓDIGO publica, 2 #CÓDIGO descarta).
"""
from pathlib import Path

from build_fase2 import CRED, OUT, RETRY, WF, check_code, config_node, pg, send_text, wait, worker_job, yt_session, YT_SESSION_URL

HERE = Path(__file__).parent
code = lambda name: (HERE / "lance" / name).read_text("utf-8")
OPENAI = {"httpHeaderAuth": {"id": "9OK91AZnXE70dKic", "name": "OpenAi - Fabrica"}}
TZ = "America/Sao_Paulo"
ACTIVE_STATUSES = "'scripting','voicing','imaging','motion','assembling','derivatives'"


def openai_node(wf, var, name, pos):
    return wf.node(var, "n8n-nodes-base.httpRequest", 4.2, name, {
        "method": "POST", "url": "https://api.openai.com/v1/responses",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"timeout": 300000}}, pos, OPENAI, output=[{"output": []}], **RETRY)


def presign(wf, var, name, urls_expr, pos):
    return wf.node(var, "n8n-nodes-base.httpRequest", 4.2, name, {
        "method": "POST", "url": "={{ $('Config').first().json.worker_url }}/files/presign",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ urls: " + urls_expr + ", expires_s: 172800 }) }}",
        "options": {"timeout": 120000}}, pos, CRED["worker"], output=[{"urls": []}], **RETRY)


SAVE_SQL = """WITH v AS (
  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, duration_s = $5::numeric, updated_at = now()
  WHERE id = $1::uuid RETURNING id
), ck AS (
  INSERT INTO checks (video_id, stage, name, passed, detail)
  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)
  FROM jsonb_array_elements($3::jsonb) c
)
INSERT INTO assets (video_id, kind, url, meta)
SELECT $1::uuid, (a->>'k')::asset_kind, a->>'u', COALESCE(a->'meta', '{}'::jsonb)
FROM jsonb_array_elements($4::jsonb) a WHERE a->>'u' IS NOT NULL;"""


# ===========================================================================
# factory.news-short
# ===========================================================================
PROXIMA_SQL = f"""-- $1 = true no teste manual: ignora canal pausado, modo prévia, horário e limite do dia
WITH ch AS (
  SELECT c.id, c.config FROM channels c
  WHERE c.config->'format'->>'type' = 'news_short'
    AND ($1::boolean OR (c.active AND COALESCE((c.config->'news'->>'preview')::boolean, true) = false))
    AND ($1::boolean OR extract(hour FROM now() AT TIME ZONE '{TZ}')
         BETWEEN COALESCE((c.config->'news'->'active_hours'->>0)::int, 8) AND COALESCE((c.config->'news'->'active_hours'->>1)::int, 23))
    -- um Short por vez por canal (o teste manual ignora)
    AND ($1::boolean OR NOT EXISTS (SELECT 1 FROM videos v WHERE v.channel_id = c.id AND v.status IN ({ACTIVE_STATUSES})
                    AND v.updated_at > now() - interval '45 minutes'))
    AND ($1::boolean OR (SELECT count(*) FROM videos v WHERE v.channel_id = c.id AND v.spec->>'type' = 'news_short'
         AND v.created_at >= date_trunc('day', now() AT TIME ZONE '{TZ}') AT TIME ZONE '{TZ}')
         < COALESCE((c.config->'news'->>'max_shorts_per_day')::int, 10))
  ORDER BY random() LIMIT 1
), t AS (
  SELECT t.id, t.title, t.notes FROM topics t
  WHERE t.channel_id = (SELECT id FROM ch) AND t.status = 'queued' AND t.source = 'news'
  ORDER BY t.priority, t.created_at DESC
  LIMIT 1 FOR UPDATE SKIP LOCKED
), up AS (
  UPDATE topics SET status = 'in_production' WHERE id = (SELECT id FROM t) RETURNING id
), v AS (
  INSERT INTO videos (channel_id, topic_id, status, spec)
  SELECT ch.id, up.id, 'scripting', jsonb_build_object('type', 'news_short') FROM ch, up
  RETURNING id
)
SELECT v.id AS video_id, t.id AS topic_id, t.title, t.notes, ch.config, ch.id AS channel_id FROM v, t, ch;"""


def build_news_short() -> str:
    wf = WF("factory-news-short", "factory.news-short")
    wf.node("t_cron", "n8n-nodes-base.scheduleTrigger", 1.2, "A cada 20 min (8h-23h)",
            {"rule": {"interval": [{"field": "cronExpression", "expression": "*/20 8-23 * * *"}]}}, [0, -100], fn="trigger")
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Testar (ignora prévia e horário)", {}, [0, 100], fn="trigger")
    config_node(wf, extra=[{"id": "c-force", "name": "force", "value": "={{ $execution.mode !== 'trigger' }}", "type": "boolean"}])
    wf.node("prox", "n8n-nodes-base.postgres", 2.5, "Próxima pauta", pg(PROXIMA_SQL, "={{ [ $json.force ] }}"),
            [480, 0], CRED["pg"], output=[{"video_id": "v", "topic_id": "t", "title": "x", "notes": "{}", "config": {}, "channel_id": "c"}], **RETRY)
    wf.node("ped", "n8n-nodes-base.code", 2, "Pedido do roteiro", {"jsCode": code("roteiro.js")}, [720, 0], output=[{"sport": "nba", "body": {}}])
    openai_node(wf, "ai", "OpenAI: roteiro", [960, 0])
    wf.node("mont", "n8n-nodes-base.code", 2, "Montar pedido", {"jsCode": code("validar.js")}, [1200, 0],
            output=[{"video_id": "v", "spec": {}, "job": {}}])
    wf.node("st", "n8n-nodes-base.postgres", 2.5, "Status: render", pg(
        "UPDATE videos SET status = 'assembling', spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid;",
        "={{ [ $json.video_id, JSON.stringify($json.spec) ] }}"), [1440, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("job", "n8n-nodes-base.httpRequest", 4.2, "Worker: Short", worker_job("news_short",
        "{ video_id: $('Montar pedido').first().json.video_id, idempotency_key: $('Montar pedido').first().json.video_id + '-news-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: $('Montar pedido').first().json.job }"),
        [1680, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("wait", "n8n-nodes-base.wait", 1.1, "Aguardar Short", wait(1), [1920, 0], CRED["callback"],
            output=[{"body": {"status": "succeeded", "result": {}}}])
    wf.node("chk", "n8n-nodes-base.code", 2, "Checar vídeo", check_code("Short"), [2160, 0],
            output=[{"url": "s3://x", "cover_url": "s3://y", "spec_url": "s3://z", "duration_s": 45, "beats": [], "checks": []}])
    wf.node("prep", "n8n-nodes-base.code", 2, "Preparar gravação", {"jsCode": code("salvar_short.js")}, [2400, 0],
            output=[{"video_id": "v", "spec": "{}", "checks": "[]", "assets": "[]", "duration_s": 45}])
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Salvar Short", pg(SAVE_SQL,
        "={{ [ $json.video_id, $json.spec, $json.checks, $json.assets, $json.duration_s ] }}"),
        [2640, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    presign(wf, "links", "Links temporários", "[ $('Checar vídeo').first().json.url, $('Checar vídeo').first().json.cover_url ]", [2880, 0])
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem de aprovação", {"jsCode": code("aprovacao.js")}, [3120, 0],
            output=[{"number": "55", "text": "x", "video": "https://x", "cover": "https://y", "caption": "#ABCD"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: pedir aprovação",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [3360, 0], CRED["evo"], **RETRY)
    wf.node("wa_vid", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: vídeo", {
        "resource": "messages-api", "operation": "send-video",
        "instanceName": "={{ $('Config').first().json.evolution_instance }}",
        "remoteJid": "={{ $('Mensagem de aprovação').first().json.number }}",
        "media": "={{ $('Mensagem de aprovação').first().json.video }}",
        "caption": "={{ $('Mensagem de aprovação').first().json.caption }}"},
        [3600, 0], CRED["evo"], onError="continueRegularOutput")
    return wf.render(
        "  .add(t_cron)\n  .to(config)\n  .to(prox)\n  .to(ped)\n  .to(ai)\n  .to(mont)\n  .to(st)\n  .to(job)\n  .to(wait)\n"
        "  .to(chk)\n  .to(prep)\n  .to(save)\n  .to(links)\n  .to(msg)\n  .to(wa)\n  .to(wa_vid)\n  .add(t_manual)\n  .to(config)")


# ===========================================================================
# factory.news-recap
# ===========================================================================
RESUMO_SQL = f"""-- um esporte por execução: o que tiver mais Shorts aprovados hoje e ainda não tiver resumo
WITH ch AS (
  SELECT c.id, c.config FROM channels c
  WHERE c.config->'format'->>'type' = 'news_short'
    AND ($1::boolean OR (c.active AND COALESCE((c.config->'news'->>'preview')::boolean, true) = false))
  LIMIT 1
), d AS (
  SELECT date_trunc('day', now() AT TIME ZONE '{TZ}') AT TIME ZONE '{TZ}' AS d0
), cand AS (
  SELECT v.spec->>'sport' AS sport,
    json_agg(json_build_object('video_id', v.id, 'headline', v.spec->>'headline', 'title', v.spec->'publishing'->>'title',
      'beats', v.spec->'beats', 'sources', v.spec->'sources') ORDER BY v.created_at) AS stories
  FROM videos v, ch, d
  WHERE v.channel_id = ch.id AND v.spec->>'type' = 'news_short' AND v.status IN ('scheduled', 'published')
    AND v.created_at >= d.d0
    AND NOT EXISTS (SELECT 1 FROM videos r WHERE r.channel_id = ch.id AND r.spec->>'type' = 'news_recap'
                    AND r.spec->>'sport' = v.spec->>'sport' AND r.created_at >= d.d0 AND r.status <> 'failed')
  GROUP BY 1
  HAVING count(*) >= COALESCE(((SELECT config FROM ch)->'recap'->>'min_stories')::int, 3)
  ORDER BY count(*) DESC LIMIT 1
), v AS (
  INSERT INTO videos (channel_id, status, spec)
  SELECT ch.id, 'scripting', jsonb_build_object('type', 'news_recap', 'sport', cand.sport) FROM ch, cand
  RETURNING id
)
SELECT v.id AS video_id, cand.sport, cand.stories, ch.config FROM v, cand, ch;"""


def build_news_recap() -> str:
    wf = WF("factory-news-recap", "factory.news-recap")
    wf.node("t_cron", "n8n-nodes-base.scheduleTrigger", 1.2, "Às 22h, 22h30, 23h e 23h30",
            {"rule": {"interval": [{"field": "cronExpression", "expression": "0,30 22-23 * * *"}]}}, [0, -100], fn="trigger")
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Testar (ignora prévia)", {}, [0, 100], fn="trigger")
    config_node(wf, extra=[{"id": "c-force", "name": "force", "value": "={{ $execution.mode !== 'trigger' }}", "type": "boolean"}])
    wf.node("prox", "n8n-nodes-base.postgres", 2.5, "Próximo resumo", pg(RESUMO_SQL, "={{ [ $json.force ] }}"),
            [480, 0], CRED["pg"], output=[{"video_id": "v", "sport": "nba", "stories": [], "config": {}}], **RETRY)
    wf.node("ped", "n8n-nodes-base.code", 2, "Pedido do resumo", {"jsCode": code("resumo_pedido.js")}, [720, 0],
            output=[{"today": "16/10", "label": "NBA", "stories": [], "body": {}}])
    openai_node(wf, "ai", "OpenAI: resumo", [960, 0])
    wf.node("mont", "n8n-nodes-base.code", 2, "Montar resumo", {"jsCode": code("resumo_validar.js")}, [1200, 0],
            output=[{"video_id": "v", "spec": {}, "job": {}}])
    wf.node("st", "n8n-nodes-base.postgres", 2.5, "Status: render", pg(
        "UPDATE videos SET status = 'assembling', spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid;",
        "={{ [ $json.video_id, JSON.stringify($json.spec) ] }}"), [1440, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("job", "n8n-nodes-base.httpRequest", 4.2, "Worker: resumo", worker_job("news_recap",
        "{ video_id: $('Montar resumo').first().json.video_id, idempotency_key: $('Montar resumo').first().json.video_id + '-recap-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: $('Montar resumo').first().json.job }"),
        [1680, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("wait", "n8n-nodes-base.wait", 1.1, "Aguardar resumo", wait(2), [1920, 0], CRED["callback"],
            output=[{"body": {"status": "succeeded", "result": {}}}])
    wf.node("chk", "n8n-nodes-base.code", 2, "Checar resumo", check_code("Resumo"), [2160, 0],
            output=[{"url": "s3://x", "srt_url": "s3://y", "thumbnails": [], "chapters": [], "duration_s": 200, "checks": []}])
    wf.node("prep", "n8n-nodes-base.code", 2, "Preparar gravação", {"jsCode": code("resumo_salvar.js")}, [2400, 0],
            output=[{"video_id": "v", "spec": {}, "spec_s": "{}", "checks": "[]", "assets": "[]", "duration_s": 200}])
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Salvar resumo", pg(SAVE_SQL,
        "={{ [ $json.video_id, $json.spec_s, $json.checks, $json.assets, $json.duration_s ] }}"),
        [2640, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    presign(wf, "links", "Links do resumo",
            "[ $('Checar resumo').first().json.url, ...($('Checar resumo').first().json.thumbnails || []).slice(0, 1).map(t => t.url) ]", [2880, 0])
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem de aprovação", {"jsCode": code("resumo_msg.js")}, [3120, 0],
            output=[{"number": "55", "text": "x", "thumb": "https://y", "caption": "#ABCD"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: pedir aprovação",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [3360, 0], CRED["evo"], **RETRY)
    wf.node("wa_img", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: thumbnail", {
        "resource": "messages-api", "operation": "send-image",
        "instanceName": "={{ $('Config').first().json.evolution_instance }}",
        "remoteJid": "={{ $('Mensagem de aprovação').first().json.number }}",
        "media": "={{ $('Mensagem de aprovação').first().json.thumb }}",
        "caption": "={{ $('Mensagem de aprovação').first().json.caption }}"},
        [3600, 0], CRED["evo"], onError="continueRegularOutput")
    return wf.render(
        "  .add(t_cron)\n  .to(config)\n  .to(prox)\n  .to(ped)\n  .to(ai)\n  .to(mont)\n  .to(st)\n  .to(job)\n  .to(wait)\n"
        "  .to(chk)\n  .to(prep)\n  .to(save)\n  .to(links)\n  .to(msg)\n  .to(wa)\n  .to(wa_img)\n  .add(t_manual)\n  .to(config)")


# ===========================================================================
# factory.publish · Lance Rápido
# ===========================================================================
LOAD_SQL = """-- muda para scheduled só se ainda estiver aguardando: um segundo "1" não publica duas vezes
WITH v AS (
  UPDATE videos SET status = 'scheduled', updated_at = now()
  WHERE id = $1::uuid AND status = 'awaiting_approval'
  RETURNING id, channel_id, topic_id, spec
)
SELECT v.id AS video_id, v.topic_id, v.spec, c.config FROM v JOIN channels c ON c.id = v.channel_id;"""

PUB_SQL = """WITH v AS (
  UPDATE videos SET status = 'published', updated_at = now(),
    spec = jsonb_set(COALESCE(spec, '{}'::jsonb), '{publishing,youtube_id}', to_jsonb($2::text))
  WHERE id = $1::uuid
), t AS (
  UPDATE topics SET status = 'done' WHERE id = NULLIF($4, '')::uuid
)
INSERT INTO publications (video_id, platform, external_id, kind, publish_at, status)
VALUES ($1::uuid, 'youtube', $2, $3::publication_kind, now(), 'published');"""

PLAYLISTS_SQL = """SELECT id, name, config FROM channels WHERE slug = $1;"""
SAVE_PLAYLISTS_SQL = """UPDATE channels SET config = jsonb_set(config, '{youtube,playlists}',
  COALESCE(config->'youtube'->'playlists', '{}'::jsonb) || $2::jsonb), updated_at = now()
WHERE slug = $1
RETURNING config->'youtube'->'playlists' AS playlists;"""


def build_publish_lance(yt=None, name="factory.publish · Lance Rápido", slug="lance-rapido") -> str:
    wf = WF("factory-publish-lance", name)
    wf.node("t_sub", "n8n-nodes-base.executeWorkflowTrigger", 1.2, "Vídeo aprovado",
            {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "video_id", "type": "string"}]}},
            [0, 0], fn="trigger", output=[{"video_id": "uuid"}])
    config_node(wf)
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Carregar e travar", pg(LOAD_SQL, "={{ [ $json.video_id ] }}"),
            [480, 0], CRED["pg"], output=[{"video_id": "v", "topic_id": "t", "spec": {}, "config": {}}], **RETRY)
    wf.node("plan", "n8n-nodes-base.code", 2, "Plano de publicação", {"jsCode": code("plano.js")}, [720, 0],
            output=[{"video_id": "v", "topic_id": "t", "kind": "short", "sport": "nba", "title": "t", "body": {},
                     "final_url": "s3://x", "thumb_url": None, "playlist_id": "PL", "number": "55", "channel": "c"}])
    wf.node("sess", "n8n-nodes-base.httpRequest", 4.2, "YouTube: sessão do vídeo",
            yt_session(YT_SESSION_URL, "video/mp4", "$json.body"), [960, 0], yt,
            output=[{"headers": {"location": "https://upload"}, "statusCode": 200}], **RETRY)
    wf.node("up", "n8n-nodes-base.httpRequest", 4.2, "Worker: enviar vídeo", worker_job("youtube_upload",
        "{ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: { uploads: [ { ref: 'video', upload_url: $json.headers.location, "
        "media_url: $('Plano de publicação').first().json.final_url, content_type: 'video/mp4' } ] } }"),
        [1200, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("w", "n8n-nodes-base.wait", 1.1, "Aguardar envio", {k: v for k, v in wait(3).items() if k != "authentication"}, [1440, 0],
            output=[{"body": {"status": "succeeded", "result": {"uploads": [{"ref": "video", "id": "abc", "ok": True}]}}}])
    wf.node("c", "n8n-nodes-base.code", 2, "Checar envio", {"jsCode": code("publicado.js")}, [1680, 0],
            output=[{"youtube_id": "abc", "url": "https://youtube.com/shorts/abc"}])
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Registrar publicação", pg(PUB_SQL,
        "={{ [ $('Plano de publicação').first().json.video_id, $json.youtube_id, $('Plano de publicação').first().json.kind, "
        "$('Plano de publicação').first().json.topic_id || '' ] }}"), [1920, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem", {"jsCode": code("publicado_msg.js")}, [2160, 0],
            output=[{"number": "55", "text": "x"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: avisar",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [2400, 0], CRED["evo"], **RETRY)
    # playlist do esporte (se existir)
    wf.node("pl", "n8n-nodes-base.code", 2, "Playlist do esporte", {"jsCode": """const p = $('Plano de publicação').first().json;
if (!p.playlist_id) return [];
return [{ json: { body: { snippet: { playlistId: p.playlist_id, resourceId: { kind: 'youtube#video', videoId: $('Checar envio').first().json.youtube_id } } } } }];
"""}, [2160, 200], output=[{"body": {}}])
    wf.node("pl_add", "n8n-nodes-base.httpRequest", 4.2, "YouTube: pôr na playlist", {
        "method": "POST", "url": "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {}},
        [2400, 200], yt, onError="continueRegularOutput", **RETRY)
    # thumbnail (só o resumo)
    wf.node("th", "n8n-nodes-base.code", 2, "Tem thumbnail?", {"jsCode": """const p = $('Plano de publicação').first().json;
return p.thumb_url ? [{ json: { youtube_id: $('Checar envio').first().json.youtube_id, thumb_url: p.thumb_url } }] : [];
"""}, [2160, 400], output=[{"youtube_id": "abc", "thumb_url": "s3://x"}])
    wf.node("th_s", "n8n-nodes-base.httpRequest", 4.2, "YouTube: sessão da thumbnail", yt_session(
        "=https://www.googleapis.com/upload/youtube/v3/thumbnails/set?uploadType=resumable&videoId={{ $json.youtube_id }}", "image/jpeg"),
        [2400, 400], yt, onError="continueRegularOutput", output=[{"headers": {"location": "https://upload"}}])
    wf.node("th_up", "n8n-nodes-base.httpRequest", 4.2, "Worker: enviar thumbnail", worker_job("youtube_upload",
        "{ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-thumb-' + $execution.id, "
        "input: { uploads: [ { ref: 'thumb', upload_url: $json.headers.location, media_url: $('Tem thumbnail?').first().json.thumb_url, content_type: 'image/jpeg' } ] } }"),
        [2640, 400], CRED["worker"], onError="continueRegularOutput")
    # gatilho manual: cria as playlists por esporte e grava na config do canal
    wf.node("t_pl", "n8n-nodes-base.manualTrigger", 1, "Criar playlists", {}, [0, 700], fn="trigger")
    wf.node("ch", "n8n-nodes-base.postgres", 2.5, "Canal", pg(PLAYLISTS_SQL, f"={{{{ [ '{slug}' ] }}}}"),
            [240, 700], CRED["pg"], output=[{"id": "c", "name": "Lance Rápido", "config": {}}], **RETRY)
    wf.node("falta", "n8n-nodes-base.code", 2, "Playlists que faltam", {"jsCode": """const r = $input.first().json;
const cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;
const have = cfg.youtube?.playlists || {};
const NAMES = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };
const desc = { futebol: 'Notícias de futebol em 1 minuto', nba: 'Notícias da NBA em 1 minuto', nfl: 'Notícias da NFL em 1 minuto' };
return Object.keys(NAMES).filter(s => !have[s]).map(s => ({ json: { sport: s, body: {
  snippet: { title: `${NAMES[s]} · ${r.name}`, description: `${desc[s]}. Shorts e resumos do dia do ${r.name}.`, defaultLanguage: 'pt-BR' },
  status: { privacyStatus: 'public' } } } }));
"""}, [480, 700], output=[{"sport": "nba", "body": {}}])
    wf.node("cria", "n8n-nodes-base.httpRequest", 4.2, "YouTube: criar playlist", {
        "method": "POST", "url": "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}", "options": {}},
        [720, 700], yt, output=[{"id": "PL"}])
    wf.node("junta", "n8n-nodes-base.code", 2, "Juntar ids", {"jsCode": """const sports = $('Playlists que faltam').all().map(i => i.json.sport);
const ids = $input.all().map(i => i.json.id);
return [{ json: { playlists: JSON.stringify(Object.fromEntries(sports.map((s, i) => [s, ids[i]]).filter(x => x[1]))) } }];
"""}, [960, 700], output=[{"playlists": "{}"}])
    wf.node("grava", "n8n-nodes-base.postgres", 2.5, "Gravar na config", pg(SAVE_PLAYLISTS_SQL,
        f"={{{{ [ '{slug}', $json.playlists ] }}}}"), [1200, 700], CRED["pg"], output=[{"playlists": {}}], **RETRY)
    return wf.render(
        "  .add(t_sub)\n  .to(config)\n  .to(load)\n  .to(plan)\n  .to(sess)\n  .to(up)\n  .to(w)\n  .to(c)\n  .to(save)\n  .to(msg)\n  .to(wa)\n"
        "  .add(save)\n  .to(pl)\n  .to(pl_add)\n  .add(save)\n  .to(th)\n  .to(th_s)\n  .to(th_up)\n"
        "  .add(t_pl)\n  .to(ch)\n  .to(falta)\n  .to(cria)\n  .to(junta)\n  .to(grava)")


if __name__ == "__main__":
    (OUT / "factory.news-short.js").write_text(build_news_short(), "utf-8")
    (OUT / "factory.news-recap.js").write_text(build_news_recap(), "utf-8")
    (OUT / "factory.publish.lance-rapido.js").write_text(build_publish_lance(), "utf-8")
    print("ok")
