"""
Historical Data Loader - загрузка исторических данных для backtesting
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger


class HistoricalDataLoader:
    """
    Загрузчик исторических OHLCV данных.
    
    Поддерживает:
    - Загрузка с биржи (Binance)
    - Загрузка из CSV файлов
    - Кэширование данных
    """
    
    def __init__(self, exchange=None):
        """
        Args:
            exchange: Exchange adapter (optional)
        """
        self.exchange = exchange
        self.cache = {}  # Simple in-memory cache
        
    def load_from_exchange(
        self,
        symbol: str,
        timeframe: str = '1h',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Загрузить данные с биржи.
        
        Args:
            symbol: Торговая пара (e.g., 'BTC/USDT')
            timeframe: Временной интервал ('1m', '5m', '1h', '1d')
            start_date: Начальная дата (optional)
            end_date: Конечная дата (optional)
            limit: Максимум свечей за запрос
            
        Returns:
            DataFrame с колонками: timestamp, open, high, low, close, volume
        """
        if self.exchange is None:
            raise ValueError("Exchange adapter not provided")
        
        # Проверить кэш
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        if cache_key in self.cache:
            logger.info(f"Using cached data for {symbol}")
            return self.cache[cache_key].copy()
        
        logger.info(f"Loading {symbol} data from exchange ({timeframe})")
        
        try:
            # Загрузить OHLCV
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            # Конвертировать в DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Фильтровать по датам
            if start_date:
                df = df[df['timestamp'] >= start_date]
            if end_date:
                df = df[df['timestamp'] <= end_date]
            
            # Сортировать по времени
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Кэшировать
            self.cache[cache_key] = df.copy()
            
            logger.info(f"Loaded {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load data from exchange: {e}")
            raise
    
    def load_from_csv(self, filepath: str) -> pd.DataFrame:
        """
        Загрузить данные из CSV файла.
        
        Expected format:
        timestamp,open,high,low,close,volume
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Loading data from CSV: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            
            # Конвертировать timestamp
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            elif 'date' in df.columns:
                df['timestamp'] = pd.to_datetime(df['date'])
                df = df.drop(columns=['date'])
            
            # Проверить обязательные колонки
            required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Сортировать
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Loaded {len(df)} candles from CSV")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise
    
    def generate_sample_data(
        self,
        symbol: str = 'BTC/USDT',
        start_price: float = 50000.0,
        num_candles: int = 1000,
        timeframe: str = '1h',
        trend: str = 'sideways',
        volatility: float = 0.02
    ) -> pd.DataFrame:
        """
        Генерация синтетических данных для тестирования.
        
        Args:
            symbol: Symbol name
            start_price: Starting price
            num_candles: Number of candles to generate
            timeframe: Timeframe string
            trend: 'uptrend', 'downtrend', or 'sideways'
            volatility: Price volatility (0.01 = 1%)
            
        Returns:
            DataFrame with synthetic OHLCV data
        """
        logger.info(f"Generating {num_candles} sample candles ({trend} trend)")
        
        # Timeframe to minutes
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        interval_minutes = tf_minutes.get(timeframe, 60)
        
        # Generate timestamps
        start_time = datetime.now() - timedelta(minutes=interval_minutes * num_candles)
        timestamps = [
            start_time + timedelta(minutes=interval_minutes * i)
            for i in range(num_candles)
        ]
        
        # Generate prices with trend
        import numpy as np
        
        prices = [start_price]
        trend_multiplier = {
            'uptrend': 1.0005,      # +0.05% per candle
            'downtrend': 0.9995,    # -0.05% per candle
            'sideways': 1.0         # No trend
        }
        
        multiplier = trend_multiplier.get(trend, 1.0)
        
        for i in range(1, num_candles):
            # Add trend
            price = prices[-1] * multiplier
            
            # Add random walk
            random_change = np.random.normal(0, volatility)
            price = price * (1 + random_change)
            
            prices.append(price)
        
        # Generate OHLC from prices
        data = []
        for i, (ts, close) in enumerate(zip(timestamps, prices)):
            # Random OHLC around close
            high = close * (1 + abs(np.random.normal(0, volatility/2)))
            low = close * (1 - abs(np.random.normal(0, volatility/2)))
            open_price = close * (1 + np.random.normal(0, volatility/3))
            
            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = np.random.uniform(100, 1000)  # Random volume
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} candles (price range: ${df['low'].min():.2f} - ${df['high'].max():.2f})")
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Валидация данных на корректность.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError if invalid
        """
        # Проверить колонки
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        
        # Проверить OHLC consistency
        invalid_ohlc = df[
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        ]
        
        if len(invalid_ohlc) > 0:
            raise ValueError(f"Found {len(invalid_ohlc)} invalid OHLC rows")
        
        # Проверить отрицательные значения
        if (df[['open', 'high', 'low', 'close', 'volume']] < 0).any().any():
            raise ValueError("Found negative prices or volumes")
        
        logger.info("Data validation passed")
        return True
