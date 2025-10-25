"""
EMA Crossover Strategy

Simple but effective strategy based on Exponential Moving Average crossovers.
- BUY when fast EMA crosses above slow EMA
- SELL when fast EMA crosses below slow EMA
- Additional filters using RSI to avoid overbought/oversold conditions
"""

import pandas as pd
from typing import Dict, Any
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover with RSI filter strategy.
    
    Entry signals:
    - BUY: Fast EMA crosses above slow EMA and RSI < overbought
    - SELL: Fast EMA crosses below slow EMA and RSI > oversold
    
    Exit signals:
    - Opposite crossover or RSI extremes
    """
    
    def __init__(
        self,
        fast_period: int = 9,
        slow_period: int = 21,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0
    ):
        """
        Initialize EMA crossover strategy.
        
        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold
            rsi_oversold: RSI oversold threshold
        """
        super().__init__("EMA_Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        logger.info(
            f"EMA Crossover Strategy initialized: "
            f"fast={fast_period}, slow={slow_period}, "
            f"RSI({rsi_period}): {rsi_oversold}-{rsi_overbought}"
        )
        
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = data.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Detect crossovers
        df['ema_diff'] = df['ema_fast'] - df['ema_slow']
        df['ema_diff_prev'] = df['ema_diff'].shift(1)
        
        return df
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Trading signal
        """
        if len(data) < max(self.slow_period, self.rsi_period) + 1:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for analysis"
            )
            
        # Calculate indicators
        df = self._calculate_indicators(data)
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        ema_fast = latest['ema_fast']
        ema_slow = latest['ema_slow']
        ema_diff = latest['ema_diff']
        ema_diff_prev = latest['ema_diff_prev']
        rsi = latest['rsi']
        price = latest['close']
        
        # Detect crossover
        bullish_cross = ema_diff > 0 and ema_diff_prev <= 0
        bearish_cross = ema_diff < 0 and ema_diff_prev >= 0
        
        # Generate signals
        if bullish_cross and rsi < self.rsi_overbought:
            confidence = min(0.9, (self.rsi_overbought - rsi) / self.rsi_overbought)
            return Signal(
                type=SignalType.BUY,
                confidence=confidence,
                reason=f"Bullish EMA crossover (Fast: {ema_fast:.2f}, Slow: {ema_slow:.2f}), RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'price': price
                }
            )
        elif bearish_cross and rsi > self.rsi_oversold:
            confidence = min(0.9, (rsi - self.rsi_oversold) / (100 - self.rsi_oversold))
            return Signal(
                type=SignalType.SELL,
                confidence=confidence,
                reason=f"Bearish EMA crossover (Fast: {ema_fast:.2f}, Slow: {ema_slow:.2f}), RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'price': price
                }
            )
        elif rsi >= self.rsi_overbought:
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.7,
                reason=f"RSI overbought: {rsi:.1f} >= {self.rsi_overbought}",
                metadata={'rsi': rsi, 'price': price}
            )
        elif rsi <= self.rsi_oversold:
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.7,
                reason=f"RSI oversold: {rsi:.1f} <= {self.rsi_oversold}",
                metadata={'rsi': rsi, 'price': price}
            )
        else:
            # Trend continuation
            if ema_fast > ema_slow:
                trend = "bullish"
            elif ema_fast < ema_slow:
                trend = "bearish"
            else:
                trend = "neutral"
                
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"No clear signal. Trend: {trend}, RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'price': price,
                    'trend': trend
                }
            )
            
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold
        }
        
    def set_params(self, params: Dict[str, Any]):
        """Set strategy parameters."""
        if 'fast_period' in params:
            self.fast_period = params['fast_period']
        if 'slow_period' in params:
            self.slow_period = params['slow_period']
        if 'rsi_period' in params:
            self.rsi_period = params['rsi_period']
        if 'rsi_overbought' in params:
            self.rsi_overbought = params['rsi_overbought']
        if 'rsi_oversold' in params:
            self.rsi_oversold = params['rsi_oversold']
            
        logger.info(f"Strategy parameters updated: {params}")
