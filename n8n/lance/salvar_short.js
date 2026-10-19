// Junta o resultado do worker ao spec e prepara a gravação.
const v = $('Montar pedido').first().json;
const r = $('Checar vídeo').first().json;
// crédito das fotos livres (CC BY pede atribuição): entra na descrição antes das hashtags
const credits = (r.credits || []).filter((c, i, a) => c && a.findIndex(x => x.file === c.file) === i);
let description = v.spec.publishing.description;
if (credits.length) {
  const lines = description.split('\n');
  const tags = lines.pop();
  description = [...lines, 'Fotos:', ...credits.map(c => `• ${c.subject}: ${c.author} (${c.license}) ${c.page || ''}`.trim()), '', tags].join('\n').slice(0, 4900);
}
const spec = { ...v.spec,
  publishing: { ...v.spec.publishing, description },
  photo_credits: credits,
  beats: r.beats,
  outputs: { final_url: r.url, cover_url: r.cover_url, spec_url: r.spec_url, duration_s: r.duration_s },
  checks: (v.spec.checks || []).concat(r.checks || []) };
const assets = [
  { k: 'final', u: r.url, meta: { duration_s: r.duration_s } },
  { k: 'thumb', u: r.cover_url, meta: { cover: true } },
  { k: 'spec', u: r.spec_url, meta: {} },
];
return [{ json: { video_id: v.video_id, spec: JSON.stringify(spec), checks: JSON.stringify(spec.checks), assets: JSON.stringify(assets), duration_s: r.duration_s } }];
