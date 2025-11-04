"""
BOSS FINAL DECISION: RSI Mean Reversion V2 - ULTIMATE

Problems with V1:
- Avg Loss -0.61% > Avg Win 0.35%
- Total Return: -11.64%

V2 Improvements:
- Tighter Stop Loss: 2% → 1%
- Higher Take Profit: 3% → 2%  
- Better risk/reward ratio: 1:2
"""
import sys
sys.path.insert(0, 'f:/AgeeKey/yun_min')

from run_backtest_v3_realdata import load_binance_historical_data, resample_to_timeframe, simulate_backtest, save_results
from yunmin.strategy.rsi_mean_reversion import RSIMeanReversionStrategy
from pathlib import Path
from datetime import datetime
from loguru import logger

# Данные
data_dir = Path("data/binance_historical")
csv_file = data_dir / "BTCUSDT_historical_2024-10-28_to_7days.csv"
df_1m = load_binance_historical_data(str(csv_file))
df_5m = resample_to_timeframe(df_1m, '5T')

logger.info("\n" + "="*70)
logger.info("🔥 BOSS ULTIMATE DECISION: RSI V2")
logger.info("="*70)
logger.info("V1: -11.64%, Avg Loss -0.61% > Avg Win 0.35%")
logger.info("V2: Tighter SL (1%), Better TP (2%), Risk:Reward 1:2")
logger.info("")

# ULTIMATE параметры
params_v2 = {
    'rsi_period': 14,
    'rsi_oversold': 25,      # Более экстремальный (30 → 25)
    'rsi_overbought': 75,    # Более экстремальный (70 → 75)
    'stop_loss': 0.01,       # TIGHTER: 2% → 1%
    'take_profit': 0.02,     # BETTER: 3% → 2%
    'initial_capital': 10000.0
}

strategy_v2 = RSIMeanReversionStrategy(
    rsi_period=params_v2['rsi_period'],
    rsi_oversold=params_v2['rsi_oversold'],
    rsi_overbought=params_v2['rsi_overbought']
)

results_v2 = simulate_backtest(
    data=df_5m,
    strategy=strategy_v2,
    initial_capital=params_v2['initial_capital'],
    stop_loss_pct=params_v2['stop_loss'],
    take_profit_pct=params_v2['take_profit'],
    commission=0.001,
    slippage=0.0005
)

metrics_v2 = results_v2.get('metrics', {})

logger.info("\n" + "=" * 70)
logger.info("📊 RSI V2 ULTIMATE RESULTS")
logger.info("=" * 70)

logger.info(f"\n💰 PERFORMANCE:")
logger.info(f"   Total Return: {metrics_v2.get('total_return', 0):.2f}%")
logger.info(f"   Win Rate: {metrics_v2.get('win_rate', 0):.2f}%")
logger.info(f"   Profit Factor: {metrics_v2.get('profit_factor', 0):.2f}")

logger.info(f"\n📈 TRADES:")
logger.info(f"   Total: {metrics_v2.get('total_trades', 0)}")
logger.info(f"   Winning: {metrics_v2.get('winning_trades', 0)}")
logger.info(f"   Losing: {metrics_v2.get('losing_trades', 0)}")

logger.info(f"\n💵 RISK/REWARD:")
logger.info(f"   Avg Win: {metrics_v2.get('avg_win', 0):.2f}%")
logger.info(f"   Avg Loss: {metrics_v2.get('avg_loss', 0):.2f}%")
logger.info(f"   Max DD: {metrics_v2.get('max_drawdown', 0):.2f}%")

# Сравнение всех версий
logger.info("\n" + "=" * 70)
logger.info("🏆 ULTIMATE COMPARISON")
logger.info("=" * 70)

logger.info("\nStrategy              Return       Win Rate     Max DD")
logger.info("-" * 70)
logger.info("EMA Crossover         -21.54%      14.61%       22.29%")
logger.info("RSI V1                -11.64%      38.89%       11.90%")
v2_ret = f"{metrics_v2.get('total_return', 0):.2f}%"
v2_wr = f"{metrics_v2.get('win_rate', 0):.2f}%"
v2_dd = f"{metrics_v2.get('max_drawdown', 0):.2f}%"
logger.info(f"RSI V2 ULTIMATE       {v2_ret:<12} {v2_wr:<12} {v2_dd}")

# BOSS VERDICT
logger.info("\n" + "=" * 70)
logger.info("🎯 BOSS VERDICT")
logger.info("=" * 70)

v2_return = metrics_v2.get('total_return', 0)
v2_winrate = metrics_v2.get('win_rate', 0)

if v2_return > 0 and v2_winrate > 50:
    logger.success("✅ RSI V2: PROFITABLE! Ready for Paper Trading!")
    verdict = "GO"
elif v2_return > -5 and v2_winrate > 40:
    logger.info("🟡 RSI V2: Promising, needs final tweak")
    verdict = "OPTIMIZE"
else:
    logger.error("❌ RSI V2: Still not profitable. Try different approach.")
    verdict = "NO-GO"

# Сохраняем
results_v2['strategy'] = 'RSI Mean Reversion V2 ULTIMATE'
results_v2['parameters'] = params_v2
results_v2['boss_verdict'] = verdict

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"backtest_rsi_v2_ultimate_{timestamp}.json"
save_results(results_v2, output_file)

logger.info(f"\n📄 Results: {output_file}")
logger.info(f"🎯 Verdict: {verdict}")
