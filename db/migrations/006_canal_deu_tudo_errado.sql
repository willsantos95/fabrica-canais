-- Canal "Deu Tudo Errado" (@DeuTudoErradoTV), PT-BR. Gerado por channels/deu-tudo-errado.py.
-- Rode com psql/cliente SQL. ATENÇÃO: o nó Postgres do n8n troca {{ ... }} da consulta por expressões
-- (os placeholders dos prompts viram "undefined"); para aplicar pelo n8n, troque {{ }} por << >> e use replace().
-- Entra PAUSADO (active = false): ative depois de criar o canal no YouTube, a credencial no n8n e a cópia
-- do factory.publish com essa credencial (troque youtube.publish_workflow_id = 'PENDENTE' pelo id da cópia).
BEGIN;

INSERT INTO channels (slug, name, config, active)
VALUES ('deu-tudo-errado', 'Deu Tudo Errado', $cfg${"slug": "deu-tudo-errado", "name": "Deu Tudo Errado", "handle": "@DeuTudoErradoTV", "youtube_channel_id": "PREENCHER_UC...", "language": "pt-BR", "niche": "O dia em que tudo deu errado: desastres históricos bizarros, erros improváveis e acidentes reais explicados pelas investigações", "tone": "narrador de documentário, curioso e envolvente, suspense pela ordem dos fatos, respeitoso com as vítimas, ironia leve só nos casos sem mortes", "point_of_view": "Todo desastre é uma corrente de pequenos detalhes. O canal mostra qual detalhe virou tudo, o que a investigação descobriu e o que mudou no mundo depois. Fatos com fonte, sem sensacionalismo.", "format": {"long_minutes": [10, 14], "words_per_minute": 150, "shots_per_video": 55, "shorts_per_video": 3, "blocks": [6, 9]}, "voice": {"provider": "edge-tts", "fallback": "edge-tts", "voice_id": "", "edge_voice": "pt-BR-AntonioNeural", "rate": "+0%"}, "visual": {"style_block": "[STYLE] cinematic 2D illustrated documentary, painterly digital art, muted vintage palette with strong red and amber accents, dramatic volumetric light, atmospheric haze, historically accurate details, 16:9 composition, high readability, no text", "negative_prompt": "gore, blood, injured people, dead bodies, photorealistic faces of real people, celebrity, logo, watermark, gibberish text, extra limbs, distorted hands, cartoonish, cute", "image_provider": "cloudflare", "image_fallback": "gemini", "video_provider": "veo", "video_fallback": "kling", "ai_motion_shots_max": 0, "brand": {"primary": "#C62828", "secondary": "#FFB300", "font": "Inter", "logo_url": ""}}, "audio": {"music_library": "fabrica/channels/deu-tudo-errado/music/", "music_volume_db": -24, "loudness_lufs": -14}, "schedule": {"timezone": "America/Sao_Paulo", "production_days": ["tue", "thu", "sat"], "production_hour": 2, "min_queued_topics": 5, "publish_times": ["19:00"], "shorts_time": "12:00"}, "youtube": {"category_id": "27", "default_tags": ["deu tudo errado", "desastres históricos", "história", "acidentes", "curiosidades"], "hashtags": ["DeuTudoErrado", "Historia"], "contains_synthetic_media": true, "made_for_kids": false, "publish_workflow_id": "PENDENTE"}, "tiktok": {"hashtags": ["DeuTudoErrado", "historia", "curiosidades"]}, "texts": {"disclaimer": "Narração e ilustrações geradas com auxílio de IA a partir das fontes listadas. Eventos reais contados com respeito às vítimas."}, "prices": {}, "prompts": {"script": "You are the head writer of the faceless YouTube channel \"{{channel.name}}\", a Brazilian Portuguese channel about real historical disasters, blunders and accidents: the day everything went wrong.\n\nChannel\n- Niche: {{channel.niche}}\n- Language of the narration: Brazilian Portuguese (pt-BR), natural spoken Portuguese from Brazil, never Portugal.\n- Tone: {{channel.tone}}\n- Point of view: {{channel.point_of_view}}\n\nYour job: research the topic on the web, then write the full narration of ONE long video.\n\nResearch rules\n- Use the web_search tool before writing. Prefer official investigation reports (CENIPA, NTSB, AAIB, BEA, national archives), encyclopedias with references, museums, universities and established newspapers.\n- Every concrete fact (date, time, number of people, measurements, names of ships, flights, companies and places, quotes) must come from a source you actually found. List each source once in \"sources\" with the exact claim it supports.\n- Never invent dialogue, thoughts, names or numbers. If sources disagree, say so in one short sentence. If something is unknown, say it is unknown.\n- Name real people only when the sources name them and it matters for the story. Treat victims with dignity: no graphic descriptions of injuries or bodies, no jokes about deaths.\n\nStory structure (one block per part, {{blocks_min}} to {{blocks_max}} blocks)\n1. Cold open: start inside the critical minute, at the moment things start to go wrong, then stop on a question (\"Como chegamos até aqui?\"). No greeting, no channel name.\n2. Context: the place, the time, what was normal that day and why nobody expected anything.\n3. The chain of small decisions and details that made the disaster possible (this is the heart of the channel: \"por um detalhe\").\n4. The moment it all went wrong, minute by minute, with the sensory details the sources support.\n5. The response, the consequences and the numbers.\n6. The investigation: what was discovered and who was responsible, according to the sources.\n7. What changed afterwards (rules, technology, engineering, laws) and why it still matters today.\n8. Closing: one short reflective line and a question that invites a comment (e.g. which detail would you have noticed). No \"like and subscribe\" begging.\n\nWriting rules\n- Total narration: between {{words_min}} and {{words_max}} words, read aloud by a synthetic voice at about {{wpm}} words per minute.\n- Each block 120 to 320 words. Spoken style: short sentences, suspense through order of facts, not through adjectives. No lists, no headings inside the narration, no stage directions, no emojis, no URLs.\n- Write numbers, dates and units the way they are spoken in Brazilian Portuguese (e.g. \"mil oitocentos e catorze\", \"cerca de um milhão e quinhentos mil litros\").\n- Avoid clichés (\"você não vai acreditar\", \"prepare-se\", \"chocante\"). Avoid sensationalism and conspiracy theories.\n- Every block must contain at least one specific, sourced detail.\n\nOutput\nReply with ONLY one JSON object wrapped in <json> and </json>, with this shape:\n\n<json>\n{\n  \"titles\": [\"10 YouTube titles in pt-BR, max 60 characters; at least 5 start with \\\"O dia em que\\\"; curiosity-driven, no clickbait lies\"],\n  \"chosen_title\": \"the title you recommend\",\n  \"hook_options\": [\"5 alternative opening lines in pt-BR, max 30 words each\"],\n  \"sources\": [{\"id\": \"src1\", \"title\": \"page title\", \"url\": \"https://...\", \"claim\": \"the exact fact used\"}],\n  \"blocks\": [\n    {\"block_id\": \"b01\", \"title\": \"short chapter title in pt-BR\", \"narration\": \"spoken text in pt-BR\", \"source_ids\": [\"src1\"]}\n  ]\n}\n</json>\n\nblock_id values are b01, b02, b03... in order. Chapter titles are short (max 40 characters) because they become YouTube chapters. Use only source ids that exist in \"sources\".\n", "script_input": "Tema: {{topic}}\n\nPesquise o caso na web (fontes oficiais primeiro) e escreva o vídeo completo agora.", "shotlist": "You are the visual director of the faceless YouTube channel \"{{channel.name}}\", a documentary channel about real historical disasters and accidents.\n\nYou receive the finished narration of one video (in Brazilian Portuguese), split into blocks. Turn it into a shot list of about {{shots_total}} shots, in narration order, so that one illustrated image is shown on screen while each piece of narration is read.\n\nRules for each shot\n- \"narration_span\": the exact words of the narration this shot covers, copied verbatim and contiguous from the block (same spelling, accents and punctuation). Spans of one block, in order, must cover the whole block without gaps or overlaps. A good span is 1 or 2 sentences (about 8 to 14 seconds of speech).\n- \"visual_prompt\": in ENGLISH, describe subject, action, setting, era and framing (wide / medium / close-up). Be historically accurate for the place and year (clothing, vehicles, architecture, machines). Concrete and visual. Do NOT include art style words; the channel style is added automatically.\n- Show tension through environment, scale, weather, machines, maps, documents and silhouettes. Never show gore, injuries, dead bodies or people in agony. For tragic moments use symbolic images (empty street, stopped clock, smoke on the horizon, rescue lights).\n- No real people's faces or likenesses, no celebrities, no brand logos, no readable text in the image unless it is a short label you also put in \"text_overlay\".\n- Keep recurring elements consistent across shots (the same ship, the same building, the same aircraft described the same way every time).\n- \"text_overlay\": null, or a label of at most 4 words in pt-BR. Use it on the first shot of each block for place and year (e.g. \"LONDRES, 1814\") and for key numbers (e.g. \"1,5 MILHÃO DE LITROS\").\n- \"kenburns\": one of push_in, pull_out, pan_left, pan_right, pan_up, pan_down. Vary it; never the same movement more than twice in a row. Prefer slow push_in for tension.\n- \"is_hook\": true only for the shots of the first 10 seconds of the video.\n- No two shots may have the same visual_prompt.\n\nDistribute shots proportionally to the length of each block.\n\nOutput\nReply with ONLY one JSON object wrapped in <json> and </json>:\n\n<json>\n{\n  \"blocks\": [\n    {\"block_id\": \"b01\", \"shots\": [\n      {\"narration_span\": \"...\", \"visual_prompt\": \"...\", \"text_overlay\": \"LONDRES, 1814\", \"kenburns\": \"push_in\", \"is_hook\": true}\n    ]}\n  ],\n  \"thumbnail\": {\n    \"phrases\": [\"2 lines in pt-BR, max 4 words total, line 2 is the impact word (e.g. \\\"RIO DE\\\", \\\"CERVEJA\\\")\"],\n    \"image_prompt\": \"the most striking moment of the event, main subject on the right third, left half dark and empty for text, dramatic light, high contrast, no gore\"\n  }\n}\n</json>\n", "reasoning_effort": "medium", "web_search": true}}$cfg$::jsonb, false)
ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name,
  -- rodar de novo atualiza prompts e textos, mas mantém aprovação e o publish já configurado
  config = EXCLUDED.config
    || jsonb_build_object('approval', channels.config->'approval')
    || jsonb_build_object('youtube', (EXCLUDED.config->'youtube') || jsonb_build_object('publish_workflow_id',
         COALESCE(channels.config->'youtube'->'publish_workflow_id', EXCLUDED.config->'youtube'->'publish_workflow_id'))),
  updated_at = now();

-- aprovação vai para o mesmo número do Career Levels
UPDATE channels SET config = config || jsonb_build_object('approval',
  COALESCE((SELECT config->'approval' FROM channels WHERE slug = 'career-levels'),
           '{"channel": "whatsapp", "to": "55DDDNUMERO", "timeout_hours": 24}'::jsonb))
WHERE slug = 'deu-tudo-errado' AND COALESCE(jsonb_typeof(config->'approval'), 'null') = 'null';

INSERT INTO topics (channel_id, title, priority, source)
SELECT (SELECT id FROM channels WHERE slug = 'deu-tudo-errado'), x.title, x.priority, 'manual'
FROM (VALUES
  ('O dia em que Londres foi inundada por cerveja (1814)', 10),
  ('O dia em que uma onda de melaço engoliu Boston (1919)', 20),
  ('O dia em que um avião ficou sem combustível no ar: o Planador de Gimli (1983)', 30),
  ('O dia em que a Austrália perdeu uma guerra para os emus (1932)', 40),
  ('O dia em que uma baleia foi explodida numa praia do Oregon (1970)', 50),
  ('O dia em que a ponte de Tacoma Narrows dançou até cair (1940)', 60),
  ('O dia em que um navio de guerra afundou na viagem inaugural: o Vasa (1628)', 70),
  ('O dia em que 1,5 milhão de balões caíram sobre Cleveland (1986)', 80),
  ('O dia em que um erro de unidades destruiu uma sonda em Marte (1999)', 90),
  ('O dia em que um Boeing 747 perdeu os quatro motores: voo 9 da British Airways (1982)', 100),
  ('A praga da dança: o verão em que Estrasburgo não parou de dançar (1518)', 110),
  ('O dia em que o Brasil apagou: o blecaute de 11 de março de 1999', 120),
  ('O dia em que um navio travou o Canal de Suez: Ever Given (2021)', 130),
  ('O dia em que um foguete explodiu por um bug: Ariane 5 (1996)', 140),
  ('O dia em que a estação espacial Skylab caiu na Austrália (1979)', 150),
  ('Houston, temos um problema: o resgate da Apollo 13 (1970)', 160),
  ('O dia em que uma explosão nuclear no espaço apagou o Havaí: Starfish Prime (1962)', 170),
  ('O Grande Fedor: o verão em que Londres não conseguia respirar (1858)', 180),
  ('O ano sem verão: quando um vulcão mudou o clima do mundo (1816)', 190),
  ('A tempestade solar que incendiou telégrafos: o Evento Carrington (1859)', 200),
  ('O dia em que o Hindenburg pegou fogo (1937)', 210),
  ('O dia em que um navio explodiu e destruiu Halifax (1917)', 220),
  ('O dia em que uma represa estourou sobre Johnstown (1889)', 230),
  ('O Grande Incêndio de Londres (1666)', 240),
  ('O Grande Incêndio de Chicago (1871)', 250),
  ('O efeito cobra: quando pagar por cobras mortas criou mais cobras', 260),
  ('O dia em que um lago soltou uma nuvem mortal: Lago Nyos (1986)', 270),
  ('A campanha contra os pardais que deu errado na China (1958)', 280),
  ('O acidente do césio-137 em Goiânia (1987)', 290),
  ('A noite em que o reator de Chernobyl explodiu (1986)', 300)
) AS x(title, priority)
ON CONFLICT (channel_id, title) DO NOTHING;

COMMIT;

-- Ativar quando estiver tudo pronto:
-- UPDATE channels SET active = true,
--   config = jsonb_set(config, '{youtube,publish_workflow_id}', to_jsonb('ID_DA_COPIA_DO_PUBLISH'::text))
-- WHERE slug = 'deu-tudo-errado';

-- Aplicado em 15/10: publish próprio do canal (factory.publish · Deu Tudo Errado = lljV9Hcv2DjR57iT) e canal ativo.
-- UPDATE channels SET active = true,
--   config = jsonb_set(config, '{youtube,publish_workflow_id}', to_jsonb('lljV9Hcv2DjR57iT'::text))
-- WHERE slug = 'deu-tudo-errado';
