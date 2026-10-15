"""Gera os workflows do n8n da Fase 1 a partir de código, com os prompts de
prompts/ embutidos. Rode de novo depois de editar um prompt:

    python n8n/build_workflows.py
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "n8n"

SCRIPT_PROMPT = (ROOT / "prompts" / "script.system.md").read_text("utf-8")
SHOTLIST_PROMPT = (ROOT / "prompts" / "shotlist.system.md").read_text("utf-8")

CRED_DB = {"postgres": {"id": "", "name": "Fabrica DB"}}
CRED_WORKER = {"httpHeaderAuth": {"id": "", "name": "Fabrica Worker"}}
CRED_CALLBACK = {"httpHeaderAuth": {"id": "", "name": "Fabrica Callback"}}
CRED_OPENAI = {"httpHeaderAuth": {"id": "", "name": "OpenAI API"}}
CRED_EVOLUTION = {"httpHeaderAuth": {"id": "", "name": "Evolution API"}}

RETRY = {"retryOnFail": True, "maxTries": 3, "waitBetweenTries": 5000}


def _id() -> str:
    return str(uuid.uuid4())


class Flow:
    def __init__(self, name: str):
        self.name = name
        self.nodes: list[dict] = []
        self.conns: dict[str, dict] = {}
        self.x = 0

    def add(self, name, type_, version, params, *, y=0, x=None, creds=None, **extra) -> str:
        if x is None:
            self.x += 240
            x = self.x
        node = {"parameters": params, "id": _id(), "name": name, "type": type_, "typeVersion": version,
                "position": [x, y]}
        if creds:
            node["credentials"] = creds
        node.update(extra)
        self.nodes.append(node)
        return name

    def link(self, src: str, dst: str, out: int = 0) -> None:
        outs = self.conns.setdefault(src, {"main": []})["main"]
        while len(outs) <= out:
            outs.append([])
        outs[out].append({"node": dst, "type": "main", "index": 0})

    def chain(self, *names: str) -> None:
        for a, b in zip(names, names[1:]):
            self.link(a, b)

    def dump(self, settings: dict | None = None) -> dict:
        names = [n["name"] for n in self.nodes]
        assert len(names) == len(set(names)), "nomes de nós repetidos"
        for src, c in self.conns.items():
            assert src in names, src
            for outs in c["main"]:
                for t in outs:
                    assert t["node"] in names, t["node"]
        return {"name": self.name, "nodes": self.nodes, "connections": self.conns,
                "settings": {"executionOrder": "v1", **(settings or {})}, "pinData": {}}


# ---------------------------------------------------------------------------
# Peças reutilizáveis
# ---------------------------------------------------------------------------
def code(js: str) -> dict:
    return {"jsCode": js.strip() + "\n"}


def pg(query: str, replacement: str) -> dict:
    return {"operation": "executeQuery", "query": query.strip(),
            "options": {"queryReplacement": replacement}}


def http_json(url: str, body_expr: str, timeout_ms: int = 120000, headers: list | None = None) -> dict:
    p = {
        "method": "POST",
        "url": url,
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": body_expr,
        "options": {"timeout": timeout_ms},
    }
    if headers:
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": headers}
    return p


def wait_callback(hours: int) -> dict:
    return {"resume": "webhook", "httpMethod": "POST", "authentication": "headerAuth",
            "limitWaitTime": True, "limitType": "afterTimeInterval", "resumeAmount": hours,
            "resumeUnit": "hours", "options": {}}


def check_callback(stage: str) -> str:
    return f"""
// O worker chama a URL de retomada do Wait com o resultado do job.
const b = $input.first().json.body;
if (!b) throw new Error('{stage}: tempo esgotado esperando o worker');
if (b.status !== 'succeeded') throw new Error('{stage} falhou no worker: ' + (b.error || 'sem detalhe'));
return [{{ json: b.result }}];
"""


def job_body(job_type: str, input_js: str) -> str:
    """Corpo de criação de job no worker; o callback é a URL de retomada do próximo Wait."""
    return ("={{ JSON.stringify({ video_id: $('Pegar próximo tema').first().json.video_id, "
            f"idempotency_key: $('Pegar próximo tema').first().json.video_id + '-{job_type}-' + $execution.id, "
            "callback_url: $execution.resumeUrl, "
            f"input: {input_js} }}) }}}}")


UPDATE_STATUS = "UPDATE videos SET status = $2::video_status, spec = $3::jsonb WHERE id = $1::uuid;"


def status_params(status: str, spec_expr: str) -> str:
    return ("={{ [ $('Pegar próximo tema').first().json.video_id, '" + status + "', "
            f"JSON.stringify({spec_expr}) ] }}}}")


# ---------------------------------------------------------------------------
# factory.produce
# ---------------------------------------------------------------------------
def build_produce() -> dict:
    f = Flow("factory.produce")
    f.add("Produzir agora", "n8n-nodes-base.manualTrigger", 1, {}, x=0, y=-100)
    f.add("Chamado pelo agendador", "n8n-nodes-base.executeWorkflowTrigger", 1.2,
          {"inputSource": "workflowInputs", "workflowInputs": {"values": [{"name": "channel_slug", "type": "string"}]}},
          x=0, y=100)

    f.add("Config", "n8n-nodes-base.set", 3.4, {
        "assignments": {"assignments": [
            {"id": _id(), "name": "channel_slug", "value": "={{ $json.channel_slug || 'career-levels' }}", "type": "string"},
            {"id": _id(), "name": "worker_url", "value": "https://render.relampagodeofertas.shop", "type": "string"},
            {"id": _id(), "name": "openai_model", "value": "gpt-5.5", "type": "string"},
            {"id": _id(), "name": "reasoning_effort", "value": "medium", "type": "string"},
            {"id": _id(), "name": "evolution_url", "value": "https://SEU-EVOLUTION", "type": "string"},
            {"id": _id(), "name": "evolution_instance", "value": "SUA-INSTANCIA", "type": "string"},
        ]},
        "options": {},
    })
    f.link("Produzir agora", "Config")
    f.link("Chamado pelo agendador", "Config")

    f.add("Pegar próximo tema", "n8n-nodes-base.postgres", 2.5, pg("""
SELECT t.topic_id, t.video_id, t.title, c.config
FROM claim_next_topic($1::text, $2::text) t
JOIN channels c ON c.slug = $1::text;
""", "={{ [ $json.channel_slug, $execution.id ] }}"), creds=CRED_DB, **RETRY)
    f.link("Config", "Pegar próximo tema")

    f.add("Pedido do roteiro", "n8n-nodes-base.code", 2, code(f"""
// Prompt do canal (config.prompts.script) ou o padrão do Career Levels.
const DEFAULT_SYSTEM = {json.dumps(SCRIPT_PROMPT, ensure_ascii=False)};
const DEFAULT_INPUT = "Topic: {{{{topic}}}}\\n\\nResearch it on the web and write the full video now.";
const EXTRA = "\\n\\nIn the same JSON object also include: \\"subject\\" (the main subject in 1 to 4 words, in the narration language), \\"tags\\" (8 to 12 YouTube search tags in the narration language) and \\"hashtags\\" (3 hashtags without #, CamelCase, in the narration language).";
const p = $('Config').first().json;
const t = $input.first().json;
const cfg = typeof t.config === 'string' ? JSON.parse(t.config) : t.config;
const pr = cfg.prompts || {{}};
const [mmin, mmax] = cfg.format.long_minutes;
const wpm = cfg.format.words_per_minute;
const [bmin, bmax] = cfg.format.blocks || [6, 12];
const vars = {{
  'channel.name': cfg.name, 'channel.niche': cfg.niche, 'channel.language': cfg.language,
  'channel.tone': cfg.tone, 'channel.point_of_view': cfg.point_of_view || '',
  words_min: Math.round(mmin * wpm), words_max: Math.round(mmax * wpm), wpm,
  blocks_min: bmin, blocks_max: bmax, topic: t.title,
}};
const fill = x => String(x).replace(/{{{{\\s*([\\w.]+)\\s*}}}}/g, (_, k) => String(vars[k] ?? ''));
const body = {{
  model: pr.model || p.openai_model,
  instructions: fill(pr.script || DEFAULT_SYSTEM) + EXTRA,
  input: fill(pr.script_input || DEFAULT_INPUT),
  tools: pr.web_search === false ? [] : [{{ type: 'web_search' }}],
  reasoning: {{ effort: pr.reasoning_effort || p.reasoning_effort || 'medium' }},
  max_output_tokens: 32000,
}};
return [{{ json: {{ video_id: t.video_id, topic_id: t.topic_id, title: t.title, config: cfg,
  words_min: vars.words_min, words_max: vars.words_max, body }} }}];
"""), y=0)
    f.link("Pegar próximo tema", "Pedido do roteiro")

    f.add("OpenAI: pesquisa e roteiro", "n8n-nodes-base.httpRequest", 4.2,
          http_json("https://api.openai.com/v1/responses", "={{ JSON.stringify($json.body) }}",
                    900000), creds=CRED_OPENAI, **RETRY)
    f.link("Pedido do roteiro", "OpenAI: pesquisa e roteiro")

    f.add("Validar roteiro", "n8n-nodes-base.code", 2, code("""
const resp = $input.first().json;
const ctx = $('Pedido do roteiro').first().json;
if (resp.status === 'incomplete') throw new Error('Resposta da OpenAI incompleta: ' + JSON.stringify(resp.incomplete_details || {}));
const text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')
  .flatMap(o => o.content || []).filter(c => c.type === 'output_text').map(c => c.text).join('');
const m = text.match(/<json>([\\s\\S]*)<\\/json>/);
if (!m) throw new Error(`Roteiro sem bloco <json> (status=${resp.status})`);
let s;
try { s = JSON.parse(m[1]); } catch (e) { throw new Error('JSON do roteiro inválido: ' + e.message); }
if (!Array.isArray(s.blocks) || s.blocks.length < 3) throw new Error('Roteiro com menos de 3 blocos');

const sources = Array.isArray(s.sources) ? s.sources.filter(x => x && x.id && /^https?:\\/\\//.test(x.url || '')) : [];
const ids = new Set(sources.map(x => x.id));
const clean = t => String(t || '').replace(/\\s+/g, ' ').trim();
const blocks = s.blocks.map((b, i) => ({
  block_id: 'b' + String(i + 1).padStart(2, '0'),
  title: clean(b.title) || `Part ${i + 1}`,
  narration: clean(b.narration),
  source_ids: (b.source_ids || []).filter(id => ids.has(id)),
}));
const words = blocks.reduce((n, b) => n + b.narration.split(' ').length, 0);
if (words < ctx.words_min * 0.8) throw new Error(`Roteiro curto demais: ${words} palavras (mínimo ${ctx.words_min})`);

const checks = [
  { stage: 'script', name: 'word_count', passed: words >= ctx.words_min && words <= ctx.words_max * 1.15,
    detail: { words, min: ctx.words_min, max: ctx.words_max } },
  { stage: 'script', name: 'has_sources', passed: sources.length >= 3, detail: { sources: sources.length } },
  { stage: 'script', name: 'blocks_cited', passed: blocks.filter(b => b.source_ids.length).length >= Math.ceil(blocks.length / 2),
    detail: { cited: blocks.filter(b => b.source_ids.length).length, blocks: blocks.length } },
];
const titles = (s.titles || []).map(clean).filter(Boolean).slice(0, 10);
return [{ json: { ...ctx, body: undefined, script: {
  titles: titles.length ? titles : [ctx.title],
  chosen_title: clean(s.chosen_title) || titles[0] || ctx.title,
  hook_options: (s.hook_options || []).map(clean).filter(Boolean),
  subject: clean(s.subject).slice(0, 60) || null,
  tags: (s.tags || []).map(clean).filter(Boolean).slice(0, 15),
  hashtags: (s.hashtags || []).map(x => clean(x).replace(/^#/, '')).filter(Boolean).slice(0, 5),
  sources, blocks }, checks, words,
  usage_script: { ...(resp.usage || {}), model: resp.model, web_searches: (resp.output || []).filter(o => o.type === 'web_search_call').length } } }];
"""), y=0)
    f.link("OpenAI: pesquisa e roteiro", "Validar roteiro")

    f.add("Pedido da shotlist", "n8n-nodes-base.code", 2, code(f"""
const DEFAULT_SYSTEM = {json.dumps(SHOTLIST_PROMPT, ensure_ascii=False)};
const p = $('Config').first().json;
const c = $input.first().json;
const pr = c.config.prompts || {{}};
const SYSTEM = pr.shotlist || DEFAULT_SYSTEM;
const vars = {{ 'channel.name': c.config.name, shots_total: c.config.format.shots_per_video }};
const system = SYSTEM.replace(/{{{{\\s*([\\w.]+)\\s*}}}}/g, (_, k) => String(vars[k] ?? ''));
const blocks = c.script.blocks.map(b => ({{ block_id: b.block_id, title: b.title, narration: b.narration }}));
const body = {{
  model: pr.shotlist_model || pr.model || p.openai_model,
  instructions: system,
  input: 'Narration blocks:\\n' + JSON.stringify({{ blocks }}, null, 1),
  reasoning: {{ effort: pr.reasoning_effort || p.reasoning_effort || 'medium' }},
  max_output_tokens: 32000,
}};
return [{{ json: {{ body }} }}];
"""), y=0)
    f.link("Validar roteiro", "Pedido da shotlist")

    f.add("OpenAI: shotlist", "n8n-nodes-base.httpRequest", 4.2,
          http_json("https://api.openai.com/v1/responses", "={{ JSON.stringify($json.body) }}",
                    900000), creds=CRED_OPENAI, **RETRY)
    f.link("Pedido da shotlist", "OpenAI: shotlist")

    f.add("Montar video_spec", "n8n-nodes-base.code", 2, code("""
const resp = $input.first().json;
const c = $('Validar roteiro').first().json;
if (resp.status === 'incomplete') throw new Error('Resposta da OpenAI incompleta: ' + JSON.stringify(resp.incomplete_details || {}));
const text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')
  .flatMap(o => o.content || []).filter(c => c.type === 'output_text').map(c => c.text).join('');
const m = text.match(/<json>([\\s\\S]*)<\\/json>/);
if (!m) throw new Error(`Shotlist sem bloco <json> (status=${resp.status})`);
const sl = JSON.parse(m[1]);
const norm = t => String(t || '').toLowerCase().replace(/[^a-z0-9à-ÿ]+/g, ' ').trim();
const MOVES = ['push_in', 'pull_out', 'pan_left', 'pan_right', 'pan_up', 'pan_down'];
const byId = Object.fromEntries((sl.blocks || []).map(b => [b.block_id, b]));

let order = 0, found = 0, total = 0, fallbackBlocks = 0;
const blocks = c.script.blocks.map(b => {
  let raw = (byId[b.block_id] || {}).shots || [];
  if (!raw.length) {
    // sem planos para o bloco: 1 plano a cada 2 frases, com o título como cena
    fallbackBlocks++;
    const sentences = b.narration.match(/[^.!?]+[.!?]+/g) || [b.narration];
    raw = [];
    for (let i = 0; i < sentences.length; i += 2) {
      raw.push({ narration_span: sentences.slice(i, i + 2).join(' ').trim(),
        visual_prompt: `${b.title}, illustrative scene, variation ${i / 2 + 1}`, text_overlay: i === 0 ? b.title.split(' - ')[0].slice(0, 30) : null });
    }
  }
  const nb = norm(b.narration);
  const shots = raw.map((s, i) => {
    order++; total++;
    const span = String(s.narration_span || '').trim();
    if (span && nb.includes(norm(span))) found++;
    const kb = MOVES.includes(s.kenburns) ? s.kenburns : MOVES[order % MOVES.length];
    return {
      shot_id: `${b.block_id}-s${String(i + 1).padStart(2, '0')}`,
      order,
      narration_span: span || b.narration.slice(0, 80),
      visual_prompt: (() => { const v = String(s.visual_prompt || '').trim();
        return v.length >= 10 ? v : `${b.title}: ${span || b.narration.slice(0, 120)}`; })(),
      text_overlay: s.text_overlay ? String(s.text_overlay).slice(0, 40) : null,
      // Fase 1: todos os planos com Ken Burns (custo zero). IA de vídeo entra na Fase 2.
      motion: { mode: 'kenburns', kenburns: kb },
      is_hook: Boolean(s.is_hook) && order <= 3,
      image: { url: null, provider: null },
      clip: { url: null, provider: null },
      start_s: null, end_s: null,
    };
  });
  return { ...b, audio: { url: null, duration_s: null, offset_s: null, words: [] }, shots };
});

// custo estimado em US$ (preço por 1M tokens; config.prices sobrescreve se a OpenAI mudar o preço)
const P = { 'gpt-5.5': { in: 5, cached: 0.5, out: 30 }, web_search: 0.01, ...(c.config.prices || {}) };
const cost = (u, model) => {
  if (!u || !u.input_tokens) return 0;
  const k = Object.keys(P).find(x => String(model || '').startsWith(x));
  const pr = (k && P[k].in != null) ? P[k] : P['gpt-5.5'];
  const cached = u.input_tokens_details?.cached_tokens || 0;
  return ((u.input_tokens - cached) * pr.in + cached * pr.cached + u.output_tokens * pr.out) / 1e6;
};
const su = c.usage_script || {};
const usage = { script: su, shotlist: { ...(resp.usage || {}), model: resp.model } };
usage.cost_usd = Math.round((cost(su, su.model) + (su.web_searches || 0) * P.web_search + cost(resp.usage, resp.model)) * 1000) / 1000;

const spec = {
  video_id: c.video_id,
  channel: c.config.slug,
  topic: c.title,
  subject: c.script.subject || null,
  tags: c.script.tags || [],
  hashtags: c.script.hashtags || [],
  usage,
  language: c.config.language,
  titles: c.script.titles,
  chosen_title: c.script.chosen_title,
  hook_options: c.script.hook_options,
  sources: c.script.sources,
  blocks,
  shorts_candidates: [],
  thumbnail: { phrases: (sl.thumbnail && sl.thumbnail.phrases) || [], image_prompt: (sl.thumbnail && sl.thumbnail.image_prompt) || '', options: [], chosen: null },
  publishing: { description: null, chapters: [], tags: [], pinned_comment: null },
  outputs: { final_url: null, srt_url: null, preview_url: null, duration_s: null },
  checks: [
    ...c.checks,
    { stage: 'shotlist', name: 'shot_count', passed: Math.abs(total - c.config.format.shots_per_video) <= c.config.format.shots_per_video * 0.3,
      detail: { shots: total, target: c.config.format.shots_per_video } },
    { stage: 'shotlist', name: 'spans_match_narration', passed: found >= total * 0.8,
      detail: { found, total, fallback_blocks: fallbackBlocks } },
  ],
};
return [{ json: { video_id: c.video_id, spec, key: `videos/${c.video_id}/video_spec.json` } }];
"""), y=0)
    f.link("OpenAI: shotlist", "Montar video_spec")

    W = "={{ $('Config').first().json.worker_url }}"
    f.add("Salvar spec", "n8n-nodes-base.httpRequest", 4.2,
          http_json(W + "/files/put", "={{ JSON.stringify({ key: $json.key, json: $json.spec }) }}"),
          creds=CRED_WORKER, **RETRY)
    f.link("Montar video_spec", "Salvar spec")

    f.add("Status: narração", "n8n-nodes-base.postgres", 2.5,
          pg(UPDATE_STATUS, status_params("voicing", "$('Montar video_spec').first().json.spec")),
          creds=CRED_DB, **RETRY)
    f.link("Salvar spec", "Status: narração")

    cfg = "$('Pegar próximo tema').first().json.config"
    f.add("Worker: narração", "n8n-nodes-base.httpRequest", 4.2,
          http_json(W + "/jobs/voice", job_body(
              "voice", f"{{ spec_url: $('Salvar spec').first().json.url, voice: {cfg}.voice.edge_voice, "
                       f"rate: {cfg}.voice.rate || '+0%' }}")),
          creds=CRED_WORKER, **RETRY)
    f.link("Status: narração", "Worker: narração")
    f.add("Aguardar narração", "n8n-nodes-base.wait", 1.1, wait_callback(1), creds=CRED_CALLBACK,
          webhookId=_id())
    f.link("Worker: narração", "Aguardar narração")
    f.add("Checar narração", "n8n-nodes-base.code", 2, code(check_callback("Narração")))
    f.link("Aguardar narração", "Checar narração")

    f.add("Status: imagens", "n8n-nodes-base.postgres", 2.5,
          pg(UPDATE_STATUS, status_params("imaging", "$('Checar narração').first().json.spec")),
          creds=CRED_DB, **RETRY)
    f.link("Checar narração", "Status: imagens")
    f.add("Worker: imagens", "n8n-nodes-base.httpRequest", 4.2,
          http_json(W + "/jobs/images", job_body(
              "images", f"{{ spec_url: $('Checar narração').first().json.spec_url, "
                        f"style_block: {cfg}.visual.style_block, negative_prompt: {cfg}.visual.negative_prompt }}")),
          creds=CRED_WORKER, **RETRY)
    f.link("Status: imagens", "Worker: imagens")
    f.add("Aguardar imagens", "n8n-nodes-base.wait", 1.1, wait_callback(2), creds=CRED_CALLBACK,
          webhookId=_id())
    f.link("Worker: imagens", "Aguardar imagens")
    f.add("Checar imagens", "n8n-nodes-base.code", 2, code(check_callback("Imagens")))
    f.link("Aguardar imagens", "Checar imagens")

    f.add("Status: montagem", "n8n-nodes-base.postgres", 2.5,
          pg(UPDATE_STATUS, status_params("assembling", "$('Checar imagens').first().json.spec")),
          creds=CRED_DB, **RETRY)
    f.link("Checar imagens", "Status: montagem")
    f.add("Worker: montagem", "n8n-nodes-base.httpRequest", 4.2,
          http_json(W + "/jobs/assemble", job_body(
              "assemble", f"{{ spec_url: $('Checar imagens').first().json.spec_url, "
                          f"loudness_lufs: {cfg}.audio.loudness_lufs, "
                          f"music_volume_db: {cfg}.audio.music_volume_db ?? -22, "
                          f"min_duration_s: Math.round({cfg}.format.long_minutes[0] * 60 * 0.8) }}")),
          creds=CRED_WORKER, **RETRY)
    f.link("Status: montagem", "Worker: montagem")
    f.add("Aguardar montagem", "n8n-nodes-base.wait", 1.1, wait_callback(3), creds=CRED_CALLBACK,
          webhookId=_id())
    f.link("Worker: montagem", "Aguardar montagem")
    f.add("Checar montagem", "n8n-nodes-base.code", 2, code(check_callback("Montagem")))
    f.link("Aguardar montagem", "Checar montagem")

    f.add("Links temporários", "n8n-nodes-base.httpRequest", 4.2,
          http_json(W + "/files/presign",
                    "={{ JSON.stringify({ urls: [ $json.outputs.preview_url, $json.outputs.final_url, "
                    "$json.outputs.srt_url ], expires_s: 172800 }) }}"),
          creds=CRED_WORKER, **RETRY)
    f.link("Checar montagem", "Links temporários")

    f.add("Salvar resultado", "n8n-nodes-base.postgres", 2.5, pg("""
WITH v AS (
  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, duration_s = $3::numeric
  WHERE id = $1::uuid RETURNING id, topic_id
), tp AS (
  UPDATE topics SET status = 'done' WHERE id = (SELECT topic_id FROM v)
), ck AS (
  INSERT INTO checks (video_id, stage, name, passed, detail)
  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)
  FROM jsonb_array_elements($2::jsonb->'checks') c
)
INSERT INTO assets (video_id, kind, url)
SELECT $1::uuid, x.k::asset_kind, x.u
FROM (VALUES ('final', $4::text), ('srt', $5::text), ('preview', $6::text), ('spec', $7::text)) AS x(k, u)
WHERE x.u IS NOT NULL;
""", "={{ (() => { const r = $('Checar montagem').first().json; return [ "
         "$('Pegar próximo tema').first().json.video_id, JSON.stringify(r.spec), r.outputs.duration_s, "
         "r.outputs.final_url, r.outputs.srt_url, r.outputs.preview_url, r.spec_url ]; })() }}"),
          creds=CRED_DB, **RETRY)
    f.link("Links temporários", "Salvar resultado")

    f.add("Mensagem", "n8n-nodes-base.code", 2, code("""
const r = $('Checar montagem').first().json;
const [preview, final, srt] = $('Links temporários').first().json.urls;
const spec = r.spec;
const d = Math.round(r.outputs.duration_s);
const dur = `${Math.floor(d / 60)}:${String(d % 60).padStart(2, '0')}`;
const failed = (spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);
const text = [
  `🎬 *Vídeo pronto para revisão*`,
  `*${spec.chosen_title}*`,
  `Duração: ${dur} · ${spec.blocks.length} blocos · ${spec.sources.length} fontes`,
  failed.length ? `⚠️ Checagens com alerta:\\n${failed.join('\\n')}` : '✅ Todas as checagens passaram',
  '',
  `▶️ Preview (480p): ${preview}`,
  `⬇️ Vídeo final: ${final}`,
  srt ? `📝 Legenda SRT: ${srt}` : '',
  '',
  'Links válidos por 48 h. Fase 1: publique pelo YouTube Studio.',
].filter(x => x !== '').join('\\n');
return [{ json: { number: $('Pegar próximo tema').first().json.config.approval.to, text } }];
"""))
    f.link("Salvar resultado", "Mensagem")

    f.add("WhatsApp: avisar", "n8n-nodes-base.httpRequest", 4.2,
          http_json("={{ $('Config').first().json.evolution_url }}/message/sendText/"
                    "{{ $('Config').first().json.evolution_instance }}",
                    "={{ JSON.stringify({ number: $json.number, text: $json.text }) }}"),
          creds=CRED_EVOLUTION, **RETRY)
    f.link("Mensagem", "WhatsApp: avisar")

    return f.dump()


# ---------------------------------------------------------------------------
# factory.error — marca o vídeo como falho, devolve o tema à fila e avisa no WhatsApp
# ---------------------------------------------------------------------------
def build_error() -> dict:
    f = Flow("factory.error")
    f.add("Erro em workflow", "n8n-nodes-base.errorTrigger", 1, {}, x=0)
    f.add("Config", "n8n-nodes-base.set", 3.4, {
        "assignments": {"assignments": [
            {"id": _id(), "name": "alert_number", "value": "55DDDNUMERO", "type": "string"},
            {"id": _id(), "name": "evolution_url", "value": "https://SEU-EVOLUTION", "type": "string"},
            {"id": _id(), "name": "evolution_instance", "value": "SUA-INSTANCIA", "type": "string"},
        ]},
        "includeOtherFields": True,
        "options": {},
    })
    f.link("Erro em workflow", "Config")
    f.add("Marcar falha", "n8n-nodes-base.postgres", 2.5, pg("""
WITH v AS (
  UPDATE videos SET status = 'failed', error = $2
  WHERE n8n_execution_id = $1 AND status NOT IN ('published', 'scheduled', 'awaiting_approval')
  RETURNING topic_id
), tp AS (
  UPDATE topics SET status = 'queued', priority = priority + 1000
  WHERE id IN (SELECT topic_id FROM v)
  RETURNING id
)
SELECT (SELECT count(*) FROM v) AS videos_marcados;
""", "={{ [ String($json.execution.id), ($json.execution.lastNodeExecuted || '') + ': ' + "
         "($json.execution.error?.message || 'erro desconhecido') ] }}"),
          creds=CRED_DB, alwaysOutputData=True, onError="continueRegularOutput")
    f.link("Config", "Marcar falha")
    f.add("Mensagem", "n8n-nodes-base.code", 2, code("""
const e = $('Config').first().json;
const text = [
  `🚨 *Falha na fábrica*`,
  `Workflow: ${e.workflow?.name || '?'}`,
  `Nó: ${e.execution?.lastNodeExecuted || '?'}`,
  `Erro: ${(e.execution?.error?.message || 'sem mensagem').slice(0, 500)}`,
  e.execution?.url ? `Execução: ${e.execution.url}` : '',
  'O tema voltou para o fim da fila.',
].filter(Boolean).join('\\n');
return [{ json: { number: e.alert_number, text } }];
"""))
    f.link("Marcar falha", "Mensagem")
    f.add("WhatsApp: alerta", "n8n-nodes-base.httpRequest", 4.2,
          http_json("={{ $('Config').first().json.evolution_url }}/message/sendText/"
                    "{{ $('Config').first().json.evolution_instance }}",
                    "={{ JSON.stringify({ number: $json.number, text: $json.text }) }}"),
          creds=CRED_EVOLUTION, **RETRY)
    f.link("Mensagem", "WhatsApp: alerta")
    return f.dump()


# ---------------------------------------------------------------------------
# teste-callback — valida o caminho worker → n8n (Wait) em segundos, sem gastar IA
# ---------------------------------------------------------------------------
def build_test_callback() -> dict:
    f = Flow("factory.teste-callback")
    f.add("Testar callback", "n8n-nodes-base.manualTrigger", 1, {}, x=0)
    f.add("Config", "n8n-nodes-base.set", 3.4, {
        "assignments": {"assignments": [
            {"id": _id(), "name": "worker_url", "value": "https://render.relampagodeofertas.shop", "type": "string"},
            {"id": _id(), "name": "media_url", "value": "s3://fabrica/testes/callback.wav", "type": "string"},
        ]},
        "options": {},
    })
    f.link("Testar callback", "Config")
    f.add("Mostrar URL de retomada", "n8n-nodes-base.code", 2, code("""
// A URL precisa começar com o domínio público do n8n (WEBHOOK_URL), nunca com localhost.
const url = $execution.resumeUrl;
if (/localhost|127\\.0\\.0\\.1/.test(url)) throw new Error('WEBHOOK_URL do n8n não configurada: ' + url);
return [{ json: { ...$input.first().json, resume_url: url } }];
"""))
    f.link("Config", "Mostrar URL de retomada")
    f.add("Worker: job de teste", "n8n-nodes-base.httpRequest", 4.2,
          http_json("={{ $json.worker_url }}/jobs/checks",
                    "={{ JSON.stringify({ video_id: 'teste-callback', idempotency_key: 'teste-callback-' + $execution.id, "
                    "callback_url: $execution.resumeUrl, input: { media_url: $json.media_url, stage: 'teste' } }) }}"),
          creds=CRED_WORKER)
    f.link("Mostrar URL de retomada", "Worker: job de teste")
    f.add("Aguardar worker", "n8n-nodes-base.wait", 1.1,
          {"resume": "webhook", "httpMethod": "POST", "authentication": "headerAuth",
           "limitWaitTime": True, "limitType": "afterTimeInterval", "resumeAmount": 10,
           "resumeUnit": "minutes", "options": {}},
          creds=CRED_CALLBACK, webhookId=_id())
    f.link("Worker: job de teste", "Aguardar worker")
    f.add("Resultado", "n8n-nodes-base.code", 2, code("""
const b = $input.first().json.body;
if (!b) throw new Error('O worker não conseguiu avisar o n8n em 10 min. Veja a linha "callback falhou" no log do serviço api/render.');
return [{ json: { callback: 'OK — o n8n recebeu o aviso do worker', status: b.status, worker_result: b.result, erro: b.error || null } }];
"""))
    f.link("Aguardar worker", "Resultado")
    return f.dump()


if __name__ == "__main__":
    for name, wf in [("factory.produce.json", build_produce()), ("factory.error.json", build_error()),
                     ("teste-callback.json", build_test_callback())]:
        (OUT / name).write_text(json.dumps(wf, ensure_ascii=False, indent=2) + "\n", "utf-8")
        print("gerado", name, len(wf["nodes"]), "nós")
