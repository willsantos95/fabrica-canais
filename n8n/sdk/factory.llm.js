import { workflow, node, trigger, switchCase, ifElse, expr } from '@n8n/workflow-sdk';

const t_sub = trigger({
  type: "n8n-nodes-base.executeWorkflowTrigger",
  version: 1.2,
  config: {
    "name": "Pedido de IA",
    "parameters": {
      "inputSource": "workflowInputs",
      "workflowInputs": {
        "values": [
          {
            "name": "body",
            "type": "object"
          },
          {
            "name": "order",
            "type": "array"
          },
          {
            "name": "prepared",
            "type": "string"
          },
          {
            "name": "gemini",
            "type": "object"
          },
          {
            "name": "stage",
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
      "body": {},
      "order": [
        "gemini",
        "openai"
      ],
      "prepared": "",
      "gemini": {},
      "stage": "script"
    }
  ]
});

const plano = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Plano",
    "parameters": {
      "jsCode": "const i = $input.first().json;\nconst valid = ['prepared', 'gemini', 'openai'];\nconst order = (Array.isArray(i.order) && i.order.length ? i.order : ['openai']).filter(p => valid.includes(p));\nreturn [{ json: { body: i.body || {}, order, prepared: i.prepared || '', gemini: i.gemini || {}, stage: i.stage || '', step: 0, errors: [] } }];\n"
    },
    "position": [
      240,
      0
    ]
  },
  output: [
    {
      "body": {},
      "order": [],
      "step": 0,
      "errors": []
    }
  ]
});

const prox = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Próximo provedor",
    "parameters": {
      "jsCode": "// Escolhe o próximo provedor da ordem (pronto → gemini → openai) e monta o pedido.\nconst i = $input.first().json;\nconst order = i.order || [];\nlet step = i.step || 0;\nconst errors = i.errors || [];\nwhile (step < order.length && order[step] === 'prepared' && !String(i.prepared || '').trim()) step++;\nif (step >= order.length) {\n  throw new Error(`Nenhum provedor de IA conseguiu responder (${i.stage || 'etapa'}): ` + (errors.join(' | ') || 'ordem vazia'));\n}\nconst provider = order[step];\nconst b = i.body || {};\nlet request = null, model = null;\nif (provider === 'openai') {\n  request = b;\n  model = b.model;\n} else if (provider === 'gemini') {\n  const g = i.gemini || {};\n  const search = (b.tools || []).some(t => t.type === 'web_search');\n  // no plano grátis, a pesquisa no Google (grounding) só funciona nos modelos 2.5\n  model = search ? (g.search_model || 'gemini-2.5-flash') : (g.model || 'gemini-3.5-flash');\n  request = {\n    systemInstruction: { parts: [{ text: String(b.instructions || '') }] },\n    contents: [{ role: 'user', parts: [{ text: typeof b.input === 'string' ? b.input : JSON.stringify(b.input) }] }],\n    generationConfig: { maxOutputTokens: Math.min(Number(b.max_output_tokens) || 16000, 65536) },\n  };\n  if (search) request.tools = [{ google_search: {} }];\n  else if (b.text?.format?.type === 'json_object') request.generationConfig.responseMimeType = 'application/json';\n}\nreturn [{ json: { ...i, step, errors, provider, model, request } }];\n"
    },
    "position": [
      480,
      0
    ]
  },
  output: [
    {
      "provider": "gemini",
      "model": "gemini-2.5-flash",
      "request": {},
      "step": 0,
      "errors": []
    }
  ]
});

const rota = switchCase({
  type: "n8n-nodes-base.switch",
  version: 3.4,
  config: {
    "name": "Provedor",
    "parameters": {
      "mode": "expression",
      "numberOutputs": 3,
      "output": expr("{{ ({ prepared: 0, openai: 1, gemini: 2 })[$json.provider] }}")
    },
    "position": [
      720,
      0
    ]
  },
  output: [
    {}
  ]
});

const pronto = node({
  type: "n8n-nodes-base.noOp",
  version: 1,
  config: {
    "name": "Texto pronto",
    "parameters": {},
    "position": [
      960,
      -200
    ]
  },
  output: [
    {}
  ]
});

const openai = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "OpenAI",
    "parameters": {
      "method": "POST",
      "url": "https://api.openai.com/v1/responses",
      "authentication": "genericCredentialType",
      "genericAuthType": "httpHeaderAuth",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.request) }}"),
      "options": {
        "timeout": 900000
      }
    },
    "credentials": {
      "httpHeaderAuth": {
        "id": "9OK91AZnXE70dKic",
        "name": "OpenAi - Fabrica"
      }
    },
    "onError": "continueRegularOutput",
    "alwaysOutputData": true,
    "position": [
      960,
      0
    ]
  },
  output: [
    {
      "output_text": "x"
    }
  ]
});

const gemini = node({
  type: "n8n-nodes-base.httpRequest",
  version: 4.2,
  config: {
    "name": "Gemini",
    "parameters": {
      "method": "POST",
      "url": expr("{{ 'https://generativelanguage.googleapis.com/v1beta/models/' + $json.model + ':generateContent' }}"),
      "authentication": "predefinedCredentialType",
      "nodeCredentialType": "googlePalmApi",
      "sendBody": true,
      "specifyBody": "json",
      "jsonBody": expr("{{ JSON.stringify($json.request) }}"),
      "options": {
        "timeout": 900000
      }
    },
    "credentials": {
      "googlePalmApi": {
        "id": "MnXJZD0zO0Nx6MpZ",
        "name": "Google Gemini(PaLM) Api account"
      }
    },
    "onError": "continueRegularOutput",
    "alwaysOutputData": true,
    "position": [
      960,
      200
    ]
  },
  output: [
    {
      "candidates": []
    }
  ]
});

const aval = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Avaliar resposta",
    "parameters": {
      "jsCode": "// Normaliza a resposta no formato da OpenAI (output_text, usage, model) ou passa para o próximo provedor.\nconst st = $('Próximo provedor').last().json;\nconst r = $input.first().json;\nconst fail = msg => [{ json: { ...st, done: false, step: st.step + 1, errors: [...st.errors, `${st.provider}: ${String(msg).slice(0, 300)}`] } }];\nconst ok = resp => [{ json: { done: true, response: { ...resp, provider: st.provider, tried: st.errors } } }];\n\nif (st.provider === 'prepared') {\n  return ok({ status: 'completed', model: 'claude-pronto', output_text: String(st.prepared), usage: { input_tokens: 0, output_tokens: 0 }, output: [] });\n}\nif (r.error) return fail(r.error.message || JSON.stringify(r.error));\n\nif (st.provider === 'openai') {\n  if (r.status && r.status !== 'completed') return fail(`status ${r.status} ${JSON.stringify(r.incomplete_details || {})}`);\n  const text = r.output_text || (r.output || []).filter(o => o.type === 'message')\n    .flatMap(o => o.content || []).filter(c => c.type === 'output_text').map(c => c.text).join('');\n  if (!text) return fail('resposta vazia');\n  return ok({ ...r, output_text: text });\n}\n\n// gemini\nconst c = (r.candidates || [])[0];\nif (!c) return fail('sem resposta: ' + JSON.stringify(r.promptFeedback || r).slice(0, 200));\nif (c.finishReason && !['STOP', 'FINISH_REASON_UNSPECIFIED'].includes(c.finishReason)) return fail('finishReason ' + c.finishReason);\nlet text = (c.content?.parts || []).filter(p => !p.thought).map(p => p.text || '').join('');\nif (!text.trim()) return fail('texto vazio');\n// links da pesquisa do Google vêm como redirecionamento: troca pelo endereço real da página\nconst chunks = (c.groundingMetadata?.groundingChunks || []).map(x => x.web).filter(Boolean).slice(0, 20);\nconst sources = [];\nfor (const w of chunks) {\n  let url = w.uri;\n  try {\n    const res = await this.helpers.httpRequest({ url: w.uri, method: 'GET', disableFollowRedirect: true, followRedirect: false, ignoreHttpStatusErrors: true, returnFullResponse: true, timeout: 10000 });\n    url = res.headers?.location || url;\n  } catch (e) {}\n  sources.push({ title: w.title, url });\n  if (url !== w.uri) text = text.split(w.uri).join(url);\n}\nconst u = r.usageMetadata || {};\nreturn ok({\n  status: 'completed', model: r.modelVersion || st.model, output_text: text,\n  usage: { input_tokens: (u.promptTokenCount || 0) + (u.toolUsePromptTokenCount || 0), output_tokens: (u.candidatesTokenCount || 0) + (u.thoughtsTokenCount || 0) },\n  output: [], grounding_sources: sources, web_search_queries: c.groundingMetadata?.webSearchQueries || [],\n});\n"
    },
    "position": [
      1200,
      0
    ]
  },
  output: [
    {
      "done": true,
      "response": {}
    }
  ]
});

const fim = ifElse({
  type: "n8n-nodes-base.if",
  version: 2.2,
  config: {
    "name": "Respondeu?",
    "parameters": {
      "conditions": {
        "options": {
          "caseSensitive": true,
          "leftValue": "",
          "typeValidation": "loose"
        },
        "conditions": [
          {
            "leftValue": expr("{{ $json.done }}"),
            "rightValue": true,
            "operator": {
              "type": "boolean",
              "operation": "true",
              "singleValue": true
            }
          }
        ],
        "combinator": "and"
      },
      "options": {}
    },
    "position": [
      1440,
      0
    ]
  },
  output: [
    {}
  ]
});

const resp = node({
  type: "n8n-nodes-base.code",
  version: 2,
  config: {
    "name": "Resposta",
    "parameters": {
      "jsCode": "return [{ json: $input.first().json.response }];"
    },
    "position": [
      1680,
      -100
    ]
  },
  output: [
    {
      "output_text": "x",
      "provider": "gemini"
    }
  ]
});

export default workflow("factory-llm", "factory.llm")
  .add(t_sub)
  .to(plano)
  .to(prox)
  .to(rota
    .onCase(0, pronto.to(aval))
    .onCase(1, openai.to(aval))
    .onCase(2, gemini.to(aval)))
  .add(aval)
  .to(fim.onTrue(resp).onFalse(prox));
