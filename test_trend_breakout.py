"""
BOSS TEST: Trend Breakout MACD Strategy

Тестируем новую стратегию на тех же данных:
- Period: Oct 28 - Nov 3, 2024 (TRENDING market BTC +9%)
- Timeframe: 5min
- Capital: $10,000

ОЖИДАНИЕ:
- EMA/RSI провалились, потому что период был ТРЕНДОВЫЙ
- Trend Breakout должна показать лучшие результаты
- MACD + BB + Volume = качественные входы
- Trailing Stop = максимальная прибыль на тренде
"""

import sys
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yunmin.strategy.trend_breakout_macd import TrendBreakoutMACD

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_binance_historical_data(csv_path: str) -> pd.DataFrame:
    """Загружаем исторические данные Binance"""
    logger.info(f"📥 Загружаем данные из {csv_path}")
    
    # Новый файл уже имеет header
    df = pd.read_csv(csv_path)
    
    # Конвертируем timestamp в datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Оставляем только нужные колонки
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    
    # Конвертируем в float
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    logger.info(f"✅ Загружено {len(df)} свечей")
    logger.info(f"📅 Период: {df['timestamp'].min()} - {df['timestamp'].max()}")
    logger.info(f"💰 Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df

def resample_to_timeframe(df: pd.DataFrame, timeframe: str = '5min') -> pd.DataFrame:
    """Ресемплируем данные в нужный таймфрейм"""
    logger.info(f"⏱️  Ресемплируем в {timeframe}")
    
    df_resampled = df.set_index('timestamp').resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    logger.info(f"✅ После ресемплинга: {len(df_resampled)} свечей")
    
    return df_resampled

def simulate_backtest(
    df: pd.DataFrame,
    strategy: TrendBreakoutMACD,
    initial_capital: float = 10000.0,
    commission: float = 0.001,  # 0.1%
    slippage: float = 0.0005    # 0.05%
) -> dict:
    """Симуляция бэктеста с учетом SL/TP"""
    logger.info(f"\n🤖 Запускаем бэктест: {strategy.get_name()}")
    logger.info(strategy.get_description())
    
    # Генерируем сигналы
    signals = strategy.generate_signals(df)
    
    if not signals:
        logger.warning("⚠️  Нет торговых сигналов!")
        return {
            'total_return': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
        }
    
    logger.info(f"📊 Сгенерировано {len(signals)} сигналов")
    
    # Симуляция торговли
    capital = initial_capital
    position = None
    entry_price = None
    position_size = None
    trades = []
    
    for signal in signals:
        price = signal['price']
        action = signal['action']
        
        if action in ['BUY', 'SELL']:
            # Входим в позицию
            position = signal['position_type']
            entry_price = price * (1 + slippage if action == 'BUY' else 1 - slippage)
            position_size = strategy.get_position_size(capital, entry_price)
            
            # Комиссия при входе
            entry_cost = position_size * entry_price
            commission_paid = entry_cost * commission
            capital -= commission_paid
            
            logger.info(f"{'🟢 LONG' if position == 'LONG' else '🔴 SHORT'} @ ${entry_price:.2f} | "
                       f"Size: {position_size:.6f} | Reason: {signal['reason']}")
            
        elif action == 'EXIT' and position is not None:
            # Выходим из позиции
            exit_price = price * (1 - slippage if position == 'LONG' else 1 + slippage)
            
            # Расчет P&L
            if position == 'LONG':
                pnl = (exit_price - entry_price) * position_size
            else:  # SHORT
                pnl = (entry_price - exit_price) * position_size
                
            # Комиссия при выходе
            exit_value = position_size * exit_price
            commission_paid = exit_value * commission
            capital -= commission_paid
            
            # Обновляем капитал
            capital += pnl
            
            # Запоминаем сделку
            pnl_pct = (pnl / (entry_price * position_size)) * 100
            trades.append({
                'entry_time': signal['timestamp'],
                'entry_price': entry_price,
                'exit_price': exit_price,
                'position_type': position,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'exit_reason': signal['reason']
            })
            
            logger.info(f"❌ EXIT @ ${exit_price:.2f} | P&L: ${pnl:.2f} ({pnl_pct:+.2f}%) | "
                       f"Reason: {signal['reason']} | Capital: ${capital:.2f}")
            
            # Reset позиция
            position = None
            entry_price = None
            position_size = None
    
    # Анализ результатов
    if not trades:
        logger.warning("⚠️  Нет завершенных сделок!")
        return {
            'total_return': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
        }
    
    total_return = ((capital - initial_capital) / initial_capital) * 100
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] <= 0]
    
    win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0
    
    avg_win = sum(t['pnl_pct'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl_pct'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    total_profit = sum(t['pnl'] for t in winning_trades)
    total_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = total_profit / total_loss if total_loss > 0 else 0
    
    # Max Drawdown
    cumulative_returns = []
    cum_capital = initial_capital
    for trade in trades:
        cum_capital += trade['pnl']
        cumulative_returns.append(cum_capital)
    
    max_dd = 0
    peak = cumulative_returns[0]
    for value in cumulative_returns:
        if value > peak:
            peak = value
        dd = ((peak - value) / peak) * 100
        if dd > max_dd:
            max_dd = dd
    
    metrics = {
        'total_return': total_return,
        'final_capital': capital,
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'trades': trades
    }
    
    return metrics

def main():
    logger.info("="*80)
    logger.info("🎯 BOSS TEST: Trend Breakout MACD Strategy")
    logger.info("="*80)
    
    # 1. Загружаем АКТУАЛЬНЫЕ данные 2025 года!
    csv_path = r"f:\AgeeKey\yun_min\data\binance_historical\BTCUSDT_historical_2025-10-01_to_30days.csv"
    df = load_binance_historical_data(csv_path)
    
    # 2. Ресемплируем в 5min
    df_5m = resample_to_timeframe(df, '5min')
    
    # 3. Создаем стратегию
    strategy = TrendBreakoutMACD(
        bb_period=20,
        bb_std=2.0,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        volume_period=20,
        volume_multiplier=1.2,
        trailing_stop_pct=0.015,  # 1.5%
        take_profit_pct=0.03,     # 3%
        position_size_pct=0.9     # 90%
    )
    
    # 4. Запускаем бэктест
    metrics = simulate_backtest(df_5m, strategy, initial_capital=10000.0)
    
    # 5. Выводим результаты
    logger.info("\n" + "="*80)
    logger.info("📊 TREND BREAKOUT RESULTS:")
    logger.info("="*80)
    logger.info(f"💰 Total Return: {metrics['total_return']:+.2f}%")
    logger.info(f"💵 Final Capital: ${metrics['final_capital']:,.2f}")
    logger.info(f"🎯 Win Rate: {metrics['win_rate']:.2f}%")
    logger.info(f"📈 Profit Factor: {metrics['profit_factor']:.2f}")
    logger.info(f"📊 Total Trades: {metrics['total_trades']}")
    logger.info(f"   ✅ Winning: {metrics['winning_trades']} ({metrics['win_rate']:.2f}%)")
    logger.info(f"   ❌ Losing: {metrics['losing_trades']} ({100-metrics['win_rate']:.2f}%)")
    logger.info(f"📊 Avg Win: {metrics['avg_win']:+.2f}%")
    logger.info(f"📊 Avg Loss: {metrics['avg_loss']:+.2f}%")
    logger.info(f"📉 Max Drawdown: {metrics['max_drawdown']:.2f}%")
    
    # 6. Сравнение с предыдущими стратегиями
    logger.info("\n" + "="*80)
    logger.info("🏆 ULTIMATE COMPARISON:")
    logger.info("="*80)
    logger.info("Strategy              Return       Win Rate     Profit Factor  Max DD")
    logger.info("-" * 80)
    logger.info(f"EMA Crossover         -21.54%      14.61%       0.17           22.29%")
    logger.info(f"RSI V1                -11.64%      38.89%       0.36           11.90%")
    logger.info(f"RSI V2 ULTIMATE       -9.86%       57.78%       0.52           11.32%")
    
    ret_str = f"{metrics['total_return']:+.2f}%"
    wr_str = f"{metrics['win_rate']:.2f}%"
    pf_str = f"{metrics['profit_factor']:.2f}"
    dd_str = f"{metrics['max_drawdown']:.2f}%"
    logger.info(f"TREND BREAKOUT        {ret_str:<12} {wr_str:<12} {pf_str:<14} {dd_str}")
    
    # 7. Вердикт
    logger.info("\n" + "="*80)
    if metrics['total_return'] > 0:
        logger.info("✅ BOSS VERDICT: PROFITABLE! Ready for Paper Trading!")
        verdict = "GO"
    elif metrics['total_return'] > -5:
        logger.info("🟡 BOSS VERDICT: Close to breakeven. Needs optimization.")
        verdict = "OPTIMIZE"
    else:
        logger.info("❌ BOSS VERDICT: Still unprofitable. Try different approach.")
        verdict = "NO-GO"
    
    logger.info("="*80)
    
    # 8. Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"backtest_trend_breakout_{timestamp}.json"
    
    # Конвертируем trades для JSON
    metrics_json = metrics.copy()
    metrics_json['trades'] = [
        {
            'entry_time': str(t['entry_time']),
            'entry_price': t['entry_price'],
            'exit_price': t['exit_price'],
            'position_type': t['position_type'],
            'pnl': t['pnl'],
            'pnl_pct': t['pnl_pct'],
            'exit_reason': t['exit_reason']
        }
        for t in metrics['trades']
    ]
    
    with open(result_file, 'w') as f:
        json.dump(metrics_json, f, indent=2)
    
    logger.info(f"\n💾 Результаты сохранены: {result_file}")
    logger.info(f"📊 Verdict: {verdict}")

if __name__ == "__main__":
    main()
