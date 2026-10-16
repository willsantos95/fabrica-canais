// Pedido do roteiro do Short (modelo barato): só com os fatos das fontes da pauta.
const p = $('Próxima pauta').first().json;
const cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;
const notes = typeof p.notes === 'string' ? JSON.parse(p.notes) : (p.notes || {});
const sport = notes.sport || 'futebol';
const [minS, maxS] = cfg.format?.short_seconds || [40, 55];
const wpm = cfg.format?.words_per_minute || 175;
const minW = Math.round(minS * wpm / 60), maxW = Math.round(maxS * wpm / 60);
const SPORT = { futebol: 'futebol', nba: 'NBA (basquete)', nfl: 'NFL (futebol americano)' }[sport] || sport;

const SYSTEM = `Você é o roteirista do canal de Shorts esportivos "${cfg.name}" (${cfg.handle || ''}), em português do Brasil.
Tom: ${cfg.tone}
Ponto de vista: ${cfg.point_of_view}

Escreva o roteiro de UM Short de ${minS} a ${maxS} segundos (entre ${minW} e ${maxW} palavras de narração no total) sobre UMA notícia de ${SPORT}.
Regras de conteúdo (obrigatórias):
- Use SÓ os fatos das fontes recebidas. Nomes, números, placares, valores e datas só se estiverem nas fontes. Se uma fonte estiver em inglês, traduza tudo para o português, inclusive termos técnicos (ex.: "blood clot" = coágulo); nada de palavras em inglês entre aspas.
- Nada de boato, opinião disfarçada de fato ou exagero. Se as fontes divergem, diga "segundo o <veículo>".
- Fale só deste esporte e desta notícia; não misture outros esportes.
- Primeira frase = gancho com o fato principal, até 14 palavras, sem "olá", sem "neste vídeo".
- Depois: contexto e números (2 a 4 trechos) e, no último trecho, por que isso importa (o que muda na tabela, no elenco ou na temporada). Pode fechar com uma pergunta curta para os comentários.
- Narração para ouvir: frases curtas, números por extenso só quando ficar mais natural; placar escrito "112 a 108".
- Não peça inscrição na narração (o cartão final já faz isso).

Divida em 5 a 7 trechos ("beats"). Cada trecho tem a narração (1 a 3 frases) e 1 visual:
- {"type":"card","card":{...}} cartão de dados desenhado pelo sistema, TODO em português (nada em inglês), com textos CURTOS tirados das fontes:
  * {"kind":"score","title":"Final","home":"Time A","away":"Time B","home_score":"112","away_score":"108","note":"..."}
  * {"kind":"stat","value":"42","label":"pontos de Fulano","note":"..."}
  * {"kind":"list","title":"...","items":["...","...","..."]} (2 a 4 itens de até 40 caracteres)
  * {"kind":"fact","title":"...","text":"frase de até 90 caracteres"}
  * {"kind":"quote","text":"citação curta da fonte, TRADUZIDA para o português","source":"quem disse"}
- {"type":"image","prompt":"..."} ilustração gerada por IA. Prompt em INGLÊS descrevendo a cena (ação do esporte, estádio, torcida, vestiário, prancheta, bola, troféu), composição quadrada. Proibido: rosto reconhecível, nome de atleta real, logos, escudos, números de camisa, texto na imagem.
Use pelo menos 2 cartões e pelo menos 2 imagens. Placar ou número marcante → cartão.

Responda só com JSON:
{"headline":"manchete para a tela, até 70 caracteres","title":"título do YouTube até 90 caracteres, fiel ao fato, sem hashtags","description":"2 ou 3 frases resumindo o fato","tags":["até 8 tags"],"beats":[{"narration":"...","visual":{...}}]}`;

const sources = (notes.sources || []).slice(0, 6).map(s => ({ veiculo: s.source, titulo: s.title, resumo: String(s.summary || '').slice(0, 700), publicado: s.published_at }));
const input = `Escreva o roteiro e responda em JSON.\n\nPauta: ${p.title}\nEsporte: ${SPORT}\nPor que é notícia: ${notes.reason || '-'}\n\nFontes:\n${sources.map(s => JSON.stringify(s)).join('\n')}`;

return [{ json: { sport, body: {
  model: cfg.news?.script_model || 'gpt-5.4-mini',
  instructions: SYSTEM,
  input,
  reasoning: { effort: 'low' },
  text: { format: { type: 'json_object' } },
  max_output_tokens: 6000,
} } }];
