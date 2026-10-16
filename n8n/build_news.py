"""Gera n8n/sdk/factory.news.js: coleta de pautas de esporte (RSS) para o Lance Rápido."""
from pathlib import Path
from build_fase2 import CRED, OUT, RETRY, WF, pg, send_text

HERE = Path(__file__).parent
code = lambda name: (HERE / "news" / name).read_text("utf-8")
OPENAI = {"httpHeaderAuth": {"id": "9OK91AZnXE70dKic", "name": "OpenAi - Fabrica"}}

CANAL_SQL = """WITH ch AS (SELECT id, config FROM channels WHERE slug = $1),
exp AS (
  UPDATE topics SET status = 'discarded'
  WHERE channel_id = (SELECT id FROM ch) AND status = 'queued'
    AND created_at < now() - make_interval(hours => COALESCE(((SELECT config FROM ch)->'news'->>'topic_ttl_hours')::int, 12))
  RETURNING id
)
SELECT ch.id, ch.config,
  (SELECT count(*) FROM topics t WHERE t.channel_id = ch.id AND t.status = 'queued') - (SELECT count(*) FROM exp) AS queued,
  COALESCE((SELECT json_agg(json_build_object('story_key', n.story_key, 'title', n.title_pt)) FROM (
     SELECT DISTINCT ON (story_key) story_key, title_pt FROM news_items
     WHERE channel_id = ch.id AND status = 'queued' AND created_at > now() - interval '48 hours' AND story_key IS NOT NULL
     ORDER BY story_key, created_at DESC) n), '[]'::json) AS recent
FROM ch;"""

GUARDAR_SQL = """-- novas desta rodada + as que ainda não foram avaliadas (ex.: a rodada anterior falhou)
WITH ins AS (
  INSERT INTO news_items (channel_id, url, title, summary, source, sport, published_at)
  SELECT $1::uuid, x.url, x.title, x.summary, x.source, x.sport, x.published_at
  FROM jsonb_to_recordset($2::jsonb) AS x(url text, title text, summary text, source text, sport text, published_at timestamptz)
  ON CONFLICT (channel_id, url) DO NOTHING
  RETURNING id, url, title, summary, source, sport, published_at
)
SELECT * FROM ins
UNION ALL
SELECT id, url, title, summary, source, sport, published_at FROM news_items
WHERE channel_id = $1::uuid AND status = 'new' AND published_at > now() - interval '18 hours';"""

SALVAR_SQL = """UPDATE news_items n SET score = u.score, story_key = u.story_key, title_pt = u.title_pt, reason = u.reason, status = u.status
FROM jsonb_to_recordset($2::jsonb) AS u(id uuid, score int, story_key text, title_pt text, reason text, status text)
WHERE n.id = u.id;
WITH ins AS (
  INSERT INTO topics (channel_id, title, notes, priority, source)
  SELECT $1::uuid, t.title, t.notes, t.priority, 'news'
  FROM jsonb_to_recordset($3::jsonb) AS t(title text, notes text, priority int)
  ON CONFLICT (channel_id, title) DO NOTHING
  RETURNING id, notes
)
UPDATE news_items n SET topic_id = ins.id
FROM ins WHERE n.channel_id = $1::uuid AND n.status = 'queued' AND n.topic_id IS NULL
  AND n.story_key = (ins.notes::jsonb->>'story_key');
SELECT count(*) AS pautas_na_fila FROM topics WHERE channel_id = $1::uuid AND status = 'queued';"""


def build_news() -> str:
    wf = WF("factory-news", "factory.news")
    wf.node("t_cron", "n8n-nodes-base.scheduleTrigger", 1.2, "De hora em hora (8h-23h)",
            {"rule": {"interval": [{"field": "cronExpression", "expression": "15 8-23 * * *"}]}}, [0, -100], fn="trigger")
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Rodar agora", {}, [0, 100], fn="trigger")
    wf.node("config", "n8n-nodes-base.set", 3.4, "Config", {"assignments": {"assignments": [
        {"id": "n-slug", "name": "channel_slug", "value": "lance-rapido", "type": "string"},
        {"id": "n-inst", "name": "evolution_instance", "value": "fabrica-videos", "type": "string"},
    ]}, "options": {}}, [240, 0])
    wf.node("canal", "n8n-nodes-base.postgres", 2.5, "Canal", pg(CANAL_SQL, "={{ [ $json.channel_slug ] }}"),
            [480, 0], CRED["pg"], output=[{"id": "c", "config": {}, "queued": 0, "recent": []}], **RETRY)
    wf.node("coletar", "n8n-nodes-base.code", 2, "Coletar feeds", {"jsCode": code("coletar.js")}, [720, 0],
            output=[{"channel_id": "c", "items": "[]", "n": 0, "errors": []}])
    wf.node("guardar", "n8n-nodes-base.postgres", 2.5, "Guardar novas", pg(GUARDAR_SQL, "={{ [ $json.channel_id, $json.items ] }}"),
            [960, 0], CRED["pg"], output=[{"id": "n", "url": "u", "title": "t", "sport": "nba"}], **RETRY)
    wf.node("pedido", "n8n-nodes-base.code", 2, "Pedido de avaliação", {"jsCode": code("pedido.js")}, [1200, 0],
            output=[{"body": {}, "ids": []}])
    wf.node("openai", "n8n-nodes-base.httpRequest", 4.2, "OpenAI: avaliar", {
        "method": "POST", "url": "https://api.openai.com/v1/responses",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.body) }}",
        "options": {"timeout": 300000}}, [1440, 0], OPENAI, output=[{"output": []}], **RETRY)
    wf.node("escolher", "n8n-nodes-base.code", 2, "Escolher pautas", {"jsCode": code("escolher.js")}, [1680, 0],
            output=[{"channel_id": "c", "updates": "[]", "topics": "[]", "picks": [], "number": "55"}])
    wf.node("salvar", "n8n-nodes-base.postgres", 2.5, "Salvar pautas",
            pg(SALVAR_SQL, "={{ [ $json.channel_id, $json.updates, $json.topics ] }}"),
            [1920, 0], CRED["pg"], output=[{"pautas_na_fila": 0}], **RETRY)
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem prévia", {"jsCode": code("mensagem.js")}, [2160, 0],
            output=[{"number": "55", "text": "x"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: pautas",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [2400, 0], CRED["evo"], **RETRY)
    return wf.render("  .add(t_cron)\n  .to(config)\n  .to(canal)\n  .to(coletar)\n  .to(guardar)\n  .to(pedido)\n  .to(openai)\n"
                     "  .to(escolher)\n  .to(salvar)\n  .to(msg)\n  .to(wa)\n  .add(t_manual)\n  .to(config)")


if __name__ == "__main__":
    (OUT / "factory.news.js").write_text(build_news(), "utf-8")
    print("ok")
