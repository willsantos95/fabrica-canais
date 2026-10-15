import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const h_get = trigger({
  type: "n8n-nodes-base.webhook",
  version: 2.1,
  config: {
    "name": "Abrir painel",
    "parameters": {
      "httpMethod": "GET",
      "path": "fabrica-painel",
      "responseMode": "responseNode",
      "options": {
        "ignoreBots": true
      }
    },
    "position": [
      0,
      -100
    ]
  },
  output: [
    {
      "query": {
        "k": "x"
      }
    }
  ]
});

const h_post = trigger({
  type: "n8n-nodes-base.webhook",
  version: 2.1,
  config: {
    "name": "Ação do painel",
    "parameters": {
      "httpMethod": "POST",
      "path": "fabrica-painel-acao",
      "responseMode": "responseNode",
      "options": {}
    },
    "position": [
      0,
      100
    ]
  },
  output: [
    {
      "body": {
        "k": "x",
        "action": "approve",
        "video_id": "v"
      }
    }
  ]
});

const config = node({
  type: "n8n-nodes-base.set",
  version: 3.4,
  config: {
    "name": "Config",
    "parameters": {
      "assignments": {
        "assignments": [
          {
            "id": "p-key",
            "name": "painel_key",
            "value": "TROQUE-ESTA-CHAVE",
            "type": "string"
          },
          {
            "id": "p-url",
            "name": "action_url",
            "value": "https://n8n.relampagodeofertas.shop/webhook/fabrica-painel-acao",
            "type": "string"
          }
        ]
      },
      "includeOtherFields": true,
      "options": {}
    },
    "position": [
      240,
      0
    ]
  },
  output: [
    {}
  ]
});

const gate = switchCase({
  type: "n8n-nodes-base.switch",
  version: 3.4,
  config: {
    "name": "Chave e tipo",
    "parameters": {
      "mode": "expression",
      "numberOutputs": 3,
      "output": expr("{{ (($json.query?.k || $json.body?.k) !== $json.painel_key) ? 2 : ($json.body?.action ? 1 : 0) }}")
    },
    "position": [
      480,
      0
    ]
  },
  output: [
    {}
  ]
});

const data = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Dados",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT\n (SELECT COALESCE(json_agg(x ORDER BY x.slug), '[]') FROM (\n   SELECT c.slug, c.name, c.active, c.config->'schedule' AS schedule, c.config->>'language' AS language,\n     (SELECT count(*) FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued')::int AS queued,\n     (SELECT t.title FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued' ORDER BY t.priority, t.created_at LIMIT 1) AS next_topic\n   FROM channels c) x) AS channels,\n (SELECT COALESCE(json_agg(x ORDER BY x.created_at DESC), '[]') FROM (\n   SELECT v.id, upper(left(v.id::text, 4)) AS code, c.slug, c.name AS channel, v.status, v.created_at, v.updated_at, v.error,\n     v.duration_s::float AS duration_s,\n     COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title', t.title) AS title, t.title AS topic,\n     (v.spec->'usage'->>'cost_usd')::float AS cost_usd,\n     v.spec->'publishing'->>'youtube_id' AS youtube_id,\n     (SELECT min(p.publish_at) FROM publications p WHERE p.video_id = v.id AND p.kind = 'long') AS publish_at\n   FROM videos v JOIN channels c ON c.id = v.channel_id LEFT JOIN topics t ON t.id = v.topic_id\n   WHERE v.created_at > now() - interval '45 days' ORDER BY v.created_at DESC LIMIT 80) x) AS videos,\n (SELECT COALESCE(json_agg(x ORDER BY x.publish_at), '[]') FROM (\n   SELECT p.kind, p.publish_at, p.external_id, p.status, c.name AS channel, c.slug,\n     COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title') AS title\n   FROM publications p JOIN videos v ON v.id = p.video_id JOIN channels c ON c.id = v.channel_id\n   WHERE p.status <> 'failed' AND p.publish_at > now() - interval '1 day' AND p.publish_at < now() + interval '21 days') x) AS calendar,\n (SELECT COALESCE(json_agg(x ORDER BY x.views DESC NULLS LAST), '[]') FROM (\n   SELECT p.external_id, p.kind, c.name AS channel, COALESCE(v.spec->'publishing'->>'title', v.spec->>'chosen_title') AS title,\n     p.publish_at, m.views, m.likes, m.comments, m.date,\n     m.views - COALESCE((SELECT m2.views FROM metrics m2 WHERE m2.publication_id = p.id AND m2.date <= m.date - 7\n                         ORDER BY m2.date DESC LIMIT 1), 0) AS views_7d\n   FROM publications p JOIN videos v ON v.id = p.video_id JOIN channels c ON c.id = v.channel_id\n   JOIN LATERAL (SELECT * FROM metrics mm WHERE mm.publication_id = p.id ORDER BY mm.date DESC LIMIT 1) m ON true\n   WHERE p.external_id IS NOT NULL ORDER BY m.views DESC NULLS LAST LIMIT 60) x) AS performance,\n (SELECT COALESCE(json_agg(x ORDER BY x.month, x.slug), '[]') FROM (\n   SELECT to_char(date_trunc('month', v.created_at AT TIME ZONE 'America/Sao_Paulo'), 'YYYY-MM') AS month, c.slug, c.name AS channel,\n     COALESCE(sum((v.spec->'usage'->>'cost_usd')::numeric), 0)::float AS cost_usd,\n     count(*) FILTER (WHERE v.spec ? 'usage')::int AS with_cost, count(*)::int AS videos\n   FROM videos v JOIN channels c ON c.id = v.channel_id\n   WHERE v.created_at > now() - interval '6 months' GROUP BY 1, 2, 3) x) AS costs,\n (SELECT COALESCE(sum(jsonb_array_length(b->'shots')), 0)::int FROM videos v, jsonb_array_elements(v.spec->'blocks') b\n   WHERE v.updated_at >= date_trunc('day', now()) AND v.status NOT IN ('scripting', 'voicing', 'imaging', 'failed')) AS images_today_est,\n now() AS generated_at;\n",
      "options": {}
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      720,
      -200
    ]
  },
  output: [
    {
      "channels": [],
      "videos": [],
      "calendar": [],
      "performance": [],
      "costs": [],
      "images_today_est": 0
    }
  ]
});

const page = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Página",
    "parameters": {
      "jsCode": "// Monta o HTML do painel da fábrica a partir da consulta \"Dados\".\nconst d = $('Dados').first().json;\nconst cfg = $('Config').first().json;\nconst KEY = cfg.painel_key;\nconst TZ = 'America/Sao_Paulo';\nconst parse = x => (typeof x === 'string' ? JSON.parse(x) : x) || [];\nconst channels = parse(d.channels), videos = parse(d.videos), calendar = parse(d.calendar);\nconst perf = parse(d.performance), costs = parse(d.costs);\n\nconst esc = s => String(s ?? '').replace(/[&<>\"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' }[c]));\nconst dt = iso => iso ? DateTime.fromISO(String(iso).replace(' ', 'T'), { zone: 'utc' }).setZone(TZ) : null;\nconst now = DateTime.now().setZone(TZ);\nconst fmtDay = x => x.toFormat('ccc dd/LL', { locale: 'pt-BR' });\nconst ago = iso => { const x = dt(iso); return x ? x.toRelative({ base: now, locale: 'pt-BR' }) : ''; };\nconst usd = n => n == null ? '—' : 'US$ ' + Number(n).toFixed(2);\nconst int = n => n == null ? '—' : Number(n).toLocaleString('pt-BR');\n\nconst STAGES = [\n  ['scripting', 'Roteiro'], ['voicing', 'Narração'], ['imaging', 'Imagens'], ['assembling', 'Montagem'],\n  ['derivatives', 'Pacote'], ['awaiting_approval', 'Aprovação'], ['scheduled', 'Agendado'], ['published', 'Publicado'],\n];\nconst LABEL = Object.fromEntries([...STAGES, ['failed', 'Falhou'], ['rejected', 'Rejeitado'], ['motion', 'Movimento']]);\nconst WORKING = ['scripting', 'voicing', 'imaging', 'motion', 'assembling', 'derivatives'];\n\n// ---- números do topo\nconst month = now.toFormat('yyyy-LL');\nconst costMonth = costs.filter(c => c.month === month).reduce((s, c) => s + Number(c.cost_usd || 0), 0);\nconst withCost = costs.filter(c => c.month === month).reduce((s, c) => s + Number(c.with_cost || 0), 0);\nconst weekStart = now.startOf('week');\nconst madeWeek = videos.filter(v => dt(v.created_at) >= weekStart && !['failed', 'rejected'].includes(v.status)).length;\nconst pending = videos.filter(v => v.status === 'awaiting_approval');\nconst failed7 = videos.filter(v => v.status === 'failed' && dt(v.updated_at) > now.minus({ days: 7 }));\nconst working = videos.filter(v => WORKING.includes(v.status));\nconst stuck = working.filter(v => dt(v.updated_at) < now.minus({ hours: 3 }));\nconst imgs = Number(d.images_today_est || 0);\n\n// ---- próxima produção de cada canal\nconst DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];\nconst nextRun = ch => {\n  const s = ch.schedule || {};\n  let hour = s.production_hour;\n  if (hour == null && s.production_cron) hour = Number(String(s.production_cron).trim().split(/\\s+/)[1]);\n  if (hour == null || Number.isNaN(Number(hour))) hour = 2;\n  const days = Array.isArray(s.production_days) && s.production_days.length ? s.production_days.map(x => String(x).slice(0, 3).toLowerCase()) : DAYS;\n  const local = now.setZone(s.timezone || TZ);\n  for (let i = 0; i < 8; i++) {\n    const c = local.startOf('day').plus({ days: i }).set({ hour: Number(hour), minute: 5 });\n    if (c > local && days.includes(DAYS[c.weekday % 7])) return c;\n  }\n  return null;\n};\nconst perWeek = ch => { const s = ch.schedule || {}; return Array.isArray(s.production_days) && s.production_days.length ? s.production_days.length : 7; };\n\n// ---- blocos\nconst kpi = (label, value, note, tone = '') => `<div class=\"kpi ${tone}\"><div class=\"kpi-l\">${label}</div><div class=\"kpi-v\">${value}</div><div class=\"kpi-n\">${note}</div></div>`;\n\nconst pill = st => `<span class=\"pill st-${esc(st)}\">${esc(LABEL[st] || st)}</span>`;\nconst ytLink = (id, kind) => id ? `<a href=\"https://${kind === 'short' ? 'youtube.com/shorts/' : 'youtu.be/'}${esc(id)}\" target=\"_blank\" rel=\"noopener\">${kind === 'short' ? 'Short' : 'YouTube'} ↗</a>` : '';\n\nconst pendingCards = pending.length ? pending.map(v => `\n  <article class=\"card\">\n    <div class=\"row\"><span class=\"code\">#${esc(v.code)}</span><span class=\"muted\">${esc(v.channel)} · ${ago(v.updated_at)}</span></div>\n    <h3>${esc(v.title)}</h3>\n    <div class=\"muted small\">${v.duration_s ? Math.floor(v.duration_s / 60) + ':' + String(Math.round(v.duration_s % 60)).padStart(2, '0') + ' · ' : ''}${v.cost_usd != null ? usd(v.cost_usd) : ''}</div>\n    <div class=\"actions\">\n      <button class=\"btn ok\" data-act=\"approve\" data-id=\"${esc(v.id)}\">Aprovar e agendar</button>\n      <button class=\"btn\" data-act=\"reject\" data-id=\"${esc(v.id)}\" data-ask=\"Motivo da rejeição (opcional)\">Rejeitar</button>\n    </div>\n    <div class=\"muted small\">Links, thumbnails e títulos estão no WhatsApp.</div>\n  </article>`).join('') : '<p class=\"empty\">Nada aguardando aprovação.</p>';\n\nconst flow = STAGES.map(([st, label]) => {\n  const n = videos.filter(v => v.status === st).length;\n  return `<div class=\"stage ${n ? 'has' : ''}\"><div class=\"stage-n\">${n}</div><div class=\"stage-l\">${label}</div></div>`;\n}).join('<div class=\"arrow\">›</div>');\n\nconst rows = videos.slice(0, 40).map(v => {\n  const late = WORKING.includes(v.status) && dt(v.updated_at) < now.minus({ hours: 3 });\n  const act = v.status === 'failed' && v.topic\n    ? `<button class=\"btn sm\" data-act=\"requeue\" data-id=\"${esc(v.id)}\">Tema de volta à fila</button>` : '';\n  return `<tr class=\"${late ? 'late' : ''}\">\n    <td><span class=\"code\">#${esc(v.code)}</span></td>\n    <td>${esc(v.channel)}</td>\n    <td class=\"t\">${esc(v.title || v.topic || '—')}${v.error ? `<div class=\"err\">${esc(String(v.error).slice(0, 180))}</div>` : ''}</td>\n    <td>${pill(v.status)}${late ? '<div class=\"err\">parado há ' + esc(ago(v.updated_at).replace('há ', '')) + '</div>' : ''}</td>\n    <td class=\"num\">${v.cost_usd != null ? usd(v.cost_usd) : '—'}</td>\n    <td class=\"nowrap muted\">${dt(v.created_at)?.toFormat('dd/LL HH:mm') || ''}</td>\n    <td>${ytLink(v.youtube_id, 'long')}${act}</td>\n  </tr>`;\n}).join('');\n\nconst byDay = {};\nfor (const p of calendar) { const k = dt(p.publish_at).toISODate(); (byDay[k] ||= []).push(p); }\nconst calHtml = Array.from({ length: 14 }, (_, i) => now.startOf('day').plus({ days: i })).map(day => {\n  const items = (byDay[day.toISODate()] || []).sort((a, b) => a.publish_at < b.publish_at ? -1 : 1);\n  return `<div class=\"day ${items.length ? '' : 'free'}\"><div class=\"day-h\">${fmtDay(day)}</div>${items.map(p => `\n    <div class=\"slot ${p.kind}\"><span class=\"hh\">${dt(p.publish_at).toFormat('HH:mm')}</span>\n      <span class=\"what\">${p.kind === 'short' ? 'Short · ' : ''}${esc(p.title || '')}</span>\n      <span class=\"muted small\">${esc(p.channel)}${p.status === 'failed' ? ' · ⚠️ falhou' : ''}</span></div>`).join('') || '<div class=\"muted small\">—</div>'}</div>`;\n}).join('');\n\nconst chHtml = channels.map(ch => {\n  const nr = nextRun(ch);\n  const weeks = ch.queued / perWeek(ch);\n  const low = ch.queued < Number(ch.schedule?.min_queued_topics ?? 5);\n  return `<article class=\"card\">\n    <div class=\"row\"><h3>${esc(ch.name)}</h3><span class=\"pill ${ch.active ? 'st-published' : 'st-rejected'}\">${ch.active ? 'ativo' : 'pausado'}</span></div>\n    <div class=\"muted small\">${esc(ch.language || '')} · ${perWeek(ch)} vídeos/semana</div>\n    <dl>\n      <dt>Temas na fila</dt><dd class=\"${low ? 'warn' : ''}\">${ch.queued} <span class=\"muted small\">(~${weeks.toFixed(1)} semanas)</span></dd>\n      <dt>Próximo tema</dt><dd>${esc(ch.next_topic || '—')}</dd>\n      <dt>Próxima produção</dt><dd>${ch.active && nr ? fmtDay(nr) + ' ' + nr.toFormat('HH:mm') : '—'}</dd>\n    </dl>\n    ${ch.active && ch.queued ? `<button class=\"btn sm\" data-act=\"produce\" data-slug=\"${esc(ch.slug)}\" data-confirm=\"Produzir um vídeo de ${esc(ch.name)} agora? (gasta ~US$ 0,65 na OpenAI)\">Produzir agora</button>` : ''}\n  </article>`;\n}).join('');\n\nconst maxViews = Math.max(1, ...perf.map(p => Number(p.views || 0)));\nconst perfHtml = perf.length ? perf.slice(0, 25).map(p => `<tr>\n    <td class=\"t\">${esc(p.title)}<div class=\"muted small\">${esc(p.channel)} · ${p.kind === 'short' ? 'Short' : 'Vídeo'}</div></td>\n    <td class=\"bar\"><div style=\"width:${(100 * Number(p.views || 0) / maxViews).toFixed(1)}%\"></div><span>${int(p.views)}</span></td>\n    <td class=\"num\">${p.views_7d != null ? '+' + int(p.views_7d) : '—'}</td>\n    <td class=\"num\">${int(p.likes)}</td><td class=\"num\">${int(p.comments)}</td>\n    <td>${ytLink(p.external_id, p.kind)}</td></tr>`).join('')\n  : '<tr><td colspan=\"6\" class=\"empty\">Sem métricas ainda. O factory.metrics coleta a cada 6 horas depois que os vídeos ficam públicos.</td></tr>';\n\nconst months = [...new Set(costs.map(c => c.month))].sort().slice(-6);\nconst maxCost = Math.max(0.01, ...months.map(m => costs.filter(c => c.month === m).reduce((s, c) => s + Number(c.cost_usd || 0), 0)));\nconst costHtml = months.length ? months.map(m => {\n  const cs = costs.filter(c => c.month === m);\n  const tot = cs.reduce((s, c) => s + Number(c.cost_usd || 0), 0);\n  return `<div class=\"cbar\"><div class=\"cbar-v\">${usd(tot)}</div><div class=\"cbar-b\"><div style=\"height:${(100 * tot / maxCost).toFixed(1)}%\"></div></div><div class=\"cbar-l\">${m.slice(5)}/${m.slice(2, 4)}</div><div class=\"muted small\">${cs.reduce((s, c) => s + c.videos, 0)} vídeos</div></div>`;\n}).join('') : '<p class=\"empty\">Sem dados de custo ainda.</p>';\n\nconst html = `<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n<meta name=\"robots\" content=\"noindex,nofollow\"><title>Fábrica de canais</title>\n<style>\n:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1b19;--muted:#6f6b64;--line:#e4e1da;--acc:#1f6feb;--ok:#1a7f4b;--warn:#b25e00;--bad:#c0362c;--soft:#eef3fd}\n@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1d1b;--ink:#ecebe7;--muted:#a19d95;--line:#33312d;--acc:#6ea3ff;--ok:#45c084;--warn:#f0a040;--bad:#ff7a6e;--soft:#1f2a3d}}\n*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,\"Segoe UI\",Roboto,sans-serif}\nmain{max-width:1180px;margin:0 auto;padding:20px 16px 60px}a{color:var(--acc)}\nheader{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:16px}\nh1{font-size:22px;margin:0}h2{font-size:16px;margin:28px 0 10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}h3{font-size:16px;margin:6px 0}\n.muted{color:var(--muted)}.small{font-size:13px}.warn{color:var(--warn);font-weight:600}.err{color:var(--bad);font-size:12px;margin-top:2px}\n.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}\n.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}.kpi-l{font-size:12px;color:var(--muted)}\n.kpi-v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}.kpi-n{font-size:12px;color:var(--muted)}\n.kpi.alert{border-color:var(--bad)}.kpi.alert .kpi-v{color:var(--bad)}.kpi.attn{border-color:var(--warn)}.kpi.attn .kpi-v{color:var(--warn)}\n.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}\n.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}\n.row{display:flex;justify-content:space-between;align-items:center;gap:8px}\n.code{font:600 13px ui-monospace,Menlo,monospace;background:var(--soft);padding:2px 6px;border-radius:6px}\n.actions{display:flex;gap:8px;margin:10px 0 6px;flex-wrap:wrap}\n.btn{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}\n.btn:hover{border-color:var(--acc)}.btn.ok{background:var(--ok);border-color:var(--ok);color:#fff}.btn.sm{padding:4px 8px;font-size:13px}.btn[disabled]{opacity:.5}\n.flow{display:flex;align-items:center;gap:4px;overflow-x:auto;padding-bottom:4px}\n.stage{min-width:78px;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 4px}\n.stage.has{border-color:var(--acc)}.stage-n{font-size:20px;font-weight:700}.stage-l{font-size:12px;color:var(--muted)}.arrow{color:var(--muted)}\n.tbl{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}\n.tbl th,.tbl td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tbl th{font-size:12px;color:var(--muted);font-weight:600}\n.tbl tr:last-child td{border-bottom:0}.tbl .t{min-width:220px}.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.nowrap{white-space:nowrap}\ntr.late{background:color-mix(in srgb,var(--warn) 9%,transparent)}\n.scroll{overflow-x:auto;border-radius:12px}\n.pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:99px;background:var(--soft);white-space:nowrap}\n.st-failed,.st-rejected{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}\n.st-awaiting_approval{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}\n.st-scheduled,.st-published{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}\n.cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}@media (max-width:760px){.cal{grid-template-columns:repeat(2,minmax(0,1fr))}}\n.day{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px;min-height:80px}.day.free{opacity:.7}\n.day-h{font-size:12px;font-weight:700;color:var(--muted);margin-bottom:4px;text-transform:capitalize}\n.slot{border-left:3px solid var(--acc);padding:2px 0 4px 6px;margin-bottom:4px;font-size:13px}.slot.short{border-color:var(--warn)}\n.slot .hh{font-weight:700;margin-right:4px}.slot .what{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}\ndl{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0;font-size:14px}dt{color:var(--muted)}dd{margin:0}\n.bar{min-width:160px;position:relative}.bar div{height:18px;background:color-mix(in srgb,var(--acc) 35%,transparent);border-radius:4px}\n.bar span{position:absolute;left:14px;top:9px;font-size:13px;font-variant-numeric:tabular-nums}\n.costs{display:flex;gap:16px;align-items:flex-end;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;overflow-x:auto}\n.cbar{text-align:center;min-width:70px}.cbar-b{height:120px;display:flex;align-items:flex-end;justify-content:center}\n.cbar-b div{width:34px;background:var(--acc);border-radius:6px 6px 0 0;min-height:2px}.cbar-v{font-size:13px;font-weight:600}.cbar-l{font-size:12px;color:var(--muted)}\n.empty{color:var(--muted);padding:8px 0}\n#toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:10px;display:none;max-width:90vw}\n</style></head><body><main>\n<header><h1>Fábrica de canais</h1><span class=\"muted small\">Atualizado ${now.toFormat('dd/LL HH:mm')} · <a href=\"\">recarregar</a></span></header>\n\n<section class=\"kpis\">\n${kpi('Aguardando aprovação', pending.length, pending.length ? 'responda no WhatsApp ou aqui' : 'tudo em dia', pending.length ? 'attn' : '')}\n${kpi('Em produção', working.length, stuck.length ? `${stuck.length} parado(s) há +3 h` : 'esteira normal', stuck.length ? 'alert' : '')}\n${kpi('Falhas (7 dias)', failed7.length, failed7.length ? 'veja a lista abaixo' : 'nenhuma', failed7.length ? 'alert' : '')}\n${kpi('Produzidos na semana', madeWeek, 'meta: ' + channels.filter(c => c.active).reduce((s, c) => s + perWeek(c), 0) + '/semana')}\n${kpi('OpenAI no mês', usd(costMonth), withCost ? `${withCost} vídeos medidos` : 'estimativa por tokens')}\n${kpi('Imagens hoje (est.)', imgs, 'cota grátis ~170/dia (UTC)', imgs > 150 ? 'attn' : '')}\n</section>\n\n<h2>Aguardando aprovação</h2>\n<div class=\"grid\">${pendingCards}</div>\n\n<h2>Esteira</h2>\n<div class=\"flow\">${flow}</div>\n\n<h2>Calendário de publicação (14 dias)</h2>\n<div class=\"cal\">${calHtml}</div>\n\n<h2>Canais</h2>\n<div class=\"grid\">${chHtml}</div>\n\n<h2>Vídeos recentes</h2>\n<div class=\"scroll\"><table class=\"tbl\"><thead><tr><th>Código</th><th>Canal</th><th>Título</th><th>Etapa</th><th class=\"num\">Custo</th><th>Criado</th><th></th></tr></thead>\n<tbody>${rows || '<tr><td colspan=\"7\" class=\"empty\">Nenhum vídeo nos últimos 45 dias.</td></tr>'}</tbody></table></div>\n\n<h2>Desempenho no YouTube</h2>\n<div class=\"scroll\"><table class=\"tbl\"><thead><tr><th>Vídeo</th><th>Visualizações</th><th class=\"num\">7 dias</th><th class=\"num\">Likes</th><th class=\"num\">Coment.</th><th></th></tr></thead>\n<tbody>${perfHtml}</tbody></table></div>\n\n<h2>Custo da OpenAI por mês</h2>\n<div class=\"costs\">${costHtml}</div>\n<p class=\"muted small\">Custo estimado pelos tokens de cada vídeo (preço de lista). Vídeos anteriores a 15/10 não têm medição.</p>\n</main><div id=\"toast\"></div>\n<script>\nconst KEY = ${JSON.stringify(KEY)};\nconst toast = (t, ms = 4000) => { const el = document.getElementById('toast'); el.textContent = t; el.style.display = 'block'; clearTimeout(el._t); el._t = setTimeout(() => el.style.display = 'none', ms); };\ndocument.addEventListener('click', async e => {\n  const b = e.target.closest('button[data-act]'); if (!b) return;\n  const body = { k: KEY, action: b.dataset.act, video_id: b.dataset.id || null, channel_slug: b.dataset.slug || null };\n  if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;\n  if (b.dataset.ask) { const r = prompt(b.dataset.ask, ''); if (r === null) return; body.reason = r; }\n  b.disabled = true;\n  try {\n    const res = await fetch(${JSON.stringify(cfg.action_url)}, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });\n    const j = await res.json().catch(() => ({}));\n    toast(j.message || (res.ok ? 'Feito.' : 'Erro ' + res.status));\n    if (res.ok && j.ok !== false) setTimeout(() => location.reload(), 1800); else b.disabled = false;\n  } catch (err) { toast('Falha de rede: ' + err.message); b.disabled = false; }\n});\n</script></body></html>`;\nreturn [{ json: { html } }];\n"
    },
    "position": [
      960,
      -200
    ]
  },
  output: [
    {
      "html": "<html>"
    }
  ]
});

const r_page = node({
  type: "n8n-nodes-base.respondToWebhook",
  version: 1.5,
  config: {
    "name": "Responder página",
    "parameters": {
      "respondWith": "text",
      "responseBody": expr("{{ $json.html }}"),
      "options": {
        "responseHeaders": {
          "entries": [
            {
              "name": "Content-Type",
              "value": "text/html; charset=utf-8"
            },
            {
              "name": "Cache-Control",
              "value": "no-store"
            },
            {
              "name": "X-Robots-Tag",
              "value": "noindex"
            }
          ]
        }
      }
    },
    "position": [
      1200,
      -200
    ]
  },
  output: [
    {}
  ]
});

const r_deny = node({
  type: "n8n-nodes-base.respondToWebhook",
  version: 1.5,
  config: {
    "name": "Negar",
    "parameters": {
      "respondWith": "text",
      "responseBody": "Not found",
      "options": {
        "responseCode": 404
      }
    },
    "position": [
      720,
      200
    ]
  },
  output: [
    {}
  ]
});

const target = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Carregar alvo",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT v.id AS video_id, v.status::text AS status, v.topic_id, t.status::text AS topic_status, c.config, c.slug, c.active\nFROM videos v JOIN channels c ON c.id = v.channel_id LEFT JOIN topics t ON t.id = v.topic_id\nWHERE $1 <> '' AND v.id = NULLIF($1, '')::uuid\nUNION ALL\nSELECT NULL, NULL, NULL, NULL, c.config, c.slug, c.active FROM channels c WHERE $1 = '' AND c.slug = $2;",
      "options": {
        "queryReplacement": expr("{{ [ $json.body.video_id || '', $json.body.channel_slug || '' ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "alwaysOutputData": true,
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "status": "awaiting_approval",
      "config": {}
    }
  ]
});

const decide = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Decidir",
    "parameters": {
      "jsCode": "// Valida a ação pedida pelo painel. Sempre responde { ok, message } para a página.\nconst req = $('Config').first().json.body || {};\nconst t = $input.first().json;\nconst cfg = typeof t.config === 'string' ? JSON.parse(t.config || 'null') : t.config;\nconst out = (route, ok, message, extra = {}) => [{ json: { route, ok, message, ...extra } }];\nconst action = String(req.action || '');\nif (action === 'produce') {\n  if (!t.slug) return out('error', false, 'Canal não encontrado.');\n  if (!t.active) return out('error', false, 'Canal pausado.');\n  return out('produce', true, `Produção de ${cfg.name} iniciada. Acompanhe na esteira.`, { channel_slug: t.slug });\n}\nif (!t.video_id) return out('error', false, 'Vídeo não encontrado.');\nif (action === 'approve') {\n  if (t.status !== 'awaiting_approval') return out('error', false, `Este vídeo está em \"${t.status}\", não dá para aprovar.`);\n  return out('approve', true, 'Aprovado. O agendamento no YouTube começou; o aviso chega no WhatsApp.', {\n    video_id: t.video_id, publish_workflow_id: cfg.youtube?.publish_workflow_id || 'y3zthNcqybMcQEl0' });\n}\nif (action === 'reject') {\n  if (t.status !== 'awaiting_approval') return out('error', false, `Este vídeo está em \"${t.status}\", não dá para rejeitar.`);\n  return out('reject', true, 'Rejeitado.', { video_id: t.video_id, reason: String(req.reason || '').slice(0, 500) });\n}\nif (action === 'requeue') {\n  if (!['failed', 'rejected'].includes(t.status)) return out('error', false, 'Só vídeos com falha ou rejeitados devolvem o tema.');\n  if (!t.topic_id) return out('error', false, 'Vídeo sem tema.');\n  if (t.topic_status === 'queued') return out('error', false, 'O tema já está na fila.');\n  return out('requeue', true, 'Tema de volta à fila.', { topic_id: t.topic_id });\n}\nreturn out('error', false, 'Ação desconhecida.');\n"
    },
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "route": "approve",
      "ok": true,
      "message": "ok",
      "video_id": "v"
    }
  ]
});

const route = switchCase({
  type: "n8n-nodes-base.switch",
  version: 3.4,
  config: {
    "name": "Rota",
    "parameters": {
      "mode": "expression",
      "numberOutputs": 5,
      "output": expr("{{ ({ approve: 0, reject: 1, requeue: 2, produce: 3 })[$json.route] ?? 4 }}")
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {}
  ]
});

const ok = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Registrar aprovação",
    "parameters": {
      "operation": "executeQuery",
      "query": "INSERT INTO approvals (video_id, decision, decided_by) VALUES ($1::uuid, 'approved', 'painel');",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      1440,
      -300
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const pub = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Publicar no YouTube",
    "parameters": {
      "mode": "once",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": expr("{{ $('Decidir').first().json.publish_workflow_id }}")
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "video_id": expr("{{ $('Decidir').first().json.video_id }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "video_id",
            "displayName": "video_id",
            "required": false,
            "defaultMatch": false,
            "display": true,
            "canBeUsedToMatch": true,
            "type": "string"
          }
        ]
      },
      "options": {
        "waitForSubWorkflow": false
      }
    },
    "position": [
      1680,
      -300
    ]
  },
  output: [
    {}
  ]
});

const clips = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Clipes TikTok",
    "parameters": {
      "mode": "once",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": "f98b6HG2uClowRB4"
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "video_id": expr("{{ $('Decidir').first().json.video_id }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "video_id",
            "displayName": "video_id",
            "required": false,
            "defaultMatch": false,
            "display": true,
            "canBeUsedToMatch": true,
            "type": "string"
          }
        ]
      },
      "options": {
        "waitForSubWorkflow": false
      }
    },
    "position": [
      1920,
      -300
    ]
  },
  output: [
    {}
  ]
});

const no = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Registrar rejeição",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH a AS (\n  INSERT INTO approvals (video_id, decision, reason, decided_by) VALUES ($1::uuid, 'rejected', NULLIF($2, ''), 'painel')\n)\nUPDATE videos SET status = 'rejected', updated_at = now() WHERE id = $1::uuid AND status = 'awaiting_approval';",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, $json.reason || '' ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      1440,
      -150
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const rq = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Devolver tema",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE topics SET status = 'queued' WHERE id = $1::uuid;",
      "options": {
        "queryReplacement": expr("{{ [ $json.topic_id ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      1440,
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const prod = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Produzir agora",
    "parameters": {
      "mode": "once",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": "6ZhBwxhg575IOsSC"
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "channel_slug": expr("{{ $json.channel_slug }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "channel_slug",
            "displayName": "channel_slug",
            "required": false,
            "defaultMatch": false,
            "display": true,
            "canBeUsedToMatch": true,
            "type": "string"
          }
        ]
      },
      "options": {
        "waitForSubWorkflow": false
      }
    },
    "position": [
      1440,
      150
    ]
  },
  output: [
    {}
  ]
});

const r_act = node({
  type: "n8n-nodes-base.respondToWebhook",
  version: 1.5,
  config: {
    "name": "Responder ação",
    "parameters": {
      "respondWith": "json",
      "responseBody": expr("{{ JSON.stringify({ ok: $('Decidir').first().json.ok, message: $('Decidir').first().json.message }) }}"),
      "options": {}
    },
    "position": [
      2160,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-painel", "factory.painel")
  .add(h_get)
  .to(config)
  .to(gate
    .onCase(0, data.to(page.to(r_page)))
    .onCase(1, target.to(decide.to(route
      .onCase(0, ok.to(pub.to(clips.to(r_act))))
      .onCase(1, no.to(r_act))
      .onCase(2, rq.to(r_act))
      .onCase(3, prod.to(r_act))
      .onCase(4, r_act))))
    .onCase(2, r_deny))
  .add(h_post)
  .to(config);
