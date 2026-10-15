import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const hook = trigger({
  type: "n8n-nodes-base.webhook",
  version: 2.1,
  config: {
    "name": "Evolution: mensagem recebida",
    "parameters": {
      "httpMethod": "POST",
      "path": "fabrica-aprovacao",
      "responseMode": "onReceived",
      "options": {
        "onlyRunIf": expr("{{ $json.body.event === 'messages.upsert' && !String($json.body.data?.key?.remoteJid || '').endsWith('@g.us') }}")
      }
    },
    "position": [
      0,
      0
    ]
  },
  output: [
    {
      "body": {
        "event": "messages.upsert",
        "data": {
          "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": false
          },
          "message": {
            "conversation": "1"
          }
        }
      }
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

const read = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Ler resposta",
    "parameters": {
      "jsCode": "// Só segue para mensagens de texto que sejam um comando 1, 2, 3 ou 4.\n// A instância da fábrica é o próprio número do Will: as respostas vêm do chat \"Você\" (mensagem para si mesmo),\n// que chegam como fromMe = true. Mensagens de outras pessoas e de grupos são ignoradas.\nconst b = $input.first().json.body || {};\nconst ev = String(b.event || '').toLowerCase().replace(/_/g, '.');\nconst d = Array.isArray(b.data) ? b.data[0] || {} : (b.data || {});\nconst key = d.key || {};\nconst raw = String(d.message?.conversation || d.message?.extendedTextMessage?.text || '').trim();\n// código do vídeo (#AB12) opcional, em qualquer posição: \"1 #AB12\", \"#AB12 3 2\"\nconst codeM = raw.match(/#\\s*([0-9a-fA-F]{4})\\b/);\nconst code = codeM ? codeM[1].toLowerCase() : '';\nconst text = raw.replace(/#\\s*[0-9a-fA-F]{4}\\b/, ' ').replace(/\\s+/g, ' ').trim();\nif (!ev.includes('messages.upsert') || !text) return [];\nconst cmd = text.match(/^([1-4])(?:[\\s.,:-]+([\\s\\S]*))?$/);\nif (!cmd) return [];\nconst num = j => String(j || '').split('@')[0].replace(/\\D/g, '');\nconst isPhone = j => j && /@s\\.whatsapp\\.net$/.test(String(j));\nconst chat = [key.remoteJid, key.remoteJidAlt, key.senderPn].filter(isPhone).map(num).filter(x => x.length >= 10);\nif (String(key.remoteJid || '').endsWith('@g.us') || !chat.length) return [];\nconst owner = num(b.sender);\nif (key.fromMe) {\n  // só vale se for o chat com você mesmo\n  if (!owner || !chat.some(x => x.slice(-8) === owner.slice(-8))) return [];\n}\nreturn [{ json: {\n  cmd: Number(cmd[1]),\n  arg: (cmd[2] || '').trim(),\n  code,\n  sender: chat[0],\n  last8: '{' + [...new Set(chat.map(x => x.slice(-8)))].join(',') + '}',\n} }];\n"
    },
    "position": [
      480,
      0
    ]
  },
  output: [
    {
      "cmd": 1,
      "arg": "",
      "code": "",
      "sender": "5511999999999",
      "last8": "{99999999}"
    }
  ]
});

const find = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Vídeo aguardando",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT v.id AS video_id, upper(left(v.id::text, 4)) AS code, v.spec, c.config, c.name AS channel_name\nFROM videos v JOIN channels c ON c.id = v.channel_id\nWHERE v.status = 'awaiting_approval'\n  AND right(regexp_replace(c.config->'approval'->>'to', '\\D', '', 'g'), 8) = ANY($1::text[])\nORDER BY v.created_at DESC LIMIT 20;",
      "options": {
        "queryReplacement": expr("{{ [ $json.last8 ] }}")
      }
    },
    "credentials": {
      "postgres": {
        "id": "CgrwOpkbdW4VgyTc",
        "name": "Postgres - Fabrica"
      }
    },
    "alwaysOutputData": true,
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
      "video_id": "v",
      "code": "ABCD",
      "spec": {},
      "config": {},
      "channel_name": "c"
    }
  ]
});

const decide = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Interpretar",
    "parameters": {
      "jsCode": "const m = $('Ler resposta').first().json;\nconst parse = x => typeof x === 'string' ? JSON.parse(x) : x;\nconst rows = $input.all().map(i => i.json).filter(r => r.video_id);\n// sem vídeo aguardando para esse número: não responde (evita responder \"1\" de qualquer conversa)\nif (!rows.length) return [];\nconst titleOf = r => { const s = parse(r.spec); return s.publishing?.title || s.chosen_title; };\nconst list = rows.map(r => `#${r.code} · ${r.channel_name} · ${titleOf(r)}`).join('\\n');\nconst number0 = parse(rows[0].config).approval?.to || m.sender;\nconst help = reply => [{ json: { action: 'help', reply, number: number0 } }];\nlet v;\nif (m.code) {\n  const hits = rows.filter(r => r.code.toLowerCase() === m.code);\n  if (!hits.length) return help(`Não achei vídeo aguardando aprovação com o código #${m.code.toUpperCase()}.\\n\\nPendentes:\\n${list}`);\n  if (hits.length > 1) return help(`Mais de um vídeo com o código #${m.code.toUpperCase()}. Responda pelo YouTube Studio ou rejeite um deles.\\n\\n${list}`);\n  v = hits[0];\n} else if (rows.length > 1) {\n  return help(`Há ${rows.length} vídeos aguardando aprovação. Inclua o código na resposta, ex.: ${m.cmd}${m.arg ? ' ' + m.arg : ''} #${rows[0].code}\\n\\n${list}`);\n} else {\n  v = rows[0];\n}\nconst spec = parse(v.spec);\nconst cfg = parse(v.config);\nconst number = cfg.approval?.to || m.sender;\nconst title = spec.publishing?.title || spec.chosen_title;\nconst tag = `[${v.channel_name} #${v.code}]`;\nlet action = 'help';\nlet reply = '';\nif (m.cmd === 1) {\n  action = 'approve';\n  reply = `✅ Aprovado ${tag}: *${title}*\\nVou agendar no YouTube e te aviso com os links.`;\n} else if (m.cmd === 2) {\n  action = 'reject';\n  reply = `🗑️ Rejeitado ${tag}: *${title}*${m.arg ? `\\nMotivo: ${m.arg}` : ''}`;\n} else if (m.cmd === 3) {\n  const n = parseInt(m.arg, 10);\n  const opts = spec.thumbnail?.options || [];\n  if (!(n >= 1 && n <= opts.length)) reply = `Escolha uma thumbnail de 1 a ${opts.length}. Ex.: 3 2 #${v.code}`;\n  else { spec.thumbnail.chosen = n; action = 'edit'; reply = `🖼️ ${tag} Thumbnail ${n} escolhida.`; }\n} else if (m.cmd === 4) {\n  const n = parseInt(m.arg, 10);\n  const titles = (spec.titles || []).slice(0, 5);\n  if (!(n >= 1 && n <= titles.length)) reply = `Escolha um título de 1 a ${titles.length}. Ex.: 4 3 #${v.code}`;\n  else {\n    spec.chosen_title = titles[n - 1];\n    spec.publishing = { ...(spec.publishing || {}), title: titles[n - 1].replace(/[<>]/g, '').slice(0, 100) };\n    action = 'edit';\n    reply = `📝 ${tag} Título ${n}: *${titles[n - 1]}*`;\n  }\n}\nif (action === 'edit') reply += `\\n\\nResponda 1 #${v.code} para aprovar, 2 #${v.code} para rejeitar, 3 N (thumbnail) ou 4 N (título).`;\nreturn [{ json: { action, reply, number, video_id: v.video_id, spec, reason: m.arg, sender: m.sender,\n  publish_workflow_id: cfg.youtube?.publish_workflow_id || 'y3zthNcqybMcQEl0' } }];\n"
    },
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "action": "approve",
      "reply": "ok",
      "number": "55",
      "video_id": "v",
      "spec": {},
      "reason": "",
      "sender": "55",
      "publish_workflow_id": "x"
    }
  ]
});

const route = switchCase({
  type: "n8n-nodes-base.switch",
  version: 3.4,
  config: {
    "name": "Ação",
    "parameters": {
      "mode": "expression",
      "numberOutputs": 4,
      "output": expr("{{ ({ approve: 0, reject: 1, edit: 2 })[$json.action] ?? 3 }}")
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {}
  ]
});

const ok = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Registrar aprovação",
    "parameters": {
      "operation": "executeQuery",
      "query": "INSERT INTO approvals (video_id, decision, decided_by) VALUES ($1::uuid, 'approved', $2);",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, $json.sender ] }}")
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
      -200
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const pub = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Publicar no YouTube",
    "parameters": {
      "mode": "once",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": expr("{{ $('Interpretar').first().json.publish_workflow_id }}")
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "video_id": expr("{{ $('Interpretar').first().json.video_id }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "video_id",
            "displayName": "video_id",
            "required": false,
            "defaultMatch": false,
            "display": true,
            "canBeUsedToMatch": true,
            "type": "string"
          }
        ]
      },
      "options": {
        "waitForSubWorkflow": false
      }
    },
    "position": [
      1680,
      -200
    ]
  },
  output: [
    {}
  ]
});

const clips = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Clipes TikTok",
    "parameters": {
      "mode": "once",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": "f98b6HG2uClowRB4"
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "video_id": expr("{{ $('Interpretar').first().json.video_id }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "video_id",
            "displayName": "video_id",
            "required": false,
            "defaultMatch": false,
            "display": true,
            "canBeUsedToMatch": true,
            "type": "string"
          }
        ]
      },
      "options": {
        "waitForSubWorkflow": false
      }
    },
    "position": [
      1800,
      -200
    ]
  },
  output: [
    {}
  ]
});

const no = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Registrar rejeição",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH a AS (\n  INSERT INTO approvals (video_id, decision, reason, decided_by) VALUES ($1::uuid, 'rejected', NULLIF($2, ''), $3)\n)\nUPDATE videos SET status = 'rejected', updated_at = now() WHERE id = $1::uuid;",
      "options": {
        "queryReplacement": expr("{{ [ $json.video_id, $json.reason || '', $json.sender ] }}")
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

const edit = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar escolha",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE videos SET spec = $2::jsonb, updated_at = now() WHERE id = $1::uuid;",
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
      200
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

const reply = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "Responder",
    "parameters": {
      "resource": "messages-api",
      "operation": "send-text",
      "instanceName": expr("{{ $('Config').first().json.evolution_instance }}"),
      "remoteJid": expr("{{ $('Interpretar').first().json.number }}"),
      "messageText": expr("{{ $('Interpretar').first().json.reply }}")
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
      1920,
      0
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-approval", "factory.approval")
  .add(hook)
  .to(config)
  .to(read)
  .to(find)
  .to(decide)
  .to(route
    .onCase(0, ok.to(pub.to(clips.to(reply))))
    .onCase(1, no.to(reply))
    .onCase(2, edit.to(reply))
    .onCase(3, reply));
