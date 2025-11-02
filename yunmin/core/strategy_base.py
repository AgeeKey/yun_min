"""
Base strategy class for all trading strategies.

Inspired by Jesse framework (MIT License): jesse/strategies/Strategy.py
Strategies should inherit this class and implement should_long/short/exit and go_long/short/exit.

Data contracts:
  - candles (multi-TF): {ts, o, h, l, c, v, symbol, timeframe}
  - decision: {intent: "BUY"|"SELL"|"EXIT"|"HOLD", confidence: float, size_hint: float}
"""

from typing import Dict, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Strategy decision output."""
    intent: str  # "BUY", "SELL", "EXIT", or "HOLD"
    confidence: float  # 0.0 to 1.0
    size_hint: Optional[float] = None  # Suggested position size as % of capital
    reason: str = ""


class StrategyBase(ABC):
    """
    Base class for trading strategies. Inspired by Jesse.
    
    Subclass must implement:
      - should_long() -> bool: check if conditions exist to go long
      - should_short() -> bool: check if conditions exist to go short
      - should_exit() -> bool: check if conditions exist to exit current position
      - go_long(): execute long entry (set orders, sizing, etc.)
      - go_short(): execute short entry
      - go_exit(): execute exit
    
    Optional:
      - should_cancel_entry() -> bool: cancel pending entry if conditions change
      - on_trade(trade: Dict): called when trade is opened/closed
    
    Example:
        class EMACrossover(StrategyBase):
            def __init__(self, timeframe: str = "5m"):
                super().__init__("EMA Crossover", timeframe=timeframe)
                self.fast_period = 9
                self.slow_period = 21
                
            def should_long(self) -> bool:
                fast_ema = self.ema(self.candles, self.fast_period)
                slow_ema = self.ema(self.candles, self.slow_period)
                return fast_ema[-1] > slow_ema[-1]
                
            def go_long(self):
                qty = self.calculate_qty(self.price, risk_pct=0.02)
                self.place_order("BUY", qty, self.price)
                self.take_profit = self.price * 1.03
                self.stop_loss = self.price * 0.98
    """
    
    def __init__(self, name: str, timeframe: str = "5m", **params):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            timeframe: Default candle timeframe
            **params: Strategy-specific parameters
        """
        self.name = name
        self.timeframe = timeframe
        self.params = params
        
        # State
        self.candles: Dict = {}  # {symbol+tf: [candles]}
        self.position = None  # Current position state
        self.pending_orders = []  # Pending orders
        
    # ============ DECISION METHODS (implement in subclass) ============
    
    @abstractmethod
    def should_long(self) -> bool:
        """
        Check if conditions exist to enter a long position.
        
        Returns:
            True if long entry conditions are met
        """
        raise NotImplementedError
        
    @abstractmethod
    def should_short(self) -> bool:
        """
        Check if conditions exist to enter a short position.
        Futures/margin only.
        
        Returns:
            True if short entry conditions are met
        """
        raise NotImplementedError
        
    @abstractmethod
    def should_exit(self) -> bool:
        """
        Check if conditions exist to exit current position.
        
        Returns:
            True if exit conditions are met
        """
        raise NotImplementedError
        
    def should_cancel_entry(self) -> bool:
        """
        Check if pending entry should be cancelled.
        Default: no cancellation.
        
        Returns:
            True to cancel pending entry
        """
        return False
    
    # ============ ACTION METHODS (implement in subclass) ============
    
    @abstractmethod
    def go_long(self):
        """
        Execute long entry. Examples:
          - self.place_order("BUY", qty=1.0, price=self.price)
          - self.take_profit = self.price * 1.03
          - self.stop_loss = self.price * 0.98
        """
        raise NotImplementedError
        
    @abstractmethod
    def go_short(self):
        """
        Execute short entry (futures only).
        """
        raise NotImplementedError
        
    @abstractmethod
    def go_exit(self):
        """
        Execute exit. Examples:
          - market sell/close position
          - or use limit order for better price
        """
        raise NotImplementedError
    
    # ============ LIFECYCLE HOOKS (optional) ============
    
    def on_trade(self, trade: Dict):
        """Called when trade is opened or closed."""
        pass
        
    def on_order_filled(self, order: Dict):
        """Called when order is partially or fully filled."""
        pass
        
    def on_candle(self, candle: Dict):
        """Called on each new candle."""
        pass
        
    # ============ TECHNICAL INDICATORS (helpers) ============
    
    @staticmethod
    def sma(candles: List[Dict], period: int) -> List[Optional[float]]:
        """
        Simple Moving Average.
        
        Args:
            candles: OHLCV candles
            period: Period
            
        Returns:
            List of SMA values (None for insufficient data)
        """
        closes = [c["close"] for c in candles]
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(closes[i - period + 1:i + 1]) / period)
        return result
        
    @staticmethod
    def ema(candles: List[Dict], period: int) -> List[Optional[float]]:
        """
        Exponential Moving Average (standard formula).
        
        Args:
            candles: OHLCV candles
            period: Period
            
        Returns:
            List of EMA values (None for insufficient data)
        """
        closes = [c["close"] for c in candles]
        multiplier = 2 / (period + 1)
        result = []
        for i in range(len(closes)):
            if i < period - 1:
                result.append(None)
            elif i == period - 1:
                result.append(sum(closes[0:period]) / period)
            else:
                result.append((closes[i] * multiplier) + (result[i - 1] * (1 - multiplier)))
        return result
        
    @staticmethod
    def rsi(candles: List[Dict], period: int = 14) -> List[Optional[float]]:
        """
        Relative Strength Index.
        
        Args:
            candles: OHLCV candles
            period: Period (default 14)
            
        Returns:
            List of RSI values (None for insufficient data)
        """
        closes = [c["close"] for c in candles]
        result = []
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        
        gains = [max(d, 0) for d in deltas]
        losses = [abs(min(d, 0)) for d in deltas]
        
        for i in range(len(closes)):
            if i < period:
                result.append(None)
            else:
                avg_gain = sum(gains[i - period:i]) / period
                avg_loss = sum(losses[i - period:i]) / period
                rs = avg_gain / avg_loss if avg_loss != 0 else 0
                rsi_value = 100 - (100 / (1 + rs))
                result.append(rsi_value)
        return result
        
    @staticmethod
    def crossover(fast: List[Optional[float]], slow: List[Optional[float]]) -> bool:
        """
        Check if fast line just crossed above slow line.
        
        Args:
            fast: Fast line values
            slow: Slow line values
            
        Returns:
            True if crossover detected in last 2 candles
        """
        if len(fast) < 2 or len(slow) < 2:
            return False
        if fast[-2] is None or fast[-1] is None or slow[-2] is None or slow[-1] is None:
            return False
        return fast[-2] <= slow[-2] and fast[-1] > slow[-1]
        
    @staticmethod
    def crossunder(fast: List[Optional[float]], slow: List[Optional[float]]) -> bool:
        """
        Check if fast line just crossed below slow line.
        
        Args:
            fast: Fast line values
            slow: Slow line values
            
        Returns:
            True if crossunder detected in last 2 candles
        """
        if len(fast) < 2 or len(slow) < 2:
            return False
        if fast[-2] is None or fast[-1] is None or slow[-2] is None or slow[-1] is None:
            return False
        return fast[-2] >= slow[-2] and fast[-1] < slow[-1]
