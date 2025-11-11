# Telemetry Feature

This feature provides comprehensive backtest result tracking and analysis capabilities.

## Overview

The telemetry system automatically saves backtest artifacts including:
- Per-trade CSV with detailed trade information
- Equity curve CSV showing portfolio performance over time
- Summary JSON with key performance metrics

## Components

### 1. Telemetry Module (`yunmin/backtesting/telemetry.py`)

The `BacktestTelemetry` class handles saving backtest artifacts to disk.

**Features:**
- Automatic timestamping of files
- Configurable output directory
- Support for custom filenames
- Comprehensive trade data capture

**Usage:**
```python
from yunmin.backtesting.telemetry import BacktestTelemetry

# Initialize telemetry
telemetry = BacktestTelemetry(output_dir="artifacts")

# Save artifacts
telemetry.save_all(
    trades=trade_list,
    equity_curve=equity_values,
    summary=metrics_dict
)
```

### 2. Backtester Integration

Both backtester classes now support telemetry:

**yunmin/backtesting/backtester.py:**
```python
from yunmin.backtesting.backtester import Backtester

backtester = Backtester(
    strategy=my_strategy,
    save_artifacts=True,  # Enable telemetry (default)
    artifacts_dir="artifacts"  # Output directory
)

results = backtester.run(data)
# Artifacts are automatically saved
```

**yunmin/core/backtester.py (AdvancedBacktester):**
```python
from yunmin.core.backtester import AdvancedBacktester

backtester = AdvancedBacktester(
    symbol="BTC/USDT",
    save_artifacts=True,  # Enable telemetry (default)
    artifacts_dir="artifacts"
)

result = backtester.run(strategy, data)
# Artifacts are automatically saved
```

### 3. Analysis Notebook (`notebooks/backtest_analysis.ipynb`)

A comprehensive Jupyter notebook for analyzing backtest results.

**Features:**
- Equity curve visualization
- P&L distribution analysis (USD and percentage)
- Top winning/losing trades identification
- Cumulative P&L over time
- Win/loss streak analysis
- Drawdown analysis
- Performance metrics summary

**How to use:**
1. Run a backtest to generate artifacts
2. Open the notebook: `jupyter notebook notebooks/backtest_analysis.ipynb`
3. Run all cells to generate visualizations

## Artifacts Format

### Trades CSV

Fields:
- `entry_time`: Trade entry timestamp
- `entry_price`: Entry price
- `exit_time`: Trade exit timestamp
- `exit_price`: Exit price
- `size`: Position size
- `pnl_usd`: Profit/Loss in USD
- `pnl_pct`: Profit/Loss as percentage
- `confidence`: Signal confidence score
- `reasons`: Trade reasoning/signals

### Equity Curve CSV

Fields:
- `step`: Time step number
- `equity`: Portfolio equity value

### Summary JSON

Structure:
```json
{
  "metadata": {
    "timestamp": "YYYYMMDD_HHMMSS",
    "generated_at": "ISO timestamp"
  },
  "metrics": {
    "total_trades": 10,
    "winning_trades": 6,
    "losing_trades": 4,
    "win_rate": 60.0,
    "total_pnl": 1234.56,
    "profit_factor": 1.5,
    "sharpe_ratio": 1.2,
    "max_drawdown": 0.15,
    ...
  }
}
```

## Testing

Run the integration test to verify the feature:
```bash
python test_telemetry_integration.py
```

This will:
1. Generate sample backtest data
2. Save artifacts to `artifacts/` directory
3. Verify all files are created correctly
4. Display summary statistics

## Demo

Run the demo script to see usage examples:
```bash
python demo_telemetry.py
```

## Configuration

### Disable Telemetry

If you want to run a backtest without saving artifacts:
```python
backtester = Backtester(
    strategy=my_strategy,
    save_artifacts=False  # Disable telemetry
)
```

### Custom Output Directory

Specify a custom directory for artifacts:
```python
backtester = Backtester(
    strategy=my_strategy,
    artifacts_dir="my_custom_dir"
)
```

## Best Practices

1. **Always review artifacts after backtests** - Check the CSV files to understand trade patterns
2. **Use the analysis notebook** - Visual analysis reveals insights not obvious in raw numbers
3. **Compare multiple runs** - Keep artifacts from different strategy configurations for comparison
4. **Archive important results** - Move artifacts to a dated subdirectory before running new tests

## File Organization

```
artifacts/
├── trades_20251111_161927.csv
├── equity_curve_20251111_161927.csv
├── summary_20251111_161927.json
├── trades_20251111_170000.csv
├── equity_curve_20251111_170000.csv
└── summary_20251111_170000.json
```

Files are automatically timestamped to prevent overwriting previous results.

## Troubleshooting

### Artifacts not being created

1. Check that `save_artifacts=True` (it's the default)
2. Verify the output directory is writable
3. Check logs for error messages

### Notebook can't find artifacts

1. Ensure you've run at least one backtest
2. Check that artifacts are in the `artifacts/` directory
3. Verify the notebook is looking in the correct path

### Missing fields in CSV

Some fields like `confidence` and `reasons` depend on the strategy implementation. If your strategy doesn't provide these, they will be empty or zero.

## Future Enhancements

Potential improvements:
- PDF report generation
- Automatic email notifications with results
- Cloud storage integration (S3, GCS)
- Real-time artifact streaming
- Multi-strategy comparison dashboard
