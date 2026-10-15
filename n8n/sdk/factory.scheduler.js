import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const t_cron = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.2,
  config: {
    "name": "A cada hora",
    "parameters": {
      "rule": {
        "interval": [
          {
            "field": "hours",
            "hoursInterval": 1,
            "triggerAtMinute": 5
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
    "name": "Canais ativos",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT c.slug, c.config,\n  (SELECT count(*) FROM topics t WHERE t.channel_id = c.id AND t.status = 'queued') AS queued,\n  (SELECT count(*) FROM videos v WHERE v.channel_id = c.id AND v.created_at > now() - interval '12 hours') AS recent\nFROM channels c WHERE c.active ORDER BY c.slug;",
      "options": {}
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
      "slug": "career-levels",
      "config": {},
      "queued": 10,
      "recent": 0
    }
  ]
});

const plan = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Quem produz agora",
    "parameters": {
      "jsCode": "// Decide quais canais produzem nesta hora.\n// config.schedule: timezone, production_days ([\"mon\",\"wed\",...], vazio = todos os dias),\n// production_hour (0-23; se faltar, usa a hora do production_cron), min_queued_topics (alerta de fila baixa).\nconst DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];\nconst out = [];\nfor (const it of $input.all()) {\n  const r = it.json;\n  if (!r.slug) continue;\n  const cfg = typeof r.config === 'string' ? JSON.parse(r.config) : r.config;\n  const s = cfg.schedule || {};\n  const now = DateTime.now().setZone(s.timezone || 'America/Sao_Paulo');\n  let hour = s.production_hour;\n  if (hour == null && s.production_cron) hour = Number(String(s.production_cron).trim().split(/\\s+/)[1]);\n  if (hour == null || Number.isNaN(Number(hour))) hour = 2;\n  const days = Array.isArray(s.production_days) && s.production_days.length\n    ? s.production_days.map(d => String(d).slice(0, 3).toLowerCase()) : DAYS;\n  if (now.hour !== Number(hour) || !days.includes(DAYS[now.weekday % 7])) continue;\n  if (Number(r.recent) > 0) continue; // já produziu nas últimas 12 h\n  const queued = Number(r.queued);\n  const number = cfg.approval?.to;\n  if (!queued) {\n    out.push({ json: { kind: 'alert', number, text: `⚠️ *${cfg.name}*: fila de temas vazia, a produção de hoje foi pulada. Adicione temas.` } });\n    continue;\n  }\n  out.push({ json: { kind: 'produce', channel_slug: r.slug, name: cfg.name } });\n  const min = Number(s.min_queued_topics ?? 5);\n  if (queued - 1 < min) {\n    out.push({ json: { kind: 'alert', number, text: `📋 *${cfg.name}*: restam ${queued - 1} temas na fila. Adicione mais para não parar.` } });\n  }\n}\nreturn out;\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "kind": "produce",
      "channel_slug": "career-levels",
      "name": "Career Levels"
    }
  ]
});

const route = switchCase({
  type: "n8n-nodes-base.switch",
  version: 3.4,
  config: {
    "name": "Tipo",
    "parameters": {
      "mode": "expression",
      "numberOutputs": 2,
      "output": expr("{{ $json.kind === 'produce' ? 0 : 1 }}")
    },
    "position": [
      960,
      0
    ]
  },
  output: [
    {}
  ]
});

const run = node({
  type: "n8n-nodes-base.executeWorkflow",
  version: 1.3,
  config: {
    "name": "Produzir vídeo",
    "parameters": {
      "mode": "each",
      "source": "database",
      "workflowId": {
        "__rl": true,
        "mode": "id",
        "value": "6ZhBwxhg575IOsSC"
      },
      "workflowInputs": {
        "mappingMode": "defineBelow",
        "value": {
          "channel_slug": expr("{{ $json.channel_slug }}")
        },
        "matchingColumns": [],
        "schema": [
          {
            "id": "channel_slug",
            "displayName": "channel_slug",
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
      1200,
      -100
    ]
  },
  output: [
    {}
  ]
});

const wa = node({
  type: "n8n-nodes-evolution-api.evolutionApi",
  version: 1,
  config: {
    "name": "WhatsApp: alerta",
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
      1200,
      100
    ]
  },
  output: [
    {}
  ]
});

export default workflow("factory-scheduler", "factory.scheduler")
  .add(t_cron)
  .to(config)
  .to(load)
  .to(plan)
  .to(route
    .onCase(0, run)
    .onCase(1, wa));
