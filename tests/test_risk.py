"""
Tests for Risk Management System
"""

import pytest
from yunmin.core.config import RiskConfig
from yunmin.risk import RiskManager
from yunmin.risk.policies import (
    OrderRequest,
    PositionInfo,
    MaxPositionSizePolicy,
    MaxLeveragePolicy,
    MaxDailyDrawdownPolicy,
    RiskCheckResult
)


class TestRiskPolicies:
    """Test individual risk policies."""
    
    def test_max_position_size_approved(self):
        """Test that valid position size is approved."""
        policy = MaxPositionSizePolicy(max_fraction=0.1)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01
        )
        
        context = {'capital': 10000, 'current_price': 50000}
        result, message = policy.check(order, context)
        
        assert result == RiskCheckResult.APPROVED
        
    def test_max_position_size_rejected(self):
        """Test that excessive position size is rejected."""
        policy = MaxPositionSizePolicy(max_fraction=0.1)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.5  # 50% of capital
        )
        
        context = {'capital': 10000, 'current_price': 50000}
        result, message = policy.check(order, context)
        
        assert result == RiskCheckResult.REJECTED
        assert "exceeds max position size" in message
        
    def test_max_leverage_approved(self):
        """Test that valid leverage is approved."""
        policy = MaxLeveragePolicy(max_leverage=3.0)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=2.0
        )
        
        result, message = policy.check(order, {})
        
        assert result == RiskCheckResult.APPROVED
        
    def test_max_leverage_rejected(self):
        """Test that excessive leverage is rejected."""
        policy = MaxLeveragePolicy(max_leverage=3.0)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=10.0
        )
        
        result, message = policy.check(order, {})
        
        assert result == RiskCheckResult.REJECTED
        assert "exceeds maximum" in message


class TestRiskManager:
    """Test Risk Manager."""
    
    def test_risk_manager_initialization(self):
        """Test that risk manager initializes correctly."""
        config = RiskConfig()
        manager = RiskManager(config)
        
        assert len(manager.policies) > 0
        assert manager.circuit_breaker is not None
        
    def test_validate_order_approved(self):
        """Test that valid order is approved."""
        config = RiskConfig(
            max_position_size=0.1,
            max_leverage=3.0
        )
        manager = RiskManager(config)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=2.0
        )
        
        context = {'capital': 10000, 'current_price': 50000}
        approved, messages = manager.validate_order(order, context)
        
        assert approved is True
        
    def test_validate_order_rejected(self):
        """Test that invalid order is rejected."""
        config = RiskConfig(
            max_position_size=0.1,
            max_leverage=3.0
        )
        manager = RiskManager(config)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.5,  # Too large
            leverage=2.0
        )
        
        context = {'capital': 10000, 'current_price': 50000}
        approved, messages = manager.validate_order(order, context)
        
        assert approved is False
        assert len(messages) > 0
        
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        config = RiskConfig(enable_circuit_breaker=True)
        manager = RiskManager(config)
        
        # Initially not triggered
        assert manager.is_circuit_breaker_triggered() is False
        
        # Trigger circuit breaker
        manager.trigger_circuit_breaker("Test emergency")
        assert manager.is_circuit_breaker_triggered() is True
        
        # Orders should be rejected
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01
        )
        approved, messages = manager.validate_order(order, {'capital': 10000})
        assert approved is False
        
        # Reset circuit breaker
        manager.reset_circuit_breaker()
        assert manager.is_circuit_breaker_triggered() is False
        
    def test_position_stop_loss(self):
        """Test position stop loss checking."""
        config = RiskConfig(stop_loss_pct=0.02)
        manager = RiskManager(config)
        
        # Position with 3% loss (should trigger 2% stop loss)
        position = PositionInfo(
            symbol='BTC/USDT',
            size=0.1,
            entry_price=50000,
            current_price=48500,  # 3% loss
            leverage=1.0
        )
        
        should_close, reason = manager.check_position(position)
        assert should_close is True
        assert "stop loss" in reason.lower()
        
    def test_position_take_profit(self):
        """Test position take profit checking."""
        config = RiskConfig(take_profit_pct=0.03)
        manager = RiskManager(config)
        
        # Position with 4% profit (should trigger 3% take profit)
        position = PositionInfo(
            symbol='BTC/USDT',
            size=0.1,
            entry_price=50000,
            current_price=52000,  # 4% profit
            leverage=1.0
        )
        
        should_close, reason = manager.check_position(position)
        assert should_close is True
        assert "take profit" in reason.lower()
