#!/usr/bin/env python3
"""
Скачивание РЕАЛЬНЫХ исторических данных с Binance (БЕЗ API ключей)

Binance предоставляет публичный доступ к историческим данным:
https://data.binance.vision/

Формат: CSV файлы с 1-минутными свечами
"""

import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time
from loguru import logger


def download_binance_klines(symbol: str, date: str, output_dir: Path):
    """
    Скачать дневные klines с Binance Data Portal.
    
    Args:
        symbol: Торговая пара (например BTCUSDT)
        date: Дата в формате YYYY-MM-DD
        output_dir: Папка для сохранения
    """
    # Binance Data Portal URL (PUBLIC, no API key needed!)
    base_url = "https://data.binance.vision/data/spot/daily/klines"
    
    # Формат: BTCUSDT/1m/BTCUSDT-1m-2024-11-01.zip
    url = f"{base_url}/{symbol}/1m/{symbol}-1m-{date}.zip"
    
    logger.info(f"Downloading {symbol} for {date}...")
    logger.info(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Сохраняем ZIP
            zip_path = output_dir / f"{symbol}-1m-{date}.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            logger.success(f"✅ Downloaded: {zip_path}")
            
            # Распаковываем
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(output_dir)
            
            csv_path = output_dir / f"{symbol}-1m-{date}.csv"
            logger.success(f"✅ Extracted: {csv_path}")
            
            # Удаляем ZIP
            zip_path.unlink()
            
            return csv_path
            
        elif response.status_code == 404:
            logger.warning(f"⚠️  No data for {date} (weekend or future date)")
            return None
        else:
            logger.error(f"❌ HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return None


def load_csv_to_dataframe(csv_path: Path) -> pd.DataFrame:
    """Загрузить CSV в pandas DataFrame."""
    
    # Binance CSV columns (no header in file)
    columns = [
        'open_time',       # 0
        'open',            # 1
        'high',            # 2
        'low',             # 3
        'close',           # 4
        'volume',          # 5
        'close_time',      # 6
        'quote_volume',    # 7
        'trades',          # 8
        'taker_buy_base',  # 9
        'taker_buy_quote', # 10
        'ignore'           # 11
    ]
    
    df = pd.read_csv(csv_path, names=columns)
    
    # ВАЖНО: Binance 2025 использует МИКРОСЕКУНДЫ (не миллисекунды!)
    # Проверяем размер timestamp и конвертируем
    if df['open_time'].iloc[0] > 1e12:  # Если больше миллисекунд - это микросекунды
        df['open_time'] = df['open_time'] / 1000
        df['close_time'] = df['close_time'] / 1000
    
    # Конвертируем timestamp
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    
    # Переименовываем для совместимости с нашим кодом
    df = df.rename(columns={
        'open_time': 'open_time_ms'
    })
    
    # Конвертируем цены в float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def download_multiple_days(
    symbol: str,
    start_date: str,
    num_days: int = 7,
    output_dir: Path = None
) -> pd.DataFrame:
    """
    Скачать несколько дней данных и объединить в один DataFrame.
    
    Args:
        symbol: BTCUSDT, ETHUSDT, etc.
        start_date: Начальная дата YYYY-MM-DD
        num_days: Сколько дней скачать
        output_dir: Папка для сохранения (опционально)
    
    Returns:
        Combined DataFrame with all candles
    """
    if output_dir is None:
        output_dir = Path(__file__).parent / "data" / "binance_historical"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_data = []
    start = datetime.strptime(start_date, "%Y-%m-%d")
    
    for i in range(num_days):
        date = start + timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        csv_path = download_binance_klines(symbol, date_str, output_dir)
        
        if csv_path and csv_path.exists():
            df = load_csv_to_dataframe(csv_path)
            all_data.append(df)
            logger.info(f"Loaded {len(df)} candles from {date_str}")
        
        # Пауза между запросами (будь вежлив к серверу)
        time.sleep(1)
    
    if not all_data:
        logger.error("No data downloaded!")
        return pd.DataFrame()
    
    # Объединяем все дни
    combined = pd.concat(all_data, ignore_index=True)
    combined = combined.sort_values('timestamp').reset_index(drop=True)
    
    logger.success(f"\n✅ Total candles: {len(combined)}")
    logger.info(f"Period: {combined['timestamp'].min()} → {combined['timestamp'].max()}")
    
    # Сохраняем объединённый файл
    output_file = output_dir / f"{symbol}_historical_{start_date}_to_{num_days}days.csv"
    combined.to_csv(output_file, index=False)
    logger.success(f"💾 Saved to: {output_file}")
    
    return combined


def main():
    """Пример использования."""
    
    logger.info("=" * 60)
    logger.info("📥 BINANCE HISTORICAL DATA DOWNLOADER")
    logger.info("=" * 60)
    logger.info("FREE - No API keys needed!")
    logger.info("Source: https://data.binance.vision/")
    logger.info("")
    
    # Скачиваем последние 7 дней BTC/USDT
    # (используй даты из прошлого, не будущего!)
    symbol = "BTCUSDT"
    start_date = "2025-10-01"  # АКТУАЛЬНО! Октябрь 2025 (30 дней до сегодня)
    num_days = 30  # 30 дней для репрезентативной выборки
    
    df = download_multiple_days(symbol, start_date, num_days)
    
    if not df.empty:
        logger.info("\n📊 Sample data:")
        print(df.head(10))
        print("\n" + "=" * 60)
        logger.success("✅ Download complete! Ready for backtesting.")
        logger.info("\nNext: Run backtest with this data")
        logger.info("File: data/binance_historical/BTCUSDT_historical_*.csv")


if __name__ == "__main__":
    main()
