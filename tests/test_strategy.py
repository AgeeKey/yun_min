"""
Tests for Strategy Module
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.strategy.base import SignalType


class TestEMACrossoverStrategy:
    """Test EMA Crossover strategy."""
    
    def create_sample_data(self, length=100):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=length, freq='5min')
        
        # Generate price data with trend
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(length) * 100)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.rand(length) * 50,
            'low': prices - np.random.rand(length) * 50,
            'close': prices,
            'volume': np.random.rand(length) * 1000
        })
        
        return data
        
    def test_strategy_initialization(self):
        """Test strategy initialization."""
        strategy = EMACrossoverStrategy(
            fast_period=9,
            slow_period=21,
            rsi_period=14
        )
        
        assert strategy.name == "EMA_Crossover"
        assert strategy.fast_period == 9
        assert strategy.slow_period == 21
        
    def test_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = EMACrossoverStrategy()
        data = self.create_sample_data(length=10)  # Too short
        
        signal = strategy.analyze(data)
        
        assert signal.type == SignalType.HOLD
        assert signal.confidence == 0.0
        assert "Insufficient data" in signal.reason
        
    def test_strategy_generates_signal(self):
        """Test that strategy generates valid signals."""
        strategy = EMACrossoverStrategy()
        data = self.create_sample_data(length=100)
        
        signal = strategy.analyze(data)
        
        assert signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD, SignalType.CLOSE]
        assert 0.0 <= signal.confidence <= 1.0
        assert len(signal.reason) > 0
        assert signal.metadata is not None
        
    def test_get_set_params(self):
        """Test getting and setting parameters."""
        strategy = EMACrossoverStrategy()
        
        # Get params
        params = strategy.get_params()
        assert 'fast_period' in params
        assert params['fast_period'] == 9
        
        # Set params
        new_params = {'fast_period': 12, 'slow_period': 26}
        strategy.set_params(new_params)
        
        updated_params = strategy.get_params()
        assert updated_params['fast_period'] == 12
        assert updated_params['slow_period'] == 26
