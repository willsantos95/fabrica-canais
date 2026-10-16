// Monta o pedido de avaliação (modelo barato) com as notícias novas desta rodada.
const c = $('Canal').first().json;
const cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;
const recent = (typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || [];
const items = $input.all().map(i => i.json)
  .sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)))
  .slice(0, 80);

const SYSTEM = `Você é o editor-chefe do canal de Shorts esportivos "${cfg.name}" (futebol, NBA e NFL para o público brasileiro).
Avalie cada notícia de 0 a 10 pelo potencial de virar hoje um Short de 45 segundos que o brasileiro quer assistir.

Pontua alto:
- fato novo e concreto: resultado marcante, transferência ou contratação confirmada, lesão de jogador importante, recorde, demissão, polêmica com fato verificável;
- interesse do público brasileiro: clubes brasileiros, Seleção, brasileiros no exterior, grandes clubes europeus, times e astros populares da NBA e da NFL no Brasil;
- dá para explicar em 45 segundos com uma frase de análise (por que importa).

Nota 0: apostas e bônus, "onde assistir", Cartola ou fantasy, melhores momentos sem fato novo, agenda, propaganda, opinião sem fato, boato sem fonte.
Nota no máximo 3: mortes, crimes, tragédias pessoais, saúde mental, assuntos de família.
Notícias sobre o MESMO fato recebem o MESMO story_key (slug curto em minúsculas com os nomes principais, ex.: "eagles-qb-coagulo-panturrilha").
Se o fato já está na lista de pautas recentes, nota no máximo 3.
title_pt: manchete em português do Brasil, até 70 caracteres, fiel ao fato, sem clickbait mentiroso.
sport: futebol | nba | nfl. reason: uma frase curta.

Responda só com JSON: {"items":[{"id":"...","score":0,"story_key":"...","title_pt":"...","sport":"nba","reason":"..."}]} com todas as notícias recebidas.`;

const lines = items.map(n => JSON.stringify({ id: n.id, sport: n.sport, source: n.source, published: n.published_at,
  title: n.title, summary: String(n.summary || '').slice(0, 280) }));
const input = `Avalie as notícias abaixo e responda em JSON.\n\nPautas recentes (já usadas ou na fila):\n${recent.map(r => `- ${r.story_key}: ${r.title}`).join('\n') || '- nenhuma'}\n\nNotícias novas:\n${lines.join('\n')}`;

return [{ json: { body: {
  model: cfg.news?.scoring_model || 'gpt-5.4-nano',
  instructions: SYSTEM,
  input,
  reasoning: { effort: 'low' },
  text: { format: { type: 'json_object' } },
  max_output_tokens: 16000,
}, ids: items.map(n => n.id) } }];
