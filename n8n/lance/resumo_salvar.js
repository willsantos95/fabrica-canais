// Descrição com capítulos e fontes; thumbnail; assets.
const v = $('Montar resumo').first().json;
const r = $('Checar resumo').first().json;
const cfg = (() => { const c = $('Próximo resumo').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();
const LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' }[v.spec.sport] || v.spec.sport;
const mmss = t => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, '0')}`;
const chapters = (r.chapters || []).map((c, i) => `${mmss(i === 0 ? 0 : c.t)} ${c.title}`);
const seen = new Set();
const sources = v.spec.sources.filter(x => x.url && !seen.has(x.url) && seen.add(x.url)).slice(0, 10).map(x => `• ${x.source}: ${x.url}`);
const hashtags = [LABEL, ...(cfg.youtube?.hashtags || [])].map(h => '#' + String(h).replace(/\s+/g, ''));
const description = [v.spec.publishing.description_base, '', 'Capítulos:', ...chapters, '', 'Fontes:', ...sources, '',
  cfg.texts?.disclaimer || '', '', hashtags.join(' ')].join('\n').slice(0, 4900);
const spec = { ...v.spec,
  publishing: { ...v.spec.publishing, description },
  chapters: r.chapters,
  thumbnail: { options: (r.thumbnails || []).map((t, i) => ({ n: i + 1, url: t.url, lines: t.lines, check: t.check })), chosen: 1 },
  outputs: { final_url: r.url, srt_url: r.srt_url, duration_s: r.duration_s },
  checks: r.checks || [] };
const assets = [{ k: 'final', u: r.url, meta: { duration_s: r.duration_s } }, { k: 'srt', u: r.srt_url, meta: {} },
  ...(r.thumbnails || []).map((t, i) => ({ k: 'thumb', u: t.url, meta: { n: i + 1, check: t.check } }))];
return [{ json: { video_id: v.video_id, spec, spec_s: JSON.stringify(spec), checks: JSON.stringify(spec.checks), assets: JSON.stringify(assets), duration_s: r.duration_s } }];
