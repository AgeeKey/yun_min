# Monitor Test #12 - OpenAI GPT-5
# Автоматический мониторинг каждые 15 минут

param(
    [int]$IntervalMinutes = 15
)

$logPath = "F:\AgeeKey\yun_min\logs"
$jobName = "Test12_OpenAI_GPT5"

Write-Host "`n🔍 МОНИТОРИНГ TEST #12 - OPENAI GPT-5" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor DarkGray

$iteration = 1
while ($true) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] Проверка #$iteration" -ForegroundColor Yellow
    
    # Проверка Job
    $job = Get-Job -Name $jobName -ErrorAction SilentlyContinue
    if ($job) {
        $state = $job.State
        $stateColor = if ($state -eq 'Running') { 'Green' } elseif ($state -eq 'Completed') { 'Cyan' } else { 'Red' }
        Write-Host "  Job State: $state" -ForegroundColor $stateColor
        
        if ($state -eq 'Completed') {
            Write-Host "`n✅ TEST #12 ЗАВЕРШЁН!" -ForegroundColor Green
            Receive-Job -Name $jobName | Select-Object -Last 20
            break
        } elseif ($state -eq 'Failed') {
            Write-Host "`n❌ TEST #12 УПАЛ!" -ForegroundColor Red
            Receive-Job -Name $jobName -Keep
            break
        }
    } else {
        Write-Host "  ⚠️ Job не найден!" -ForegroundColor Red
        break
    }
    
    # Последние логи
    Set-Location $logPath
    $latestLog = Get-ChildItem -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    if ($latestLog) {
        Write-Host "  Лог: $($latestLog.Name) ($([math]::Round($latestLog.Length/1KB, 1)) KB)" -ForegroundColor Gray
        
        # Подсчёт итераций
        $iterations = (Get-Content $latestLog.FullName | Select-String "=== Trading Loop Iteration ===" | Measure-Object).Count
        Write-Host "  Итераций: $iterations / 120" -ForegroundColor Cyan
        
        # Подсчёт сигналов
        $signals = Get-Content $latestLog.FullName | Select-String "📊 OpenAI gpt-5: (BUY|SELL|HOLD)"
        $buyCount = ($signals | Select-String "BUY").Count
        $sellCount = ($signals | Select-String "SELL").Count
        $holdCount = ($signals | Select-String "HOLD").Count
        
        Write-Host "  Сигналы: BUY=$buyCount, SELL=$sellCount, HOLD=$holdCount" -ForegroundColor Yellow
        
        # Последний сигнал
        $lastSignal = $signals | Select-Object -Last 1
        if ($lastSignal) {
            Write-Host "  Последний: $($lastSignal.Line.Substring(0, [Math]::Min(80, $lastSignal.Line.Length)))..." -ForegroundColor White
        }
    }
    
    Write-Host ""
    $iteration++
    
    # Ждём следующего интервала
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "Мониторинг завершён: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
