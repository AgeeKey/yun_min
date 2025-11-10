"""
Advanced Technical Indicators Module

PHASE 2.3: Advanced indicators for better signal quality
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- ATR (Average True Range)
- OBV (On-Balance Volume)
- Ichimoku Cloud

Author: Phase 2 Implementation
Date: November 2025
"""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from loguru import logger


class TechnicalIndicators:
    """Collection of advanced technical indicators for trading strategy."""
    
    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        MACD measures momentum and trend strength through EMA differences.
        
        Args:
            prices: Price series (typically close prices)
            fast_period: Fast EMA period (default: 12)
            slow_period: Slow EMA period (default: 26)
            signal_period: Signal line EMA period (default: 9)
            
        Returns:
            Dictionary with 'macd_line', 'signal_line', 'histogram'
            
        Signals:
            - MACD > Signal: Bullish (rising momentum)
            - MACD < Signal: Bearish (falling momentum)
            - Crossover: Potential trend reversal
        """
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }
    
    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Bollinger Bands measure volatility and identify overbought/oversold conditions.
        
        Args:
            prices: Price series (typically close prices)
            period: Moving average period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
            
        Returns:
            Dictionary with 'upper_band', 'middle_band', 'lower_band', 'bandwidth'
            
        Signals:
            - Price touches upper band: Overbought (potential SELL)
            - Price touches lower band: Oversold (potential BUY)
            - Squeeze: Bands narrowing = low volatility, big move coming
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        # Bandwidth: measure of volatility
        bandwidth = (upper_band - lower_band) / middle_band
        
        return {
            'upper_band': upper_band,
            'middle_band': middle_band,
            'lower_band': lower_band,
            'bandwidth': bandwidth
        }
    
    @staticmethod
    def calculate_atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Calculate ATR (Average True Range).
        
        ATR measures market volatility for adaptive stop-loss and position sizing.
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period (default: 14)
            
        Returns:
            ATR series
            
        Usage:
            - dynamic_stop_loss = close - (2 × ATR)
            - position_size = account_size / (price - stop_loss)
            - Higher ATR = more volatility = smaller position
        """
        # True Range components
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # ATR is the moving average of True Range
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_obv(
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        Calculate OBV (On-Balance Volume).
        
        OBV measures buying/selling pressure using volume flow.
        
        Args:
            close: Close price series
            volume: Volume series
            
        Returns:
            OBV series
            
        Signals:
            - OBV rises with price: Strong uptrend (buyers in control)
            - OBV falls with price: Strong downtrend (sellers in control)
            - OBV divergence: Trend weakening, potential reversal
        """
        obv = pd.Series(index=close.index, dtype=float)
        obv.iloc[0] = volume.iloc[0]
        
        for i in range(1, len(close)):
            if close.iloc[i] > close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] + volume.iloc[i]
            elif close.iloc[i] < close.iloc[i - 1]:
                obv.iloc[i] = obv.iloc[i - 1] - volume.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i - 1]
        
        return obv
    
    @staticmethod
    def calculate_ichimoku(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        displacement: int = 26
    ) -> Dict[str, pd.Series]:
        """
        Calculate Ichimoku Cloud.
        
        Ichimoku provides comprehensive trend, momentum, and support/resistance analysis.
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            tenkan_period: Conversion line period (default: 9)
            kijun_period: Base line period (default: 26)
            senkou_b_period: Leading Span B period (default: 52)
            displacement: Cloud displacement (default: 26)
            
        Returns:
            Dictionary with Ichimoku components
            
        Signals:
            - Price above cloud: Strong uptrend
            - Price below cloud: Strong downtrend
            - Tenkan crosses above Kijun: Bullish signal
            - Tenkan crosses below Kijun: Bearish signal
        """
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan_sen = (high.rolling(window=tenkan_period).max() + 
                      low.rolling(window=tenkan_period).min()) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        kijun_sen = (high.rolling(window=kijun_period).max() + 
                     low.rolling(window=kijun_period).min()) / 2
        
        # Senkou Span A (Leading Span A): (Conversion Line + Base Line) / 2
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2
        senkou_span_b = ((high.rolling(window=senkou_b_period).max() + 
                         low.rolling(window=senkou_b_period).min()) / 2).shift(displacement)
        
        # Chikou Span (Lagging Span): Current close shifted back
        chikou_span = close.shift(-displacement)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span,
            'cloud_top': pd.concat([senkou_span_a, senkou_span_b], axis=1).max(axis=1),
            'cloud_bottom': pd.concat([senkou_span_a, senkou_span_b], axis=1).min(axis=1)
        }
    
    @staticmethod
    def analyze_macd_signal(macd_data: Dict[str, pd.Series]) -> Tuple[str, float]:
        """
        Analyze MACD for trading signal.
        
        Args:
            macd_data: Dictionary from calculate_macd()
            
        Returns:
            Tuple of (signal, strength) where signal is 'bullish'/'bearish'/'neutral'
            and strength is 0-1
        """
        if macd_data['histogram'].iloc[-1] > 0:
            # Bullish: MACD above signal
            strength = min(abs(macd_data['histogram'].iloc[-1]) / 
                          abs(macd_data['macd_line'].iloc[-1]), 1.0) if macd_data['macd_line'].iloc[-1] != 0 else 0.5
            return 'bullish', strength
        elif macd_data['histogram'].iloc[-1] < 0:
            # Bearish: MACD below signal
            strength = min(abs(macd_data['histogram'].iloc[-1]) / 
                          abs(macd_data['macd_line'].iloc[-1]), 1.0) if macd_data['macd_line'].iloc[-1] != 0 else 0.5
            return 'bearish', strength
        else:
            return 'neutral', 0.0
    
    @staticmethod
    def analyze_bollinger_position(
        price: float,
        bb_data: Dict[str, pd.Series]
    ) -> Tuple[str, float]:
        """
        Analyze price position relative to Bollinger Bands.
        
        Args:
            price: Current price
            bb_data: Dictionary from calculate_bollinger_bands()
            
        Returns:
            Tuple of (signal, strength) where signal is 'overbought'/'oversold'/'normal'
        """
        upper = bb_data['upper_band'].iloc[-1]
        lower = bb_data['lower_band'].iloc[-1]
        middle = bb_data['middle_band'].iloc[-1]
        
        if pd.isna(upper) or pd.isna(lower) or pd.isna(middle):
            return 'normal', 0.0
        
        band_width = upper - lower
        if band_width == 0:
            return 'normal', 0.0
        
        if price >= upper:
            # Overbought
            strength = min((price - upper) / band_width, 1.0)
            return 'overbought', strength
        elif price <= lower:
            # Oversold
            strength = min((lower - price) / band_width, 1.0)
            return 'oversold', strength
        else:
            return 'normal', 0.0
    
    @staticmethod
    def analyze_obv_trend(obv: pd.Series, period: int = 10) -> Tuple[str, float]:
        """
        Analyze OBV trend.
        
        Args:
            obv: OBV series
            period: Lookback period for trend analysis
            
        Returns:
            Tuple of (trend, strength) where trend is 'bullish'/'bearish'/'neutral'
        """
        if len(obv) < period:
            return 'neutral', 0.0
        
        # Compare current OBV to its moving average
        obv_ma = obv.rolling(window=period).mean()
        current_obv = obv.iloc[-1]
        current_ma = obv_ma.iloc[-1]
        
        if pd.isna(current_ma) or current_ma == 0:
            return 'neutral', 0.0
        
        deviation = (current_obv - current_ma) / abs(current_ma)
        
        if deviation > 0.05:  # OBV significantly above MA
            return 'bullish', min(deviation, 1.0)
        elif deviation < -0.05:  # OBV significantly below MA
            return 'bearish', min(abs(deviation), 1.0)
        else:
            return 'neutral', 0.0
    
    @staticmethod
    def analyze_ichimoku_signal(
        price: float,
        ichimoku_data: Dict[str, pd.Series]
    ) -> Tuple[str, float]:
        """
        Analyze Ichimoku Cloud for trading signal.
        
        Args:
            price: Current price
            ichimoku_data: Dictionary from calculate_ichimoku()
            
        Returns:
            Tuple of (signal, strength) where signal is 'bullish'/'bearish'/'neutral'
        """
        cloud_top = ichimoku_data['cloud_top'].iloc[-1]
        cloud_bottom = ichimoku_data['cloud_bottom'].iloc[-1]
        tenkan = ichimoku_data['tenkan_sen'].iloc[-1]
        kijun = ichimoku_data['kijun_sen'].iloc[-1]
        
        if pd.isna(cloud_top) or pd.isna(cloud_bottom):
            return 'neutral', 0.0
        
        # Price position relative to cloud
        if price > cloud_top:
            # Above cloud: bullish
            strength = 0.7
            if tenkan > kijun:
                strength = 0.9  # Strong bullish
            return 'bullish', strength
        elif price < cloud_bottom:
            # Below cloud: bearish
            strength = 0.7
            if tenkan < kijun:
                strength = 0.9  # Strong bearish
            return 'bearish', strength
        else:
            # Inside cloud: neutral
            return 'neutral', 0.0


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all technical indicators for a dataframe.
    
    Args:
        df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
    Returns:
        DataFrame with all indicators added
    """
    if df.empty or len(df) < 52:  # Need at least 52 periods for Ichimoku
        logger.warning("Insufficient data for all indicators")
        return df
    
    indicators = TechnicalIndicators()
    result = df.copy()
    
    try:
        # MACD
        macd_data = indicators.calculate_macd(df['close'])
        result['macd_line'] = macd_data['macd_line']
        result['macd_signal'] = macd_data['signal_line']
        result['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = indicators.calculate_bollinger_bands(df['close'])
        result['bb_upper'] = bb_data['upper_band']
        result['bb_middle'] = bb_data['middle_band']
        result['bb_lower'] = bb_data['lower_band']
        result['bb_bandwidth'] = bb_data['bandwidth']
        
        # ATR
        result['atr'] = indicators.calculate_atr(df['high'], df['low'], df['close'])
        
        # OBV
        result['obv'] = indicators.calculate_obv(df['close'], df['volume'])
        
        # Ichimoku
        ichimoku_data = indicators.calculate_ichimoku(df['high'], df['low'], df['close'])
        result['ichimoku_tenkan'] = ichimoku_data['tenkan_sen']
        result['ichimoku_kijun'] = ichimoku_data['kijun_sen']
        result['ichimoku_senkou_a'] = ichimoku_data['senkou_span_a']
        result['ichimoku_senkou_b'] = ichimoku_data['senkou_span_b']
        result['ichimoku_cloud_top'] = ichimoku_data['cloud_top']
        result['ichimoku_cloud_bottom'] = ichimoku_data['cloud_bottom']
        
        logger.info("✅ All indicators calculated successfully")
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
    
    return result
