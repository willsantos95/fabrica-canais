const p = $('Plano de publicação').first().json;
const r = $('Checar envio').first().json;
const LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };
const lines = [
  `✅ *Publicado* · ${p.channel}`,
  `*${p.title}*`,
  r.url,
  p.playlist_id ? `Playlist: ${LABEL[p.sport] || p.sport}` : `⚠️ Sem playlist de ${LABEL[p.sport] || p.sport} (rode "Criar playlists" no factory.publish do canal).`,
];
return [{ json: { number: p.number, text: lines.join('\n') } }];
