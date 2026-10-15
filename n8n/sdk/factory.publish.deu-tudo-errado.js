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
          },
          {
            "id": "c-lead",
            "name": "lead_hours",
            "value": 3,
            "type": "number"
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
      "query": "-- muda para scheduled só se ainda estiver aguardando: um segundo \"1\" não publica duas vezes\nWITH v AS (\n  UPDATE videos SET status = 'scheduled', updated_at = now()\n  WHERE id = $1::uuid AND status = 'awaiting_approval'\n  RETURNING id, channel_id, spec\n)\nSELECT v.id AS video_id, v.spec, c.config, c.id AS channel_id,\n  COALESCE((SELECT json_agg(p.publish_at) FROM publications p JOIN videos v2 ON v2.id = p.video_id\n            WHERE v2.channel_id = c.id AND p.kind = 'long' AND p.publish_at > now()), '[]'::json) AS taken\nFROM v JOIN channels c ON c.id = v.channel_id;",
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
      "spec": {},
      "config": {},
      "taken": []
    }
  ]
});

const plan = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Plano de publicação",
    "parameters": {
      "jsCode": "const r = $input.first().json;\nconst spec = typeof r.spec === 'string' ? JSON.parse(r.spec) : r.spec;\nconst cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;\nconst pub = spec.publishing || {};\nconst tz = cfg.schedule?.timezone || 'America/Sao_Paulo';\nconst times = [...(cfg.schedule?.publish_times?.length ? cfg.schedule.publish_times : ['18:00'])].sort();\nconst shortsTime = cfg.schedule?.shorts_time || '12:00';\nconst fmt = dt => dt.toUTC().toFormat(\"yyyy-MM-dd'T'HH:mm\");\nconst taken = new Set((r.taken || []).map(t => fmt(DateTime.fromISO(String(t).replace(' ', 'T')))));\nconst earliest = DateTime.now().setZone(tz).plus({ hours: Number($('Config').first().json.lead_hours) || 3 });\n\n// próximo horário livre de publish_times, a partir de agora + folga\nlet slot = null;\nfor (let d = 0; d < 60 && !slot; d++) {\n  for (const t of times) {\n    const [h, mi] = t.split(':').map(Number);\n    const c = earliest.startOf('day').plus({ days: d }).set({ hour: h, minute: mi });\n    if (c > earliest && !taken.has(fmt(c))) { slot = c; break; }\n  }\n}\nif (!slot) throw new Error('Nenhum horário livre nos próximos 60 dias');\n\nconst [sh, sm] = shortsTime.split(':').map(Number);\nconst iso = dt => dt.toUTC().toISO({ suppressMilliseconds: true });\nconst status = (at) => ({\n  privacyStatus: 'private',\n  publishAt: iso(at),\n  selfDeclaredMadeForKids: !!pub.made_for_kids,\n  containsSyntheticMedia: !!pub.contains_synthetic_media,\n});\nconst snippet = (title, description) => ({\n  title, description, tags: pub.tags || [], categoryId: pub.category_id || '27',\n  defaultLanguage: pub.language || 'en', defaultAudioLanguage: pub.language || 'en',\n});\nconst thumbs = spec.thumbnail?.options || [];\nconst thumb = thumbs.find(t => t.n === spec.thumbnail?.chosen) || thumbs[0];\nconst shorts = (spec.shorts_candidates || []).map((s, i) => {\n  const at = slot.plus({ days: i + 1 }).set({ hour: sh, minute: sm });\n  return { n: s.n, url: s.url, publish_at: iso(at), title: s.title, description: s.description, status: status(at) };\n});\nreturn [{ json: {\n  video_id: r.video_id,\n  title: pub.title || spec.chosen_title,\n  publish_at: iso(slot),\n  publish_local: slot.toFormat('dd/MM HH:mm'),\n  final_url: spec.outputs.final_url,\n  thumb_url: thumb?.url || null,\n  long_body: { snippet: snippet((pub.title || spec.chosen_title).slice(0, 100), pub.description || ''), status: status(slot) },\n  shorts,\n  snippet_base: snippet('', ''),\n  number: cfg.approval?.to,\n  tz,\n} }];\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "video_id": "v",
      "title": "t",
      "publish_at": "2026-10-16T21:00:00Z",
      "publish_local": "16/10 18:00",
      "final_url": "s3://x",
      "thumb_url": "s3://y",
      "long_body": {},
      "shorts": [],
      "snippet_base": {},
      "number": "55",
      "tz": "America/Sao_Paulo"
    }
  ]
});

const s_long = node({
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
      "jsonBody": expr("{{ JSON.stringify($json.long_body) }}")
    },
    "credentials": {
      "youTubeOAuth2Api": {
        "id": "pnIjvYU4Eixl66cj",
        "name": "YouTube - Deu Tudo Errado TV"
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
      "headers": {
        "location": "https://upload"
      },
      "statusCode": 200
    }
  ]
});

const up_long = node({
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
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-long-' + $execution.id, callback_url: $execution.resumeUrl, input: { uploads: [ { ref: 'long', upload_url: $json.headers.location, media_url: $('Plano de publicação').first().json.final_url, content_type: 'video/mp4' } ] } }) }}"),
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

const w_long = node({
  type: "n8n-nodes-base.wait",
  version: 1.1,
  config: {
    "name": "Aguardar envio do vídeo",
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
              "ref": "long",
              "id": "abc"
            }
          ]
        }
      }
    }
  ]
});

const c_long = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Checar envio do vídeo",
    "parameters": {
      "jsCode": "const b = $input.first().json.body;\nif (!b) throw new Error('Envio do vídeo: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Envio do vídeo ao YouTube falhou: ' + (b.error || 'sem detalhe'));\nconst up = b.result.uploads[0] || {};\nif (!up.id) throw new Error('O YouTube não aceitou o vídeo: ' + (up.error || 'sem id na resposta'));\nreturn [{ json: { youtube_id: up.id } }];\n"
    },
    "position": [
      1680,
      0
    ]
  },
  output: [
    {
      "youtube_id": "abc"
    }
  ]
});

const s_thumb = node({
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
    "credentials": {
      "youTubeOAuth2Api": {
        "id": "pnIjvYU4Eixl66cj",
        "name": "YouTube - Deu Tudo Errado TV"
      }
    },
    "onError": "continueRegularOutput",
    "alwaysOutputData": true,
    "position": [
      1920,
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

const shorts = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Shorts a enviar",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nconst id = $('Checar envio do vídeo').first().json.youtube_id;\nreturn p.shorts.map(s => ({ json: {\n  n: s.n,\n  url: s.url,\n  publish_at: s.publish_at,\n  body: {\n    snippet: { ...p.snippet_base, title: s.title, description: String(s.description || '').replace('{{LONG_URL}}', `https://youtu.be/${id}`) },\n    status: s.status,\n  },\n} }));\n"
    },
    "position": [
      2160,
      0
    ]
  },
  output: [
    {
      "n": 1,
      "url": "s3://x",
      "publish_at": "2026-10-17T15:00:00Z",
      "body": {}
    }
  ]
});

const s_shorts = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: sessões dos Shorts",
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
    "credentials": {
      "youTubeOAuth2Api": {
        "id": "pnIjvYU4Eixl66cj",
        "name": "YouTube - Deu Tudo Errado TV"
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
    {
      "headers": {
        "location": "https://upload"
      },
      "statusCode": 200
    }
  ]
});

const uploads = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Montar envios",
    "parameters": {
      "jsCode": "const p = $('Plano de publicação').first().json;\nconst shorts = $('Shorts a enviar').all().map(i => i.json);\nconst sessions = $('YouTube: sessões dos Shorts').all().map(i => i.json);\nconst thumbSession = $('YouTube: sessão da thumbnail').first().json;\nconst uploads = shorts.map((s, i) => ({ ref: `short${s.n}`, upload_url: sessions[i].headers.location, media_url: s.url, content_type: 'video/mp4' }));\nconst thumbUrl = thumbSession?.headers?.location;\nif (thumbUrl && p.thumb_url) uploads.unshift({ ref: 'thumb', upload_url: thumbUrl, media_url: p.thumb_url, content_type: 'image/jpeg' });\nreturn [{ json: {\n  uploads,\n  thumb_error: thumbUrl ? null : (thumbSession?.error?.message || JSON.stringify(thumbSession?.error || thumbSession).slice(0, 300)),\n} }];\n"
    },
    "position": [
      2640,
      0
    ]
  },
  output: [
    {
      "uploads": [],
      "thumb_error": null
    }
  ]
});

const up_rest = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Worker: enviar Shorts e thumbnail",
    "parameters": {
      "method": "POST",
      "url": expr("{{ $('Config').first().json.worker_url }}/jobs/youtube_upload"),
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify({ video_id: $('Plano de publicação').first().json.video_id, idempotency_key: $('Plano de publicação').first().json.video_id + '-yt-rest-' + $execution.id, callback_url: $execution.resumeUrl, input: { uploads: $json.uploads } }) }}"),
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
      "job_id": "j",
      "status": "queued"
    }
  ]
});

const w_rest = node({
  type: "n8n-nodes-base.wait",
  version: 1.1,
  config: {
    "name": "Aguardar envio dos Shorts",
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
      3120,
      0
    ]
  },
  output: [
    {
      "body": {
        "status": "succeeded",
        "result": {
          "uploads": []
        }
      }
    }
  ]
});

const c_rest = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Checar envio dos Shorts",
    "parameters": {
      "jsCode": "const b = $input.first().json.body;\nif (!b) throw new Error('Envio dos Shorts: tempo esgotado esperando o worker');\nif (b.status !== 'succeeded') throw new Error('Envio dos Shorts ao YouTube falhou: ' + (b.error || 'sem detalhe'));\nconst p = $('Plano de publicação').first().json;\nconst longId = $('Checar envio do vídeo').first().json.youtube_id;\nconst shorts = $('Shorts a enviar').all().map(i => i.json);\nconst byRef = Object.fromEntries(b.result.uploads.map(u => [u.ref, u]));\nconst pubs = [{ kind: 'long', id: longId, publish_at: p.publish_at }];\nfor (const s of shorts) {\n  const u = byRef[`short${s.n}`] || {};\n  pubs.push({ kind: 'short', id: u.ok ? u.id : null, publish_at: s.publish_at, n: s.n, error: u.ok ? null : (u.error || 'não enviado') });\n}\nreturn [{ json: { long_id: longId, pubs, thumb_ok: !!byRef.thumb?.ok, thumb_upload_error: byRef.thumb && !byRef.thumb.ok ? byRef.thumb.error : null } }];\n"
    },
    "position": [
      3360,
      0
    ]
  },
  output: [
    {
      "long_id": "abc",
      "pubs": [],
      "thumb_ok": true
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
      "query": "WITH v AS (\n  UPDATE videos SET spec = jsonb_set(COALESCE(spec, '{}'::jsonb), '{publishing,youtube_id}', to_jsonb($2::text)), updated_at = now()\n  WHERE id = $1::uuid\n)\nINSERT INTO publications (video_id, platform, external_id, kind, publish_at, status)\nSELECT $1::uuid, 'youtube', p->>'id', (p->>'kind')::publication_kind, (p->>'publish_at')::timestamptz,\n       CASE WHEN p->>'id' IS NULL THEN 'failed' ELSE 'scheduled' END::publication_status\nFROM jsonb_array_elements($3::jsonb) p;",
      "options": {
        "queryReplacement": expr("{{ [ $('Plano de publicação').first().json.video_id, $json.long_id, JSON.stringify($json.pubs) ] }}")
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
      3600,
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
      "jsCode": "const p = $('Plano de publicação').first().json;\nconst r = $('Checar envio dos Shorts').first().json;\nconst thumbErr = r.thumb_upload_error || $('Montar envios').first().json.thumb_error;\nconst local = iso => DateTime.fromISO(iso).setZone(p.tz).toFormat('dd/MM HH:mm');\nconst lines = [\n  '📅 *Agendado no YouTube*',\n  `*${p.title}*`,\n  `Vídeo: ${p.publish_local} — https://youtu.be/${r.long_id}`,\n  '',\n  '📱 Shorts:',\n  ...r.pubs.filter(x => x.kind === 'short').map(x => x.id\n    ? `${x.n}. ${local(x.publish_at)} — https://youtube.com/shorts/${x.id}`\n    : `${x.n}. ⚠️ não enviado: ${String(x.error || '').slice(0, 200)}`),\n  '',\n  r.thumb_ok ? '🖼️ Thumbnail aplicada.' : `⚠️ Thumbnail não aplicada${thumbErr ? `: ${String(thumbErr).slice(0, 300)}` : ''}. Envie pelo YouTube Studio.`,\n  '',\n  'Tudo fica privado até o horário agendado. Confira no YouTube Studio > Conteúdo.',\n];\nreturn [{ json: { number: p.number, text: lines.join('\\n') } }];\n"
    },
    "position": [
      3840,
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
      4080,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-publish", "factory.publish \u00b7 Deu Tudo Errado")
  .add(t_sub)
  .to(config)
  .to(load)
  .to(plan)
  .to(s_long)
  .to(up_long)
  .to(w_long)
  .to(c_long)
  .to(s_thumb)
  .to(shorts)
  .to(s_shorts)
  .to(uploads)
  .to(up_rest)
  .to(w_rest)
  .to(c_rest)
  .to(save)
  .to(msg)
  .to(wa);
