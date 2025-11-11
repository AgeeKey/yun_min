"""
Parameter Optimizer for Backtesting (Issue #40)

Provides grid search, random search, and walk-forward validation
for optimizing trading strategy parameters.
"""

import json
import itertools
import random
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger

from yunmin.backtesting.backtester import Backtester
from yunmin.backtesting.data_loader import HistoricalDataLoader


class ParameterOptimizer:
    """
    Optimize strategy parameters using various methods.

    Supports:
    - Grid search: exhaustive search over parameter grid
    - Random search: random sampling from parameter space
    - Walk-forward validation: rolling window optimization
    """

    def __init__(self, strategy_class: type, data: pd.DataFrame, metric: str = "sharpe_ratio"):
        """
        Initialize optimizer.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical data for backtesting
            metric: Optimization metric (sharpe_ratio, total_pnl, win_rate)
        """
        self.strategy_class = strategy_class
        self.data = data
        self.metric = metric
        self.results: List[Dict[str, Any]] = []
        logger.info(
            f"Optimizer initialized for {strategy_class.__name__}, "
            f"metric={metric}, data_size={len(data)}"
        )

    def grid_search(
        self,
        param_grid: Dict[str, List],
        backtest_config: Optional[Dict[str, Any]] = None,
        max_combinations: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Perform grid search over parameter combinations.

        Args:
            param_grid: Dictionary mapping parameter names to lists of values
            backtest_config: Configuration for backtester
            max_combinations: Maximum combinations to test (None = all)

        Returns:
            DataFrame with results sorted by metric
        """
        logger.info(f"Starting grid search over {param_grid}")

        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))

        if max_combinations and len(combinations) > max_combinations:
            logger.warning(f"Limiting to {max_combinations} of {len(combinations)} combinations")
            combinations = random.sample(combinations, max_combinations)

        logger.info(f"Testing {len(combinations)} parameter combinations")

        backtest_config = backtest_config or {}
        results = []

        for i, combo in enumerate(combinations, 1):
            params = dict(zip(param_names, combo))
            logger.debug(f"Testing combination {i}/{len(combinations)}: {params}")

            try:
                result = self._test_parameters(params, backtest_config)
                results.append(result)
            except Exception as e:
                logger.error(f"Error testing {params}: {e}")
                continue

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(combinations)} combinations tested")

        self.results = results
        df_results = pd.DataFrame(results)

        # Sort by metric (higher is better for most metrics)
        if self.metric in ["max_drawdown"]:
            df_results = df_results.sort_values(self.metric, ascending=True)
        else:
            df_results = df_results.sort_values(self.metric, ascending=False)

        logger.info(
            f"Grid search complete. Best {self.metric}: " f"{df_results.iloc[0][self.metric]:.4f}"
        )

        return df_results

    def random_search(
        self,
        param_ranges: Dict[str, Tuple],
        n_iterations: int = 100,
        backtest_config: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Perform random search over parameter space.

        Args:
            param_ranges: Dict mapping parameter names to (min, max) tuples
            n_iterations: Number of random samples to test
            backtest_config: Configuration for backtester

        Returns:
            DataFrame with results sorted by metric
        """
        logger.info(f"Starting random search with {n_iterations} iterations")

        backtest_config = backtest_config or {}
        results = []

        for i in range(n_iterations):
            # Sample random parameters
            params = {}
            for param_name, (min_val, max_val) in param_ranges.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = random.randint(min_val, max_val)
                else:
                    params[param_name] = random.uniform(min_val, max_val)

            logger.debug(f"Testing iteration {i+1}/{n_iterations}: {params}")

            try:
                result = self._test_parameters(params, backtest_config)
                results.append(result)
            except Exception as e:
                logger.error(f"Error testing {params}: {e}")
                continue

            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{n_iterations} iterations tested")

        self.results = results
        df_results = pd.DataFrame(results)

        # Sort by metric
        if self.metric in ["max_drawdown"]:
            df_results = df_results.sort_values(self.metric, ascending=True)
        else:
            df_results = df_results.sort_values(self.metric, ascending=False)

        logger.info(
            f"Random search complete. Best {self.metric}: " f"{df_results.iloc[0][self.metric]:.4f}"
        )

        return df_results

    def walk_forward(
        self,
        param_grid: Dict[str, List],
        train_size: int = 1000,
        test_size: int = 200,
        n_splits: int = 5,
        backtest_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform walk-forward validation.

        Train on in-sample data, test on out-of-sample data, rolling forward.

        Args:
            param_grid: Parameter grid for optimization
            train_size: Number of bars for training window
            test_size: Number of bars for testing window
            n_splits: Number of walk-forward splits
            backtest_config: Configuration for backtester

        Returns:
            Dictionary with walk-forward results
        """
        logger.info(
            f"Starting walk-forward validation: train={train_size}, "
            f"test={test_size}, splits={n_splits}"
        )

        backtest_config = backtest_config or {}
        total_bars = len(self.data)

        if train_size + test_size > total_bars:
            raise ValueError(
                f"train_size + test_size ({train_size + test_size}) "
                f"exceeds data length ({total_bars})"
            )

        wf_results = []

        for split in range(n_splits):
            # Calculate window
            start_idx = split * test_size
            train_end = start_idx + train_size
            test_end = train_end + test_size

            if test_end > total_bars:
                logger.warning(f"Split {split+1} exceeds data length, stopping")
                break

            train_data = self.data.iloc[start_idx:train_end]
            test_data = self.data.iloc[train_end:test_end]

            logger.info(
                f"Split {split+1}/{n_splits}: train=[{start_idx}:{train_end}], "
                f"test=[{train_end}:{test_end}]"
            )

            # Optimize on training data
            train_optimizer = ParameterOptimizer(self.strategy_class, train_data, self.metric)
            train_results = train_optimizer.grid_search(
                param_grid, backtest_config, max_combinations=50
            )

            # Get best parameters
            best_params = train_results.iloc[0][list(param_grid.keys())].to_dict()
            logger.info(f"Best params for split {split+1}: {best_params}")

            # Test on out-of-sample data
            test_optimizer = ParameterOptimizer(self.strategy_class, test_data, self.metric)
            test_result = test_optimizer._test_parameters(best_params, backtest_config)

            wf_results.append(
                {
                    "split": split + 1,
                    "train_start": start_idx,
                    "train_end": train_end,
                    "test_start": train_end,
                    "test_end": test_end,
                    "best_params": best_params,
                    "train_metric": train_results.iloc[0][self.metric],
                    "test_metric": test_result[self.metric],
                    "test_results": test_result,
                }
            )

        # Calculate aggregate metrics
        test_metrics = [r["test_metric"] for r in wf_results]

        summary = {
            "n_splits": len(wf_results),
            "avg_test_metric": np.mean(test_metrics),
            "std_test_metric": np.std(test_metrics),
            "min_test_metric": np.min(test_metrics),
            "max_test_metric": np.max(test_metrics),
            "splits": wf_results,
        }

        logger.info(
            f"Walk-forward complete. Avg test {self.metric}: "
            f"{summary['avg_test_metric']:.4f} ± {summary['std_test_metric']:.4f}"
        )

        return summary

    def _test_parameters(
        self, params: Dict[str, Any], backtest_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test a single parameter set.

        Args:
            params: Strategy parameters
            backtest_config: Backtester configuration

        Returns:
            Dictionary with parameters and backtest results
        """
        # Create strategy with parameters
        strategy = self.strategy_class(**params)

        # Create backtester
        backtester = Backtester(strategy=strategy, **backtest_config)

        # Run backtest
        results = backtester.run(self.data)

        # Combine parameters and results
        output = params.copy()
        output.update(results)

        return output

    def save_results(self, filepath: str):
        """
        Save optimization results to JSON file.

        Args:
            filepath: Path to save results
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self.strategy_class.__name__,
            "metric": self.metric,
            "data_size": len(self.data),
            "results": self.results,
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(output, f, indent=2, default=str)

        logger.info(f"Results saved to {filepath}")


def load_optimizer_config(config_path: str) -> Dict[str, Any]:
    """
    Load optimizer configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary
    """
    import yaml

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config.get("optimizer", {})


if __name__ == "__main__":
    # Example usage
    from yunmin.strategy.ema_crossover import EMACrossoverStrategy

    # Generate sample data
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT", start_price=50000, num_candles=2000, trend="uptrend"
    )

    # Create optimizer
    optimizer = ParameterOptimizer(
        strategy_class=EMACrossoverStrategy, data=data, metric="sharpe_ratio"
    )

    # Grid search example
    param_grid = {"fast_period": [5, 10, 15], "slow_period": [20, 30, 40]}

    backtest_config = {
        "initial_capital": 100000.0,
        "position_size_pct": 0.01,
        "use_risk_manager": False,
    }

    results = optimizer.grid_search(param_grid, backtest_config)

    print("\nTop 5 Results:")
    print(results.head())

    # Save results
    optimizer.save_results("optimization_results.json")
