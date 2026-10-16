// Publicação do canal de notícias: público na hora (Short) ou no próximo horário (resumo, se configurado).
const r = $input.first().json;
const spec = typeof r.spec === 'string' ? JSON.parse(r.spec) : r.spec;
const cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;
const pub = spec.publishing || {};
const kind = spec.type === 'news_recap' ? 'long' : 'short';
const tz = cfg.schedule?.timezone || 'America/Sao_Paulo';
const status = { privacyStatus: 'public', selfDeclaredMadeForKids: !!pub.made_for_kids,
  containsSyntheticMedia: pub.contains_synthetic_media !== false };
const body = {
  snippet: { title: String(pub.title || spec.chosen_title).slice(0, 100), description: pub.description || '',
    tags: pub.tags || [], categoryId: pub.category_id || '17', defaultLanguage: 'pt-BR', defaultAudioLanguage: 'pt-BR' },
  status,
};
const thumbs = spec.thumbnail?.options || [];
const thumb = thumbs.find(t => t.n === spec.thumbnail?.chosen) || thumbs[0];
return [{ json: {
  video_id: r.video_id, topic_id: r.topic_id, kind, sport: spec.sport, title: body.snippet.title, body,
  final_url: spec.outputs?.final_url, thumb_url: kind === 'long' ? (thumb?.url || null) : null,
  playlist_id: cfg.youtube?.playlists?.[spec.sport] || null,
  number: cfg.approval?.to, tz, channel: cfg.name,
} }];
