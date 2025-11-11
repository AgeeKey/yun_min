"""
Unit tests for parameter optimization tool.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

# Import the optimizer
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.optimizer import StrategyOptimizer


@pytest.fixture
def sample_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    periods = 500
    
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
    
    return pd.DataFrame(data)


@pytest.fixture
def minimal_config():
    """Create minimal configuration for testing."""
    return {
        'data': {
            'source': 'synthetic',
            'data_path': 'data/historical/btc_usdt_5m_2025.csv',
            'symbol': 'BTC/USDT',
            'timeframe': '5m',
            'start_date': None,
            'end_date': None
        },
        'optimization': {
            'method': 'grid_search',
            'n_random_samples': 10,
            'metric': 'sharpe_ratio',
            'initial_capital': 10000.0,
            'commission': 0.001,
            'slippage': 0.0005
        },
        'walk_forward': {
            'enabled': True,
            'n_splits': 2,
            'train_ratio': 0.7
        },
        'parameters': {
            'rsi_oversold': [30, 35],
            'rsi_overbought': [65, 70],
            'fast_period': [9, 12],
            'slow_period': [21, 26],
            'volume_multiplier': [1.2, 1.5],
            'min_ema_distance': [0.003, 0.005],
            'confidence_threshold': [0.6, 0.7],
            'position_size': [0.02, 0.05],
            'stop_loss_pct': [0.02, 0.03]
        },
        'output': {
            'results_dir': 'results',
            'save_json': True,
            'save_csv': True,
            'generate_report': True,
            'generate_heatmaps': False,
            'top_n': 5
        }
    }


@pytest.fixture
def config_file(minimal_config, tmp_path):
    """Create a temporary config file."""
    config_path = tmp_path / "test_config.yaml"
    
    with open(config_path, 'w') as f:
        yaml.dump(minimal_config, f)
    
    return str(config_path)


class TestStrategyOptimizer:
    """Test suite for StrategyOptimizer."""
    
    def test_initialization(self, config_file):
        """Test optimizer initialization."""
        optimizer = StrategyOptimizer(config_file)
        
        assert optimizer.config is not None
        assert optimizer.backtester is not None
        assert optimizer.results_dir.exists()
    
    def test_load_config(self, config_file, minimal_config):
        """Test configuration loading."""
        optimizer = StrategyOptimizer(config_file)
        
        assert optimizer.config['data']['symbol'] == minimal_config['data']['symbol']
        assert optimizer.config['optimization']['method'] == minimal_config['optimization']['method']
    
    def test_generate_synthetic_data(self, config_file):
        """Test synthetic data generation."""
        optimizer = StrategyOptimizer(config_file)
        
        data = optimizer._generate_synthetic_data(periods=100)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 100
        assert 'timestamp' in data.columns
        assert 'open' in data.columns
        assert 'high' in data.columns
        assert 'low' in data.columns
        assert 'close' in data.columns
        assert 'volume' in data.columns
    
    def test_grid_search_optimization(self, config_file, sample_data):
        """Test grid search optimization with small parameter grid."""
        optimizer = StrategyOptimizer(config_file)
        
        # Use minimal parameter grid for fast testing
        param_config = {
            'rsi_oversold': [30, 35],
            'rsi_overbought': [65, 70],
            'fast_period': [9, 12],
            'slow_period': [21, 26],
            'volume_multiplier': [1.2],
            'min_ema_distance': [0.003],
            'confidence_threshold': [0.6],
            'position_size': [0.02],
            'stop_loss_pct': [0.02]
        }
        
        opt_config = {
            'metric': 'sharpe_ratio',
            'initial_capital': 10000.0,
            'commission': 0.001,
            'slippage': 0.0005
        }
        
        results = optimizer._grid_search_optimization(
            sample_data,
            param_config,
            opt_config
        )
        
        assert results is not None
        assert 'method' in results
        assert results['method'] == 'grid_search'
        assert 'best_params' in results
        assert 'best_score' in results
        assert 'all_results' in results
        assert len(results['all_results']) > 0
        
        # Check that best_params contain required fields
        assert 'rsi_oversold' in results['best_params']
        assert 'rsi_overbought' in results['best_params']
        assert 'fast_period' in results['best_params']
        assert 'slow_period' in results['best_params']
    
    def test_random_search_optimization(self, config_file, sample_data):
        """Test random search optimization."""
        optimizer = StrategyOptimizer(config_file)
        
        param_config = {
            'rsi_oversold': [30, 35],
            'rsi_overbought': [65, 70],
            'fast_period': [9, 12],
            'slow_period': [21, 26],
            'volume_multiplier': [1.2],
            'min_ema_distance': [0.003],
            'confidence_threshold': [0.6],
            'position_size': [0.02],
            'stop_loss_pct': [0.02]
        }
        
        opt_config = {
            'metric': 'sharpe_ratio',
            'initial_capital': 10000.0,
            'commission': 0.001,
            'slippage': 0.0005,
            'n_random_samples': 5  # Small number for testing
        }
        
        results = optimizer._random_search_optimization(
            sample_data,
            param_config,
            opt_config
        )
        
        assert results is not None
        assert results['method'] == 'random_search'
        assert 'best_params' in results
        assert 'best_score' in results
        assert len(results['all_results']) > 0
    
    def test_walk_forward_validation(self, config_file, sample_data):
        """Test walk-forward validation."""
        optimizer = StrategyOptimizer(config_file)
        
        # Use simple best params
        best_params = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'fast_period': 9,
            'slow_period': 21,
            'volume_multiplier': 1.2,
            'min_ema_distance': 0.003,
            'confidence_threshold': 0.6,
            'position_size': 0.02,
            'stop_loss_pct': 0.02
        }
        
        results = optimizer.walk_forward_validation(sample_data, best_params)
        
        assert results is not None
        assert 'enabled' in results
        
        if results['enabled']:
            assert 'splits' in results
            assert 'stability' in results
            assert len(results['splits']) > 0
    
    def test_walk_forward_disabled(self, config_file, sample_data):
        """Test walk-forward validation when disabled."""
        optimizer = StrategyOptimizer(config_file)
        optimizer.config['walk_forward']['enabled'] = False
        
        best_params = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'fast_period': 9,
            'slow_period': 21
        }
        
        results = optimizer.walk_forward_validation(sample_data, best_params)
        
        assert results['enabled'] is False
    
    def test_invalid_parameter_combination(self, config_file, sample_data):
        """Test that invalid parameter combinations are skipped."""
        optimizer = StrategyOptimizer(config_file)
        
        # Create config where fast_period >= slow_period (invalid)
        param_config = {
            'rsi_oversold': [30],
            'rsi_overbought': [70],
            'fast_period': [21],  # Invalid: fast >= slow
            'slow_period': [21],
            'volume_multiplier': [1.2],
            'min_ema_distance': [0.003],
            'confidence_threshold': [0.6],
            'position_size': [0.02],
            'stop_loss_pct': [0.02]
        }
        
        opt_config = {
            'metric': 'sharpe_ratio',
            'initial_capital': 10000.0,
            'commission': 0.001,
            'slippage': 0.0005
        }
        
        results = optimizer._grid_search_optimization(
            sample_data,
            param_config,
            opt_config
        )
        
        # Should have no results since all combinations are invalid
        assert len(results['all_results']) == 0


class TestIntegration:
    """Integration tests for the full optimization workflow."""
    
    def test_full_optimization_workflow(self, config_file, tmp_path):
        """Test complete optimization workflow."""
        optimizer = StrategyOptimizer(config_file)
        
        # Override results directory to use temp
        optimizer.results_dir = tmp_path
        optimizer.config['output']['results_dir'] = str(tmp_path)
        
        # Load data
        data = optimizer.load_data()
        assert len(data) > 100
        
        # Run optimization with minimal grid for speed
        optimizer.config['parameters']['rsi_oversold'] = [30]
        optimizer.config['parameters']['rsi_overbought'] = [70]
        optimizer.config['parameters']['fast_period'] = [9]
        optimizer.config['parameters']['slow_period'] = [21]
        
        opt_results = optimizer.run_optimization(data)
        
        assert opt_results is not None
        assert 'best_params' in opt_results
        assert 'best_score' in opt_results
        
        # Run walk-forward
        wf_results = optimizer.walk_forward_validation(data, opt_results['best_params'])
        
        assert wf_results is not None
        
        # Save results
        optimizer.save_results(opt_results, wf_results)
        
        # Check that files were created
        json_files = list(tmp_path.glob('optimization_results_*.json'))
        assert len(json_files) > 0
        
        if optimizer.config['output']['save_csv']:
            csv_files = list(tmp_path.glob('optimization_results_*.csv'))
            assert len(csv_files) > 0
        
        if optimizer.config['output']['generate_report']:
            md_files = list(tmp_path.glob('optimization_report_*.md'))
            assert len(md_files) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
