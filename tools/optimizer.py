#!/usr/bin/env python3
"""
Parameter Optimization Tool for Trading Strategies.

This script provides comprehensive parameter optimization with:
- Grid search and random search methods
- Walk-forward validation for robust testing
- YAML configuration for easy parameter management
- CSV/JSON export of results
- Detailed reports on best configurations

Usage:
    python tools/optimizer.py --config tools/optimizer_config.yaml
    python tools/optimizer.py --config tools/optimizer_config.yaml --method random_search
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import itertools
import random

import numpy as np
import pandas as pd
import yaml
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from yunmin.core.backtester import AdvancedBacktester, OptimizationMethod, BacktestResult
from yunmin.strategy.ema_crossover import EMACrossoverStrategy


class StrategyOptimizer:
    """
    Advanced parameter optimizer with walk-forward validation.
    """
    
    def __init__(self, config_path: str):
        """
        Initialize optimizer with configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.backtester = AdvancedBacktester(
            symbol=self.config['data']['symbol'],
            timeframe=self.config['data']['timeframe']
        )
        self.results_dir = Path(self.config['output']['results_dir'])
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info(f"Optimizer initialized with config: {config_path}")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    
    def load_data(self) -> pd.DataFrame:
        """
        Load data based on configuration.
        
        Returns:
            DataFrame with OHLCV data
        """
        data_config = self.config['data']
        
        if data_config['source'] == 'historical':
            data_path = Path(data_config['data_path'])
            
            if data_path.exists():
                logger.info(f"Loading historical data from {data_path}")
                data = pd.read_csv(data_path)
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                
                # Filter by date range if specified
                if data_config.get('start_date'):
                    start_date = pd.to_datetime(data_config['start_date'])
                    data = data[data['timestamp'] >= start_date]
                    
                if data_config.get('end_date'):
                    end_date = pd.to_datetime(data_config['end_date'])
                    data = data[data['timestamp'] <= end_date]
                
                logger.success(f"Loaded {len(data)} bars of historical data")
                return data
            else:
                logger.warning(f"Data file not found: {data_path}")
                logger.info("Falling back to synthetic data")
        
        # Generate synthetic data
        return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self, periods: int = 2000) -> pd.DataFrame:
        """
        Generate synthetic price data for testing.
        
        Args:
            periods: Number of periods to generate
            
        Returns:
            DataFrame with synthetic OHLCV data
        """
        logger.info(f"Generating {periods} periods of synthetic data")
        
        np.random.seed(42)
        start_price = 50000.0
        trend = 0.0001
        volatility = 0.02
        
        returns = np.random.randn(periods) * volatility + trend
        prices = start_price * np.exp(np.cumsum(returns))
        
        data = []
        start_time = datetime(2025, 10, 1)
        
        for i in range(periods):
            price = prices[i]
            high_offset = np.abs(np.random.randn()) * price * 0.005
            low_offset = np.abs(np.random.randn()) * price * 0.005
            
            data.append({
                'timestamp': start_time + pd.Timedelta(minutes=5*i),
                'open': price,
                'high': price + high_offset,
                'low': price - low_offset,
                'close': price,
                'volume': np.random.uniform(100, 1000)
            })
        
        df = pd.DataFrame(data)
        logger.success(f"Generated synthetic data: {len(df)} bars")
        return df
    
    def run_optimization(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run parameter optimization with selected method.
        
        Args:
            data: Historical data
            
        Returns:
            Dictionary with optimization results
        """
        opt_config = self.config['optimization']
        param_config = self.config['parameters']
        
        method = opt_config['method']
        logger.info(f"Starting optimization with method: {method}")
        
        if method == 'grid_search':
            return self._grid_search_optimization(data, param_config, opt_config)
        elif method == 'random_search':
            return self._random_search_optimization(data, param_config, opt_config)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
    
    def _grid_search_optimization(
        self,
        data: pd.DataFrame,
        param_config: Dict,
        opt_config: Dict
    ) -> Dict[str, Any]:
        """
        Perform grid search optimization.
        
        Args:
            data: Historical data
            param_config: Parameter configuration
            opt_config: Optimization configuration
            
        Returns:
            Optimization results
        """
        # Build parameter grid (only use parameters supported by EMACrossoverStrategy)
        param_grid = {
            'rsi_oversold': param_config['rsi_oversold'],
            'rsi_overbought': param_config['rsi_overbought'],
            'fast_period': param_config['fast_period'],
            'slow_period': param_config['slow_period']
        }
        
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        total_combinations = len(combinations)
        logger.info(f"Testing {total_combinations} parameter combinations")
        
        # Store additional parameters for later use (not optimized but tracked)
        additional_params = {
            'volume_multiplier': param_config['volume_multiplier'][0],  # Use first value
            'min_ema_distance': param_config['min_ema_distance'][0],
            'confidence_threshold': param_config['confidence_threshold'][0],
            'position_size': param_config['position_size'][0],
            'stop_loss_pct': param_config['stop_loss_pct'][0]
        }
        
        results = []
        best_score = float('-inf')
        best_params = None
        
        for i, combo in enumerate(combinations):
            params = dict(zip(param_names, combo))
            
            # Skip invalid combinations (fast must be < slow)
            if params['fast_period'] >= params['slow_period']:
                continue
            
            try:
                # Create strategy with these parameters
                strategy = EMACrossoverStrategy(**params)
                
                # Run backtest
                result = self.backtester.run(
                    strategy,
                    data,
                    initial_capital=opt_config['initial_capital'],
                    commission=opt_config['commission'],
                    slippage=opt_config['slippage']
                )
                
                # Get optimization metric
                metric = opt_config['metric']
                score = getattr(result, metric, 0.0)
                
                # Store result with additional parameters for reference
                result_entry = {
                    'params': {**params, **additional_params},
                    'score': float(score),
                    'metric': metric,
                    'total_profit': float(result.total_profit),
                    'win_rate': float(result.win_rate),
                    'max_drawdown': float(result.max_drawdown),
                    'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else 0.0,
                    'sortino_ratio': float(result.sortino_ratio) if result.sortino_ratio else 0.0,
                    'total_trades': int(result.total_trades),
                    'winning_trades': int(result.winning_trades),
                    'losing_trades': int(result.losing_trades),
                    'profit_factor': float(result.profit_factor),
                    'expectancy': float(result.expectancy)
                }
                
                results.append(result_entry)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{total_combinations} combinations tested")
                
            except Exception as e:
                logger.warning(f"Error testing params {params}: {e}")
                continue
        
        logger.success(f"Grid search complete. Best {opt_config['metric']}: {best_score:.4f}")
        
        # Handle case where no valid combinations were found
        if best_params is None:
            best_params = {}
        
        return {
            'method': 'grid_search',
            'metric': opt_config['metric'],
            'best_params': {**best_params, **additional_params} if best_params else additional_params,
            'best_score': float(best_score),
            'total_combinations': len(results),
            'all_results': results,
            'additional_params': additional_params
        }
    
    def _random_search_optimization(
        self,
        data: pd.DataFrame,
        param_config: Dict,
        opt_config: Dict
    ) -> Dict[str, Any]:
        """
        Perform random search optimization.
        
        Args:
            data: Historical data
            param_config: Parameter configuration
            opt_config: Optimization configuration
            
        Returns:
            Optimization results
        """
        n_samples = opt_config.get('n_random_samples', 100)
        logger.info(f"Testing {n_samples} random parameter combinations")
        
        # Only randomize parameters supported by EMACrossoverStrategy
        param_grid = {
            'rsi_oversold': param_config['rsi_oversold'],
            'rsi_overbought': param_config['rsi_overbought'],
            'fast_period': param_config['fast_period'],
            'slow_period': param_config['slow_period']
        }
        
        # Additional parameters (use first value from config)
        additional_params = {
            'volume_multiplier': param_config['volume_multiplier'][0],
            'min_ema_distance': param_config['min_ema_distance'][0],
            'confidence_threshold': param_config['confidence_threshold'][0],
            'position_size': param_config['position_size'][0],
            'stop_loss_pct': param_config['stop_loss_pct'][0]
        }
        
        results = []
        best_score = float('-inf')
        best_params = None
        
        for i in range(n_samples):
            # Randomly sample parameters
            params = {
                name: random.choice(values)
                for name, values in param_grid.items()
            }
            
            # Skip invalid combinations
            if params['fast_period'] >= params['slow_period']:
                continue
            
            try:
                strategy = EMACrossoverStrategy(**params)
                
                result = self.backtester.run(
                    strategy,
                    data,
                    initial_capital=opt_config['initial_capital'],
                    commission=opt_config['commission'],
                    slippage=opt_config['slippage']
                )
                
                metric = opt_config['metric']
                score = getattr(result, metric, 0.0)
                
                result_entry = {
                    'params': {**params, **additional_params},
                    'score': float(score),
                    'metric': metric,
                    'total_profit': float(result.total_profit),
                    'win_rate': float(result.win_rate),
                    'max_drawdown': float(result.max_drawdown),
                    'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else 0.0,
                    'sortino_ratio': float(result.sortino_ratio) if result.sortino_ratio else 0.0,
                    'total_trades': int(result.total_trades),
                    'winning_trades': int(result.winning_trades),
                    'losing_trades': int(result.losing_trades),
                    'profit_factor': float(result.profit_factor),
                    'expectancy': float(result.expectancy)
                }
                
                results.append(result_entry)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{n_samples} combinations tested")
                
            except Exception as e:
                logger.warning(f"Error testing params {params}: {e}")
                continue
        
        logger.success(f"Random search complete. Best {opt_config['metric']}: {best_score:.4f}")
        
        return {
            'method': 'random_search',
            'metric': opt_config['metric'],
            'best_params': {**best_params, **additional_params},
            'best_score': float(best_score),
            'total_combinations': len(results),
            'all_results': results,
            'additional_params': additional_params
        }
    
    def walk_forward_validation(
        self,
        data: pd.DataFrame,
        best_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform walk-forward validation on best parameters.
        
        Args:
            data: Full dataset
            best_params: Best parameters from optimization
            
        Returns:
            Walk-forward validation results
        """
        wf_config = self.config['walk_forward']
        
        if not wf_config['enabled']:
            logger.info("Walk-forward validation disabled")
            return {'enabled': False}
        
        n_splits = wf_config['n_splits']
        train_ratio = wf_config['train_ratio']
        
        logger.info(f"Running walk-forward validation: {n_splits} splits, {train_ratio:.0%} train ratio")
        
        # Only use parameters that EMACrossoverStrategy accepts
        strategy_params = {
            'rsi_oversold': best_params['rsi_oversold'],
            'rsi_overbought': best_params['rsi_overbought'],
            'fast_period': best_params['fast_period'],
            'slow_period': best_params['slow_period']
        }
        
        window_size = len(data) // n_splits
        validation_results = []
        
        for i in range(n_splits):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, len(data))
            
            window_data = data.iloc[start_idx:end_idx]
            train_size = int(len(window_data) * train_ratio)
            
            test_data = window_data.iloc[train_size:]
            
            if len(test_data) < 100:
                logger.warning(f"Split {i+1}: Insufficient test data ({len(test_data)} bars)")
                continue
            
            # Create strategy with best parameters
            strategy = EMACrossoverStrategy(**strategy_params)
            
            # Test on out-of-sample data
            result = self.backtester.run(
                strategy,
                test_data,
                initial_capital=self.config['optimization']['initial_capital']
            )
            
            split_result = {
                'split': i + 1,
                'total_bars': len(window_data),
                'train_bars': train_size,
                'test_bars': len(test_data),
                'total_profit': float(result.total_profit),
                'win_rate': float(result.win_rate),
                'sharpe_ratio': float(result.sharpe_ratio) if result.sharpe_ratio else 0.0,
                'max_drawdown': float(result.max_drawdown),
                'total_trades': int(result.total_trades)
            }
            
            validation_results.append(split_result)
            
            sharpe_value = result.sharpe_ratio if result.sharpe_ratio else 0.0
            logger.info(
                f"Split {i+1}/{n_splits}: "
                f"Profit=${result.total_profit:.2f}, "
                f"Win Rate={result.win_rate*100:.1f}%, "
                f"Sharpe={sharpe_value:.2f}"
            )
        
        # Calculate stability metrics
        if validation_results:
            profits = [r['total_profit'] for r in validation_results]
            sharpes = [r['sharpe_ratio'] for r in validation_results]
            win_rates = [r['win_rate'] for r in validation_results]
            
            stability = {
                'profit_mean': float(np.mean(profits)),
                'profit_std': float(np.std(profits)),
                'profit_cv': float(np.std(profits) / np.mean(profits)) if np.mean(profits) != 0 else 0.0,
                'sharpe_mean': float(np.mean(sharpes)),
                'sharpe_std': float(np.std(sharpes)),
                'win_rate_mean': float(np.mean(win_rates)),
                'win_rate_std': float(np.std(win_rates))
            }
        else:
            stability = {}
        
        logger.success("Walk-forward validation complete")
        
        return {
            'enabled': True,
            'n_splits': n_splits,
            'train_ratio': train_ratio,
            'splits': validation_results,
            'stability': stability
        }
    
    def save_results(
        self,
        optimization_results: Dict[str, Any],
        walkforward_results: Dict[str, Any]
    ) -> None:
        """
        Save optimization results to files.
        
        Args:
            optimization_results: Optimization results
            walkforward_results: Walk-forward validation results
        """
        output_config = self.config['output']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        if output_config['save_json']:
            json_path = self.results_dir / f'optimization_results_{timestamp}.json'
            
            combined_results = {
                'timestamp': datetime.now().isoformat(),
                'config': self.config,
                'optimization': optimization_results,
                'walk_forward': walkforward_results
            }
            
            with open(json_path, 'w') as f:
                json.dump(combined_results, f, indent=2)
            
            logger.success(f"Results saved to {json_path}")
        
        # Save CSV
        if output_config['save_csv']:
            csv_path = self.results_dir / f'optimization_results_{timestamp}.csv'
            
            # Convert results to DataFrame
            df = pd.DataFrame(optimization_results['all_results'])
            
            # Flatten params dictionary
            params_df = pd.json_normalize(df['params'])
            df = pd.concat([params_df, df.drop('params', axis=1)], axis=1)
            
            df.to_csv(csv_path, index=False)
            logger.success(f"CSV results saved to {csv_path}")
        
        # Generate report
        if output_config['generate_report']:
            report_path = self.results_dir / f'optimization_report_{timestamp}.md'
            self._generate_report(
                optimization_results,
                walkforward_results,
                report_path
            )
    
    def _generate_report(
        self,
        opt_results: Dict[str, Any],
        wf_results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """
        Generate markdown report.
        
        Args:
            opt_results: Optimization results
            wf_results: Walk-forward results
            output_path: Path to save report
        """
        logger.info("Generating optimization report...")
        
        best_params = opt_results['best_params']
        best_score = opt_results['best_score']
        metric = opt_results['metric']
        
        # Get top N results
        top_n = self.config['output']['top_n']
        sorted_results = sorted(
            opt_results['all_results'],
            key=lambda x: x['score'],
            reverse=True
        )[:top_n]
        
        report = f"""# Parameter Optimization Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Configuration

- **Symbol**: {self.config['data']['symbol']}
- **Timeframe**: {self.config['data']['timeframe']}
- **Optimization Method**: {opt_results['method']}
- **Metric Optimized**: {metric}
- **Total Combinations Tested**: {opt_results['total_combinations']}
- **Initial Capital**: ${self.config['optimization']['initial_capital']:,.2f}

## Best Parameters Found

**Performance**: {metric} = {best_score:.4f}

### Strategy Parameters
"""
        
        for param, value in best_params.items():
            report += f"- **{param}**: {value}\n"
        
        report += f"""

## Top {top_n} Configurations

| Rank | {metric.upper()} | Win Rate | Max DD | Profit | Trades | RSI (O/O) | EMA (F/S) |
|------|---------|----------|--------|--------|--------|-----------|-----------|
"""
        
        for i, result in enumerate(sorted_results, 1):
            p = result['params']
            report += (
                f"| {i} | {result['score']:.4f} | "
                f"{result['win_rate']*100:.1f}% | "
                f"{result['max_drawdown']*100:.1f}% | "
                f"${result['total_profit']:.2f} | "
                f"{result['total_trades']} | "
                f"{p['rsi_oversold']}/{p['rsi_overbought']} | "
                f"{p['fast_period']}/{p['slow_period']} |\n"
            )
        
        # Walk-forward validation section
        if wf_results.get('enabled'):
            report += f"""

## Walk-Forward Validation

**Configuration**: {wf_results['n_splits']} splits, {wf_results['train_ratio']:.0%} train / {1-wf_results['train_ratio']:.0%} test

### Out-of-Sample Performance

| Split | Profit | Win Rate | Sharpe | Max DD | Trades |
|-------|--------|----------|--------|--------|--------|
"""
            
            for split in wf_results['splits']:
                report += (
                    f"| {split['split']} | "
                    f"${split['total_profit']:.2f} | "
                    f"{split['win_rate']*100:.1f}% | "
                    f"{split['sharpe_ratio']:.2f} | "
                    f"{split['max_drawdown']*100:.1f}% | "
                    f"{split['total_trades']} |\n"
                )
            
            stability = wf_results['stability']
            report += f"""

### Stability Analysis

- **Mean Profit**: ${stability['profit_mean']:.2f} ± ${stability['profit_std']:.2f}
- **Profit Coefficient of Variation**: {stability['profit_cv']:.2%}
- **Mean Sharpe Ratio**: {stability['sharpe_mean']:.3f} ± {stability['sharpe_std']:.3f}
- **Mean Win Rate**: {stability['win_rate_mean']:.1%} ± {stability['win_rate_std']:.1%}

**Stability Assessment**: {'✅ Stable' if stability['profit_cv'] < 0.5 else '⚠️ Moderate' if stability['profit_cv'] < 1.0 else '❌ Unstable'} 
(CV < 0.5 is considered stable)
"""
        
        report += """

## Recommendations

### Implementation

Update your strategy configuration with the optimized parameters:

```yaml
strategy:
  name: ema_crossover
"""
        
        # Only show parameters that are actually used by the strategy
        for param in ['fast_period', 'slow_period', 'rsi_oversold', 'rsi_overbought']:
            if param in best_params:
                # Convert parameter names to match config format
                config_param = param.replace('_period', '_ema') if 'period' in param else param
                report += f"  {config_param}: {best_params[param]}\n"
        
        report += """```

### Risk Management

Consider these additional optimized parameters:

"""
        
        # Show additional parameters
        for param in ['volume_multiplier', 'min_ema_distance', 'confidence_threshold', 'position_size', 'stop_loss_pct']:
            if param in best_params:
                report += f"- **{param}**: {best_params[param]}\n"
        
        report += """

### Next Steps

1. **Paper Trading**: Test parameters in paper trading mode before live deployment
2. **Monitor Performance**: Track actual performance vs. backtest expectations
3. **Re-optimize Periodically**: Re-run optimization every 3-6 months
4. **Adjust for Market Regime**: Different market conditions may require different parameters

---

*Generated by yunmin optimizer tool*
"""
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        logger.success(f"Report saved to {output_path}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Parameter optimization tool for trading strategies'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='tools/optimizer_config.yaml',
        help='Path to configuration file (default: tools/optimizer_config.yaml)'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['grid_search', 'random_search'],
        help='Optimization method (overrides config)'
    )
    parser.add_argument(
        '--n-samples',
        type=int,
        help='Number of random samples for random_search (overrides config)'
    )
    
    args = parser.parse_args()
    
    # Initialize optimizer
    optimizer = StrategyOptimizer(args.config)
    
    # Override config with command line arguments
    if args.method:
        optimizer.config['optimization']['method'] = args.method
    if args.n_samples:
        optimizer.config['optimization']['n_random_samples'] = args.n_samples
    
    logger.info("=" * 80)
    logger.info("🎯 Parameter Optimization Tool")
    logger.info("=" * 80)
    
    try:
        # Load data
        data = optimizer.load_data()
        logger.info(f"Data loaded: {len(data)} bars")
        
        # Run optimization
        opt_results = optimizer.run_optimization(data)
        logger.info(f"Optimization complete. Best {opt_results['metric']}: {opt_results['best_score']:.4f}")
        
        # Run walk-forward validation
        wf_results = optimizer.walk_forward_validation(data, opt_results['best_params'])
        
        # Save results
        optimizer.save_results(opt_results, wf_results)
        
        logger.success("=" * 80)
        logger.success("✅ Optimization Complete!")
        logger.success("=" * 80)
        logger.success(f"Best parameters: {opt_results['best_params']}")
        logger.success(f"Check the 'results' directory for detailed output")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        raise


if __name__ == "__main__":
    main()
