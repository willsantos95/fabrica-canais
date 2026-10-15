# Fábrica de Canais — Fase 0 (fundação)

Base da fábrica descrita no SDD: banco, contratos e worker de render.
O canal piloto é o **Career Levels**.

```
fabrica-canais/
├── db/migrations/        001_init.sql (10 tabelas + funções) · 002_seed_career_levels.sql
├── contracts/            JSON Schema do video_spec e da config do canal + exemplos
├── worker/               API FastAPI + fila RQ + ffmpeg (Ken Burns, montagem, Shorts, thumbnails, checagens)
├── deploy/               compose do servidor (EasyPanel) e do worker no seu PC
└── n8n/                  workflow de teste do worker + webhook de callback
```

## O que já foi testado

- Migrations aplicadas em Postgres 16 com pgvector; `claim_next_topic('career-levels')` tira o próximo tema da fila.
- Os exemplos validam contra os dois JSON Schemas.
- Teste de ponta a ponta do worker (`worker/tests/smoke_test.py`), com armazenamento local e com S3: vídeo 1080p montado a partir de imagens e áudio, legenda SRT, loudness medido em −14 LUFS, Short vertical com legenda palavra por palavra e thumbnail aprovada no teste de legibilidade.
- API: `/health`, autenticação por token, criação de job, idempotência (mesmo `idempotency_key` não duplica) e consulta de status.

**Não testado aqui** (sem acesso de rede no ambiente de construção): `edge-tts`, `faster-whisper` (baixa o modelo na primeira execução) e o build da imagem Docker. Valide os três no servidor seguindo o passo 5.

## Implantação no EasyPanel

### 1. Banco
No Postgres do EasyPanel (precisa da extensão **pgvector**; a imagem `pgvector/pgvector:pg16` já traz):

```bash
psql "$DATABASE_URL" -f db/migrations/001_init.sql
psql "$DATABASE_URL" -f db/migrations/002_seed_career_levels.sql
```

Depois edite a config do canal (`youtube_channel_id`, número do WhatsApp em `approval.to`):

```sql
UPDATE channels SET config = jsonb_set(config, '{approval,to}', '"55DDDNUMERO"') WHERE slug = 'career-levels';
```

`script_embedding` usa 1536 dimensões (ex.: `text-embedding-3-small` da OpenAI). Se usar outro modelo, ajuste o tamanho em `001_init.sql` antes de rodar.

### 2. Repositório
Suba esta pasta para um repositório privado no GitHub. No EasyPanel, crie um app do tipo **Compose** apontando para `deploy/docker-compose.yml`.

### 3. Variáveis
Copie `deploy/.env.example` para `deploy/.env` e preencha os segredos (`openssl rand -hex 24`).

### 4. Domínios no EasyPanel
- `render.relampagodeofertas.shop` → serviço `api`, porta 8000
- `arquivos.relampagodeofertas.shop` → serviço `minio`, porta 9000 (links de preview)
- Console do MinIO (porta 9001): só se precisar, de preferência sem domínio público

### 5. Teste no servidor
```bash
curl https://render.relampagodeofertas.shop/health
# {"ok":true,"redis":true,"storage":true,...}
```
Importe `n8n/teste-worker.json` no n8n, troque os dois tokens e execute: o job de thumbnail deve voltar pelo webhook `render-callback` com `status: succeeded`.

Para validar voz e transcrição, dentro do container `render`:
```bash
python -c "from app import tts; from pathlib import Path; print(tts.synthesize('Every level counts.', 'en-US-AndrewNeural', Path('/tmp/t.mp3'))[:3])"
python -c "from app import align; from pathlib import Path; print(align.transcribe(Path('/tmp/t.mp3'), 'en')[:3])"
```

### 6. Auditoria da API do YouTube
Uploads pela API ficam travados como privados até o projeto passar pela auditoria do YouTube. Peça já nesta fase: no Google Cloud, crie o projeto, ative a YouTube Data API v3, configure a tela de consentimento OAuth e envie o formulário de auditoria de API do YouTube. Enquanto isso, a Fase 1 publica pelo YouTube Studio.

## Workers no seu PC (mais velocidade)

A fila fica no servidor; qualquer máquina com o worker puxa jobs dela. Ligue o PC e ele ajuda; desligue e o servidor continua sozinho.

1. Instale a **Tailscale** no servidor e no PC (rede privada entre os dois, sem expor o Redis na internet).
2. No `.env` do servidor, troque `REDIS_BIND` pelo IP da Tailscale do servidor (`100.x.y.z`) e reinicie o compose.
3. No PC (Docker Desktop), copie `deploy/.env.local.example` para `deploy/.env.local`, preencha e rode:
   ```bash
   cd deploy
   docker compose -f docker-compose.local-worker.yml --env-file .env.local up -d --build
   ```
4. O log do worker mostra `pc-...` pegando jobs.

**O que vale rodar no PC:** `assemble` (Ken Burns e montagem, o mais pesado), `shorts` e `align` (Whisper). **O que fica no servidor:** API, fila, MinIO, n8n, banco. Neste ambiente de teste com 2 núcleos, o Ken Burns levou ~0,9 s por segundo de vídeo; um PC de 8 núcleos deve ser bem mais rápido. Meça na Fase 1.

Ajustes de velocidade (no `.env`): `CLIP_WORKERS` (planos renderizados em paralelo), `X264_PRESET=ultrafast` (~40% mais rápido, arquivo maior) e `KB_UPSCALE=1.5` (mais rápido, movimento um pouco menos suave).

## API do worker

Todas as rotas, menos `/health`, exigem `Authorization: Bearer <WORKER_API_TOKEN>`.

| Rota | `input` principal | Resultado |
| --- | --- | --- |
| `POST /jobs/tts` | `text`, `voice`, `rate`, `name` | `url`, `duration_s`, `words` |
| `POST /jobs/align` | `audio_url`, `language`, `expected_text` | `words`, `match_ratio` |
| `POST /jobs/kenburns` | `image_url`, `duration_s`, `mode`, `text_overlay` | `url` |
| `POST /jobs/assemble` | `spec_url`, `loudness_lufs`, `music_url`, `music_volume_db`, `min_duration_s` | `outputs`, `spec_url`, `checks`, `words` |
| `POST /jobs/shorts` | `final_url`, `spec_url` ou `words`, `candidates` | `shorts[]` |
| `POST /jobs/thumbnail` | `options[{image_url, lines}]`, `brand` | `thumbnails[]` com checagem |
| `POST /jobs/checks` | `media_url`, `stage`, `expect_lufs`, `min_duration_s` | `checks[]` |
| `GET /jobs/{id}` | — | status e resultado |
| `POST /files/presign` | `url`, `expires_s` | link temporário |

Corpo de todo job: `{video_id, idempotency_key, callback_url, input}`. O callback recebe `{status, result | error, video_id, type, idempotency_key, elapsed_s}` com `Authorization: Bearer <CALLBACK_TOKEN>`.

Para `assemble`, cada bloco do `video_spec` precisa de `audio.url` (e de preferência `audio.words`) e cada plano de `image.url` (ou `clip.url` com `motion.mode = "ai"`).

## Teste local do worker

```bash
cd worker
pip install -r requirements.txt
STORAGE=local LOCAL_STORAGE_ROOT=/tmp/fab WORK_DIR=/tmp/fab-work \
  python -m tests.smoke_test ../contracts/examples/demo.video_spec.json
```

## Próximo passo: Fase 1

Workflows n8n `factory.orchestrator`, `factory.script` (OpenAI), `factory.voice`, `factory.visuals` (Nano Banana) e `factory.assemble`, produzindo o primeiro vídeo real do Career Levels com Ken Burns em todos os planos e upload pelo Studio.
