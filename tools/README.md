# Parameter Optimization Tool

This tool provides comprehensive parameter optimization for trading strategies with walk-forward validation.

## Features

- **Grid Search**: Exhaustive testing of all parameter combinations
- **Random Search**: Efficient sampling of parameter space
- **Walk-Forward Validation**: Robust out-of-sample testing
- **YAML Configuration**: Easy parameter management
- **Multiple Export Formats**: JSON, CSV, and Markdown reports
- **Stability Analysis**: Assess parameter robustness across time periods

## Quick Start

### Basic Usage

```bash
# Run optimization with default configuration
python tools/optimizer.py

# Run with custom configuration
python tools/optimizer.py --config tools/optimizer_config.yaml

# Run random search instead of grid search
python tools/optimizer.py --method random_search --n-samples 100
```

### Quick Test Run

For a quick test with minimal parameter combinations:

```bash
python tools/optimizer.py --config tools/optimizer_config_quick.yaml
```

This uses a smaller parameter grid (2×2×2×2 = 16 combinations) and completes in ~2 minutes.

## Configuration

Configuration is done via YAML files. See `optimizer_config.yaml` for the full configuration template.

### Key Configuration Sections

#### Data Configuration

```yaml
data:
  source: historical  # 'historical' or 'synthetic'
  data_path: data/historical/btc_usdt_5m_2025.csv
  symbol: BTC/USDT
  timeframe: 5m
  start_date: "2025-10-01"  # Optional date filter
  end_date: "2025-10-31"    # Optional date filter
```

#### Optimization Settings

```yaml
optimization:
  method: grid_search  # 'grid_search' or 'random_search'
  n_random_samples: 100  # For random_search only
  metric: sharpe_ratio  # Metric to optimize
  initial_capital: 10000.0
  commission: 0.001  # 0.1%
  slippage: 0.0005   # 0.05%
```

**Available Metrics:**
- `sharpe_ratio` - Risk-adjusted returns (recommended)
- `sortino_ratio` - Downside risk-adjusted returns
- `total_profit` - Absolute profit
- `win_rate` - Percentage of winning trades
- `calmar_ratio` - Return / max drawdown

#### Walk-Forward Validation

```yaml
walk_forward:
  enabled: true
  n_splits: 3      # Number of time windows
  train_ratio: 0.7  # 70% train, 30% test
```

Walk-forward validation splits data into multiple periods:
- Each period: 70% in-sample (training), 30% out-of-sample (testing)
- Tests strategy stability across different time periods
- Provides stability metrics (mean, std, coefficient of variation)

#### Parameter Grid

```yaml
parameters:
  # Strategy parameters to optimize
  rsi_oversold: [25, 30, 35, 40]
  rsi_overbought: [60, 65, 70, 75]
  fast_period: [9, 12, 15, 20]
  slow_period: [21, 26, 30, 50]
  
  # Risk management parameters
  volume_multiplier: [1.0, 1.2, 1.5, 2.0]
  min_ema_distance: [0.001, 0.003, 0.005, 0.01]
  confidence_threshold: [0.5, 0.6, 0.7, 0.8]
  position_size: [0.02, 0.05, 0.08, 0.10]
  stop_loss_pct: [0.01, 0.02, 0.03, 0.05]
```

**Note**: Currently, only `rsi_oversold`, `rsi_overbought`, `fast_period`, and `slow_period` are optimized. Other parameters are tracked for reference but use the first value in the list.

## Output

Results are saved to the `results/` directory with timestamp:

### Files Generated

1. **JSON Results** (`optimization_results_TIMESTAMP.json`)
   - Complete optimization data
   - All parameter combinations tested
   - Walk-forward validation results
   - Configuration used

2. **CSV Summary** (`optimization_results_TIMESTAMP.csv`)
   - Tabular format for analysis in Excel/Python
   - One row per parameter combination
   - All performance metrics

3. **Markdown Report** (`optimization_report_TIMESTAMP.md`)
   - Executive summary
   - Best parameters found
   - Top N configurations
   - Walk-forward validation results
   - Stability analysis
   - Implementation recommendations

### Report Sections

The generated markdown report includes:

- **Configuration Summary**: Settings used for optimization
- **Best Parameters**: Optimal configuration found
- **Top N Configurations**: Rankings by metric
- **Walk-Forward Validation**: Out-of-sample performance
- **Stability Analysis**: Parameter robustness metrics
- **Implementation Guide**: Code snippets for deployment
- **Risk Considerations**: Important caveats and next steps

## Example Run: October 2025

To optimize parameters using October 2025 data:

1. Ensure data file exists: `data/historical/btc_usdt_5m_2025.csv`

2. Update config date filters:
```yaml
data:
  start_date: "2025-10-01"
  end_date: "2025-10-31"
```

3. Run optimization:
```bash
python tools/optimizer.py --config tools/optimizer_config.yaml
```

4. Results will be in `results/optimization_report_*.md`

**Note**: If historical data is not available, the tool automatically falls back to synthetic data generation for testing purposes.

## Interpreting Results

### Sharpe Ratio

The default optimization metric. Higher is better:
- **> 2.0**: Excellent
- **1.5 - 2.0**: Very good
- **1.0 - 1.5**: Good
- **0.5 - 1.0**: Acceptable
- **< 0.5**: Poor

### Stability Metrics

From walk-forward validation:

- **Profit CV (Coefficient of Variation)**: Profit std / profit mean
  - < 0.5: Stable
  - 0.5 - 1.0: Moderate
  - \> 1.0: Unstable

- **Sharpe Mean**: Average Sharpe across all splits
  - Should be consistently positive
  
### Win Rate

Percentage of profitable trades:
- **> 60%**: Excellent
- **50-60%**: Good
- **45-50%**: Acceptable
- **< 45%**: Concerning

### Max Drawdown

Maximum peak-to-trough decline:
- **< 10%**: Excellent
- **10-20%**: Good
- **20-30%**: Acceptable
- **> 30%**: High risk

## Advanced Usage

### Random Search

For large parameter spaces, random search is more efficient:

```bash
python tools/optimizer.py --method random_search --n-samples 100
```

Randomly samples 100 parameter combinations instead of testing all.

### Custom Metric

Edit config to optimize for different metrics:

```yaml
optimization:
  metric: sortino_ratio  # Or total_profit, win_rate, etc.
```

### Disable Walk-Forward

For faster optimization without validation:

```yaml
walk_forward:
  enabled: false
```

## Testing

Run unit tests to verify installation:

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/test_optimizer.py -v
```

Expected output: All 9 tests should pass.

## Performance Notes

- **Grid Search**: Tests all combinations (can be slow with large grids)
  - 4×4×4×4 = 256 combinations ≈ 20-30 minutes
  - 4×4×2×2 = 64 combinations ≈ 5-10 minutes
  
- **Random Search**: Much faster for large parameter spaces
  - 100 samples ≈ 5-10 minutes
  
- **Walk-Forward**: Adds ~30% overhead for validation

**Tip**: Use `optimizer_config_quick.yaml` for quick tests, then expand parameter grid once satisfied with setup.

## Troubleshooting

### "Data file not found"

The tool falls back to synthetic data automatically. This is fine for testing but use real data for production optimization.

### Out of Memory

Reduce parameter grid size or use random search with fewer samples.

### Slow Performance

- Use smaller parameter grid
- Switch to random_search method
- Disable walk_forward validation for initial tests
- Use faster machine or cloud computing

### No Valid Combinations

Ensure `fast_period < slow_period`. The tool automatically skips invalid combinations.

## Integration with Strategy

After finding optimal parameters, update your strategy configuration:

```yaml
# In config/default.yaml
strategy:
  name: ema_crossover
  fast_ema: 12  # Use optimized fast_period
  slow_ema: 26  # Use optimized slow_period
  rsi_oversold: 35  # Use optimized value
  rsi_overbought: 65  # Use optimized value
```

## Best Practices

1. **Use Historical Data**: Always optimize on real market data when available
2. **Walk-Forward Validation**: Always enable for robust parameter selection
3. **Re-optimize Regularly**: Re-run every 3-6 months as market conditions change
4. **Paper Trade First**: Test optimized parameters in paper trading before live
5. **Monitor Performance**: Track actual vs. expected performance
6. **Don't Over-optimize**: Avoid fitting to noise (use walk-forward validation)
7. **Consider Market Regime**: Different parameters may work better in different market conditions

## Future Enhancements

Planned features:
- Genetic algorithm optimization
- Multi-objective optimization (Pareto frontier)
- Parameter importance analysis
- Visualization heatmaps
- Monte Carlo simulation integration
- Parallel processing for faster optimization

## Support

For issues or questions:
1. Check this README
2. Review example configurations
3. Run unit tests to verify installation
4. Check generated reports for insights

---

*Part of the yunmin trading system*
