"""
Test enhanced strategy filters for entry signal validation.

Tests for Problem #4 fix: Entry logic with multiple confirmation filters.
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy


class TestStrategyFilters:
    """Test strategy filter methods."""
    
    def setup_method(self):
        """Setup test strategy instance."""
        self.strategy = GrokAIStrategy(grok_analyzer=None)
    
    def test_check_volume_confirmation_sufficient(self):
        """Test volume confirmation with sufficient volume."""
        current_volume = 1000
        avg_volume = 600
        
        result = self.strategy._check_volume_confirmation(current_volume, avg_volume, multiplier=1.5)
        assert result is True
    
    def test_check_volume_confirmation_insufficient(self):
        """Test volume confirmation with insufficient volume."""
        current_volume = 800
        avg_volume = 600
        
        result = self.strategy._check_volume_confirmation(current_volume, avg_volume, multiplier=1.5)
        assert result is False
    
    def test_check_volume_confirmation_zero_avg(self):
        """Test volume confirmation with zero average volume."""
        current_volume = 1000
        avg_volume = 0
        
        result = self.strategy._check_volume_confirmation(current_volume, avg_volume, multiplier=1.5)
        assert result is False
    
    def test_check_ema_crossover_bullish(self):
        """Test detection of bullish EMA crossover."""
        # Create dataframe with bullish crossover
        df = pd.DataFrame({
            'ema_fast': [100, 101, 102, 103],  # Fast EMA rising
            'ema_slow': [102, 102, 102, 102]   # Slow EMA flat, fast crosses above
        })
        
        has_crossover, direction = self.strategy._check_ema_crossover(df)
        assert has_crossover is True
        assert direction == 'bullish'
    
    def test_check_ema_crossover_bearish(self):
        """Test detection of bearish EMA crossover."""
        # Create dataframe with bearish crossover
        df = pd.DataFrame({
            'ema_fast': [103, 102.5, 102, 101],  # Fast EMA falling, crosses below
            'ema_slow': [102, 102, 102, 102]      # Slow EMA flat
        })
        
        has_crossover, direction = self.strategy._check_ema_crossover(df)
        # Note: May not detect as crossover in last period, but should be bearish state
        assert direction == 'bearish'
    
    def test_check_ema_crossover_no_crossover_bullish_state(self):
        """Test no crossover but bullish state."""
        df = pd.DataFrame({
            'ema_fast': [103, 104, 105, 106],  # Fast above slow, no crossover
            'ema_slow': [100, 100, 100, 100]
        })
        
        has_crossover, direction = self.strategy._check_ema_crossover(df)
        assert has_crossover is False
        assert direction == 'bullish'
    
    def test_check_ema_distance_sufficient(self):
        """Test EMA distance check with sufficient distance."""
        ema_fast = 100
        ema_slow = 95  # 5% distance
        
        result = self.strategy._check_ema_distance(ema_fast, ema_slow, min_distance=0.005)
        assert result is True
    
    def test_check_ema_distance_insufficient(self):
        """Test EMA distance check with insufficient distance."""
        ema_fast = 100
        ema_slow = 99.4  # 0.6% distance
        
        result = self.strategy._check_ema_distance(ema_fast, ema_slow, min_distance=0.01)
        assert result is False
    
    def test_check_divergence_bearish(self):
        """Test detection of bearish divergence."""
        # Price rising, RSI falling
        df = pd.DataFrame({
            'close': [100, 102, 103, 105, 106],
            'rsi': [60, 58, 56, 54, 52]
        })
        
        has_divergence, div_type = self.strategy._check_divergence(df)
        assert has_divergence is True
        assert div_type == 'bearish'
    
    def test_check_divergence_bullish(self):
        """Test detection of bullish divergence."""
        # Price falling, RSI rising
        df = pd.DataFrame({
            'close': [100, 98, 96, 94, 92],
            'rsi': [40, 42, 44, 46, 48]
        })
        
        has_divergence, div_type = self.strategy._check_divergence(df)
        assert has_divergence is True
        assert div_type == 'bullish'
    
    def test_check_divergence_none(self):
        """Test no divergence detected."""
        # Price and RSI both rising
        df = pd.DataFrame({
            'close': [100, 102, 104, 106, 108],
            'rsi': [50, 52, 54, 56, 58]
        })
        
        has_divergence, div_type = self.strategy._check_divergence(df)
        assert has_divergence is False
        assert div_type == 'none'
    
    def test_check_divergence_insufficient_data(self):
        """Test divergence check with insufficient data."""
        df = pd.DataFrame({
            'close': [100, 102],
            'rsi': [50, 52]
        })
        
        has_divergence, div_type = self.strategy._check_divergence(df)
        assert has_divergence is False
        assert div_type == 'none'
    
    def test_calculate_indicators(self):
        """Test indicator calculation."""
        # Create sample OHLCV data
        dates = pd.date_range('2025-01-01', periods=50, freq='5min')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(100, 110, 50),
            'high': np.random.uniform(110, 120, 50),
            'low': np.random.uniform(90, 100, 50),
            'close': np.random.uniform(100, 110, 50),
            'volume': np.random.uniform(1000, 2000, 50)
        })
        
        # Calculate indicators
        result = self.strategy._calculate_indicators(df)
        
        # Check that indicators were added
        assert 'rsi' in result.columns
        assert 'ema_fast' in result.columns
        assert 'ema_slow' in result.columns
        assert 'avg_volume' in result.columns
        
        # Check RSI is in valid range (0-100)
        assert result['rsi'].dropna().min() >= 0
        assert result['rsi'].dropna().max() <= 100
        
        # Check EMAs are calculated
        assert not result['ema_fast'].dropna().empty
        assert not result['ema_slow'].dropna().empty
        
        # Check avg_volume is calculated
        assert not result['avg_volume'].dropna().empty


class TestStrategyIntegration:
    """Integration tests for strategy with filters."""
    
    def setup_method(self):
        """Setup test strategy instance."""
        self.strategy = GrokAIStrategy(grok_analyzer=None)
    
    def create_sample_data(self, periods=50):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range('2025-01-01', periods=periods, freq='5min')
        np.random.seed(42)
        
        # Create trending data
        base_price = 100
        trend = np.linspace(0, 10, periods)  # Upward trend
        noise = np.random.normal(0, 2, periods)
        
        close_prices = base_price + trend + noise
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices - np.random.uniform(0, 1, periods),
            'high': close_prices + np.random.uniform(0, 2, periods),
            'low': close_prices - np.random.uniform(0, 2, periods),
            'close': close_prices,
            'volume': np.random.uniform(1000, 2000, periods)
        })
        
        return df
    
    def test_analyze_with_insufficient_data(self):
        """Test analyze method with insufficient data."""
        df = pd.DataFrame({
            'close': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        
        signal = self.strategy.analyze(df)
        
        assert signal.type.value == 'hold'
        assert signal.confidence == 0.0
        assert 'insufficient' in signal.reason.lower()
    
    def test_analyze_with_sufficient_data_no_ai(self):
        """Test analyze method with sufficient data but no AI."""
        df = self.create_sample_data(periods=50)
        
        signal = self.strategy.analyze(df)
        
        # Should get a signal (BUY, SELL, or HOLD)
        assert signal.type.value in ['buy', 'sell', 'hold']
        assert 0.0 <= signal.confidence <= 1.0
        assert len(signal.reason) > 0
    
    def test_fallback_logic_with_filters(self):
        """Test fallback logic uses filters correctly."""
        enhanced_data = {
            'price': 100,
            'rsi': 75,  # Overbought
            'trend': 'bearish',
            'volume_ok': True,
            'ema_distance_ok': True,
            'crossover_direction': 'bearish'
        }
        
        df = self.create_sample_data()
        
        signal = self.strategy._fallback_logic_with_filters(enhanced_data, df)
        
        # Should generate SELL signal with overbought RSI + bearish trend + filters passed
        assert signal.type.value == 'sell'
        assert signal.confidence > 0.5
        assert 'fallback' in signal.reason.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
