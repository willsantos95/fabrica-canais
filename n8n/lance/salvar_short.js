// Junta o resultado do worker ao spec e prepara a gravação.
const v = $('Montar pedido').first().json;
const r = $('Checar vídeo').first().json;
const spec = { ...v.spec,
  beats: r.beats,
  outputs: { final_url: r.url, cover_url: r.cover_url, spec_url: r.spec_url, duration_s: r.duration_s },
  checks: (v.spec.checks || []).concat(r.checks || []) };
const assets = [
  { k: 'final', u: r.url, meta: { duration_s: r.duration_s } },
  { k: 'thumb', u: r.cover_url, meta: { cover: true } },
  { k: 'spec', u: r.spec_url, meta: {} },
];
return [{ json: { video_id: v.video_id, spec: JSON.stringify(spec), checks: JSON.stringify(spec.checks), assets: JSON.stringify(assets), duration_s: r.duration_s } }];
