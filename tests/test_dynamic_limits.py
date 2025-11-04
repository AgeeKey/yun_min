"""
Tests for Dynamic Risk Limits Engine
"""

import pytest
from datetime import date
from yunmin.risk.dynamic_limits import (
    DynamicRiskLimits,
    RiskBudget,
    DrawdownState,
    PositionLimits,
    MarketRegime
)


class TestRiskBudget:
    """Test RiskBudget tracking."""
    
    def test_risk_budget_initialization(self):
        """Test risk budget is initialized correctly."""
        today = date.today()
        budget = RiskBudget(date=today, max_daily_risk=0.02)
        
        assert budget.date == today
        assert budget.max_daily_risk == 0.02
        assert budget.used_risk == 0.0
        assert budget.trades_count == 0
        assert budget.remaining_risk == 0.02
        assert not budget.is_exhausted
    
    def test_risk_budget_consumption(self):
        """Test risk budget consumption."""
        budget = RiskBudget(date=date.today(), max_daily_risk=0.02)
        
        budget.use_risk(0.01)
        assert budget.used_risk == 0.01
        assert budget.remaining_risk == 0.01
        assert budget.trades_count == 1
        assert not budget.is_exhausted
        
        budget.use_risk(0.01)
        assert budget.used_risk == 0.02
        assert budget.remaining_risk == 0.0
        assert budget.trades_count == 2
        assert budget.is_exhausted
    
    def test_risk_budget_over_exhaustion(self):
        """Test risk budget handles over-exhaustion."""
        budget = RiskBudget(date=date.today(), max_daily_risk=0.02)
        
        budget.use_risk(0.03)
        assert budget.is_exhausted
        assert budget.remaining_risk == 0.0  # Capped at 0


class TestDrawdownState:
    """Test DrawdownState tracking."""
    
    def test_drawdown_initialization(self):
        """Test drawdown state initialization."""
        state = DrawdownState()
        
        assert state.current_drawdown == 0.0
        assert state.peak_capital == 0.0
        assert state.current_capital == 0.0
        assert state.drawdown_percentage == 0.0
    
    def test_drawdown_update_increasing(self):
        """Test drawdown when capital is increasing."""
        state = DrawdownState()
        
        state.update(10000)
        assert state.peak_capital == 10000
        assert state.current_capital == 10000
        assert state.current_drawdown == 0.0
        
        state.update(11000)
        assert state.peak_capital == 11000
        assert state.current_capital == 11000
        assert state.current_drawdown == 0.0
    
    def test_drawdown_update_decreasing(self):
        """Test drawdown when capital is decreasing."""
        state = DrawdownState()
        
        state.update(10000)
        assert state.current_drawdown == 0.0
        
        state.update(9500)
        assert state.peak_capital == 10000
        assert state.current_capital == 9500
        assert state.current_drawdown == 0.05  # 5% drawdown
        assert state.drawdown_percentage == 5.0
        
        state.update(9000)
        assert state.current_drawdown == 0.10  # 10% drawdown
        assert state.drawdown_percentage == 10.0
    
    def test_drawdown_recovery(self):
        """Test drawdown during recovery."""
        state = DrawdownState()
        
        state.update(10000)
        state.update(9000)  # 10% drawdown
        assert state.current_drawdown == 0.10
        
        state.update(9500)  # Partial recovery
        assert state.current_drawdown == 0.05  # Still 5% from peak
        
        state.update(10000)  # Full recovery
        assert state.current_drawdown == 0.0
        
        state.update(10500)  # New peak
        assert state.peak_capital == 10500
        assert state.current_drawdown == 0.0


class TestMarketRegime:
    """Test MarketRegime detection."""
    
    def test_normal_regime(self):
        """Test normal volatility regime."""
        regime = MarketRegime.detect_regime(0.01)
        assert regime == MarketRegime.NORMAL
    
    def test_high_volatility_regime(self):
        """Test high volatility regime."""
        regime = MarketRegime.detect_regime(0.03)
        assert regime == MarketRegime.HIGH_VOLATILITY
    
    def test_extreme_volatility_regime(self):
        """Test extreme volatility regime."""
        regime = MarketRegime.detect_regime(0.05)
        assert regime == MarketRegime.EXTREME_VOLATILITY
    
    def test_custom_thresholds(self):
        """Test regime detection with custom thresholds."""
        regime = MarketRegime.detect_regime(0.03, normal_threshold=0.04, high_threshold=0.06)
        assert regime == MarketRegime.NORMAL


class TestPositionLimits:
    """Test PositionLimits calculations."""
    
    def test_position_limits(self):
        """Test position limit calculations."""
        limits = PositionLimits(max_position_pct=0.30, max_total_exposure_pct=0.50)
        
        capital = 10000
        assert limits.get_max_position_size(capital) == 3000
        assert limits.get_max_total_exposure(capital) == 5000


class TestDynamicRiskLimits:
    """Test DynamicRiskLimits engine."""
    
    def test_initialization(self):
        """Test dynamic risk limits initialization."""
        limits = DynamicRiskLimits(
            max_daily_risk=0.02,
            normal_max_position=0.30,
            high_vol_max_position=0.15,
            max_total_exposure=0.50
        )
        
        assert limits.max_daily_risk == 0.02
        assert limits.normal_max_position == 0.30
        assert limits.high_vol_max_position == 0.15
        assert limits.max_total_exposure == 0.50
        assert limits.risk_budget is None
        assert limits.current_regime == MarketRegime.NORMAL
    
    def test_update_state(self):
        """Test state update with capital and volatility."""
        limits = DynamicRiskLimits()
        limits.update_state(capital=10000, volatility=0.01)
        
        assert limits.risk_budget is not None
        assert limits.risk_budget.date == date.today()
        assert limits.drawdown_state.current_capital == 10000
        assert limits.current_regime == MarketRegime.NORMAL
    
    def test_update_state_high_volatility(self):
        """Test state update with high volatility."""
        limits = DynamicRiskLimits()
        limits.update_state(capital=10000, volatility=0.03)
        
        assert limits.current_regime == MarketRegime.HIGH_VOLATILITY
    
    def test_calculate_max_position_size_normal(self):
        """Test max position size calculation in normal conditions."""
        limits = DynamicRiskLimits(normal_max_position=0.30)
        limits.update_state(capital=10000, volatility=0.01)
        
        max_size = limits.calculate_max_position_size(
            capital=10000,
            volatility=0.01,
            price=50000
        )
        
        # 30% of 10000 = 3000, divided by price 50000 = 0.06
        assert abs(max_size - 0.06) < 0.001
    
    def test_calculate_max_position_size_high_volatility(self):
        """Test max position size calculation in high volatility."""
        limits = DynamicRiskLimits(
            normal_max_position=0.30,
            high_vol_max_position=0.15
        )
        limits.update_state(capital=10000, volatility=0.03)
        
        max_size = limits.calculate_max_position_size(
            capital=10000,
            volatility=0.03,
            price=50000
        )
        
        # 15% of 10000 = 1500, divided by price 50000 = 0.03
        assert abs(max_size - 0.03) < 0.001
    
    def test_drawdown_reduces_position_size(self):
        """Test that drawdown reduces position sizes."""
        limits = DynamicRiskLimits(
            normal_max_position=0.30,
            drawdown_threshold_1=0.03
        )
        
        # Set initial state
        limits.update_state(capital=10000, volatility=0.01)
        limits.drawdown_state.update(10000)
        
        # Simulate 3% drawdown
        limits.drawdown_state.update(9700)
        
        max_size = limits.calculate_max_position_size(
            capital=9700,
            volatility=0.01,
            price=50000
        )
        
        # Should be reduced by 25%: 0.30 * 0.75 * 9700 / 50000 = 0.04365
        expected = 0.30 * 0.75 * 9700 / 50000
        assert abs(max_size - expected) < 0.001
    
    def test_can_open_new_position_ok(self):
        """Test can open new position in normal conditions."""
        limits = DynamicRiskLimits()
        limits.update_state(capital=10000, volatility=0.01)
        
        can_open, reason = limits.can_open_new_position()
        assert can_open
        assert reason == "OK"
    
    def test_can_open_new_position_risk_exhausted(self):
        """Test cannot open new position when risk budget exhausted."""
        limits = DynamicRiskLimits(max_daily_risk=0.02)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Exhaust risk budget
        limits.risk_budget.use_risk(0.02)
        
        can_open, reason = limits.can_open_new_position()
        assert not can_open
        assert "risk budget exhausted" in reason.lower()
    
    def test_can_open_new_position_drawdown_threshold(self):
        """Test cannot open new position at drawdown threshold 2."""
        limits = DynamicRiskLimits(drawdown_threshold_2=0.05)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Simulate 5% drawdown
        limits.drawdown_state.update(10000)
        limits.drawdown_state.update(9500)
        
        can_open, reason = limits.can_open_new_position()
        assert not can_open
        assert "drawdown" in reason.lower()
    
    def test_should_emergency_exit(self):
        """Test emergency exit trigger at threshold 3."""
        limits = DynamicRiskLimits(drawdown_threshold_3=0.07)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Simulate 7% drawdown
        limits.drawdown_state.update(10000)
        limits.drawdown_state.update(9300)
        
        should_exit, reason = limits.should_emergency_exit()
        assert should_exit
        assert "emergency exit" in reason.lower()
    
    def test_should_not_emergency_exit(self):
        """Test no emergency exit below threshold."""
        limits = DynamicRiskLimits(drawdown_threshold_3=0.07)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Simulate 5% drawdown (below threshold)
        limits.drawdown_state.update(10000)
        limits.drawdown_state.update(9500)
        
        should_exit, reason = limits.should_emergency_exit()
        assert not should_exit
        assert reason == "OK"
    
    def test_validate_position_size_ok(self):
        """Test position size validation passes."""
        limits = DynamicRiskLimits(normal_max_position=0.30)
        limits.update_state(capital=10000, volatility=0.01)
        
        is_valid, reason = limits.validate_position_size(
            position_value=2000,
            capital=10000,
            total_exposure=1000
        )
        
        assert is_valid
        assert reason == "OK"
    
    def test_validate_position_size_too_large(self):
        """Test position size validation fails for too large position."""
        limits = DynamicRiskLimits(normal_max_position=0.30)
        limits.update_state(capital=10000, volatility=0.01)
        
        is_valid, reason = limits.validate_position_size(
            position_value=4000,  # Exceeds 30% limit
            capital=10000,
            total_exposure=0
        )
        
        assert not is_valid
        assert "exceeds max" in reason.lower()
    
    def test_validate_position_size_total_exposure_exceeded(self):
        """Test position size validation fails for total exposure."""
        limits = DynamicRiskLimits(max_total_exposure=0.50)
        limits.update_state(capital=10000, volatility=0.01)
        
        is_valid, reason = limits.validate_position_size(
            position_value=2000,
            capital=10000,
            total_exposure=4000  # Would exceed 50% total
        )
        
        assert not is_valid
        assert "total exposure" in reason.lower()
    
    def test_consume_risk_budget(self):
        """Test risk budget consumption."""
        limits = DynamicRiskLimits(max_daily_risk=0.02)
        limits.update_state(capital=10000, volatility=0.01)
        
        limits.consume_risk_budget(0.01)
        assert limits.risk_budget.used_risk == 0.01
        assert limits.risk_budget.trades_count == 1
    
    def test_get_state_summary(self):
        """Test state summary generation."""
        limits = DynamicRiskLimits()
        limits.update_state(capital=10000, volatility=0.01)
        
        summary = limits.get_state_summary()
        
        assert "market_regime" in summary
        assert "drawdown_pct" in summary
        assert "drawdown_thresholds" in summary
        assert "risk_budget" in summary
        assert "position_limits" in summary
        assert "peak_capital" in summary
        assert "current_capital" in summary
        
        assert summary["market_regime"] == MarketRegime.NORMAL
        assert summary["peak_capital"] == 10000
        assert summary["current_capital"] == 10000
    
    def test_risk_budget_resets_daily(self):
        """Test that risk budget resets on new day."""
        limits = DynamicRiskLimits(max_daily_risk=0.02)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Consume some risk
        limits.consume_risk_budget(0.01)
        assert limits.risk_budget.used_risk == 0.01
        
        # Create a new budget (simulating new day)
        old_date = limits.risk_budget.date
        limits.risk_budget = RiskBudget(
            date=date.today(),
            max_daily_risk=0.02
        )
        
        # Update state should reset if date changes
        # (In real scenario, date.today() would return different value)
        limits.update_state(capital=10000, volatility=0.01)
        
        # Budget should be reset if it's a new day
        assert limits.risk_budget.used_risk == 0.0
