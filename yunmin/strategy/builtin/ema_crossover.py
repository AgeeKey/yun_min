"""
EMA Crossover Strategy

Entry:
  - Long: Fast EMA (9) crosses above Slow EMA (21)
  - Short: Fast EMA crosses below Slow EMA

Exit:
  - Exit opposite side crossover
  - Or take profit / stop loss hit

Risk management:
  - Fixed position size: 2% of capital per trade
  - Stop loss: 2% below entry
  - Take profit: 3% above entry
"""

from yunmin.core.strategy_base import StrategyBase
import logging

logger = logging.getLogger(__name__)


class EMACrossover(StrategyBase):
    """
    Simple EMA crossover strategy.
    
    Parameters:
      - fast_period: Fast EMA period (default 9)
      - slow_period: Slow EMA period (default 21)
      - risk_pct: Risk per trade as % of capital (default 0.02)
      - tp_pct: Take profit % above entry (default 0.03)
      - sl_pct: Stop loss % below entry (default 0.02)
    """
    
    def __init__(self, timeframe: str = "5m"):
        super().__init__(
            name="EMA Crossover",
            timeframe=timeframe,
            fast_period=9,
            slow_period=21,
            risk_pct=0.02,
            tp_pct=0.03,
            sl_pct=0.02
        )
        
    def should_long(self) -> bool:
        """Long when fast EMA crosses above slow EMA."""
        if not self.candles or len(self.candles) < self.params["slow_period"]:
            return False
            
        candles = self.candles
        fast_ema = self.ema(candles, self.params["fast_period"])
        slow_ema = self.ema(candles, self.params["slow_period"])
        
        # Crossover: fast above slow
        return self.crossover(fast_ema, slow_ema)
        
    def should_short(self) -> bool:
        """Short when fast EMA crosses below slow EMA."""
        if not self.candles or len(self.candles) < self.params["slow_period"]:
            return False
            
        candles = self.candles
        fast_ema = self.ema(candles, self.params["fast_period"])
        slow_ema = self.ema(candles, self.params["slow_period"])
        
        # Crossunder: fast below slow
        return self.crossunder(fast_ema, slow_ema)
        
    def should_exit(self) -> bool:
        """Exit on opposite EMA crossover."""
        if not self.position:
            return False
            
        if not self.candles or len(self.candles) < self.params["slow_period"]:
            return False
            
        candles = self.candles
        fast_ema = self.ema(candles, self.params["fast_period"])
        slow_ema = self.ema(candles, self.params["slow_period"])
        
        if self.position["side"] == "LONG":
            # Exit long on crossunder
            return self.crossunder(fast_ema, slow_ema)
        else:  # SHORT
            # Exit short on crossover
            return self.crossover(fast_ema, slow_ema)
            
    def go_long(self):
        """
        Enter long position.
        
        Sets:
          - Order: market buy at current price
          - Take profit: 3% above entry
          - Stop loss: 2% below entry
        """
        # TODO: Integrate with execution engine
        logger.debug(f"{self.name}: Going long at {self.candles[-1]['c']}")
        
    def go_short(self):
        """Enter short position."""
        # TODO: Integrate with execution engine
        logger.debug(f"{self.name}: Going short at {self.candles[-1]['c']}")
        
    def go_exit(self):
        """Exit current position."""
        # TODO: Integrate with execution engine
        logger.debug(f"{self.name}: Exiting {self.position['side']} at {self.candles[-1]['c']}")
