// Mensagem de aprovação do Short (WhatsApp): texto + vídeo.
const v = $('Montar pedido').first().json;
const r = $('Checar vídeo').first().json;
const [videoLink, coverLink] = $('Links temporários').first().json.urls;
const cfg = (() => { const c = $('Próxima pauta').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();
const TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };
const code = String(v.video_id).slice(0, 4).toUpperCase();
const spec = v.spec;
const failed = (r.checks || []).concat(spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);
const src = (spec.sources || []).slice(0, 3).map(s => `${s.source}: ${s.url}`);
const lines = [
  `📱 *Short pronto* · ${cfg.name} · código *#${code}*`,
  `${TAG[spec.sport] || spec.sport} · *${spec.publishing.title}*`,
  `Duração: ${Math.round(r.duration_s)}s${r.fallback_images ? ` · ⚠️ ${r.fallback_images} imagem(ns) trocada(s) por cartão` : ''}`,
  failed.length ? `⚠️ Checagens com alerta:\n${failed.join('\n')}` : '✅ Checagens ok',
  '',
  `▶️ Vídeo: ${videoLink}`,
  '',
  '📰 Fontes:',
  ...src,
  '',
  '*Responda:*',
  `1 #${code} → publicar agora no YouTube`,
  `2 #${code} motivo → descartar`,
  '',
  'Confira nomes e números com as fontes antes de aprovar. Link válido por 48 h.',
];
return [{ json: { number: cfg.approval?.to, text: lines.join('\n'), video: videoLink, cover: coverLink, caption: `#${code} · ${spec.headline}` } }];
