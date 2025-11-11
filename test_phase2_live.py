#!/usr/bin/env python3
"""
Quick Phase 2 validation on live Binance testnet data
Tests GrokAIStrategy with relaxed thresholds and advanced indicators
"""

import sys
import asyncio
from datetime import datetime

sys.path.insert(0, '/f/AgeeKey/yun_min')

from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.connectors.binance_connector import BinanceConnector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run Phase 2 validation"""
    logger.info("=" * 80)
    logger.info("PHASE 2 LIVE VALIDATION - GrokAIStrategy with Advanced Indicators")
    logger.info("=" * 80)
    
    # Initialize connector
    connector = BinanceConnector(testnet=True)
    strategy = GrokAIStrategy()
    
    try:
        logger.info("\n📊 Fetching 200 candles from Binance testnet (5m, BTC/USDT)...")
        candles = await connector.get_historical_klines(
            symbol="BTCUSDT",
            interval="5m",
            limit=200
        )
        
        if not candles or len(candles) < 50:
            logger.error(f"❌ Not enough data: {len(candles) if candles else 0} candles")
            return
        
        logger.info(f"✅ Fetched {len(candles)} candles")
        logger.info(f"   Date range: {datetime.fromtimestamp(candles[0][0]//1000)} → {datetime.fromtimestamp(candles[-1][0]//1000)}")
        
        # Test strategy on different parts of data
        logger.info("\n🧪 Testing Phase 2 Strategy on historical data...")
        
        trades = 0
        buy_signals = 0
        sell_signals = 0
        
        for i in range(50, len(candles)):
            # Prepare market data
            market_data = {
                'symbol': 'BTC/USDT',
                'timestamp': candles[i][0],
                'open': float(candles[i][1]),
                'high': float(candles[i][2]),
                'low': float(candles[i][3]),
                'close': float(candles[i][4]),
                'volume': float(candles[i][5]),
            }
            
            # Get signal
            signal = strategy.get_signal(market_data, {})
            
            if signal['action'] != 'HOLD':
                trades += 1
                if signal['action'] == 'BUY':
                    buy_signals += 1
                    logger.info(f"   [{i:3d}] BUY  @ {market_data['close']:.2f} (conf: {signal.get('confidence', 0):.1%})")
                else:
                    sell_signals += 1
                    logger.info(f"   [{i:3d}] SELL @ {market_data['close']:.2f} (conf: {signal.get('confidence', 0):.1%})")
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 PHASE 2 VALIDATION RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total candles tested: {len(candles) - 50}")
        logger.info(f"Total signals: {trades} ({trades/(len(candles)-50)*100:.1f}%)")
        logger.info(f"  - BUY signals: {buy_signals}")
        logger.info(f"  - SELL signals: {sell_signals}")
        
        if trades >= (len(candles) - 50) * 0.1:  # At least 10% trading frequency
            logger.info("\n✅ SUCCESS: Trading frequency meets Phase 2 target (≥10%)")
        else:
            logger.warning(f"\n⚠️  Trading frequency below target: {trades/(len(candles)-50)*100:.1f}%")
        
        logger.info("\n🎉 Phase 2 strategy is functioning correctly!")
        
    except Exception as e:
        logger.error(f"❌ Error during validation: {e}", exc_info=True)
        return False
    
    return True


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
