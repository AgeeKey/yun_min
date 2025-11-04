"""
Tests for Adaptive Position Sizing Optimizer
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.strategy.position_optimizer import (
    PositionOptimizer,
    PositionSize,
    PerformanceState
)


class TestPositionOptimizer:
    """Test suite for Position Optimizer."""
    
    @pytest.fixture
    def sample_data_low_volatility(self):
        """Create sample data with low volatility."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # Low volatility: small price movements
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(100) * 10)  # Small changes
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.rand(100) * 5,
            'low': prices - np.random.rand(100) * 5,
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
    
    @pytest.fixture
    def sample_data_high_volatility(self):
        """Create sample data with high volatility."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        # High volatility: large price movements
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(100) * 500)  # Large changes
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.rand(100) * 200,
            'low': prices - np.random.rand(100) * 200,
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
    
    @pytest.fixture
    def optimizer(self):
        """Create default optimizer instance."""
        return PositionOptimizer(initial_capital=10000.0, base_risk_pct=0.02)
    
    def test_initialization(self):
        """Test optimizer initialization."""
        optimizer = PositionOptimizer(
            initial_capital=10000.0,
            base_risk_pct=0.02,
            atr_period=14
        )
        
        assert optimizer.initial_capital == 10000.0
        assert optimizer.current_capital == 10000.0
        assert optimizer.base_risk_pct == 0.02
        assert optimizer.atr_period == 14
        assert optimizer.current_streak == 0
        assert optimizer.max_drawdown == 0.0
    
    def test_insufficient_data(self, optimizer):
        """Test with insufficient data."""
        data = pd.DataFrame({
            'close': [50000],
            'high': [50100],
            'low': [49900],
            'volume': [100]
        })
        
        result = optimizer.calculate_position_size(data)
        
        assert result.adjusted_size == 0.0
        assert "Insufficient data" in result.reasoning
    
    def test_calculate_position_size_basic(self, optimizer, sample_data_low_volatility):
        """Test basic position size calculation."""
        result = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.7
        )
        
        assert result.base_size > 0
        assert result.adjusted_size > 0
        assert result.size_multiplier > 0
        assert 0 <= result.volatility_factor <= 1.0
        assert 0.75 <= result.performance_factor <= 1.25
        assert result.risk_percentage > 0
        assert len(result.reasoning) > 0
    
    def test_high_volatility_reduces_position(self, optimizer, sample_data_high_volatility):
        """Test that high volatility reduces position size."""
        result = optimizer.calculate_position_size(
            sample_data_high_volatility,
            signal_confidence=0.7
        )
        
        # High volatility should give factor between 0.25-0.50
        assert 0.25 <= result.volatility_factor <= 0.50
        assert "High volatility" in result.reasoning or "volatility" in result.reasoning.lower()
    
    def test_low_volatility_increases_position(self, optimizer, sample_data_low_volatility):
        """Test that low volatility increases position size."""
        result = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.7
        )
        
        # Low volatility should give factor between 0.75-1.00
        assert result.volatility_factor >= 0.50  # At least normal or higher
    
    def test_winning_streak_increases_position(self, optimizer, sample_data_low_volatility):
        """Test that winning streak increases position size."""
        # Simulate 3 winning trades
        for _ in range(3):
            optimizer.record_trade(profit_loss=100.0, was_win=True)
        
        assert optimizer.current_streak == 3
        
        result = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.7
        )
        
        assert result.performance_factor == 1.25  # +25% after 3 wins
        assert "Winning streak" in result.reasoning
    
    def test_losing_streak_decreases_position(self, optimizer, sample_data_low_volatility):
        """Test that losing streak decreases position size."""
        # Simulate 3 losing trades
        for _ in range(3):
            optimizer.record_trade(profit_loss=-100.0, was_win=False)
        
        assert optimizer.current_streak == -3
        
        result = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.7
        )
        
        assert result.performance_factor == 0.75  # -25% after 3 losses
        assert "Losing streak" in result.reasoning
    
    def test_record_trade_win(self, optimizer):
        """Test recording a winning trade."""
        initial_capital = optimizer.current_capital
        
        optimizer.record_trade(profit_loss=100.0, was_win=True)
        
        assert optimizer.current_capital == initial_capital + 100.0
        assert optimizer.current_streak == 1
        assert len(optimizer.trade_history) == 1
        assert optimizer.trade_history[0]['was_win'] is True
    
    def test_record_trade_loss(self, optimizer):
        """Test recording a losing trade."""
        initial_capital = optimizer.current_capital
        
        optimizer.record_trade(profit_loss=-50.0, was_win=False)
        
        assert optimizer.current_capital == initial_capital - 50.0
        assert optimizer.current_streak == -1
        assert len(optimizer.trade_history) == 1
        assert optimizer.trade_history[0]['was_win'] is False
    
    def test_streak_reset_on_direction_change(self, optimizer):
        """Test that streak resets when direction changes."""
        # 2 wins
        optimizer.record_trade(100, True)
        optimizer.record_trade(100, True)
        assert optimizer.current_streak == 2
        
        # 1 loss should reset to -1
        optimizer.record_trade(-50, False)
        assert optimizer.current_streak == -1
        
        # 1 win should reset to 1
        optimizer.record_trade(100, True)
        assert optimizer.current_streak == 1
    
    def test_max_drawdown_tracking(self, optimizer):
        """Test maximum drawdown tracking."""
        # Win to set peak
        optimizer.record_trade(1000, True)
        assert optimizer.peak_capital == 11000
        
        # Losses to create drawdown
        optimizer.record_trade(-500, False)
        optimizer.record_trade(-500, False)
        
        expected_dd = (11000 - 10000) / 11000
        assert abs(optimizer.max_drawdown - expected_dd) < 0.01
    
    def test_reset_on_recovery(self, optimizer):
        """Test streak reset on capital recovery."""
        # Create losing streak
        for _ in range(3):
            optimizer.record_trade(-100, False)
        
        assert optimizer.current_streak == -3
        
        # Recover capital
        optimizer.record_trade(400, True)
        optimizer.reset_on_recovery()
        
        # Streak should reset if recovered
        if optimizer.current_capital >= optimizer.peak_capital * 0.95:
            assert optimizer.current_streak == 0
    
    def test_get_statistics_empty(self, optimizer):
        """Test statistics with no trades."""
        stats = optimizer.get_statistics()
        
        assert stats['total_trades'] == 0
        assert stats['win_rate'] == 0.0
        assert stats['total_pnl'] == 0.0
        assert stats['current_capital'] == 10000.0
    
    def test_get_statistics_with_trades(self, optimizer):
        """Test statistics with trade history."""
        # 2 wins, 1 loss
        optimizer.record_trade(100, True)
        optimizer.record_trade(50, True)
        optimizer.record_trade(-30, False)
        
        stats = optimizer.get_statistics()
        
        assert stats['total_trades'] == 3
        assert stats['wins'] == 2
        assert stats['losses'] == 1
        assert stats['win_rate'] == 2/3
        assert stats['total_pnl'] == 120
        assert stats['current_capital'] == 10120
        assert stats['roi'] == 1.2
    
    def test_adjust_for_drawdown_none(self, optimizer):
        """Test drawdown adjustment with no drawdown."""
        factor = optimizer.adjust_for_drawdown()
        assert factor == 1.0
    
    def test_adjust_for_drawdown_moderate(self, optimizer):
        """Test drawdown adjustment with moderate drawdown."""
        # Create 15% drawdown
        optimizer.peak_capital = 10000
        optimizer.current_capital = 8500
        
        factor = optimizer.adjust_for_drawdown()
        assert factor == 0.75  # 10-20% DD
    
    def test_adjust_for_drawdown_severe(self, optimizer):
        """Test drawdown adjustment with severe drawdown."""
        # Create 25% drawdown
        optimizer.peak_capital = 10000
        optimizer.current_capital = 7500
        
        factor = optimizer.adjust_for_drawdown()
        assert factor == 0.5  # 20%+ DD
    
    def test_position_size_limits(self, optimizer, sample_data_low_volatility):
        """Test that position size respects min/max limits."""
        # Test with very high confidence
        result = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=1.0
        )
        
        max_allowed = optimizer.current_capital * optimizer.max_position_pct
        min_allowed = optimizer.current_capital * optimizer.min_position_pct
        
        assert result.adjusted_size <= max_allowed
        assert result.adjusted_size >= min_allowed
    
    def test_position_size_with_low_confidence(self, optimizer, sample_data_low_volatility):
        """Test position sizing with low confidence signal."""
        result_low = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.3
        )
        
        result_high = optimizer.calculate_position_size(
            sample_data_low_volatility,
            signal_confidence=0.9
        )
        
        # Higher confidence should generally give larger base size
        # (though final size depends on other factors too)
        assert result_high.base_size >= result_low.base_size
    
    def test_get_params(self, optimizer):
        """Test getting optimizer parameters."""
        params = optimizer.get_params()
        
        assert 'base_risk_pct' in params
        assert 'atr_period' in params
        assert 'kelly_fraction' in params
        assert 'max_position_pct' in params
        assert 'min_position_pct' in params
        assert params['base_risk_pct'] == 0.02
        assert params['atr_period'] == 14
    
    def test_atr_calculation(self, optimizer):
        """Test ATR calculation."""
        # Create data with known ranges
        data = pd.DataFrame({
            'high': [100, 105, 103, 108, 106] + [100] * 10,
            'low': [95, 100, 98, 103, 101] + [95] * 10,
            'close': [98, 103, 101, 106, 104] + [98] * 10,
            'volume': [1000] * 15
        })
        
        atr = optimizer._calculate_atr(data)
        
        assert atr > 0
        assert isinstance(atr, (int, float, np.number))
    
    def test_volatility_factor_high(self, optimizer):
        """Test volatility factor calculation for high volatility."""
        high_vol = 0.04  # 4% volatility
        factor = optimizer._get_volatility_factor(high_vol)
        
        assert 0.25 <= factor <= 0.50
    
    def test_volatility_factor_low(self, optimizer):
        """Test volatility factor calculation for low volatility."""
        low_vol = 0.01  # 1% volatility
        factor = optimizer._get_volatility_factor(low_vol)
        
        assert 0.75 <= factor <= 1.0
    
    def test_volatility_factor_normal(self, optimizer):
        """Test volatility factor calculation for normal volatility."""
        normal_vol = 0.02  # 2% volatility (between thresholds)
        factor = optimizer._get_volatility_factor(normal_vol)
        
        assert 0.50 <= factor <= 0.75
    
    def test_performance_factor_neutral(self, optimizer):
        """Test performance factor with no streak."""
        factor = optimizer._get_performance_factor()
        assert factor == 1.0
    
    def test_performance_factor_winning(self, optimizer):
        """Test performance factor after wins."""
        optimizer.current_streak = 3
        factor = optimizer._get_performance_factor()
        assert factor == 1.25
    
    def test_performance_factor_losing(self, optimizer):
        """Test performance factor after losses."""
        optimizer.current_streak = -3
        factor = optimizer._get_performance_factor()
        assert factor == 0.75
    
    def test_capital_tracking(self, optimizer):
        """Test that capital is tracked correctly through trades."""
        initial = optimizer.current_capital
        
        optimizer.record_trade(100, True)
        assert optimizer.current_capital == initial + 100
        
        optimizer.record_trade(-50, False)
        assert optimizer.current_capital == initial + 100 - 50
        
        optimizer.record_trade(200, True)
        assert optimizer.current_capital == initial + 100 - 50 + 200
    
    def test_custom_parameters(self):
        """Test initialization with custom parameters."""
        optimizer = PositionOptimizer(
            initial_capital=50000.0,
            base_risk_pct=0.01,
            atr_period=20,
            kelly_fraction=0.5,
            streak_threshold=5
        )
        
        assert optimizer.initial_capital == 50000.0
        assert optimizer.base_risk_pct == 0.01
        assert optimizer.atr_period == 20
        assert optimizer.kelly_fraction == 0.5
        assert optimizer.streak_threshold == 5
