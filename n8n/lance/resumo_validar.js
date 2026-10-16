// Confere o roteiro do resumo e monta o pedido do worker (reaproveita as cenas dos Shorts).
const p = $('Próximo resumo').first().json;
const cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;
const ped = $('Pedido do resumo').first().json;
const resp = $input.first().json;
const text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')
  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');
let s;
try { s = JSON.parse(text); } catch (e) { throw new Error('Roteiro do resumo sem JSON válido: ' + text.slice(0, 200)); }
const clean = t => String(t || '').replace(/\s+/g, ' ').trim();
const byId = Object.fromEntries(ped.stories.map(x => [x.video_id, x]));
const stories = (s.stories || []).filter(x => byId[x.video_id] && clean(x.narration));
if (stories.length < 2) throw new Error('Resumo com poucas notícias válidas: ' + stories.length);

const LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' }[p.sport] || p.sport;
const scenesOf = st => (st.beats || []).flatMap(b => (b.scenes || []).map(x => ({ url: x.url }))).filter(x => x.url);
const segments = [
  { headline: `Resumo ${LABEL} · ${ped.today}`, chapter: 'Abertura', narration: clean(s.intro?.narration),
    visuals: [{ type: 'card', card: { kind: 'list', title: `${LABEL} hoje`, items: stories.slice(0, 4).map(x => clean(x.chapter).slice(0, 40)) } }] },
  ...stories.map(x => ({ story: true, headline: byId[x.video_id].headline, kicker: clean(x.kicker).slice(0, 50),
    chapter: clean(x.chapter).slice(0, 60), narration: clean(x.narration), visuals: scenesOf(byId[x.video_id]), video_id: x.video_id })),
  { headline: 'Até amanhã', chapter: 'Fechamento', narration: clean(s.outro?.narration),
    visuals: [{ type: 'card', card: { kind: 'fact', title: cfg.name, text: `Resumo de ${LABEL} todo dia no ${cfg.name}` } }] },
].filter(x => x.narration);

const yt = cfg.youtube || {};
const title = clean(s.title || `Resumo ${LABEL} ${ped.today}`).replace(/#\S+/g, '').slice(0, 95);
const usage = resp.usage || {};
const spec = {
  type: 'news_recap', sport: p.sport, date: ped.today, headline: title, chosen_title: title, titles: [title],
  stories: stories.map(x => x.video_id),
  publishing: { title, description_base: clean(s.description), tags: [...new Set([...(s.tags || []), LABEL, ...(yt.default_tags || [])].map(clean).filter(Boolean))].slice(0, 15),
    category_id: yt.category_id || '17', language: 'pt-BR', contains_synthetic_media: yt.contains_synthetic_media !== false, made_for_kids: false, kind: 'long' },
  sources: stories.flatMap(x => (byId[x.video_id].sources || []).slice(0, 2)),
  segments: segments.map(({ visuals, ...rest }) => rest),
  usage: { script: { ...usage, model: resp.model } },
};
const job = {
  sport: p.sport, color: cfg.visual?.sport_colors?.[p.sport], title: `${LABEL} HOJE`, channel_name: cfg.name,
  voice: cfg.voice?.edge_voice || 'pt-BR-FranciscaNeural', rate: cfg.recap?.rate || '+5%',
  end_card: [`Inscreva-se no ${cfg.name}`], thumbnail_lines: (s.thumbnail_lines || [`${LABEL} HOJE`, ped.today]).slice(0, 2).map(clean),
  lufs: cfg.audio?.loudness_lufs || -14, min_duration_s: 60, segments, key_prefix: `videos/${p.video_id}`,
};
return [{ json: { video_id: p.video_id, spec, job } }];
