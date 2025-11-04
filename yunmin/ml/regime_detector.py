"""
Market Regime Detection

Automatically detects market regime (trending, ranging, volatile) and provides
adaptive strategy recommendations.
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class MarketRegime(Enum):
    """Market regime types."""
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class TrendDirection(Enum):
    """Trend direction."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"


@dataclass
class RegimeAnalysis:
    """Market regime analysis result."""
    regime: MarketRegime
    trend_direction: TrendDirection
    trend_strength: float  # ADX value
    volatility: float  # BB width percentage
    confidence: float  # 0.0-1.0
    reasoning: str
    metrics: Dict[str, Any]
    position_sizing_recommendation: float  # Multiplier 0.25-1.0


class RegimeDetector:
    """
    Market regime detector using technical indicators.
    
    Features:
    - ADX (Average Directional Index) for trend strength
    - Bollinger Band width for volatility measurement
    - Price action pattern detection (HH/HL, LH/LL)
    - Regime classification with confidence scores
    - Trading recommendations based on regime
    """
    
    def __init__(
        self,
        adx_period: int = 14,
        adx_trending_threshold: float = 25.0,
        adx_ranging_threshold: float = 20.0,
        bb_period: int = 20,
        bb_std: float = 2.0,
        bb_volatility_threshold: float = 0.04,
        pattern_lookback: int = 10
    ):
        """
        Initialize regime detector.
        
        Args:
            adx_period: Period for ADX calculation
            adx_trending_threshold: ADX above this = trending (default 25)
            adx_ranging_threshold: ADX below this = ranging (default 20)
            bb_period: Period for Bollinger Bands
            bb_std: Standard deviations for Bollinger Bands
            bb_volatility_threshold: BB width % threshold for high volatility
            pattern_lookback: Candles to look back for pattern detection
        """
        self.adx_period = adx_period
        self.adx_trending_threshold = adx_trending_threshold
        self.adx_ranging_threshold = adx_ranging_threshold
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.bb_volatility_threshold = bb_volatility_threshold
        self.pattern_lookback = pattern_lookback
        
        logger.info(
            f"Regime Detector initialized: "
            f"ADX trending>{adx_trending_threshold}, "
            f"ranging<{adx_ranging_threshold}, "
            f"BB volatility>{bb_volatility_threshold*100:.1f}%"
        )
    
    def detect_regime(self, df: pd.DataFrame) -> RegimeAnalysis:
        """
        Detect current market regime.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            RegimeAnalysis with detected regime and recommendations
        """
        if df.empty or len(df) < max(self.adx_period, self.bb_period) + 1:
            return RegimeAnalysis(
                regime=MarketRegime.UNKNOWN,
                trend_direction=TrendDirection.SIDEWAYS,
                trend_strength=0.0,
                volatility=0.0,
                confidence=0.0,
                reasoning="Insufficient data for regime detection",
                metrics={},
                position_sizing_recommendation=0.5
            )
        
        # Calculate indicators
        adx_value = self._calculate_adx(df)
        bb_width = self._calculate_bb_width(df)
        trend_direction = self._detect_trend_direction(df)
        pattern_score = self._detect_price_patterns(df)
        
        # Classify regime
        regime, confidence = self._classify_regime(adx_value, bb_width, pattern_score)
        
        # Get position sizing recommendation
        position_multiplier = self._get_position_recommendation(regime, adx_value, bb_width)
        
        # Build reasoning
        reasoning = self._build_reasoning(regime, adx_value, bb_width, trend_direction, pattern_score)
        
        return RegimeAnalysis(
            regime=regime,
            trend_direction=trend_direction,
            trend_strength=adx_value,
            volatility=bb_width,
            confidence=confidence,
            reasoning=reasoning,
            metrics={
                'adx': adx_value,
                'bb_width': bb_width,
                'pattern_score': pattern_score,
                'trend': trend_direction.value
            },
            position_sizing_recommendation=position_multiplier
        )
    
    def _calculate_adx(self, df: pd.DataFrame) -> float:
        """
        Calculate Average Directional Index (ADX).
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            ADX value (0-100)
        """
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Calculate True Range
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate +DM and -DM
        high_diff = np.diff(high, prepend=high[0])
        low_diff = -np.diff(low, prepend=low[0])
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        # Smooth TR, +DM, -DM
        atr = pd.Series(tr).rolling(window=self.adx_period).mean()
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=self.adx_period).mean() / atr)
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=self.adx_period).mean() / atr)
        
        # Calculate DX and ADX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=self.adx_period).mean()
        
        return adx.iloc[-1]
    
    def _calculate_bb_width(self, df: pd.DataFrame) -> float:
        """
        Calculate Bollinger Band width as percentage.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            BB width as percentage
        """
        close = df['close']
        
        # Calculate Bollinger Bands
        sma = close.rolling(window=self.bb_period).mean()
        std = close.rolling(window=self.bb_period).std()
        
        upper_band = sma + (self.bb_std * std)
        lower_band = sma - (self.bb_std * std)
        
        # BB width as percentage of price
        bb_width = ((upper_band - lower_band) / sma).iloc[-1]
        
        return bb_width
    
    def _detect_trend_direction(self, df: pd.DataFrame) -> TrendDirection:
        """
        Detect trend direction using price action.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Trend direction
        """
        # Use last N candles for pattern detection
        lookback = min(self.pattern_lookback, len(df))
        recent_df = df.tail(lookback)
        
        highs = recent_df['high'].values
        lows = recent_df['low'].values
        
        # Count higher highs and higher lows (bullish)
        higher_highs = sum(highs[i] > highs[i-1] for i in range(1, len(highs)))
        higher_lows = sum(lows[i] > lows[i-1] for i in range(1, len(lows)))
        
        # Count lower highs and lower lows (bearish)
        lower_highs = sum(highs[i] < highs[i-1] for i in range(1, len(highs)))
        lower_lows = sum(lows[i] < lows[i-1] for i in range(1, len(lows)))
        
        bullish_score = higher_highs + higher_lows
        bearish_score = lower_highs + lower_lows
        
        if bullish_score > bearish_score * 1.5:
            return TrendDirection.BULLISH
        elif bearish_score > bullish_score * 1.5:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.SIDEWAYS
    
    def _detect_price_patterns(self, df: pd.DataFrame) -> float:
        """
        Detect price action patterns and return pattern strength score.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Pattern score (-1.0 to 1.0, negative=bearish, positive=bullish)
        """
        lookback = min(self.pattern_lookback, len(df))
        recent_df = df.tail(lookback)
        
        closes = recent_df['close'].values
        
        # Calculate momentum
        momentum = (closes[-1] - closes[0]) / closes[0]
        
        # Calculate consistency (lower std = more consistent trend)
        returns = np.diff(closes) / closes[:-1]
        consistency = 1 - min(np.std(returns), 1.0)
        
        # Combine momentum and consistency
        pattern_score = momentum * 10 * consistency
        
        # Clamp to -1.0 to 1.0
        pattern_score = max(-1.0, min(1.0, pattern_score))
        
        return pattern_score
    
    def _classify_regime(
        self, 
        adx: float, 
        bb_width: float, 
        pattern_score: float
    ) -> Tuple[MarketRegime, float]:
        """
        Classify market regime based on indicators.
        
        Args:
            adx: ADX value
            bb_width: Bollinger Band width
            pattern_score: Price pattern score
            
        Returns:
            Tuple of (regime, confidence)
        """
        # High volatility takes precedence
        if bb_width > self.bb_volatility_threshold:
            confidence = min((bb_width / self.bb_volatility_threshold) * 0.8, 0.95)
            return MarketRegime.VOLATILE, confidence
        
        # Strong trend
        if adx > self.adx_trending_threshold:
            # Confidence based on how far above threshold
            confidence = min(0.6 + (adx - self.adx_trending_threshold) / 100, 0.95)
            return MarketRegime.TRENDING, confidence
        
        # Ranging market
        if adx < self.adx_ranging_threshold:
            # Confidence based on how far below threshold
            confidence = min(0.6 + (self.adx_ranging_threshold - adx) / 100, 0.95)
            return MarketRegime.RANGING, confidence
        
        # Transitional (between trending and ranging)
        # Use pattern score to help decide
        if abs(pattern_score) > 0.5:
            return MarketRegime.TRENDING, 0.5
        else:
            return MarketRegime.RANGING, 0.4
    
    def _get_position_recommendation(
        self, 
        regime: MarketRegime, 
        adx: float, 
        bb_width: float
    ) -> float:
        """
        Get position sizing recommendation based on regime.
        
        TRENDING: Allow aggressive (0.75-1.0)
        RANGING: Smaller positions (0.50-0.75)
        VOLATILE: Reduce significantly (0.25-0.50)
        
        Args:
            regime: Detected regime
            adx: ADX value
            bb_width: BB width
            
        Returns:
            Position size multiplier (0.25-1.0)
        """
        if regime == MarketRegime.TRENDING:
            # More aggressive in strong trends
            multiplier = 0.75 + min((adx - self.adx_trending_threshold) / 100, 0.25)
            logger.debug(f"TRENDING regime -> {multiplier:.2f}x position size")
            return multiplier
        
        elif regime == MarketRegime.RANGING:
            # Conservative in ranging markets
            multiplier = 0.50 + max((self.adx_ranging_threshold - adx) / 100, 0) * 0.25
            logger.debug(f"RANGING regime -> {multiplier:.2f}x position size")
            return max(0.50, min(0.75, multiplier))
        
        elif regime == MarketRegime.VOLATILE:
            # Very conservative in high volatility
            # More volatility = smaller position
            excess_volatility = bb_width - self.bb_volatility_threshold
            reduction = min(excess_volatility / 0.04, 0.25)
            multiplier = 0.50 - reduction
            logger.debug(f"VOLATILE regime -> {multiplier:.2f}x position size")
            return max(0.25, multiplier)
        
        else:
            # Unknown regime - use moderate sizing
            return 0.50
    
    def _build_reasoning(
        self,
        regime: MarketRegime,
        adx: float,
        bb_width: float,
        trend_direction: TrendDirection,
        pattern_score: float
    ) -> str:
        """Build human-readable reasoning for regime detection."""
        parts = []
        
        # Regime
        parts.append(f"Regime: {regime.value.upper()}")
        
        # ADX component
        if adx > self.adx_trending_threshold:
            parts.append(f"ADX {adx:.1f} (strong trend)")
        elif adx < self.adx_ranging_threshold:
            parts.append(f"ADX {adx:.1f} (weak trend/ranging)")
        else:
            parts.append(f"ADX {adx:.1f} (transitional)")
        
        # Volatility
        if bb_width > self.bb_volatility_threshold:
            parts.append(f"High volatility ({bb_width*100:.1f}%)")
        else:
            parts.append(f"Volatility {bb_width*100:.1f}%")
        
        # Trend direction
        parts.append(f"Direction: {trend_direction.value}")
        
        # Pattern
        if abs(pattern_score) > 0.5:
            direction = "bullish" if pattern_score > 0 else "bearish"
            parts.append(f"Pattern: {direction} ({pattern_score:.2f})")
        
        return " | ".join(parts)
    
    def get_strategy_adjustments(self, regime: MarketRegime) -> Dict[str, Any]:
        """
        Get recommended strategy adjustments for regime.
        
        Args:
            regime: Current market regime
            
        Returns:
            Dictionary with recommended adjustments
        """
        if regime == MarketRegime.TRENDING:
            return {
                'allow_aggressive': True,
                'required_confidence': 0.6,  # Lower confidence OK
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.5,  # Wider targets
                'position_sizing': 1.0,
                'description': 'Trending market: Allow aggressive positioning with wider targets'
            }
        
        elif regime == MarketRegime.RANGING:
            return {
                'allow_aggressive': False,
                'required_confidence': 0.75,  # Higher confidence needed
                'stop_loss_multiplier': 0.75,  # Tighter stops
                'take_profit_multiplier': 0.75,  # Tighter targets
                'position_sizing': 0.625,  # 62.5% of normal
                'description': 'Ranging market: Require higher confidence, tighter stops, smaller positions'
            }
        
        elif regime == MarketRegime.VOLATILE:
            return {
                'allow_aggressive': False,
                'required_confidence': 0.80,  # Much higher confidence
                'stop_loss_multiplier': 1.25,  # Wider stops (avoid whipsaw)
                'take_profit_multiplier': 0.75,  # Quick profits
                'position_sizing': 0.375,  # 37.5% of normal (25% reduction from base)
                'description': 'Volatile market: Reduce leverage significantly, wider stops, quick profits'
            }
        
        else:
            return {
                'allow_aggressive': False,
                'required_confidence': 0.70,
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'position_sizing': 0.75,
                'description': 'Unknown regime: Use conservative defaults'
            }
    
    def visualize_regime(self, analysis: RegimeAnalysis) -> str:
        """
        Create text visualization of regime.
        
        Args:
            analysis: Regime analysis result
            
        Returns:
            Formatted text visualization
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"MARKET REGIME ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Regime: {analysis.regime.value.upper()}")
        lines.append(f"Confidence: {analysis.confidence*100:.1f}%")
        lines.append(f"Trend Direction: {analysis.trend_direction.value.upper()}")
        lines.append("-" * 60)
        lines.append(f"ADX (Trend Strength): {analysis.trend_strength:.1f}")
        lines.append(f"BB Width (Volatility): {analysis.volatility*100:.2f}%")
        lines.append(f"Pattern Score: {analysis.metrics.get('pattern_score', 0):.2f}")
        lines.append("-" * 60)
        lines.append(f"Position Sizing Rec: {analysis.position_sizing_recommendation*100:.0f}%")
        lines.append(f"Reasoning: {analysis.reasoning}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def get_params(self) -> Dict[str, Any]:
        """Get detector parameters."""
        return {
            'adx_period': self.adx_period,
            'adx_trending_threshold': self.adx_trending_threshold,
            'adx_ranging_threshold': self.adx_ranging_threshold,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_volatility_threshold': self.bb_volatility_threshold,
            'pattern_lookback': self.pattern_lookback
        }
