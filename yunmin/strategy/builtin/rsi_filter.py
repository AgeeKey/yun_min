"""
RSI Filter Strategy

Uses EMA for direction + RSI for confirmation.

Entry:
  - Long: Price above EMA(21) AND RSI(14) < 40 (oversold for trend confirmation)
  - Short: Price below EMA(21) AND RSI(14) > 60 (overbought)

Exit:
  - Long: RSI > 75 (overbought exit) OR price < EMA(21)
  - Short: RSI < 25 (oversold exit) OR price > EMA(21)

Risk management:
  - Fixed position size: 2% of capital per trade
  - Tight stops based on support/resistance
"""

from yunmin.core.strategy_base import StrategyBase
import logging

logger = logging.getLogger(__name__)


class RSIFilter(StrategyBase):
    """
    EMA trend + RSI confirmation strategy.
    
    Parameters:
      - ema_period: EMA for trend (default 21)
      - rsi_period: RSI period (default 14)
      - rsi_oversold: RSI oversold threshold (default 40)
      - rsi_overbought: RSI overbought threshold (default 60)
      - rsi_exit_long: RSI level to exit long (default 75)
      - rsi_exit_short: RSI level to exit short (default 25)
      - risk_pct: Risk per trade (default 0.02)
    """
    
    def __init__(self, timeframe: str = "5m"):
        super().__init__(
            name="RSI Filter",
            timeframe=timeframe,
            ema_period=21,
            rsi_period=14,
            rsi_oversold=40,
            rsi_overbought=60,
            rsi_exit_long=75,
            rsi_exit_short=25,
            risk_pct=0.02
        )
        
    def should_long(self) -> bool:
        """Long: price above EMA AND RSI oversold."""
        if not self.candles or len(self.candles) < self.params["ema_period"]:
            return False
            
        candles = self.candles
        price = candles[-1]["c"]
        ema = self.ema(candles, self.params["ema_period"])
        rsi_vals = self.rsi(candles, self.params["rsi_period"])
        
        if ema[-1] is None or rsi_vals[-1] is None:
            return False
            
        above_ema = price > ema[-1]
        rsi_low = rsi_vals[-1] < self.params["rsi_oversold"]
        
        return above_ema and rsi_low
        
    def should_short(self) -> bool:
        """Short: price below EMA AND RSI overbought."""
        if not self.candles or len(self.candles) < self.params["ema_period"]:
            return False
            
        candles = self.candles
        price = candles[-1]["c"]
        ema = self.ema(candles, self.params["ema_period"])
        rsi_vals = self.rsi(candles, self.params["rsi_period"])
        
        if ema[-1] is None or rsi_vals[-1] is None:
            return False
            
        below_ema = price < ema[-1]
        rsi_high = rsi_vals[-1] > self.params["rsi_overbought"]
        
        return below_ema and rsi_high
        
    def should_exit(self) -> bool:
        """Exit on RSI extreme or trend break."""
        if not self.position or not self.candles:
            return False
            
        candles = self.candles
        price = candles[-1]["c"]
        ema = self.ema(candles, self.params["ema_period"])
        rsi_vals = self.rsi(candles, self.params["rsi_period"])
        
        if ema[-1] is None or rsi_vals[-1] is None:
            return False
            
        if self.position["side"] == "LONG":
            # Exit long on RSI too high OR price below EMA
            rsi_exit = rsi_vals[-1] > self.params["rsi_exit_long"]
            trend_break = price < ema[-1]
            return rsi_exit or trend_break
        else:  # SHORT
            # Exit short on RSI too low OR price above EMA
            rsi_exit = rsi_vals[-1] < self.params["rsi_exit_short"]
            trend_break = price > ema[-1]
            return rsi_exit or trend_break
            
    def go_long(self):
        """Enter long position."""
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
