"""
Unit tests for artifacts saving (Issue #42).

Tests:
- Save trade CSV
- Save equity curve CSV
- Save summary JSON
- Save rejected trades CSV
- Directory creation
- File naming
"""
import pytest
import pandas as pd
import numpy as np
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from yunmin.backtesting.backtester import Backtester
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class SimpleTestStrategy(BaseStrategy):
    """Simple strategy for testing."""
    
    def __init__(self):
        super().__init__("test")
        self.signal_count = 0
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        if len(data) > 50 and self.signal_count == 0:
            self.signal_count += 1
            return Signal(type=SignalType.BUY, confidence=0.8, reason="Test buy")
        return Signal(type=SignalType.HOLD, confidence=0.0, reason="Hold")


def generate_test_data(n_bars=200):
    """Generate test data."""
    timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n_bars)]
    prices = np.linspace(50000, 52000, n_bars) + np.random.randn(n_bars) * 100
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.ones(n_bars) * 10000
    })


def test_save_artifacts_creates_directory():
    """Test that save_artifacts creates output directory."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test_artifacts"
        
        backtester.save_artifacts(str(output_dir), run_name="test_run")
        
        # Check directory was created
        assert output_dir.exists()
        assert output_dir.is_dir()


def test_save_artifacts_creates_all_files():
    """Test that all artifact files are created."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        output_dir = Path(result['output_dir'])
        
        # Check all expected files exist
        assert (output_dir / "test_run_trades.csv").exists()
        assert (output_dir / "test_run_equity_curve.csv").exists()
        assert (output_dir / "test_run_summary.json").exists()


def test_save_artifacts_trades_csv_content():
    """Test that trades CSV contains expected columns."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        # Load and check trades CSV
        trades_file = Path(result['output_dir']) / "test_run_trades.csv"
        trades_df = pd.read_csv(trades_file)
        
        # Check required columns
        required_cols = [
            'entry_time', 'exit_time', 'entry_bar', 'exit_bar',
            'side', 'entry_price', 'exit_price', 'amount',
            'leverage', 'pnl', 'pnl_pct', 'fees',
            'exit_reason', 'symbol', 'capital_after'
        ]
        
        for col in required_cols:
            assert col in trades_df.columns, f"Missing column: {col}"


def test_save_artifacts_equity_curve_csv_content():
    """Test that equity curve CSV contains equity data."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        # Load and check equity curve CSV
        equity_file = Path(result['output_dir']) / "test_run_equity_curve.csv"
        equity_df = pd.read_csv(equity_file)
        
        # Check equity column exists
        assert 'equity' in equity_df.columns
        
        # Should have at least initial value
        assert len(equity_df) > 0


def test_save_artifacts_summary_json_content():
    """Test that summary JSON contains expected data."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.05,
        leverage=2.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        # Load and check summary JSON
        summary_file = Path(result['output_dir']) / "test_run_summary.json"
        with open(summary_file) as f:
            summary = json.load(f)
        
        # Check required keys
        assert 'run_name' in summary
        assert 'timestamp' in summary
        assert 'config' in summary
        assert 'metrics' in summary
        assert 'trade_count' in summary
        assert 'rejected_count' in summary
        
        # Check config contains expected values
        assert summary['config']['initial_capital'] == 10000.0
        assert summary['config']['position_size_pct'] == 0.05
        assert summary['config']['leverage'] == 2.0


def test_save_artifacts_rejected_trades():
    """Test that rejected trades are saved when present."""
    strategy = SimpleTestStrategy()
    
    # Set up to generate rejections
    backtester = Backtester(
        strategy=strategy,
        initial_capital=1000.0,  # Small capital
        position_size_pct=0.5,  # Large position
        leverage=10.0,  # High leverage
        use_risk_manager=True  # Enable to get rejections
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        # Check if rejected trades file exists
        rejected_file = Path(result['output_dir']) / "test_run_rejected_trades.csv"
        
        if backtester.get_rejected_trades().empty:
            # No rejections - file shouldn't exist
            assert not rejected_file.exists()
        else:
            # Rejections present - file should exist
            assert rejected_file.exists()
            
            # Load and verify
            rejected_df = pd.read_csv(rejected_file)
            assert 'timestamp' in rejected_df.columns
            assert 'reason' in rejected_df.columns


def test_save_artifacts_auto_run_name():
    """Test that run name is auto-generated if not provided."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Don't provide run_name
        result = backtester.save_artifacts(tmpdir)
        
        # Should have auto-generated run_name
        assert result['run_name'] is not None
        assert len(result['run_name']) > 0
        
        # Files should exist with auto-generated name
        output_dir = Path(result['output_dir'])
        summary_files = list(output_dir.glob("*_summary.json"))
        assert len(summary_files) == 1


def test_save_artifacts_multiple_runs():
    """Test saving multiple runs with different names."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save first run
        result1 = backtester.save_artifacts(tmpdir, run_name="run1")
        
        # Save second run
        result2 = backtester.save_artifacts(tmpdir, run_name="run2")
        
        # Both should exist
        output_dir = Path(tmpdir)
        assert (output_dir / "run1_summary.json").exists()
        assert (output_dir / "run2_summary.json").exists()


def test_save_artifacts_return_value():
    """Test that save_artifacts returns correct information."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(200)
    backtester.run(data)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = backtester.save_artifacts(tmpdir, run_name="test_run")
        
        # Check return value structure
        assert 'output_dir' in result
        assert 'run_name' in result
        assert 'files' in result
        
        # Check files dict
        assert 'trades' in result['files']
        assert 'equity_curve' in result['files']
        assert 'summary' in result['files']
        assert 'rejected_trades' in result['files']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
