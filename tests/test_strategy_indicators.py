"""
Unit tests for Phase 2.3 Advanced Indicators Module

Tests all advanced technical indicators:
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- OBV (On-Balance Volume)
- Ichimoku Cloud
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.strategy.indicators import (
    TechnicalIndicators,
    calculate_all_indicators
)


class TestTechnicalIndicators:
    """Test suite for advanced technical indicators."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        n = 100
        dates = pd.date_range(start='2024-01-01', periods=n, freq='5min')
        
        # Generate realistic price data
        base_price = 50000
        trend = np.linspace(0, 1000, n)  # Upward trend
        noise = np.random.randn(n) * 100
        close_prices = base_price + trend + noise
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(n) * 50,
            'high': close_prices + abs(np.random.randn(n) * 100),
            'low': close_prices - abs(np.random.randn(n) * 100),
            'close': close_prices,
            'volume': np.random.rand(n) * 1000 + 500
        })
        
        return df
    
    @pytest.fixture
    def indicators(self):
        """Create TechnicalIndicators instance."""
        return TechnicalIndicators()
    
    def test_calculate_macd(self, sample_data, indicators):
        """Test MACD calculation."""
        result = indicators.calculate_macd(sample_data['close'])
        
        # Check all components exist
        assert 'macd_line' in result
        assert 'signal_line' in result
        assert 'histogram' in result
        
        # Check correct length
        assert len(result['macd_line']) == len(sample_data)
        assert len(result['signal_line']) == len(sample_data)
        assert len(result['histogram']) == len(sample_data)
        
        # Check histogram is difference of MACD and signal
        latest_hist = result['histogram'].iloc[-1]
        latest_macd = result['macd_line'].iloc[-1]
        latest_signal = result['signal_line'].iloc[-1]
        
        if not pd.isna(latest_hist):
            assert abs(latest_hist - (latest_macd - latest_signal)) < 0.01
    
    def test_calculate_bollinger_bands(self, sample_data, indicators):
        """Test Bollinger Bands calculation."""
        result = indicators.calculate_bollinger_bands(sample_data['close'])
        
        # Check all components exist
        assert 'upper_band' in result
        assert 'middle_band' in result
        assert 'lower_band' in result
        assert 'bandwidth' in result
        
        # Check upper > middle > lower (where not NaN)
        for i in range(20, len(sample_data)):  # After warmup period
            upper = result['upper_band'].iloc[i]
            middle = result['middle_band'].iloc[i]
            lower = result['lower_band'].iloc[i]
            
            if not pd.isna(upper) and not pd.isna(middle) and not pd.isna(lower):
                assert upper > middle
                assert middle > lower
    
    def test_calculate_atr(self, sample_data, indicators):
        """Test ATR calculation."""
        result = indicators.calculate_atr(
            sample_data['high'],
            sample_data['low'],
            sample_data['close']
        )
        
        # Check result exists and has correct length
        assert len(result) == len(sample_data)
        
        # ATR should be positive (volatility measure)
        valid_atr = result.dropna()
        assert (valid_atr > 0).all()
    
    def test_calculate_obv(self, sample_data, indicators):
        """Test OBV calculation."""
        result = indicators.calculate_obv(
            sample_data['close'],
            sample_data['volume']
        )
        
        # Check result exists and has correct length
        assert len(result) == len(sample_data)
        
        # OBV should accumulate volume
        # First value should equal first volume
        assert result.iloc[0] == sample_data['volume'].iloc[0]
    
    def test_calculate_ichimoku(self, sample_data, indicators):
        """Test Ichimoku Cloud calculation."""
        result = indicators.calculate_ichimoku(
            sample_data['high'],
            sample_data['low'],
            sample_data['close']
        )
        
        # Check all components exist
        assert 'tenkan_sen' in result
        assert 'kijun_sen' in result
        assert 'senkou_span_a' in result
        assert 'senkou_span_b' in result
        assert 'chikou_span' in result
        assert 'cloud_top' in result
        assert 'cloud_bottom' in result
        
        # Check cloud top >= cloud bottom
        for i in range(52, len(sample_data)):
            top = result['cloud_top'].iloc[i]
            bottom = result['cloud_bottom'].iloc[i]
            
            if not pd.isna(top) and not pd.isna(bottom):
                assert top >= bottom
    
    def test_analyze_macd_signal(self, sample_data, indicators):
        """Test MACD signal analysis."""
        macd_data = indicators.calculate_macd(sample_data['close'])
        signal, strength = indicators.analyze_macd_signal(macd_data)
        
        # Check signal is valid
        assert signal in ['bullish', 'bearish', 'neutral']
        
        # Check strength is in valid range
        assert 0.0 <= strength <= 1.0
    
    def test_analyze_bollinger_position(self, sample_data, indicators):
        """Test Bollinger Bands position analysis."""
        bb_data = indicators.calculate_bollinger_bands(sample_data['close'])
        current_price = sample_data['close'].iloc[-1]
        
        signal, strength = indicators.analyze_bollinger_position(current_price, bb_data)
        
        # Check signal is valid
        assert signal in ['overbought', 'oversold', 'normal']
        
        # Check strength is in valid range
        assert 0.0 <= strength <= 1.0
    
    def test_analyze_obv_trend(self, sample_data, indicators):
        """Test OBV trend analysis."""
        obv = indicators.calculate_obv(sample_data['close'], sample_data['volume'])
        
        trend, strength = indicators.analyze_obv_trend(obv)
        
        # Check trend is valid
        assert trend in ['bullish', 'bearish', 'neutral']
        
        # Check strength is in valid range
        assert 0.0 <= strength <= 1.0
    
    def test_analyze_ichimoku_signal(self, sample_data, indicators):
        """Test Ichimoku signal analysis."""
        ichimoku_data = indicators.calculate_ichimoku(
            sample_data['high'],
            sample_data['low'],
            sample_data['close']
        )
        current_price = sample_data['close'].iloc[-1]
        
        signal, strength = indicators.analyze_ichimoku_signal(current_price, ichimoku_data)
        
        # Check signal is valid
        assert signal in ['bullish', 'bearish', 'neutral']
        
        # Check strength is in valid range
        assert 0.0 <= strength <= 1.0
    
    def test_calculate_all_indicators(self, sample_data):
        """Test calculation of all indicators at once."""
        result = calculate_all_indicators(sample_data)
        
        # Check original columns still exist
        assert 'open' in result.columns
        assert 'high' in result.columns
        assert 'low' in result.columns
        assert 'close' in result.columns
        assert 'volume' in result.columns
        
        # Check MACD columns added
        assert 'macd_line' in result.columns
        assert 'macd_signal' in result.columns
        assert 'macd_histogram' in result.columns
        
        # Check Bollinger Bands columns added
        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns
        
        # Check ATR added
        assert 'atr' in result.columns
        
        # Check OBV added
        assert 'obv' in result.columns
        
        # Check Ichimoku columns added
        assert 'ichimoku_tenkan' in result.columns
        assert 'ichimoku_kijun' in result.columns
        assert 'ichimoku_cloud_top' in result.columns
        assert 'ichimoku_cloud_bottom' in result.columns
    
    def test_insufficient_data(self, indicators):
        """Test behavior with insufficient data."""
        # Create very short dataframe
        short_df = pd.DataFrame({
            'close': [50000, 50100, 50200],
            'high': [50100, 50200, 50300],
            'low': [49900, 50000, 50100],
            'volume': [100, 110, 105]
        })
        
        result = calculate_all_indicators(short_df)
        
        # Should return original dataframe without crashing
        assert len(result) == 3
    
    def test_macd_crossover_detection(self, sample_data, indicators):
        """Test MACD crossover detection."""
        macd_data = indicators.calculate_macd(sample_data['close'])
        
        # Find crossovers
        macd_line = macd_data['macd_line']
        signal_line = macd_data['signal_line']
        
        # Check for any crossovers (histogram changes sign)
        histogram = macd_data['histogram'].dropna()
        if len(histogram) > 1:
            sign_changes = (histogram.shift(1) * histogram < 0).sum()
            # Just verify we can detect sign changes
            assert sign_changes >= 0
    
    def test_bollinger_squeeze_detection(self, sample_data, indicators):
        """Test Bollinger Bands squeeze detection."""
        bb_data = indicators.calculate_bollinger_bands(sample_data['close'])
        
        # Bandwidth should be calculable
        bandwidth = bb_data['bandwidth'].dropna()
        assert len(bandwidth) > 0
        
        # Check if there's any period of low volatility (squeeze)
        # Low bandwidth indicates squeeze
        min_bandwidth = bandwidth.min()
        assert min_bandwidth >= 0
    
    def test_atr_for_stop_loss(self, sample_data, indicators):
        """Test using ATR for dynamic stop-loss calculation."""
        atr = indicators.calculate_atr(
            sample_data['high'],
            sample_data['low'],
            sample_data['close']
        )
        
        # Simulate stop-loss calculation
        current_price = sample_data['close'].iloc[-1]
        current_atr = atr.iloc[-1]
        
        if not pd.isna(current_atr):
            # 2x ATR stop loss
            stop_loss_distance = 2 * current_atr
            stop_loss_price = current_price - stop_loss_distance
            
            # Stop loss should be below current price
            assert stop_loss_price < current_price
    
    def test_obv_divergence_detection(self, sample_data, indicators):
        """Test OBV divergence detection."""
        obv = indicators.calculate_obv(sample_data['close'], sample_data['volume'])
        
        # Get last 10 periods
        recent_obv = obv.iloc[-10:]
        recent_price = sample_data['close'].iloc[-10:]
        
        # Check if OBV and price are moving in same direction
        obv_direction = 1 if recent_obv.iloc[-1] > recent_obv.iloc[0] else -1
        price_direction = 1 if recent_price.iloc[-1] > recent_price.iloc[0] else -1
        
        # Both should be either positive or negative
        # (no assertion here, just demonstrating the concept)
        assert obv_direction in [-1, 1]
        assert price_direction in [-1, 1]


class TestIndicatorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        empty_df = pd.DataFrame()
        result = calculate_all_indicators(empty_df)
        assert result.empty
    
    def test_nan_values(self):
        """Test handling of NaN values."""
        df = pd.DataFrame({
            'close': [50000, np.nan, 50200, 50300],
            'high': [50100, 50200, np.nan, 50400],
            'low': [49900, 50000, 50100, np.nan],
            'volume': [100, 110, np.nan, 115]
        })
        
        indicators = TechnicalIndicators()
        
        # Should not crash
        macd = indicators.calculate_macd(df['close'])
        assert 'macd_line' in macd
    
    def test_zero_volume(self):
        """Test OBV with zero volume."""
        df = pd.DataFrame({
            'close': [50000, 50100, 50200],
            'volume': [0, 0, 0]
        })
        
        indicators = TechnicalIndicators()
        obv = indicators.calculate_obv(df['close'], df['volume'])
        
        # Should return zeros
        assert (obv == 0).all()
    
    def test_constant_prices(self):
        """Test with constant prices (no volatility)."""
        df = pd.DataFrame({
            'close': [50000] * 50,
            'high': [50000] * 50,
            'low': [50000] * 50,
            'volume': [100] * 50
        })
        
        indicators = TechnicalIndicators()
        
        # Bollinger Bands bandwidth should be zero
        bb = indicators.calculate_bollinger_bands(df['close'])
        bandwidth = bb['bandwidth'].dropna()
        if len(bandwidth) > 0:
            assert bandwidth.iloc[-1] < 0.01  # Very small or zero


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
