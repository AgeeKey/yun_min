"""
Market Data Provider - Rich Market Context

Fetches and aggregates market data from multiple timeframes.
Provides 500+ candles, technical indicators, and market metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger


class MarketDataProvider:
    """
    Provides comprehensive market data for AI decision-making.
    
    Features:
    - Multi-timeframe candles (5m, 1h, 4h)
    - Technical indicators (RSI, MACD, Bollinger, etc.)
    - Support/resistance levels
    - Volume profile
    """
    
    def __init__(self, exchange_connector: Optional[Any] = None):
        """
        Initialize market data provider.
        
        Args:
            exchange_connector: Exchange connector for fetching data
        """
        self.exchange = exchange_connector
        logger.info("📊 Market Data Provider initialized")
    
    async def fetch_market_context(
        self,
        symbol: str = 'BTC/USDT',
        include_multi_timeframe: bool = True
    ) -> Dict[str, Any]:
        """
        Fetch comprehensive market context.
        
        Args:
            symbol: Trading symbol
            include_multi_timeframe: Whether to include multiple timeframes
            
        Returns:
            Rich market context dictionary
        """
        logger.debug(f"📊 Fetching market context for {symbol}")
        
        context = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat()
        }
        
        # Fetch candles for different timeframes
        if include_multi_timeframe:
            context['candles_5m'] = await self._fetch_candles(symbol, '5m', 500)
            context['candles_1h'] = await self._fetch_candles(symbol, '1h', 200)
            context['candles_4h'] = await self._fetch_candles(symbol, '4h', 100)
        else:
            context['candles_5m'] = await self._fetch_candles(symbol, '5m', 100)
        
        # Calculate indicators from 5m data
        df = context['candles_5m']
        if df is not None and len(df) > 0:
            context['price'] = float(df['close'].iloc[-1])
            context['indicators'] = self._calculate_indicators(df)
            context['support_resistance'] = self._find_support_resistance(df)
            context['volume_profile'] = self._calculate_volume_profile(df)
            context['trend'] = self._identify_trend(df)
            context['volatility'] = self._calculate_volatility(df)
            context['price_change_pct'] = float((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2] * 100) if len(df) > 1 else 0.0
        
        logger.debug(f"✅ Market context fetched: price={context.get('price', 0):.2f}")
        return context
    
    async def _fetch_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candles from exchange.
        """
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_ohlcv'):
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )
                
                df = pd.DataFrame(
                    ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                return df
            else:
                # Generate sample data for testing
                return self._generate_sample_candles(limit)
        
        except Exception as e:
            logger.warning(f"Failed to fetch {timeframe} candles: {e}, using sample data")
            return self._generate_sample_candles(limit)
    
    def _generate_sample_candles(self, limit: int) -> pd.DataFrame:
        """
        Generate sample OHLCV data for testing.
        """
        dates = pd.date_range(end=datetime.now(), periods=limit, freq='5min')
        
        # Generate realistic-looking price data
        base_price = 50000.0
        returns = np.random.randn(limit) * 0.001  # 0.1% std returns
        prices = base_price * (1 + returns).cumprod()
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * (1 + np.random.rand(limit) * 0.002),
            'low': prices * (1 - np.random.rand(limit) * 0.002),
            'close': prices,
            'volume': np.random.rand(limit) * 1000 + 500
        })
        
        return df
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate technical indicators.
        """
        indicators = {}
        
        # RSI
        indicators['rsi'] = self._calculate_rsi(df['close'], period=14)
        
        # EMA
        indicators['ema_fast'] = float(df['close'].ewm(span=9, adjust=False).mean().iloc[-1])
        indicators['ema_slow'] = float(df['close'].ewm(span=21, adjust=False).mean().iloc[-1])
        
        # MACD
        macd_line, signal_line, _ = self._calculate_macd(df['close'])
        indicators['macd'] = float(macd_line.iloc[-1] if len(macd_line) > 0 else 0)
        indicators['macd_signal'] = float(signal_line.iloc[-1] if len(signal_line) > 0 else 0)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(df['close'])
        indicators['bb_upper'] = float(bb_upper.iloc[-1])
        indicators['bb_middle'] = float(bb_middle.iloc[-1])
        indicators['bb_lower'] = float(bb_lower.iloc[-1])
        
        # Volume
        indicators['volume_ratio'] = float(df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else 1.0
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi.iloc[-1]) if len(rsi) > 0 else 50.0
    
    def _calculate_macd(
        self,
        prices: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """Calculate MACD indicator."""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(
        self,
        prices: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> tuple:
        """Calculate Bollinger Bands."""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def _find_support_resistance(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        Find support and resistance levels.
        """
        # Simple approach: find local maxima/minima
        highs = df['high'].values
        lows = df['low'].values
        
        # Find local maxima (resistance)
        resistance = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance.append(float(highs[i]))
        
        # Find local minima (support)
        support = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support.append(float(lows[i]))
        
        # Keep only recent levels
        resistance = sorted(resistance[-5:], reverse=True)
        support = sorted(support[-5:])
        
        return {
            'resistance_levels': resistance[:3],
            'support_levels': support[:3]
        }
    
    def _calculate_volume_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate volume profile metrics.
        """
        # Volume-weighted average price (VWAP)
        vwap = (df['close'] * df['volume']).sum() / df['volume'].sum()
        
        # High volume price levels
        price_bins = 20
        price_range = df['high'].max() - df['low'].min()
        bin_size = price_range / price_bins
        
        return {
            'vwap': float(vwap),
            'avg_volume': float(df['volume'].mean()),
            'volume_trend': 'increasing' if df['volume'].iloc[-5:].mean() > df['volume'].iloc[-20:-5].mean() else 'decreasing'
        }
    
    def _identify_trend(self, df: pd.DataFrame) -> str:
        """
        Identify market trend.
        """
        # Use EMA crossover
        ema_fast = df['close'].ewm(span=9, adjust=False).mean()
        ema_slow = df['close'].ewm(span=21, adjust=False).mean()
        
        if ema_fast.iloc[-1] > ema_slow.iloc[-1] * 1.01:
            return 'bullish'
        elif ema_fast.iloc[-1] < ema_slow.iloc[-1] * 0.99:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Calculate price volatility (standard deviation of returns).
        """
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std().iloc[-1]
        
        return float(volatility) if not pd.isna(volatility) else 0.02
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.
        """
        # This would normally query the exchange
        # For now, return None to trigger async fetch
        return None


class MarketDataCollector:
    """
    Simplified market data collector for testing.
    Stores candle history and provides context.
    """
    
    def __init__(self, history_length: int = 500):
        """
        Args:
            history_length: Maximum history length
        """
        self.history_length = history_length
        self.candles: Optional[pd.DataFrame] = None
        logger.info(f"📊 Market Data Collector initialized (max length={history_length})")
    
    def update(self, candles: pd.DataFrame):
        """
        Updates the candle history.
        
        Args:
            candles: DataFrame with candles
        """
        if self.candles is None:
            self.candles = candles.tail(self.history_length).copy()
        else:
            # Объединяем и обрезаем
            self.candles = pd.concat([self.candles, candles]).tail(self.history_length)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Returns market context.
        
        Returns:
            Dict with market data
        """
        if self.candles is None or len(self.candles) == 0:
            return {
                'candles_count': 0,
                'indicators': {}
            }
        
        # Calculate basic indicators
        close = self.candles['close']
        
        indicators = {
            'current_price': float(close.iloc[-1]),
            'price_change_24h': float((close.iloc[-1] - close.iloc[0]) / close.iloc[0] * 100),
            'high_24h': float(self.candles['high'].max()),
            'low_24h': float(self.candles['low'].min()),
            'volume_total': float(self.candles['volume'].sum())
        }
        
        return {
            'candles_count': len(self.candles),
            'indicators': indicators,
            'timeframe': '5min'
        }
