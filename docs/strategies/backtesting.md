# Backtesting Guide

## Overview

Backtesting allows you to test trading strategies on historical data before risking real capital. YunMin provides a comprehensive backtesting framework.

## Quick Start

### Basic Backtest

```bash
python run_v4_backtest.py \
    --strategy ai_agent \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --symbol BTC/USDT
```

### With Custom Parameters

```bash
python run_v4_backtest.py \
    --strategy ai_agent \
    --symbol BTC/USDT \
    --timeframe 5m \
    --capital 10000 \
    --commission 0.001 \
    --start-date 2024-06-01 \
    --end-date 2024-12-31
```

## Configuration

### Backtest Settings

```yaml
backtesting:
  # Date range
  start_date: "2024-01-01"
  end_date: "2024-12-31"
  
  # Capital
  initial_capital: 10000
  
  # Trading costs
  commission: 0.001  # 0.1% per trade
  slippage: 0.0005   # 0.05% slippage
  
  # Data settings
  timeframe: 5m
  warmup_candles: 100  # Candles needed before first trade
  
  # Risk management
  max_positions: 10
  position_size: 0.1  # 10% per position
```

## Running Backtests

### Using Python Script

```python
from yunmin.backtester.engine import BacktestEngine
from yunmin.strategy.ai_agent_strategy import AIAgentStrategy

# Initialize strategy
strategy = AIAgentStrategy(
    model="grok-2-1212",
    min_confidence=0.65
)

# Initialize backtester
engine = BacktestEngine(
    strategy=strategy,
    initial_capital=10000,
    commission=0.001,
    slippage=0.0005
)

# Run backtest
results = await engine.run(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    timeframe="5m"
)

# Print results
print(f"Total Return: {results['total_return']:.2%}")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2%}")
print(f"Win Rate: {results['win_rate']:.2%}")
```

### Using CLI

```bash
# Run with default settings
python run_v4_backtest.py

# Run with specific strategy
python run_v4_backtest.py --strategy rsi_v2

# Run on multiple symbols
python run_v4_backtest.py --symbols BTC/USDT ETH/USDT SOL/USDT

# Run with custom config
python run_v4_backtest.py --config config/backtest_aggressive.yaml
```

## Analyzing Results

### Performance Metrics

The backtester provides comprehensive metrics:

```python
{
    "total_return": 0.156,  # 15.6% return
    "annual_return": 0.182,  # Annualized
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.31,
    "max_drawdown": 0.087,  # 8.7%
    "win_rate": 0.628,  # 62.8%
    "profit_factor": 1.94,
    "total_trades": 342,
    "avg_trade_duration": "2h 15m",
    "avg_profit": 45.23,
    "avg_loss": -32.18,
    "best_trade": 312.50,
    "worst_trade": -98.25,
    "consecutive_wins": 12,
    "consecutive_losses": 5
}
```

### Visualization

Generate performance charts:

```python
from yunmin.backtester.visualizer import BacktestVisualizer

viz = BacktestVisualizer(results)

# Equity curve
viz.plot_equity_curve(save_path="equity_curve.png")

# Drawdown chart
viz.plot_drawdown(save_path="drawdown.png")

# Trade distribution
viz.plot_trade_distribution(save_path="trades.png")

# Monthly returns heatmap
viz.plot_monthly_returns(save_path="monthly.png")
```

### Trade Log

Review individual trades:

```python
# Get all trades
trades = results['trades']

# Filter winning trades
winners = [t for t in trades if t['pnl'] > 0]

# Filter losing trades
losers = [t for t in trades if t['pnl'] < 0]

# Analyze by side
long_trades = [t for t in trades if t['side'] == 'LONG']
short_trades = [t for t in trades if t['side'] == 'SHORT']

print(f"LONG win rate: {len([t for t in long_trades if t['pnl'] > 0]) / len(long_trades):.2%}")
print(f"SHORT win rate: {len([t for t in short_trades if t['pnl'] > 0]) / len(short_trades):.2%}")
```

## Advanced Backtesting

### Walk-Forward Analysis

Test strategy across multiple time periods:

```python
from yunmin.backtester.walk_forward import WalkForwardAnalyzer

analyzer = WalkForwardAnalyzer(
    strategy=strategy,
    train_period_days=90,
    test_period_days=30
)

results = await analyzer.run(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Results for each period
for period in results['periods']:
    print(f"{period['start']} to {period['end']}: {period['return']:.2%}")
```

### Monte Carlo Simulation

Test strategy robustness:

```python
from yunmin.backtester.monte_carlo import MonteCarloSimulator

simulator = MonteCarloSimulator(
    strategy=strategy,
    n_simulations=1000
)

results = await simulator.run(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Statistical results
print(f"Mean return: {results['mean_return']:.2%}")
print(f"Std deviation: {results['std_return']:.2%}")
print(f"5th percentile: {results['percentile_5']:.2%}")
print(f"95th percentile: {results['percentile_95']:.2%}")
```

### Parameter Optimization

Find optimal strategy parameters:

```python
from yunmin.backtester.optimizer import ParameterOptimizer

optimizer = ParameterOptimizer(
    strategy_class=AIAgentStrategy,
    optimization_metric="sharpe_ratio"
)

# Define parameter grid
param_grid = {
    "min_confidence": [0.55, 0.60, 0.65, 0.70],
    "lookback_candles": [200, 300, 500, 700],
    "risk_per_trade": [0.01, 0.02, 0.03]
}

# Run optimization
best_params = await optimizer.optimize(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    param_grid=param_grid
)

print(f"Best parameters: {best_params}")
```

## Best Practices

### 1. Use Sufficient Data

- Minimum 6 months of data
- Include different market conditions (bull, bear, sideways)
- Account for seasonal patterns

### 2. Avoid Overfitting

- Don't optimize too many parameters
- Use walk-forward analysis
- Test on out-of-sample data
- Keep strategy logic simple

### 3. Realistic Assumptions

- Include commission costs (0.1% typical)
- Account for slippage (0.05% typical)
- Consider market impact for large orders
- Use realistic execution delays

### 4. Validate Results

- Compare with buy-and-hold
- Check consistency across timeframes
- Verify with paper trading
- Review individual trades for sanity

### 5. Risk Management

- Set maximum drawdown limits
- Test with different position sizes
- Validate stop-loss effectiveness
- Monitor consecutive losses

## Common Pitfalls

### Look-Ahead Bias

❌ **Wrong:** Using future data in current decision
```python
# This uses tomorrow's close in today's decision
if tomorrow_close > today_close:
    open_position()
```

✅ **Correct:** Only use past and current data
```python
# Only uses current and historical data
if ema_20 > ema_50:
    open_position()
```

### Survivorship Bias

- Test on delisted assets too
- Include failed trades
- Don't cherry-pick successful periods

### Data Snooping

- Don't repeatedly test until you find "good" parameters
- Use separate validation dataset
- Document all tests performed

## Comparing Strategies

```python
from yunmin.backtester.comparison import StrategyComparison

comparison = StrategyComparison([
    AIAgentStrategy(model="grok-2-1212"),
    RSIStrategy(),
    EMAStrategy()
])

results = await comparison.run(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# Print comparison table
comparison.print_results()

# Generate comparison chart
comparison.plot_equity_curves(save_path="comparison.png")
```

## Exporting Results

### JSON Export

```python
import json

with open("backtest_results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### CSV Export

```python
import pandas as pd

# Export trades
trades_df = pd.DataFrame(results['trades'])
trades_df.to_csv("trades.csv", index=False)

# Export equity curve
equity_df = pd.DataFrame(results['equity_curve'])
equity_df.to_csv("equity.csv", index=False)
```

### PDF Report

```python
from yunmin.backtester.reporter import PDFReporter

reporter = PDFReporter(results)
reporter.generate(output_path="backtest_report.pdf")
```

## Next Steps

- [AI Strategies](ai-strategies.md) - Learn about AI-powered strategies
- [Creating Custom Strategies](custom-strategy.md) - Build your own strategy
- [Paper Trading](../testing/testnet-setup.md) - Test with paper money
