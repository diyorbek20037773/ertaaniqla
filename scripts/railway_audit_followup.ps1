# One-off follow-up after the Railway audit fixes (D-075/D-076). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File scripts\railway_audit_followup.ps1
# Works from cmd.exe too (it starts PowerShell). Railway builds the `master` branch.
# Steps: fast-forward master -> media volume -> wait for the new deploy -> apply seed text once
# -> remove audit test messages (asks first) -> checks. Safe to re-run.
param(
    [string]$Service = "ertaaniqla",
    [string]$Url = "https://ertaaniqla-production.up.railway.app"
)
$ErrorActionPreference = "Continue"
$env:Path = "$(npm prefix -g);$env:Path"
if (-not (Get-Command railway -ErrorAction SilentlyContinue)) { throw "Railway CLI not found (npm install -g @railway/cli)" }

function Step($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
# railway ssh joins the words and runs them in the container's shell (cwd /app). No quotes are
# sent: Windows PowerShell 5.1 mangles embedded double quotes of native arguments.
function Remote($cmd) {
    Write-Host "> $cmd" -ForegroundColor DarkGray
    $words = $cmd -split " "
    railway ssh --service $Service -- @words 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "   (failed, exit $LASTEXITCODE)" -ForegroundColor Red }
}
# Python for `manage.py shell`, shipped as base64 so it survives both shells unchanged.
function RemotePython($code) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($code))
    Remote "echo $b64 | base64 -d | python manage.py shell"
}

Step "0. Deploy the fixes: fast-forward master (Railway builds master)"
git fetch origin
git push origin HEAD:master
if ($LASTEXITCODE -ne 0) { throw "push to master failed (not a fast-forward?) - merge by hand" }

Step "1. Media volume at /srv/media"
$volumes = railway volume list 2>&1 | Out-String
if ($volumes -match "/srv/media") {
    Write-Host "volume already mounted at /srv/media"
} else {
    railway volume add --service $Service --mount-path /srv/media
}

Step "2. Waiting for the new deploy (robots.txt must say 'Disallow: /'), max 20 min"
$deadline = (Get-Date).AddMinutes(20)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        $robots = (Invoke-WebRequest "$Url/robots.txt" -UseBasicParsing -TimeoutSec 15).Content
        if ($robots -match "Disallow: /\s*$") { $ready = $true; break }
    } catch { }
    Write-Host "  not yet... $(Get-Date -Format HH:mm:ss)"
    Start-Sleep -Seconds 20
}
if (-not $ready) {
    Write-Host "New deploy not live yet. Check Railway (Deploy / Apply changes), then run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "new deploy is live" -ForegroundColor Green

Step "3. Apply the new seed text once (no CMS edits exist yet - never do this later)"
Remote "python manage.py seed_content"
Remote "python manage.py regenerate_social_images"
Remote "python manage.py sync_site"

Step "4. Audit test messages"
$models = "from apps.feedback.models import FeedbackSubmission as F`nfrom apps.faq.models import Question as Q`n"
RemotePython ($models + "print('feedback:', F.objects.filter(text__contains='AUDIT TEST').count(), 'questions:', Q.objects.filter(text__contains='AUDIT TEST').count())")
$answer = Read-Host "Delete these AUDIT TEST rows? (yes/no)"
if ($answer -eq "yes") {
    RemotePython ($models + "print(F.objects.filter(text__contains='AUDIT TEST').delete(), Q.objects.filter(text__contains='AUDIT TEST').delete())")
} else {
    Write-Host "skipped"
}

Step "5. Checks"
function Check($name, $ok) {
    if ($ok) { Write-Host "  OK   $name" -ForegroundColor Green } else { Write-Host "  FAIL $name" -ForegroundColor Red }
}
try {
    $landing = Invoke-WebRequest "$Url/uz/" -UseBasicParsing
    Check "X-Robots-Tag noindex" ($landing.Headers["X-Robots-Tag"] -match "noindex")
    $page = (Invoke-WebRequest "$Url/uz/ayollar/ogohlik/kokrak-bezi-saratoni/" -UseBasicParsing).Content
    Check "no 'localhost' in page" (([regex]::Matches($page, "localhost")).Count -eq 0)
    Check "canonical on the public host" ($page -match [regex]::Escape("rel=`"canonical`" href=`"$Url/"))
    $og = [regex]::Match($page, 'property="og:image" content="([^"]+)"').Groups[1].Value
    $ogStatus = 0
    if ($og) { try { $ogStatus = (Invoke-WebRequest $og -UseBasicParsing).StatusCode } catch { } }
    Check "OG image 200 ($og)" ($ogStatus -eq 200)
    $privacy = 0
    try { $privacy = (Invoke-WebRequest "$Url/uz/maxfiylik-siyosati/" -UseBasicParsing).StatusCode } catch { }
    Check "privacy policy page 200" ($privacy -eq 200)
    $dir = (Invoke-WebRequest "$Url/uz/ayollar/qayerga-murojaat/" -UseBasicParsing).Content
    Check "directory has institutions" ($dir -notmatch "hozircha yo")
    $admin = 0
    try { $admin = (Invoke-WebRequest "$Url/django-admin/login/" -UseBasicParsing).StatusCode } catch { $admin = $_.Exception.Response.StatusCode.value__ }
    Check "/django-admin/ is off (404)" ($admin -eq 404)
} catch {
    Write-Host "check failed: $_" -ForegroundColor Red
}
Write-Host ""
Write-Host "Done. Next: run the Chrome extension audit again (docs/CHROME_AUDIT_PROMPT.md)."
