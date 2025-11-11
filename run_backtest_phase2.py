#!/usr/bin/env python3
"""
Phase 2 Backtest Script - Tests GrokAIStrategy with advanced indicators

This runs backtest using:
- GrokAIStrategy (Phase 2 implementation)
- Advanced indicators (MACD, Bollinger, ATR, OBV, Ichimoku)
- Hybrid mode (classical + AI)
- Relaxed entry thresholds

Expected improvements over Phase 1:
- Win Rate: 40%+ (was 0%)
- Trading frequency: 15-20% (was 4%)
- Max Drawdown: <15% (was 99%)
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

from yunmin.core.backtester import AdvancedBacktester
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.core.config import Config


def load_historical_data(file_path: str) -> pd.DataFrame:
    """Load BTC/USDT 5m data from CSV"""
    logger.info(f"Loading historical data from {file_path}...")
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    logger.info(f"✓ Loaded {len(df)} candles")
    return df


def run_phase2_backtest():
    """Run Phase 2 backtest"""
    logger.info("=" * 80)
    logger.info("🚀 PHASE 2 BACKTEST - GrokAIStrategy with Advanced Indicators")
    logger.info("=" * 80)
    logger.info("")
    
    # Load configuration
    config = Config.load("config/default.yaml")
    
    # Check if we have historical data
    data_file = Path("data/historical/btc_usdt_5m_2025.csv")
    if not data_file.exists():
        logger.warning("⚠️ Historical data not found. Please run: python run_backtest_2025.py first")
        logger.info("This will download 2025 data from Binance and save it")
        return
    
    # Load data
    df = load_historical_data(str(data_file))
    
    logger.info("")
    logger.info(f"Period: {df.index[0]} to {df.index[-1]}")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    logger.info("")
    
    # Initialize strategy (GrokAIStrategy with Phase 2 enhancements)
    logger.info("Initializing Phase 2 Strategy...")
    strategy = GrokAIStrategy(
        grok_analyzer=None,  # Use fallback (no LLM needed for this test)
        use_advanced_indicators=True,  # Phase 2.3: Enable MACD, BB, ATR, OBV, Ichimoku
        hybrid_mode=True  # Phase 2.2: Enable voting system
    )
    logger.info("✓ Strategy initialized with Phase 2 enhancements")
    logger.info("  - Advanced indicators: ENABLED")
    logger.info("  - Hybrid mode (classical + voting): ENABLED")
    logger.info("  - RSI oversold: 35 (was 30)")
    logger.info("  - RSI overbought: 65 (was 70)")
    logger.info("  - Volume multiplier: 1.2x (was 1.5x)")
    logger.info("")
    
    # Run backtest
    logger.info("Running backtest...")
    backtester = AdvancedBacktester(
        strategy=strategy,
        initial_capital=10000,
        commission=0.001,  # 0.1%
        slippage=0.0005  # 0.05%
    )
    
    results = backtester.run(df)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 PHASE 2 BACKTEST RESULTS")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Initial Capital:    ${results['initial_capital']:,.2f}")
    logger.info(f"Final Capital:      ${results['final_capital']:,.2f}")
    logger.info(f"P&L:                ${results['pnl']:,.2f} ({results['return_pct']:.2f}%)")
    logger.info("")
    
    logger.info("Performance Metrics:")
    logger.info(f"  Win Rate:         {results['win_rate']:.2f}% (Target: >40%)")
    logger.info(f"  Profit Factor:    {results['profit_factor']:.4f} (Target: >1.5)")
    logger.info(f"  Max Drawdown:     {results['max_drawdown']:.2f}% (Target: <15%)")
    logger.info(f"  Sharpe Ratio:     {results['sharpe_ratio']:.4f}")
    logger.info(f"  Sortino Ratio:    {results['sortino_ratio']:.4f}")
    logger.info("")
    
    logger.info("Trade Statistics:")
    logger.info(f"  Total Trades:     {results['total_trades']}")
    logger.info(f"  Winning Trades:   {results['num_wins']}")
    logger.info(f"  Losing Trades:    {results['num_losses']}")
    logger.info(f"  Avg Win:          ${results['avg_win']:.2f}")
    logger.info(f"  Avg Loss:         ${results['avg_loss']:.2f}")
    logger.info(f"  Expectancy:       ${results['expectancy']:.2f}")
    logger.info("")
    
    # Check acceptance criteria
    logger.info("=" * 80)
    logger.info("✅ ACCEPTANCE CRITERIA CHECK")
    logger.info("=" * 80)
    
    criteria_met = 0
    criteria_total = 4
    
    # Criterion 1: Win Rate > 40%
    if results['win_rate'] >= 40:
        logger.info(f"✅ Win Rate {results['win_rate']:.2f}% >= 40%")
        criteria_met += 1
    else:
        logger.warning(f"❌ Win Rate {results['win_rate']:.2f}% < 40%")
    
    # Criterion 2: Profit Factor > 1.5
    if results['profit_factor'] >= 1.5:
        logger.info(f"✅ Profit Factor {results['profit_factor']:.4f} >= 1.5")
        criteria_met += 1
    else:
        logger.warning(f"❌ Profit Factor {results['profit_factor']:.4f} < 1.5")
    
    # Criterion 3: Max Drawdown < 15%
    if results['max_drawdown'] <= 15:
        logger.info(f"✅ Max Drawdown {results['max_drawdown']:.2f}% <= 15%")
        criteria_met += 1
    else:
        logger.warning(f"❌ Max Drawdown {results['max_drawdown']:.2f}% > 15%")
    
    # Criterion 4: Positive P&L
    if results['pnl'] > 0:
        logger.info(f"✅ Positive P&L: ${results['pnl']:.2f}")
        criteria_met += 1
    else:
        logger.warning(f"❌ Negative P&L: ${results['pnl']:.2f}")
    
    logger.info("")
    logger.info(f"Criteria Met: {criteria_met}/{criteria_total}")
    logger.info("")
    
    if criteria_met == criteria_total:
        logger.success("🎉 ALL CRITERIA MET - PHASE 2 VALIDATED!")
    else:
        logger.warning(f"⚠️ {criteria_total - criteria_met} criteria not met - needs further optimization")
    
    # Save results
    results_file = Path("backtest_results_phase2.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to: {results_file}")
    
    return results


if __name__ == "__main__":
    try:
        results = run_phase2_backtest()
        if results:
            logger.success("Phase 2 backtest completed successfully!")
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
