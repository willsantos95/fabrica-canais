import { workflow, node, trigger, switchCase, ifElse, expr } from '@n8n/workflow-sdk';

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
      0
    ]
  },
  output: [
    {
      "video_id": "uuid"
    }
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
    "name": "Carregar e travar",
    "parameters": {
      "operation": "executeQuery",
      "query": "-- muda para scheduled só se ainda estiver aguardando: um segundo \"1\" não publica duas vezes\nWITH v AS (\n  UPDATE videos SET status = 'scheduled', updated_at = now()\n  WHERE id = $1::uuid AND status = 'awaiting_approval'\n  RETURNING id, channel_id, topic_id, spec\n)\nSELECT v.id AS video_id, v.topic_id, v.spec, c.config FROM v JOIN channels c ON c.id = v.channel_id;",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id ] }}")
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
      "spec": {},
      "config": {}
    }
  ]
});

const plan = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Plano de publicação",
    "parameters": {
      "jsCode": "// Publicação do canal de notícias: público na hora (Short) ou no próximo horário (resumo, se configurado).\nconst r = $input.first().json;\nconst spec = typeof r.spec === 'string' ? JSON.parse(r.spec) : r.spec;\nconst cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;\nconst pub = spec.publishing || {};\nconst kind = spec.type === 'news_recap' ? 'long' : 'short';\nconst tz = cfg.schedule?.timezone || 'America/Sao_Paulo';\nconst status = { privacyStatus: 'public', selfDeclaredMadeForKids: !!pub.made_for_kids,\n  containsSyntheticMedia: pub.contains_synthetic_media !== false };\nconst body = {\n  snippet: { title: String(pub.title || spec.chosen_title).slice(0, 100), description: pub.description || '',\n    tags: pub.tags || [], categoryId: pub.category_id || '17', defaultLanguage: 'pt-BR', defaultAudioLanguage: 'pt-BR' },\n  status,\n};\nconst thumbs = spec.thumbnail?.options || [];\nconst thumb = thumbs.find(t => t.n === spec.thumbnail?.chosen) || thumbs[0];\nreturn [{ json: {\n  video_id: r.video_id, topic_id: r.topic_id, kind, sport: spec.sport, title: body.snippet.title, body,\n  final_url: spec.outputs?.final_url, thumb_url: kind === 'long' ? (thumb?.url || null) : null,\n  playlist_id: cfg.youtube?.playlists?.[spec.sport] || null,\n  number: cfg.approval?.to, tz, channel: cfg.name,\n} }];\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "topic_id": "t",
      "kind": "short",
      "sport": "nba",
      "title": "t",
      "body": {},
      "final_url": "s3://x",
      "thumb_url": null,
      "playlist_id": "PL",
      "number": "55",
      "channel": "c"
    }
  ]
});

const sess = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: sessão do vídeo",
    "parameters": {
      "method": "POST",
      "url": "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "youTubeOAuth2Api",
      "sendHeaders": true,
      "headerParameters": {
        "parameters": [
          {
            "name": "X-Upload-Content-Type",
            "value": "video/mp4"
          }
        ]
      },
      "options": {
        "timeout": 60000,
        "response": {
          "response": {
            "fullResponse": true,
            "responseFormat": "text"
          }
        }
      },
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.body) }}")
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
      "headers": {
        "location": "https://upload"
      },
      "statusCode": 200
    }
  ]
});

const up = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Worker: enviar vídeo",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/youtube_upload"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-' + $execution.id, callback_url: $execution.resumeUrl, input: { uploads: [ { ref: 'video', upload_url: $json.headers.location, media_url: $('Plano de publicação').first().json.final_url, content_type: 'video/mp4' } ] } }) }}"),
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
      1200,
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

const w = node({
  type: "n8n-nodes-base.wait",
  version: 1.1,
  config: {
    "name": "Aguardar envio",
    "parameters": {
      "resume": "webhook",
      "httpMethod": "POST",
      "limitWaitTime": true,
      "limitType": "afterTimeInterval",
      "resumeAmount": 3,
      "resumeUnit": "hours",
      "options": {}
    },
    "position": [
      1440,
      0
    ]
  },
  output: [
    {
      "body": {
        "status": "succeeded",
        "result": {
          "uploads": [
            {
              "ref": "video",
              "id": "abc",
              "ok": true
            }
          ]
        }
      }
    }
  ]
});

const c = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Checar envio",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nconst b = $input.first().json.body;\nif (!b) throw new Error('Envio ao YouTube: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Envio ao YouTube falhou: ' + (b.error || 'sem detalhe'));\nconst byRef = Object.fromEntries((b.result.uploads || []).map(u => [u.ref, u]));\nconst up = byRef.video || {};\nif (!up.id) throw new Error('O YouTube não aceitou o vídeo: ' + (up.error || 'sem id na resposta'));\nreturn [{ json: { youtube_id: up.id, url: p.kind === 'short' ? `https://youtube.com/shorts/${up.id}` : `https://youtu.be/${up.id}` } }];\n"
    },
    "position": [
      1680,
      0
    ]
  },
  output: [
    {
      "youtube_id": "abc",
      "url": "https://youtube.com/shorts/abc"
    }
  ]
});

const save = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Registrar publicação",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH v AS (\n  UPDATE videos SET status = 'published', updated_at = now(),\n    spec = jsonb_set(COALESCE(spec, '{}'::jsonb), '{publishing,youtube_id}', to_jsonb($2::text))\n  WHERE id = $1::uuid\n), t AS (\n  UPDATE topics SET status = 'done' WHERE id = NULLIF($4, '')::uuid\n)\nINSERT INTO publications (video_id, platform, external_id, kind, publish_at, status)\nVALUES ($1::uuid, 'youtube', $2, $3::publication_kind, now(), 'published');",
      "options": {
        "queryReplacement": expr("{{ [ $('Plano de publicação').first().json.video_id, $json.youtube_id, $('Plano de publicação').first().json.kind, $('Plano de publicação').first().json.topic_id || '' ] }}")
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
    "name": "Mensagem",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nconst r = $('Checar envio').first().json;\nconst LABEL = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };\nconst lines = [\n  `✅ *Publicado* · ${p.channel}`,\n  `*${p.title}*`,\n  r.url,\n  p.playlist_id ? `Playlist: ${LABEL[p.sport] || p.sport}` : `⚠️ Sem playlist de ${LABEL[p.sport] || p.sport} (rode \"Criar playlists\" no factory.publish do canal).`,\n];\nreturn [{ json: { number: p.number, text: lines.join('\\n') } }];\n"
    },
    "position": [
      2160,
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
    "name": "WhatsApp: avisar",
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

const pl = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Playlist do esporte",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nif (!p.playlist_id) return [];\nreturn [{ json: { body: { snippet: { playlistId: p.playlist_id, resourceId: { kind: 'youtube#video', videoId: $('Checar envio').first().json.youtube_id } } } } }];\n"
    },
    "position": [
      2160,
      200
    ]
  },
  output: [
    {
      "body": {}
    }
  ]
});

const pl_add = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: pôr na playlist",
    "parameters": {
      "method": "POST",
      "url": "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "youTubeOAuth2Api",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.body) }}"),
      "options": {}
    },
    "onError": "continueRegularOutput",
    "retryOnFail": true,
    "maxTries": 3,
    "waitBetweenTries": 5000,
    "position": [
      2400,
      200
    ]
  },
  output: [
    {}
  ]
});

const th = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Tem thumbnail?",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nreturn p.thumb_url ? [{ json: { youtube_id: $('Checar envio').first().json.youtube_id, thumb_url: p.thumb_url } }] : [];\n"
    },
    "position": [
      2160,
      400
    ]
  },
  output: [
    {
      "youtube_id": "abc",
      "thumb_url": "s3://x"
    }
  ]
});

const th_s = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: sessão da thumbnail",
    "parameters": {
      "method": "POST",
      "url": expr("https://www.googleapis.com/upload/youtube/v3/thumbnails/set?uploadType=resumable&videoId={{ $json.youtube_id }}"),
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "youTubeOAuth2Api",
      "sendHeaders": true,
      "headerParameters": {
        "parameters": [
          {
            "name": "X-Upload-Content-Type",
            "value": "image/jpeg"
          }
        ]
      },
      "options": {
        "timeout": 60000,
        "response": {
          "response": {
            "fullResponse": true,
            "responseFormat": "text"
          }
        }
      }
    },
    "onError": "continueRegularOutput",
    "position": [
      2400,
      400
    ]
  },
  output: [
    {
      "headers": {
        "location": "https://upload"
      }
    }
  ]
});

const th_up = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Worker: enviar thumbnail",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/youtube_upload"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-thumb-' + $execution.id, input: { uploads: [ { ref: 'thumb', upload_url: $json.headers.location, media_url: $('Tem thumbnail?').first().json.thumb_url, content_type: 'image/jpeg' } ] } }) }}"),
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
    "onError": "continueRegularOutput",
    "position": [
      2640,
      400
    ]
  },
  output: [
    {}
  ]
});

const t_pl = trigger({
  type: "n8n-nodes-base.manualTrigger",
  version: 1,
  config: {
    "name": "Criar playlists",
    "parameters": {},
    "position": [
      0,
      700
    ]
  },
  output: [
    {}
  ]
});

const ch = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Canal",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT id, name, config FROM channels WHERE slug = $1;",
      "options": {
        "queryReplacement": expr("{{ [ 'lance-rapido' ] }}")
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
      240,
      700
    ]
  },
  output: [
    {
      "id": "c",
      "name": "Lance Rápido",
      "config": {}
    }
  ]
});

const falta = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Playlists que faltam",
    "parameters": {
      "jsCode": "const r = $input.first().json;\nconst cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;\nconst have = cfg.youtube?.playlists || {};\nconst NAMES = { futebol: 'Futebol', nba: 'NBA', nfl: 'NFL' };\nconst desc = { futebol: 'Notícias de futebol em 1 minuto', nba: 'Notícias da NBA em 1 minuto', nfl: 'Notícias da NFL em 1 minuto' };\nreturn Object.keys(NAMES).filter(s => !have[s]).map(s => ({ json: { sport: s, body: {\n  snippet: { title: `${NAMES[s]} · ${r.name}`, description: `${desc[s]}. Shorts e resumos do dia do ${r.name}.`, defaultLanguage: 'pt-BR' },\n  status: { privacyStatus: 'public' } } } }));\n"
    },
    "position": [
      480,
      700
    ]
  },
  output: [
    {
      "sport": "nba",
      "body": {}
    }
  ]
});

const cria = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: criar playlist",
    "parameters": {
      "method": "POST",
      "url": "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status",
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "youTubeOAuth2Api",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.body) }}"),
      "options": {}
    },
    "position": [
      720,
      700
    ]
  },
  output: [
    {
      "id": "PL"
    }
  ]
});

const junta = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Juntar ids",
    "parameters": {
      "jsCode": "const sports = $('Playlists que faltam').all().map(i => i.json.sport);\nconst ids = $input.all().map(i => i.json.id);\nreturn [{ json: { playlists: JSON.stringify(Object.fromEntries(sports.map((s, i) => [s, ids[i]]).filter(x => x[1]))) } }];\n"
    },
    "position": [
      960,
      700
    ]
  },
  output: [
    {
      "playlists": "{}"
    }
  ]
});

const grava = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Gravar na config",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE channels SET config = jsonb_set(config, '{youtube,playlists}',\n  COALESCE(config->'youtube'->'playlists', '{}'::jsonb) || $2::jsonb), updated_at = now()\nWHERE slug = $1\nRETURNING config->'youtube'->'playlists' AS playlists;",
      "options": {
        "queryReplacement": expr("{{ [ 'lance-rapido', $json.playlists ] }}")
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
      1200,
      700
    ]
  },
  output: [
    {
      "playlists": {}
    }
  ]
});

export default workflow("factory-publish-lance", "factory.publish \u00b7 Lance R\u00e1pido")
  .add(t_sub)
  .to(config)
  .to(load)
  .to(plan)
  .to(sess)
  .to(up)
  .to(w)
  .to(c)
  .to(save)
  .to(msg)
  .to(wa)
  .add(save)
  .to(pl)
  .to(pl_add)
  .add(save)
  .to(th)
  .to(th_s)
  .to(th_up)
  .add(t_pl)
  .to(ch)
  .to(falta)
  .to(cria)
  .to(junta)
  .to(grava);
