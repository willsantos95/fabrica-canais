const p = $('Plano de publicação').first().json;
const b = $input.first().json.body;
if (!b) throw new Error('Envio ao YouTube: tempo esgotado esperando o worker');
if (b.status !== 'succeeded') throw new Error('Envio ao YouTube falhou: ' + (b.error || 'sem detalhe'));
const byRef = Object.fromEntries((b.result.uploads || []).map(u => [u.ref, u]));
const up = byRef.video || {};
if (!up.id) throw new Error('O YouTube não aceitou o vídeo: ' + (up.error || 'sem id na resposta'));
return [{ json: { youtube_id: up.id, url: p.kind === 'short' ? `https://youtube.com/shorts/${up.id}` : `https://youtu.be/${up.id}` } }];
