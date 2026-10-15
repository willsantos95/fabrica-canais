import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const t_sub = trigger({
  type: "n8n-nodes-base.executeWorkflowTrigger",
  version: 1.2,
  config: {
    "name": "Chamado pelo produce",
    "parameters": {
      "inputSource": "workflowInputs",
      "workflowInputs": {
        "values": [
          {
            "name": "video_id",
            "type": "string"
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
    {
      "video_id": "uuid"
    }
  ]
});

const t_manual = trigger({
  type: "n8n-nodes-base.manualTrigger",
  version: 1,
  config: {
    "name": "Testar com o último vídeo",
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

const load = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Carregar vídeo",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT v.id AS video_id, v.spec, c.config,\n  (SELECT a.url FROM assets a WHERE a.video_id = v.id AND a.kind = 'spec' ORDER BY a.created_at DESC LIMIT 1) AS spec_url\nFROM videos v JOIN channels c ON c.id = v.channel_id\nWHERE v.id = COALESCE(NULLIF($1::text, '')::uuid,\n  (SELECT id FROM videos WHERE status IN ('derivatives', 'awaiting_approval') ORDER BY created_at DESC LIMIT 1));",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id || '' ] }}")
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
      "spec": {},
      "config": {},
      "spec_url": "s3://x"
    }
  ]
});

const st = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Status: pacote",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE videos SET status = 'derivatives', updated_at = now() WHERE id = $1::uuid;",
      "options": {
        "queryReplacement": expr("{{ [ $('Carregar vídeo').first().json.video_id ] }}")
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
      720,
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
    "name": "Worker: pacote",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/package"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Carregar vídeo').first().json.video_id, idempotency_key: $('Carregar vídeo').first().json.video_id + '-package-' + $execution.id, callback_url: $execution.resumeUrl, input: { spec_url: $('Carregar vídeo').first().json.spec_url, config: $('Carregar vídeo').first().json.config } }) }}"),
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
      960,
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
    "name": "Aguardar pacote",
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
      1200,
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
    "name": "Checar pacote",
    "parameters": {
      "jsCode": "// O worker chama a URL de retomada do Wait com o resultado do job.\nconst b = $input.first().json.body;\nif (!b) throw new Error('Pacote: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Pacote falhou no worker: ' + (b.error || 'sem detalhe'));\nreturn [{ json: b.result }];\n"
    },
    "position": [
      1440,
      0
    ]
  },
  output: [
    {
      "spec": {},
      "shorts": [],
      "thumbnails": [],
      "outputs": {},
      "checks": []
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
      "jsonBody": expr("{{ JSON.stringify({ urls: [ $json.outputs.preview_url, $json.outputs.final_url, ...$json.thumbnails.map(t => t.url), ...$json.shorts.map(s => s.url) ], expires_s: 172800 }) }}"),
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
      "urls": []
    }
  ]
});

const save = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar pacote",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH v AS (\n  UPDATE videos SET status = 'awaiting_approval', spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid RETURNING id\n), ck AS (\n  INSERT INTO checks (video_id, stage, name, passed, detail)\n  SELECT $1::uuid, c->>'stage', c->>'name', (c->>'passed')::boolean, COALESCE(c->'detail', '{}'::jsonb)\n  FROM jsonb_array_elements($3::jsonb) c\n)\nINSERT INTO assets (video_id, kind, url, meta)\nSELECT $1::uuid, (a->>'k')::asset_kind, a->>'u', COALESCE(a->'meta', '{}'::jsonb)\nFROM jsonb_array_elements($4::jsonb) a;",
      "options": {
        "queryReplacement": expr("{{ (() => { const r = $('Checar pacote').first().json; const assets = [ ...r.thumbnails.map(t => ({ k: 'thumb', u: t.url, meta: { n: t.n, check: t.check } })), ...r.shorts.map(s => ({ k: 'short', u: s.url, meta: { n: s.n, start_s: s.start_s, end_s: s.end_s } })) ]; return [ $('Carregar vídeo').first().json.video_id, JSON.stringify(r.spec), JSON.stringify(r.checks || []), JSON.stringify(assets) ]; })() }}")
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
      1920,
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const msg = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Mensagem de aprovação",
    "parameters": {
      "jsCode": "const r = $('Checar pacote').first().json;\nconst urls = $('Links temporários').first().json.urls;\nconst [preview, final] = urls;\nconst nT = r.thumbnails.length;\nconst thumbLinks = urls.slice(2, 2 + nT);\nconst shortLinks = urls.slice(2 + nT);\nconst spec = r.spec;\nconst cfg = $('Carregar vídeo').first().json.config;\nconst code = String($('Carregar vídeo').first().json.video_id).slice(0, 4).toUpperCase();\nconst d = Math.round(r.outputs.duration_s || 0);\nconst dur = `${Math.floor(d / 60)}:${String(d % 60).padStart(2, '0')}`;\nconst failed = (spec.checks || []).filter(c => !c.passed).map(c => `• ${c.stage}/${c.name}`);\nconst titles = (spec.titles || []).slice(0, 5);\nconst current = spec.publishing?.title || spec.chosen_title;\nconst lines = [\n  `🎬 *Vídeo pronto para revisão* · ${cfg.name} · código *#${code}*`,\n  `*${current}*`,\n  `Duração: ${dur} · ${spec.blocks.length} blocos · ${(spec.sources || []).length} fontes`,\n  failed.length ? `⚠️ Checagens com alerta:\\n${failed.join('\\n')}` : '✅ Todas as checagens passaram',\n  '',\n  `▶️ Preview (480p): ${preview}`,\n  `⬇️ Vídeo final: ${final}`,\n  '',\n  '📱 *Shorts*',\n  ...r.shorts.map((s, i) => `${i + 1}. ${s.hook} (${Math.round(s.duration_s)}s): ${shortLinks[i]}`),\n  '',\n  '📝 *Títulos*',\n  ...titles.map((t, i) => `${i + 1}. ${t}${t === spec.chosen_title ? ' ✅' : ''}`),\n  '',\n  `🖼️ Thumbnails nas próximas mensagens (sugerida: ${spec.thumbnail?.chosen || 1})`,\n  '',\n  '*Responda:*',\n  '1 → aprovar e agendar no YouTube',\n  '2 motivo → rejeitar (ex.: 2 imagens fracas)',\n  '3 N → usar a thumbnail N',\n  '4 N → usar o título N',\n  `Com mais de um vídeo pendente, inclua o código: 1 #${code}`,\n  '',\n  'Links válidos por 48 h.',\n];\nreturn [{ json: {\n  number: cfg.approval.to,\n  text: lines.join('\\n'),\n  thumbs: r.thumbnails.map((t, i) => ({ n: t.n, url: thumbLinks[i], legible: t.check?.passed })),\n  chosen: spec.thumbnail?.chosen || 1,\n  code,\n} }];\n"
    },
    "position": [
      2160,
      0
    ]
  },
  output: [
    {
      "number": "55",
      "text": "x",
      "thumbs": [],
      "chosen": 1
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
      2400,
      0
    ]
  },
  output: [
    {}
  ]
});

const thumbs = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Uma mensagem por thumbnail",
    "parameters": {
      "jsCode": "const m = $('Mensagem de aprovação').first().json;\nreturn m.thumbs.map(t => ({ json: {\n  number: m.number,\n  media: t.url,\n  caption: `#${m.code} · Thumbnail ${t.n}${t.n === m.chosen ? ' (sugerida)' : ''}${t.legible === false ? ' · ⚠️ texto pequeno' : ''}`,\n} }));\n"
    },
    "position": [
      2640,
      0
    ]
  },
  output: [
    {
      "number": "55",
      "media": "https://x",
      "caption": "Thumbnail 1"
    }
  ]
});

const wa_img = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: thumbnails",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-image",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $json.number }}"),
      "media": expr("{{ $json.media }}"),
      "caption": expr("{{ $json.caption }}")
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
      2880,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-package", "factory.package")
  .add(t_sub)
  .to(config)
  .to(load)
  .to(st)
  .to(job)
  .to(wait)
  .to(chk)
  .to(links)
  .to(save)
  .to(msg)
  .to(wa)
  .to(thumbs)
  .to(wa_img)
  .add(t_manual)
  .to(config);
