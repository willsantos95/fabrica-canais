// Pedido do roteiro do resumo diário de um esporte, a partir dos Shorts aprovados hoje.
const p = $('Próximo resumo').first().json;
const cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;
const all = typeof p.stories === 'string' ? JSON.parse(p.stories) : p.stories;
const max = cfg.recap?.max_stories || 8;
const stories = all.slice(-max);
const LABEL = { futebol: 'futebol', nba: 'NBA', nfl: 'NFL' }[p.sport] || p.sport;
const today = DateTime.now().setZone(cfg.schedule?.timezone || 'America/Sao_Paulo').toFormat('dd/MM');

const SYSTEM = `Você é o roteirista do canal "${cfg.name}" (${cfg.handle || ''}), em português do Brasil.
Tom: ${cfg.tone}

Escreva o roteiro do RESUMO DO DIA de ${LABEL} (${today}), um vídeo horizontal de 3 a 6 minutos com as notícias abaixo, nesta ordem ou na ordem que fizer mais sentido (mais importante primeiro).
Regras:
- Use SÓ os fatos que estão nas notícias recebidas (as narrações já foram conferidas). Não acrescente números, nomes ou resultados.
- Só ${LABEL}. Nada de outros esportes.
- Abertura: até 35 palavras, chamando as 2 ou 3 notícias mais fortes.
- Cada notícia: 60 a 95 palavras, reescrita com começo forte, contexto e por que importa; transição natural para a próxima.
- Fechamento: até 30 palavras, com uma pergunta para os comentários. Não peça inscrição.
- chapter: título curto do capítulo (até 40 caracteres). kicker: linha curta acima da manchete (placar, número ou contexto, até 40 caracteres).

Responda só com JSON:
{"title":"título do YouTube até 90 caracteres","description":"2 a 4 frases","tags":["até 10"],"thumbnail_lines":["linha 1 até 16 caracteres","linha 2 até 16 caracteres"],
 "intro":{"narration":"..."},"stories":[{"video_id":"...","chapter":"...","kicker":"...","narration":"..."}],"outro":{"narration":"..."}}`;

const input = `Escreva o roteiro e responda em JSON.\n\nNotícias de hoje:\n` + stories.map(s => JSON.stringify({
  video_id: s.video_id, manchete: s.headline, titulo: s.title,
  narracao_do_short: (s.beats || []).map(b => b.narration).join(' '),
  fontes: (s.sources || []).map(x => x.source).filter(Boolean),
})).join('\n');

return [{ json: { today, label: LABEL, stories, body: {
  model: cfg.recap?.script_model || cfg.news?.script_model || 'gpt-5.4-mini',
  instructions: SYSTEM, input,
  reasoning: { effort: 'low' },
  text: { format: { type: 'json_object' } },
  max_output_tokens: 8000,
} } }];
