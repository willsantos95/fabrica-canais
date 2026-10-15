// Monta o HTML do painel da fábrica a partir da consulta "Dados".
const d = $('Dados').first().json;
const cfg = $('Config').first().json;
const KEY = cfg.painel_key;
const TZ = 'America/Sao_Paulo';
const parse = x => (typeof x === 'string' ? JSON.parse(x) : x) || [];
const channels = parse(d.channels), videos = parse(d.videos), calendar = parse(d.calendar);
const perf = parse(d.performance), costs = parse(d.costs);

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const dt = iso => iso ? DateTime.fromISO(String(iso).replace(' ', 'T'), { zone: 'utc' }).setZone(TZ) : null;
const now = DateTime.now().setZone(TZ);
const fmtDay = x => x.toFormat('ccc dd/LL', { locale: 'pt-BR' });
const ago = iso => { const x = dt(iso); return x ? x.toRelative({ base: now, locale: 'pt-BR' }) : ''; };
const usd = n => n == null ? '—' : 'US$ ' + Number(n).toFixed(2);
const int = n => n == null ? '—' : Number(n).toLocaleString('pt-BR');

const STAGES = [
  ['scripting', 'Roteiro'], ['voicing', 'Narração'], ['imaging', 'Imagens'], ['assembling', 'Montagem'],
  ['derivatives', 'Pacote'], ['awaiting_approval', 'Aprovação'], ['scheduled', 'Agendado'], ['published', 'Publicado'],
];
const LABEL = Object.fromEntries([...STAGES, ['failed', 'Falhou'], ['rejected', 'Rejeitado'], ['motion', 'Movimento']]);
const WORKING = ['scripting', 'voicing', 'imaging', 'motion', 'assembling', 'derivatives'];

// ---- números do topo
const month = now.toFormat('yyyy-LL');
const costMonth = costs.filter(c => c.month === month).reduce((s, c) => s + Number(c.cost_usd || 0), 0);
const withCost = costs.filter(c => c.month === month).reduce((s, c) => s + Number(c.with_cost || 0), 0);
const weekStart = now.startOf('week');
const madeWeek = videos.filter(v => dt(v.created_at) >= weekStart && !['failed', 'rejected'].includes(v.status)).length;
const pending = videos.filter(v => v.status === 'awaiting_approval');
const failed7 = videos.filter(v => v.status === 'failed' && dt(v.updated_at) > now.minus({ days: 7 }));
const working = videos.filter(v => WORKING.includes(v.status));
const stuck = working.filter(v => dt(v.updated_at) < now.minus({ hours: 3 }));
const imgs = Number(d.images_today_est || 0);

// ---- próxima produção de cada canal
const DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
const nextRun = ch => {
  const s = ch.schedule || {};
  let hour = s.production_hour;
  if (hour == null && s.production_cron) hour = Number(String(s.production_cron).trim().split(/\s+/)[1]);
  if (hour == null || Number.isNaN(Number(hour))) hour = 2;
  const days = Array.isArray(s.production_days) && s.production_days.length ? s.production_days.map(x => String(x).slice(0, 3).toLowerCase()) : DAYS;
  const local = now.setZone(s.timezone || TZ);
  for (let i = 0; i < 8; i++) {
    const c = local.startOf('day').plus({ days: i }).set({ hour: Number(hour), minute: 5 });
    if (c > local && days.includes(DAYS[c.weekday % 7])) return c;
  }
  return null;
};
const perWeek = ch => { const s = ch.schedule || {}; return Array.isArray(s.production_days) && s.production_days.length ? s.production_days.length : 7; };

// ---- blocos
const kpi = (label, value, note, tone = '') => `<div class="kpi ${tone}"><div class="kpi-l">${label}</div><div class="kpi-v">${value}</div><div class="kpi-n">${note}</div></div>`;

const pill = st => `<span class="pill st-${esc(st)}">${esc(LABEL[st] || st)}</span>`;
const ytLink = (id, kind) => id ? `<a href="https://${kind === 'short' ? 'youtube.com/shorts/' : 'youtu.be/'}${esc(id)}" target="_blank" rel="noopener">${kind === 'short' ? 'Short' : 'YouTube'} ↗</a>` : '';

const pendingCards = pending.length ? pending.map(v => `
  <article class="card">
    <div class="row"><span class="code">#${esc(v.code)}</span><span class="muted">${esc(v.channel)} · ${ago(v.updated_at)}</span></div>
    <h3>${esc(v.title)}</h3>
    <div class="muted small">${v.duration_s ? Math.floor(v.duration_s / 60) + ':' + String(Math.round(v.duration_s % 60)).padStart(2, '0') + ' · ' : ''}${v.cost_usd != null ? usd(v.cost_usd) : ''}</div>
    <div class="actions">
      <button class="btn ok" data-act="approve" data-id="${esc(v.id)}">Aprovar e agendar</button>
      <button class="btn" data-act="reject" data-id="${esc(v.id)}" data-ask="Motivo da rejeição (opcional)">Rejeitar</button>
    </div>
    <div class="muted small">Links, thumbnails e títulos estão no WhatsApp.</div>
  </article>`).join('') : '<p class="empty">Nada aguardando aprovação.</p>';

const flow = STAGES.map(([st, label]) => {
  const n = videos.filter(v => v.status === st).length;
  return `<div class="stage ${n ? 'has' : ''}"><div class="stage-n">${n}</div><div class="stage-l">${label}</div></div>`;
}).join('<div class="arrow">›</div>');

const rows = videos.slice(0, 40).map(v => {
  const late = WORKING.includes(v.status) && dt(v.updated_at) < now.minus({ hours: 3 });
  const act = v.status === 'failed' && v.topic
    ? `<button class="btn sm" data-act="requeue" data-id="${esc(v.id)}">Tema de volta à fila</button>` : '';
  return `<tr class="${late ? 'late' : ''}">
    <td><span class="code">#${esc(v.code)}</span></td>
    <td>${esc(v.channel)}</td>
    <td class="t">${esc(v.title || v.topic || '—')}${v.error ? `<div class="err">${esc(String(v.error).slice(0, 180))}</div>` : ''}</td>
    <td>${pill(v.status)}${late ? '<div class="err">parado há ' + esc(ago(v.updated_at).replace('há ', '')) + '</div>' : ''}</td>
    <td class="num">${v.cost_usd != null ? usd(v.cost_usd) : '—'}</td>
    <td class="nowrap muted">${dt(v.created_at)?.toFormat('dd/LL HH:mm') || ''}</td>
    <td>${ytLink(v.youtube_id, 'long')}${act}</td>
  </tr>`;
}).join('');

const byDay = {};
for (const p of calendar) { const k = dt(p.publish_at).toISODate(); (byDay[k] ||= []).push(p); }
const calHtml = Array.from({ length: 14 }, (_, i) => now.startOf('day').plus({ days: i })).map(day => {
  const items = (byDay[day.toISODate()] || []).sort((a, b) => a.publish_at < b.publish_at ? -1 : 1);
  return `<div class="day ${items.length ? '' : 'free'}"><div class="day-h">${fmtDay(day)}</div>${items.map(p => `
    <div class="slot ${p.kind}"><span class="hh">${dt(p.publish_at).toFormat('HH:mm')}</span>
      <span class="what">${p.kind === 'short' ? 'Short · ' : ''}${esc(p.title || '')}</span>
      <span class="muted small">${esc(p.channel)}${p.status === 'failed' ? ' · ⚠️ falhou' : ''}</span></div>`).join('') || '<div class="muted small">—</div>'}</div>`;
}).join('');

const chHtml = channels.map(ch => {
  const nr = nextRun(ch);
  const weeks = ch.queued / perWeek(ch);
  const low = ch.queued < Number(ch.schedule?.min_queued_topics ?? 5);
  return `<article class="card">
    <div class="row"><h3>${esc(ch.name)}</h3><span class="pill ${ch.active ? 'st-published' : 'st-rejected'}">${ch.active ? 'ativo' : 'pausado'}</span></div>
    <div class="muted small">${esc(ch.language || '')} · ${perWeek(ch)} vídeos/semana</div>
    <dl>
      <dt>Temas na fila</dt><dd class="${low ? 'warn' : ''}">${ch.queued} <span class="muted small">(~${weeks.toFixed(1)} semanas)</span></dd>
      <dt>Próximo tema</dt><dd>${esc(ch.next_topic || '—')}</dd>
      <dt>Próxima produção</dt><dd>${ch.active && nr ? fmtDay(nr) + ' ' + nr.toFormat('HH:mm') : '—'}</dd>
    </dl>
    ${ch.active && ch.queued ? `<button class="btn sm" data-act="produce" data-slug="${esc(ch.slug)}" data-confirm="Produzir um vídeo de ${esc(ch.name)} agora? (gasta ~US$ 0,65 na OpenAI)">Produzir agora</button>` : ''}
  </article>`;
}).join('');

const maxViews = Math.max(1, ...perf.map(p => Number(p.views || 0)));
const perfHtml = perf.length ? perf.slice(0, 25).map(p => `<tr>
    <td class="t">${esc(p.title)}<div class="muted small">${esc(p.channel)} · ${p.kind === 'short' ? 'Short' : 'Vídeo'}</div></td>
    <td class="bar"><div style="width:${(100 * Number(p.views || 0) / maxViews).toFixed(1)}%"></div><span>${int(p.views)}</span></td>
    <td class="num">${p.views_7d != null ? '+' + int(p.views_7d) : '—'}</td>
    <td class="num">${int(p.likes)}</td><td class="num">${int(p.comments)}</td>
    <td>${ytLink(p.external_id, p.kind)}</td></tr>`).join('')
  : '<tr><td colspan="6" class="empty">Sem métricas ainda. O factory.metrics coleta a cada 6 horas depois que os vídeos ficam públicos.</td></tr>';

const months = [...new Set(costs.map(c => c.month))].sort().slice(-6);
const maxCost = Math.max(0.01, ...months.map(m => costs.filter(c => c.month === m).reduce((s, c) => s + Number(c.cost_usd || 0), 0)));
const costHtml = months.length ? months.map(m => {
  const cs = costs.filter(c => c.month === m);
  const tot = cs.reduce((s, c) => s + Number(c.cost_usd || 0), 0);
  return `<div class="cbar"><div class="cbar-v">${usd(tot)}</div><div class="cbar-b"><div style="height:${(100 * tot / maxCost).toFixed(1)}%"></div></div><div class="cbar-l">${m.slice(5)}/${m.slice(2, 4)}</div><div class="muted small">${cs.reduce((s, c) => s + c.videos, 0)} vídeos</div></div>`;
}).join('') : '<p class="empty">Sem dados de custo ainda.</p>';

const html = `<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Fábrica de canais</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1c1b19;--muted:#6f6b64;--line:#e4e1da;--acc:#1f6feb;--ok:#1a7f4b;--warn:#b25e00;--bad:#c0362c;--soft:#eef3fd}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1d1b;--ink:#ecebe7;--muted:#a19d95;--line:#33312d;--acc:#6ea3ff;--ok:#45c084;--warn:#f0a040;--bad:#ff7a6e;--soft:#1f2a3d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1180px;margin:0 auto;padding:20px 16px 60px}a{color:var(--acc)}
header{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:16px}
h1{font-size:22px;margin:0}h2{font-size:16px;margin:28px 0 10px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}h3{font-size:16px;margin:6px 0}
.muted{color:var(--muted)}.small{font-size:13px}.warn{color:var(--warn);font-weight:600}.err{color:var(--bad);font-size:12px;margin-top:2px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}.kpi-l{font-size:12px;color:var(--muted)}
.kpi-v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}.kpi-n{font-size:12px;color:var(--muted)}
.kpi.alert{border-color:var(--bad)}.kpi.alert .kpi-v{color:var(--bad)}.kpi.attn{border-color:var(--warn)}.kpi.attn .kpi-v{color:var(--warn)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.code{font:600 13px ui-monospace,Menlo,monospace;background:var(--soft);padding:2px 6px;border-radius:6px}
.actions{display:flex;gap:8px;margin:10px 0 6px;flex-wrap:wrap}
.btn{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}
.btn:hover{border-color:var(--acc)}.btn.ok{background:var(--ok);border-color:var(--ok);color:#fff}.btn.sm{padding:4px 8px;font-size:13px}.btn[disabled]{opacity:.5}
.flow{display:flex;align-items:center;gap:4px;overflow-x:auto;padding-bottom:4px}
.stage{min-width:78px;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 4px}
.stage.has{border-color:var(--acc)}.stage-n{font-size:20px;font-weight:700}.stage-l{font-size:12px;color:var(--muted)}.arrow{color:var(--muted)}
.tbl{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.tbl th,.tbl td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tbl th{font-size:12px;color:var(--muted);font-weight:600}
.tbl tr:last-child td{border-bottom:0}.tbl .t{min-width:220px}.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.nowrap{white-space:nowrap}
tr.late{background:color-mix(in srgb,var(--warn) 9%,transparent)}
.scroll{overflow-x:auto;border-radius:12px}
.pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:99px;background:var(--soft);white-space:nowrap}
.st-failed,.st-rejected{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.st-awaiting_approval{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}
.st-scheduled,.st-published{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}
.cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:8px}@media (max-width:760px){.cal{grid-template-columns:repeat(2,minmax(0,1fr))}}
.day{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px;min-height:80px}.day.free{opacity:.7}
.day-h{font-size:12px;font-weight:700;color:var(--muted);margin-bottom:4px;text-transform:capitalize}
.slot{border-left:3px solid var(--acc);padding:2px 0 4px 6px;margin-bottom:4px;font-size:13px}.slot.short{border-color:var(--warn)}
.slot .hh{font-weight:700;margin-right:4px}.slot .what{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
dl{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0;font-size:14px}dt{color:var(--muted)}dd{margin:0}
.bar{min-width:160px;position:relative}.bar div{height:18px;background:color-mix(in srgb,var(--acc) 35%,transparent);border-radius:4px}
.bar span{position:absolute;left:14px;top:9px;font-size:13px;font-variant-numeric:tabular-nums}
.costs{display:flex;gap:16px;align-items:flex-end;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;overflow-x:auto}
.cbar{text-align:center;min-width:70px}.cbar-b{height:120px;display:flex;align-items:flex-end;justify-content:center}
.cbar-b div{width:34px;background:var(--acc);border-radius:6px 6px 0 0;min-height:2px}.cbar-v{font-size:13px;font-weight:600}.cbar-l{font-size:12px;color:var(--muted)}
.empty{color:var(--muted);padding:8px 0}
#toast{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);background:var(--ink);color:var(--bg);padding:10px 16px;border-radius:10px;display:none;max-width:90vw}
</style></head><body><main>
<header><h1>Fábrica de canais</h1><span class="muted small">Atualizado ${now.toFormat('dd/LL HH:mm')} · <a href="">recarregar</a></span></header>

<section class="kpis">
${kpi('Aguardando aprovação', pending.length, pending.length ? 'responda no WhatsApp ou aqui' : 'tudo em dia', pending.length ? 'attn' : '')}
${kpi('Em produção', working.length, stuck.length ? `${stuck.length} parado(s) há +3 h` : 'esteira normal', stuck.length ? 'alert' : '')}
${kpi('Falhas (7 dias)', failed7.length, failed7.length ? 'veja a lista abaixo' : 'nenhuma', failed7.length ? 'alert' : '')}
${kpi('Produzidos na semana', madeWeek, 'meta: ' + channels.filter(c => c.active).reduce((s, c) => s + perWeek(c), 0) + '/semana')}
${kpi('OpenAI no mês', usd(costMonth), withCost ? `${withCost} vídeos medidos` : 'estimativa por tokens')}
${kpi('Imagens hoje (est.)', imgs, 'cota grátis ~170/dia (UTC)', imgs > 150 ? 'attn' : '')}
</section>

<h2>Aguardando aprovação</h2>
<div class="grid">${pendingCards}</div>

<h2>Esteira</h2>
<div class="flow">${flow}</div>

<h2>Calendário de publicação (14 dias)</h2>
<div class="cal">${calHtml}</div>

<h2>Canais</h2>
<div class="grid">${chHtml}</div>

<h2>Vídeos recentes</h2>
<div class="scroll"><table class="tbl"><thead><tr><th>Código</th><th>Canal</th><th>Título</th><th>Etapa</th><th class="num">Custo</th><th>Criado</th><th></th></tr></thead>
<tbody>${rows || '<tr><td colspan="7" class="empty">Nenhum vídeo nos últimos 45 dias.</td></tr>'}</tbody></table></div>

<h2>Desempenho no YouTube</h2>
<div class="scroll"><table class="tbl"><thead><tr><th>Vídeo</th><th>Visualizações</th><th class="num">7 dias</th><th class="num">Likes</th><th class="num">Coment.</th><th></th></tr></thead>
<tbody>${perfHtml}</tbody></table></div>

<h2>Custo da OpenAI por mês</h2>
<div class="costs">${costHtml}</div>
<p class="muted small">Custo estimado pelos tokens de cada vídeo (preço de lista). Vídeos anteriores a 15/10 não têm medição.</p>
</main><div id="toast"></div>
<script>
const KEY = ${JSON.stringify(KEY)};
const toast = (t, ms = 4000) => { const el = document.getElementById('toast'); el.textContent = t; el.style.display = 'block'; clearTimeout(el._t); el._t = setTimeout(() => el.style.display = 'none', ms); };
document.addEventListener('click', async e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const body = { k: KEY, action: b.dataset.act, video_id: b.dataset.id || null, channel_slug: b.dataset.slug || null };
  if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
  if (b.dataset.ask) { const r = prompt(b.dataset.ask, ''); if (r === null) return; body.reason = r; }
  b.disabled = true;
  try {
    const res = await fetch(${JSON.stringify(cfg.action_url)}, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await res.json().catch(() => ({}));
    toast(j.message || (res.ok ? 'Feito.' : 'Erro ' + res.status));
    if (res.ok && j.ok !== false) setTimeout(() => location.reload(), 1800); else b.disabled = false;
  } catch (err) { toast('Falha de rede: ' + err.message); b.disabled = false; }
});
</script></body></html>`;
return [{ json: { html } }];
