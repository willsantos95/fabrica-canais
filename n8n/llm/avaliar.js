// Normaliza a resposta no formato da OpenAI (output_text, usage, model) ou passa para o próximo provedor.
const st = $('Próximo provedor').last().json;
const r = $input.first().json;
const fail = msg => [{ json: { ...st, done: false, step: st.step + 1, errors: [...st.errors, `${st.provider}: ${String(msg).slice(0, 300)}`] } }];
const ok = resp => [{ json: { done: true, response: { ...resp, provider: st.provider, tried: st.errors } } }];

if (st.provider === 'prepared') {
  return ok({ status: 'completed', model: 'claude-pronto', output_text: String(st.prepared), usage: { input_tokens: 0, output_tokens: 0 }, output: [] });
}
if (r.error) return fail(r.error.message || JSON.stringify(r.error));

if (st.provider === 'openai') {
  if (r.status && r.status !== 'completed') return fail(`status ${r.status} ${JSON.stringify(r.incomplete_details || {})}`);
  const text = r.output_text || (r.output || []).filter(o => o.type === 'message')
    .flatMap(o => o.content || []).filter(c => c.type === 'output_text').map(c => c.text).join('');
  if (!text) return fail('resposta vazia');
  return ok({ ...r, output_text: text });
}

// gemini
const c = (r.candidates || [])[0];
if (!c) return fail('sem resposta: ' + JSON.stringify(r.promptFeedback || r).slice(0, 200));
if (c.finishReason && !['STOP', 'FINISH_REASON_UNSPECIFIED'].includes(c.finishReason)) return fail('finishReason ' + c.finishReason);
let text = (c.content?.parts || []).filter(p => !p.thought).map(p => p.text || '').join('');
if (!text.trim()) return fail('texto vazio');
// links da pesquisa do Google vêm como redirecionamento: troca pelo endereço real da página
const chunks = (c.groundingMetadata?.groundingChunks || []).map(x => x.web).filter(Boolean).slice(0, 20);
const sources = [];
for (const w of chunks) {
  let url = w.uri;
  try {
    const res = await this.helpers.httpRequest({ url: w.uri, method: 'GET', disableFollowRedirect: true, followRedirect: false, ignoreHttpStatusErrors: true, returnFullResponse: true, timeout: 10000 });
    url = res.headers?.location || url;
  } catch (e) {}
  sources.push({ title: w.title, url });
  if (url !== w.uri) text = text.split(w.uri).join(url);
}
const u = r.usageMetadata || {};
return ok({
  status: 'completed', model: r.modelVersion || st.model, output_text: text,
  usage: { input_tokens: (u.promptTokenCount || 0) + (u.toolUsePromptTokenCount || 0), output_tokens: (u.candidatesTokenCount || 0) + (u.thoughtsTokenCount || 0) },
  output: [], grounding_sources: sources, web_search_queries: c.groundingMetadata?.webSearchQueries || [],
});
