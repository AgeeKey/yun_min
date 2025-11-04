"""
RSI Mean Reversion Strategy

BOSS DECISION: Switching from failed EMA Crossover to Mean Reversion
Why: EMA failed with -21.54%, Mean Reversion works better in choppy markets

Strategy Logic:
- BUY when RSI < 30 (oversold, price likely to bounce)
- SELL when RSI > 70 (overbought, price likely to drop)
- Exit at RSI 50 (neutral zone)

Expected Win Rate: 60-70%
"""

import pandas as pd
from typing import Dict, Any
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI Mean Reversion - купить дешево, продать дорого.
    
    Entry signals:
    - BUY: RSI drops below oversold (30) → price oversold, ready to bounce
    - SELL: RSI rises above overbought (70) → price overbought, ready to drop
    
    Exit signals:
    - Close position when RSI returns to 50 (mean)
    - Or opposite signal triggers
    """
    
    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        rsi_neutral: float = 50.0,
        bb_period: int = 20,          # Bollinger Bands for confirmation
        bb_std: float = 2.0
    ):
        """
        Initialize RSI Mean Reversion strategy.
        
        Args:
            rsi_period: RSI calculation period
            rsi_oversold: RSI oversold threshold (buy zone)
            rsi_overbought: RSI overbought threshold (sell zone)
            rsi_neutral: RSI neutral level (exit zone)
            bb_period: Bollinger Bands period
            bb_std: Bollinger Bands standard deviations
        """
        super().__init__("RSI_Mean_Reversion")
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.rsi_neutral = rsi_neutral
        self.bb_period = bb_period
        self.bb_std = bb_std
        
        logger.info(
            f"RSI Mean Reversion Strategy initialized: "
            f"RSI({rsi_period}): oversold={rsi_oversold}, overbought={rsi_overbought}, "
            f"BB({bb_period}, {bb_std}σ)"
        )
        
    def _calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = data.copy()
        
        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate Bollinger Bands (confirmation)
        df['bb_mid'] = df['close'].rolling(window=self.bb_period).mean()
        df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * self.bb_std)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * self.bb_std)
        
        # Price position relative to BB
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        return df
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data and generate trading signal.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Trading signal
        """
        min_required = max(self.rsi_period, self.bb_period) + 1
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
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        rsi = latest['rsi']
        rsi_prev = prev['rsi']
        price = latest['close']
        bb_lower = latest['bb_lower']
        bb_upper = latest['bb_upper']
        bb_position = latest['bb_position']
        
        # MEAN REVERSION LOGIC
        
        # BUY Signal: RSI oversold + price near lower BB
        if rsi < self.rsi_oversold and bb_position < 0.3:
            # Strong oversold condition with BB confirmation
            confidence = 0.9 if rsi < 25 else 0.7
            return Signal(
                type=SignalType.BUY,
                confidence=confidence,
                reason=f"🔵 OVERSOLD: RSI {rsi:.1f} < {self.rsi_oversold}, BB position {bb_position:.2%}",
                metadata={
                    'rsi': rsi,
                    'price': price,
                    'bb_lower': bb_lower,
                    'bb_position': bb_position,
                    'strategy': 'mean_reversion_buy'
                }
            )
        
        # SELL Signal: RSI overbought + price near upper BB
        elif rsi > self.rsi_overbought and bb_position > 0.7:
            # Strong overbought condition with BB confirmation
            confidence = 0.9 if rsi > 75 else 0.7
            return Signal(
                type=SignalType.SELL,
                confidence=confidence,
                reason=f"🔴 OVERBOUGHT: RSI {rsi:.1f} > {self.rsi_overbought}, BB position {bb_position:.2%}",
                metadata={
                    'rsi': rsi,
                    'price': price,
                    'bb_upper': bb_upper,
                    'bb_position': bb_position,
                    'strategy': 'mean_reversion_sell'
                }
            )
        
        # EXIT Signal: RSI returns to neutral (mean reversion complete)
        elif abs(rsi - self.rsi_neutral) < 5:
            # Price returned to mean
            return Signal(
                type=SignalType.CLOSE,
                confidence=0.8,
                reason=f"🟢 MEAN REVERSION: RSI {rsi:.1f} ≈ {self.rsi_neutral} (neutral)",
                metadata={
                    'rsi': rsi,
                    'price': price,
                    'strategy': 'mean_reversion_exit'
                }
            )
        
        # HOLD: Wait for extreme conditions
        else:
            trend = "neutral"
            if rsi > 55:
                trend = "bullish bias"
            elif rsi < 45:
                trend = "bearish bias"
                
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"⏸ WAITING: RSI {rsi:.1f}, {trend}, BB pos {bb_position:.2%}",
                metadata={
                    'rsi': rsi,
                    'price': price,
                    'bb_position': bb_position,
                    'trend': trend
                }
            )
            
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'rsi_neutral': self.rsi_neutral,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std
        }
