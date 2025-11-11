"""
Unit tests for parameter optimizer (Issue #40).

Tests:
- Grid search
- Random search
- Walk-forward validation
- Results export
"""
import pytest
import pandas as pd
import numpy as np
import json
import tempfile
import os
from datetime import datetime, timedelta

from tools.optimizer import ParameterOptimizer
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class SimpleStrategy(BaseStrategy):
    """Simple test strategy with configurable parameters."""
    
    def __init__(self, threshold: float = 0.5, period: int = 10):
        super().__init__("simple")
        self.threshold = threshold
        self.period = period
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        if len(data) < self.period:
            return Signal(type=SignalType.HOLD, confidence=0.0, reason="Insufficient data")
        
        # Simple logic: buy if close > threshold * 100
        if data['close'].iloc[-1] > self.threshold * 50000:
            return Signal(type=SignalType.BUY, confidence=0.8, reason="Above threshold")
        else:
            return Signal(type=SignalType.HOLD, confidence=0.0, reason="Below threshold")


def generate_test_data(n_bars=500):
    """Generate test data."""
    timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n_bars)]
    prices = np.linspace(40000, 60000, n_bars) + np.random.randn(n_bars) * 500
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(1000, 2000, n_bars)
    })


def test_optimizer_initialization():
    """Test optimizer initialization."""
    data = generate_test_data(500)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='sharpe_ratio'
    )
    
    assert optimizer.strategy_class == SimpleStrategy
    assert len(optimizer.data) == 500
    assert optimizer.metric == 'sharpe_ratio'
    assert len(optimizer.results) == 0


def test_grid_search():
    """Test grid search optimization."""
    data = generate_test_data(500)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='total_pnl'
    )
    
    param_grid = {
        'threshold': [0.8, 0.9, 1.0],
        'period': [5, 10, 15]
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'position_size_pct': 0.1,
        'use_risk_manager': False
    }
    
    results = optimizer.grid_search(param_grid, backtest_config)
    
    # Should test 3 x 3 = 9 combinations
    assert len(results) <= 9
    assert 'threshold' in results.columns
    assert 'period' in results.columns
    assert 'total_pnl' in results.columns
    
    # Results should be sorted by metric
    pnl_values = results['total_pnl'].values
    assert list(pnl_values) == sorted(pnl_values, reverse=True)


def test_grid_search_with_limit():
    """Test grid search with max_combinations limit."""
    data = generate_test_data(500)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='win_rate'
    )
    
    param_grid = {
        'threshold': [0.7, 0.8, 0.9, 1.0, 1.1],
        'period': [5, 10, 15, 20]
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'use_risk_manager': False
    }
    
    # Limit to 10 combinations (would be 5 x 4 = 20 otherwise)
    results = optimizer.grid_search(param_grid, backtest_config, max_combinations=10)
    
    assert len(results) <= 10


def test_random_search():
    """Test random search optimization."""
    data = generate_test_data(500)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='sharpe_ratio'
    )
    
    param_ranges = {
        'threshold': (0.5, 1.5),
        'period': (5, 20)
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'position_size_pct': 0.1,
        'use_risk_manager': False
    }
    
    results = optimizer.random_search(param_ranges, n_iterations=20, 
                                     backtest_config=backtest_config)
    
    # Should test 20 random combinations
    assert len(results) <= 20
    assert 'threshold' in results.columns
    assert 'period' in results.columns
    assert 'sharpe_ratio' in results.columns
    
    # Check parameter values are within ranges
    assert results['threshold'].min() >= 0.5
    assert results['threshold'].max() <= 1.5
    assert results['period'].min() >= 5
    assert results['period'].max() <= 20


def test_walk_forward_validation():
    """Test walk-forward validation."""
    data = generate_test_data(1500)  # Need more data for walk-forward
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='total_pnl'
    )
    
    param_grid = {
        'threshold': [0.9, 1.0],
        'period': [10, 15]
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'position_size_pct': 0.1,
        'use_risk_manager': False
    }
    
    wf_results = optimizer.walk_forward(
        param_grid,
        train_size=500,
        test_size=200,
        n_splits=3,
        backtest_config=backtest_config
    )
    
    # Check structure
    assert 'n_splits' in wf_results
    assert 'avg_test_metric' in wf_results
    assert 'std_test_metric' in wf_results
    assert 'splits' in wf_results
    
    # Should have 3 splits
    assert len(wf_results['splits']) <= 3
    
    # Each split should have required keys
    for split in wf_results['splits']:
        assert 'split' in split
        assert 'best_params' in split
        assert 'train_metric' in split
        assert 'test_metric' in split


def test_save_results():
    """Test saving optimization results."""
    data = generate_test_data(300)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='total_pnl'
    )
    
    param_grid = {
        'threshold': [0.9, 1.0],
        'period': [10, 15]
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'use_risk_manager': False
    }
    
    # Run optimization
    results = optimizer.grid_search(param_grid, backtest_config)
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        filepath = f.name
    
    try:
        optimizer.save_results(filepath)
        
        # Check file exists
        assert os.path.exists(filepath)
        
        # Load and verify
        with open(filepath) as f:
            saved_data = json.load(f)
        
        assert 'timestamp' in saved_data
        assert 'strategy' in saved_data
        assert 'metric' in saved_data
        assert 'results' in saved_data
        assert saved_data['strategy'] == 'SimpleStrategy'
        assert saved_data['metric'] == 'total_pnl'
        assert len(saved_data['results']) > 0
        
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


def test_different_metrics():
    """Test optimization with different metrics."""
    data = generate_test_data(400)
    
    param_grid = {
        'threshold': [0.9, 1.0],
        'period': [10]
    }
    
    backtest_config = {
        'initial_capital': 10000.0,
        'use_risk_manager': False
    }
    
    metrics = ['total_pnl', 'win_rate', 'sharpe_ratio']
    
    for metric in metrics:
        optimizer = ParameterOptimizer(
            strategy_class=SimpleStrategy,
            data=data,
            metric=metric
        )
        
        results = optimizer.grid_search(param_grid, backtest_config)
        
        # Should have results
        assert len(results) > 0
        assert metric in results.columns


def test_empty_parameter_grid():
    """Test with empty parameter grid (all defaults)."""
    data = generate_test_data(300)
    
    optimizer = ParameterOptimizer(
        strategy_class=SimpleStrategy,
        data=data,
        metric='total_pnl'
    )
    
    param_grid = {}  # Empty grid - will use defaults
    
    backtest_config = {
        'initial_capital': 10000.0,
        'use_risk_manager': False
    }
    
    # Should handle empty grid gracefully
    results = optimizer.grid_search(param_grid, backtest_config)
    
    # Should have 1 result (default parameters)
    assert len(results) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
