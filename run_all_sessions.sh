#!/bin/bash
# Run all three test sessions for comprehensive validation
# Usage: ./run_all_sessions.sh

set -e

echo "================================================"
echo "🚀 Yun Min Live Test - All Sessions"
echo "================================================"
echo ""
echo "This script will run 3 test sessions:"
echo "  Session 1: Normal market (100 iterations, 5-min)"
echo "  Session 2: Volatile market (50 iterations, 2-min)"
echo "  Session 3: Overnight test (50 iterations, 10-min)"
echo ""
echo "Total expected time: ~18 hours"
echo ""
read -p "Do you want to continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Aborted."
    exit 1
fi

echo ""
echo "================================================"
echo "Session 1: Normal Market"
echo "================================================"
python run_live_test.py --session 1 --iterations 100 --interval 300 --condition normal

echo ""
echo "================================================"
echo "Waiting 30 minutes before Session 2..."
echo "================================================"
sleep 1800

echo ""
echo "================================================"
echo "Session 2: Volatile Market"
echo "================================================"
python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile

echo ""
echo "================================================"
echo "Waiting 30 minutes before Session 3..."
echo "================================================"
sleep 1800

echo ""
echo "================================================"
echo "Session 3: Overnight Market"
echo "================================================"
python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight

echo ""
echo "================================================"
echo "✅ All sessions complete!"
echo "================================================"
echo ""
echo "Results saved to:"
echo "  - data/live_test/live_test_results.json"
echo "  - data/live_test/live_test_log_*.csv"
echo "  - data/live_test/LIVE_TEST_REPORT.md"
echo ""
