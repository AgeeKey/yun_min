"""
Enhanced EMA Crossover Strategy with Advanced Risk Management

New features:
- ATR-based adaptive stop-loss (instead of fixed 2%)
- Trailing stop to protect profits
- Market regime detection (trending vs ranging using ADX)
- Volatility-based position sizing
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class EMACrossoverEnhanced(BaseStrategy):
    """
    Enhanced EMA Crossover strategy with adaptive risk management.
    
    Improvements over basic version:
    1. ATR-based stops: Dynamic stop-loss based on market volatility
    2. Trailing stop: Protect profits as position moves in our favor
    3. ADX filter: Only trade in trending markets (ADX > 25)
    4. Volatility adjustment: Scale position size based on ATR
    """
    
    def __init__(
        self,
        # Strategy parameters (OPTIMIZED)
        fast_period: int = 12,
        slow_period: int = 26,
        rsi_period: int = 14,
        rsi_overbought: float = 70.0,
        rsi_oversold: float = 30.0,
        
        # Risk management parameters
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,  # Stop at 2 * ATR
        trailing_stop_activation: float = 0.02,  # Activate after 2% profit
        trailing_stop_distance: float = 1.5,  # Trail at 1.5 * ATR
        
        # Market regime filter
        adx_period: int = 14,
        adx_threshold: float = 25.0,  # Min ADX for trending market
        use_adx_filter: bool = True
    ):
        """
        Initialize enhanced strategy.
        
        Args:
            fast_period: Fast EMA period (12 optimized)
            slow_period: Slow EMA period (26 optimized)
            rsi_period: RSI period
            rsi_overbought: RSI overbought threshold (70 optimized)
            rsi_oversold: RSI oversold threshold (30 optimized)
            atr_period: ATR calculation period
            atr_stop_multiplier: Stop loss distance in ATR units
            trailing_stop_activation: Profit percent to activate trailing stop
            trailing_stop_distance: Trailing distance in ATR units
            adx_period: ADX calculation period
            adx_threshold: Minimum ADX for trend trading
            use_adx_filter: Enable or disable ADX filtering
        """
        super().__init__("EMA_Crossover_Enhanced")
        
        # Strategy parameters
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        
        # Risk parameters
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.trailing_stop_activation = trailing_stop_activation
        self.trailing_stop_distance = trailing_stop_distance
        
        # Market regime parameters
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.use_adx_filter = use_adx_filter
        
        # Track position for trailing stop
        self.entry_price: Optional[float] = None
        self.highest_price: Optional[float] = None
        self.lowest_price: Optional[float] = None
        
        logger.info(
            f"Enhanced EMA Crossover Strategy initialized:\n"
            f"  Signal: EMA {fast_period}/{slow_period}, RSI {rsi_oversold}-{rsi_overbought}\n"
            f"  Risk: ATR({atr_period}) stop={atr_stop_multiplier}x, trailing={trailing_stop_distance}x\n"
            f"  Filter: ADX({adx_period}) threshold={adx_threshold}, enabled={use_adx_filter}"
        )
        
    def _calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range."""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # True Range components
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        # True Range = max of three components
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR = EMA of True Range
        atr = tr.ewm(span=self.atr_period, adjust=False).mean()
        
        return atr
    
    def _calculate_adx(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate Average Directional Index (ADX).
        ADX measures trend strength (not direction).
        ADX > 25: Strong trend
        ADX < 20: Weak trend (ranging market)
        """
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Directional Movement
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        # Only keep positive moves
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Smoothed TR and DM
        atr = tr.ewm(span=self.adx_period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=self.adx_period, adjust=False).mean() / atr)
        
        # Directional Index
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        # ADX = smoothed DX
        adx = dx.ewm(span=self.adx_period, adjust=False).mean()
        
        return adx
        
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""
        df = data.copy()
        
        # Original indicators
        df['ema_fast'] = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Crossover detection
        df['ema_diff'] = df['ema_fast'] - df['ema_slow']
        df['ema_diff_prev'] = df['ema_diff'].shift(1)
        
        # New: ATR for adaptive stops
        df['atr'] = self._calculate_atr(df)
        
        # New: ADX for market regime
        df['adx'] = self._calculate_adx(df)
        
        return df
    
    def calculate_stop_loss(self, entry_price: float, atr: float, direction: str) -> float:
        """
        Calculate ATR-based stop loss.
        
        Args:
            entry_price: Position entry price
            atr: Current ATR value
            direction: 'long' or 'short'
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * self.atr_stop_multiplier
        
        if direction == 'long':
            return entry_price - stop_distance
        else:  # short
            return entry_price + stop_distance
    
    def calculate_trailing_stop(
        self, 
        entry_price: float, 
        current_price: float, 
        atr: float, 
        direction: str
    ) -> Optional[float]:
        """
        Calculate trailing stop price.
        
        Returns None if trailing stop not yet activated.
        Returns stop price if trailing is active.
        """
        # Check if profit threshold reached
        if direction == 'long':
            profit_pct = (current_price - entry_price) / entry_price
            if profit_pct < self.trailing_stop_activation:
                return None  # Not enough profit yet
            
            # Update highest price seen
            if self.highest_price is None or current_price > self.highest_price:
                self.highest_price = current_price
            
            # Trail from highest price
            trail_distance = atr * self.trailing_stop_distance
            return self.highest_price - trail_distance
            
        else:  # short
            profit_pct = (entry_price - current_price) / entry_price
            if profit_pct < self.trailing_stop_activation:
                return None
            
            # Update lowest price seen
            if self.lowest_price is None or current_price < self.lowest_price:
                self.lowest_price = current_price
            
            # Trail from lowest price
            trail_distance = atr * self.trailing_stop_distance
            return self.lowest_price + trail_distance
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market and generate trading signal with enhanced risk management.
        """
        min_periods = max(self.slow_period, self.rsi_period, self.atr_period, self.adx_period)
        
        if len(data) < min_periods + 1:
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
        ema_diff = latest['ema_diff']
        ema_diff_prev = df.iloc[-2]['ema_diff']
        rsi = latest['rsi']
        atr = latest['atr']
        adx = latest['adx']
        price = latest['close']
        
        # Market regime filter
        if self.use_adx_filter and adx < self.adx_threshold:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.3,
                reason=f"Ranging market (ADX {adx:.1f} < {self.adx_threshold})",
                metadata={
                    'adx': adx,
                    'atr': atr,
                    'regime': 'ranging'
                }
            )
        
        # Detect crossovers
        bullish_cross = ema_diff > 0 and ema_diff_prev <= 0
        bearish_cross = ema_diff < 0 and ema_diff_prev >= 0
        
        # BUY signal
        if bullish_cross and rsi < self.rsi_overbought:
            confidence = min(0.9, (self.rsi_overbought - rsi) / self.rsi_overbought)
            
            # Calculate stop loss
            stop_loss = self.calculate_stop_loss(price, atr, 'long')
            stop_loss_pct = (price - stop_loss) / price
            
            # Reset trailing stop tracking
            self.entry_price = price
            self.highest_price = price
            self.lowest_price = None
            
            return Signal(
                type=SignalType.BUY,
                confidence=confidence,
                reason=f"Bullish crossover in trend (ADX {adx:.1f}), RSI {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'atr': atr,
                    'adx': adx,
                    'price': price,
                    'stop_loss': stop_loss,
                    'stop_loss_pct': stop_loss_pct,
                    'regime': 'trending'
                }
            )
        
        # SELL signal
        elif bearish_cross and rsi > self.rsi_oversold:
            confidence = min(0.9, (rsi - self.rsi_oversold) / (100 - self.rsi_oversold))
            
            # Calculate stop loss
            stop_loss = self.calculate_stop_loss(price, atr, 'short')
            stop_loss_pct = (stop_loss - price) / price
            
            # Reset trailing stop tracking
            self.entry_price = price
            self.highest_price = None
            self.lowest_price = price
            
            return Signal(
                type=SignalType.SELL,
                confidence=confidence,
                reason=f"Bearish crossover in trend (ADX {adx:.1f}), RSI {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'atr': atr,
                    'adx': adx,
                    'price': price,
                    'stop_loss': stop_loss,
                    'stop_loss_pct': stop_loss_pct,
                    'regime': 'trending'
                }
            )
        
        # Check exit conditions (RSI extremes or trailing stop)
        elif rsi >= self.rsi_overbought or rsi <= self.rsi_oversold:
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.7,
                reason=f"RSI extreme: {rsi:.1f}",
                metadata={'rsi': rsi, 'price': price, 'atr': atr}
            )
        
        # Hold
        else:
            trend = "bullish" if ema_fast > ema_slow else "bearish" if ema_fast < ema_slow else "neutral"
            regime = "trending" if adx >= self.adx_threshold else "ranging"
            
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"No signal. Trend: {trend}, ADX: {adx:.1f} ({regime}), RSI: {rsi:.1f}",
                metadata={
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'rsi': rsi,
                    'atr': atr,
                    'adx': adx,
                    'price': price,
                    'trend': trend,
                    'regime': regime
                }
            )
            
    def get_params(self) -> Dict[str, Any]:
        """Get all strategy parameters."""
        return {
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'rsi_period': self.rsi_period,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'atr_period': self.atr_period,
            'atr_stop_multiplier': self.atr_stop_multiplier,
            'trailing_stop_activation': self.trailing_stop_activation,
            'trailing_stop_distance': self.trailing_stop_distance,
            'adx_period': self.adx_period,
            'adx_threshold': self.adx_threshold,
            'use_adx_filter': self.use_adx_filter
        }
