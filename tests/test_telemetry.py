"""
Tests for the telemetry module.
"""

import pytest
import pandas as pd
from pathlib import Path
import json
import tempfile
import shutil
from datetime import datetime

from yunmin.backtesting.telemetry import BacktestTelemetry


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test artifacts."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_trades():
    """Create sample trade data for testing."""
    return [
        {
            'entry_time': datetime(2024, 1, 1, 10, 0),
            'entry_price': 45000.0,
            'exit_time': datetime(2024, 1, 1, 12, 0),
            'exit_price': 45500.0,
            'amount': 0.1,
            'pnl': 50.0,
            'pnl_pct': 1.11,
            'signal_confidence': 0.85,
            'reasons': 'RSI oversold + bullish trend'
        },
        {
            'entry_time': datetime(2024, 1, 2, 10, 0),
            'entry_price': 46000.0,
            'exit_time': datetime(2024, 1, 2, 14, 0),
            'exit_price': 45500.0,
            'amount': 0.1,
            'pnl': -50.0,
            'pnl_pct': -1.09,
            'signal_confidence': 0.75,
            'reasons': 'MACD crossover'
        }
    ]


@pytest.fixture
def sample_equity_curve():
    """Create sample equity curve data."""
    return [10000.0, 10050.0, 10100.0, 10050.0, 10200.0]


@pytest.fixture
def sample_summary():
    """Create sample summary metrics."""
    return {
        'total_trades': 2,
        'winning_trades': 1,
        'losing_trades': 1,
        'win_rate': 50.0,
        'total_pnl': 0.0,
        'profit_factor': 1.0,
        'sharpe_ratio': 0.5,
        'max_drawdown': 0.05
    }


class TestBacktestTelemetry:
    """Test cases for BacktestTelemetry class."""
    
    def test_initialization(self, temp_dir):
        """Test telemetry initialization creates directory."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        assert Path(temp_dir).exists()
        assert telemetry.output_dir == Path(temp_dir)
    
    def test_save_trades(self, temp_dir, sample_trades):
        """Test saving trades to CSV."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_trades(sample_trades)
        
        assert output_path is not None
        assert output_path.exists()
        assert output_path.suffix == '.csv'
        
        # Load and verify content
        df = pd.read_csv(output_path)
        assert len(df) == 2
        assert 'entry_time' in df.columns
        assert 'exit_time' in df.columns
        assert 'entry_price' in df.columns
        assert 'exit_price' in df.columns
        assert 'size' in df.columns
        assert 'pnl_usd' in df.columns
        assert 'pnl_pct' in df.columns
        assert 'confidence' in df.columns
        assert 'reasons' in df.columns
    
    def test_save_empty_trades(self, temp_dir):
        """Test saving empty trades list."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_trades([])
        
        assert output_path is None
    
    def test_save_equity_curve(self, temp_dir, sample_equity_curve):
        """Test saving equity curve to CSV."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_equity_curve(sample_equity_curve)
        
        assert output_path is not None
        assert output_path.exists()
        assert output_path.suffix == '.csv'
        
        # Load and verify content
        df = pd.read_csv(output_path)
        assert len(df) == len(sample_equity_curve)
        assert 'step' in df.columns
        assert 'equity' in df.columns
        assert df['equity'].tolist() == sample_equity_curve
    
    def test_save_empty_equity_curve(self, temp_dir):
        """Test saving empty equity curve."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_equity_curve([])
        
        assert output_path is None
    
    def test_save_summary(self, temp_dir, sample_summary):
        """Test saving summary to JSON."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_summary(sample_summary)
        
        assert output_path is not None
        assert output_path.exists()
        assert output_path.suffix == '.json'
        
        # Load and verify content
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        assert 'metadata' in data
        assert 'metrics' in data
        assert data['metrics'] == sample_summary
    
    def test_save_empty_summary(self, temp_dir):
        """Test saving empty summary."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_summary({})
        
        assert output_path is None
    
    def test_save_all(self, temp_dir, sample_trades, sample_equity_curve, sample_summary):
        """Test saving all artifacts at once."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        paths = telemetry.save_all(sample_trades, sample_equity_curve, sample_summary)
        
        assert 'trades' in paths
        assert 'equity_curve' in paths
        assert 'summary' in paths
        
        assert paths['trades'] is not None
        assert paths['equity_curve'] is not None
        assert paths['summary'] is not None
        
        assert paths['trades'].exists()
        assert paths['equity_curve'].exists()
        assert paths['summary'].exists()
    
    def test_custom_filename(self, temp_dir, sample_trades):
        """Test saving with custom filename."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        custom_name = "custom_trades.csv"
        output_path = telemetry.save_trades(sample_trades, filename=custom_name)
        
        assert output_path.name == custom_name
        assert output_path.exists()
    
    def test_timestamp_in_filename(self, temp_dir, sample_trades):
        """Test that timestamp is included in default filename."""
        telemetry = BacktestTelemetry(output_dir=temp_dir)
        output_path = telemetry.save_trades(sample_trades)
        
        assert telemetry.timestamp in output_path.name
        assert output_path.name.startswith('trades_')
