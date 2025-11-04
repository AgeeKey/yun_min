"""
EMA Crossover Strategy V4 - Grok AI Optimized

Enhanced version based on V3 test results and Grok AI recommendations:
- V3 Issue: SHORT 100% WR, LONG 38.7% WR (asymmetric performance)
- V4 Solution: Asymmetric SL/TP ratios + trend filter + optimized RSI

Key Improvements:
1. Asymmetric Risk Management:
   - SHORT positions: Tighter SL (1.5%), standard TP (2%)
   - LONG positions: Wider SL (3%), higher TP (4%)
   
2. Trend Filter (EMA 50):
   - LONG only in uptrend (price > EMA50)
   - SHORT only in downtrend (price < EMA50)
   
3. Optimized RSI Thresholds:
   - More conservative entry zones
   - Reduced choppy market exposure
"""

import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class EMACrossoverV4Strategy(BaseStrategy):
    """
    V4: EMA Crossover with asymmetric risk and trend filter.
    
    Designed to fix V3's LONG underperformance (38.7% WR → target 60%+)
    """
    
    def __init__(
        self,
        fast_period: int = 9,
        slow_period: int = 21,
        trend_period: int = 50,  # NEW: Trend filter
        rsi_period: int = 14,
        rsi_overbought: float = 65.0,  # More conservative (was 70)
        rsi_oversold: float = 35.0,    # More conservative (was 30)
        # Asymmetric SL/TP
        short_sl_pct: float = 1.5,
        short_tp_pct: float = 2.0,
        long_sl_pct: float = 3.0,
        long_tp_pct: float = 4.0,
        trend_filter_enabled: bool = True
    ):
        """
        Initialize V4 strategy with Grok AI optimizations.
        
        Args:
            fast_period: Fast EMA period (9)
            slow_period: Slow EMA period (21)
            trend_period: Trend EMA period (50) - NEW
            rsi_period: RSI period (14)
            rsi_overbought: RSI overbought (65, was 70)
            rsi_oversold: RSI oversold (35, was 30)
            short_sl_pct: SHORT stop loss % (1.5%)
            short_tp_pct: SHORT take profit % (2.0%)
            long_sl_pct: LONG stop loss % (3.0%)
            long_tp_pct: LONG take profit % (4.0%)
            trend_filter_enabled: Enable trend filter (True)
        """
        super().__init__("EMA_Crossover_V4")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trend_period = trend_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        # Asymmetric risk management
        self.short_sl_pct = short_sl_pct
        self.short_tp_pct = short_tp_pct
        self.long_sl_pct = long_sl_pct
        self.long_tp_pct = long_tp_pct
        
        self.trend_filter_enabled = trend_filter_enabled
        
        logger.info(
            f"V4 Strategy initialized: "
            f"EMA({fast_period}/{slow_period}/{trend_period}), "
            f"RSI({rsi_period}): {rsi_oversold}-{rsi_overbought}, "
            f"SHORT SL/TP: {short_sl_pct}%/{short_tp_pct}%, "
            f"LONG SL/TP: {long_sl_pct}%/{long_tp_pct}%, "
            f"Trend Filter: {trend_filter_enabled}"
        )
        
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators including trend filter."""
        df = data.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['ema_trend'] = df['close'].ewm(span=self.trend_period, adjust=False).mean()  # NEW
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Detect crossovers
        df['ema_diff'] = df['ema_fast'] - df['ema_slow']
        df['ema_diff_prev'] = df['ema_diff'].shift(1)
        
        # Trend classification
        df['in_uptrend'] = df['close'] > df['ema_trend']
        df['in_downtrend'] = df['close'] < df['ema_trend']
        
        return df
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data and generate V4 trading signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Trading signal with asymmetric risk parameters
        """
        min_data_length = max(self.slow_period, self.rsi_period, self.trend_period) + 1
        if len(data) < min_data_length:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Insufficient data for V4 analysis (need {min_data_length})"
            )
            
        # Calculate indicators
        df = self._calculate_indicators(data)
        
        # Get latest values
        latest = df.iloc[-1]
        
        ema_fast = latest['ema_fast']
        ema_slow = latest['ema_slow']
        ema_trend = latest['ema_trend']
        ema_diff = latest['ema_diff']
        ema_diff_prev = latest['ema_diff_prev']
        rsi = latest['rsi']
        price = latest['close']
        in_uptrend = latest['in_uptrend']
        in_downtrend = latest['in_downtrend']
        
        # Detect crossover
        bullish_cross = ema_diff > 0 and ema_diff_prev <= 0
        bearish_cross = ema_diff < 0 and ema_diff_prev >= 0
        
        # V4 IMPROVEMENT 1: Trend Filter
        long_allowed = not self.trend_filter_enabled or in_uptrend
        short_allowed = not self.trend_filter_enabled or in_downtrend
        
        # Generate signals with V4 enhancements
        if bullish_cross and rsi < self.rsi_overbought and long_allowed:
            # LONG signal with asymmetric SL/TP
            confidence = min(0.9, (self.rsi_overbought - rsi) / self.rsi_overbought)
            
            return Signal(
                type=SignalType.BUY,
                confidence=confidence,
                reason=(
                    f"V4 LONG: EMA cross + uptrend (Fast: {ema_fast:.2f}, "
                    f"Slow: {ema_slow:.2f}, Trend: {ema_trend:.2f}), RSI: {rsi:.1f}"
                ),
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'in_uptrend': in_uptrend,
                    # V4 IMPROVEMENT 2: Asymmetric risk
                    'stop_loss_pct': self.long_sl_pct,
                    'take_profit_pct': self.long_tp_pct,
                    'stop_loss': price * (1 - self.long_sl_pct / 100),
                    'take_profit': price * (1 + self.long_tp_pct / 100)
                }
            )
            
        elif bearish_cross and rsi > self.rsi_oversold and short_allowed:
            # SHORT signal with tighter SL/TP
            confidence = min(0.9, (rsi - self.rsi_oversold) / (100 - self.rsi_oversold))
            
            return Signal(
                type=SignalType.SELL,
                confidence=confidence,
                reason=(
                    f"V4 SHORT: EMA cross + downtrend (Fast: {ema_fast:.2f}, "
                    f"Slow: {ema_slow:.2f}, Trend: {ema_trend:.2f}), RSI: {rsi:.1f}"
                ),
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'in_downtrend': in_downtrend,
                    # V4 IMPROVEMENT 2: Asymmetric risk
                    'stop_loss_pct': self.short_sl_pct,
                    'take_profit_pct': self.short_tp_pct,
                    'stop_loss': price * (1 + self.short_sl_pct / 100),
                    'take_profit': price * (1 - self.short_tp_pct / 100)
                }
            )
            
        elif bullish_cross and not long_allowed:
            # Filtered LONG (trend not favorable)
            return Signal(
                type=SignalType.HOLD,
                confidence=0.3,
                reason=f"V4 Filter: Bullish cross but not in uptrend (price: {price:.2f} < EMA50: {ema_trend:.2f})",
                metadata={
                    'price': price,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'filtered': True
                }
            )
            
        elif bearish_cross and not short_allowed:
            # Filtered SHORT (trend not favorable)
            return Signal(
                type=SignalType.HOLD,
                confidence=0.3,
                reason=f"V4 Filter: Bearish cross but not in downtrend (price: {price:.2f} > EMA50: {ema_trend:.2f})",
                metadata={
                    'price': price,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'filtered': True
                }
            )
            
        elif rsi >= self.rsi_overbought:
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.7,
                reason=f"V4 Exit: RSI overbought {rsi:.1f} >= {self.rsi_overbought}",
                metadata={'rsi': rsi, 'price': price}
            )
            
        elif rsi <= self.rsi_oversold:
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.7,
                reason=f"V4 Exit: RSI oversold {rsi:.1f} <= {self.rsi_oversold}",
                metadata={'rsi': rsi, 'price': price}
            )
            
        else:
            # No signal - trend continuation
            if in_uptrend:
                trend = "uptrend"
            elif in_downtrend:
                trend = "downtrend"
            else:
                trend = "sideways"
                
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"V4 Hold: No signal. Trend: {trend}, RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'trend': trend
                }
            )
            
    def get_params(self) -> Dict[str, Any]:
        """Get V4 strategy parameters."""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'trend_period': self.trend_period,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'short_sl_pct': self.short_sl_pct,
            'short_tp_pct': self.short_tp_pct,
            'long_sl_pct': self.long_sl_pct,
            'long_tp_pct': self.long_tp_pct,
            'trend_filter_enabled': self.trend_filter_enabled
        }
        
    def set_params(self, params: Dict[str, Any]):
        """Set V4 strategy parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
        logger.info(f"V4 Strategy parameters updated: {params}")
