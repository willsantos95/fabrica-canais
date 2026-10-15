# Workflows n8n — Fase 1

| Arquivo | O que faz |
| --- | --- |
| `factory.produce.json` | Pega o próximo tema da fila, escreve roteiro e shotlist com a OpenAI (com busca na web), manda o worker narrar, gerar imagens e montar, e avisa no WhatsApp com os links |
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
| `OpenAI API` | Header Auth | Name `Authorization`, Value `Bearer <sua chave da API da OpenAI>` |
| `Evolution API` | Header Auth | Name `apikey`, Value `<chave da sua Evolution API>` |

Ao importar, abra cada nó que mostrar alerta de credencial e selecione a credencial correspondente.

## Ajustes depois de importar

**`factory.produce` → nó `Config`:**
- `evolution_url`: endereço da sua Evolution API (sem barra no final)
- `evolution_instance`: nome da instância do WhatsApp
- `openai_model`: modelo da OpenAI para roteiro e shotlist (padrão `gpt-5.5`)
- `reasoning_effort`: `low`, `medium` (padrão) ou `high`. Mais alto = roteiro mais cuidadoso, mais lento e mais caro

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

## Fase 2 — pacote, aprovação e publicação

Fluxos criados no n8n (código do SDK em `n8n/sdk/`, gerado por `n8n/build_fase2.py`):

| Fluxo | Gatilho | O que faz |
| --- | --- | --- |
| `factory.package` | chamado pelo `factory.produce` (ou manual: pega o último vídeo pronto) | job `package` no worker: 3 Shorts, 3 thumbnails, título, descrição com capítulos e fontes, tags. Manda no WhatsApp os links, os títulos e as thumbnails, com as opções de resposta |
| `factory.approval` | webhook `POST /webhook/fabrica-aprovacao` (Evolution, evento `MESSAGES_UPSERT`) | `1` aprova e chama o `factory.publish`; `2 motivo` rejeita; `3 N` escolhe a thumbnail; `4 N` escolhe o título |
| `factory.publish` | chamado pela aprovação | abre sessões de upload no YouTube com a credencial OAuth do n8n; o worker (`youtube_upload`) envia os arquivos direto do MinIO. Vídeo privado com `publishAt` no próximo horário livre de `schedule.publish_times`; Shorts nos dias seguintes em `schedule.shorts_time` (padrão 12:00); thumbnail por `thumbnails.set` |

Nenhuma etapa da Fase 2 chama a OpenAI: título, descrição, capítulos e tags saem do `video_spec`.

**Evolution:** na instância usada pela fábrica, configure o webhook para `https://<seu-n8n>/webhook/fabrica-aprovacao` com o evento `MESSAGES_UPSERT`. A instância só aceita um webhook; se ela já atende outro fluxo, use uma instância separada para a fábrica.

**YouTube:**
- Enquanto o projeto da API não passar pela auditoria do YouTube, os vídeos enviados pela API ficam travados como privados, mesmo com `publishAt`.
- Thumbnail personalizada exige o canal verificado por telefone.
- A credencial `YouTube account` precisa ter sido autorizada escolhendo o canal Career Levels (conta de marca), não o canal pessoal.

**Se a publicação falhar no meio:** o vídeo já foi marcado como `scheduled`. Para tentar de novo, volte o status e responda `1` outra vez:

```sql
UPDATE videos SET status = 'awaiting_approval' WHERE id = '<video_id>';
```

## Clipes para TikTok/Reels (`factory.clips`)

Disparado pelo `factory.approval` logo depois do `1` (ou manual: "Testar com o último vídeo"). Sem aprovação e sem custo de API.

- Job `clips` no worker: um clipe por nível, em 9:16, remontado a partir das imagens do vídeo (cena num quadrado no meio, fundo desfocado), com o áudio já mixado do vídeo final, título fixo no topo, legenda palavra por palavra e cartão final "Full video on YouTube". Nível com até 75 s vai inteiro; mais longo é cortado no fim da última frase que cabe em 60 s.
- No WhatsApp chegam, para cada clipe, duas mensagens: o link (válido por 7 dias) e a legenda pronta para colar. A publicação no TikTok é manual.
- Os clipes ficam em `assets` com `kind = 'short'` e `meta.platform = 'tiktok'`.
