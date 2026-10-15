import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const t_sub = trigger({
  type: "n8n-nodes-base.executeWorkflowTrigger",
  version: 1.2,
  config: {
    "name": "Vídeo aprovado",
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
      "query": "SELECT v.id AS video_id, c.config,\n  (SELECT a.url FROM assets a WHERE a.video_id = v.id AND a.kind = 'spec' ORDER BY a.created_at DESC LIMIT 1) AS spec_url\nFROM videos v JOIN channels c ON c.id = v.channel_id\nWHERE v.id = COALESCE(NULLIF($1::text, '')::uuid,\n  (SELECT id FROM videos WHERE status IN ('awaiting_approval', 'scheduled', 'published') ORDER BY created_at DESC LIMIT 1));",
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
      "config": {},
      "spec_url": "s3://x"
    }
  ]
});

const job = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Worker: clipes",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/clips"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $json.video_id, idempotency_key: $json.video_id + '-clips-' + $execution.id, callback_url: $execution.resumeUrl, input: { spec_url: $json.spec_url, config: $json.config } }) }}"),
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
      720,
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
    "name": "Aguardar clipes",
    "parameters": {
      "resume": "webhook",
      "httpMethod": "POST",
      "limitWaitTime": true,
      "limitType": "afterTimeInterval",
      "resumeAmount": 4,
      "resumeUnit": "hours",
      "options": {}
    },
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "body": {
        "status": "succeeded",
        "result": {
          "clips": []
        }
      }
    }
  ]
});

const chk = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Checar clipes",
    "parameters": {
      "jsCode": "// O worker chama a URL de retomada do Wait com o resultado do job.\nconst b = $input.first().json.body;\nif (!b) throw new Error('Clipes: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Clipes falhou no worker: ' + (b.error || 'sem detalhe'));\nreturn [{ json: b.result }];\n"
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {
      "clips": [
        {
          "n": 1,
          "url": "s3://x",
          "caption": "c",
          "title": "t",
          "duration_s": 60
        }
      ],
      "title": "t"
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
      "jsonBody": expr("{{ JSON.stringify({ urls: $json.clips.map(c => c.url), expires_s: 604800 }) }}"),
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
      1440,
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
    "name": "Salvar clipes",
    "parameters": {
      "operation": "executeQuery",
      "query": "INSERT INTO assets (video_id, kind, url, meta)\nSELECT $1::uuid, 'short', c->>'url', jsonb_build_object('platform', 'tiktok', 'n', c->'n', 'title', c->>'title', 'caption', c->>'caption')\nFROM jsonb_array_elements($2::jsonb) c;",
      "options": {
        "queryReplacement": expr("{{ [ $('Carregar vídeo').first().json.video_id, JSON.stringify($('Checar clipes').first().json.clips) ] }}")
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
      1680,
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const msgs = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Mensagens",
    "parameters": {
      "jsCode": "// Para cada clipe: uma mensagem com o link e outra só com a legenda (fácil de copiar no celular).\nconst r = $('Checar clipes').first().json;\nconst urls = $('Links temporários').first().json.urls;\nconst number = $('Carregar vídeo').first().json.config.approval.to;\nconst out = [{ json: { number, text: `🎵 *Clipes para TikTok/Reels* (${r.clips.length})\\n*${r.title}*\\n\\nCada clipe vem em 2 mensagens: o link do vídeo e a legenda para colar. Links válidos por 7 dias.\\nPostar 1 a 3 por dia; marque como conteúdo gerado por IA.` } }];\nr.clips.forEach((c, i) => {\n  out.push({ json: { number, text: `*${c.n}/${r.clips.length} · ${c.title}* (${Math.round(c.duration_s)}s)\\n${urls[i]}` } });\n  out.push({ json: { number, text: c.caption } });\n});\nreturn out;\n"
    },
    "position": [
      1920,
      0
    ]
  },
  output: [
    {
      "number": "55",
      "text": "x"
    }
  ]
});

const wa = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: enviar clipes",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-text",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $json.number }}"),
      "messageText": expr("{{ $json.text }}"),
      "options_message": {
        "delay": 1500
      }
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
      2160,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-clips", "factory.clips")
  .add(t_sub)
  .to(config)
  .to(load)
  .to(job)
  .to(wait)
  .to(chk)
  .to(links)
  .to(save)
  .to(msgs)
  .to(wa)
  .add(t_manual)
  .to(config);
