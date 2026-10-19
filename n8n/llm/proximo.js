// Escolhe o próximo provedor da ordem (pronto → gemini → openai) e monta o pedido.
const i = $input.first().json;
const order = i.order || [];
let step = i.step || 0;
const errors = i.errors || [];
while (step < order.length && order[step] === 'prepared' && !String(i.prepared || '').trim()) step++;
if (step >= order.length) {
  throw new Error(`Nenhum provedor de IA conseguiu responder (${i.stage || 'etapa'}): ` + (errors.join(' | ') || 'ordem vazia'));
}
const provider = order[step];
const b = i.body || {};
let request = null, model = null;
if (provider === 'openai') {
  request = b;
  model = b.model;
} else if (provider === 'gemini') {
  const g = i.gemini || {};
  const search = (b.tools || []).some(t => t.type === 'web_search');
  // no plano grátis, a pesquisa no Google (grounding) só funciona nos modelos 2.5
  model = search ? (g.search_model || 'gemini-2.5-flash') : (g.model || 'gemini-3.5-flash');
  request = {
    systemInstruction: { parts: [{ text: String(b.instructions || '') }] },
    contents: [{ role: 'user', parts: [{ text: typeof b.input === 'string' ? b.input : JSON.stringify(b.input) }] }],
    generationConfig: { maxOutputTokens: Math.min(Number(b.max_output_tokens) || 16000, 65536) },
  };
  if (search) request.tools = [{ google_search: {} }];
  else if (b.text?.format?.type === 'json_object') request.generationConfig.responseMimeType = 'application/json';
}
return [{ json: { ...i, step, errors, provider, model, request } }];
