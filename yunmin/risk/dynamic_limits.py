"""
Dynamic Risk Limits Engine

Adaptive risk limits based on market conditions and portfolio state.
Implements dynamic position sizing, risk budgeting, and drawdown controls.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from loguru import logger
import math


@dataclass
class RiskBudget:
    """Daily risk budget tracking."""
    date: date
    max_daily_risk: float  # Maximum risk allowed per day (as fraction)
    used_risk: float = 0.0  # Risk used so far today
    trades_count: int = 0
    
    @property
    def remaining_risk(self) -> float:
        """Get remaining risk budget for the day."""
        return max(0.0, self.max_daily_risk - self.used_risk)
    
    @property
    def is_exhausted(self) -> bool:
        """Check if daily risk budget is exhausted."""
        return self.used_risk >= self.max_daily_risk
    
    def use_risk(self, amount: float):
        """Consume risk budget."""
        self.used_risk += amount
        self.trades_count += 1


@dataclass
class DrawdownState:
    """Portfolio drawdown state tracking."""
    current_drawdown: float = 0.0  # Current drawdown as fraction
    peak_capital: float = 0.0
    current_capital: float = 0.0
    
    def update(self, capital: float):
        """Update drawdown state."""
        self.current_capital = capital
        if capital > self.peak_capital:
            self.peak_capital = capital
        
        if self.peak_capital > 0:
            self.current_drawdown = (self.peak_capital - capital) / self.peak_capital
        else:
            self.current_drawdown = 0.0
    
    @property
    def drawdown_percentage(self) -> float:
        """Get drawdown as percentage."""
        return self.current_drawdown * 100


@dataclass
class PositionLimits:
    """Dynamic position size limits."""
    max_position_pct: float  # Maximum % of portfolio in single position
    max_total_exposure_pct: float  # Maximum total exposure
    
    def get_max_position_size(self, capital: float) -> float:
        """Calculate maximum position size in currency units."""
        return capital * self.max_position_pct
    
    def get_max_total_exposure(self, capital: float) -> float:
        """Calculate maximum total exposure."""
        return capital * self.max_total_exposure_pct


class MarketRegime:
    """Market volatility regime detection."""
    
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    EXTREME_VOLATILITY = "extreme_volatility"
    
    @staticmethod
    def detect_regime(volatility: float, normal_threshold: float = 0.02, high_threshold: float = 0.04) -> str:
        """
        Detect market regime based on volatility.
        
        Args:
            volatility: Current market volatility (as fraction)
            normal_threshold: Threshold for normal volatility
            high_threshold: Threshold for high volatility
            
        Returns:
            Market regime string
        """
        if volatility < normal_threshold:
            return MarketRegime.NORMAL
        elif volatility < high_threshold:
            return MarketRegime.HIGH_VOLATILITY
        else:
            return MarketRegime.EXTREME_VOLATILITY


class DynamicRiskLimits:
    """
    Dynamic risk limits engine that adapts to market conditions and portfolio state.
    
    Features:
    - Volatility-based position sizing
    - Daily risk budgeting
    - Drawdown-based limit adjustments
    - Market regime adaptation
    """
    
    def __init__(
        self,
        max_daily_risk: float = 0.02,  # 2% max risk per day
        normal_max_position: float = 0.30,  # 30% max in normal conditions
        high_vol_max_position: float = 0.15,  # 15% max in high volatility
        max_total_exposure: float = 0.50,  # 50% max total exposure
        drawdown_threshold_1: float = 0.03,  # 3% drawdown - reduce positions
        drawdown_threshold_2: float = 0.05,  # 5% drawdown - stop new positions
        drawdown_threshold_3: float = 0.07,  # 7% drawdown - emergency exit
    ):
        """
        Initialize dynamic risk limits.
        
        Args:
            max_daily_risk: Maximum daily risk budget (fraction of capital)
            normal_max_position: Max position size in normal conditions
            high_vol_max_position: Max position size in high volatility
            max_total_exposure: Max total exposure at any time
            drawdown_threshold_1: First drawdown threshold (reduce positions)
            drawdown_threshold_2: Second drawdown threshold (stop new)
            drawdown_threshold_3: Third drawdown threshold (emergency exit)
        """
        self.max_daily_risk = max_daily_risk
        self.normal_max_position = normal_max_position
        self.high_vol_max_position = high_vol_max_position
        self.max_total_exposure = max_total_exposure
        
        self.drawdown_threshold_1 = drawdown_threshold_1
        self.drawdown_threshold_2 = drawdown_threshold_2
        self.drawdown_threshold_3 = drawdown_threshold_3
        
        # State tracking
        self.risk_budget: Optional[RiskBudget] = None
        self.drawdown_state = DrawdownState()
        self.current_regime = MarketRegime.NORMAL
        
        logger.info("DynamicRiskLimits initialized with max_daily_risk={:.1%}", max_daily_risk)
    
    def update_state(self, capital: float, volatility: float):
        """
        Update internal state based on current market conditions.
        
        Args:
            capital: Current portfolio capital
            volatility: Current market volatility (as fraction)
        """
        # Update drawdown state
        self.drawdown_state.update(capital)
        
        # Detect market regime
        self.current_regime = MarketRegime.detect_regime(volatility)
        
        # Initialize or reset daily risk budget
        today = date.today()
        if self.risk_budget is None or self.risk_budget.date != today:
            self.risk_budget = RiskBudget(
                date=today,
                max_daily_risk=self.max_daily_risk
            )
            logger.info("Reset daily risk budget for {}", today)
    
    def calculate_max_position_size(
        self,
        capital: float,
        volatility: float,
        price: float
    ) -> float:
        """
        Calculate maximum position size based on volatility and market conditions.
        
        Args:
            capital: Current portfolio capital
            volatility: Asset volatility (as fraction)
            price: Current asset price
            
        Returns:
            Maximum position size in base currency units
        """
        # Base position limit based on market regime
        if self.current_regime == MarketRegime.HIGH_VOLATILITY:
            max_pct = self.high_vol_max_position
            logger.debug("High volatility regime - using {}% max position", max_pct * 100)
        elif self.current_regime == MarketRegime.EXTREME_VOLATILITY:
            max_pct = self.high_vol_max_position * 0.5
            logger.debug("Extreme volatility regime - using {}% max position", max_pct * 100)
        else:
            max_pct = self.normal_max_position
        
        # Adjust based on drawdown
        drawdown_multiplier = self._get_drawdown_multiplier()
        adjusted_pct = max_pct * drawdown_multiplier
        
        # Calculate position size
        max_value = capital * adjusted_pct
        max_size = max_value / price if price > 0 else 0
        
        logger.debug(
            "Max position size: {:.4f} (capital={:.2f}, pct={:.1%}, price={:.2f})",
            max_size, capital, adjusted_pct, price
        )
        
        return max_size
    
    def _get_drawdown_multiplier(self) -> float:
        """
        Get position size multiplier based on current drawdown.
        
        Returns:
            Multiplier (0.0 to 1.0)
        """
        dd = self.drawdown_state.current_drawdown
        
        if dd >= self.drawdown_threshold_2:
            # Stop new positions at 5% drawdown
            return 0.0
        elif dd >= self.drawdown_threshold_1:
            # Reduce position sizes by 25% at 3% drawdown
            return 0.75
        else:
            return 1.0
    
    def can_open_new_position(self) -> tuple[bool, str]:
        """
        Check if new positions can be opened.
        
        Returns:
            Tuple of (can_open, reason)
        """
        # Check daily risk budget
        if self.risk_budget and self.risk_budget.is_exhausted:
            return False, "Daily risk budget exhausted"
        
        # Check drawdown limits
        dd = self.drawdown_state.current_drawdown
        if dd >= self.drawdown_threshold_2:
            return False, f"Drawdown {dd*100:.1f}% exceeds threshold {self.drawdown_threshold_2*100:.1f}%"
        
        return True, "OK"
    
    def should_emergency_exit(self) -> tuple[bool, str]:
        """
        Check if emergency exit of all positions is required.
        
        Returns:
            Tuple of (should_exit, reason)
        """
        dd = self.drawdown_state.current_drawdown
        if dd >= self.drawdown_threshold_3:
            return True, f"Emergency exit: Drawdown {dd*100:.1f}% exceeds {self.drawdown_threshold_3*100:.1f}%"
        
        return False, "OK"
    
    def get_position_limits(self, capital: float) -> PositionLimits:
        """
        Get current position limits based on state.
        
        Args:
            capital: Current portfolio capital
            
        Returns:
            PositionLimits object
        """
        # Adjust based on regime and drawdown
        if self.current_regime == MarketRegime.HIGH_VOLATILITY:
            max_pos = self.high_vol_max_position
        else:
            max_pos = self.normal_max_position
        
        # Apply drawdown adjustment
        max_pos *= self._get_drawdown_multiplier()
        
        return PositionLimits(
            max_position_pct=max_pos,
            max_total_exposure_pct=self.max_total_exposure
        )
    
    def consume_risk_budget(self, risk_amount: float):
        """
        Consume risk budget for a trade.
        
        Args:
            risk_amount: Risk amount as fraction of capital
        """
        if self.risk_budget:
            self.risk_budget.use_risk(risk_amount)
            logger.debug(
                "Risk budget used: {:.2%} / {:.2%} remaining",
                self.risk_budget.used_risk,
                self.risk_budget.remaining_risk
            )
    
    def validate_position_size(
        self,
        position_value: float,
        capital: float,
        total_exposure: float
    ) -> tuple[bool, str]:
        """
        Validate if position size is within limits.
        
        Args:
            position_value: Value of the position
            capital: Current capital
            total_exposure: Total current exposure
            
        Returns:
            Tuple of (is_valid, reason)
        """
        limits = self.get_position_limits(capital)
        
        # Check single position limit
        max_position_value = limits.get_max_position_size(capital)
        if position_value > max_position_value:
            return False, f"Position value {position_value:.2f} exceeds max {max_position_value:.2f}"
        
        # Check total exposure limit
        new_total_exposure = total_exposure + position_value
        max_total = limits.get_max_total_exposure(capital)
        if new_total_exposure > max_total:
            return False, f"Total exposure {new_total_exposure:.2f} would exceed max {max_total:.2f}"
        
        return True, "OK"
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get summary of current risk state.
        
        Returns:
            Dictionary with risk state information
        """
        return {
            "market_regime": self.current_regime,
            "drawdown_pct": self.drawdown_state.drawdown_percentage,
            "drawdown_thresholds": {
                "reduce_positions": self.drawdown_threshold_1 * 100,
                "stop_new": self.drawdown_threshold_2 * 100,
                "emergency_exit": self.drawdown_threshold_3 * 100,
            },
            "risk_budget": {
                "date": str(self.risk_budget.date) if self.risk_budget else None,
                "used": self.risk_budget.used_risk if self.risk_budget else 0,
                "remaining": self.risk_budget.remaining_risk if self.risk_budget else 0,
                "trades_count": self.risk_budget.trades_count if self.risk_budget else 0,
            } if self.risk_budget else None,
            "position_limits": {
                "normal_max_pct": self.normal_max_position * 100,
                "high_vol_max_pct": self.high_vol_max_position * 100,
                "max_total_exposure_pct": self.max_total_exposure * 100,
            },
            "peak_capital": self.drawdown_state.peak_capital,
            "current_capital": self.drawdown_state.current_capital,
        }
