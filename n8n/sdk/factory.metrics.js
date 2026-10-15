import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const t_cron = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.2,
  config: {
    "name": "A cada 6 horas",
    "parameters": {
      "rule": {
        "interval": [
          {
            "field": "hours",
            "hoursInterval": 6,
            "triggerAtMinute": 20
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
    "name": "Coletar agora",
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

const load = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Publicações",
    "parameters": {
      "operation": "executeQuery",
      "query": "SELECT p.external_id FROM publications p\nWHERE p.platform = 'youtube' AND p.external_id IS NOT NULL AND p.status IN ('scheduled', 'published')\n  AND p.created_at > now() - interval '120 days'\nORDER BY p.created_at DESC LIMIT 1000;",
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
      240,
      0
    ]
  },
  output: [
    {
      "external_id": "abc"
    }
  ]
});

const split = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Lotes de 50",
    "parameters": {
      "jsCode": "// Lotes de até 50 ids por chamada (videos.list custa 1 unidade de cota por chamada).\nconst ids = [...new Set($input.all().map(i => i.json.external_id).filter(Boolean))];\nconst out = [];\nfor (let i = 0; i < ids.length; i += 50) out.push({ json: { ids: ids.slice(i, i + 50).join(',') } });\nreturn out;\n"
    },
    "position": [
      480,
      0
    ]
  },
  output: [
    {
      "ids": "a,b"
    }
  ]
});

const yt = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "YouTube: estatísticas",
    "parameters": {
      "method": "GET",
      "url": expr("https://www.googleapis.com/youtube/v3/videos?part=statistics,status&maxResults=50&id={{ $json.ids }}"),
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "youTubeOAuth2Api",
      "options": {
        "timeout": 60000
      }
    },
    "credentials": {
      "youTubeOAuth2Api": {
        "id": "nnKxTYcW1aFdkd4a",
        "name": "YouTube - Fabrica"
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
      "items": []
    }
  ]
});

const rows = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Juntar",
    "parameters": {
      "jsCode": "const rows = [];\nfor (const it of $input.all()) {\n  for (const v of it.json.items || []) {\n    const s = v.statistics || {};\n    rows.push({ external_id: v.id, views: Number(s.viewCount ?? 0), likes: s.likeCount != null ? Number(s.likeCount) : null,\n      comments: s.commentCount != null ? Number(s.commentCount) : null, privacy: v.status?.privacyStatus || null });\n  }\n}\nreturn [{ json: { rows: JSON.stringify(rows), n: rows.length } }];\n"
    },
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "rows": "[]",
      "n": 0
    }
  ]
});

const save = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar métricas",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH d AS (\n  SELECT * FROM jsonb_to_recordset($1::jsonb) AS x(external_id text, views int, likes int, comments int, privacy text)\n), pubs AS (\n  UPDATE publications p SET status = 'published'\n  FROM d WHERE p.external_id = d.external_id AND d.privacy = 'public' AND p.status = 'scheduled'\n  RETURNING p.video_id, p.kind\n), vids AS (\n  UPDATE videos v SET status = 'published', updated_at = now()\n  WHERE v.id IN (SELECT video_id FROM pubs WHERE kind = 'long') AND v.status = 'scheduled'\n)\nINSERT INTO metrics (publication_id, date, views, likes, comments, updated_at)\nSELECT p.id, (now() AT TIME ZONE 'America/Sao_Paulo')::date, d.views, d.likes, d.comments, now()\nFROM d JOIN publications p ON p.external_id = d.external_id\nON CONFLICT (publication_id, date) DO UPDATE\n  SET views = EXCLUDED.views, likes = EXCLUDED.likes, comments = EXCLUDED.comments, updated_at = now();",
      "options": {
        "queryReplacement": expr("{{ [ $json.rows ] }}")
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
      0
    ]
  },
  output: [
    {
      "success": true
    }
  ]
});

export default workflow("factory-metrics", "factory.metrics")
  .add(t_cron)
  .to(load)
  .to(split)
  .to(yt)
  .to(rows)
  .to(save)
  .add(t_manual)
  .to(load);
