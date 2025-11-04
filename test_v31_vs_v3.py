"""
Тест V3.1 (AI-оптимизированной) vs V3 (оригинальной)
"""
import sys
sys.path.insert(0, 'f:/AgeeKey/yun_min')

from run_backtest_v3_realdata import load_binance_historical_data, resample_to_timeframe, run_backtest_with_params, save_results
from yunmin.strategy.ema_crossover_v31 import EMACrossoverV31Strategy
import pandas as pd
from pathlib import Path
from datetime import datetime
from loguru import logger

# Загружаем данные
data_dir = Path("data/binance_historical")
csv_file = data_dir / "BTCUSDT_historical_2024-10-28_to_7days.csv"

df_1m = load_binance_historical_data(str(csv_file))
df_5m = resample_to_timeframe(df_1m, '5T')

# Параметры V3.1 (AI-оптимизированные)
params_v31 = {
    'fast_ema': 12,          # AI: 9 → 12
    'slow_ema': 21,
    'rsi_period': 14,
    'rsi_overbought': 65.0,  # AI: 70 → 65
    'rsi_oversold': 30.0,
    'stop_loss': 0.015,      # AI: 2% → 1.5%
    'take_profit': 0.04,
    'initial_capital': 10000.0
}

logger.info("\n" + "="*70)
logger.info("🤖 TESTING V3.1 (AI-OPTIMIZED)")
logger.info("="*70)
logger.info("Changes:")
logger.info("  - Fast EMA: 9 → 12 (less noise)")
logger.info("  - RSI Overbought: 70 → 65 (more LONG signals)")
logger.info("  - Added EMA50 trend filter")
logger.info("  - Stop Loss: 2% → 1.5% (faster exits)")
logger.info("")

# Запускаем бэктест с V3.1
from run_backtest_v3_realdata import simulate_backtest

strategy_v31 = EMACrossoverV31Strategy(
    fast_period=params_v31['fast_ema'],
    slow_period=params_v31['slow_ema'],
    rsi_period=params_v31['rsi_period'],
    rsi_overbought=params_v31['rsi_overbought'],
    rsi_oversold=params_v31['rsi_oversold']
)

results_v31 = simulate_backtest(
    data=df_5m,
    strategy=strategy_v31,
    initial_capital=params_v31['initial_capital'],
    stop_loss_pct=params_v31['stop_loss'],
    take_profit_pct=params_v31['take_profit'],
    commission=0.001,
    slippage=0.0005
)

# Выводим результаты
logger.info("\n" + "=" * 70)
logger.info("📊 V3.1 BACKTEST RESULTS")
logger.info("=" * 70)

metrics = results_v31.get('metrics', {})

logger.info(f"\n💰 PERFORMANCE:")
logger.info(f"   Total Return: {metrics.get('total_return', 0):.2f}%")
logger.info(f"   Win Rate: {metrics.get('win_rate', 0):.2f}%")
logger.info(f"   Profit Factor: {metrics.get('profit_factor', 0):.2f}")
logger.info(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")

logger.info(f"\n📈 TRADES:")
logger.info(f"   Total Trades: {metrics.get('total_trades', 0)}")
logger.info(f"   Winning: {metrics.get('winning_trades', 0)}")
logger.info(f"   Losing: {metrics.get('losing_trades', 0)}")

logger.info(f"\n💵 AVERAGE:")
logger.info(f"   Avg Win: {metrics.get('avg_win', 0):.2f}%")
logger.info(f"   Avg Loss: {metrics.get('avg_loss', 0):.2f}%")

logger.info(f"\n⚠️  RISK:")
logger.info(f"   Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")

# Сравнение с V3
logger.info("\n" + "=" * 70)
logger.info("📊 COMPARISON: V3.1 vs V3")
logger.info("=" * 70)

v3_return = -21.54
v3_winrate = 14.61
v3_trades = 89

v31_return = metrics.get('total_return', 0)
v31_winrate = metrics.get('win_rate', 0)
v31_trades = metrics.get('total_trades', 0)

logger.info(f"\nReturn:")
logger.info(f"  V3:   {v3_return:.2f}%")
logger.info(f"  V3.1: {v31_return:.2f}%")
logger.info(f"  Δ:    {v31_return - v3_return:+.2f}%")

logger.info(f"\nWin Rate:")
logger.info(f"  V3:   {v3_winrate:.2f}%")
logger.info(f"  V3.1: {v31_winrate:.2f}%")
logger.info(f"  Δ:    {v31_winrate - v3_winrate:+.2f}%")

logger.info(f"\nTrades:")
logger.info(f"  V3:   {v3_trades}")
logger.info(f"  V3.1: {v31_trades}")
logger.info(f"  Δ:    {v31_trades - v3_trades:+d}")

# Сохраняем результаты
results_v31['strategy'] = 'EMA Crossover V3.1 (AI-Optimized)'
results_v31['data_source'] = 'Binance Historical (Real Market Data)'
results_v31['period'] = f"{df_5m.index[0]} to {df_5m.index[-1]}"
results_v31['timeframe'] = '5m'
results_v31['parameters'] = params_v31
results_v31['ai_changes'] = [
    'Fast EMA: 9 → 12',
    'RSI Overbought: 70 → 65', 
    'Added EMA50 trend filter',
    'Stop Loss: 2% → 1.5%'
]

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"backtest_v31_realdata_{timestamp}.json"
save_results(results_v31, output_file)

logger.info(f"\n✅ V3.1 backtest complete!")
logger.info(f"📄 Results: {output_file}")
