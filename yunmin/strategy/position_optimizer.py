"""
Adaptive Position Sizing Optimizer

Dynamically adjusts position sizes based on:
- Market volatility (ATR)
- Kelly Criterion for optimal sizing
- Portfolio performance (win/loss streaks)
- Dynamic risk management
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class PerformanceState(Enum):
    """Current performance state."""
    WINNING_STREAK = "winning_streak"
    LOSING_STREAK = "losing_streak"
    NEUTRAL = "neutral"


@dataclass
class PositionSize:
    """Position sizing recommendation."""
    base_size: float
    adjusted_size: float
    size_multiplier: float
    volatility_factor: float
    performance_factor: float
    risk_percentage: float
    reasoning: str


class PositionOptimizer:
    """
    Adaptive position sizing optimizer.
    
    Features:
    - ATR-based volatility analysis
    - Kelly Criterion for optimal sizing
    - Dynamic adjustment based on drawdown
    - Performance-based scaling (win/loss streaks)
    - Automatic position reduction in high risk
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        base_risk_pct: float = 0.02,
        atr_period: int = 14,
        kelly_fraction: float = 0.25,
        max_position_pct: float = 0.10,
        min_position_pct: float = 0.01,
        volatility_threshold_high: float = 0.03,
        volatility_threshold_low: float = 0.015,
        streak_threshold: int = 3,
        performance_adjustment_pct: float = 0.25,
        reward_risk_ratio: float = 2.0
    ):
        """
        Initialize position optimizer.
        
        Args:
            initial_capital: Starting capital
            base_risk_pct: Base risk per trade (e.g., 0.02 = 2%)
            atr_period: Period for ATR calculation
            kelly_fraction: Fraction of Kelly Criterion to use (0.25 = 25% Kelly)
            max_position_pct: Maximum position size as % of capital
            min_position_pct: Minimum position size as % of capital
            volatility_threshold_high: High volatility threshold (3% default)
            volatility_threshold_low: Low volatility threshold (1.5% default)
            streak_threshold: Number of wins/losses to trigger adjustment
            performance_adjustment_pct: % to adjust size after streaks (0.25 = 25%)
            reward_risk_ratio: Expected reward/risk ratio for Kelly (2.0 = 2:1 default)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.base_risk_pct = base_risk_pct
        self.atr_period = atr_period
        self.kelly_fraction = kelly_fraction
        self.max_position_pct = max_position_pct
        self.min_position_pct = min_position_pct
        self.volatility_threshold_high = volatility_threshold_high
        self.volatility_threshold_low = volatility_threshold_low
        self.streak_threshold = streak_threshold
        self.performance_adjustment_pct = performance_adjustment_pct
        self.reward_risk_ratio = reward_risk_ratio
        
        # Performance tracking
        self.trade_history: List[Dict[str, Any]] = []
        self.current_streak = 0  # Positive for wins, negative for losses
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        logger.info(f"Position Optimizer initialized: base_risk={base_risk_pct*100:.1f}%")
    
    def calculate_position_size(
        self,
        df: pd.DataFrame,
        signal_confidence: float = 0.7,
        current_price: Optional[float] = None
    ) -> PositionSize:
        """
        Calculate optimal position size.
        
        Args:
            df: Market data DataFrame with OHLCV
            signal_confidence: Signal confidence (0.0-1.0)
            current_price: Current price (uses latest close if not provided)
            
        Returns:
            PositionSize recommendation
        """
        if df.empty or len(df) < self.atr_period:
            return PositionSize(
                base_size=0.0,
                adjusted_size=0.0,
                size_multiplier=0.0,
                volatility_factor=0.0,
                performance_factor=0.0,
                risk_percentage=0.0,
                reasoning="Insufficient data for position sizing"
            )
        
        if current_price is None:
            current_price = df['close'].iloc[-1]
        
        # Calculate volatility
        atr = self._calculate_atr(df)
        volatility_pct = atr / current_price
        
        # Calculate volatility factor
        volatility_factor = self._get_volatility_factor(volatility_pct)
        
        # Calculate performance factor
        performance_factor = self._get_performance_factor()
        
        # Calculate base position size
        base_size = self._calculate_base_size(signal_confidence)
        
        # Apply adjustments
        size_multiplier = volatility_factor * performance_factor
        adjusted_size = base_size * size_multiplier
        
        # Apply limits
        max_size = self.current_capital * self.max_position_pct
        min_size = self.current_capital * self.min_position_pct
        adjusted_size = max(min_size, min(adjusted_size, max_size))
        
        # Calculate risk percentage
        risk_pct = (adjusted_size / self.current_capital) * 100
        
        # Build reasoning
        reasoning = self._build_reasoning(
            volatility_pct, 
            volatility_factor, 
            performance_factor,
            size_multiplier,
            risk_pct
        )
        
        return PositionSize(
            base_size=base_size,
            adjusted_size=adjusted_size,
            size_multiplier=size_multiplier,
            volatility_factor=volatility_factor,
            performance_factor=performance_factor,
            risk_percentage=risk_pct,
            reasoning=reasoning
        )
    
    def _calculate_atr(self, df: pd.DataFrame) -> float:
        """
        Calculate Average True Range.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            ATR value
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # True Range components
        tr1 = high - low
        # Use shift for previous close (proper handling of first element)
        prev_close = np.concatenate([[close[0]], close[:-1]])
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Average True Range
        atr = pd.Series(tr).rolling(window=self.atr_period).mean().iloc[-1]
        
        return atr
    
    def _get_volatility_factor(self, volatility_pct: float) -> float:
        """
        Calculate volatility adjustment factor.
        
        High volatility -> reduce position (0.25-0.50)
        Low volatility -> increase position (0.75-1.00)
        Normal volatility -> standard position (0.50-0.75)
        
        Args:
            volatility_pct: Volatility as percentage
            
        Returns:
            Volatility factor (0.25 to 1.0)
        """
        if volatility_pct > self.volatility_threshold_high:
            # High volatility: 25-50% of normal size
            factor = 0.25 + (0.25 * (1 - min(volatility_pct / 0.05, 1.0)))
            logger.debug(f"High volatility ({volatility_pct*100:.2f}%) -> factor {factor:.2f}")
            return factor
        elif volatility_pct < self.volatility_threshold_low:
            # Low volatility: 75-100% of normal size
            factor = 0.75 + (0.25 * (1 - volatility_pct / self.volatility_threshold_low))
            logger.debug(f"Low volatility ({volatility_pct*100:.2f}%) -> factor {factor:.2f}")
            return factor
        else:
            # Normal volatility: 50-75% of normal size
            normalized = (volatility_pct - self.volatility_threshold_low) / \
                        (self.volatility_threshold_high - self.volatility_threshold_low)
            factor = 0.75 - (0.25 * normalized)
            logger.debug(f"Normal volatility ({volatility_pct*100:.2f}%) -> factor {factor:.2f}")
            return factor
    
    def _get_performance_factor(self) -> float:
        """
        Calculate performance adjustment factor based on win/loss streaks.
        
        After 3 wins -> increase size by 25% (factor = 1.25)
        After 3 losses -> decrease size by 25% (factor = 0.75)
        Otherwise -> no adjustment (factor = 1.0)
        
        Returns:
            Performance factor (0.75 to 1.25)
        """
        if self.current_streak >= self.streak_threshold:
            # Winning streak: increase size
            factor = 1.0 + self.performance_adjustment_pct
            logger.info(f"Winning streak ({self.current_streak}) -> increase size to {factor:.2f}x")
            return factor
        elif self.current_streak <= -self.streak_threshold:
            # Losing streak: decrease size
            factor = 1.0 - self.performance_adjustment_pct
            logger.warning(f"Losing streak ({abs(self.current_streak)}) -> reduce size to {factor:.2f}x")
            return factor
        else:
            # No significant streak
            return 1.0
    
    def _calculate_base_size(self, signal_confidence: float) -> float:
        """
        Calculate base position size using Kelly Criterion approach.
        
        Args:
            signal_confidence: Signal confidence (0.0-1.0)
            
        Returns:
            Base position size in capital units
        """
        # Use simplified Kelly with confidence as win probability
        # Kelly % = (Win% * Win/Loss Ratio - Loss%) / Win/Loss Ratio
        # Simplified: use confidence and assume 2:1 win/loss ratio
        
        win_prob = signal_confidence
        loss_prob = 1 - win_prob
        win_loss_ratio = self.reward_risk_ratio
        
        if win_prob > 0 and win_loss_ratio > 0:
            kelly_pct = (win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
            kelly_pct = max(0, kelly_pct)  # Don't allow negative
        else:
            kelly_pct = 0
        
        # Use fraction of Kelly (e.g., 25% Kelly)
        fractional_kelly = kelly_pct * self.kelly_fraction
        
        # Combine with base risk
        combined_risk = (self.base_risk_pct + fractional_kelly) / 2
        
        # Calculate position size
        base_size = self.current_capital * combined_risk
        
        return base_size
    
    def _build_reasoning(
        self,
        volatility_pct: float,
        volatility_factor: float,
        performance_factor: float,
        size_multiplier: float,
        risk_pct: float
    ) -> str:
        """Build human-readable reasoning for position size."""
        parts = []
        
        # Volatility component
        if volatility_pct > self.volatility_threshold_high:
            parts.append(f"High volatility ({volatility_pct*100:.2f}%) -> reduced to {volatility_factor*100:.0f}%")
        elif volatility_pct < self.volatility_threshold_low:
            parts.append(f"Low volatility ({volatility_pct*100:.2f}%) -> increased to {volatility_factor*100:.0f}%")
        else:
            parts.append(f"Normal volatility ({volatility_pct*100:.2f}%)")
        
        # Performance component
        if self.current_streak >= self.streak_threshold:
            parts.append(f"Winning streak (+{self.current_streak}) -> size +{self.performance_adjustment_pct*100:.0f}%")
        elif self.current_streak <= -self.streak_threshold:
            parts.append(f"Losing streak ({self.current_streak}) -> size -{self.performance_adjustment_pct*100:.0f}%")
        
        # Final multiplier
        parts.append(f"Total multiplier: {size_multiplier:.2f}x, Risk: {risk_pct:.2f}%")
        
        return " | ".join(parts)
    
    def record_trade(self, profit_loss: float, was_win: bool):
        """
        Record trade result and update performance tracking.
        
        Args:
            profit_loss: Profit or loss amount
            was_win: Whether trade was profitable
        """
        # Update capital
        self.current_capital += profit_loss
        
        # Update peak and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        # Update streak
        if was_win:
            self.current_streak = max(1, self.current_streak + 1) if self.current_streak >= 0 else 1
        else:
            self.current_streak = min(-1, self.current_streak - 1) if self.current_streak <= 0 else -1
        
        # Record trade
        self.trade_history.append({
            'profit_loss': profit_loss,
            'was_win': was_win,
            'capital': self.current_capital,
            'streak': self.current_streak,
            'drawdown': drawdown
        })
        
        logger.info(
            f"Trade recorded: {'WIN' if was_win else 'LOSS'} "
            f"P/L: ${profit_loss:.2f}, Capital: ${self.current_capital:.2f}, "
            f"Streak: {self.current_streak}, DD: {drawdown*100:.2f}%"
        )
    
    def reset_on_recovery(self):
        """
        Reset adjustments when recovering from drawdown.
        
        Called when capital recovers to near peak (within 5%).
        """
        if self.current_capital >= self.peak_capital * 0.95:
            old_streak = self.current_streak
            self.current_streak = 0
            logger.info(f"Recovery detected - streak reset from {old_streak} to 0")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'current_capital': self.current_capital,
                'max_drawdown': 0.0,
                'current_streak': 0
            }
        
        wins = sum(1 for t in self.trade_history if t['was_win'])
        total_trades = len(self.trade_history)
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        total_pnl = sum(t['profit_loss'] for t in self.trade_history)
        
        return {
            'total_trades': total_trades,
            'wins': wins,
            'losses': total_trades - wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'max_drawdown': self.max_drawdown,
            'current_streak': self.current_streak,
            'roi': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        }
    
    def adjust_for_drawdown(self) -> float:
        """
        Get additional risk reduction factor based on current drawdown.
        
        Returns:
            Risk reduction factor (0.5 to 1.0)
        """
        current_dd = (self.peak_capital - self.current_capital) / self.peak_capital
        
        if current_dd > 0.20:
            # 20%+ drawdown: reduce to 50%
            return 0.5
        elif current_dd > 0.10:
            # 10-20% drawdown: reduce to 75%
            return 0.75
        else:
            # < 10% drawdown: no reduction
            return 1.0
    
    def get_params(self) -> Dict[str, Any]:
        """Get optimizer parameters."""
        return {
            'base_risk_pct': self.base_risk_pct,
            'atr_period': self.atr_period,
            'kelly_fraction': self.kelly_fraction,
            'max_position_pct': self.max_position_pct,
            'min_position_pct': self.min_position_pct,
            'streak_threshold': self.streak_threshold,
            'performance_adjustment_pct': self.performance_adjustment_pct
        }
