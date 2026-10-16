"""Gera o código do Workflow SDK (n8n) da Fase 2:

- factory.package  : Shorts, thumbnails e metadados (worker) + mensagem de aprovação no WhatsApp
- factory.approval : recebe a resposta no WhatsApp (Evolution) e aprova, rejeita ou troca thumbnail/título
- factory.publish  : envia vídeo, thumbnail e Shorts ao YouTube, agendados

Saída: n8n/sdk/*.js (criados no n8n pelo conector MCP com create_workflow_from_code).
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "sdk"
WORKER_URL = "https://render.relampagodeofertas.shop"
INSTANCE = "fabrica-videos"
CLIPS_ID = "f98b6HG2uClowRB4"  # factory.clips no n8n
PRODUCE_ID = "6ZhBwxhg575IOsSC"  # factory.produce no n8n
PUBLISH_DEFAULT = "y3zthNcqybMcQEl0"  # factory.publish do Career Levels
YOUTUBE_SCOPE_NOTE = ""

CRED = {
    "pg": {"postgres": {"id": "CgrwOpkbdW4VgyTc", "name": "Postgres - Fabrica"}},
    "worker": {"httpHeaderAuth": {"id": "R96vQrkAjGn3GHEt", "name": "Auth - Fabrica Worker"}},
    "callback": {"httpHeaderAuth": {"id": "dBAcX42kLwL5n3eW", "name": "Auth - Fabrica Callback"}},
    "evo": {"evolutionApi": {"id": "570ZlMjp90Xd9ZZk", "name": "Evolution API"}},
    "yt": {"youTubeOAuth2Api": {"id": "nnKxTYcW1aFdkd4a", "name": "YouTube - Fabrica"}},
}
RETRY = {"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000}


def js(v, ind=0):
    pad = "  " * ind
    if isinstance(v, str):
        if v.startswith("="):
            return "expr(" + json.dumps(v[1:], ensure_ascii=False) + ")"
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, bool) or v is None or isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, dict):
        if not v:
            return "{}"
        return "{\n" + ",\n".join(f"{pad}  {json.dumps(k)}: {js(x, ind + 1)}" for k, x in v.items()) + f"\n{pad}}}"
    if isinstance(v, list):
        if not v:
            return "[]"
        return "[\n" + ",\n".join(f"{pad}  {js(x, ind + 1)}" for x in v) + f"\n{pad}]"
    raise TypeError(v)


class WF:
    def __init__(self, wid, name):
        self.wid, self.name, self.decls, self.n = wid, name, [], 0

    def node(self, var, typ, ver, name, params, pos, creds=None, fn="node", output=None, **settings):
        cfg = {"name": name, "parameters": params}
        if creds:
            cfg["credentials"] = creds
        cfg.update(settings)
        cfg["position"] = pos
        out = js(output if output is not None else [{}], 1)
        self.decls.append(f"const {var} = {fn}({{\n  type: {json.dumps(typ)},\n  version: {ver},\n"
                          f"  config: {js(cfg, 1)},\n  output: {out}\n}});\n")
        return var

    def render(self, chain: str) -> str:
        head = "import { workflow, node, trigger, switchCase, ifElse, expr } from '@n8n/workflow-sdk';\n\n"
        return head + "\n".join(self.decls) + f"\nexport default workflow({json.dumps(self.wid)}, {json.dumps(self.name)})\n{chain};\n"


def pg(query, replacement):
    if replacement is None:
        return {"operation": "executeQuery", "query": query, "options": {}}
    return {"operation": "executeQuery", "query": query, "options": {"queryReplacement": replacement}}


def worker_job(job_type, body_expr):
    return {
        "method": "POST", "url": "={{ $('Config').first().json.worker_url }}/jobs/" + job_type,
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify(" + body_expr + ") }}",
        "options": {"timeout": 120000},
    }


def wait(hours):
    return {"resume": "webhook", "httpMethod": "POST", "authentication": "headerAuth", "limitWaitTime": True,
            "limitType": "afterTimeInterval", "resumeAmount": hours, "resumeUnit": "hours", "options": {}}


def check_code(label):
    return {"jsCode": (
        "// O worker chama a URL de retomada do Wait com o resultado do job.\n"
        "const b = $input.first().json.body;\n"
        f"if (!b) throw new Error('{label}: tempo esgotado esperando o worker');\n"
        f"if (b.status !== 'succeeded') throw new Error('{label} falhou no worker: ' + (b.error || 'sem detalhe'));\n"
        "return [{ json: b.result }];\n")}


def send_text(number_expr, text_expr):
    return {"resource": "messages-api", "operation": "send-text", "instanceName": "={{ $('Config').first().json.evolution_instance }}",
            "remoteJid": number_expr, "messageText": text_expr}


def config_node(wf, extra=None, pos=(240, 0)):
    assigns = [
        {"id": "c-worker", "name": "worker_url", "value": WORKER_URL, "type": "string"},
        {"id": "c-instance", "name": "evolution_instance", "value": INSTANCE, "type": "string"},
    ] + (extra or [])
    return wf.node("config", "n8n-nodes-base.set", 3.4, "Config",
                   {"assignments": {"assignments": assigns}, "includeOtherFields": True, "options": {}}, list(pos))


# ===========================================================================
# factory.package
# ===========================================================================
def build_package() -> str:
    wf = WF("factory-package", "factory.package")
    wf.node("t_sub", "n8n-nodes-base.executeWorkflowTrigger", 1.2, "Chamado pelo produce",
            {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "video_id", "type": "string"}]}},
            [0, -100], fn="trigger", output=[{"video_id": "uuid"}])
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Testar com o último vídeo", {}, [0, 100], fn="trigger")
    config_node(wf)
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Carregar vídeo", pg(
        "SELECT v.id AS video_id, v.spec, c.config,\n"
        "  (SELECT a.url FROM assets a WHERE a.video_id = v.id AND a.kind = 'spec' ORDER BY a.created_at DESC LIMIT 1) AS spec_url\n"
        "FROM videos v JOIN channels c ON c.id = v.channel_id\n"
        "WHERE v.id = COALESCE(NULLIF($1::text, '')::uuid,\n"
        "  (SELECT id FROM videos WHERE status IN ('derivatives', 'awaiting_approval') ORDER BY created_at DESC LIMIT 1));",
        "={{ [ $json.video_id || '' ] }}"), [480, 0], CRED["pg"], output=[{"video_id": "v", "spec": {}, "config": {}, "spec_url": "s3://x"}], **RETRY)
    wf.node("st", "n8n-nodes-base.postgres", 2.5, "Status: pacote", pg(
        "UPDATE videos SET status = 'derivatives', updated_at = now() WHERE id = $1::uuid;",
        "={{ [ $('Carregar vídeo').first().json.video_id ] }}"), [720, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("job", "n8n-nodes-base.httpRequest", 4.2, "Worker: pacote", worker_job("package",
        "{ video_id: $('Carregar vídeo').first().json.video_id, idempotency_key: $('Carregar vídeo').first().json.video_id + '-package-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: { spec_url: $('Carregar vídeo').first().json.spec_url, config: $('Carregar vídeo').first().json.config } }"),
        [960, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("wait", "n8n-nodes-base.wait", 1.1, "Aguardar pacote", wait(2), [1200, 0], CRED["callback"],
            output=[{"body": {"status": "succeeded", "result": {}}}])
    wf.node("chk", "n8n-nodes-base.code", 2, "Checar pacote", check_code("Pacote"), [1440, 0],
            output=[{"spec": {}, "shorts": [], "thumbnails": [], "outputs": {}, "checks": []}])
    wf.node("links", "n8n-nodes-base.httpRequest", 4.2, "Links temporários", {
        "method": "POST", "url": "={{ $('Config').first().json.worker_url }}/files/presign",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ urls: [ $json.outputs.preview_url, $json.outputs.final_url, ...$json.thumbnails.map(t => t.url), ...$json.shorts.map(s => s.url) ], expires_s: 172800 }) }}",
        "options": {"timeout": 120000}}, [1680, 0], CRED["worker"], output=[{"urls": []}], **RETRY)
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Salvar pacote", pg(
        "WITH v AS (\n"
        "  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid RETURNING id\n"
        "), ck AS (\n"
        "  INSERT INTO checks (video_id, stage, name, passed, detail)\n"
        "  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)\n"
        "  FROM jsonb_array_elements($3::jsonb) c\n"
        ")\n"
        "INSERT INTO assets (video_id, kind, url, meta)\n"
        "SELECT $1::uuid, (a->>'k')::asset_kind, a->>'u', COALESCE(a->'meta', '{}'::jsonb)\n"
        "FROM jsonb_array_elements($4::jsonb) a;",
        "={{ (() => { const r = $('Checar pacote').first().json; const assets = [ ...r.thumbnails.map(t => ({ k: 'thumb', u: t.url, meta: { n: t.n, check: t.check } })), ...r.shorts.map(s => ({ k: 'short', u: s.url, meta: { n: s.n, start_s: s.start_s, end_s: s.end_s } })) ]; "
        "return [ $('Carregar vídeo').first().json.video_id, JSON.stringify(r.spec), JSON.stringify(r.checks || []), JSON.stringify(assets) ]; })() }}"),
        [1920, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem de aprovação", {"jsCode": r"""const r = $('Checar pacote').first().json;
const urls = $('Links temporários').first().json.urls;
const [preview, final] = urls;
const nT = r.thumbnails.length;
const thumbLinks = urls.slice(2, 2 + nT);
const shortLinks = urls.slice(2 + nT);
const spec = r.spec;
const cfg = $('Carregar vídeo').first().json.config;
const code = String($('Carregar vídeo').first().json.video_id).slice(0, 4).toUpperCase();
const d = Math.round(r.outputs.duration_s || 0);
const dur = `${Math.floor(d / 60)}:${String(d % 60).padStart(2, '0')}`;
const failed = (spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);
const titles = (spec.titles || []).slice(0, 5);
const current = spec.publishing?.title || spec.chosen_title;
const lines = [
  `🎬 *Vídeo pronto para revisão* · ${cfg.name} · código *#${code}*`,
  `*${current}*`,
  `Duração: ${dur} · ${spec.blocks.length} blocos · ${(spec.sources || []).length} fontes`,
  failed.length ? `⚠️ Checagens com alerta:\n${failed.join('\n')}` : '✅ Todas as checagens passaram',
  '',
  `▶️ Preview (480p): ${preview}`,
  `⬇️ Vídeo final: ${final}`,
  '',
  '📱 *Shorts*',
  ...r.shorts.map((s, i) => `${i + 1}. ${s.hook} (${Math.round(s.duration_s)}s): ${shortLinks[i]}`),
  '',
  '📝 *Títulos*',
  ...titles.map((t, i) => `${i + 1}. ${t}${t === spec.chosen_title ? ' ✅' : ''}`),
  '',
  `🖼️ Thumbnails nas próximas mensagens (sugerida: ${spec.thumbnail?.chosen || 1})`,
  '',
  '*Responda:*',
  '1 → aprovar e agendar no YouTube',
  '2 motivo → rejeitar (ex.: 2 imagens fracas)',
  '3 N → usar a thumbnail N',
  '4 N → usar o título N',
  `Com mais de um vídeo pendente, inclua o código: 1 #${code}`,
  '',
  'Links válidos por 48 h.',
];
return [{ json: {
  number: cfg.approval.to,
  text: lines.join('\n'),
  thumbs: r.thumbnails.map((t, i) => ({ n: t.n, url: thumbLinks[i], legible: t.check?.passed })),
  chosen: spec.thumbnail?.chosen || 1,
  code,
} }];
"""}, [2160, 0], output=[{"number": "55", "text": "x", "thumbs": [], "chosen": 1}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: pedir aprovação",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [2400, 0], CRED["evo"], **RETRY)
    wf.node("thumbs", "n8n-nodes-base.code", 2, "Uma mensagem por thumbnail", {"jsCode": r"""const m = $('Mensagem de aprovação').first().json;
return m.thumbs.map(t => ({ json: {
  number: m.number,
  media: t.url,
  caption: `#${m.code} · Thumbnail ${t.n}${t.n === m.chosen ? ' (sugerida)' : ''}${t.legible === false ? ' · ⚠️ texto pequeno' : ''}`,
} }));
"""}, [2640, 0], output=[{"number": "55", "media": "https://x", "caption": "Thumbnail 1"}])
    wf.node("wa_img", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: thumbnails", {
        "resource": "messages-api", "operation": "send-image",
        "instanceName": "={{ $('Config').first().json.evolution_instance }}",
        "remoteJid": "={{ $json.number }}", "media": "={{ $json.media }}", "caption": "={{ $json.caption }}"},
        [2880, 0], CRED["evo"], **RETRY)
    return wf.render(
        "  .add(t_sub)\n  .to(config)\n  .to(load)\n  .to(st)\n  .to(job)\n  .to(wait)\n  .to(chk)\n  .to(links)\n"
        "  .to(save)\n  .to(msg)\n  .to(wa)\n  .to(thumbs)\n  .to(wa_img)\n  .add(t_manual)\n  .to(config)")


# ===========================================================================
# factory.approval
# ===========================================================================
def build_approval(publish_id: str = PUBLISH_DEFAULT) -> str:
    wf = WF("factory-approval", "factory.approval")
    wf.node("hook", "n8n-nodes-base.webhook", 2.1, "Evolution: mensagem recebida", {
        "httpMethod": "POST", "path": "fabrica-aprovacao", "responseMode": "onReceived",
        "options": {"onlyRunIf": "={{ $json.body.event === 'messages.upsert' && !String($json.body.data?.key?.remoteJid || '').endsWith('@g.us') }}"}},
        [0, 0], fn="trigger", output=[{"body": {"event": "messages.upsert", "data": {"key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": False}, "message": {"conversation": "1"}}}}])
    config_node(wf, pos=(240, 0))
    wf.node("read", "n8n-nodes-base.code", 2, "Ler resposta", {"jsCode": r"""// Só segue para mensagens de texto que sejam um comando 1, 2, 3 ou 4.
// A instância da fábrica é o próprio número do Will: as respostas vêm do chat "Você" (mensagem para si mesmo),
// que chegam como fromMe = true. Mensagens de outras pessoas e de grupos são ignoradas.
const b = $input.first().json.body || {};
const ev = String(b.event || '').toLowerCase().replace(/_/g, '.');
const d = Array.isArray(b.data) ? b.data[0] || {} : (b.data || {});
const key = d.key || {};
const raw = String(d.message?.conversation || d.message?.extendedTextMessage?.text || '').trim();
// código do vídeo (#AB12) opcional, em qualquer posição: "1 #AB12", "#AB12 3 2"
const codeM = raw.match(/#\s*([0-9a-fA-F]{4})\b/);
const code = codeM ? codeM[1].toLowerCase() : '';
const text = raw.replace(/#\s*[0-9a-fA-F]{4}\b/, ' ').replace(/\s+/g, ' ').trim();
if (!ev.includes('messages.upsert') || !text) return [];
const cmd = text.match(/^([1-4])(?:[\s.,:-]+([\s\S]*))?$/);
if (!cmd) return [];
const num = j => String(j || '').split('@')[0].replace(/\D/g, '');
const isPhone = j => j && /@s\.whatsapp\.net$/.test(String(j));
const chat = [key.remoteJid, key.remoteJidAlt, key.senderPn].filter(isPhone).map(num).filter(x => x.length >= 10);
if (String(key.remoteJid || '').endsWith('@g.us') || !chat.length) return [];
const owner = num(b.sender);
if (key.fromMe) {
  // só vale se for o chat com você mesmo
  if (!owner || !chat.some(x => x.slice(-8) === owner.slice(-8))) return [];
}
return [{ json: {
  cmd: Number(cmd[1]),
  arg: (cmd[2] || '').trim(),
  code,
  sender: chat[0],
  last8: '{' + [...new Set(chat.map(x => x.slice(-8)))].join(',') + '}',
} }];
"""}, [480, 0], output=[{"cmd": 1, "arg": "", "code": "", "sender": "5511999999999", "last8": "{99999999}"}])
    wf.node("find", "n8n-nodes-base.postgres", 2.5, "Vídeo aguardando", pg(
        "SELECT v.id AS video_id, upper(left(v.id::text, 4)) AS code, v.spec, c.config, c.name AS channel_name\n"
        "FROM videos v JOIN channels c ON c.id = v.channel_id\n"
        "WHERE v.status = 'awaiting_approval'\n"
        "  AND right(regexp_replace(c.config->'approval'->>'to', '\\D', '', 'g'), 8) = ANY($1::text[])\n"
        "ORDER BY v.created_at DESC LIMIT 20;",
        "={{ [ $json.last8 ] }}"), [720, 0], CRED["pg"], alwaysOutputData=True,
        output=[{"video_id": "v", "code": "ABCD", "spec": {}, "config": {}, "channel_name": "c"}], **RETRY)
    wf.node("decide", "n8n-nodes-base.code", 2, "Interpretar", {"jsCode": r"""const m = $('Ler resposta').first().json;
const parse = x => typeof x === 'string' ? JSON.parse(x) : x;
const rows = $input.all().map(i => i.json).filter(r => r.video_id);
// sem vídeo aguardando para esse número: não responde (evita responder "1" de qualquer conversa)
if (!rows.length) return [];
const titleOf = r => { const s = parse(r.spec); return s.publishing?.title || s.chosen_title; };
const list = rows.map(r => `#${r.code} · ${r.channel_name} · ${titleOf(r)}`).join('\n');
const number0 = parse(rows[0].config).approval?.to || m.sender;
const help = reply => [{ json: { action: 'help', reply, number: number0 } }];
let v;
if (m.code) {
  const hits = rows.filter(r => r.code.toLowerCase() === m.code);
  if (!hits.length) return help(`Não achei vídeo aguardando aprovação com o código #${m.code.toUpperCase()}.\n\nPendentes:\n${list}`);
  if (hits.length > 1) return help(`Mais de um vídeo com o código #${m.code.toUpperCase()}. Responda pelo YouTube Studio ou rejeite um deles.\n\n${list}`);
  v = hits[0];
} else if (rows.length > 1) {
  return help(`Há ${rows.length} vídeos aguardando aprovação. Inclua o código na resposta, ex.: ${m.cmd}${m.arg ? ' ' + m.arg : ''} #${rows[0].code}\n\n${list}`);
} else {
  v = rows[0];
}
const spec = parse(v.spec);
const cfg = parse(v.config);
const number = cfg.approval?.to || m.sender;
const title = spec.publishing?.title || spec.chosen_title;
const tag = `[${v.channel_name} #${v.code}]`;
// canal de notícias: publica na hora e não gera clipes de TikTok
const news = cfg.format?.type === 'news_short';
let action = 'help';
let reply = '';
if (m.cmd === 1) {
  action = 'approve';
  reply = news
    ? `✅ Aprovado ${tag}: *${title}*\nPublicando no YouTube agora; te aviso com o link.`
    : `✅ Aprovado ${tag}: *${title}*\nVou agendar no YouTube e te aviso com os links.`;
} else if (m.cmd === 2) {
  action = 'reject';
  reply = `🗑️ Rejeitado ${tag}: *${title}*${m.arg ? `\nMotivo: ${m.arg}` : ''}`;
} else if (m.cmd === 3) {
  const n = parseInt(m.arg, 10);
  const opts = spec.thumbnail?.options || [];
  if (!(n >= 1 && n <= opts.length)) reply = `Escolha uma thumbnail de 1 a ${opts.length}. Ex.: 3 2 #${v.code}`;
  else { spec.thumbnail.chosen = n; action = 'edit'; reply = `🖼️ ${tag} Thumbnail ${n} escolhida.`; }
} else if (m.cmd === 4) {
  const n = parseInt(m.arg, 10);
  const titles = (spec.titles || []).slice(0, 5);
  if (!(n >= 1 && n <= titles.length)) reply = `Escolha um título de 1 a ${titles.length}. Ex.: 4 3 #${v.code}`;
  else {
    spec.chosen_title = titles[n - 1];
    spec.publishing = { ...(spec.publishing || {}), title: titles[n - 1].replace(/[<>]/g, '').slice(0, 100) };
    action = 'edit';
    reply = `📝 ${tag} Título ${n}: *${titles[n - 1]}*`;
  }
}
if (action === 'edit') reply += `\n\nResponda 1 #${v.code} para aprovar, 2 #${v.code} para rejeitar, 3 N (thumbnail) ou 4 N (título).`;
return [{ json: { action, reply, number, video_id: v.video_id, spec, reason: m.arg, sender: m.sender, clips: !news,
  publish_workflow_id: cfg.youtube?.publish_workflow_id || 'PUBLISH_DEFAULT_ID' } }];
""".replace('PUBLISH_DEFAULT_ID', publish_id)}, [960, 0], output=[{"action": "approve", "reply": "ok", "number": "55", "video_id": "v", "spec": {}, "reason": "", "sender": "55", "publish_workflow_id": "x"}])
    wf.node("route", "n8n-nodes-base.switch", 3.4, "Ação", {
        "mode": "expression", "numberOutputs": 4,
        "output": "={{ ({ approve: 0, reject: 1, edit: 2 })[$json.action] ?? 3 }}"}, [1200, 0], fn="switchCase")
    wf.node("ok", "n8n-nodes-base.postgres", 2.5, "Registrar aprovação", pg(
        "INSERT INTO approvals (video_id, decision, decided_by) VALUES ($1::uuid, 'approved', $2);",
        "={{ [ $json.video_id, $json.sender ] }}"), [1440, -200], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("pub", "n8n-nodes-base.executeWorkflow", 1.3, "Publicar no YouTube", {
        "mode": "once", "source": "database",
        # cada canal tem o seu factory.publish (credencial do YouTube própria): config.youtube.publish_workflow_id
        "workflowId": {"__rl": True, "mode": "id", "value": "={{ $('Interpretar').first().json.publish_workflow_id }}"},
        "workflowInputs": {"mappingMode": "defineBelow",
                           "value": {"video_id": "={{ $('Interpretar').first().json.video_id }}"},
                           "matchingColumns": [], "schema": [{"id": "video_id", "displayName": "video_id", "required": False,
                                                              "defaultMatch": False, "display": True, "canBeUsedToMatch": True, "type": "string"}]},
        "options": {"waitForSubWorkflow": False}}, [1680, -200], output=[{}])
    wf.node("clips", "n8n-nodes-base.executeWorkflow", 1.3, "Clipes TikTok", {
        "mode": "once", "source": "database",
        "workflowId": {"__rl": True, "mode": "id", "value": CLIPS_ID},
        "workflowInputs": {"mappingMode": "defineBelow",
                           "value": {"video_id": "={{ $('Interpretar').first().json.video_id }}"},
                           "matchingColumns": [], "schema": [{"id": "video_id", "displayName": "video_id", "required": False,
                                                              "defaultMatch": False, "display": True, "canBeUsedToMatch": True, "type": "string"}]},
        "options": {"waitForSubWorkflow": False}}, [1800, -200], output=[{}])
    wf.node("gate", "n8n-nodes-base.if", 2.2, "Gera clipes?", {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose"},
        "conditions": [{"leftValue": "={{ $('Interpretar').first().json.clips }}", "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}],
        "combinator": "and"}, "options": {}}, [1740, -200], fn="ifElse")
    wf.node("no", "n8n-nodes-base.postgres", 2.5, "Registrar rejeição", pg(
        "WITH a AS (\n  INSERT INTO approvals (video_id, decision, reason, decided_by) VALUES ($1::uuid, 'rejected', NULLIF($2, ''), $3)\n)\n"
        "UPDATE videos SET status = 'rejected', updated_at = now() WHERE id = $1::uuid;",
        "={{ [ $json.video_id, $json.reason || '', $json.sender ] }}"), [1440, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("edit", "n8n-nodes-base.postgres", 2.5, "Salvar escolha", pg(
        "UPDATE videos SET spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid;",
        "={{ [ $json.video_id, JSON.stringify($json.spec) ] }}"), [1440, 200], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("reply", "n8n-nodes-evolution-api.evolutionApi", 1, "Responder", send_text(
        "={{ $('Interpretar').first().json.number }}", "={{ $('Interpretar').first().json.reply }}"),
        [1920, 0], CRED["evo"], **RETRY)
    return wf.render(
        "  .add(hook)\n  .to(config)\n  .to(read)\n  .to(find)\n  .to(decide)\n"
        "  .to(route\n    .onCase(0, ok.to(pub.to(gate.onTrue(clips.to(reply)).onFalse(reply))))\n    .onCase(1, no.to(reply))\n    .onCase(2, edit.to(reply))\n    .onCase(3, reply))")


# ===========================================================================
# factory.publish
# ===========================================================================
YT_SESSION_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


def yt_session(url, content_type, body_expr=None):
    p = {"method": "POST", "url": url, "authentication": "predefinedCredentialType", "nodeCredentialType": "youTubeOAuth2Api",
         "sendHeaders": True, "headerParameters": {"parameters": [{"name": "X-Upload-Content-Type", "value": content_type}]},
         "options": {"timeout": 60000, "response": {"response": {"fullResponse": True, "responseFormat": "text"}}}}
    if body_expr:
        p.update({"sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify(" + body_expr + ") }}"})
    return p


def build_publish(yt=None, name="factory.publish") -> str:
    """Um factory.publish por canal do YouTube (cada canal tem a sua credencial OAuth)."""
    yt = yt or yt
    wf = WF("factory-publish", name)
    wf.node("t_sub", "n8n-nodes-base.executeWorkflowTrigger", 1.2, "Vídeo aprovado",
            {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "video_id", "type": "string"}]}},
            [0, 0], fn="trigger", output=[{"video_id": "uuid"}])
    config_node(wf, extra=[{"id": "c-lead", "name": "lead_hours", "value": 3, "type": "number"}])
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Carregar e travar", pg(
        "-- muda para scheduled só se ainda estiver aguardando: um segundo \"1\" não publica duas vezes\n"
        "WITH v AS (\n"
        "  UPDATE videos SET status = 'scheduled', updated_at = now()\n"
        "  WHERE id = $1::uuid AND status = 'awaiting_approval'\n"
        "  RETURNING id, channel_id, spec\n"
        ")\n"
        "SELECT v.id AS video_id, v.spec, c.config, c.id AS channel_id,\n"
        "  COALESCE((SELECT json_agg(p.publish_at) FROM publications p JOIN videos v2 ON v2.id = p.video_id\n"
        "            WHERE v2.channel_id = c.id AND p.kind = 'long' AND p.publish_at > now()), '[]'::json) AS taken\n"
        "FROM v JOIN channels c ON c.id = v.channel_id;",
        "={{ [ $json.video_id ] }}"), [480, 0], CRED["pg"], output=[{"video_id": "v", "spec": {}, "config": {}, "taken": []}], **RETRY)
    wf.node("plan", "n8n-nodes-base.code", 2, "Plano de publicação", {"jsCode": r"""const r = $input.first().json;
const spec = typeof r.spec === 'string' ? JSON.parse(r.spec) : r.spec;
const cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;
const pub = spec.publishing || {};
const tz = cfg.schedule?.timezone || 'America/Sao_Paulo';
const times = [...(cfg.schedule?.publish_times?.length ? cfg.schedule.publish_times : ['18:00'])].sort();
const shortsTime = cfg.schedule?.shorts_time || '12:00';
const fmt = dt => dt.toUTC().toFormat("yyyy-MM-dd'T'HH:mm");
const taken = new Set((r.taken || []).map(t => fmt(DateTime.fromISO(String(t).replace(' ', 'T')))));
const earliest = DateTime.now().setZone(tz).plus({ hours: Number($('Config').first().json.lead_hours) || 3 });

// próximo horário livre de publish_times, a partir de agora + folga
let slot = null;
for (let d = 0; d < 60 && !slot; d++) {
  for (const t of times) {
    const [h, mi] = t.split(':').map(Number);
    const c = earliest.startOf('day').plus({ days: d }).set({ hour: h, minute: mi });
    if (c > earliest && !taken.has(fmt(c))) { slot = c; break; }
  }
}
if (!slot) throw new Error('Nenhum horário livre nos próximos 60 dias');

const [sh, sm] = shortsTime.split(':').map(Number);
const iso = dt => dt.toUTC().toISO({ suppressMilliseconds: true });
const status = (at) => ({
  privacyStatus: 'private',
  publishAt: iso(at),
  selfDeclaredMadeForKids: !!pub.made_for_kids,
  containsSyntheticMedia: !!pub.contains_synthetic_media,
});
const snippet = (title, description) => ({
  title, description, tags: pub.tags || [], categoryId: pub.category_id || '27',
  defaultLanguage: pub.language || 'en', defaultAudioLanguage: pub.language || 'en',
});
const thumbs = spec.thumbnail?.options || [];
const thumb = thumbs.find(t => t.n === spec.thumbnail?.chosen) || thumbs[0];
const shorts = (spec.shorts_candidates || []).map((s, i) => {
  const at = slot.plus({ days: i + 1 }).set({ hour: sh, minute: sm });
  return { n: s.n, url: s.url, publish_at: iso(at), title: s.title, description: s.description, status: status(at) };
});
return [{ json: {
  video_id: r.video_id,
  title: pub.title || spec.chosen_title,
  publish_at: iso(slot),
  publish_local: slot.toFormat('dd/MM HH:mm'),
  final_url: spec.outputs.final_url,
  thumb_url: thumb?.url || null,
  long_body: { snippet: snippet((pub.title || spec.chosen_title).slice(0, 100), pub.description || ''), status: status(slot) },
  shorts,
  snippet_base: snippet('', ''),
  number: cfg.approval?.to,
  tz,
} }];
"""}, [720, 0], output=[{"video_id": "v", "title": "t", "publish_at": "2026-10-16T21:00:00Z", "publish_local": "16/10 18:00",
                         "final_url": "s3://x", "thumb_url": "s3://y", "long_body": {}, "shorts": [], "snippet_base": {}, "number": "55", "tz": "America/Sao_Paulo"}])
    wf.node("s_long", "n8n-nodes-base.httpRequest", 4.2, "YouTube: sessão do vídeo",
            yt_session(YT_SESSION_URL, "video/mp4", "$json.long_body"), [960, 0], yt,
            output=[{"headers": {"location": "https://upload"}, "statusCode": 200}], **RETRY)
    wf.node("up_long", "n8n-nodes-base.httpRequest", 4.2, "Worker: enviar vídeo", worker_job("youtube_upload",
        "{ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-long-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: { uploads: [ { ref: 'long', upload_url: $json.headers.location, "
        "media_url: $('Plano de publicação').first().json.final_url, content_type: 'video/mp4' } ] } }"),
        [1200, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("w_long", "n8n-nodes-base.wait", 1.1, "Aguardar envio do vídeo", {k: v for k, v in wait(3).items() if k != "authentication"}, [1440, 0],
            output=[{"body": {"status": "succeeded", "result": {"uploads": [{"ref": "long", "id": "abc"}]}}}])
    wf.node("c_long", "n8n-nodes-base.code", 2, "Checar envio do vídeo", {"jsCode": """const b = $input.first().json.body;
if (!b) throw new Error('Envio do vídeo: tempo esgotado esperando o worker');
if (b.status !== 'succeeded') throw new Error('Envio do vídeo ao YouTube falhou: ' + (b.error || 'sem detalhe'));
const up = b.result.uploads[0] || {};
if (!up.id) throw new Error('O YouTube não aceitou o vídeo: ' + (up.error || 'sem id na resposta'));
return [{ json: { youtube_id: up.id } }];
"""}, [1680, 0], output=[{"youtube_id": "abc"}])
    wf.node("s_thumb", "n8n-nodes-base.httpRequest", 4.2, "YouTube: sessão da thumbnail", yt_session(
        "=https://www.googleapis.com/upload/youtube/v3/thumbnails/set?uploadType=resumable&videoId={{ $json.youtube_id }}", "image/jpeg"),
        [1920, 0], yt, onError="continueRegularOutput", alwaysOutputData=True,
        output=[{"headers": {"location": "https://upload"}, "statusCode": 200}])
    wf.node("shorts", "n8n-nodes-base.code", 2, "Shorts a enviar", {"jsCode": r"""const p = $('Plano de publicação').first().json;
const id = $('Checar envio do vídeo').first().json.youtube_id;
return p.shorts.map(s => ({ json: {
  n: s.n,
  url: s.url,
  publish_at: s.publish_at,
  body: {
    snippet: { ...p.snippet_base, title: s.title, description: String(s.description || '').replace('{{LONG_URL}}', `https://youtu.be/${id}`) },
    status: s.status,
  },
} }));
"""}, [2160, 0], output=[{"n": 1, "url": "s3://x", "publish_at": "2026-10-17T15:00:00Z", "body": {}}])
    wf.node("s_shorts", "n8n-nodes-base.httpRequest", 4.2, "YouTube: sessões dos Shorts",
            yt_session(YT_SESSION_URL, "video/mp4", "$json.body"), [2400, 0], yt,
            output=[{"headers": {"location": "https://upload"}, "statusCode": 200}], **RETRY)
    wf.node("uploads", "n8n-nodes-base.code", 2, "Montar envios", {"jsCode": r"""const p = $('Plano de publicação').first().json;
const shorts = $('Shorts a enviar').all().map(i => i.json);
const sessions = $('YouTube: sessões dos Shorts').all().map(i => i.json);
const thumbSession = $('YouTube: sessão da thumbnail').first().json;
const uploads = shorts.map((s, i) => ({ ref: `short${s.n}`, upload_url: sessions[i].headers.location, media_url: s.url, content_type: 'video/mp4' }));
const thumbUrl = thumbSession?.headers?.location;
if (thumbUrl && p.thumb_url) uploads.unshift({ ref: 'thumb', upload_url: thumbUrl, media_url: p.thumb_url, content_type: 'image/jpeg' });
return [{ json: {
  uploads,
  thumb_error: thumbUrl ? null : (thumbSession?.error?.message || JSON.stringify(thumbSession?.error || thumbSession).slice(0, 300)),
} }];
"""}, [2640, 0], output=[{"uploads": [], "thumb_error": None}])
    wf.node("up_rest", "n8n-nodes-base.httpRequest", 4.2, "Worker: enviar Shorts e thumbnail", worker_job("youtube_upload",
        "{ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-rest-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: { uploads: $json.uploads } }"),
        [2880, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("w_rest", "n8n-nodes-base.wait", 1.1, "Aguardar envio dos Shorts", {k: v for k, v in wait(3).items() if k != "authentication"}, [3120, 0],
            output=[{"body": {"status": "succeeded", "result": {"uploads": []}}}])
    wf.node("c_rest", "n8n-nodes-base.code", 2, "Checar envio dos Shorts", {"jsCode": r"""const b = $input.first().json.body;
if (!b) throw new Error('Envio dos Shorts: tempo esgotado esperando o worker');
if (b.status !== 'succeeded') throw new Error('Envio dos Shorts ao YouTube falhou: ' + (b.error || 'sem detalhe'));
const p = $('Plano de publicação').first().json;
const longId = $('Checar envio do vídeo').first().json.youtube_id;
const shorts = $('Shorts a enviar').all().map(i => i.json);
const byRef = Object.fromEntries(b.result.uploads.map(u => [u.ref, u]));
const pubs = [{ kind: 'long', id: longId, publish_at: p.publish_at }];
for (const s of shorts) {
  const u = byRef[`short${s.n}`] || {};
  pubs.push({ kind: 'short', id: u.ok ? u.id : null, publish_at: s.publish_at, n: s.n, error: u.ok ? null : (u.error || 'não enviado') });
}
return [{ json: { long_id: longId, pubs, thumb_ok: !!byRef.thumb?.ok, thumb_upload_error: byRef.thumb && !byRef.thumb.ok ? byRef.thumb.error : null } }];
"""}, [3360, 0], output=[{"long_id": "abc", "pubs": [], "thumb_ok": True}])
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Registrar publicação", pg(
        "WITH v AS (\n"
        "  UPDATE videos SET spec = jsonb_set(COALESCE(spec, '{}'::jsonb), '{publishing,youtube_id}', to_jsonb($2::text)), updated_at = now()\n"
        "  WHERE id = $1::uuid\n"
        ")\n"
        "INSERT INTO publications (video_id, platform, external_id, kind, publish_at, status)\n"
        "SELECT $1::uuid, 'youtube', p->>'id', (p->>'kind')::publication_kind, (p->>'publish_at')::timestamptz,\n"
        "       CASE WHEN p->>'id' IS NULL THEN 'failed' ELSE 'scheduled' END::publication_status\n"
        "FROM jsonb_array_elements($3::jsonb) p;",
        "={{ [ $('Plano de publicação').first().json.video_id, $json.long_id, JSON.stringify($json.pubs) ] }}"),
        [3600, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("msg", "n8n-nodes-base.code", 2, "Mensagem", {"jsCode": r"""const p = $('Plano de publicação').first().json;
const r = $('Checar envio dos Shorts').first().json;
const thumbErr = r.thumb_upload_error || $('Montar envios').first().json.thumb_error;
const local = iso => DateTime.fromISO(iso).setZone(p.tz).toFormat('dd/MM HH:mm');
const lines = [
  '📅 *Agendado no YouTube*',
  `*${p.title}*`,
  `Vídeo: ${p.publish_local} — https://youtu.be/${r.long_id}`,
  '',
  '📱 Shorts:',
  ...r.pubs.filter(x => x.kind === 'short').map(x => x.id
    ? `${x.n}. ${local(x.publish_at)} — https://youtube.com/shorts/${x.id}`
    : `${x.n}. ⚠️ não enviado: ${String(x.error || '').slice(0, 200)}`),
  '',
  r.thumb_ok ? '🖼️ Thumbnail aplicada.' : `⚠️ Thumbnail não aplicada${thumbErr ? `: ${String(thumbErr).slice(0, 300)}` : ''}. Envie pelo YouTube Studio.`,
  '',
  'Tudo fica privado até o horário agendado. Confira no YouTube Studio > Conteúdo.',
];
return [{ json: { number: p.number, text: lines.join('\n') } }];
"""}, [3840, 0], output=[{"number": "55", "text": "x"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: avisar",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [4080, 0], CRED["evo"], **RETRY)
    return wf.render(
        "  .add(t_sub)\n  .to(config)\n  .to(load)\n  .to(plan)\n  .to(s_long)\n  .to(up_long)\n  .to(w_long)\n  .to(c_long)\n"
        "  .to(s_thumb)\n  .to(shorts)\n  .to(s_shorts)\n  .to(uploads)\n  .to(up_rest)\n  .to(w_rest)\n  .to(c_rest)\n  .to(save)\n  .to(msg)\n  .to(wa)")


# ===========================================================================
# factory.clips — clipes verticais para TikTok/Reels, enviados no WhatsApp (sem aprovação)
# ===========================================================================
def build_clips() -> str:
    wf = WF("factory-clips", "factory.clips")
    wf.node("t_sub", "n8n-nodes-base.executeWorkflowTrigger", 1.2, "Vídeo aprovado",
            {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "video_id", "type": "string"}]}},
            [0, -100], fn="trigger", output=[{"video_id": "uuid"}])
    wf.node("t_manual", "n8n-nodes-base.manualTrigger", 1, "Testar com o último vídeo", {}, [0, 100], fn="trigger")
    config_node(wf)
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Carregar vídeo", pg(
        "SELECT v.id AS video_id, c.config,\n"
        "  (SELECT a.url FROM assets a WHERE a.video_id = v.id AND a.kind = 'spec' ORDER BY a.created_at DESC LIMIT 1) AS spec_url\n"
        "FROM videos v JOIN channels c ON c.id = v.channel_id\n"
        "WHERE v.id = COALESCE(NULLIF($1::text, '')::uuid,\n"
        "  (SELECT id FROM videos WHERE status IN ('awaiting_approval', 'scheduled', 'published') ORDER BY created_at DESC LIMIT 1));",
        "={{ [ $json.video_id || '' ] }}"), [480, 0], CRED["pg"], output=[{"video_id": "v", "config": {}, "spec_url": "s3://x"}], **RETRY)
    wf.node("job", "n8n-nodes-base.httpRequest", 4.2, "Worker: clipes", worker_job("clips",
        "{ video_id: $json.video_id, idempotency_key: $json.video_id + '-clips-' + $execution.id, "
        "callback_url: $execution.resumeUrl, input: { spec_url: $json.spec_url, config: $json.config } }"),
        [720, 0], CRED["worker"], output=[{"job_id": "j", "status": "queued"}], **RETRY)
    wf.node("wait", "n8n-nodes-base.wait", 1.1, "Aguardar clipes", {
        "resume": "webhook", "httpMethod": "POST", "limitWaitTime": True, "limitType": "afterTimeInterval",
        "resumeAmount": 4, "resumeUnit": "hours", "options": {}}, [960, 0],
        output=[{"body": {"status": "succeeded", "result": {"clips": []}}}])
    wf.node("chk", "n8n-nodes-base.code", 2, "Checar clipes", check_code("Clipes"), [1200, 0],
            output=[{"clips": [{"n": 1, "url": "s3://x", "caption": "c", "title": "t", "duration_s": 60}], "title": "t"}])
    wf.node("links", "n8n-nodes-base.httpRequest", 4.2, "Links temporários", {
        "method": "POST", "url": "={{ $('Config').first().json.worker_url }}/files/presign",
        "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ urls: $json.clips.map(c => c.url), expires_s: 604800 }) }}",
        "options": {"timeout": 120000}}, [1440, 0], CRED["worker"], output=[{"urls": []}], **RETRY)
    wf.node("save", "n8n-nodes-base.postgres", 2.5, "Salvar clipes", pg(
        "INSERT INTO assets (video_id, kind, url, meta)\n"
        "SELECT $1::uuid, 'short', c->>'url', jsonb_build_object('platform', 'tiktok', 'n', c->'n', 'title', c->>'title', 'caption', c->>'caption')\n"
        "FROM jsonb_array_elements($2::jsonb) c;",
        "={{ [ $('Carregar vídeo').first().json.video_id, JSON.stringify($('Checar clipes').first().json.clips) ] }}"),
        [1680, 0], CRED["pg"], output=[{"success": True}], **RETRY)
    wf.node("msgs", "n8n-nodes-base.code", 2, "Mensagens", {"jsCode": r"""// Para cada clipe: uma mensagem com o link e outra só com a legenda (fácil de copiar no celular).
const r = $('Checar clipes').first().json;
const urls = $('Links temporários').first().json.urls;
const number = $('Carregar vídeo').first().json.config.approval.to;
const out = [{ json: { number, text: `🎵 *Clipes para TikTok/Reels* (${r.clips.length})\n*${r.title}*\n\nCada clipe vem em 2 mensagens: o link do vídeo e a legenda para colar. Links válidos por 7 dias.\nPostar 1 a 3 por dia; marque como conteúdo gerado por IA.` } }];
r.clips.forEach((c, i) => {
  out.push({ json: { number, text: `*${c.n}/${r.clips.length} · ${c.title}* (${Math.round(c.duration_s)}s)\n${urls[i]}` } });
  out.push({ json: { number, text: c.caption } });
});
return out;
"""}, [1920, 0], output=[{"number": "55", "text": "x"}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: enviar clipes",
            {**send_text("={{ $json.number }}", "={{ $json.text }}"), "options_message": {"delay": 1500}},
            [2160, 0], CRED["evo"], **RETRY)
    return wf.render(
        "  .add(t_sub)\n  .to(config)\n  .to(load)\n  .to(job)\n  .to(wait)\n  .to(chk)\n  .to(links)\n  .to(save)\n  .to(msgs)\n  .to(wa)\n"
        "  .add(t_manual)\n  .to(config)")


# ===========================================================================
# factory.scheduler — a cada hora vê quais canais produzem agora e chama o factory.produce
# ===========================================================================
SCHEDULER_PLAN = r"""// Decide quais canais produzem nesta hora.
// config.schedule: timezone, production_days (["mon","wed",...], vazio = todos os dias),
// production_hour (0-23; se faltar, usa a hora do production_cron), min_queued_topics (alerta de fila baixa).
const DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
const out = [];
for (const it of $input.all()) {
  const r = it.json;
  if (!r.slug) continue;
  const cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;
  if (cfg.format?.type === 'news_short') continue; // canais de notícia são movidos pelo factory.news
  const s = cfg.schedule || {};
  const now = DateTime.now().setZone(s.timezone || 'America/Sao_Paulo');
  let hour = s.production_hour;
  if (hour == null && s.production_cron) hour = Number(String(s.production_cron).trim().split(/\s+/)[1]);
  if (hour == null || Number.isNaN(Number(hour))) hour = 2;
  const days = Array.isArray(s.production_days) && s.production_days.length
    ? s.production_days.map(d => String(d).slice(0, 3).toLowerCase()) : DAYS;
  if (now.hour !== Number(hour) || !days.includes(DAYS[now.weekday % 7])) continue;
  if (Number(r.recent) > 0) continue; // já produziu nas últimas 12 h
  const queued = Number(r.queued);
  const number = cfg.approval?.to;
  if (!queued) {
    out.push({ json: { kind: 'alert', number, text: `⚠️ *${cfg.name}*: fila de temas vazia, a produção de hoje foi pulada. Adicione temas.` } });
    continue;
  }
  out.push({ json: { kind: 'produce', channel_slug: r.slug, name: cfg.name } });
  const min = Number(s.min_queued_topics ?? 5);
  if (queued - 1 < min) {
    out.push({ json: { kind: 'alert', number, text: `📋 *${cfg.name}*: restam ${queued - 1} temas na fila. Adicione mais para não parar.` } });
  }
}
return out;
"""


def build_scheduler(produce_id: str = PRODUCE_ID) -> str:
    wf = WF("factory-scheduler", "factory.scheduler")
    wf.node("t_cron", "n8n-nodes-base.scheduleTrigger", 1.2, "A cada hora",
            {"rule": {"interval": [{"field": "hours", "hoursInterval": 1, "triggerAtMinute": 5}]}},
            [0, 0], fn="trigger")
    config_node(wf)
    wf.node("load", "n8n-nodes-base.postgres", 2.5, "Canais ativos", pg(
        "SELECT c.slug, c.config,\n"
        "  (SELECT count(*) FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued') AS queued,\n"
        "  (SELECT count(*) FROM videos v WHERE v.channel_id = c.id AND v.created_at > now() - interval '12 hours') AS recent\n"
        "FROM channels c WHERE c.active ORDER BY c.slug;",
        None), [480, 0], CRED["pg"], output=[{"slug": "career-levels", "config": {}, "queued": 10, "recent": 0}], **RETRY)
    wf.node("plan", "n8n-nodes-base.code", 2, "Quem produz agora", {"jsCode": SCHEDULER_PLAN}, [720, 0],
            output=[{"kind": "produce", "channel_slug": "career-levels", "name": "Career Levels"}])
    wf.node("route", "n8n-nodes-base.switch", 3.4, "Tipo", {
        "mode": "expression", "numberOutputs": 2,
        "output": "={{ $json.kind === 'produce' ? 0 : 1 }}"}, [960, 0], fn="switchCase")
    wf.node("run", "n8n-nodes-base.executeWorkflow", 1.3, "Produzir vídeo", {
        "mode": "each", "source": "database",
        "workflowId": {"__rl": True, "mode": "id", "value": produce_id},
        "workflowInputs": {"mappingMode": "defineBelow",
                           "value": {"channel_slug": "={{ $json.channel_slug }}"},
                           "matchingColumns": [], "schema": [{"id": "channel_slug", "displayName": "channel_slug", "required": False,
                                                              "defaultMatch": False, "display": True, "canBeUsedToMatch": True, "type": "string"}]},
        "options": {"waitForSubWorkflow": False}}, [1200, -100], output=[{}])
    wf.node("wa", "n8n-nodes-evolution-api.evolutionApi", 1, "WhatsApp: alerta",
            send_text("={{ $json.number }}", "={{ $json.text }}"), [1200, 100], CRED["evo"], **RETRY)
    return wf.render("  .add(t_cron)\n  .to(config)\n  .to(load)\n  .to(plan)\n  .to(route\n    .onCase(0, run)\n    .onCase(1, wa))")


if __name__ == "__main__":
    import sys
    OUT.mkdir(exist_ok=True)
    (OUT / "factory.package.js").write_text(build_package(), "utf-8")
    (OUT / "factory.clips.js").write_text(build_clips(), "utf-8")
    (OUT / "factory.publish.js").write_text(build_publish(), "utf-8")
    (OUT / "factory.publish.deu-tudo-errado.js").write_text(build_publish(
        {"youTubeOAuth2Api": {"id": "pnIjvYU4Eixl66cj", "name": "YouTube - Deu Tudo Errado TV"}},
        "factory.publish · Deu Tudo Errado"), "utf-8")
    (OUT / "factory.approval.js").write_text(build_approval(), "utf-8")
    (OUT / "factory.scheduler.js").write_text(build_scheduler(), "utf-8")
    print("ok", [p.name for p in OUT.iterdir()])
