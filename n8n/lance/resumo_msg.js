const s = $('Preparar gravação').first().json;
const spec = s.spec;
const [videoLink, thumbLink] = $('Links do resumo').first().json.urls;
const cfg = (() => { const c = $('Próximo resumo').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();
const TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };
const code = String(s.video_id).slice(0, 4).toUpperCase();
const d = Math.round(s.duration_s || 0);
const failed = (spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);
const lines = [
  `🎬 *Resumo do dia pronto* · ${cfg.name} · código *#${code}*`,
  `${TAG[spec.sport] || spec.sport} · *${spec.publishing.title}*`,
  `Duração: ${Math.floor(d / 60)}:${String(d % 60).padStart(2, '0')} · ${spec.stories.length} notícias`,
  failed.length ? `⚠️ Checagens com alerta:\n${failed.join('\n')}` : '✅ Checagens ok',
  '',
  `▶️ Vídeo: ${videoLink}`,
  '',
  '📑 Capítulos:',
  ...(spec.chapters || []).map(c => `• ${c.title}`),
  '',
  '*Responda:*',
  `1 #${code} → publicar agora no YouTube`,
  `2 #${code} motivo → descartar`,
  '',
  'Link válido por 48 h.',
];
return [{ json: { number: cfg.approval?.to, text: lines.join('\n'), thumb: thumbLink || null, caption: `#${code} · Thumbnail` } }];
