// Confere o roteiro, monta o pedido do worker e o spec do vídeo.
const p = $('Próxima pauta').first().json;
const cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;
const notes = typeof p.notes === 'string' ? JSON.parse(p.notes) : (p.notes || {});
const sport = $('Pedido do roteiro').first().json.sport;
const resp = $input.first().json;
const text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')
  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');
let s;
try { s = JSON.parse(text); } catch (e) { throw new Error('Roteiro sem JSON válido: ' + text.slice(0, 200)); }

const clean = t => String(t || '').replace(/\s+/g, ' ').trim();
const KINDS = ['score', 'stat', 'list', 'fact', 'quote'];
const beats = (s.beats || []).map(b => {
  const v = b.visual || (b.visuals || [])[0] || {};
  let visual;
  if (v.type === 'card' && v.card && KINDS.includes(v.card.kind)) visual = { type: 'card', card: v.card };
  else visual = { type: 'image', prompt: clean(v.prompt || 'dramatic stadium under lights, crowd, sports atmosphere') };
  return { narration: clean(b.narration), visuals: [visual] };
}).filter(b => b.narration);
if (beats.length < 3) throw new Error('Roteiro com poucos trechos: ' + beats.length);

const words = beats.reduce((n, b) => n + b.narration.split(' ').length, 0);
const [minS, maxS] = cfg.format?.short_seconds || [40, 55];
const wpm = cfg.format?.words_per_minute || 175;
if (words > Math.round((maxS + 15) * wpm / 60)) throw new Error(`Roteiro longo demais: ${words} palavras`);
const checks = [{ stage: 'script', name: 'words_in_range', passed: words >= minS * wpm / 60 * 0.85 && words <= maxS * wpm / 60 * 1.1,
  detail: { words, min: Math.round(minS * wpm / 60), max: Math.round(maxS * wpm / 60) } }];

const LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };
const srcNames = [...new Set((notes.sources || []).map(x => x.source).filter(Boolean))];
const style = String(cfg.visual?.style_block || '').replace(/\[STYLE\]\s*/i, '').replace(/,?\s*9:16 vertical/i, ', square composition');
const neg = cfg.visual?.negative_prompt ? ` Avoid: ${cfg.visual.negative_prompt}.` : '';
const yt = cfg.youtube || {};
const headline = clean(s.headline || p.title).slice(0, 80);
const title = clean(s.title || p.title).replace(/#\S+/g, '').slice(0, 95);
const hashtags = ['Shorts', LABEL[sport] || sport, ...(yt.hashtags || [])].map(h => '#' + String(h).replace(/\s+/g, ''));
const description = [
  clean(s.description),
  '',
  'Fontes:',
  ...(notes.sources || []).slice(0, 4).map(x => `• ${x.source}: ${x.url}`),
  '',
  cfg.texts?.disclaimer || '',
  '',
  hashtags.join(' '),
].join('\n').slice(0, 4900);
const tags = [...new Set([...(s.tags || []), LABEL[sport], ...(yt.default_tags || [])].map(clean).filter(Boolean))].slice(0, 15);

const usage = resp.usage || {};
const P = { 'gpt-5.4-mini': { in: 0.75, out: 4.5 }, 'gpt-5.4-nano': { in: 0.2, out: 1.25 }, ...(cfg.prices || {}) };
const pr = P[String(resp.model || '').replace(/-\d{4}-\d{2}-\d{2}$/, '')] || P['gpt-5.4-mini'];
const cost_usd = Math.round(((usage.input_tokens || 0) * pr.in + (usage.output_tokens || 0) * pr.out) / 1e6 * 10000) / 10000;

const spec = {
  type: 'news_short', sport, topic_id: p.topic_id, story_key: notes.story_key,
  headline, chosen_title: title, titles: [title],
  publishing: { title, description, tags, category_id: yt.category_id || '17', language: 'pt-BR',
    contains_synthetic_media: yt.contains_synthetic_media !== false, made_for_kids: false, kind: 'short' },
  sources: notes.sources || [], beats, checks, usage: { script: { ...usage, model: resp.model }, cost_usd },
};
const color = cfg.visual?.sport_colors?.[sport];
const job = {
  sport, color, headline, channel_name: cfg.name,
  sources_label: srcNames.length ? 'Fontes: ' + srcNames.join(' · ') : '',
  voice: cfg.voice?.edge_voice || 'pt-BR-FranciscaNeural', rate: cfg.voice?.rate || '+10%',
  image_style: style + neg, end_card: cfg.news?.end_card || [`Segue o ${cfg.name}`, 'notícia rápida todo dia'],
  lufs: cfg.audio?.loudness_lufs || -14, beats, key_prefix: `videos/${p.video_id}`,
};
return [{ json: { video_id: p.video_id, spec, job } }];
