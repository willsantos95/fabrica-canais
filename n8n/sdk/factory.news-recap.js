import { workflow, node, trigger, switchCase, ifElse, expr } from '@n8n/workflow-sdk';

const t_cron = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.2,
  config: {
    "name": "Às 22h, 22h30, 23h e 23h30",
    "parameters": {
      "rule": {
        "interval": [
          {
            "field": "cronExpression",
            "expression": "0,30 22-23 * * *"
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
    "name": "Testar (ignora prévia)",
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
            "value": expr("{{ $execution.mode !== 'trigger' }}"),
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
    "name": "Próximo resumo",
    "parameters": {
      "operation": "executeQuery",
      "query": "-- um esporte por execução: o que tiver mais Shorts aprovados hoje e ainda não tiver resumo\nWITH ch AS (\n  SELECT c.id, c.config FROM channels c\n  WHERE c.config->'format'->>'type' = 'news_short'\n    AND ($1::boolean OR (c.active AND COALESCE((c.config->'news'->>'preview')::boolean, true) = false))\n  LIMIT 1\n), d AS (\n  SELECT date_trunc('day', now() AT TIME ZONE 'America/Sao_Paulo') AT TIME ZONE 'America/Sao_Paulo' AS d0\n), cand AS (\n  SELECT v.spec->>'sport' AS sport,\n    json_agg(json_build_object('video_id', v.id, 'headline', v.spec->>'headline', 'title', v.spec->'publishing'->>'title',\n      'beats', v.spec->'beats', 'sources', v.spec->'sources') ORDER BY v.created_at) AS stories\n  FROM videos v, ch, d\n  WHERE v.channel_id = ch.id AND v.spec->>'type' = 'news_short' AND v.status IN ('scheduled', 'published')\n    AND v.created_at >= d.d0\n    AND NOT EXISTS (SELECT 1 FROM videos r WHERE r.channel_id = ch.id AND r.spec->>'type' = 'news_recap'\n                    AND r.spec->>'sport' = v.spec->>'sport' AND r.created_at >= d.d0 AND r.status <> 'failed')\n  GROUP BY 1\n  HAVING count(*) >= COALESCE(((SELECT config FROM ch)->'recap'->>'min_stories')::int, 3)\n  ORDER BY count(*) DESC LIMIT 1\n), v AS (\n  INSERT INTO videos (channel_id, status, spec)\n  SELECT ch.id, 'scripting', jsonb_build_object('type', 'news_recap', 'sport', cand.sport) FROM ch, cand\n  RETURNING id\n)\nSELECT v.id AS video_id, cand.sport, cand.stories, ch.config FROM v, cand, ch;",
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
      "sport": "nba",
      "stories": [],
      "config": {}
    }
  ]
});

const ped = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Pedido do resumo",
    "parameters": {
      "jsCode": "// Pedido do roteiro do resumo diário de um esporte, a partir dos Shorts aprovados hoje.\nconst p = $('Próximo resumo').first().json;\nconst cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;\nconst all = typeof p.stories === 'string' ? JSON.parse(p.stories) : p.stories;\nconst max = cfg.recap?.max_stories || 8;\nconst stories = all.slice(-max);\nconst LABEL = { futebol: 'futebol', nba: 'NBA', nfl: 'NFL' }[p.sport] || p.sport;\nconst today = DateTime.now().setZone(cfg.schedule?.timezone || 'America/Sao_Paulo').toFormat('dd/MM');\n\nconst SYSTEM = `Você é o roteirista do canal \"${cfg.name}\" (${cfg.handle || ''}), em português do Brasil.\nTom: ${cfg.tone}\n\nEscreva o roteiro do RESUMO DO DIA de ${LABEL} (${today}), um vídeo horizontal de 3 a 6 minutos com as notícias abaixo, nesta ordem ou na ordem que fizer mais sentido (mais importante primeiro).\nRegras:\n- Use SÓ os fatos que estão nas notícias recebidas (as narrações já foram conferidas). Não acrescente números, nomes ou resultados.\n- Só ${LABEL}. Nada de outros esportes.\n- Abertura: até 35 palavras, chamando as 2 ou 3 notícias mais fortes.\n- Cada notícia: 60 a 95 palavras, reescrita com começo forte, contexto e por que importa; transição natural para a próxima.\n- Fechamento: até 30 palavras, com uma pergunta para os comentários. Não peça inscrição.\n- chapter: título curto do capítulo (até 40 caracteres). kicker: linha curta acima da manchete (placar, número ou contexto, até 40 caracteres).\n\nResponda só com JSON:\n{\"title\":\"título do YouTube até 90 caracteres\",\"description\":\"2 a 4 frases\",\"tags\":[\"até 10\"],\"thumbnail_lines\":[\"linha 1 até 16 caracteres\",\"linha 2 até 16 caracteres\"],\n \"intro\":{\"narration\":\"...\"},\"stories\":[{\"video_id\":\"...\",\"chapter\":\"...\",\"kicker\":\"...\",\"narration\":\"...\"}],\"outro\":{\"narration\":\"...\"}}`;\n\nconst input = `Escreva o roteiro e responda em JSON.\\n\\nNotícias de hoje:\\n` + stories.map(s => JSON.stringify({\n  video_id: s.video_id, manchete: s.headline, titulo: s.title,\n  narracao_do_short: (s.beats || []).map(b => b.narration).join(' '),\n  fontes: (s.sources || []).map(x => x.source).filter(Boolean),\n})).join('\\n');\n\nreturn [{ json: { today, label: LABEL, stories, body: {\n  model: cfg.recap?.script_model || cfg.news?.script_model || 'gpt-5.4-mini',\n  instructions: SYSTEM, input,\n  reasoning: { effort: 'low' },\n  text: { format: { type: 'json_object' } },\n  max_output_tokens: 8000,\n} } }];\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "today": "16/10",
      "label": "NBA",
      "stories": [],
      "body": {}
    }
  ]
});

const ai = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "OpenAI: resumo",
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
    "name": "Montar resumo",
    "parameters": {
      "jsCode": "// Confere o roteiro do resumo e monta o pedido do worker (reaproveita as cenas dos Shorts).\nconst p = $('Próximo resumo').first().json;\nconst cfg = typeof p.config === 'string' ? JSON.parse(p.config) : p.config;\nconst ped = $('Pedido do resumo').first().json;\nconst resp = $input.first().json;\nconst text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')\n  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');\nlet s;\ntry { s = JSON.parse(text); } catch (e) { throw new Error('Roteiro do resumo sem JSON válido: ' + text.slice(0, 200)); }\nconst clean = t => String(t || '').replace(/\\s+/g, ' ').trim();\nconst byId = Object.fromEntries(ped.stories.map(x => [x.video_id, x]));\nconst stories = (s.stories || []).filter(x => byId[x.video_id] && clean(x.narration));\nif (stories.length < 2) throw new Error('Resumo com poucas notícias válidas: ' + stories.length);\n\nconst LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' }[p.sport] || p.sport;\nconst scenesOf = st => (st.beats || []).flatMap(b => (b.scenes || []).map(x => ({ url: x.url }))).filter(x => x.url);\nconst segments = [\n  { headline: `Resumo ${LABEL} · ${ped.today}`, chapter: 'Abertura', narration: clean(s.intro?.narration),\n    visuals: [{ type: 'card', card: { kind: 'list', title: `${LABEL} hoje`, items: stories.slice(0, 4).map(x => clean(x.chapter).slice(0, 40)) } }] },\n  ...stories.map(x => ({ story: true, headline: byId[x.video_id].headline, kicker: clean(x.kicker).slice(0, 50),\n    chapter: clean(x.chapter).slice(0, 60), narration: clean(x.narration), visuals: scenesOf(byId[x.video_id]), video_id: x.video_id })),\n  { headline: 'Até amanhã', chapter: 'Fechamento', narration: clean(s.outro?.narration),\n    visuals: [{ type: 'card', card: { kind: 'fact', title: cfg.name, text: `Resumo de ${LABEL} todo dia no ${cfg.name}` } }] },\n].filter(x => x.narration);\n\nconst yt = cfg.youtube || {};\nconst title = clean(s.title || `Resumo ${LABEL} ${ped.today}`).replace(/#\\S+/g, '').slice(0, 95);\nconst usage = resp.usage || {};\nconst spec = {\n  type: 'news_recap', sport: p.sport, date: ped.today, headline: title, chosen_title: title, titles: [title],\n  stories: stories.map(x => x.video_id),\n  publishing: { title, description_base: clean(s.description), tags: [...new Set([...(s.tags || []), LABEL, ...(yt.default_tags || [])].map(clean).filter(Boolean))].slice(0, 15),\n    category_id: yt.category_id || '17', language: 'pt-BR', contains_synthetic_media: yt.contains_synthetic_media !== false, made_for_kids: false, kind: 'long' },\n  sources: stories.flatMap(x => (byId[x.video_id].sources || []).slice(0, 2)),\n  segments: segments.map(({ visuals, ...rest }) => rest),\n  usage: { script: { ...usage, model: resp.model } },\n};\nconst job = {\n  sport: p.sport, color: cfg.visual?.sport_colors?.[p.sport], title: `${LABEL} HOJE`, channel_name: cfg.name,\n  voice: cfg.voice?.edge_voice || 'pt-BR-FranciscaNeural', rate: cfg.recap?.rate || '+5%',\n  end_card: [`Inscreva-se no ${cfg.name}`], thumbnail_lines: (s.thumbnail_lines || [`${LABEL} HOJE`, ped.today]).slice(0, 2).map(clean),\n  lufs: cfg.audio?.loudness_lufs || -14, min_duration_s: 60, segments, key_prefix: `videos/${p.video_id}`,\n};\nreturn [{ json: { video_id: p.video_id, spec, job } }];\n"
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
    "name": "Worker: resumo",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/news_recap"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Montar resumo').first().json.video_id, idempotency_key: $('Montar resumo').first().json.video_id + '-recap-' + $execution.id, callback_url: $execution.resumeUrl, input: $('Montar resumo').first().json.job }) }}"),
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
    "name": "Aguardar resumo",
    "parameters": {
      "resume": "webhook",
      "httpMethod": "POST",
      "authentication": "headerAuth",
      "limitWaitTime": true,
      "limitType": "afterTimeInterval",
      "resumeAmount": 2,
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
    "name": "Checar resumo",
    "parameters": {
      "jsCode": "// O worker chama a URL de retomada do Wait com o resultado do job.\nconst b = $input.first().json.body;\nif (!b) throw new Error('Resumo: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Resumo falhou no worker: ' + (b.error || 'sem detalhe'));\nreturn [{ json: b.result }];\n"
    },
    "position": [
      2160,
      0
    ]
  },
  output: [
    {
      "url": "s3://x",
      "srt_url": "s3://y",
      "thumbnails": [],
      "chapters": [],
      "duration_s": 200,
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
      "jsCode": "// Descrição com capítulos e fontes; thumbnail; assets.\nconst v = $('Montar resumo').first().json;\nconst r = $('Checar resumo').first().json;\nconst cfg = (() => { const c = $('Próximo resumo').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();\nconst LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' }[v.spec.sport] || v.spec.sport;\nconst mmss = t => `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, '0')}`;\nconst chapters = (r.chapters || []).map((c, i) => `${mmss(i === 0 ? 0 : c.t)} ${c.title}`);\nconst seen = new Set();\nconst sources = v.spec.sources.filter(x => x.url && !seen.has(x.url) && seen.add(x.url)).slice(0, 10).map(x => `• ${x.source}: ${x.url}`);\nconst hashtags = [LABEL, ...(cfg.youtube?.hashtags || [])].map(h => '#' + String(h).replace(/\\s+/g, ''));\nconst description = [v.spec.publishing.description_base, '', 'Capítulos:', ...chapters, '', 'Fontes:', ...sources, '',\n  cfg.texts?.disclaimer || '', '', hashtags.join(' ')].join('\\n').slice(0, 4900);\nconst spec = { ...v.spec,\n  publishing: { ...v.spec.publishing, description },\n  chapters: r.chapters,\n  thumbnail: { options: (r.thumbnails || []).map((t, i) => ({ n: i + 1, url: t.url, lines: t.lines, check: t.check })), chosen: 1 },\n  outputs: { final_url: r.url, srt_url: r.srt_url, duration_s: r.duration_s },\n  checks: r.checks || [] };\nconst assets = [{ k: 'final', u: r.url, meta: { duration_s: r.duration_s } }, { k: 'srt', u: r.srt_url, meta: {} },\n  ...(r.thumbnails || []).map((t, i) => ({ k: 'thumb', u: t.url, meta: { n: i + 1, check: t.check } }))];\nreturn [{ json: { video_id: v.video_id, spec, spec_s: JSON.stringify(spec), checks: JSON.stringify(spec.checks), assets: JSON.stringify(assets), duration_s: r.duration_s } }];\n"
    },
    "position": [
      2400,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "spec": {},
      "spec_s": "{}",
      "checks": "[]",
      "assets": "[]",
      "duration_s": 200
    }
  ]
});

const save = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar resumo",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH v AS (\n  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, duration_s = $5::numeric, updated_at = now()\n  WHERE id = $1::uuid RETURNING id\n), ck AS (\n  INSERT INTO checks (video_id, stage, name, passed, detail)\n  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)\n  FROM jsonb_array_elements($3::jsonb) c\n)\nINSERT INTO assets (video_id, kind, url, meta)\nSELECT $1::uuid, (a->>'k')::asset_kind, a->>'u', COALESCE(a->'meta', '{}'::jsonb)\nFROM jsonb_array_elements($4::jsonb) a WHERE a->>'u' IS NOT NULL;",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, $json.spec_s, $json.checks, $json.assets, $json.duration_s ] }}")
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
    "name": "Links do resumo",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/files/presign"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ urls: [ $('Checar resumo').first().json.url, ...($('Checar resumo').first().json.thumbnails || []).slice(0, 1).map(t => t.url) ], expires_s: 172800 }) }}"),
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
      "jsCode": "const s = $('Preparar gravação').first().json;\nconst spec = s.spec;\nconst [videoLink, thumbLink] = $('Links do resumo').first().json.urls;\nconst cfg = (() => { const c = $('Próximo resumo').first().json.config; return typeof c === 'string' ? JSON.parse(c) : c; })();\nconst TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };\nconst code = String(s.video_id).slice(0, 4).toUpperCase();\nconst d = Math.round(s.duration_s || 0);\nconst failed = (spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);\nconst lines = [\n  `🎬 *Resumo do dia pronto* · ${cfg.name} · código *#${code}*`,\n  `${TAG[spec.sport] || spec.sport} · *${spec.publishing.title}*`,\n  `Duração: ${Math.floor(d / 60)}:${String(d % 60).padStart(2, '0')} · ${spec.stories.length} notícias`,\n  failed.length ? `⚠️ Checagens com alerta:\\n${failed.join('\\n')}` : '✅ Checagens ok',\n  '',\n  `▶️ Vídeo: ${videoLink}`,\n  '',\n  '📑 Capítulos:',\n  ...(spec.chapters || []).map(c => `• ${c.title}`),\n  '',\n  '*Responda:*',\n  `1 #${code} → publicar agora no YouTube`,\n  `2 #${code} motivo → descartar`,\n  '',\n  'Link válido por 48 h.',\n];\nreturn [{ json: { number: cfg.approval?.to, text: lines.join('\\n'), thumb: thumbLink || null, caption: `#${code} · Thumbnail` } }];\n"
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
      "thumb": "https://y",
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

const wa_img = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: thumbnail",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-image",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $('Mensagem de aprovação').first().json.number }}"),
      "media": expr("{{ $('Mensagem de aprovação').first().json.thumb }}"),
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

export default workflow("factory-news-recap", "factory.news-recap")
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
  .to(wa_img)
  .add(t_manual)
  .to(config);
