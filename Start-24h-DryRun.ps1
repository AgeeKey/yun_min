# Start-24h-DryRun.ps1
# Запуск 24-часового DRY RUN теста в фоновом режиме

Write-Host "🚀 YunMin 24-Hour DRY RUN Test" -ForegroundColor Cyan
Write-Host "=" * 80

# Проверить .env
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env with:" -ForegroundColor Yellow
    Write-Host "  YUNMIN_TRADING_MODE=dry_run"
    Write-Host "  YUNMIN_EXCHANGE_TESTNET=true"
    exit 1
}

# Проверить Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found!" -ForegroundColor Red
    exit 1
}

# Проверить зависимости
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$packages = @("loguru", "aiohttp", "pydantic-settings", "ccxt", "pytest")
foreach ($pkg in $packages) {
    $installed = python -m pip show $pkg 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ $pkg" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $pkg NOT INSTALLED" -ForegroundColor Red
        Write-Host "Run: python -m pip install $pkg" -ForegroundColor Yellow
        exit 1
    }
}

# Создать директории
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }
if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "data/snapshots")) { New-Item -ItemType Directory -Path "data/snapshots" | Out-Null }

Write-Host ""
Write-Host "📝 Configuration:" -ForegroundColor Cyan
Write-Host "  Mode: DRY_RUN (no real trades)"
Write-Host "  Duration: 24 hours"
Write-Host "  Status updates: Every 5 minutes"
Write-Host "  Snapshots: Every 1 hour"
Write-Host ""

# Запустить в фоне
Write-Host "🚀 Starting 24-hour test in background..." -ForegroundColor Green
Write-Host ""

$startTime = Get-Date
Write-Host "Start time: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
$endTime = $startTime.AddHours(24)
Write-Host "End time:   $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Cyan
Write-Host ""

# Запустить как фоновую задачу (Job)
$job = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python run_24h_dry_run.py
}

Write-Host "✅ Job started (ID: $($job.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "📊 To monitor progress:" -ForegroundColor Yellow
Write-Host "  1. Check log file: logs/dry_run_24h_*.log"
Write-Host "  2. View job status: Get-Job $($job.Id)"
Write-Host "  3. See output: Receive-Job $($job.Id) -Keep"
Write-Host "  4. Stop test: Stop-Job $($job.Id)"
Write-Host ""

# Tail последний лог файл
$latestLog = Get-ChildItem "logs/dry_run_24h_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($latestLog) {
    Write-Host "📄 Log file: $($latestLog.FullName)" -ForegroundColor Cyan
    Write-Host "To tail logs: Get-Content '$($latestLog.FullName)' -Wait -Tail 20" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "⏰ Test will run for 24 hours in the background" -ForegroundColor Green
Write-Host "Press Ctrl+C to exit this script (test will continue running)" -ForegroundColor Gray
Write-Host ""

# Опционально: показывать живой вывод
$response = Read-Host "Watch live output? (y/N)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "Watching output... (Ctrl+C to stop watching)" -ForegroundColor Cyan
    Write-Host "=" * 80
    
    try {
        while ($true) {
            Start-Sleep -Seconds 5
            $output = Receive-Job $job -Keep
            if ($output) {
                $output | Select-Object -Last 10 | ForEach-Object { Write-Host $_ }
            }
            
            # Проверить статус
            if ($job.State -eq "Completed") {
                Write-Host ""
                Write-Host "✅ Job completed!" -ForegroundColor Green
                Receive-Job $job
                break
            } elseif ($job.State -eq "Failed") {
                Write-Host ""
                Write-Host "❌ Job failed!" -ForegroundColor Red
                Receive-Job $job
                break
            }
        }
    } catch {
        Write-Host ""
        Write-Host "Stopped watching. Job is still running in background." -ForegroundColor Yellow
    }
} else {
    Write-Host "Job is running in background (ID: $($job.Id))" -ForegroundColor Green
    Write-Host "Check status anytime: Get-Job $($job.Id)" -ForegroundColor Yellow
}
