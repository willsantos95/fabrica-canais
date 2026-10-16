import { workflow, node, trigger, switchCase, ifElse, expr } from '@n8n/workflow-sdk';

const t_cron = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.2,
  config: {
    "name": "A cada 20 min (8h-23h)",
    "parameters": {
      "rule": {
        "interval": [
          {
            "field": "cronExpression",
            "expression": "*/20 8-23 * * *"
          }
        ]
      }
    },
    "position": [
      0,
      -100
    ]
  },
  output: [
    {}
  ]
});

const t_manual = trigger({
  type: "n8n-nodes-base.manualTrigger",
  version: 1,
  config: {
    "name": "Testar (ignora prévia e horário)",
    "parameters": {},
    "position": [
      0,
      100
    ]
  },
  output: [
    {}
  ]
});

const config = node({
  type: "n8n-nodes-base.set",
  version: 3.4,
  config: {
    "name": "Config",
    "parameters": {
      "assignments": {
        "assignments": [
          {
            "id": "c-worker",
            "name": "worker_url",
            "value": "https://render.relampagodeofertas.shop",
            "type": "string"
          },
          {
            "id": "c-instance",
            "name": "evolution_instance",
            "value": "fabrica-videos",
            "type": "string"
          },
          {
            "id": "c-force",
            "name": "force",
            "value": expr("{{ !!$('Testar (ignora prévia e horário)').isExecuted }}"),
            "type": "boolean"
          }
        ]
      },
      "includeOtherFields": true,
      "options": {}
    },
    "position": [
      240,
      0
    ]
  },
  output: [
    {}
  ]
});

const prox = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Próxima pauta",
    "parameters": {
      "operation": "executeQuery",
      "query": "-- $1 = true no teste manual: ignora canal pausado, modo prévia, horário e limite do dia\nWITH ch AS (\n  SELECT c.id, c.config FROM channels c\n  WHERE c.config->'format'->>'type' = 'news_short'\n    AND ($1::boolean OR (c.active AND COALESCE((c.config->'news'->>'preview')::boolean, true) = false))\n    AND ($1::boolean OR extract(hour FROM now() AT TIME ZONE 'America/Sao_Paulo')\n         BETWEEN COALESCE((c.config->'news'->'active_hours'->>0)::int, 8) AND COALESCE((c.config->'news'->'active_hours'->>1)::int, 23))\n    -- um Short por vez por canal\n    AND NOT EXISTS (SELECT 1 FROM videos v WHERE v.channel_id = c.id AND v.status IN ('scripting','voicing','imaging','motion','assembling','derivatives')\n                    AND v.updated_at > now() - interval '45 minutes')\n    AND ($1::boolean OR (SELECT count(*) FROM videos v WHERE v.channel_id = c.id AND v.spec->>'type' = 'news_short'\n         AND v.created_at >= date_trunc('day', now() AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'America/Sao_Paulo')\n         < COALESCE((c.config->'news'->>'max_shorts_per_day')::int, 10))\n  ORDER BY random() LIMIT 1\n), t AS (\n  SELECT t.id, t.title, t.notes FROM topics t\n  WHERE t.channel_id = (SELECT id FROM ch) AND t.status = 'queued' AND t.source = 'news'\n  ORDER BY t.priority, t.created_at DESC\n  LIMIT 1 FOR UPDATE SKIP LOCKED\n), up AS (\n  UPDATE topics SET status = 'in_production' WHERE id = (SELECT id FROM t) RETURNING id\n), v AS (\n  INSERT INTO videos (channel_id, topic_id, status, spec)\n  SELECT ch.id, up.id, 'scripting', jsonb_build_object('type', 'news_short') FROM ch, up\n  RETURNING id\n)\nSELECT v.id AS video_id, t.id AS topic_id, t.title, t.notes, ch.config, ch.id AS channel_id FROM v, t, ch;",
      "options": {
        "queryReplacement": expr("{{ [ $json.force ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      480,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "topic_id": "t",
      "title": "x",
      "notes": "{}",
      "config": {},
      "channel_id": "c"
    }
  ]
});

const ped = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Pedido do roteiro",
    "parameters": {
      "jsCode": "// Pedido do roteiro do Short (modelo barato): só com os fatos das fontes da pauta.\nconst p = $('Próxima pauta').first().json;\nconst cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;\nconst notes = typeof p.notes === 'string' ? JSON.parse(p.notes) : (p.notes || {});\nconst sport = notes.sport || 'futebol';\nconst [minS, maxS] = cfg.format?.short_seconds || [40, 55];\nconst wpm = cfg.format?.words_per_minute || 175;\nconst minW = Math.round(minS * wpm / 60), maxW = Math.round(maxS * wpm / 60);\nconst SPORT = { futebol: 'futebol', nba: 'NBA (basquete)', nfl: 'NFL (futebol americano)' }[sport] || sport;\n\nconst SYSTEM = `Você é o roteirista do canal de Shorts esportivos \"${cfg.name}\" (${cfg.handle || ''}), em português do Brasil.\nTom: ${cfg.tone}\nPonto de vista: ${cfg.point_of_view}\n\nEscreva o roteiro de UM Short de ${minS} a ${maxS} segundos (entre ${minW} e ${maxW} palavras de narração no total) sobre UMA notícia de ${SPORT}.\nRegras de conteúdo (obrigatórias):\n- Use SÓ os fatos das fontes recebidas. Nomes, números, placares, valores e datas só se estiverem nas fontes. Se uma fonte estiver em inglês, traduza.\n- Nada de boato, opinião disfarçada de fato ou exagero. Se as fontes divergem, diga \"segundo o <veículo>\".\n- Fale só deste esporte e desta notícia; não misture outros esportes.\n- Primeira frase = gancho com o fato principal, até 14 palavras, sem \"olá\", sem \"neste vídeo\".\n- Depois: contexto e números (2 a 4 trechos) e, no último trecho, por que isso importa (o que muda na tabela, no elenco ou na temporada). Pode fechar com uma pergunta curta para os comentários.\n- Narração para ouvir: frases curtas, números por extenso só quando ficar mais natural; placar escrito \"112 a 108\".\n- Não peça inscrição na narração (o cartão final já faz isso).\n\nDivida em 5 a 7 trechos (\"beats\"). Cada trecho tem a narração (1 a 3 frases) e 1 visual:\n- {\"type\":\"card\",\"card\":{...}} cartão de dados desenhado pelo sistema, em português, com textos CURTOS tirados das fontes:\n  * {\"kind\":\"score\",\"title\":\"Final\",\"home\":\"Time A\",\"away\":\"Time B\",\"home_score\":\"112\",\"away_score\":\"108\",\"note\":\"...\"}\n  * {\"kind\":\"stat\",\"value\":\"42\",\"label\":\"pontos de Fulano\",\"note\":\"...\"}\n  * {\"kind\":\"list\",\"title\":\"...\",\"items\":[\"...\",\"...\",\"...\"]} (2 a 4 itens de até 40 caracteres)\n  * {\"kind\":\"fact\",\"title\":\"...\",\"text\":\"frase de até 90 caracteres\"}\n  * {\"kind\":\"quote\",\"text\":\"citação curta que está na fonte\",\"source\":\"quem disse\"}\n- {\"type\":\"image\",\"prompt\":\"...\"} ilustração gerada por IA. Prompt em INGLÊS descrevendo a cena (ação do esporte, estádio, torcida, vestiário, prancheta, bola, troféu), composição quadrada. Proibido: rosto reconhecível, nome de atleta real, logos, escudos, números de camisa, texto na imagem.\nUse pelo menos 2 cartões e pelo menos 2 imagens. Placar ou número marcante → cartão.\n\nResponda só com JSON:\n{\"headline\":\"manchete para a tela, até 70 caracteres\",\"title\":\"título do YouTube até 90 caracteres, fiel ao fato, sem hashtags\",\"description\":\"2 ou 3 frases resumindo o fato\",\"tags\":[\"até 8 tags\"],\"beats\":[{\"narration\":\"...\",\"visual\":{...}}]}`;\n\nconst sources = (notes.sources || []).slice(0, 6).map(s => ({ veiculo: s.source, titulo: s.title, resumo: String(s.summary || '').slice(0, 700), publicado: s.published_at }));\nconst input = `Escreva o roteiro e responda em JSON.\\n\\nPauta: ${p.title}\\nEsporte: ${SPORT}\\nPor que é notícia: ${notes.reason || '-'}\\n\\nFontes:\\n${sources.map(s => JSON.stringify(s)).join('\\n')}`;\n\nreturn [{ json: { sport, body: {\n  model: cfg.news?.script_model || 'gpt-5.4-mini',\n  instructions: SYSTEM,\n  input,\n  reasoning: { effort: 'low' },\n  text: { format: { type: 'json_object' } },\n  max_output_tokens: 6000,\n} } }];\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "sport": "nba",
      "body": {}
    }
  ]
});

const ai = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "OpenAI: roteiro",
    "parameters": {
      "method": "POST",
      "url": "https://api.openai.com/v1/responses",
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.body) }}"),
      "options": {
        "timeout": 300000
      }
    },
    "credentials": {
      "httpHeaderAuth": {
        "id": "9OK91AZnXE70dKic",
        "name": "OpenAi - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "output": []
    }
  ]
});

const mont = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Montar pedido",
    "parameters": {
      "jsCode": "// Confere o roteiro, monta o pedido do worker e o spec do vídeo.\nconst p = $('Próxima pauta').first().json;\nconst cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;\nconst notes = typeof p.notes === 'string' ? JSON.parse(p.notes) : (p.notes || {});\nconst sport = $('Pedido do roteiro').first().json.sport;\nconst resp = $input.first().json;\nconst text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')\n  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');\nlet s;\ntry { s = JSON.parse(text); } catch (e) { throw new Error('Roteiro sem JSON válido: ' + text.slice(0, 200)); }\n\nconst clean = t => String(t || '').replace(/\\s+/g, ' ').trim();\nconst KINDS = ['score', 'stat', 'list', 'fact', 'quote'];\nconst beats = (s.beats || []).map(b => {\n  const v = b.visual || (b.visuals || [])[0] || {};\n  let visual;\n  if (v.type === 'card' && v.card && KINDS.includes(v.card.kind)) visual = { type: 'card', card: v.card };\n  else visual = { type: 'image', prompt: clean(v.prompt || 'dramatic stadium under lights, crowd, sports atmosphere') };\n  return { narration: clean(b.narration), visuals: [visual] };\n}).filter(b => b.narration);\nif (beats.length < 3) throw new Error('Roteiro com poucos trechos: ' + beats.length);\n\nconst words = beats.reduce((n, b) => n + b.narration.split(' ').length, 0);\nconst [minS, maxS] = cfg.format?.short_seconds || [40, 55];\nconst wpm = cfg.format?.words_per_minute || 175;\nif (words > Math.round((maxS + 15) * wpm / 60)) throw new Error(`Roteiro longo demais: ${words} palavras`);\nconst checks = [{ stage: 'script', name: 'words_in_range', passed: words >= minS * wpm / 60 * 0.85 && words <= maxS * wpm / 60 * 1.1,\n  detail: { words, min: Math.round(minS * wpm / 60), max: Math.round(maxS * wpm / 60) } }];\n\nconst LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };\nconst srcNames = [...new Set((notes.sources || []).map(x => x.source).filter(Boolean))];\nconst style = String(cfg.visual?.style_block || '').replace(/\\[STYLE\\]\\s*/i, '').replace(/,?\\s*9:16 vertical/i, ', square composition');\nconst neg = cfg.visual?.negative_prompt ? ` Avoid: ${cfg.visual.negative_prompt}.` : '';\nconst yt = cfg.youtube || {};\nconst headline = clean(s.headline || p.title).slice(0, 80);\nconst title = clean(s.title || p.title).replace(/#\\S+/g, '').slice(0, 95);\nconst hashtags = ['Shorts', LABEL[sport] || sport, ...(yt.hashtags || [])].map(h => '#' + String(h).replace(/\\s+/g, ''));\nconst description = [\n  clean(s.description),\n  '',\n  'Fontes:',\n  ...(notes.sources || []).slice(0, 4).map(x => `• ${x.source}: ${x.url}`),\n  '',\n  cfg.texts?.disclaimer || '',\n  '',\n  hashtags.join(' '),\n].join('\\n').slice(0, 4900);\nconst tags = [...new Set([...(s.tags || []), LABEL[sport], ...(yt.default_tags || [])].map(clean).filter(Boolean))].slice(0, 15);\n\nconst usage = resp.usage || {};\nconst P = { 'gpt-5.4-mini': { in: 0.75, out: 4.5 }, 'gpt-5.4-nano': { in: 0.2, out: 1.25 }, ...(cfg.prices || {}) };\nconst pr = P[String(resp.model || '').replace(/-\\d{4}-\\d{2}-\\d{2}$/, '')] || P['gpt-5.4-mini'];\nconst cost_usd = Math.round(((usage.input_tokens || 0) * pr.in + (usage.output_tokens || 0) * pr.out) / 1e6 * 10000) / 10000;\n\nconst spec = {\n  type: 'news_short', sport, topic_id: p.topic_id, story_key: notes.story_key,\n  headline, chosen_title: title, titles: [title],\n  publishing: { title, description, tags, category_id: yt.category_id || '17', language: 'pt-BR',\n    contains_synthetic_media: yt.contains_synthetic_media !== false, made_for_kids: false, kind: 'short' },\n  sources: notes.sources || [], beats, checks, usage: { script: { ...usage, model: resp.model }, cost_usd },\n};\nconst color = cfg.visual?.sport_colors?.[sport];\nconst job = {\n  sport, color, headline, channel_name: cfg.name,\n  sources_label: srcNames.length ? 'Fontes: ' + srcNames.join(' · ') : '',\n  voice: cfg.voice?.edge_voice || 'pt-BR-FranciscaNeural', rate: cfg.voice?.rate || '+10%',\n  image_style: style + neg, end_card: cfg.news?.end_card || [`Segue o ${cfg.name}`, 'notícia rápida todo dia'],\n  lufs: cfg.audio?.loudness_lufs || -14, beats, key_prefix: `videos/${p.video_id}`,\n};\nreturn [{ json: { video_id: p.video_id, spec, job } }];\n"
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "spec": {},
      "job": {}
    }
  ]
});

const st = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Status: render",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE videos SET status = 'assembling', spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid;",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, JSON.stringify($json.spec) ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      1440,
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const job = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Worker: Short",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/news_short"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Montar pedido').first().json.video_id, idempotency_key: $('Montar pedido').first().json.video_id + '-news-' + $execution.id, callback_url: $execution.resumeUrl, input: $('Montar pedido').first().json.job }) }}"),
      "options": {
        "timeout": 120000
      }
    },
    "credentials": {
      "httpHeaderAuth": {
        "id": "R96vQrkAjGn3GHEt",
        "name": "Auth - Fabrica Worker"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      1680,
      0
    ]
  },
  output: [
    {
      "job_id": "j",
      "status": "queued"
    }
  ]
});

const wait = node({
  type: "n8n-nodes-base.wait",
  version: 1.1,
  config: {
    "name": "Aguardar Short",
    "parameters": {
      "resume": "webhook",
      "httpMethod": "POST",
      "authentication": "headerAuth",
      "limitWaitTime": true,
      "limitType": "afterTimeInterval",
      "resumeAmount": 1,
      "resumeUnit": "hours",
      "options": {}
    },
    "credentials": {
      "httpHeaderAuth": {
        "id": "dBAcX42kLwL5n3eW",
        "name": "Auth - Fabrica Callback"
      }
    },
    "position": [
      1920,
      0
    ]
  },
  output: [
    {
      "body": {
        "status": "succeeded",
        "result": {}
      }
    }
  ]
});

const chk = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Checar vídeo",
    "parameters": {
      "jsCode": "// O worker chama a URL de retomada do Wait com o resultado do job.\nconst b = $input.first().json.body;\nif (!b) throw new Error('Short: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Short falhou no worker: ' + (b.error || 'sem detalhe'));\nreturn [{ json: b.result }];\n"
    },
    "position": [
      2160,
      0
    ]
  },
  output: [
    {
      "url": "s3://x",
      "cover_url": "s3://y",
      "spec_url": "s3://z",
      "duration_s": 45,
      "beats": [],
      "checks": []
    }
  ]
});

const prep = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Preparar gravação",
    "parameters": {
      "jsCode": "// Junta o resultado do worker ao spec e prepara a gravação.\nconst v = $('Montar pedido').first().json;\nconst r = $('Checar vídeo').first().json;\nconst spec = { ...v.spec,\n  beats: r.beats,\n  outputs: { final_url: r.url, cover_url: r.cover_url, spec_url: r.spec_url, duration_s: r.duration_s },\n  checks: (v.spec.checks || []).concat(r.checks || []) };\nconst assets = [\n  { k: 'final', u: r.url, meta: { duration_s: r.duration_s } },\n  { k: 'thumb', u: r.cover_url, meta: { cover: true } },\n  { k: 'spec', u: r.spec_url, meta: {} },\n];\nreturn [{ json: { video_id: v.video_id, spec: JSON.stringify(spec), checks: JSON.stringify(spec.checks), assets: JSON.stringify(assets), duration_s: r.duration_s } }];\n"
    },
    "position": [
      2400,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "spec": "{}",
      "checks": "[]",
      "assets": "[]",
      "duration_s": 45
    }
  ]
});

const save = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar Short",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH v AS (\n  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, duration_s = $5::numeric, updated_at = now()\n  WHERE id = $1::uuid RETURNING id\n), ck AS (\n  INSERT INTO checks (video_id, stage, name, passed, detail)\n  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)\n  FROM jsonb_array_elements($3::jsonb) c\n)\nINSERT INTO assets (video_id, kind, url, meta)\nSELECT $1::uuid, (a->>'k')::asset_kind, a->>'u', COALESCE(a->'meta', '{}'::jsonb)\nFROM jsonb_array_elements($4::jsonb) a WHERE a->>'u' IS NOT NULL;",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, $json.spec, $json.checks, $json.assets, $json.duration_s ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      2640,
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const links = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Links temporários",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/files/presign"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ urls: [ $('Checar vídeo').first().json.url, $('Checar vídeo').first().json.cover_url ], expires_s: 172800 }) }}"),
      "options": {
        "timeout": 120000
      }
    },
    "credentials": {
      "httpHeaderAuth": {
        "id": "R96vQrkAjGn3GHEt",
        "name": "Auth - Fabrica Worker"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      2880,
      0
    ]
  },
  output: [
    {
      "urls": []
    }
  ]
});

const msg = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Mensagem de aprovação",
    "parameters": {
      "jsCode": "// Mensagem de aprovação do Short (WhatsApp): texto + vídeo.\nconst v = $('Montar pedido').first().json;\nconst r = $('Checar vídeo').first().json;\nconst [videoLink, coverLink] = $('Links temporários').first().json.urls;\nconst cfg = (() => { const c = $('Próxima pauta').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();\nconst TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };\nconst code = String(v.video_id).slice(0, 4).toUpperCase();\nconst spec = v.spec;\nconst failed = (r.checks || []).concat(spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);\nconst src = (spec.sources || []).slice(0, 3).map(s => `${s.source}: ${s.url}`);\nconst lines = [\n  `📱 *Short pronto* · ${cfg.name} · código *#${code}*`,\n  `${TAG[spec.sport] || spec.sport} · *${spec.publishing.title}*`,\n  `Duração: ${Math.round(r.duration_s)}s${r.fallback_images ? ` · ⚠️ ${r.fallback_images} imagem(ns) trocada(s) por cartão` : ''}`,\n  failed.length ? `⚠️ Checagens com alerta:\\n${failed.join('\\n')}` : '✅ Checagens ok',\n  '',\n  `▶️ Vídeo: ${videoLink}`,\n  '',\n  '📰 Fontes:',\n  ...src,\n  '',\n  '*Responda:*',\n  `1 #${code} → publicar agora no YouTube`,\n  `2 #${code} motivo → descartar`,\n  '',\n  'Confira nomes e números com as fontes antes de aprovar. Link válido por 48 h.',\n];\nreturn [{ json: { number: cfg.approval?.to, text: lines.join('\\n'), video: videoLink, cover: coverLink, caption: `#${code} · ${spec.headline}` } }];\n"
    },
    "position": [
      3120,
      0
    ]
  },
  output: [
    {
      "number": "55",
      "text": "x",
      "video": "https://x",
      "cover": "https://y",
      "caption": "#ABCD"
    }
  ]
});

const wa = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: pedir aprovação",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-text",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $json.number }}"),
      "messageText": expr("{{ $json.text }}")
    },
    "credentials": {
      "evolutionApi": {
        "id": "570ZlMjp90Xd9ZZk",
        "name": "Evolution API"
      }
    },
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      3360,
      0
    ]
  },
  output: [
    {}
  ]
});

const wa_vid = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: vídeo",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-video",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $('Mensagem de aprovação').first().json.number }}"),
      "media": expr("{{ $('Mensagem de aprovação').first().json.video }}"),
      "caption": expr("{{ $('Mensagem de aprovação').first().json.caption }}")
    },
    "credentials": {
      "evolutionApi": {
        "id": "570ZlMjp90Xd9ZZk",
        "name": "Evolution API"
      }
    },
    "onError": "continueRegularOutput",
    "position": [
      3600,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-news-short", "factory.news-short")
  .add(t_cron)
  .to(config)
  .to(prox)
  .to(ped)
  .to(ai)
  .to(mont)
  .to(st)
  .to(job)
  .to(wait)
  .to(chk)
  .to(prep)
  .to(save)
  .to(links)
  .to(msg)
  .to(wa)
  .to(wa_vid)
  .add(t_manual)
  .to(config);
