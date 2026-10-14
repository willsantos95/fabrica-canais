# Workflows n8n — Fase 1

| Arquivo | O que faz |
| --- | --- |
| `factory.produce.json` | Pega o próximo tema da fila, escreve roteiro e shotlist com o Claude, manda o worker narrar, gerar imagens e montar, e avisa no WhatsApp com os links |
| `factory.error.json` | Quando o `factory.produce` falha: marca o vídeo como `failed`, devolve o tema ao fim da fila e manda alerta no WhatsApp |
| `teste-worker.json` | Teste simples do worker (Fase 0) |

Os JSON são gerados por `build_workflows.py`, que embute os prompts de `prompts/`. Depois de editar um prompt, rode `python n8n/build_workflows.py` e reimporte.

## Antes de importar

1. **Banco:** rode `db/migrations/003_execucao_n8n.sql` (pode rodar mais de uma vez).
2. **Worker:** no `.env` do EasyPanel, preencha `GEMINI_API_KEY` e faça o deploy.
3. **n8n:** a variável `WEBHOOK_URL` do n8n precisa ser o endereço público (`https://n8n.relampagodeofertas.shop/`). É ela que forma a URL de retomada que o worker chama no fim de cada job.

## Credenciais (crie no n8n com estes nomes)

| Nome | Tipo | Configuração |
| --- | --- | --- |
| `Fabrica DB` | Postgres | Host interno do Postgres (aba Credentials do EasyPanel), banco, usuário, senha, SSL desligado |
| `Fabrica Worker` | Header Auth | Name `Authorization`, Value `Bearer <WORKER_API_TOKEN>` |
| `Fabrica Callback` | Header Auth | Name `Authorization`, Value `Bearer <CALLBACK_TOKEN>` |
| `Anthropic API` | Header Auth | Name `x-api-key`, Value `<sua chave da API da Anthropic>` |
| `Evolution API` | Header Auth | Name `apikey`, Value `<chave da sua Evolution API>` |

Ao importar, abra cada nó que mostrar alerta de credencial e selecione a credencial correspondente.

## Ajustes depois de importar

**`factory.produce` → nó `Config`:**
- `evolution_url`: endereço da sua Evolution API (sem barra no final)
- `evolution_instance`: nome da instância do WhatsApp
- `anthropic_model`: modelo do Claude para roteiro e shotlist (padrão `claude-sonnet-5-5`)

**`factory.error` → nó `Config`:** os mesmos dados da Evolution e `alert_number` (seu WhatsApp com DDI e DDD).

**Ligar o workflow de erro:** abra `factory.produce` → **Settings** → **Error Workflow** → escolha `factory.error`. Sem isso, falhas não geram alerta.

O nó `WhatsApp: avisar` usa o formato da **Evolution API v2** (`/message/sendText/{instância}` com `number` e `text`). Na v1, o corpo seria `{ number, textMessage: { text } }`.

## Primeira execução

1. Execute `factory.produce` manualmente (**Test workflow**).
2. Etapas e tempos esperados:
   - roteiro com pesquisa: 2 a 5 min;
   - shotlist: 1 a 2 min;
   - narração: 1 a 2 min;
   - 50 imagens: 3 a 8 min;
   - montagem de ~10 min de vídeo: 10 a 20 min em 2 núcleos (bem menos com um worker no seu PC).
3. Nos nós `Aguardar …` a execução fica em espera; o n8n retoma sozinho quando o worker termina. Dá para acompanhar em **Executions**.
4. No fim chega no WhatsApp o preview em 480p, o vídeo final e a legenda, com links válidos por 48 h.
5. Fase 1: baixe o `FINAL.mp4` e o `FINAL.srt` e publique pelo YouTube Studio.

Quando estiver satisfeito com o resultado, ative o nó `Agenda diária` (desativado por padrão, roda às 2h) e ative o workflow.

## Onde cada coisa fica

- Estado de cada vídeo: tabela `videos` (`status`, `spec`, `error`, `n8n_execution_id`)
- Arquivos: MinIO em `videos/<video_id>/` (áudio, imagens, `FINAL.mp4`, `FINAL.srt`, `preview.mp4`, `video_spec.json`)
- Checagens: tabela `checks`; custo por vídeo: view `video_costs` (preenchida a partir da Fase 2)
