param(
    [string]$RunTag = "self_20261113_v1",
    [switch]$SkipOffline,
    [switch]$ChecksOnly
)

$ErrorActionPreference = "Stop"
if ($RunTag -notmatch '^[A-Za-z0-9_-]+$') {
    throw "RunTag may contain only letters, digits, underscores, and hyphens."
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Project .venv is missing. Follow README.md setup first."
}

function Invoke-PythonChecked {
    param([string[]]$Arguments)
    Write-Host "`n> python $($Arguments -join ' ')" -ForegroundColor Cyan
    & $python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed (exit $LASTEXITCODE): python $($Arguments -join ' ')"
    }
}

$offlineId = "submission_full_guide_$RunTag"
$qwenId = "submission_qwen_v2_$RunTag"
$mvpId = "suite-offline-$RunTag"
if (-not $SkipOffline) {
    if ((Test-Path -LiteralPath (Join-Path $projectRoot "outputs\$offlineId")) -or
        (Test-Path -LiteralPath (Join-Path $projectRoot "data\derived\$offlineId"))) {
        throw "Offline run path already exists. Choose a new -RunTag."
    }
}
if ((Test-Path -LiteralPath (Join-Path $projectRoot "outputs\$qwenId")) -or
    (Test-Path -LiteralPath (Join-Path $projectRoot "data\derived\$qwenId"))) {
    throw "Qwen run path already exists. Choose a new -RunTag."
}
if (-not $ChecksOnly -and (Test-Path -LiteralPath (Join-Path $projectRoot "outputs\mvp\$mvpId"))) {
    throw "Synthetic MVP run path already exists. Choose a new -RunTag."
}

try {
    $models = (Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 10).models.name
} catch {
    throw "Local Ollama is unavailable at 127.0.0.1:11434. Start Ollama and rerun."
}
if ($models -notcontains "qwen2.5:3b") {
    throw "Local Ollama model qwen2.5:3b is missing. Run: ollama pull qwen2.5:3b"
}

Invoke-PythonChecked @("-m", "src.cli", "self-test-phase2")
Invoke-PythonChecked @("-m", "src.cli", "baseline-self-test")
Invoke-PythonChecked @("-m", "src.cli", "agent-self-test")
Invoke-PythonChecked @("-m", "src.cli", "evaluation-self-test")
Invoke-PythonChecked @("-m", "src.cli", "phase6a-self-test")
Invoke-PythonChecked @("-m", "src.cli", "phase6b-self-test")
Invoke-PythonChecked @("-m", "src.mvp_demo", "self-test")
Invoke-PythonChecked @("-m", "src.offline_joint_comparison_v1", "self-test")
Invoke-PythonChecked @("-m", "src.offline_joint_comparison", "self-test")
Invoke-PythonChecked @("-m", "src.submission_full_guide", "self-test")
Invoke-PythonChecked @("-m", "src.submission_local_qwen", "self-test")
Invoke-PythonChecked @("-m", "src.submission_local_qwen_v2", "self-test")
Invoke-PythonChecked @("-m", "src.submission_local_qwen_v2", "plan")
Invoke-PythonChecked @("-m", "src.cli", "check-leakage", "--features", "data/derived/preprocessing/feature_view.csv", "--policy", "configs/field_policy.yaml", "--audit", "data/derived/preprocessing/leakage_audit.json")
Invoke-PythonChecked @("-m", "src.cli", "check-splits", "--manifest", "data/derived/preprocessing/split_manifest.json", "--expected", "10,10,30")
Invoke-PythonChecked @("-m", "submission.generate_figures")
Invoke-PythonChecked @("-m", "submission.generate_submission_figures")
Invoke-PythonChecked @("-m", "src.build_simulation_dashboard")
Invoke-PythonChecked @("-m", "submission.verify_package")

if ($ChecksOnly) {
    Write-Host "`nSoftware checks and Qwen sample plan passed; no prediction run was started." -ForegroundColor Green
    return
}

Invoke-PythonChecked @("-m", "src.mvp_demo", "run", "--run-id", $mvpId)

if (-not $SkipOffline) {
    Invoke-PythonChecked @("-m", "src.submission_full_guide", "predict", "--run-id", $offlineId)
    Invoke-PythonChecked @("-m", "src.submission_full_guide", "evaluate", "--run-id", $offlineId)
    Invoke-PythonChecked @("-m", "submission.verify_run_manifests", $offlineId)
} else {
    Write-Host "`nUsing the already recorded full offline run: outputs/submission_full_guide_20261112_v1" -ForegroundColor Yellow
}

Invoke-PythonChecked @("-m", "src.submission_local_qwen_v2", "predict", "--run-id", $qwenId)
Invoke-PythonChecked @("-m", "src.submission_local_qwen_v2", "evaluate", "--run-id", $qwenId)
Invoke-PythonChecked @("-m", "submission.verify_run_manifests", $qwenId)

Write-Host "`nCompleted. Public aggregate results:" -ForegroundColor Green
if (-not $SkipOffline) {
    Write-Host "  outputs/$offlineId/metrics.json"
}
Write-Host "  outputs/$qwenId/metrics.json"
Write-Host "  outputs/$qwenId/run_manifest.json"
Write-Host "  outputs/mvp/$mvpId/metrics.json (fictional software check only)"
Write-Host "Private prediction files are under data/derived/ and must not be submitted."
