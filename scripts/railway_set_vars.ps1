# Sets the web service variables on the Railway demo host (D-070).
# Postgres and Redis generate their own variables; only the web service needs these.
# Secrets are generated here and are NEVER overwritten once set (rotating PII_ENCRYPTION_KEYS
# would make stored PII unreadable).
#
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts\railway_set_vars.ps1
param(
    [string]$Service = "ertaaniqla",
    [string]$PostgresService = "Postgres",
    [string]$RedisService = "Redis",
    [string]$Domain = "ertaaniqla-production.up.railway.app"
)
# Not "Stop": in Windows PowerShell 5.1 any stderr line of a native command (railway prints
# "No linked project" there) becomes a terminating error. Exit codes are checked explicitly.
$ErrorActionPreference = "Continue"

function New-UrlSafeKey([int]$Bytes) {
    $buf = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($buf)
    return [Convert]::ToBase64String($buf).Replace("+", "-").Replace("/", "_")
}

# npm's global bin dir is often missing from PATH on Windows; add it for this session
$npmBin = (npm prefix -g)
if ($npmBin -and (($env:Path -split ';') -notcontains $npmBin)) { $env:Path = "$npmBin;$env:Path" }

if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
    Write-Host "Railway CLI topilmadi, o'rnatilmoqda..."
    npm install -g @railway/cli
}

railway whoami *> $null
if ($LASTEXITCODE -ne 0) { railway login }

railway status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Loyihani tanlang (ertaaniqla joylashgan project):"
    railway link
    if ($LASTEXITCODE -ne 0) { throw "railway link bajarilmadi" }
}

# Existing variables of the web service, so secrets are only created once
$existing = @{}
$json = railway variable list --service $Service --json 2>$null
if ($LASTEXITCODE -ne 0) { throw "'$Service' servisi topilmadi. Railway'dagi nomini -Service bilan bering." }
$parsed = $json | Out-String | ConvertFrom-Json
if ($parsed -is [array]) {
    $parsed | ForEach-Object { $existing[$(if ($_.name) { $_.name } else { $_.key })] = $true }
} elseif ($parsed) {
    $parsed.PSObject.Properties | ForEach-Object { $existing[$_.Name] = $true }
}

$vars = [ordered]@{
    # ${{...}} are Railway references, resolved on Railway (single quotes: no PowerShell expansion)
    "DATABASE_URL"                = '${{' + $PostgresService + '.DATABASE_URL}}'
    "REDIS_URL"                   = '${{' + $RedisService + '.REDIS_URL}}'
    "CELERY_BROKER_URL"           = '${{' + $RedisService + '.REDIS_URL}}/1'
    "CELERY_RESULT_BACKEND"       = '${{' + $RedisService + '.REDIS_URL}}/2'
    # no worker service on the demo host: tasks run inline in the web process
    "CELERY_TASK_ALWAYS_EAGER"    = "True"
    "SITE_BASE_URL"               = "https://$Domain"
    "ENVIRONMENT"                 = "railway-demo"
    "GUNICORN_WORKERS"            = "2"
    # pre-deploy hook does not run on Railway (D-073): the web role migrates on start
    "RUN_MIGRATIONS_ON_START"     = "1"
    # demo only (D-075): idempotent seed tree + sample institutions on every start
    "SEED_DEMO_ON_START"          = "1"
    # demo host must not be indexed (EA-14)
    "ROBOTS_NOINDEX"              = "true"
    # no nginx in front: Django serves public /media/ (EA-04); mount a volume at /app/media
    "SERVE_MEDIA"                 = "true"
    # no SMTP on the demo host: moderator e-mails go to the log (EA-02)
    "EMAIL_URL"                   = "consolemail://"
    # Cloudflare's official always-pass test keys; replace with real ones before going live
    "TURNSTILE_SITE_KEY"          = "1x00000000000000000000AA"
    "TURNSTILE_SECRET_KEY"        = "1x0000000000000000000000000000000AA"
}
if (-not $existing.ContainsKey("DJANGO_SECRET_KEY")) { $vars["DJANGO_SECRET_KEY"] = New-UrlSafeKey 50 }
if (-not $existing.ContainsKey("PII_ENCRYPTION_KEYS")) { $vars["PII_ENCRYPTION_KEYS"] = New-UrlSafeKey 32 }  # Fernet key

# Railway CLI v5: `variable set KEY=VALUE...` in one call → one redeploy
$cliArgs = @("variable", "set", "--service", $Service)
foreach ($k in $vars.Keys) { $cliArgs += "$k=$($vars[$k])" }
& railway @cliArgs
if ($LASTEXITCODE -ne 0) { throw "railway variable set xato bilan tugadi" }

Write-Host ""
Write-Host "Tayyor. O'rnatilgan kalitlar:" ($vars.Keys -join ", ")
if ($existing.ContainsKey("PII_ENCRYPTION_KEYS")) { Write-Host "DJANGO_SECRET_KEY / PII_ENCRYPTION_KEYS allaqachon bor edi - o'zgartirilmadi." }
Write-Host "Endi Railway canvas'da 'Deploy' (Apply changes) tugmasini bosing - Redis ham ishga tushadi."
