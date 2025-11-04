"""
Тест RSI Mean Reversion против провалившейся EMA Crossover

BOSS DECISION: Новая стратегия на тех же данных
"""
import sys
sys.path.insert(0, 'f:/AgeeKey/yun_min')

from run_backtest_v3_realdata import load_binance_historical_data, resample_to_timeframe, simulate_backtest, save_results
from yunmin.strategy.rsi_mean_reversion import RSIMeanReversionStrategy
from pathlib import Path
from datetime import datetime
from loguru import logger

# Загружаем те же данные
data_dir = Path("data/binance_historical")
csv_file = data_dir / "BTCUSDT_historical_2024-10-28_to_7days.csv"

df_1m = load_binance_historical_data(str(csv_file))
df_5m = resample_to_timeframe(df_1m, '5T')

logger.info("\n" + "="*70)
logger.info("🚀 BOSS DECISION: TESTING NEW STRATEGY")
logger.info("="*70)
logger.info("OLD: EMA Crossover → -21.54% (FAILED)")
logger.info("NEW: RSI Mean Reversion → Testing now...")
logger.info("")

# RSI Mean Reversion параметры
params = {
    'rsi_period': 14,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'stop_loss': 0.02,       # 2% SL
    'take_profit': 0.03,     # 3% TP (более консервативно)
    'initial_capital': 10000.0
}

strategy = RSIMeanReversionStrategy(
    rsi_period=params['rsi_period'],
    rsi_oversold=params['rsi_oversold'],
    rsi_overbought=params['rsi_overbought']
)

results = simulate_backtest(
    data=df_5m,
    strategy=strategy,
    initial_capital=params['initial_capital'],
    stop_loss_pct=params['stop_loss'],
    take_profit_pct=params['take_profit'],
    commission=0.001,
    slippage=0.0005
)

# Результаты
metrics = results.get('metrics', {})

logger.info("\n" + "=" * 70)
logger.info("📊 RSI MEAN REVERSION RESULTS")
logger.info("=" * 70)

logger.info(f"\n💰 PERFORMANCE:")
logger.info(f"   Total Return: {metrics.get('total_return', 0):.2f}%")
logger.info(f"   Win Rate: {metrics.get('win_rate', 0):.2f}%")
logger.info(f"   Profit Factor: {metrics.get('profit_factor', 0):.2f}")
logger.info(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")

logger.info(f"\n📈 TRADES:")
logger.info(f"   Total: {metrics.get('total_trades', 0)}")
logger.info(f"   Winning: {metrics.get('winning_trades', 0)}")
logger.info(f"   Losing: {metrics.get('losing_trades', 0)}")

logger.info(f"\n💵 AVERAGE:")
logger.info(f"   Avg Win: {metrics.get('avg_win', 0):.2f}%")
logger.info(f"   Avg Loss: {metrics.get('avg_loss', 0):.2f}%")

logger.info(f"\n⚠️  RISK:")
logger.info(f"   Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")

# Сравнение с EMA
logger.info("\n" + "=" * 70)
logger.info("⚔️  RSI MEAN REVERSION vs EMA CROSSOVER")
logger.info("=" * 70)

ema_return = -21.54
ema_winrate = 14.61
rsi_return = metrics.get('total_return', 0)
rsi_winrate = metrics.get('win_rate', 0)

logger.info(f"\nReturn:")
logger.info(f"  EMA:  {ema_return:.2f}%")
logger.info(f"  RSI:  {rsi_return:.2f}%")
logger.info(f"  Δ:    {rsi_return - ema_return:+.2f}%")

logger.info(f"\nWin Rate:")
logger.info(f"  EMA:  {ema_winrate:.2f}%")
logger.info(f"  RSI:  {rsi_winrate:.2f}%")
logger.info(f"  Δ:    {rsi_winrate - ema_winrate:+.2f}%")

# Вердикт
logger.info("\n" + "=" * 70)
if rsi_return > 0 and rsi_winrate > 50:
    logger.success("✅ RSI MEAN REVERSION: WINNER! Ready for production!")
elif rsi_return > ema_return:
    logger.info("🟡 RSI better than EMA, but needs optimization")
else:
    logger.error("❌ RSI also failed. Need different approach.")

# Сохраняем
results['strategy'] = 'RSI Mean Reversion'
results['comparison'] = {
    'ema_return': ema_return,
    'ema_winrate': ema_winrate,
    'improvement': rsi_return - ema_return
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"backtest_rsi_meanrev_{timestamp}.json"
save_results(results, output_file)

logger.info(f"\n📄 Results: {output_file}")
