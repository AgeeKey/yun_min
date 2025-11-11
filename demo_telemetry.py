"""
Demo script showing how to use the telemetry feature with backtest.

This demonstrates:
1. Running a backtest with telemetry enabled
2. Saving artifacts to the artifacts/ directory
3. Loading and viewing the results
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("TELEMETRY FEATURE DEMO")
print("=" * 70)
print()

print("This demo shows how the new telemetry feature works:")
print()
print("1. TELEMETRY MODULE (yunmin/backtesting/telemetry.py)")
print("   - Saves per-trade CSV with all trade details")
print("   - Saves equity curve CSV showing portfolio growth")
print("   - Saves summary JSON with performance metrics")
print()

print("2. INTEGRATION WITH BACKTESTER")
print("   - Both Backtester classes now support save_artifacts parameter")
print("   - Automatically saves artifacts when backtest completes")
print()

print("Example usage:")
print()
print("  from yunmin.backtesting.backtester import Backtester")
print("  from yunmin.strategy.ema_crossover import EMACrossoverStrategy")
print()
print("  # Initialize with telemetry enabled (default)")
print("  backtester = Backtester(")
print("      strategy=EMACrossoverStrategy(),")
print("      save_artifacts=True,  # Enable telemetry")
print("      artifacts_dir='artifacts'  # Output directory")
print("  )")
print()
print("  # Run backtest")
print("  results = backtester.run(data)")
print()
print("  # Artifacts are automatically saved to:")
print("  # - artifacts/trades_YYYYMMDD_HHMMSS.csv")
print("  # - artifacts/equity_curve_YYYYMMDD_HHMMSS.csv")
print("  # - artifacts/summary_YYYYMMDD_HHMMSS.json")
print()

print("3. ANALYSIS NOTEBOOK (notebooks/backtest_analysis.ipynb)")
print("   - Load latest artifacts from artifacts/ directory")
print("   - Visualize equity curve")
print("   - Analyze P&L distribution")
print("   - Identify top winning/losing trades")
print("   - Show drawdown analysis")
print("   - Display performance metrics")
print()

print("=" * 70)
print("HOW TO USE")
print("=" * 70)
print()
print("Step 1: Run a backtest with your strategy")
print("  $ python run_backtest_v3_realdata.py")
print()
print("Step 2: Check the artifacts directory")
print("  $ ls -lh artifacts/")
print()
print("Step 3: Open the analysis notebook")
print("  $ jupyter notebook notebooks/backtest_analysis.ipynb")
print()
print("Step 4: Run all cells to generate visualizations")
print()

print("=" * 70)
print("ARTIFACTS CREATED")
print("=" * 70)
print()

# Check if artifacts exist
artifacts_dir = Path(__file__).parent / "artifacts"
if artifacts_dir.exists():
    trade_files = list(artifacts_dir.glob("trades_*.csv"))
    equity_files = list(artifacts_dir.glob("equity_curve_*.csv"))
    summary_files = list(artifacts_dir.glob("summary_*.json"))
    
    if trade_files or equity_files or summary_files:
        print(f"Found {len(trade_files)} trade files")
        print(f"Found {len(equity_files)} equity curve files")
        print(f"Found {len(summary_files)} summary files")
        print()
        
        if trade_files:
            print("Latest files:")
            print(f"  Trades: {sorted(trade_files)[-1].name}")
            print(f"  Equity: {sorted(equity_files)[-1].name}")
            print(f"  Summary: {sorted(summary_files)[-1].name}")
    else:
        print("No artifacts found yet.")
        print("Run the integration test to generate sample artifacts:")
        print("  $ python test_telemetry_integration.py")
else:
    print("Artifacts directory not created yet.")
    print("Run the integration test to generate sample artifacts:")
    print("  $ python test_telemetry_integration.py")

print()
print("=" * 70)
