-- Thumbnail "antes e depois" (DIA 1 x DIA N) no Um Ano Preso: tela dividida na diagonal por um raio,
-- lado esquerdo claro e tranquilo, lado direito escuro e perigoso, números grandes no topo.
-- O roteiro pode mandar spec.thumbnail.split {left_prompt, right_prompt, left_label, right_label};
-- sem isso, o worker monta os dois lados a partir do thumbnail.image_prompt e dos selos "DIA X".
UPDATE channels
SET config = jsonb_set(config, '{thumbnail}', COALESCE(config->'thumbnail', '{}'::jsonb) || '{"style": "split"}'::jsonb),
    updated_at = now()
WHERE slug = 'um-ano-preso';
