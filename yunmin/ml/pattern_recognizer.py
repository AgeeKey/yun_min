"""
Pattern Recognition System - Automatic chart pattern detection.

This module implements template matching and ML-based classification
for detecting classical chart patterns like Head & Shoulders, Double Tops/Bottoms,
Flags, and Triangles.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from scipy.signal import find_peaks, argrelextrema
from scipy.spatial.distance import euclidean
from sklearn.ensemble import RandomForestClassifier
import pickle


class PatternType(Enum):
    """Types of chart patterns."""
    # Bullish patterns
    DOUBLE_BOTTOM = "double_bottom"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    BULL_FLAG = "bull_flag"
    ASCENDING_TRIANGLE = "ascending_triangle"
    
    # Bearish patterns
    DOUBLE_TOP = "double_top"
    HEAD_SHOULDERS = "head_shoulders"
    BEAR_FLAG = "bear_flag"
    DESCENDING_TRIANGLE = "descending_triangle"
    
    # Neutral patterns
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    RECTANGLE = "rectangle"


class PatternSentiment(Enum):
    """Pattern sentiment."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class Pattern:
    """Detected chart pattern."""
    pattern_type: PatternType
    sentiment: PatternSentiment
    reliability_score: float  # 0.0 to 1.0
    start_idx: int
    end_idx: int
    key_points: List[Tuple[int, float]]  # [(index, price), ...]
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'pattern_type': self.pattern_type.value,
            'sentiment': self.sentiment.value,
            'reliability_score': self.reliability_score,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'key_points': self.key_points,
            'metadata': self.metadata or {}
        }


@dataclass
class PatternSignal:
    """Trading signal from pattern recognition."""
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0.0 to 1.0
    pattern: Pattern
    reason: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'action': self.action,
            'confidence': self.confidence,
            'pattern': self.pattern.to_dict(),
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat()
        }


class PatternRecognizer:
    """
    Chart pattern recognition system.
    
    Uses template matching for classical patterns and ML classifier
    for pattern validation based on historical success rates.
    """
    
    def __init__(self, lookback_window: int = 100, min_pattern_length: int = 10):
        """
        Initialize pattern recognizer.
        
        Args:
            lookback_window: Number of candles to analyze
            min_pattern_length: Minimum candles for a valid pattern
        """
        self.lookback_window = lookback_window
        self.min_pattern_length = min_pattern_length
        self.classifier: Optional[RandomForestClassifier] = None
        self.pattern_success_rates = {}
        self.is_trained = False
        
    def _find_pivot_points(self, prices: np.ndarray, order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find pivot highs and lows in price data.
        
        Args:
            prices: Array of prices
            order: Number of points on each side to use for comparison
            
        Returns:
            Tuple of (pivot_highs_indices, pivot_lows_indices)
        """
        # Find local maxima (pivot highs)
        pivot_highs = argrelextrema(prices, np.greater, order=order)[0]
        
        # Find local minima (pivot lows)
        pivot_lows = argrelextrema(prices, np.less, order=order)[0]
        
        return pivot_highs, pivot_lows
    
    def _detect_double_top(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect double top pattern.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        prices = df['high'].values
        pivot_highs, _ = self._find_pivot_points(prices)
        
        if len(pivot_highs) < 2:
            return None
        
        # Look for two consecutive highs at similar levels
        for i in range(len(pivot_highs) - 1):
            idx1, idx2 = pivot_highs[i], pivot_highs[i + 1]
            price1, price2 = prices[idx1], prices[idx2]
            
            # Check if peaks are at similar levels (within 2%)
            price_diff_pct = abs(price1 - price2) / price1
            if price_diff_pct < 0.02:
                # Check if there's a trough between them
                middle_section = prices[idx1:idx2]
                if len(middle_section) > 0:
                    trough_price = np.min(middle_section)
                    trough_idx = idx1 + np.argmin(middle_section)
                    
                    # Trough should be significantly lower (at least 1.5% below peaks)
                    trough_depth = (price1 - trough_price) / price1
                    if trough_depth > 0.015:
                        reliability = min(0.9, trough_depth * 20)  # Scale reliability
                        
                        return Pattern(
                            pattern_type=PatternType.DOUBLE_TOP,
                            sentiment=PatternSentiment.BEARISH,
                            reliability_score=reliability,
                            start_idx=int(idx1),
                            end_idx=int(idx2),
                            key_points=[
                                (int(idx1), float(price1)),
                                (int(trough_idx), float(trough_price)),
                                (int(idx2), float(price2))
                            ]
                        )
        
        return None
    
    def _detect_double_bottom(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect double bottom pattern.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        prices = df['low'].values
        _, pivot_lows = self._find_pivot_points(prices)
        
        if len(pivot_lows) < 2:
            return None
        
        # Look for two consecutive lows at similar levels
        for i in range(len(pivot_lows) - 1):
            idx1, idx2 = pivot_lows[i], pivot_lows[i + 1]
            price1, price2 = prices[idx1], prices[idx2]
            
            # Check if troughs are at similar levels (within 2%)
            price_diff_pct = abs(price1 - price2) / price1
            if price_diff_pct < 0.02:
                # Check if there's a peak between them
                middle_section = df['high'].values[idx1:idx2]
                if len(middle_section) > 0:
                    peak_price = np.max(middle_section)
                    peak_idx = idx1 + np.argmax(middle_section)
                    
                    # Peak should be significantly higher (at least 1.5% above troughs)
                    peak_height = (peak_price - price1) / price1
                    if peak_height > 0.015:
                        reliability = min(0.9, peak_height * 20)
                        
                        return Pattern(
                            pattern_type=PatternType.DOUBLE_BOTTOM,
                            sentiment=PatternSentiment.BULLISH,
                            reliability_score=reliability,
                            start_idx=int(idx1),
                            end_idx=int(idx2),
                            key_points=[
                                (int(idx1), float(price1)),
                                (int(peak_idx), float(peak_price)),
                                (int(idx2), float(price2))
                            ]
                        )
        
        return None
    
    def _detect_head_shoulders(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect head and shoulders pattern.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        prices = df['high'].values
        pivot_highs, _ = self._find_pivot_points(prices)
        
        if len(pivot_highs) < 3:
            return None
        
        # Look for three peaks: left shoulder, head, right shoulder
        for i in range(len(pivot_highs) - 2):
            left_idx, head_idx, right_idx = pivot_highs[i], pivot_highs[i + 1], pivot_highs[i + 2]
            left_price, head_price, right_price = prices[left_idx], prices[head_idx], prices[right_idx]
            
            # Head should be higher than shoulders
            if head_price > left_price and head_price > right_price:
                # Shoulders should be at similar levels (within 3%)
                shoulder_diff = abs(left_price - right_price) / left_price
                if shoulder_diff < 0.03:
                    # Head should be significantly higher than shoulders (at least 2%)
                    head_prominence = (head_price - max(left_price, right_price)) / head_price
                    if head_prominence > 0.02:
                        reliability = min(0.9, head_prominence * 15)
                        
                        return Pattern(
                            pattern_type=PatternType.HEAD_SHOULDERS,
                            sentiment=PatternSentiment.BEARISH,
                            reliability_score=reliability,
                            start_idx=int(left_idx),
                            end_idx=int(right_idx),
                            key_points=[
                                (int(left_idx), float(left_price)),
                                (int(head_idx), float(head_price)),
                                (int(right_idx), float(right_price))
                            ]
                        )
        
        return None
    
    def _detect_inverse_head_shoulders(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect inverse head and shoulders pattern.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        prices = df['low'].values
        _, pivot_lows = self._find_pivot_points(prices)
        
        if len(pivot_lows) < 3:
            return None
        
        # Look for three troughs: left shoulder, head, right shoulder
        for i in range(len(pivot_lows) - 2):
            left_idx, head_idx, right_idx = pivot_lows[i], pivot_lows[i + 1], pivot_lows[i + 2]
            left_price, head_price, right_price = prices[left_idx], prices[head_idx], prices[right_idx]
            
            # Head should be lower than shoulders
            if head_price < left_price and head_price < right_price:
                # Shoulders should be at similar levels (within 3%)
                shoulder_diff = abs(left_price - right_price) / left_price
                if shoulder_diff < 0.03:
                    # Head should be significantly lower than shoulders (at least 2%)
                    head_depth = (min(left_price, right_price) - head_price) / head_price
                    if head_depth > 0.02:
                        reliability = min(0.9, head_depth * 15)
                        
                        return Pattern(
                            pattern_type=PatternType.INVERSE_HEAD_SHOULDERS,
                            sentiment=PatternSentiment.BULLISH,
                            reliability_score=reliability,
                            start_idx=int(left_idx),
                            end_idx=int(right_idx),
                            key_points=[
                                (int(left_idx), float(left_price)),
                                (int(head_idx), float(head_price)),
                                (int(right_idx), float(right_price))
                            ]
                        )
        
        return None
    
    def _detect_flag(self, df: pd.DataFrame, bullish: bool = True) -> Optional[Pattern]:
        """
        Detect bull or bear flag pattern.
        
        Args:
            df: DataFrame with OHLCV data
            bullish: Whether to detect bull flag (True) or bear flag (False)
            
        Returns:
            Pattern object if detected, None otherwise
        """
        if len(df) < 20:
            return None
        
        prices = df['close'].values
        
        # Look for strong initial move (pole)
        pole_length = 10
        flag_length = 15
        
        if len(prices) < pole_length + flag_length:
            return None
        
        # Check for pole
        pole_prices = prices[:pole_length]
        pole_move = (pole_prices[-1] - pole_prices[0]) / pole_prices[0]
        
        if bullish:
            # For bull flag, need upward pole (at least 3% move)
            if pole_move < 0.03:
                return None
        else:
            # For bear flag, need downward pole (at least 3% move)
            if pole_move > -0.03:
                return None
        
        # Check for consolidation (flag)
        flag_prices = prices[pole_length:pole_length + flag_length]
        flag_range = (np.max(flag_prices) - np.min(flag_prices)) / np.mean(flag_prices)
        
        # Flag should be relatively tight (less than 2% range)
        if flag_range < 0.02:
            pattern_type = PatternType.BULL_FLAG if bullish else PatternType.BEAR_FLAG
            sentiment = PatternSentiment.BULLISH if bullish else PatternSentiment.BEARISH
            
            # Calculate reliability based on pole strength and flag tightness
            reliability = min(0.9, abs(pole_move) * 10 + (0.02 - flag_range) * 10)
            
            return Pattern(
                pattern_type=pattern_type,
                sentiment=sentiment,
                reliability_score=reliability,
                start_idx=0,
                end_idx=pole_length + flag_length,
                key_points=[
                    (0, float(pole_prices[0])),
                    (pole_length - 1, float(pole_prices[-1])),
                    (pole_length + flag_length - 1, float(flag_prices[-1]))
                ]
            )
        
        return None
    
    def _detect_triangle(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect triangle patterns (ascending, descending, symmetrical).
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        if len(df) < 20:
            return None
        
        highs = df['high'].values[-20:]
        lows = df['low'].values[-20:]
        
        # Fit trend lines to highs and lows
        x = np.arange(len(highs))
        
        # Upper trend line (resistance)
        upper_coef = np.polyfit(x, highs, 1)
        upper_slope = upper_coef[0]
        
        # Lower trend line (support)
        lower_coef = np.polyfit(x, lows, 1)
        lower_slope = lower_coef[0]
        
        # Normalize slopes by price level
        avg_price = np.mean(df['close'].values[-20:])
        upper_slope_pct = upper_slope / avg_price
        lower_slope_pct = lower_slope / avg_price
        
        # Ascending triangle: flat resistance, rising support
        if abs(upper_slope_pct) < 0.001 and lower_slope_pct > 0.001:
            return Pattern(
                pattern_type=PatternType.ASCENDING_TRIANGLE,
                sentiment=PatternSentiment.BULLISH,
                reliability_score=min(0.8, lower_slope_pct * 200),
                start_idx=len(df) - 20,
                end_idx=len(df) - 1,
                key_points=[
                    (len(df) - 20, float(highs[0])),
                    (len(df) - 1, float(highs[-1]))
                ]
            )
        
        # Descending triangle: declining resistance, flat support
        if upper_slope_pct < -0.001 and abs(lower_slope_pct) < 0.001:
            return Pattern(
                pattern_type=PatternType.DESCENDING_TRIANGLE,
                sentiment=PatternSentiment.BEARISH,
                reliability_score=min(0.8, abs(upper_slope_pct) * 200),
                start_idx=len(df) - 20,
                end_idx=len(df) - 1,
                key_points=[
                    (len(df) - 20, float(highs[0])),
                    (len(df) - 1, float(highs[-1]))
                ]
            )
        
        # Symmetrical triangle: both converging
        if upper_slope_pct < -0.001 and lower_slope_pct > 0.001:
            convergence = abs(upper_slope_pct) + lower_slope_pct
            return Pattern(
                pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                sentiment=PatternSentiment.NEUTRAL,
                reliability_score=min(0.7, convergence * 100),
                start_idx=len(df) - 20,
                end_idx=len(df) - 1,
                key_points=[
                    (len(df) - 20, float(highs[0])),
                    (len(df) - 1, float(highs[-1]))
                ]
            )
        
        return None
    
    def _detect_rectangle(self, df: pd.DataFrame) -> Optional[Pattern]:
        """
        Detect rectangle (trading range) pattern.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Pattern object if detected, None otherwise
        """
        if len(df) < 20:
            return None
        
        highs = df['high'].values[-20:]
        lows = df['low'].values[-20:]
        
        # Check if highs and lows are relatively flat
        high_range = (np.max(highs) - np.min(highs)) / np.mean(highs)
        low_range = (np.max(lows) - np.min(lows)) / np.mean(lows)
        
        # Both should be tight (less than 2%)
        if high_range < 0.02 and low_range < 0.02:
            # Check that there's a meaningful channel width
            channel_width = (np.mean(highs) - np.mean(lows)) / np.mean(df['close'].values[-20:])
            
            if channel_width > 0.01:  # At least 1% channel
                return Pattern(
                    pattern_type=PatternType.RECTANGLE,
                    sentiment=PatternSentiment.NEUTRAL,
                    reliability_score=min(0.7, (0.02 - high_range) * 20),
                    start_idx=len(df) - 20,
                    end_idx=len(df) - 1,
                    key_points=[
                        (len(df) - 20, float(np.mean(highs))),
                        (len(df) - 1, float(np.mean(lows)))
                    ]
                )
        
        return None
    
    def detect_patterns(self, df: pd.DataFrame) -> List[Pattern]:
        """
        Detect all patterns in the given data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            List of detected patterns
        """
        if len(df) < self.min_pattern_length:
            return []
        
        # Use only the lookback window
        df_window = df.iloc[-self.lookback_window:] if len(df) > self.lookback_window else df
        
        patterns = []
        
        # Detect all pattern types
        pattern_detectors = [
            self._detect_double_top,
            self._detect_double_bottom,
            self._detect_head_shoulders,
            self._detect_inverse_head_shoulders,
            lambda df: self._detect_flag(df, bullish=True),
            lambda df: self._detect_flag(df, bullish=False),
            self._detect_triangle,
            self._detect_rectangle
        ]
        
        for detector in pattern_detectors:
            try:
                pattern = detector(df_window)
                if pattern is not None:
                    patterns.append(pattern)
            except Exception:
                continue
        
        return patterns
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        current_trend: Optional[str] = None
    ) -> Optional[PatternSignal]:
        """
        Generate trading signal based on detected patterns.
        
        Args:
            df: DataFrame with OHLCV data
            current_trend: Current market trend ('uptrend', 'downtrend', None)
            
        Returns:
            PatternSignal or None
        """
        patterns = self.detect_patterns(df)
        
        if not patterns:
            return None
        
        # Sort by reliability score
        patterns.sort(key=lambda p: p.reliability_score, reverse=True)
        best_pattern = patterns[0]
        
        # Generate signal based on pattern and trend
        action = 'HOLD'
        confidence = best_pattern.reliability_score
        reason = f"Detected {best_pattern.pattern_type.value}"
        
        if best_pattern.sentiment == PatternSentiment.BULLISH:
            if current_trend == 'uptrend':
                action = 'BUY'
                confidence *= 1.2  # Boost confidence when pattern aligns with trend
                reason += " in uptrend - Strong BUY signal"
            else:
                action = 'BUY'
                reason += " - Potential reversal"
                
        elif best_pattern.sentiment == PatternSentiment.BEARISH:
            if current_trend == 'downtrend':
                action = 'SELL'
                confidence *= 1.2
                reason += " in downtrend - Strong SELL signal"
            else:
                action = 'SELL'
                reason += " - Potential reversal"
        
        # Cap confidence at 1.0
        confidence = min(1.0, confidence)
        
        return PatternSignal(
            action=action,
            confidence=confidence,
            pattern=best_pattern,
            reason=reason,
            timestamp=datetime.now()
        )
    
    def train_classifier(self, historical_patterns: List[Dict]):
        """
        Train ML classifier to validate patterns based on historical success.
        
        Args:
            historical_patterns: List of historical pattern outcomes
                Each dict should have: {'pattern_type', 'features', 'success': bool}
        """
        if len(historical_patterns) < 10:
            return
        
        X = []
        y = []
        
        for record in historical_patterns:
            if 'features' in record and 'success' in record:
                X.append(record['features'])
                y.append(1 if record['success'] else 0)
        
        if len(X) > 0:
            self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
            self.classifier.fit(X, y)
            self.is_trained = True
    
    def get_pattern_success_rate(self, pattern_type: PatternType) -> float:
        """
        Get historical success rate for a pattern type.
        
        Args:
            pattern_type: Type of pattern
            
        Returns:
            Success rate (0.0 to 1.0)
        """
        return self.pattern_success_rates.get(pattern_type.value, 0.5)
    
    def save_model(self, filepath: str):
        """Save pattern recognizer to disk."""
        data = {
            'classifier': self.classifier,
            'pattern_success_rates': self.pattern_success_rates,
            'lookback_window': self.lookback_window,
            'min_pattern_length': self.min_pattern_length,
            'is_trained': self.is_trained
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load_model(self, filepath: str):
        """Load pattern recognizer from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.classifier = data['classifier']
        self.pattern_success_rates = data['pattern_success_rates']
        self.lookback_window = data['lookback_window']
        self.min_pattern_length = data['min_pattern_length']
        self.is_trained = data['is_trained']
