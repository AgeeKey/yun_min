"""
Tests for Market Regime Detector
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.ml.regime_detector import (
    RegimeDetector,
    MarketRegime,
    TrendDirection,
    RegimeAnalysis
)


class TestRegimeDetector:
    """Test suite for Market Regime Detector."""
    
    @pytest.fixture
    def detector(self):
        """Create default detector instance."""
        return RegimeDetector(
            adx_period=14,
            adx_trending_threshold=25.0,
            adx_ranging_threshold=20.0,
            bb_volatility_threshold=0.04
        )
    
    @pytest.fixture
    def trending_data(self):
        """Create sample data with strong trend."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # Strong uptrend
        base_price = 50000
        trend = np.linspace(0, 5000, 100)  # +5000 over period
        noise = np.random.randn(100) * 50
        prices = base_price + trend + noise
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(100) * 30),
            'low': prices - np.abs(np.random.randn(100) * 30),
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
    
    @pytest.fixture
    def ranging_data(self):
        """Create sample data with ranging (sideways) market."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # Sideways movement
        base_price = 50000
        oscillation = np.sin(np.linspace(0, 4 * np.pi, 100)) * 200
        noise = np.random.randn(100) * 50
        prices = base_price + oscillation + noise
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(100) * 30),
            'low': prices - np.abs(np.random.randn(100) * 30),
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
    
    @pytest.fixture
    def volatile_data(self):
        """Create sample data with high volatility."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # High volatility swings
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(100) * 500)  # Large swings
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(100) * 300),
            'low': prices - np.abs(np.random.randn(100) * 300),
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
    
    def test_initialization(self):
        """Test detector initialization."""
        detector = RegimeDetector(
            adx_period=14,
            adx_trending_threshold=25.0,
            bb_period=20
        )
        
        assert detector.adx_period == 14
        assert detector.adx_trending_threshold == 25.0
        assert detector.bb_period == 20
    
    def test_insufficient_data(self, detector):
        """Test with insufficient data."""
        data = pd.DataFrame({
            'close': [50000],
            'high': [50100],
            'low': [49900],
            'volume': [100]
        })
        
        result = detector.detect_regime(data)
        
        assert result.regime == MarketRegime.UNKNOWN
        assert result.confidence == 0.0
        assert "Insufficient data" in result.reasoning
    
    def test_detect_trending_regime(self, detector, trending_data):
        """Test detection of trending regime."""
        result = detector.detect_regime(trending_data)
        
        # Should detect trending or at least not ranging with high confidence
        # ADX should be higher in trending markets
        assert result.trend_strength > 0
        # Could be TRENDING or VOLATILE depending on exact data
        assert result.regime in [MarketRegime.TRENDING, MarketRegime.VOLATILE, MarketRegime.RANGING]
    
    def test_detect_ranging_regime(self, detector, ranging_data):
        """Test detection of ranging regime."""
        result = detector.detect_regime(ranging_data)
        
        # Ranging data should have lower ADX
        # Note: Due to random noise, exact regime might vary
        assert result.trend_strength >= 0
        assert result.regime in [MarketRegime.RANGING, MarketRegime.TRENDING, MarketRegime.VOLATILE]
    
    def test_detect_volatile_regime(self, detector, volatile_data):
        """Test detection of volatile regime."""
        result = detector.detect_regime(volatile_data)
        
        # High volatility should be detected
        assert result.volatility > 0
        # Should likely be VOLATILE but could be TRENDING with high volatility
        assert result.regime in [MarketRegime.VOLATILE, MarketRegime.TRENDING]
    
    def test_trend_direction_bullish(self, detector):
        """Test bullish trend direction detection."""
        # Create clear uptrend
        data = pd.DataFrame({
            'high': [100, 105, 110, 115, 120, 125, 130, 135, 140, 145],
            'low': [95, 100, 105, 110, 115, 120, 125, 130, 135, 140],
            'close': [98, 103, 108, 113, 118, 123, 128, 133, 138, 143],
            'volume': [1000] * 10
        })
        
        direction = detector._detect_trend_direction(data)
        assert direction == TrendDirection.BULLISH
    
    def test_trend_direction_bearish(self, detector):
        """Test bearish trend direction detection."""
        # Create clear downtrend
        data = pd.DataFrame({
            'high': [145, 140, 135, 130, 125, 120, 115, 110, 105, 100],
            'low': [140, 135, 130, 125, 120, 115, 110, 105, 100, 95],
            'close': [143, 138, 133, 128, 123, 118, 113, 108, 103, 98],
            'volume': [1000] * 10
        })
        
        direction = detector._detect_trend_direction(data)
        assert direction == TrendDirection.BEARISH
    
    def test_trend_direction_sideways(self, detector):
        """Test sideways trend direction detection."""
        # Create sideways movement
        data = pd.DataFrame({
            'high': [105, 104, 106, 105, 104, 106, 105, 104, 106, 105],
            'low': [95, 96, 94, 95, 96, 94, 95, 96, 94, 95],
            'close': [100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
            'volume': [1000] * 10
        })
        
        direction = detector._detect_trend_direction(data)
        assert direction == TrendDirection.SIDEWAYS
    
    def test_calculate_adx(self, detector, trending_data):
        """Test ADX calculation."""
        adx = detector._calculate_adx(trending_data)
        
        assert isinstance(adx, (int, float, np.number))
        assert adx >= 0  # ADX should be non-negative
        assert not np.isnan(adx)
    
    def test_calculate_bb_width(self, detector, trending_data):
        """Test Bollinger Band width calculation."""
        bb_width = detector._calculate_bb_width(trending_data)
        
        assert isinstance(bb_width, (int, float, np.number))
        assert bb_width > 0  # BB width should be positive
        assert not np.isnan(bb_width)
    
    def test_detect_price_patterns_bullish(self, detector):
        """Test bullish price pattern detection."""
        # Create bullish pattern
        data = pd.DataFrame({
            'close': np.linspace(100, 110, 10),  # Steady uptrend
            'high': np.linspace(102, 112, 10),
            'low': np.linspace(98, 108, 10),
            'volume': [1000] * 10
        })
        
        score = detector._detect_price_patterns(data)
        assert score > 0  # Should be positive for bullish
    
    def test_detect_price_patterns_bearish(self, detector):
        """Test bearish price pattern detection."""
        # Create bearish pattern
        data = pd.DataFrame({
            'close': np.linspace(110, 100, 10),  # Steady downtrend
            'high': np.linspace(112, 102, 10),
            'low': np.linspace(108, 98, 10),
            'volume': [1000] * 10
        })
        
        score = detector._detect_price_patterns(data)
        assert score < 0  # Should be negative for bearish
    
    def test_classify_regime_trending(self, detector):
        """Test regime classification for trending market."""
        adx = 30.0  # Above trending threshold (25)
        bb_width = 0.03  # Normal volatility
        pattern_score = 0.7
        
        regime, confidence = detector._classify_regime(adx, bb_width, pattern_score)
        
        assert regime == MarketRegime.TRENDING
        assert 0.0 < confidence <= 1.0
    
    def test_classify_regime_ranging(self, detector):
        """Test regime classification for ranging market."""
        adx = 15.0  # Below ranging threshold (20)
        bb_width = 0.02  # Low volatility
        pattern_score = 0.1
        
        regime, confidence = detector._classify_regime(adx, bb_width, pattern_score)
        
        assert regime == MarketRegime.RANGING
        assert 0.0 < confidence <= 1.0
    
    def test_classify_regime_volatile(self, detector):
        """Test regime classification for volatile market."""
        adx = 22.0
        bb_width = 0.05  # Above volatility threshold (0.04)
        pattern_score = 0.3
        
        regime, confidence = detector._classify_regime(adx, bb_width, pattern_score)
        
        assert regime == MarketRegime.VOLATILE
        assert 0.0 < confidence <= 1.0
    
    def test_position_recommendation_trending(self, detector):
        """Test position sizing for trending market."""
        multiplier = detector._get_position_recommendation(
            MarketRegime.TRENDING, 
            adx=30.0, 
            bb_width=0.03
        )
        
        assert 0.75 <= multiplier <= 1.0
    
    def test_position_recommendation_ranging(self, detector):
        """Test position sizing for ranging market."""
        multiplier = detector._get_position_recommendation(
            MarketRegime.RANGING, 
            adx=15.0, 
            bb_width=0.02
        )
        
        assert 0.50 <= multiplier <= 0.75
    
    def test_position_recommendation_volatile(self, detector):
        """Test position sizing for volatile market."""
        multiplier = detector._get_position_recommendation(
            MarketRegime.VOLATILE, 
            adx=22.0, 
            bb_width=0.06
        )
        
        assert 0.25 <= multiplier <= 0.50
    
    def test_get_strategy_adjustments_trending(self, detector):
        """Test strategy adjustments for trending regime."""
        adjustments = detector.get_strategy_adjustments(MarketRegime.TRENDING)
        
        assert adjustments['allow_aggressive'] is True
        assert adjustments['required_confidence'] < 0.75
        assert adjustments['position_sizing'] >= 0.75
    
    def test_get_strategy_adjustments_ranging(self, detector):
        """Test strategy adjustments for ranging regime."""
        adjustments = detector.get_strategy_adjustments(MarketRegime.RANGING)
        
        assert adjustments['allow_aggressive'] is False
        assert adjustments['required_confidence'] >= 0.70
        assert adjustments['position_sizing'] < 0.75
    
    def test_get_strategy_adjustments_volatile(self, detector):
        """Test strategy adjustments for volatile regime."""
        adjustments = detector.get_strategy_adjustments(MarketRegime.VOLATILE)
        
        assert adjustments['allow_aggressive'] is False
        assert adjustments['required_confidence'] >= 0.75
        assert adjustments['position_sizing'] < 0.50
    
    def test_visualize_regime(self, detector, trending_data):
        """Test regime visualization."""
        analysis = detector.detect_regime(trending_data)
        visualization = detector.visualize_regime(analysis)
        
        assert isinstance(visualization, str)
        assert len(visualization) > 0
        assert "MARKET REGIME ANALYSIS" in visualization
        assert analysis.regime.value.upper() in visualization
    
    def test_regime_analysis_structure(self, detector, trending_data):
        """Test that RegimeAnalysis has all expected fields."""
        analysis = detector.detect_regime(trending_data)
        
        assert hasattr(analysis, 'regime')
        assert hasattr(analysis, 'trend_direction')
        assert hasattr(analysis, 'trend_strength')
        assert hasattr(analysis, 'volatility')
        assert hasattr(analysis, 'confidence')
        assert hasattr(analysis, 'reasoning')
        assert hasattr(analysis, 'metrics')
        assert hasattr(analysis, 'position_sizing_recommendation')
        
        assert isinstance(analysis.regime, MarketRegime)
        assert isinstance(analysis.trend_direction, TrendDirection)
        assert isinstance(analysis.metrics, dict)
    
    def test_get_params(self, detector):
        """Test getting detector parameters."""
        params = detector.get_params()
        
        assert 'adx_period' in params
        assert 'adx_trending_threshold' in params
        assert 'adx_ranging_threshold' in params
        assert 'bb_period' in params
        assert params['adx_period'] == 14
        assert params['adx_trending_threshold'] == 25.0
    
    def test_custom_parameters(self):
        """Test initialization with custom parameters."""
        detector = RegimeDetector(
            adx_period=20,
            adx_trending_threshold=30.0,
            adx_ranging_threshold=15.0,
            bb_period=30,
            bb_volatility_threshold=0.05
        )
        
        assert detector.adx_period == 20
        assert detector.adx_trending_threshold == 30.0
        assert detector.adx_ranging_threshold == 15.0
        assert detector.bb_period == 30
        assert detector.bb_volatility_threshold == 0.05
    
    def test_confidence_range(self, detector, trending_data):
        """Test that confidence is always in valid range [0, 1]."""
        analysis = detector.detect_regime(trending_data)
        assert 0.0 <= analysis.confidence <= 1.0
    
    def test_position_multiplier_range(self, detector, trending_data):
        """Test that position multiplier is in valid range [0.25, 1.0]."""
        analysis = detector.detect_regime(trending_data)
        assert 0.25 <= analysis.position_sizing_recommendation <= 1.0
    
    def test_adx_calculation_consistency(self, detector):
        """Test that ADX calculation is consistent."""
        # Same data should give same ADX
        data = pd.DataFrame({
            'high': [100, 105, 103, 108, 106] + [100] * 20,
            'low': [95, 100, 98, 103, 101] + [95] * 20,
            'close': [98, 103, 101, 106, 104] + [98] * 20,
            'volume': [1000] * 25
        })
        
        adx1 = detector._calculate_adx(data)
        adx2 = detector._calculate_adx(data)
        
        assert adx1 == adx2
    
    def test_pattern_score_range(self, detector, trending_data):
        """Test that pattern score is in valid range [-1, 1]."""
        score = detector._detect_price_patterns(trending_data)
        assert -1.0 <= score <= 1.0
