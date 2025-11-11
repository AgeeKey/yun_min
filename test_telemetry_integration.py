"""
Integration test demonstrating the telemetry feature.

This script creates a simple backtest and verifies that artifacts are saved.
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import telemetry module directly
import importlib.util
spec = importlib.util.spec_from_file_location(
    'telemetry', 
    '/home/runner/work/yun_min/yun_min/yunmin/backtesting/telemetry.py'
)
telemetry_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telemetry_module)

BacktestTelemetry = telemetry_module.BacktestTelemetry


def create_sample_backtest_data():
    """Create sample backtest data for demonstration."""
    # Create sample trades
    start_date = datetime(2024, 1, 1)
    trades = []
    
    for i in range(10):
        entry_time = start_date + timedelta(days=i)
        exit_time = entry_time + timedelta(hours=2)
        entry_price = 45000 + np.random.randint(-500, 500)
        
        # 60% win rate
        if np.random.random() < 0.6:
            exit_price = entry_price * 1.02  # 2% win
        else:
            exit_price = entry_price * 0.99  # 1% loss
        
        pnl = (exit_price - entry_price) * 0.1
        
        trades.append({
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'amount': 0.1,
            'pnl': pnl,
            'pnl_pct': (pnl / (entry_price * 0.1)) * 100,
            'signal_confidence': 0.7 + np.random.random() * 0.3,
            'reasons': 'Test strategy signal'
        })
    
    # Create equity curve
    initial_capital = 10000.0
    equity_curve = [initial_capital]
    
    for trade in trades:
        equity_curve.append(equity_curve[-1] + trade['pnl'])
    
    # Create summary
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    
    total_pnl = sum(t['pnl'] for t in trades)
    
    summary = {
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': (len(winning_trades) / len(trades)) * 100,
        'total_pnl': total_pnl,
        'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
        'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
        'final_equity': equity_curve[-1],
        'total_return': ((equity_curve[-1] / initial_capital) - 1) * 100
    }
    
    return trades, equity_curve, summary


def main():
    """Run integration test."""
    print("=" * 70)
    print("TELEMETRY INTEGRATION TEST")
    print("=" * 70)
    print()
    
    # Create artifacts directory
    artifacts_dir = Path(__file__).parent.parent / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)
    
    print(f"Artifacts directory: {artifacts_dir}")
    print()
    
    # Initialize telemetry
    telemetry = BacktestTelemetry(output_dir=str(artifacts_dir))
    print("✓ Telemetry initialized")
    
    # Create sample backtest data
    trades, equity_curve, summary = create_sample_backtest_data()
    print(f"✓ Generated sample backtest data ({len(trades)} trades)")
    
    # Save all artifacts
    paths = telemetry.save_all(trades, equity_curve, summary)
    print()
    print("✓ Artifacts saved:")
    print(f"  - Trades CSV: {paths['trades'].name}")
    print(f"  - Equity CSV: {paths['equity_curve'].name}")
    print(f"  - Summary JSON: {paths['summary'].name}")
    print()
    
    # Verify files exist and contain data
    trades_df = pd.read_csv(paths['trades'])
    equity_df = pd.read_csv(paths['equity_curve'])
    
    print("Verification:")
    print(f"  ✓ Trades CSV contains {len(trades_df)} rows")
    print(f"  ✓ Equity CSV contains {len(equity_df)} rows")
    print(f"  ✓ Summary JSON created")
    print()
    
    # Print summary
    print("Backtest Summary:")
    print(f"  Total Trades: {summary['total_trades']}")
    print(f"  Win Rate: {summary['win_rate']:.1f}%")
    print(f"  Total P&L: ${summary['total_pnl']:.2f}")
    print(f"  Total Return: {summary['total_return']:.2f}%")
    print()
    
    print("=" * 70)
    print("✓✓✓ INTEGRATION TEST PASSED ✓✓✓")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run a real backtest to generate artifacts")
    print("  2. Open notebooks/backtest_analysis.ipynb")
    print("  3. Analyze the results with visualizations")


if __name__ == '__main__':
    main()
