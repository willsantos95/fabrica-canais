import { workflow, node, trigger, switchCase, expr } from '@n8n/workflow-sdk';

const t_cron = trigger({
  type: "n8n-nodes-base.scheduleTrigger",
  version: 1.2,
  config: {
    "name": "De hora em hora (8h-23h)",
    "parameters": {
      "rule": {
        "interval": [
          {
            "field": "cronExpression",
            "expression": "15 8-23 * * *"
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
    "name": "Rodar agora",
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
            "id": "n-slug",
            "name": "channel_slug",
            "value": "lance-rapido",
            "type": "string"
          },
          {
            "id": "n-inst",
            "name": "evolution_instance",
            "value": "fabrica-videos",
            "type": "string"
          }
        ]
      },
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

const canal = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Canal",
    "parameters": {
      "operation": "executeQuery",
      "query": "WITH ch AS (SELECT id, config FROM channels WHERE slug = $1),\nexp AS (\n  UPDATE topics SET status = 'discarded'\n  WHERE channel_id = (SELECT id FROM ch) AND status = 'queued'\n    AND created_at < now() - make_interval(hours => COALESCE(((SELECT config FROM ch)->'news'->>'topic_ttl_hours')::int, 12))\n  RETURNING id\n)\nSELECT ch.id, ch.config,\n  (SELECT count(*) FROM topics t WHERE t.channel_id = ch.id AND t.status = 'queued') - (SELECT count(*) FROM exp) AS queued,\n  COALESCE((SELECT json_agg(json_build_object('story_key', n.story_key, 'title', n.title_pt)) FROM (\n     SELECT DISTINCT ON (story_key) story_key, title_pt FROM news_items\n     WHERE channel_id = ch.id AND status = 'queued' AND created_at > now() - interval '48 hours' AND story_key IS NOT NULL\n     ORDER BY story_key, created_at DESC) n), '[]'::json) AS recent\nFROM ch;",
      "options": {
        "queryReplacement": expr("{{ [ $json.channel_slug ] }}")
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
      "id": "c",
      "config": {},
      "queued": 0,
      "recent": []
    }
  ]
});

const coletar = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Coletar feeds",
    "parameters": {
      "jsCode": "// Lê os feeds RSS do canal e devolve as notícias recentes (uma lista só, para gravar de uma vez).\nconst c = $('Canal').first().json;\nconst cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;\nconst news = cfg.news || {};\nconst maxAgeMs = (news.max_age_hours || 18) * 3600e3;\nconst now = Date.now();\n\nconst dec = s => String(s || '')\n  .replace(/<!\\[CDATA\\[([\\s\\S]*?)\\]\\]>/g, '$1')\n  .replace(/<[^>]+>/g, ' ')\n  .replace(/&#(\\d+);/g, (_, n) => String.fromCharCode(Number(n)))\n  .replace(/&amp;/g, '&').replace(/&quot;/g, '\"').replace(/&#39;|&apos;/g, \"'\")\n  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ')\n  .replace(/\\s+/g, ' ').trim();\nconst tag = (x, t) => {\n  const m = x.match(new RegExp('<' + t + '(?:\\\\s[^>]*)?>([\\\\s\\\\S]*?)</' + t + '>', 'i'));\n  return m ? dec(m[1]) : '';\n};\nconst link = x => {\n  const l = tag(x, 'link');\n  if (l) return l;\n  const m = x.match(/<link[^>]*href=\"([^\"]+)\"/i);\n  return m ? m[1] : '';\n};\n// fora disso não é notícia para Short\nconst JUNK = /onde assistir|bonus code|bônus|odds|aposta|bet(mgm|365|ano)|cartola|fantasy|melhores momentos|ao vivo:|live:|podcast|newsletter/i;\n\nconst out = [];\nconst errors = [];\nfor (const f of news.feeds || []) {\n  try {\n    const xml = await this.helpers.httpRequest({ url: f.url, timeout: 20000, headers: { 'User-Agent': 'Mozilla/5.0 (LanceRapido news reader)' } });\n    const items = String(xml).match(/<(item|entry)[\\s>][\\s\\S]*?<\\/(item|entry)>/gi) || [];\n    for (const x of items.slice(0, 40)) {\n      const title = tag(x, 'title');\n      const url = link(x);\n      const date = Date.parse(tag(x, 'pubDate') || tag(x, 'updated') || tag(x, 'published') || tag(x, 'dc:date'));\n      if (!title || !url || !date || now - date > maxAgeMs || JUNK.test(title)) continue;\n      out.push({ url, title: title.slice(0, 300), summary: (tag(x, 'description') || tag(x, 'summary')).slice(0, 600),\n        source: f.source, sport: f.sport, published_at: new Date(date).toISOString() });\n    }\n  } catch (e) {\n    errors.push(`${f.source} ${f.sport}: ${String(e.message).slice(0, 80)}`);\n  }\n}\nif (!out.length) return [];\nreturn [{ json: { channel_id: c.id, items: JSON.stringify(out), n: out.length, errors } }];\n"
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {
      "channel_id": "c",
      "items": "[]",
      "n": 0,
      "errors": []
    }
  ]
});

const guardar = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Guardar novas",
    "parameters": {
      "operation": "executeQuery",
      "query": "-- novas desta rodada + as que ainda não foram avaliadas (ex.: a rodada anterior falhou)\nWITH ins AS (\n  INSERT INTO news_items (channel_id, url, title, summary, source, sport, published_at)\n  SELECT $1::uuid, x.url, x.title, x.summary, x.source, x.sport, x.published_at\n  FROM jsonb_to_recordset($2::jsonb) AS x(url text, title text, summary text, source text, sport text, published_at timestamptz)\n  ON CONFLICT (channel_id, url) DO NOTHING\n  RETURNING id, url, title, summary, source, sport, published_at\n)\nSELECT * FROM ins\nUNION ALL\nSELECT id, url, title, summary, source, sport, published_at FROM news_items\nWHERE channel_id = $1::uuid AND status = 'new' AND published_at > now() - interval '18 hours';",
      "options": {
        "queryReplacement": expr("{{ [ $json.channel_id, $json.items ] }}")
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
      960,
      0
    ]
  },
  output: [
    {
      "id": "n",
      "url": "u",
      "title": "t",
      "sport": "nba"
    }
  ]
});

const pedido = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Pedido de avaliação",
    "parameters": {
      "jsCode": "// Monta o pedido de avaliação (modelo barato) com as notícias novas desta rodada.\nconst c = $('Canal').first().json;\nconst cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;\nconst recent = (typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || [];\nconst items = $input.all().map(i => i.json)\n  .sort((a, b) => String(b.published_at).localeCompare(String(a.published_at)))\n  .slice(0, 80);\n\nconst SYSTEM = `Você é o editor-chefe do canal de Shorts esportivos \"${cfg.name}\" (futebol, NBA e NFL para o público brasileiro).\nAvalie cada notícia de 0 a 10 pelo potencial de virar hoje um Short de 45 segundos que o brasileiro quer assistir.\n\nPontua alto:\n- fato novo e concreto: resultado marcante, transferência ou contratação confirmada, lesão de jogador importante, recorde, demissão, polêmica com fato verificável;\n- interesse do público brasileiro: clubes brasileiros, Seleção, brasileiros no exterior, grandes clubes europeus, times e astros populares da NBA e da NFL no Brasil;\n- dá para explicar em 45 segundos com uma frase de análise (por que importa).\n\nNota 0: apostas e bônus, \"onde assistir\", Cartola ou fantasy, melhores momentos sem fato novo, agenda, propaganda, opinião sem fato, boato sem fonte.\nNota no máximo 3: mortes, crimes, tragédias pessoais, saúde mental, assuntos de família.\nNotícias sobre o MESMO fato recebem o MESMO story_key (slug curto em minúsculas com os nomes principais, ex.: \"eagles-qb-coagulo-panturrilha\").\nSe o fato já está na lista de pautas recentes, nota no máximo 3.\ntitle_pt: manchete em português do Brasil, até 70 caracteres, fiel ao fato, sem clickbait mentiroso.\nsport: futebol | nba | nfl. reason: uma frase curta.\n\nResponda só com JSON: {\"items\":[{\"id\":\"...\",\"score\":0,\"story_key\":\"...\",\"title_pt\":\"...\",\"sport\":\"nba\",\"reason\":\"...\"}]} com todas as notícias recebidas.`;\n\nconst lines = items.map(n => JSON.stringify({ id: n.id, sport: n.sport, source: n.source, published: n.published_at,\n  title: n.title, summary: String(n.summary || '').slice(0, 280) }));\nconst input = `Avalie as notícias abaixo e responda em JSON.\\n\\nPautas recentes (já usadas ou na fila):\\n${recent.map(r => `- ${r.story_key}: ${r.title}`).join('\\n') || '- nenhuma'}\\n\\nNotícias novas:\\n${lines.join('\\n')}`;\n\nreturn [{ json: { body: {\n  model: cfg.news?.scoring_model || 'gpt-5.4-nano',\n  instructions: SYSTEM,\n  input,\n  reasoning: { effort: 'low' },\n  text: { format: { type: 'json_object' } },\n  max_output_tokens: 16000,\n}, ids: items.map(n => n.id) } }];\n"
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {
      "body": {},
      "ids": []
    }
  ]
});

const openai = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "OpenAI: avaliar",
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
      1440,
      0
    ]
  },
  output: [
    {
      "output": []
    }
  ]
});

const escolher = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Escolher pautas",
    "parameters": {
      "jsCode": "// Lê as notas, escolhe as pautas da rodada e prepara a gravação.\nconst c = $('Canal').first().json;\nconst cfg = typeof c.config === 'string' ? JSON.parse(c.config) : c.config;\nconst news = cfg.news || {};\nconst recent = new Set(((typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || []).map(r => r.story_key));\nconst queued = Number(c.queued || 0);\nconst byId = Object.fromEntries($('Guardar novas').all().map(i => [i.json.id, i.json]));\n\nconst resp = $input.first().json;\nconst text = resp.output_text || (resp.output || []).filter(o => o.type === 'message')\n  .flatMap(o => o.content || []).filter(x => x.type === 'output_text').map(x => x.text).join('');\nlet parsed;\ntry { parsed = JSON.parse(text); } catch (e) { throw new Error('Avaliação sem JSON válido: ' + text.slice(0, 200)); }\n\nconst slug = s => String(s || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')\n  .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80);\nconst scored = (parsed.items || []).filter(x => byId[x.id]).map(x => ({\n  id: x.id,\n  score: Math.max(0, Math.min(10, Math.round(Number(x.score) || 0))),\n  story_key: slug(x.story_key) || slug(byId[x.id].title),\n  title_pt: String(x.title_pt || byId[x.id].title).replace(/\\s+/g, ' ').trim().slice(0, 90),\n  sport: ['futebol', 'nba', 'nfl'].includes(x.sport) ? x.sport : byId[x.id].sport,\n  reason: String(x.reason || '').slice(0, 300),\n}));\n\n// o modelo às vezes dá story_keys diferentes para o mesmo fato: junta por semelhança das manchetes\nconst words = t => new Set(slug(t).split('-').filter(w => w.length > 3));\n// nomes próprios (palavras com maiúscula fora do início) pesam mais: \"Eagles\", \"Joe\", \"Milton\"\nconst names = t => new Set(String(t || '').split(/\\s+/).slice(1).filter(w => /^[A-ZÀ-Ý]/.test(w)).map(w => slug(w)).filter(Boolean));\nconst overlap = (A, B) => { let i = 0; for (const w of A) if (B.has(w)) i++; return [i, A.size && B.size ? i / Math.min(A.size, B.size) : 0]; };\nconst similar = (a, b) => {\n  const [ni, nr] = overlap(names(a), names(b));\n  if (ni >= 2 && nr >= 0.6) return true;\n  const [, wr] = overlap(words(a), words(b));\n  return wr >= 0.6;\n};\nconst recentTitles = ((typeof c.recent === 'string' ? JSON.parse(c.recent) : c.recent) || []).map(r => r.title || '');\nconst groups = [];\nfor (const s of [...scored].sort((a, b) => b.score - a.score)) {\n  const g = groups.find(g => g.key === s.story_key || similar(g.title, s.title_pt));\n  if (g) { s.story_key = g.key; continue; }\n  groups.push({ key: s.story_key, title: s.title_pt });\n}\n\n// uma pauta por fato (a nota mais alta), fora as que já foram usadas\nconst minScore = news.min_score ?? 7;\nconst best = {};\nfor (const s of scored) {\n  if (s.score < minScore - 1 || recent.has(s.story_key) || recentTitles.some(t => similar(t, s.title_pt))) continue;\n  if (!best[s.story_key] || s.score > best[s.story_key].score) best[s.story_key] = s;\n}\nconst room = Math.max(0, (news.max_queue ?? 8) - queued);\nconst limit = Math.min(news.max_topics_per_run ?? 3, room);\n// equilíbrio entre esportes: o melhor de cada esporte entra com 1 ponto de tolerância; o resto só acima da nota mínima\nconst ranked = Object.values(best).sort((a, b) => b.score - a.score);\nconst picks = [];\nfor (const sp of ['futebol', 'nba', 'nfl']) {\n  const top = ranked.find(r => r.sport === sp);\n  if (top && picks.length < limit) picks.push(top);\n}\nfor (const r of ranked) if (picks.length < limit && !picks.includes(r) && r.score >= minScore) picks.push(r);\npicks.sort((a, b) => b.score - a.score);\n\nconst pickedKeys = new Set(picks.map(p => p.story_key));\nconst updates = scored.map(s => ({ ...s, status: pickedKeys.has(s.story_key) ? 'queued' : (s.score < 4 ? 'skipped' : 'scored') }));\nfor (const p of picks) {\n  p.sources = scored.filter(s => s.story_key === p.story_key).map(s => byId[s.id])\n    .map(n => ({ title: n.title, url: n.url, source: n.source, published_at: n.published_at, summary: n.summary }));\n}\nconst topics = picks.map(p => ({ title: p.title_pt, priority: 100 - p.score * 10,\n  notes: JSON.stringify({ story_key: p.story_key, sport: p.sport, score: p.score, reason: p.reason, sources: p.sources }) }));\n\nreturn [{ json: { channel_id: c.id, updates: JSON.stringify(updates), topics: JSON.stringify(topics), picks,\n  scored: scored.length, room, preview: news.preview !== false, number: cfg.approval?.to, name: cfg.name } }];\n"
    },
    "position": [
      1680,
      0
    ]
  },
  output: [
    {
      "channel_id": "c",
      "updates": "[]",
      "topics": "[]",
      "picks": [],
      "number": "55"
    }
  ]
});

const salvar = node({
  type: "n8n-nodes-base.postgres",
  version: 2.5,
  config: {
    "name": "Salvar pautas",
    "parameters": {
      "operation": "executeQuery",
      "query": "UPDATE news_items n SET score = u.score, story_key = u.story_key, title_pt = u.title_pt, reason = u.reason, status = u.status\nFROM jsonb_to_recordset($2::jsonb) AS u(id uuid, score int, story_key text, title_pt text, reason text, status text)\nWHERE n.id = u.id;\nWITH ins AS (\n  INSERT INTO topics (channel_id, title, notes, priority, source)\n  SELECT $1::uuid, t.title, t.notes, t.priority, 'news'\n  FROM jsonb_to_recordset($3::jsonb) AS t(title text, notes text, priority int)\n  ON CONFLICT (channel_id, title) DO NOTHING\n  RETURNING id, notes\n)\nUPDATE news_items n SET topic_id = ins.id\nFROM ins WHERE n.channel_id = $1::uuid AND n.status = 'queued' AND n.topic_id IS NULL\n  AND n.story_key = (ins.notes::jsonb->>'story_key');\nSELECT count(*) AS pautas_na_fila FROM topics WHERE channel_id = $1::uuid AND status = 'queued';",
      "options": {
        "queryReplacement": expr("{{ [ $json.channel_id, $json.updates, $json.topics ] }}")
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
      "pautas_na_fila": 0
    }
  ]
});

const msg = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Mensagem prévia",
    "parameters": {
      "jsCode": "// Prévia no WhatsApp: quais notícias viraram pauta nesta rodada.\nconst e = $('Escolher pautas').first().json;\nif (!e.picks.length || !e.number) return [];\nconst TAG = { futebol: '⚽ FUTEBOL', nba: '🏀 NBA', nfl: '🏈 NFL' };\nconst lines = [`📰 *${e.name}* · ${e.picks.length} pauta(s) nova(s)${e.preview ? ' (prévia: nada é produzido ainda)' : ''}`, ''];\ne.picks.forEach((p, i) => {\n  const s = p.sources || [];\n  lines.push(`${i + 1}. ${TAG[p.sport] || p.sport} · nota ${p.score}`);\n  lines.push(`*${p.title_pt}*`);\n  if (p.reason) lines.push(`_${p.reason}_`);\n  if (s[0]) lines.push(`${s[0].source}: ${s[0].url}${s.length > 1 ? ` (+${s.length - 1} fonte(s))` : ''}`);\n  lines.push('');\n});\nlines.push(`Avaliadas nesta rodada: ${e.scored}. Vagas na fila: ${e.room}.`);\nreturn [{ json: { number: e.number, text: lines.join('\\n') } }];\n"
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
    "name": "WhatsApp: pautas",
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

export default workflow("factory-news", "factory.news")
  .add(t_cron)
  .to(config)
  .to(canal)
  .to(coletar)
  .to(guardar)
  .to(pedido)
  .to(openai)
  .to(escolher)
  .to(salvar)
  .to(msg)
  .to(wa)
  .add(t_manual)
  .to(config);
