"""Gera o código do Workflow SDK de:

- factory.painel  : página do painel (GET /webhook/fabrica-painel?k=CHAVE) e ações (POST /webhook/fabrica-painel-acao)
- factory.metrics : a cada 6 h lê visualizações, likes e comentários dos vídeos publicados (YouTube Data API)

A chave do painel NÃO fica no repositório: passe em PAINEL_KEY ao gerar (o workflow no n8n guarda a chave real).
Saída: n8n/sdk/factory.painel.js e n8n/sdk/factory.metrics.js
"""
from __future__ import annotations

import os
from pathlib import Path

from build_fase2 import CRED, OUT, RETRY, PRODUCE_ID, CLIPS_ID, PUBLISH_DEFAULT, WF, pg

HERE = Path(__file__).parent
N8N_URL = "https://n8n.relampagodeofertas.shop"
PAINEL_KEY = os.environ.get("PAINEL_KEY", "TROQUE-ESTA-CHAVE")


def exec_wf(name, wid_expr, inputs: dict, pos, mode="once"):
    schema = [{"id": k, "displayName": k, "required": False, "defaultMatch": False, "display": True,
               "canBeUsedToMatch": True, "type": "string"} for k in inputs]
    return {"mode": mode, "source": "database", "workflowId": {"__rl": True, "mode": "id", "value": wid_expr},
            "workflowInputs": {"mappingMode": "defineBelow", "value": inputs, "matchingColumns": [], "schema": schema},
            "options": {"waitForSubWorkflow": False}}


DECIDE = r"""// Valida a ação pedida pelo painel. Sempre responde { ok, message } para a página.
const req = $('Config').first().json.body || {};
const t = $input.first().json;
const cfg = typeof t.config === 'string' ? JSON.parse(t.config || 'null') : t.config;
const out = (route, ok, message, extra = {}) => [{ json: { route, ok, message, ...extra } }];
const action = String(req.action || '');
if (action === 'produce') {
  if (!t.slug) return out('error', false, 'Canal não encontrado.');
  if (!t.active) return out('error', false, 'Canal pausado.');
  return out('produce', true, `Produção de ${cfg.name} iniciada. Acompanhe na esteira.`, { channel_slug: t.slug });
}
if (!t.video_id) return out('error', false, 'Vídeo não encontrado.');
if (action === 'approve') {
  if (t.status !== 'awaiting_approval') return out('error', false, `Este vídeo está em "${t.status}", não dá para aprovar.`);
  return out('approve', true, 'Aprovado. O agendamento no YouTube começou; o aviso chega no WhatsApp.', {
    video_id: t.video_id, publish_workflow_id: cfg.youtube?.publish_workflow_id || 'PUBLISH_DEFAULT_ID' });
}
if (action === 'reject') {
  if (t.status !== 'awaiting_approval') return out('error', false, `Este vídeo está em "${t.status}", não dá para rejeitar.`);
  return out('reject', true, 'Rejeitado.', { video_id: t.video_id, reason: String(req.reason || '').slice(0, 500) });
}
if (action === 'requeue') {
  if (!['failed', 'rejected'].includes(t.status)) return out('error', false, 'Só vídeos com falha ou rejeitados devolvem o tema.');
  if (!t.topic_id) return out('error', false, 'Vídeo sem tema.');
  if (t.topic_status === 'queued') return out('error', false, 'O tema já está na fila.');
  return out('requeue', true, 'Tema de volta à fila.', { topic_id: t.topic_id });
}
return out('error', false, 'Ação desconhecida.');
"""


def build_painel() -> str:
    wf = WF("factory-painel", "factory.painel")
    wf.node("h_get", "n8n-nodes-base.webhook", 2.1, "Abrir painel", {
        "httpMethod": "GET", "path": "fabrica-painel", "responseMode": "responseNode",
        "options": {"ignoreBots": True}}, [0, -100], fn="trigger", output=[{"query": {"k": "x"}}])
    wf.node("h_post", "n8n-nodes-base.webhook", 2.1, "Ação do painel", {
        "httpMethod": "POST", "path": "fabrica-painel-acao", "responseMode": "responseNode", "options": {}},
        [0, 100], fn="trigger", output=[{"body": {"k": "x", "action": "approve", "video_id": "v"}}])
    wf.node("config", "n8n-nodes-base.set", 3.4, "Config", {"assignments": {"assignments": [
        {"id": "p-key", "name": "painel_key", "value": PAINEL_KEY, "type": "string"},
        {"id": "p-url", "name": "action_url", "value": N8N_URL + "/webhook/fabrica-painel-acao", "type": "string"},
    ]}, "includeOtherFields": True, "options": {}}, [240, 0])
    wf.node("gate", "n8n-nodes-base.switch", 3.4, "Chave e tipo", {
        "mode": "expression", "numberOutputs": 3,
        "output": "={{ (($json.query?.k || $json.body?.k) !== $json.painel_key) ? 2 : ($json.body?.action ? 1 : 0) }}"},
        [480, 0], fn="switchCase")
    wf.node("data", "n8n-nodes-base.postgres", 2.5, "Dados", pg((HERE / "painel" / "dados.sql").read_text("utf-8"), None),
            [720, -200], CRED["pg"], output=[{"channels": [], "videos": [], "calendar": [], "performance": [], "costs": [], "images_today_est": 0}], **RETRY)
    wf.node("page", "n8n-nodes-base.code", 2, "Página", {"jsCode": (HERE / "painel" / "pagina.js").read_text("utf-8")},
            [960, -200], output=[{"html": "<html>"}])
    wf.node("r_page", "n8n-nodes-base.respondToWebhook", 1.5, "Responder página", {
        "respondWith": "text", "responseBody": "={{ $json.html }}",
        "options": {"responseHeaders": {"entries": [
            {"name": "Content-Type", "value": "text/html; charset=utf-8"},
            {"name": "Cache-Control", "value": "no-store"},
            {"name": "X-Robots-Tag", "value": "noindex"}]}}}, [1200, -200])
    wf.node("r_deny", "n8n-nodes-base.respondToWebhook", 1.5, "Negar", {
        "respondWith": "text", "responseBody": "Not found", "options": {"responseCode": 404}}, [720, 200])
    wf.node("target", "n8n-nodes-base.postgres", 2.5, "Carregar alvo", pg(
        "SELECT v.id AS video_id, v.status::text AS status, v.topic_id, t.status::text AS topic_status, c.config, c.slug, c.active\n"
        "FROM videos v JOIN channels c ON c.id = v.channel_id LEFT JOIN topics t ON t.id = v.topic_id\n"
        "WHERE $1 <> '' AND v.id = NULLIF($1, '')::uuid\n"
        "UNION ALL\n"
        "SELECT NULL, NULL, NULL, NULL, c.config, c.slug, c.active FROM channels c WHERE $1 = '' AND c.slug = $2;",
        "={{ [ $json.body.video_id || '', $json.body.channel_slug || '' ] }}"),
        [720, 0], CRED["pg"], alwaysOutputData=True, output=[{"video_id": "v", "status": "awaiting_approval", "config": {}}], **RETRY)
    wf.node("decide", "n8n-nodes-base.code", 2, "Decidir", {"jsCode": DECIDE.replace("PUBLISH_DEFAULT_ID", PUBLISH_DEFAULT)},
            [960, 0], output=[{"route": "approve", "ok": True, "message": "ok", "video_id": "v"}])
    wf.node("route", "n8n-nodes-base.switch", 3.4, "Rota", {
        "mode": "expression", "numberOutputs": 5,
        "output": "={{ ({ approve: 0, reject: 1, requeue: 2, produce: 3 })[$json.route] ?? 4 }}"}, [1200, 0], fn="switchCase")
    wf.node("ok", "n8n-nodes-base.postgres", 2.5, "Registrar aprovação", pg(
        "INSERT INTO approvals (video_id, decision, decided_by) VALUES ($1::uuid, 'approved', 'painel');",
        "={{ [ $json.video_id ] }}"), [1440, -300], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("pub", "n8n-nodes-base.executeWorkflow", 1.3, "Publicar no YouTube", exec_wf(
        "pub", "={{ $('Decidir').first().json.publish_workflow_id }}", {"video_id": "={{ $('Decidir').first().json.video_id }}"}, None),
        [1680, -300], output=[{}])
    wf.node("clips", "n8n-nodes-base.executeWorkflow", 1.3, "Clipes TikTok", exec_wf(
        "clips", CLIPS_ID, {"video_id": "={{ $('Decidir').first().json.video_id }}"}, None), [1920, -300], output=[{}])
    wf.node("no", "n8n-nodes-base.postgres", 2.5, "Registrar rejeição", pg(
        "WITH a AS (\n  INSERT INTO approvals (video_id, decision, reason, decided_by) VALUES ($1::uuid, 'rejected', NULLIF($2, ''), 'painel')\n)\n"
        "UPDATE videos SET status = 'rejected', updated_at = now() WHERE id = $1::uuid AND status = 'awaiting_approval';",
        "={{ [ $json.video_id, $json.reason || '' ] }}"), [1440, -150], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("rq", "n8n-nodes-base.postgres", 2.5, "Devolver tema", pg(
        "UPDATE topics SET status = 'queued' WHERE id = $1::uuid;", "={{ [ $json.topic_id ] }}"),
        [1440, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("prod", "n8n-nodes-base.executeWorkflow", 1.3, "Produzir agora", exec_wf(
        "prod", PRODUCE_ID, {"channel_slug": "={{ $json.channel_slug }}"}, None), [1440, 150], output=[{}])
    wf.node("r_act", "n8n-nodes-base.respondToWebhook", 1.5, "Responder ação", {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ ok: $('Decidir').first().json.ok, message: $('Decidir').first().json.message }) }}",
        "options": {}}, [2160, 0])
    return wf.render(
        "  .add(h_get)\n  .to(config)\n"
        "  .to(gate\n    .onCase(0, data.to(page.to(r_page)))\n    .onCase(1, target.to(decide.to(route\n"
        "      .onCase(0, ok.to(pub.to(clips.to(r_act))))\n      .onCase(1, no.to(r_act))\n      .onCase(2, rq.to(r_act))\n"
        "      .onCase(3, prod.to(r_act))\n      .onCase(4, r_act))))\n    .onCase(2, r_deny))\n  .add(h_post)\n  .to(config)")


METRICS_SPLIT = r"""// Lotes de até 50 ids por chamada (videos.list custa 1 unidade de cota por chamada).
const ids = [...new Set($input.all().map(i => i.json.external_id).filter(Boolean))];
const out = [];
for (let i = 0; i < ids.length; i += 50) out.push({ json: { ids: ids.slice(i, i + 50).join(',') } });
return out;
"""

METRICS_ROWS = r"""const rows = [];
for (const it of $input.all()) {
  for (const v of it.json.items || []) {
    const s = v.statistics || {};
    rows.push({ external_id: v.id, views: Number(s.viewCount ?? 0), likes: s.likeCount != null ? Number(s.likeCount) : null,
      comments: s.commentCount != null ? Number(s.commentCount) : null, privacy: v.status?.privacyStatus || null });
  }
}
return [{ json: { rows: JSON.stringify(rows), n: rows.length } }];
"""

METRICS_SAVE = """WITH d AS (
  SELECT * FROM jsonb_to_recordset($1::jsonb) AS x(external_id text, views int, likes int, comments int, privacy text)
), pubs AS (
  UPDATE publications p SET status = 'published'
  FROM d WHERE p.external_id = d.external_id AND d.privacy = 'public' AND p.status = 'scheduled'
  RETURNING p.video_id, p.kind
), vids AS (
  UPDATE videos v SET status = 'published', updated_at = now()
  WHERE v.id IN (SELECT video_id FROM pubs WHERE kind = 'long') AND v.status = 'scheduled'
)
INSERT INTO metrics (publication_id, date, views, likes, comments, updated_at)
SELECT p.id, (now() AT TIME ZONE 'America/Sao_Paulo')::date, d.views, d.likes, d.comments, now()
FROM d JOIN publications p ON p.external_id = d.external_id
ON CONFLICT (publication_id, date) DO UPDATE
  SET views = EXCLUDED.views, likes = EXCLUDED.likes, comments = EXCLUDED.comments, updated_at = now();"""


def build_metrics() -> str:
    wf = WF("factory-metrics", "factory.metrics")
    wf.node("t_cron", "n8n-nodes-base.scheduleTrigger", 1.2, "A cada 6 horas",
            {"rule": {"interval": [{"field": "hours", "hoursInterval": 6, "triggerAtMinute": 20}]}}, [0, -100], fn="trigger")
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Coletar agora", {}, [0, 100], fn="trigger")
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Publicações", pg(
        "SELECT p.external_id FROM publications p\n"
        "WHERE p.platform = 'youtube' AND p.external_id IS NOT NULL AND p.status IN ('scheduled', 'published')\n"
        "  AND p.created_at > now() - interval '120 days'\n"
        "ORDER BY p.created_at DESC LIMIT 1000;", None), [240, 0], CRED["pg"], output=[{"external_id": "abc"}], **RETRY)
    wf.node("split", "n8n-nodes-base.code", 2, "Lotes de 50", {"jsCode": METRICS_SPLIT}, [480, 0], output=[{"ids": "a,b"}])
    wf.node("yt", "n8n-nodes-base.httpRequest", 4.2, "YouTube: estatísticas", {
        "method": "GET", "url": "=https://www.googleapis.com/youtube/v3/videos?part=statistics,status&maxResults=50&id={{ $json.ids }}",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api", "options": {"timeout": 60000}},
        [720, 0], CRED["yt"], output=[{"items": []}], **RETRY)
    wf.node("rows", "n8n-nodes-base.code", 2, "Juntar", {"jsCode": METRICS_ROWS}, [960, 0], output=[{"rows": "[]", "n": 0}])
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Salvar métricas", pg(METRICS_SAVE, "={{ [ $json.rows ] }}"),
            [1200, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    return wf.render("  .add(t_cron)\n  .to(load)\n  .to(split)\n  .to(yt)\n  .to(rows)\n  .to(save)\n  .add(t_manual)\n  .to(load)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "factory.painel.js").write_text(build_painel(), "utf-8")
    (OUT / "factory.metrics.js").write_text(build_metrics(), "utf-8")
    print("ok")
