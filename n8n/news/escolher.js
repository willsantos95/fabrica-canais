// Lê as notas, escolhe as pautas da rodada e prepara a gravação.
const c = $('Canal').first().json;
const cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;
const news = cfg.news || {};
const recent = new Set(((typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || []).map(r => r.story_key));
const queued = Number(c.queued || 0);
const byId = Object.fromEntries($('Guardar novas').all().map(i => [i.json.id, i.json]));

const resp = $input.first().json;
const text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')
  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');
let parsed;
try { parsed = JSON.parse(text); } catch (e) { throw new Error('Avaliação sem JSON válido: ' + text.slice(0, 200)); }

const slug = s => String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80);
const scored = (parsed.items || []).filter(x => byId[x.id]).map(x => ({
  id: x.id,
  score: Math.max(0, Math.min(10, Math.round(Number(x.score) || 0))),
  story_key: slug(x.story_key) || slug(byId[x.id].title),
  title_pt: String(x.title_pt || byId[x.id].title).replace(/\s+/g, ' ').trim().slice(0, 90),
  sport: ['futebol', 'nba', 'nfl'].includes(x.sport) ? x.sport : byId[x.id].sport,
  reason: String(x.reason || '').slice(0, 300),
}));

// o modelo às vezes dá story_keys diferentes para o mesmo fato: junta por semelhança das manchetes
const words = t => new Set(slug(t).split('-').filter(w => w.length > 3));
// nomes próprios (palavras com maiúscula fora do início) pesam mais: "Eagles", "Joe", "Milton"
const names = t => new Set(String(t || '').split(/\s+/).slice(1).filter(w => /^[A-ZÀ-Ý]/.test(w)).map(w => slug(w)).filter(Boolean));
const overlap = (A, B) => { let i = 0; for (const w of A) if (B.has(w)) i++; return [i, A.size && B.size ? i / Math.min(A.size, B.size) : 0]; };
const similar = (a, b) => {
  const [ni, nr] = overlap(names(a), names(b));
  if (ni >= 2 && nr >= 0.6) return true;
  const [, wr] = overlap(words(a), words(b));
  return wr >= 0.6;
};
const recentTitles = ((typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || []).map(r => r.title || '');
const groups = [];
for (const s of [...scored].sort((a, b) => b.score - a.score)) {
  const g = groups.find(g => g.key === s.story_key || similar(g.title, s.title_pt));
  if (g) { s.story_key = g.key; continue; }
  groups.push({ key: s.story_key, title: s.title_pt });
}

// uma pauta por fato (a nota mais alta), fora as que já foram usadas
const minScore = news.min_score ?? 7;
const best = {};
for (const s of scored) {
  if (s.score < minScore - 1 || recent.has(s.story_key) || recentTitles.some(t => similar(t, s.title_pt))) continue;
  if (!best[s.story_key] || s.score > best[s.story_key].score) best[s.story_key] = s;
}
const room = Math.max(0, (news.max_queue ?? 8) - queued);
const limit = Math.min(news.max_topics_per_run ?? 3, room);
// equilíbrio entre esportes: o melhor de cada esporte entra com 1 ponto de tolerância; o resto só acima da nota mínima
const ranked = Object.values(best).sort((a, b) => b.score - a.score);
const picks = [];
for (const sp of ['futebol', 'nba', 'nfl']) {
  const top = ranked.find(r => r.sport === sp);
  if (top && picks.length < limit) picks.push(top);
}
for (const r of ranked) if (picks.length < limit && !picks.includes(r) && r.score >= minScore) picks.push(r);
picks.sort((a, b) => b.score - a.score);

const pickedKeys = new Set(picks.map(p => p.story_key));
const updates = scored.map(s => ({ ...s, status: pickedKeys.has(s.story_key) ? 'queued' : (s.score < 4 ? 'skipped' : 'scored') }));
for (const p of picks) {
  p.sources = scored.filter(s => s.story_key === p.story_key).map(s => byId[s.id])
    .map(n => ({ title: n.title, url: n.url, source: n.source, published_at: n.published_at, summary: n.summary }));
}
const topics = picks.map(p => ({ title: p.title_pt, priority: 100 - p.score * 10,
  notes: JSON.stringify({ story_key: p.story_key, sport: p.sport, score: p.score, reason: p.reason, sources: p.sources }) }));

return [{ json: { channel_id: c.id, updates: JSON.stringify(updates), topics: JSON.stringify(topics), picks,
  scored: scored.length, room, preview: news.preview !== false, number: cfg.approval?.to, name: cfg.name } }];
