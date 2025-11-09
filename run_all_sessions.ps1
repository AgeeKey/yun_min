# Run all three test sessions for comprehensive validation
# Usage: .\run_all_sessions.ps1

Write-Host "================================================"
Write-Host "🚀 Yun Min Live Test - All Sessions"
Write-Host "================================================"
Write-Host ""
Write-Host "This script will run 3 test sessions:"
Write-Host "  Session 1: Normal market (100 iterations, 5-min)"
Write-Host "  Session 2: Volatile market (50 iterations, 2-min)"
Write-Host "  Session 3: Overnight test (50 iterations, 10-min)"
Write-Host ""
Write-Host "Total expected time: ~18 hours"
Write-Host ""

$confirmation = Read-Host "Do you want to continue? (y/n)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Aborted."
    exit 1
}

Write-Host ""
Write-Host "================================================"
Write-Host "Session 1: Normal Market"
Write-Host "================================================"
python run_live_test.py --session 1 --iterations 100 --interval 300 --condition normal

Write-Host ""
Write-Host "================================================"
Write-Host "Waiting 30 minutes before Session 2..."
Write-Host "================================================"
Start-Sleep -Seconds 1800

Write-Host ""
Write-Host "================================================"
Write-Host "Session 2: Volatile Market"
Write-Host "================================================"
python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile

Write-Host ""
Write-Host "================================================"
Write-Host "Waiting 30 minutes before Session 3..."
Write-Host "================================================"
Start-Sleep -Seconds 1800

Write-Host ""
Write-Host "================================================"
Write-Host "Session 3: Overnight Market"
Write-Host "================================================"
python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight

Write-Host ""
Write-Host "================================================"
Write-Host "✅ All sessions complete!"
Write-Host "================================================"
Write-Host ""
Write-Host "Results saved to:"
Write-Host "  - data/live_test/live_test_results.json"
Write-Host "  - data/live_test/live_test_log_*.csv"
Write-Host "  - data/live_test/LIVE_TEST_REPORT.md"
Write-Host ""
