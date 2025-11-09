#!/usr/bin/env python3
"""
Parameter optimization script for EMA Crossover Strategy.
Tests 256 combinations of RSI/EMA parameters.

This script systematically tests all combinations of:
- RSI oversold: [25, 30, 35, 40]
- RSI overbought: [60, 65, 70, 75]
- EMA fast: [9, 12, 15, 20]
- EMA slow: [21, 26, 30, 50]

Total: 4 × 4 × 4 × 4 = 256 parameter combinations
"""

import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from loguru import logger
import matplotlib.pyplot as plt
import seaborn as sns

from yunmin.core.backtester import AdvancedBacktester, OptimizationMethod
from yunmin.strategy.ema_crossover import EMACrossoverStrategy


def generate_synthetic_data(
    periods: int = 2000,
    start_price: float = 50000.0,
    trend: float = 0.0001,
    volatility: float = 0.02
) -> pd.DataFrame:
    """
    Generate synthetic BTC/USDT price data for backtesting.
    
    Args:
        periods: Number of 5-minute bars to generate
        start_price: Starting price
        trend: Trend component (positive = uptrend)
        volatility: Volatility of price movements
        
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Generating {periods} bars of synthetic data...")
    
    # Generate random walk with trend
    np.random.seed(42)  # For reproducibility
    returns = np.random.randn(periods) * volatility + trend
    prices = start_price * np.exp(np.cumsum(returns))
    
    # Create OHLCV data
    data = []
    start_time = datetime(2025, 1, 1)
    
    for i in range(periods):
        price = prices[i]
        high_offset = np.abs(np.random.randn()) * price * 0.005
        low_offset = np.abs(np.random.randn()) * price * 0.005
        
        data.append({
            'timestamp': start_time + timedelta(minutes=5*i),
            'open': price,
            'high': price + high_offset,
            'low': price - low_offset,
            'close': price,
            'volume': np.random.uniform(100, 1000)
        })
    
    df = pd.DataFrame(data)
    logger.success(f"Generated data: {len(df)} bars, price range {df['close'].min():.2f} - {df['close'].max():.2f}")
    return df


def load_or_generate_data() -> pd.DataFrame:
    """
    Load historical data if available, otherwise generate synthetic data.
    
    Returns:
        DataFrame with OHLCV data
    """
    # Try to load historical data first
    data_path = Path("data/historical/btc_usdt_5m_2025.csv")
    
    if data_path.exists():
        logger.info(f"Loading historical data from {data_path}")
        data = pd.read_csv(data_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        logger.success(f"Loaded {len(data)} bars of historical data")
        return data
    else:
        logger.warning(f"Historical data not found at {data_path}")
        logger.info("Generating synthetic data for optimization...")
        return generate_synthetic_data(periods=2000)


def optimize() -> Dict[str, Any]:
    """
    Run parameter optimization for EMA Crossover Strategy.
    
    Returns:
        Dictionary with optimization results
    """
    logger.info("=" * 80)
    logger.info("🎯 Starting RSI/EMA Parameter Optimization")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # Load data
    data = load_or_generate_data()
    
    # Initialize backtester
    backtester = AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
    
    # Define parameter grid
    # Note: EMACrossoverStrategy uses 'fast_period' and 'slow_period', not 'ema_fast' and 'ema_slow'
    param_grid = {
        'rsi_oversold': [25, 30, 35, 40],
        'rsi_overbought': [60, 65, 70, 75],
        'fast_period': [9, 12, 15, 20],
        'slow_period': [21, 26, 30, 50]
    }
    
    total_combinations = (
        len(param_grid['rsi_oversold']) * 
        len(param_grid['rsi_overbought']) * 
        len(param_grid['fast_period']) * 
        len(param_grid['slow_period'])
    )
    
    logger.info(f"Testing {total_combinations} parameter combinations")
    logger.info(f"Parameter grid: {param_grid}")
    logger.info("")
    
    # Run optimization
    logger.info("Running grid search optimization...")
    result = backtester.optimize_parameters(
        strategy_class=EMACrossoverStrategy,
        data=data,
        param_grid=param_grid,
        optimization_metric='sharpe_ratio',
        method=OptimizationMethod.GRID_SEARCH,
        initial_capital=10000.0
    )
    
    execution_time = time.time() - start_time
    
    logger.success("=" * 80)
    logger.success("✅ Optimization Complete!")
    logger.success("=" * 80)
    logger.success(f"Best parameters: {result.best_params}")
    logger.success(f"Best Sharpe Ratio: {result.best_score:.4f}")
    logger.success(f"Execution time: {execution_time:.2f} seconds")
    logger.success("")
    
    # Sort results by score
    sorted_results = sorted(
        result.all_results,
        key=lambda x: x['score'],
        reverse=True
    )
    
    # Get top 10
    top_10 = sorted_results[:10]
    
    logger.info("Top 10 Parameter Combinations:")
    logger.info("-" * 80)
    for i, res in enumerate(top_10, 1):
        logger.info(
            f"{i}. Sharpe: {res['score']:.4f} | "
            f"Win Rate: {res['win_rate']*100:.1f}% | "
            f"Max DD: {res['max_drawdown']*100:.1f}% | "
            f"Params: {res['params']}"
        )
    
    # Prepare output
    optimization_results = {
        'optimization_method': result.optimization_method,
        'metric_optimized': result.metric_optimized,
        'total_combinations_tested': total_combinations,
        'best_params': result.best_params,
        'best_score': float(result.best_score),
        'top_10_combinations': [
            {
                'params': r['params'],
                'sharpe_ratio': float(r['score']),
                'win_rate': float(r['win_rate']),
                'max_drawdown': float(r['max_drawdown']),
                'total_profit': float(r['total_profit'])
            }
            for r in top_10
        ],
        'execution_time_seconds': execution_time,
        'data_points': len(data),
        'timestamp': datetime.now().isoformat()
    }
    
    return optimization_results, result.all_results


def create_heatmap(all_results: List[Dict], output_path: str = "optimization_heatmap.png"):
    """
    Create heatmap visualization of optimization results.
    
    Args:
        all_results: List of all optimization results
        output_path: Path to save heatmap
    """
    logger.info("Creating optimization heatmap...")
    
    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(all_results)
    
    # Extract parameters
    df['rsi_oversold'] = df['params'].apply(lambda x: x['rsi_oversold'])
    df['rsi_overbought'] = df['params'].apply(lambda x: x['rsi_overbought'])
    df['fast_period'] = df['params'].apply(lambda x: x['fast_period'])
    df['slow_period'] = df['params'].apply(lambda x: x['slow_period'])
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('RSI/EMA Parameter Optimization Heatmaps', fontsize=16, fontweight='bold')
    
    # 1. RSI Oversold vs Overbought (average across EMA params)
    pivot1 = df.groupby(['rsi_oversold', 'rsi_overbought'])['score'].mean().reset_index()
    pivot1_matrix = pivot1.pivot(index='rsi_oversold', columns='rsi_overbought', values='score')
    sns.heatmap(pivot1_matrix, annot=True, fmt='.3f', cmap='RdYlGn', ax=axes[0, 0], cbar_kws={'label': 'Sharpe Ratio'})
    axes[0, 0].set_title('RSI Oversold vs Overbought (avg across EMA)')
    axes[0, 0].set_xlabel('RSI Overbought')
    axes[0, 0].set_ylabel('RSI Oversold')
    
    # 2. EMA Fast vs Slow (average across RSI params)
    pivot2 = df.groupby(['fast_period', 'slow_period'])['score'].mean().reset_index()
    pivot2_matrix = pivot2.pivot(index='fast_period', columns='slow_period', values='score')
    sns.heatmap(pivot2_matrix, annot=True, fmt='.3f', cmap='RdYlGn', ax=axes[0, 1], cbar_kws={'label': 'Sharpe Ratio'})
    axes[0, 1].set_title('EMA Fast vs Slow (avg across RSI)')
    axes[0, 1].set_xlabel('EMA Slow Period')
    axes[0, 1].set_ylabel('EMA Fast Period')
    
    # 3. Win Rate heatmap
    pivot3 = df.groupby(['fast_period', 'slow_period'])['win_rate'].mean().reset_index()
    pivot3_matrix = pivot3.pivot(index='fast_period', columns='slow_period', values='win_rate')
    sns.heatmap(pivot3_matrix, annot=True, fmt='.2%', cmap='RdYlGn', ax=axes[1, 0], cbar_kws={'label': 'Win Rate'})
    axes[1, 0].set_title('Win Rate by EMA Periods')
    axes[1, 0].set_xlabel('EMA Slow Period')
    axes[1, 0].set_ylabel('EMA Fast Period')
    
    # 4. Max Drawdown heatmap (lower is better, so reverse colormap)
    pivot4 = df.groupby(['rsi_oversold', 'rsi_overbought'])['max_drawdown'].mean().reset_index()
    pivot4_matrix = pivot4.pivot(index='rsi_oversold', columns='rsi_overbought', values='max_drawdown')
    sns.heatmap(pivot4_matrix, annot=True, fmt='.2%', cmap='RdYlGn_r', ax=axes[1, 1], cbar_kws={'label': 'Max Drawdown'})
    axes[1, 1].set_title('Max Drawdown by RSI Thresholds (lower is better)')
    axes[1, 1].set_xlabel('RSI Overbought')
    axes[1, 1].set_ylabel('RSI Oversold')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    logger.success(f"Heatmap saved to {output_path}")
    plt.close()


def create_report(results: Dict[str, Any], output_path: str = "OPTIMIZATION_REPORT.md"):
    """
    Create markdown report with optimization analysis.
    
    Args:
        results: Optimization results dictionary
        output_path: Path to save report
    """
    logger.info("Creating optimization report...")
    
    best = results['best_params']
    top_10 = results['top_10_combinations']
    
    # Compare with current default params
    current_params = {
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'fast_period': 9,
        'slow_period': 21
    }
    
    # Find current params performance in results
    current_perf = next(
        (r for r in top_10 if r['params'] == current_params),
        None
    )
    
    report = f"""# Parameter Optimization Report

## Executive Summary

- **Optimization Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Data Points Analyzed**: {results['data_points']:,}
- **Total Combinations Tested**: {results['total_combinations_tested']}
- **Execution Time**: {results['execution_time_seconds']:.1f} seconds ({results['execution_time_seconds']/60:.1f} minutes)
- **Optimization Method**: {results['optimization_method']}
- **Metric Optimized**: {results['metric_optimized']}

## Best Parameters Found

**Optimal Configuration:**
- **RSI Oversold**: {best['rsi_oversold']}
- **RSI Overbought**: {best['rsi_overbought']}
- **EMA Fast**: {best['fast_period']}
- **EMA Slow**: {best['slow_period']}

**Performance Metrics:**
- **Sharpe Ratio**: {results['best_score']:.4f}
- **Win Rate**: {top_10[0]['win_rate']*100:.2f}%
- **Max Drawdown**: {top_10[0]['max_drawdown']*100:.2f}%
- **Total Profit**: ${top_10[0]['total_profit']:.2f}

## Key Findings

### 1. RSI Thresholds
- **Optimal Oversold**: {best['rsi_oversold']} (tested: 25, 30, 35, 40)
- **Optimal Overbought**: {best['rsi_overbought']} (tested: 60, 65, 70, 75)
- **Insight**: {'More conservative' if best['rsi_oversold'] >= 30 else 'More aggressive'} oversold threshold performs better

### 2. EMA Periods
- **Optimal Fast EMA**: {best['fast_period']} (tested: 9, 12, 15, 20)
- **Optimal Slow EMA**: {best['slow_period']} (tested: 21, 26, 30, 50)
- **Insight**: {'Faster' if best['fast_period'] <= 12 else 'Slower'} moving averages with {'standard' if best['slow_period'] == 26 else 'modified'} slow period

### 3. Risk-Adjusted Returns
- The optimal parameters achieve a Sharpe ratio of **{results['best_score']:.4f}**
- This represents {'strong' if results['best_score'] > 1.5 else 'moderate' if results['best_score'] > 1.0 else 'acceptable'} risk-adjusted performance
- Maximum drawdown maintained at **{top_10[0]['max_drawdown']*100:.2f}%** ({'✅ Below' if top_10[0]['max_drawdown'] < 0.20 else '⚠️ Above'} 20% threshold)

## Top 10 Parameter Combinations

| Rank | RSI (O/O) | EMA (F/S) | Sharpe | Win Rate | Max DD | Profit |
|------|-----------|-----------|--------|----------|--------|--------|
"""
    
    for i, r in enumerate(top_10, 1):
        p = r['params']
        report += f"| {i} | {p['rsi_oversold']}/{p['rsi_overbought']} | {p['fast_period']}/{p['slow_period']} | {r['sharpe_ratio']:.4f} | {r['win_rate']*100:.1f}% | {r['max_drawdown']*100:.1f}% | ${r['total_profit']:.2f} |\n"
    
    report += f"""
## Performance Comparison

### Current vs Optimized Parameters

| Configuration | RSI (O/O) | EMA (F/S) | Sharpe | Win Rate | Max DD |
|---------------|-----------|-----------|--------|----------|--------|
| **Optimized** | {best['rsi_oversold']}/{best['rsi_overbought']} | {best['fast_period']}/{best['slow_period']} | {results['best_score']:.4f} | {top_10[0]['win_rate']*100:.1f}% | {top_10[0]['max_drawdown']*100:.1f}% |
| Current Default | {current_params['rsi_oversold']}/{current_params['rsi_overbought']} | {current_params['fast_period']}/{current_params['slow_period']} | {'N/A' if not current_perf else f"{current_perf['sharpe_ratio']:.4f}"} | {'N/A' if not current_perf else f"{current_perf['win_rate']*100:.1f}%"} | {'N/A' if not current_perf else f"{current_perf['max_drawdown']*100:.1f}%"} |

"""
    
    if current_perf:
        improvement = ((results['best_score'] - current_perf['sharpe_ratio']) / abs(current_perf['sharpe_ratio'])) * 100
        report += f"**Improvement**: {improvement:+.1f}% in Sharpe ratio\n\n"
    
    report += f"""
## Recommendations

### ✅ Implementation Recommendation

**Update strategy configuration to use optimized parameters:**

```python
strategy = EMACrossoverStrategy(
    fast_period={best['fast_period']},
    slow_period={best['slow_period']},
    rsi_oversold={best['rsi_oversold']},
    rsi_overbought={best['rsi_overbought']}
)
```

### 📊 Validation Steps

1. **Out-of-Sample Testing**: Validate on 2024 data (if available)
2. **Walk-Forward Analysis**: Test on rolling windows
3. **Monte Carlo Simulation**: Assess robustness of returns
4. **Paper Trading**: Test in live market conditions before deployment

### ⚠️ Risk Considerations

- Optimization based on {'synthetic' if 'data/historical' not in str(results.get('data_source', 'synthetic')) else 'historical'} data
- Parameters may need adjustment for different market regimes
- Monitor performance and re-optimize periodically (every 3-6 months)
- Consider implementing dynamic parameter adjustment based on market volatility

## Appendix

### Methodology

- **Optimization Method**: Grid Search (exhaustive)
- **Metric**: Sharpe Ratio (risk-adjusted returns)
- **Constraints**: 
  - Maximum Drawdown < 20%
  - Minimum trades requirement
- **Commission**: 0.1% per trade
- **Slippage**: 0.05%

### Visualization

See `optimization_heatmap.png` for visual analysis of parameter performance across different combinations.

---

*Generated by yunmin optimization system on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    with open(output_path, 'w') as f:
        f.write(report)
    
    logger.success(f"Report saved to {output_path}")


def main():
    """Main execution function."""
    try:
        print("=" * 80)
        print("🎯 RSI/EMA Parameter Optimization")
        print("=" * 80)
        print()
        
        # Run optimization
        results, all_results = optimize()
        
        # Save results to JSON
        output_file = "optimization_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.success(f"Results saved to {output_file}")
        
        # Create visualizations
        create_heatmap(all_results)
        
        # Create report
        create_report(results)
        
        print()
        print("=" * 80)
        print("✅ Optimization Complete!")
        print("=" * 80)
        print()
        print(f"📊 Results: {output_file}")
        print(f"📈 Heatmap: optimization_heatmap.png")
        print(f"📝 Report: OPTIMIZATION_REPORT.md")
        print()
        print(f"🎯 Best Sharpe Ratio: {results['best_score']:.4f}")
        print(f"⚙️  Best Parameters: {results['best_params']}")
        print()
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise


if __name__ == "__main__":
    main()
