"""
Download real BTC/USDT data for 2025 from Binance

Downloads 5m candles for backtesting Dual-Brain system.
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import time


def download_binance_data(
    symbol: str = "BTC/USDT",
    timeframe: str = "5m",
    start_date: str = "2025-01-01",
    end_date: str = "2025-11-30"
):
    """
    Download historical data from Binance.
    
    Args:
        symbol: Trading pair (BTC/USDT)
        timeframe: Candle timeframe (5m, 15m, 1h)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    logger.info(f"🚀 Starting download: {symbol} {timeframe}")
    logger.info(f"   Period: {start_date} → {end_date}")
    
    # Initialize Binance
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}  # Futures market
    })
    
    # Convert dates to timestamps
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
    
    # Calculate timeframe in ms
    timeframe_ms = {
        '1m': 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000
    }[timeframe]
    
    # Download in chunks (max 1500 candles per request)
    all_candles = []
    current_ts = start_ts
    chunk_num = 0
    
    while current_ts < end_ts:
        try:
            # Fetch candles
            candles = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=current_ts,
                limit=1500
            )
            
            if not candles:
                logger.warning("No more data available")
                break
            
            all_candles.extend(candles)
            chunk_num += 1
            
            # Update timestamp
            last_ts = candles[-1][0]
            current_ts = last_ts + timeframe_ms
            
            # Progress
            progress = (current_ts - start_ts) / (end_ts - start_ts) * 100
            logger.info(f"   Chunk {chunk_num}: {len(candles)} candles | Progress: {progress:.1f}%")
            
            # Rate limit
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            logger.error(f"Error downloading chunk {chunk_num}: {e}")
            time.sleep(5)
            continue
    
    # Convert to DataFrame
    df = pd.DataFrame(
        all_candles,
        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
    )
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Remove duplicates
    df = df[~df.index.duplicated(keep='first')]
    
    # Sort by time
    df.sort_index(inplace=True)
    
    logger.success(f"✅ Downloaded {len(df)} candles")
    logger.info(f"   Period: {df.index[0]} → {df.index[-1]}")
    logger.info(f"   Price range: ${df['close'].min():,.0f} - ${df['close'].max():,.0f}")
    
    return df


def save_data(df: pd.DataFrame, symbol: str = "BTC/USDT", timeframe: str = "5m"):
    """Save data to CSV."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Filename: BTCUSDT_5m_2025.csv
    filename = f"{symbol.replace('/', '')}_{timeframe}_2025.csv"
    filepath = data_dir / filename
    
    df.to_csv(filepath)
    logger.success(f"💾 Saved to: {filepath}")
    logger.info(f"   Size: {filepath.stat().st_size / 1024 / 1024:.2f} MB")
    
    return filepath


def main():
    """Main function."""
    logger.info("=" * 80)
    logger.info("📊 BINANCE DATA DOWNLOADER - 2025")
    logger.info("=" * 80)
    
    # Download data
    df = download_binance_data(
        symbol="BTC/USDT",
        timeframe="5m",
        start_date="2025-01-01",
        end_date="2025-11-30"
    )
    
    # Save to CSV
    filepath = save_data(df, symbol="BTC/USDT", timeframe="5m")
    
    # Stats
    logger.info("\n" + "=" * 80)
    logger.info("📈 DATA STATISTICS")
    logger.info("=" * 80)
    logger.info(f"Total candles: {len(df):,}")
    logger.info(f"Period: {df.index[0]} → {df.index[-1]}")
    logger.info(f"Days: {(df.index[-1] - df.index[0]).days}")
    logger.info(f"\nPrice statistics:")
    logger.info(f"   Open:  ${df['open'].iloc[0]:,.2f}")
    logger.info(f"   Close: ${df['close'].iloc[-1]:,.2f}")
    logger.info(f"   High:  ${df['high'].max():,.2f}")
    logger.info(f"   Low:   ${df['low'].min():,.2f}")
    logger.info(f"   Change: {(df['close'].iloc[-1] / df['open'].iloc[0] - 1) * 100:+.2f}%")
    logger.info(f"\nVolume:")
    logger.info(f"   Total: ${df['volume'].sum():,.0f}")
    logger.info(f"   Avg:   ${df['volume'].mean():,.0f}")
    
    logger.info("\n" + "=" * 80)
    logger.success("✅ Download complete!")
    logger.info("=" * 80)
    logger.info(f"\n💡 Next step: Run backtest")
    logger.info(f"   python run_backtest_dual_brain.py")


if __name__ == "__main__":
    main()
