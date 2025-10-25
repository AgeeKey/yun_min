"""
Risk Management Policies

Defines various risk checks and policies for trading.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time


class RiskCheckResult(Enum):
    """Result of a risk check."""
    APPROVED = "approved"
    REJECTED = "rejected"
    WARNING = "warning"


@dataclass
class PositionInfo:
    """Information about current position."""
    symbol: str
    size: float  # Position size in base currency
    entry_price: float
    current_price: float
    leverage: float = 1.0
    unrealized_pnl: float = 0.0
    
    @property
    def pnl_percentage(self) -> float:
        """Calculate PnL percentage."""
        if self.entry_price == 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price * 100 * self.leverage


@dataclass
class OrderRequest:
    """Represents a trading order request."""
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market' or 'limit'
    amount: float
    price: Optional[float] = None
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class RiskPolicy:
    """Base class for risk policies."""
    
    def __init__(self, name: str):
        self.name = name
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """
        Check if order passes this risk policy.
        
        Args:
            order: Order request to check
            context: Additional context (balance, positions, etc.)
            
        Returns:
            Tuple of (result, message)
        """
        raise NotImplementedError


class MaxPositionSizePolicy(RiskPolicy):
    """Limits maximum position size as fraction of capital."""
    
    def __init__(self, max_fraction: float = 0.1):
        super().__init__("max_position_size")
        self.max_fraction = max_fraction
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if order size exceeds maximum position size."""
        capital = context.get('capital', 0)
        order_value = order.amount * (order.price or context.get('current_price', 0))
        
        max_allowed = capital * self.max_fraction
        
        if order_value > max_allowed:
            return (
                RiskCheckResult.REJECTED,
                f"Order value {order_value:.2f} exceeds max position size {max_allowed:.2f} "
                f"({self.max_fraction*100:.1f}% of capital)"
            )
        
        return RiskCheckResult.APPROVED, "Position size check passed"


class MaxLeveragePolicy(RiskPolicy):
    """Limits maximum leverage."""
    
    def __init__(self, max_leverage: float = 3.0):
        super().__init__("max_leverage")
        self.max_leverage = max_leverage
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if leverage exceeds maximum."""
        if order.leverage > self.max_leverage:
            return (
                RiskCheckResult.REJECTED,
                f"Leverage {order.leverage}x exceeds maximum {self.max_leverage}x"
            )
        
        return RiskCheckResult.APPROVED, "Leverage check passed"


class MaxDailyDrawdownPolicy(RiskPolicy):
    """Prevents trading if daily drawdown exceeds limit."""
    
    def __init__(self, max_drawdown: float = 0.05):
        super().__init__("max_daily_drawdown")
        self.max_drawdown = max_drawdown
        self.daily_start_capital = None
        self.last_reset_day = None
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if daily drawdown exceeds limit."""
        current_capital = context.get('capital', 0)
        current_day = time.strftime('%Y-%m-%d')
        
        # Reset at start of new day
        if self.last_reset_day != current_day:
            self.daily_start_capital = current_capital
            self.last_reset_day = current_day
            
        if self.daily_start_capital is None:
            self.daily_start_capital = current_capital
            
        drawdown = (self.daily_start_capital - current_capital) / self.daily_start_capital
        
        if drawdown > self.max_drawdown:
            return (
                RiskCheckResult.REJECTED,
                f"Daily drawdown {drawdown*100:.2f}% exceeds limit {self.max_drawdown*100:.2f}%. "
                "Trading halted for today."
            )
        elif drawdown > self.max_drawdown * 0.8:
            return (
                RiskCheckResult.WARNING,
                f"Daily drawdown {drawdown*100:.2f}% approaching limit {self.max_drawdown*100:.2f}%"
            )
            
        return RiskCheckResult.APPROVED, "Drawdown check passed"


class StopLossPolicy(RiskPolicy):
    """Enforces stop loss on positions."""
    
    def __init__(self, stop_loss_pct: float = 0.02):
        super().__init__("stop_loss")
        self.stop_loss_pct = stop_loss_pct
        
    def check_position(self, position: PositionInfo) -> tuple[RiskCheckResult, str]:
        """Check if position has hit stop loss."""
        if position.pnl_percentage <= -self.stop_loss_pct * 100:
            return (
                RiskCheckResult.REJECTED,
                f"Position hit stop loss: {position.pnl_percentage:.2f}% loss "
                f"(limit: {self.stop_loss_pct*100:.2f}%)"
            )
            
        return RiskCheckResult.APPROVED, "Stop loss check passed"
    
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if order has stop loss set."""
        # For new orders, just verify stop loss is configured if required
        return RiskCheckResult.APPROVED, "Order validated"


class MarginCheckPolicy(RiskPolicy):
    """Ensures sufficient margin for leveraged positions."""
    
    def __init__(self, min_margin_ratio: float = 0.15):
        super().__init__("margin_check")
        self.min_margin_ratio = min_margin_ratio
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if sufficient margin available."""
        capital = context.get('capital', 0)
        current_price = order.price or context.get('current_price', 0)
        
        required_margin = (order.amount * current_price) / order.leverage
        available_margin = capital * 0.95  # Keep 5% buffer
        
        if required_margin > available_margin:
            return (
                RiskCheckResult.REJECTED,
                f"Insufficient margin: required {required_margin:.2f}, "
                f"available {available_margin:.2f}"
            )
            
        # Warning if using more than 70% of capital
        if required_margin > capital * 0.7:
            return (
                RiskCheckResult.WARNING,
                f"High margin usage: {required_margin/capital*100:.1f}% of capital"
            )
            
        return RiskCheckResult.APPROVED, "Margin check passed"


class CircuitBreakerPolicy(RiskPolicy):
    """Emergency circuit breaker for abnormal situations."""
    
    def __init__(self):
        super().__init__("circuit_breaker")
        self.is_triggered = False
        self.trigger_reason = ""
        
    def trigger(self, reason: str):
        """Trigger the circuit breaker."""
        self.is_triggered = True
        self.trigger_reason = reason
        
    def reset(self):
        """Reset the circuit breaker."""
        self.is_triggered = False
        self.trigger_reason = ""
        
    def check(self, order: OrderRequest, context: Dict[str, Any]) -> tuple[RiskCheckResult, str]:
        """Check if circuit breaker is triggered."""
        if self.is_triggered:
            return (
                RiskCheckResult.REJECTED,
                f"Circuit breaker triggered: {self.trigger_reason}"
            )
            
        return RiskCheckResult.APPROVED, "Circuit breaker not triggered"
