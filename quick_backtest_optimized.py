#!/usr/bin/env python3
"""
Quick backtest with optimized parameters.
Tests RSI 30/70, EMA 12/26 on synthetic 2025 data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from yunmin.core.backtester import AdvancedBacktester
from yunmin.strategy.ema_crossover import EMACrossoverStrategy


def generate_synthetic_btc_data(periods: int = 90000) -> pd.DataFrame:
    """
    Generate synthetic BTC price data similar to 2025 market conditions.
    
    Jan-Nov 2025: ~90,000 5-minute candles
    Price range: $40,000 - $110,000 with realistic volatility
    """
    logger.info("📊 Generating synthetic BTC data (90,000 candles)...")
    
    # Start from Jan 1, 2025
    start_date = datetime(2025, 1, 1)
    dates = [start_date + timedelta(minutes=5*i) for i in range(periods)]
    
    # Generate realistic price movement
    # Base price with uptrend: $40k → $110k over 10 months
    base_prices = np.linspace(40000, 110000, periods)
    
    # Add volatility: ±2% per candle with random walk
    np.random.seed(42)  # Reproducible results
    volatility = np.random.randn(periods) * 0.02
    cumulative_volatility = np.cumsum(volatility)
    prices = base_prices * (1 + cumulative_volatility * 0.1)
    
    # Generate OHLCV
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        # Intrabar volatility ±0.5%
        high = price * (1 + abs(np.random.randn()) * 0.005)
        low = price * (1 - abs(np.random.randn()) * 0.005)
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        
        # Volume: realistic range 100-500 BTC per 5m candle
        volume = np.random.uniform(100, 500)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    logger.success(f"✓ Generated {len(df)} candles from {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df


def run_backtest(data: pd.DataFrame) -> dict:
    """Run backtest with optimized parameters."""
    logger.info("=" * 70)
    logger.info("🚀 RUNNING BACKTEST WITH OPTIMIZED PARAMETERS")
    logger.info("=" * 70)
    
    # Strategy with OPTIMIZED parameters
    strategy = EMACrossoverStrategy(
        fast_period=12,  # Optimized (was 9)
        slow_period=26,  # Optimized (was 21)
        rsi_period=14,
        rsi_overbought=70,  # Optimized (was 65)
        rsi_oversold=30     # Optimized (was 35)
    )
    
    logger.info(f"Strategy: {strategy.name}")
    logger.info(f"Parameters: {strategy.get_params()}")
    
    # Backtester
    backtester = AdvancedBacktester(
        symbol="BTC/USDT",
        timeframe="5m"
    )
    
    # Run backtest
    logger.info("\n⏳ Running backtest...")
    results = backtester.run(
        strategy=strategy,
        data=data,
        initial_capital=10000.0,
        commission=0.001,  # 0.1% fee
        slippage=0.0005    # 0.05% slippage
    )
    
    return results


def print_results(results: dict):
    """Print formatted results."""
    metrics = results['metrics']
    
    logger.info("\n" + "=" * 70)
    logger.info("📊 BACKTEST RESULTS")
    logger.info("=" * 70)
    
    # Performance metrics
    win_rate = metrics['win_rate'] * 100
    total_pnl = metrics['total_pnl']
    final_capital = results['final_capital']
    roi = (final_capital / results['initial_capital'] - 1) * 100
    
    logger.info("\n💰 PERFORMANCE:")
    logger.info(f"  Initial Capital:  ${results['initial_capital']:,.2f}")
    logger.info(f"  Final Capital:    ${final_capital:,.2f}")
    logger.info(f"  Total P&L:        ${total_pnl:,.2f}")
    logger.info(f"  ROI:              {roi:+.2f}%")
    
    # Trade statistics
    logger.info("\n📈 TRADE STATISTICS:")
    logger.info(f"  Total Trades:     {metrics['total_trades']}")
    logger.info(f"  Winning Trades:   {metrics['winning_trades']}")
    logger.info(f"  Losing Trades:    {metrics['losing_trades']}")
    logger.info(f"  Win Rate:         {win_rate:.2f}%")
    logger.info(f"  Avg Win:          ${metrics['avg_win']:.2f}")
    logger.info(f"  Avg Loss:         ${metrics['avg_loss']:.2f}")
    logger.info(f"  Expectancy:       ${metrics['expectancy']:.2f}")
    
    # Risk metrics
    logger.info("\n⚠️  RISK METRICS:")
    logger.info(f"  Max Drawdown:     {metrics['max_drawdown']*100:.2f}%")
    logger.info(f"  Sharpe Ratio:     {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  Sortino Ratio:    {metrics['sortino_ratio']:.2f}")
    logger.info(f"  Profit Factor:    {metrics['profit_factor']:.2f}")
    logger.info(f"  Calmar Ratio:     {metrics.get('calmar_ratio', 0):.2f}")
    
    # Acceptance criteria
    logger.info("\n✅ ACCEPTANCE CRITERIA:")
    if win_rate >= 45:
        logger.success(f"  ✓ Win Rate: {win_rate:.1f}% (target ≥45%)")
    else:
        logger.warning(f"  ✗ Win Rate: {win_rate:.1f}% (target ≥45%)")
    
    if metrics['max_drawdown'] <= 0.20:
        logger.success(f"  ✓ Max Drawdown: {metrics['max_drawdown']*100:.1f}% (target ≤20%)")
    else:
        logger.warning(f"  ✗ Max Drawdown: {metrics['max_drawdown']*100:.1f}% (target ≤20%)")
    
    if metrics['sharpe_ratio'] >= 1.0:
        logger.success(f"  ✓ Sharpe Ratio: {metrics['sharpe_ratio']:.2f} (target ≥1.0)")
    else:
        logger.warning(f"  ✗ Sharpe Ratio: {metrics['sharpe_ratio']:.2f} (target ≥1.0)")


def main():
    """Main execution."""
    logger.info("\n" + "=" * 70)
    logger.info("QUICK BACKTEST WITH OPTIMIZED PARAMETERS")
    logger.info("RSI 30/70, EMA 12/26 (Grid Search Best Results)")
    logger.info("=" * 70 + "\n")
    
    # Generate data
    data = generate_synthetic_btc_data(periods=90000)
    
    # Run backtest
    results = run_backtest(data)
    
    # Print results
    print_results(results)
    
    # Save results
    import json
    with open('backtest_optimized_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    logger.success("\n💾 Results saved to: backtest_optimized_results.json")
    
    # Compare with old results
    logger.info("\n" + "=" * 70)
    logger.info("📊 COMPARISON WITH OLD PARAMETERS")
    logger.info("=" * 70)
    logger.info("OLD (RSI 35/70, EMA 9/21):  7% win rate, -$9,987 P&L, 99.88% DD")
    logger.info(f"NEW (RSI 30/70, EMA 12/26): {results['metrics']['win_rate']*100:.1f}% win rate, ${results['metrics']['total_pnl']:,.2f} P&L, {results['metrics']['max_drawdown']*100:.2f}% DD")
    
    improvement = ((results['metrics']['win_rate'] - 0.0705) / 0.0705) * 100
    logger.info(f"\n🎯 Win rate improvement: +{improvement:.1f}%")


if __name__ == "__main__":
    main()
