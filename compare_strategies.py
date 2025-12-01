#!/usr/bin/env python3
"""
Compare Basic vs Enhanced EMA Crossover Strategy

Tests both strategies on same data to measure improvement from:
- ATR-based stops
- Trailing stop
- ADX market regime filter
"""

from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.strategy.ema_crossover_enhanced import EMACrossoverEnhanced
from yunmin.core.backtester import AdvancedBacktester
import pandas as pd
import numpy as np

print("=" * 80)
print("STRATEGY COMPARISON: BASIC vs ENHANCED")
print("=" * 80)

# Generate realistic test data
np.random.seed(42)
periods = 10000  # ~35 days of 5m data

# Create realistic BTC price action with trends and ranges
base_price = 50000
prices = [base_price]

for i in range(1, periods):
    # Add trending and ranging periods
    if i % 1000 < 700:  # 70% trending
        trend = 0.0002 if (i // 1000) % 2 == 0 else -0.0002
        volatility = 0.001
    else:  # 30% ranging
        trend = 0
        volatility = 0.0005
    
    change = trend + np.random.randn() * volatility
    new_price = prices[-1] * (1 + change)
    prices.append(new_price)

# Build OHLCV dataframe
data = pd.DataFrame({
    'timestamp': pd.date_range('2025-01-01', periods=periods, freq='5min'),
    'close': prices
})

# Generate OHLC from close
data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
data['high'] = data[['open', 'close']].max(axis=1) * (1 + abs(np.random.randn(periods)) * 0.002)
data['low'] = data[['open', 'close']].min(axis=1) * (1 - abs(np.random.randn(periods)) * 0.002)
data['volume'] = np.random.randint(100, 500, periods)

print(f"\nTest Data:")
print(f"  Periods: {len(data)} candles (~{len(data)*5/60/24:.1f} days)")
print(f"  Date range: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")
print(f"  Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
print(f"  Price change: {((data['close'].iloc[-1]/data['close'].iloc[0]-1)*100):+.2f}%")

# Test 1: Basic Strategy
print("\n" + "=" * 80)
print("TEST 1: BASIC STRATEGY (Original)")
print("=" * 80)

strategy_basic = EMACrossoverStrategy(
    fast_period=12,
    slow_period=26,
    rsi_overbought=70,
    rsi_oversold=30
)

backtester = AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
result_basic = backtester.run(strategy_basic, data, initial_capital=10000.0)

print(f"\nResults:")
print(f"  Win Rate:       {result_basic.metrics['win_rate']*100:.2f}%")
print(f"  Total Trades:   {result_basic.metrics['total_trades']}")
print(f"  Winning:        {result_basic.metrics['winning_trades']}")
print(f"  Losing:         {result_basic.metrics['losing_trades']}")
print(f"  Total P&L:      ${result_basic.metrics['total_pnl']:,.2f}")
print(f"  Final Capital:  ${result_basic.final_capital:,.2f}")
print(f"  ROI:            {(result_basic.final_capital/10000-1)*100:+.2f}%")
print(f"  Max Drawdown:   {result_basic.metrics['max_drawdown']*100:.2f}%")
print(f"  Sharpe Ratio:   {result_basic.metrics['sharpe_ratio']:.2f}")
print(f"  Profit Factor:  {result_basic.metrics['profit_factor']:.2f}")

# Test 2: Enhanced Strategy
print("\n" + "=" * 80)
print("TEST 2: ENHANCED STRATEGY (ATR stops + Trailing + ADX filter)")
print("=" * 80)

strategy_enhanced = EMACrossoverEnhanced(
    fast_period=12,
    slow_period=26,
    rsi_overbought=70,
    rsi_oversold=30,
    atr_period=14,
    atr_stop_multiplier=2.0,
    trailing_stop_activation=0.02,
    trailing_stop_distance=1.5,
    adx_period=14,
    adx_threshold=25.0,
    use_adx_filter=True
)

result_enhanced = backtester.run(strategy_enhanced, data, initial_capital=10000.0)

print(f"\nResults:")
print(f"  Win Rate:       {result_enhanced.metrics['win_rate']*100:.2f}%")
print(f"  Total Trades:   {result_enhanced.metrics['total_trades']}")
print(f"  Winning:        {result_enhanced.metrics['winning_trades']}")
print(f"  Losing:         {result_enhanced.metrics['losing_trades']}")
print(f"  Total P&L:      ${result_enhanced.metrics['total_pnl']:,.2f}")
print(f"  Final Capital:  ${result_enhanced.final_capital:,.2f}")
print(f"  ROI:            {(result_enhanced.final_capital/10000-1)*100:+.2f}%")
print(f"  Max Drawdown:   {result_enhanced.metrics['max_drawdown']*100:.2f}%")
print(f"  Sharpe Ratio:   {result_enhanced.metrics['sharpe_ratio']:.2f}")
print(f"  Profit Factor:  {result_enhanced.metrics['profit_factor']:.2f}")

# Comparison
print("\n" + "=" * 80)
print("IMPROVEMENT ANALYSIS")
print("=" * 80)

wr_improvement = (result_enhanced.metrics['win_rate'] - result_basic.metrics['win_rate']) * 100
pnl_improvement = result_enhanced.metrics['total_pnl'] - result_basic.metrics['total_pnl']
dd_improvement = (result_basic.metrics['max_drawdown'] - result_enhanced.metrics['max_drawdown']) * 100
sharpe_improvement = result_enhanced.metrics['sharpe_ratio'] - result_basic.metrics['sharpe_ratio']

print(f"\nWin Rate:       {result_basic.metrics['win_rate']*100:.2f}% → {result_enhanced.metrics['win_rate']*100:.2f}% ({wr_improvement:+.2f}pp)")
print(f"Total P&L:      ${result_basic.metrics['total_pnl']:,.2f} → ${result_enhanced.metrics['total_pnl']:,.2f} (${pnl_improvement:+,.2f})")
print(f"Max Drawdown:   {result_basic.metrics['max_drawdown']*100:.2f}% → {result_enhanced.metrics['max_drawdown']*100:.2f}% ({dd_improvement:+.2f}pp)")
print(f"Sharpe Ratio:   {result_basic.metrics['sharpe_ratio']:.2f} → {result_enhanced.metrics['sharpe_ratio']:.2f} ({sharpe_improvement:+.2f})")
print(f"Trade Count:    {result_basic.metrics['total_trades']} → {result_enhanced.metrics['total_trades']} ({result_enhanced.metrics['total_trades']-result_basic.metrics['total_trades']:+d})")

print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)
print("\n✅ Enhanced Strategy Benefits:")
print("  • ATR-based stops adapt to market volatility")
print("  • Trailing stop protects profits in strong moves")
print("  • ADX filter avoids choppy ranging markets")
print("  • Fewer but higher-quality trades")

if result_enhanced.metrics['win_rate'] > result_basic.metrics['win_rate']:
    print(f"\n🎯 Win rate improved by {wr_improvement:.1f} percentage points")
if result_enhanced.metrics['total_pnl'] > result_basic.metrics['total_pnl']:
    print(f"💰 Profit improved by ${pnl_improvement:,.2f}")
if result_enhanced.metrics['max_drawdown'] < result_basic.metrics['max_drawdown']:
    print(f"⚡ Drawdown reduced by {dd_improvement:.1f} percentage points")
if result_enhanced.metrics['sharpe_ratio'] > result_basic.metrics['sharpe_ratio']:
    print(f"📈 Sharpe ratio improved by {sharpe_improvement:.2f}")

print("\n" + "=" * 80)
