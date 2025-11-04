"""
EMA Crossover V3.1 - AI Optimized Strategy

Улучшения на основе Groq AI анализа реальных данных:
1. Fast EMA: 9 → 12 (меньше ложных сигналов)
2. RSI Overbought: 70 → 65 (больше LONG сигналов)
3. Добавлен TREND FILTER (EMA 50) - торговать только по тренду
4. Уменьшен Stop Loss: 2% → 1.5% (меньше потери)

AI Оценка оригинальной V3: 2/10 баллов (-21.54% return, 14.61% win rate)
Цель V3.1: Win Rate > 40%, Positive Return
"""

import pandas as pd
from typing import Dict, Any
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class EMACrossoverV31Strategy(BaseStrategy):
    """
    AI-Optimized EMA Crossover with Trend Filter.
    
    Ключевые улучшения:
    - Более медленная Fast EMA (12 vs 9) → меньше шума
    - Более агрессивный RSI порог (65 vs 70) → больше LONG входов
    - Trend filter (EMA50) → торговать только по тренду
    - Уменьшенный SL (1.5% vs 2%) → быстрый выход из убыточных позиций
    """
    
    def __init__(
        self,
        fast_period: int = 12,       # AI: было 9
        slow_period: int = 21,
        trend_period: int = 50,      # AI: новый параметр
        rsi_period: int = 14,
        rsi_overbought: float = 65.0,  # AI: было 70
        rsi_oversold: float = 30.0
    ):
        """
        Initialize AI-optimized EMA crossover strategy.
        
        Args:
            fast_period: Fast EMA period (12 - AI optimized)
            slow_period: Slow EMA period
            trend_period: Trend filter EMA period (50)
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold (65 - AI optimized)
            rsi_oversold: RSI oversold threshold
        """
        super().__init__("EMA_Crossover_V31_AI")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trend_period = trend_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        logger.info(
            f"EMA Crossover V3.1 (AI-Optimized) initialized: "
            f"fast={fast_period}, slow={slow_period}, trend={trend_period}, "
            f"RSI({rsi_period}): {rsi_oversold}-{rsi_overbought}"
        )
        
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = data.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['ema_trend'] = df['close'].ewm(span=self.trend_period, adjust=False).mean()  # AI: trend filter
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Detect crossovers
        df['ema_diff'] = df['ema_fast'] - df['ema_slow']
        df['ema_diff_prev'] = df['ema_diff'].shift(1)
        
        # Determine trend
        df['is_uptrend'] = df['close'] > df['ema_trend']
        df['is_downtrend'] = df['close'] < df['ema_trend']
        
        return df
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Trading signal
        """
        min_required = max(self.trend_period, self.slow_period, self.rsi_period) + 1
        if len(data) < min_required:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for analysis"
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
        is_uptrend = latest['is_uptrend']
        is_downtrend = latest['is_downtrend']
        
        # Detect crossover
        bullish_cross = ema_diff > 0 and ema_diff_prev <= 0
        bearish_cross = ema_diff < 0 and ema_diff_prev >= 0
        
        # AI IMPROVEMENT: Только по тренду!
        # LONG только в uptrend, SHORT только в downtrend
        
        if bullish_cross and rsi < self.rsi_overbought and is_uptrend:
            # BUY signal - с подтверждением тренда
            confidence = min(0.95, (self.rsi_overbought - rsi) / self.rsi_overbought + 0.2)
            return Signal(
                type=SignalType.BUY,
                confidence=confidence,
                reason=f"✅ Bullish EMA cross + UPTREND (EMA{self.trend_period}), RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'trend': 'UP'
                }
            )
        elif bearish_cross and rsi > self.rsi_oversold and is_downtrend:
            # SELL signal - с подтверждением тренда
            confidence = min(0.95, (rsi - self.rsi_oversold) / (100 - self.rsi_oversold) + 0.2)
            return Signal(
                type=SignalType.SELL,
                confidence=confidence,
                reason=f"✅ Bearish EMA cross + DOWNTREND (EMA{self.trend_period}), RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'trend': 'DOWN'
                }
            )
        elif bullish_cross and not is_uptrend:
            # Кросс есть, но тренд не подтверждает - пропускаем
            return Signal(
                type=SignalType.HOLD,
                confidence=0.3,
                reason=f"⚠️ Bullish cross but NO uptrend (price {price:.2f} < EMA50 {ema_trend:.2f})",
                metadata={'price': price, 'ema_trend': ema_trend}
            )
        elif bearish_cross and not is_downtrend:
            # Кросс есть, но тренд не подтверждает - пропускаем
            return Signal(
                type=SignalType.HOLD,
                confidence=0.3,
                reason=f"⚠️ Bearish cross but NO downtrend (price {price:.2f} > EMA50 {ema_trend:.2f})",
                metadata={'price': price, 'ema_trend': ema_trend}
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
            # No signal
            trend_desc = "UPTREND" if is_uptrend else ("DOWNTREND" if is_downtrend else "NEUTRAL")
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"No signal. Trend: {trend_desc}, RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'ema_trend': ema_trend,
                    'rsi': rsi,
                    'price': price,
                    'trend': trend_desc
                }
            )
            
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'trend_period': self.trend_period,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold
        }
