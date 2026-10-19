param([ValidateSet("all", "week4", "week5")][string]$Only = "all")
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot)
$env:PYTHONIOENCODING = "utf-8"

function Start-Server([int]$Parallel, [int]$Unified = 0) {
    $script = Join-Path $PSScriptRoot "serve_llamacpp.ps1"
    $log = "traces\llamacpp-np$Parallel.log"
    $p = Start-Process powershell -PassThru -WindowStyle Hidden -RedirectStandardError $log `
        -ArgumentList "-NoProfile", "-File", $script, "-Parallel", $Parallel, "-Unified", $Unified
    for ($i = 0; $i -lt 300; $i++) {
        try { if ((Invoke-WebRequest http://127.0.0.1:8080/health -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { return $p } } catch {}
        Start-Sleep 1
    }
    throw "llama-server did not start; see $log"
}

function Stop-Server($p) {
    Get-Process llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
    if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force }
    Start-Sleep 3
}

function Run([string]$Config, [string]$Tasks, [string]$Out, [int]$Concurrency = 1) {
    Write-Host "`n=== $Out ($Config, concurrency $Concurrency) ==="
    uv run agentic-profiling $Config $Tasks --out $Out --concurrency $Concurrency | Tee-Object -Append "$Out.log"
}

New-Item -ItemType Directory -Force traces\week4, traces\week5 | Out-Null
ollama stop llama3.2:3b-ctx8k 2>$null
Stop-Server $null

if ($Only -in "all", "week4") {
    $srv = Start-Server 1
    foreach ($w in "gsm8k", "hotpotqa") {
        Run configs/llamacpp.yaml         "tasks/$($w)_100.yaml" "traces/week4/$w-cache-on"
        Run configs/llamacpp-nocache.yaml "tasks/$($w)_100.yaml" "traces/week4/$w-cache-off"
    }
    Stop-Server $srv
    uv run agentic-compare week4-gsm8k traces/week4/gsm8k-cache-on traces/week4/gsm8k-cache-off
    uv run agentic-compare week4-hotpotqa traces/week4/hotpotqa-cache-on traces/week4/hotpotqa-cache-off
}

if ($Only -in "all", "week5") {
    foreach ($n in 1, 2, 4, 8) {
        $srv = Start-Server $n 16384
        Run configs/llamacpp.yaml tasks/gsm8k_100.yaml "traces/week5/gsm8k-c$n" $n
        Stop-Server $srv
    }
    $srv = Start-Server 1
    Run configs/llamacpp-window2.yaml tasks/hotpotqa_100.yaml traces/week5/hotpotqa-window2
    Stop-Server $srv
    uv run agentic-compare week5-concurrency traces/week5/gsm8k-c1 traces/week5/gsm8k-c2 traces/week5/gsm8k-c4 traces/week5/gsm8k-c8
    uv run agentic-compare week5-truncation traces/week4/hotpotqa-cache-on traces/week5/hotpotqa-window2
}
