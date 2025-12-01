#!/usr/bin/env python3
"""Simple backtest to test optimized parameters."""

from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.core.backtester import AdvancedBacktester
import pandas as pd
import numpy as np

# Generate simple synthetic data
np.random.seed(42)
periods = 5000  # 5000 candles = ~17 days of 5m data

data = pd.DataFrame({
    'timestamp': pd.date_range('2025-01-01', periods=periods, freq='5min'),
    'open': 50000 + np.random.randn(periods).cumsum() * 100,
    'high': 50100 + np.random.randn(periods).cumsum() * 100,
    'low': 49900 + np.random.randn(periods).cumsum() * 100,
    'close': 50000 + np.random.randn(periods).cumsum() * 100,
    'volume': np.random.randint(100, 500, periods)
})

# Ensure high/low are correct
data['high'] = data[['open', 'high', 'low', 'close']].max(axis=1)
data['low'] = data[['open', 'high', 'low', 'close']].min(axis=1)

print("=" * 70)
print("SIMPLE BACKTEST - OPTIMIZED PARAMETERS")
print("RSI 30/70, EMA 12/26")
print("=" * 70)
print(f"\nData: {len(data)} candles")
print(f"Period: {data['timestamp'].iloc[0]} to {data['timestamp'].iloc[-1]}")
print(f"Price range: ${data['close'].min():.2f} - ${data['close'].max():.2f}")

# Run backtest with optimized parameters
strategy = EMACrossoverStrategy(
    fast_period=12,  # OPTIMIZED
    slow_period=26,  # OPTIMIZED
    rsi_oversold=30,  # OPTIMIZED
    rsi_overbought=70  # OPTIMIZED
)

print(f"\nStrategy: {strategy.name}")
print(f"Parameters: {strategy.get_params()}")

backtester = AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
result = backtester.run(strategy, data, initial_capital=10000.0)

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
print(f"Win Rate:       {result.metrics['win_rate']*100:.2f}%")
print(f"Total Trades:   {result.metrics['total_trades']}")
print(f"Winning:        {result.metrics['winning_trades']}")
print(f"Losing:         {result.metrics['losing_trades']}")
print(f"Total P&L:      ${result.metrics['total_pnl']:,.2f}")
print(f"Final Capital:  ${result.final_capital:,.2f}")
print(f"ROI:            {(result.final_capital/10000-1)*100:+.2f}%")
print(f"Max Drawdown:   {result.metrics['max_drawdown']*100:.2f}%")
print(f"Sharpe Ratio:   {result.metrics['sharpe_ratio']:.2f}")
print(f"Profit Factor:  {result.metrics['profit_factor']:.2f}")

print("\n" + "=" * 70)
print("COMPARISON")
print("=" * 70)
print("OLD (RSI 35/70, EMA 9/21):  7% win rate, -$9,987 loss")
print(f"NEW (RSI 30/70, EMA 12/26): {result.metrics['win_rate']*100:.1f}% win rate, ${result.metrics['total_pnl']:,.2f}")
print("=" * 70)
