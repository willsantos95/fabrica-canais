# Teste de geração de música no PC (ACE-Step 1.5, só processador)
# ------------------------------------------------------------------
# Instala o ACE-Step 1.5 numa pasta própria, sobe a API local, gera faixas
# instrumentais curtas e mede quanto tempo cada uma leva.
#
# Como rodar (PowerShell, não precisa ser administrador):
#   powershell -ExecutionPolicy Bypass -File .\teste-musica-pc.ps1
# Opções:
#   -Pasta C:\fabrica-musica   onde instalar (padrão)
#   -Segundos 60               duração de cada faixa de teste
#   -Faixas 2                  quantas faixas gerar
#   -Dispositivo cpu           cpu (padrão) ou auto (deixa o ACE-Step escolher)
#
# A primeira execução baixa as dependências e os modelos (vários GB): leva um tempo.
# As faixas ficam em <Pasta>\saida. Nada é enviado para fora do PC.
# Na geração: "." = ainda processando; "~" = a API demorou a responder (normal com CPU no limite).

param(
  [string]$Pasta = "C:\fabrica-musica",
  [int]$Segundos = 60,
  [int]$Faixas = 2,
  [ValidateSet("cpu", "auto")][string]$Dispositivo = "cpu"
)

$ErrorActionPreference = "Stop"
$Repo = Join-Path $Pasta "ACE-Step-1.5"
$Saida = Join-Path $Pasta "saida"
$Log = Join-Path $Pasta "api.log"
$Api = "http://127.0.0.1:8001"

function Etapa($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "   $t" -ForegroundColor Green }
function Aviso($t) { Write-Host "   $t" -ForegroundColor Yellow }
# "uv run" abre um python filho; matar só o uv deixa a API viva segurando a porta. Mata a árvore toda.
function Parar-Arvore($procId) { if ($procId) { & taskkill /PID $procId /T /F 2>$null | Out-Null } }
function Liberar-Porta($porta) {
  $donos = Get-NetTCPConnection -LocalPort $porta -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($d in $donos) { Aviso "porta $porta ocupada pelo processo $d (API de um teste anterior), encerrando..."; Parar-Arvore $d }
  if ($donos) { Start-Sleep -Seconds 3 }
}

New-Item -ItemType Directory -Force -Path $Pasta, $Saida | Out-Null

# ---------------------------------------------------------------- 1. ferramentas
Etapa "1/5 Conferindo git e uv"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw "Git não encontrado. Instale em https://git-scm.com/download/win e rode o script de novo."
}
Ok "git ok"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Aviso "uv não encontrado, instalando (gerenciador de Python usado pelo ACE-Step)..."
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw "uv não ficou disponível. Feche e abra o PowerShell e rode de novo." }
}
Ok "uv ok"

# ---------------------------------------------------------------- 2. ACE-Step
Etapa "2/5 Baixando e instalando o ACE-Step 1.5 (só na primeira vez)"
if (-not (Test-Path (Join-Path $Repo ".git"))) {
  git clone --depth 1 https://github.com/ACE-Step/ACE-Step-1.5.git $Repo
} else {
  Ok "já baixado em $Repo"
}
Push-Location $Repo
try {
  uv sync
  if ($LASTEXITCODE -ne 0) { throw "uv sync falhou (veja as mensagens acima)." }
} finally { Pop-Location }
Ok "dependências instaladas"

# ---------------------------------------------------------------- 3. API local
Etapa "3/5 Subindo a API local do ACE-Step ($Dispositivo)"
# modelo turbo (rápido), sem o modelo de linguagem auxiliar (economiza memória e tempo)
$env:ACESTEP_CONFIG_PATH = "acestep-v15-turbo"
$env:ACESTEP_INIT_LLM = "false"
$env:ACESTEP_DEVICE = $Dispositivo
$env:ACESTEP_USE_FLASH_ATTENTION = "false"
$env:ACESTEP_API_HOST = "127.0.0.1"
$env:ACESTEP_API_PORT = "8001"

$cpu = (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$ram = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
Ok "Processador: $cpu · RAM: $ram GB"

Liberar-Porta 8001
$server = Start-Process -FilePath "uv" -ArgumentList "run", "acestep-api" -WorkingDirectory $Repo `
  -RedirectStandardOutput $Log -RedirectStandardError "$Log.err" -PassThru -WindowStyle Hidden

$inicio = Get-Date
$pronto = $false
Write-Host "   esperando a API (o primeiro início baixa os modelos; pode levar 10-30 min)..." -NoNewline
while (((Get-Date) - $inicio).TotalMinutes -lt 45) {
  if ($server.HasExited) { break }
  try {
    $h = Invoke-RestMethod -Uri "$Api/health" -TimeoutSec 5
    if ($h.data.status -eq "ok") { $pronto = $true; break }
  } catch { }
  Write-Host "." -NoNewline
  Start-Sleep -Seconds 10
}
Write-Host ""
if (-not $pronto) {
  Aviso "A API não subiu. Últimas linhas do log:"
  if (Test-Path "$Log.err") { Get-Content "$Log.err" -Tail 30 }
  if (-not $server.HasExited) { Parar-Arvore $server.Id }
  throw "API do ACE-Step não respondeu. Mande o arquivo $Log.err para análise."
}
Ok ("API pronta em {0:N0} s" -f ((Get-Date) - $inicio).TotalSeconds)

# ---------------------------------------------------------------- 4. gerar
Etapa "4/5 Gerando $Faixas faixa(s) de $Segundos s"
$estilos = @(
  "bossa nova lofi, soft nylon guitar, warm Rhodes piano, brushed drums, vinyl crackle, light rain, relaxing, 80 bpm, instrumental",
  "calm lofi hip hop for studying, mellow piano chords, soft bass, dusty drums, cozy cafe ambience, instrumental"
)
$resultados = @()
try {
  for ($i = 0; $i -lt $Faixas; $i++) {
    $estilo = $estilos[$i % $estilos.Count]
    $body = @{
      prompt = $estilo
      lyrics = "[Instrumental]"
      audio_duration = $Segundos
      batch_size = 1
      inference_steps = 8
      thinking = $false
      use_cot_caption = $false
      use_cot_language = $false
      audio_format = "mp3"
    } | ConvertTo-Json
    $t0 = Get-Date
    $sub = Invoke-RestMethod -Method Post -Uri "$Api/release_task" -ContentType "application/json" -Body $body -TimeoutSec 120 -DisableKeepAlive
    $taskId = $sub.data.task_id
    Write-Host ("   faixa {0}: tarefa {1}" -f ($i + 1), $taskId) -NoNewline

    $res = $null
    while (((Get-Date) - $t0).TotalMinutes -lt 60) {
      Start-Sleep -Seconds 10
      if ($server.HasExited) {
        Aviso "a API do ACE-Step fechou no meio da geração. Últimas linhas do log:"
        if (Test-Path "$Log.err") { Get-Content "$Log.err" -Tail 40 }
        throw "API encerrada durante a faixa $($i + 1). Mande o arquivo $Log.err."
      }
      # durante o processamento pesado a API pode demorar ou derrubar a conexão: tenta de novo
      try {
        $q = Invoke-RestMethod -Method Post -Uri "$Api/query_result" -ContentType "application/json" `
          -Body (@{ task_id_list = @($taskId) } | ConvertTo-Json) -TimeoutSec 120 -DisableKeepAlive
      } catch {
        Write-Host "~" -NoNewline
        continue
      }
      $item = $q.data | Select-Object -First 1
      if ($item.status -eq 1) { $res = $item; break }
      if ($item.status -eq 2) { throw "a geração falhou: $($item.result)" }
      Write-Host "." -NoNewline
    }
    Write-Host ""
    if (-not $res) { throw "passou de 60 minutos sem terminar (veja $Log.err)" }
    $seg = ((Get-Date) - $t0).TotalSeconds

    $r = $res.result | ConvertFrom-Json
    if ($r -is [array]) { $r = $r[0] }
    $arquivo = Join-Path $Saida ("teste_{0:yyyyMMdd_HHmmss}_{1}.mp3" -f (Get-Date), ($i + 1))
    Invoke-WebRequest -Uri ($Api + $r.file) -OutFile $arquivo -TimeoutSec 300 -DisableKeepAlive -UseBasicParsing
    $resultados += [pscustomobject]@{ Faixa = $i + 1; Segundos_audio = $Segundos; Segundos_gerando = [math]::Round($seg); Arquivo = $arquivo }
    Ok ("pronta em {0:N0} s -> {1}" -f $seg, $arquivo)
  }
} finally {
  # ---------------------------------------------------------------- 5. resumo
  Parar-Arvore $server.Id
  Liberar-Porta 8001
}

Etapa "5/5 Resultado"
$resultados | Format-Table -AutoSize
if ($resultados.Count) {
  # a 1ª faixa inclui o aquecimento do modelo; a média usa as demais quando houver
  $base = if ($resultados.Count -gt 1) { $resultados | Select-Object -Skip 1 } else { $resultados }
  $media = ($base | Measure-Object -Property Segundos_gerando -Average).Average
  $porMinuto = $media / ($Segundos / 60)
  $faixa4min = $porMinuto * 4 / 60
  $hora = [math]::Floor(60 / [math]::Max($faixa4min, 0.01))
  Write-Host ("   ~{0:N0} s de processamento por minuto de música" -f $porMinuto)
  Write-Host ("   uma faixa de 4 min levaria ~{0:N1} min; ~{1} faixas por hora" -f $faixa4min, $hora)
  Write-Host ("   para um mix de 2 h (~30 faixas): ~{0:N1} h de PC ligado" -f (30 * $faixa4min / 60))
  Write-Host ""
  Write-Host "Ouça as faixas em $Saida e me mande este resumo." -ForegroundColor Cyan
}
