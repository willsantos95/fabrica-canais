// Prévia no WhatsApp: quais notícias viraram pauta nesta rodada.
const e = $('Escolher pautas').first().json;
if (!e.picks.length || !e.number) return [];
const TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };
const lines = [`📰 *${e.name}* · ${e.picks.length} pauta(s) nova(s)${e.preview ? ' (prévia: nada é produzido ainda)' : ''}`, ''];
e.picks.forEach((p, i) => {
  const s = p.sources || [];
  lines.push(`${i + 1}. ${TAG[p.sport] || p.sport} · nota ${p.score}`);
  lines.push(`*${p.title_pt}*`);
  if (p.reason) lines.push(`_${p.reason}_`);
  if (s[0]) lines.push(`${s[0].source}: ${s[0].url}${s.length > 1 ? ` (+${s.length - 1} fonte(s))` : ''}`);
  lines.push('');
});
lines.push(`Avaliadas nesta rodada: ${e.scored}. Vagas na fila: ${e.room}.`);
return [{ json: { number: e.number, text: lines.join('\n') } }];
