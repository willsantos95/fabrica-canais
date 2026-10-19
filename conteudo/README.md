# Conteúdo pronto (escrito pelo Claude)

A fábrica escolhe a IA de texto por canal em `channels.config.llm.order`:

| Valor | O que faz | Custo |
|---|---|---|
| `prepared` | usa o roteiro/shotlist gravado no tema (`topics.prepared`) | zero |
| `gemini` | Gemini no plano grátis (pesquisa no Google com `gemini-2.5-flash`; sem pesquisa `gemini-3.5-flash`) | zero, dentro da cota |
| `openai` | OpenAI (gpt-5.5 no vídeo longo, mini/nano nas notícias) | pago |

Padrão atual: vídeo longo `["prepared","gemini","openai"]`; Lance Rápido `["gemini","openai"]`.
Se um provedor falhar (cota, fora do ar, resposta cortada), o `factory.llm` passa para o próximo.
Temas com conteúdo pronto saem primeiro da fila (`claim_next_topic`).

## Como pedir ao Claude

"Prepare os próximos N temas do Deu Tudo Errado / Career Levels." O Claude:
1. lê os temas da fila e o formato do canal (minutos, palavras por minuto, blocos, planos);
2. pesquisa as fontes na web e escreve roteiro + shotlist num script desta pasta (`<canal>/<tema>.py`);
3. gera o JSON e envia para o webhook `factory.preparar`, que confere o formato e grava no tema.

Formato de `prepared`: `script` = mesmo JSON que a IA devolveria (titles, chosen_title, hook_options, sources,
blocks, subject, tags, hashtags); `shotlist` = {blocks: [{block_id, shots: [{narration_span, visual_prompt,
text_overlay, kenburns, is_hook}]}], thumbnail}. Cada `narration_span` é um trecho literal da narração do bloco.
