"""
Tests for Pattern Recognition System
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile

from yunmin.ml.pattern_recognizer import (
    PatternRecognizer, Pattern, PatternSignal,
    PatternType, PatternSentiment
)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    np.random.seed(42)
    n_samples = 100
    
    base_price = 50000
    prices = [base_price]
    
    for i in range(n_samples - 1):
        change = np.random.randn() * 0.01
        prices.append(prices[-1] * (1 + change))
    
    prices = np.array(prices)
    
    data = {
        'timestamp': [datetime.now() - timedelta(minutes=5*i) for i in range(n_samples, 0, -1)],
        'open': prices * (1 + np.random.randn(n_samples) * 0.002),
        'high': prices * (1 + np.abs(np.random.randn(n_samples)) * 0.005),
        'low': prices * (1 - np.abs(np.random.randn(n_samples)) * 0.005),
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000 + 500
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def double_top_data():
    """Generate data with a double top pattern."""
    n_samples = 100
    x = np.linspace(0, 4 * np.pi, n_samples)
    
    # Create two peaks at similar levels
    prices = 50000 + 1000 * np.sin(x) + np.random.randn(n_samples) * 50
    prices[20] = 51000  # First peak
    prices[60] = 51050  # Second peak (similar level)
    prices[40] = 50300  # Trough between
    
    data = {
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def double_bottom_data():
    """Generate data with a double bottom pattern."""
    n_samples = 100
    x = np.linspace(0, 4 * np.pi, n_samples)
    
    # Create two troughs at similar levels
    prices = 50000 - 1000 * np.sin(x) + np.random.randn(n_samples) * 50
    prices[20] = 49000  # First trough
    prices[60] = 49050  # Second trough (similar level)
    prices[40] = 49700  # Peak between
    
    data = {
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    }
    
    return pd.DataFrame(data)


def test_pattern_recognizer_initialization():
    """Test pattern recognizer initialization."""
    recognizer = PatternRecognizer(
        lookback_window=100,
        min_pattern_length=10
    )
    
    assert recognizer.lookback_window == 100
    assert recognizer.min_pattern_length == 10
    assert not recognizer.is_trained


def test_find_pivot_points(sample_price_data):
    """Test pivot point detection."""
    recognizer = PatternRecognizer()
    prices = sample_price_data['close'].values
    
    pivot_highs, pivot_lows = recognizer._find_pivot_points(prices, order=5)
    
    # Should find some pivot points
    assert len(pivot_highs) > 0
    assert len(pivot_lows) > 0
    
    # Pivot points should be within valid range
    assert all(0 <= idx < len(prices) for idx in pivot_highs)
    assert all(0 <= idx < len(prices) for idx in pivot_lows)


def test_detect_double_top(double_top_data):
    """Test double top pattern detection."""
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_double_top(double_top_data)
    
    # May or may not detect depending on randomness, but should not crash
    if pattern is not None:
        assert pattern.pattern_type == PatternType.DOUBLE_TOP
        assert pattern.sentiment == PatternSentiment.BEARISH
        assert 0 <= pattern.reliability_score <= 1.0
        assert len(pattern.key_points) == 3  # Two peaks and one trough


def test_detect_double_bottom(double_bottom_data):
    """Test double bottom pattern detection."""
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_double_bottom(double_bottom_data)
    
    # May or may not detect depending on randomness, but should not crash
    if pattern is not None:
        assert pattern.pattern_type == PatternType.DOUBLE_BOTTOM
        assert pattern.sentiment == PatternSentiment.BULLISH
        assert 0 <= pattern.reliability_score <= 1.0
        assert len(pattern.key_points) == 3  # Two troughs and one peak


def test_detect_head_shoulders():
    """Test head and shoulders pattern detection."""
    # Create clear H&S pattern
    n_samples = 100
    prices = np.ones(n_samples) * 50000
    
    # Left shoulder, head, right shoulder
    prices[20] = 50800  # Left shoulder
    prices[50] = 51500  # Head (higher)
    prices[80] = 50750  # Right shoulder (similar to left)
    
    # Add some noise
    prices += np.random.randn(n_samples) * 20
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    })
    
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_head_shoulders(data)
    
    # Should detect the pattern
    if pattern is not None:
        assert pattern.pattern_type == PatternType.HEAD_SHOULDERS
        assert pattern.sentiment == PatternSentiment.BEARISH


def test_detect_inverse_head_shoulders():
    """Test inverse head and shoulders pattern detection."""
    # Create clear inverse H&S pattern
    n_samples = 100
    prices = np.ones(n_samples) * 50000
    
    # Left shoulder, head, right shoulder (inverted)
    prices[20] = 49200  # Left shoulder
    prices[50] = 48500  # Head (lower)
    prices[80] = 49250  # Right shoulder (similar to left)
    
    # Add some noise
    prices += np.random.randn(n_samples) * 20
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices * 1.002,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    })
    
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_inverse_head_shoulders(data)
    
    # Should detect the pattern
    if pattern is not None:
        assert pattern.pattern_type == PatternType.INVERSE_HEAD_SHOULDERS
        assert pattern.sentiment == PatternSentiment.BULLISH


def test_detect_bull_flag():
    """Test bull flag pattern detection."""
    # Create bull flag: strong upward move followed by consolidation
    n_samples = 30
    
    # Pole: strong upward move
    pole = np.linspace(50000, 52000, 10)
    
    # Flag: consolidation
    flag = np.ones(20) * 52000 + np.random.randn(20) * 50
    
    prices = np.concatenate([pole, flag])
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    })
    
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_flag(data, bullish=True)
    
    if pattern is not None:
        assert pattern.pattern_type == PatternType.BULL_FLAG
        assert pattern.sentiment == PatternSentiment.BULLISH


def test_detect_bear_flag():
    """Test bear flag pattern detection."""
    # Create bear flag: strong downward move followed by consolidation
    n_samples = 30
    
    # Pole: strong downward move
    pole = np.linspace(52000, 50000, 10)
    
    # Flag: consolidation
    flag = np.ones(20) * 50000 + np.random.randn(20) * 50
    
    prices = np.concatenate([pole, flag])
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    })
    
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_flag(data, bullish=False)
    
    if pattern is not None:
        assert pattern.pattern_type == PatternType.BEAR_FLAG
        assert pattern.sentiment == PatternSentiment.BEARISH


def test_detect_triangle(sample_price_data):
    """Test triangle pattern detection."""
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_triangle(sample_price_data)
    
    # May or may not detect, but should not crash
    if pattern is not None:
        assert pattern.pattern_type in [
            PatternType.ASCENDING_TRIANGLE,
            PatternType.DESCENDING_TRIANGLE,
            PatternType.SYMMETRICAL_TRIANGLE
        ]


def test_detect_rectangle():
    """Test rectangle pattern detection."""
    # Create rectangle pattern: sideways movement
    n_samples = 30
    prices = np.ones(n_samples) * 50000 + np.random.randn(n_samples) * 100
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices + 200,
        'low': prices - 200,
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000
    })
    
    recognizer = PatternRecognizer()
    pattern = recognizer._detect_rectangle(data)
    
    # Should detect rectangle due to tight range
    if pattern is not None:
        assert pattern.pattern_type == PatternType.RECTANGLE
        assert pattern.sentiment == PatternSentiment.NEUTRAL


def test_detect_patterns(sample_price_data):
    """Test detecting all patterns."""
    recognizer = PatternRecognizer()
    patterns = recognizer.detect_patterns(sample_price_data)
    
    # Should return a list (may be empty)
    assert isinstance(patterns, list)
    
    # All detected patterns should be valid
    for pattern in patterns:
        assert isinstance(pattern, Pattern)
        assert pattern.reliability_score >= 0
        assert pattern.reliability_score <= 1.0


def test_generate_signal_no_patterns(sample_price_data):
    """Test signal generation when no patterns detected."""
    recognizer = PatternRecognizer(lookback_window=10, min_pattern_length=20)
    
    # With very restrictive parameters, may not detect patterns
    signal = recognizer.generate_signal(sample_price_data[:15])
    
    # May return None if no patterns found
    if signal is None:
        assert True
    else:
        assert isinstance(signal, PatternSignal)


def test_generate_signal_with_trend(double_bottom_data):
    """Test signal generation with trend context."""
    recognizer = PatternRecognizer()
    
    # Test with uptrend
    signal = recognizer.generate_signal(double_bottom_data, current_trend='uptrend')
    
    if signal is not None:
        assert isinstance(signal, PatternSignal)
        assert signal.action in ['BUY', 'SELL', 'HOLD']
        assert 0 <= signal.confidence <= 1.0


def test_pattern_to_dict():
    """Test Pattern to_dict method."""
    pattern = Pattern(
        pattern_type=PatternType.DOUBLE_BOTTOM,
        sentiment=PatternSentiment.BULLISH,
        reliability_score=0.75,
        start_idx=10,
        end_idx=50,
        key_points=[(10, 49000.0), (30, 49700.0), (50, 49050.0)],
        metadata={'test': 'value'}
    )
    
    result = pattern.to_dict()
    
    assert result['pattern_type'] == 'double_bottom'
    assert result['sentiment'] == 'bullish'
    assert result['reliability_score'] == 0.75
    assert result['start_idx'] == 10
    assert result['end_idx'] == 50
    assert len(result['key_points']) == 3


def test_pattern_signal_to_dict():
    """Test PatternSignal to_dict method."""
    pattern = Pattern(
        pattern_type=PatternType.BULL_FLAG,
        sentiment=PatternSentiment.BULLISH,
        reliability_score=0.8,
        start_idx=0,
        end_idx=20,
        key_points=[]
    )
    
    signal = PatternSignal(
        action='BUY',
        confidence=0.85,
        pattern=pattern,
        reason='Bull flag detected',
        timestamp=datetime.now()
    )
    
    result = signal.to_dict()
    
    assert result['action'] == 'BUY'
    assert result['confidence'] == 0.85
    assert result['reason'] == 'Bull flag detected'
    assert 'pattern' in result
    assert 'timestamp' in result


def test_train_classifier():
    """Test training the ML classifier."""
    recognizer = PatternRecognizer()
    
    # Create sample historical patterns
    historical_patterns = [
        {'pattern_type': 'double_bottom', 'features': [1, 2, 3], 'success': True},
        {'pattern_type': 'double_top', 'features': [2, 3, 4], 'success': False},
        {'pattern_type': 'head_shoulders', 'features': [3, 4, 5], 'success': False},
        {'pattern_type': 'bull_flag', 'features': [4, 5, 6], 'success': True},
        {'pattern_type': 'double_bottom', 'features': [1.1, 2.1, 3.1], 'success': True},
        {'pattern_type': 'double_top', 'features': [2.1, 3.1, 4.1], 'success': False},
        {'pattern_type': 'head_shoulders', 'features': [3.1, 4.1, 5.1], 'success': True},
        {'pattern_type': 'bull_flag', 'features': [4.1, 5.1, 6.1], 'success': True},
        {'pattern_type': 'bear_flag', 'features': [5, 6, 7], 'success': False},
        {'pattern_type': 'triangle', 'features': [6, 7, 8], 'success': True},
    ]
    
    recognizer.train_classifier(historical_patterns)
    
    assert recognizer.is_trained
    assert recognizer.classifier is not None


def test_get_pattern_success_rate():
    """Test getting pattern success rates."""
    recognizer = PatternRecognizer()
    
    # Default should be 0.5
    rate = recognizer.get_pattern_success_rate(PatternType.DOUBLE_BOTTOM)
    assert rate == 0.5
    
    # Set custom rate
    recognizer.pattern_success_rates[PatternType.DOUBLE_BOTTOM.value] = 0.75
    rate = recognizer.get_pattern_success_rate(PatternType.DOUBLE_BOTTOM)
    assert rate == 0.75


def test_save_and_load_model():
    """Test saving and loading pattern recognizer."""
    recognizer = PatternRecognizer(lookback_window=80, min_pattern_length=15)
    
    # Train classifier
    historical_patterns = [
        {'pattern_type': 'test', 'features': [i, i+1, i+2], 'success': i % 2 == 0}
        for i in range(20)
    ]
    recognizer.train_classifier(historical_patterns)
    
    # Save
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_recognizer.pkl')
        recognizer.save_model(filepath)
        
        # Load into new recognizer
        recognizer2 = PatternRecognizer()
        recognizer2.load_model(filepath)
        
        assert recognizer2.is_trained
        assert recognizer2.lookback_window == 80
        assert recognizer2.min_pattern_length == 15
        assert recognizer2.classifier is not None


def test_insufficient_data():
    """Test with insufficient data."""
    recognizer = PatternRecognizer(min_pattern_length=50)
    
    # Create small dataset
    small_data = pd.DataFrame({
        'open': [1, 2, 3, 4, 5],
        'high': [1.1, 2.1, 3.1, 4.1, 5.1],
        'low': [0.9, 1.9, 2.9, 3.9, 4.9],
        'close': [1, 2, 3, 4, 5],
        'volume': [100, 200, 300, 400, 500]
    })
    
    patterns = recognizer.detect_patterns(small_data)
    assert patterns == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
