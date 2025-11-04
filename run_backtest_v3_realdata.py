"""
Бэктест EMA Crossover Strategy на РЕАЛЬНЫХ данных Binance

Использует скачанные исторические данные из data/binance_historical/
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
from loguru import logger

from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.core.backtester import Backtester


def simulate_backtest(
    data: pd.DataFrame,
    strategy,
    initial_capital: float,
    stop_loss_pct: float,
    take_profit_pct: float,
    commission: float = 0.001,
    slippage: float = 0.0005
) -> dict:
    """
    Простая симуляция бэктеста
    
    Args:
        data: DataFrame с OHLCV данными
        strategy: Экземпляр стратегии
        initial_capital: Начальный капитал
        stop_loss_pct: Stop loss в процентах
        take_profit_pct: Take profit в процентах
        commission: Комиссия биржи
        slippage: Проскальзывание
        
    Returns:
        Словарь с результатами
    """
    capital = initial_capital
    position = None
    trades = []
    equity_curve = [initial_capital]
    
    for i in range(len(data)):
        current_bar = data.iloc[:i+1]
        
        if len(current_bar) < 25:  # Недостаточно данных для индикаторов
            continue
            
        current_price = current_bar['close'].iloc[-1]
        
        # Если есть открытая позиция - проверяем выход
        if position is not None:
            entry_price = position['entry_price']
            side = position['side']
            
            # Рассчитываем P&L
            if side == 'LONG':
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # SHORT
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Проверяем SL/TP
            exit_reason = None
            if pnl_pct <= -stop_loss_pct:
                exit_reason = 'Stop Loss'
            elif pnl_pct >= take_profit_pct:
                exit_reason = 'Take Profit'
            
            # Проверяем сигнал на закрытие
            if exit_reason is None:
                signal = strategy.analyze(current_bar)
                if (side == 'LONG' and signal.type.name == 'SELL') or \
                   (side == 'SHORT' and signal.type.name == 'BUY'):
                    exit_reason = 'Signal Exit'
            
            if exit_reason:
                # Закрываем позицию
                exit_price = current_price * (1 + slippage if side == 'SHORT' else 1 - slippage)
                
                # Рассчитываем финальный P&L с учетом комиссий
                if side == 'LONG':
                    pnl_pct_final = (exit_price - entry_price) / entry_price - commission * 2
                else:
                    pnl_pct_final = (entry_price - exit_price) / entry_price - commission * 2
                
                pnl_usd = capital * 0.95 * pnl_pct_final  # 95% капитала в сделке
                capital += pnl_usd
                
                # Сохраняем сделку
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': current_bar.index[-1],
                    'side': side,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct_final * 100,
                    'pnl_usd': pnl_usd,
                    'exit_reason': exit_reason,
                    'duration_hours': (current_bar.index[-1] - position['entry_time']).total_seconds() / 3600
                })
                
                position = None
                equity_curve.append(capital)
        
        # Если нет позиции - проверяем сигнал на вход
        if position is None:
            signal = strategy.analyze(current_bar)
            
            if signal.type.name in ['BUY', 'SELL']:
                side = 'LONG' if signal.type.name == 'BUY' else 'SHORT'
                entry_price = current_price * (1 + slippage if side == 'LONG' else 1 - slippage)
                
                position = {
                    'entry_time': current_bar.index[-1],
                    'entry_price': entry_price,
                    'side': side
                }
    
    # Рассчитываем метрики
    winning_trades = [t for t in trades if t['pnl_pct'] > 0]
    losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
    
    total_return = ((capital - initial_capital) / initial_capital) * 100
    win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
    
    avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
    
    profit_factor = (sum([t['pnl_usd'] for t in winning_trades]) / 
                     abs(sum([t['pnl_usd'] for t in losing_trades]))) if losing_trades else 0
    
    # Max Drawdown
    peak = initial_capital
    max_dd = 0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    # Sharpe Ratio (упрощенный)
    returns = [trades[i]['pnl_pct'] for i in range(len(trades))]
    sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if len(returns) > 1 else 0
    
    metrics = {
        'total_return': total_return,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'best_trade': max([t['pnl_pct'] for t in trades]) if trades else 0,
        'worst_trade': min([t['pnl_pct'] for t in trades]) if trades else 0,
        'avg_trade_duration_hours': np.mean([t['duration_hours'] for t in trades]) if trades else 0
    }
    
    return {
        'metrics': metrics,
        'trades': trades,
        'equity_curve': equity_curve,
        'final_capital': capital
    }


def load_binance_historical_data(csv_path: str) -> pd.DataFrame:
    """
    Загрузить исторические данные Binance из CSV
    
    Args:
        csv_path: Путь к CSV файлу
        
    Returns:
        DataFrame с OHLCV данными
    """
    logger.info(f"Loading data from: {csv_path}")
    
    df = pd.read_csv(csv_path)
    
    # Конвертируем timestamp в datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Проверяем наличие необходимых колонок
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Missing required columns. Found: {df.columns.tolist()}")
    
    logger.success(f"✅ Loaded {len(df)} candles")
    logger.info(f"Period: {df.index[0]} → {df.index[-1]}")
    logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df


def resample_to_timeframe(df: pd.DataFrame, timeframe: str = '5T') -> pd.DataFrame:
    """
    Ресэмплировать 1-минутные данные в нужный таймфрейм
    
    Args:
        df: DataFrame с 1-минутными свечами
        timeframe: Целевой таймфрейм ('5T' = 5 минут, '15T' = 15 минут, и т.д.)
        
    Returns:
        Ресэмплированный DataFrame
    """
    logger.info(f"Resampling to {timeframe} timeframe...")
    
    ohlc_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    resampled = df.resample(timeframe).agg(ohlc_dict).dropna()
    
    # Reset index to make timestamp a column again
    resampled = resampled.reset_index()
    
    logger.success(f"✅ Resampled to {len(resampled)} candles")
    
    return resampled


def run_backtest_with_params(
    data: pd.DataFrame,
    fast_ema: int = 9,
    slow_ema: int = 21,
    rsi_period: int = 14,
    rsi_overbought: float = 70.0,
    rsi_oversold: float = 30.0,
    stop_loss: float = 0.02,
    take_profit: float = 0.04,
    initial_capital: float = 10000.0
) -> dict:
    """
    Запустить бэктест с заданными параметрами
    
    Returns:
        Словарь с результатами
    """
    logger.info("=" * 70)
    logger.info("🚀 RUNNING BACKTEST ON REAL BINANCE DATA")
    logger.info("=" * 70)
    
    # Создаем стратегию
    strategy = EMACrossoverStrategy(
        fast_period=fast_ema,
        slow_period=slow_ema,
        rsi_period=rsi_period,
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold
    )
    
    logger.info(f"Strategy: {strategy.name}")
    logger.info(f"Parameters: Fast EMA={fast_ema}, Slow EMA={slow_ema}")
    logger.info(f"RSI: {rsi_period} period, levels {rsi_oversold}-{rsi_overbought}")
    logger.info(f"Risk: SL={stop_loss*100:.1f}%, TP={take_profit*100:.1f}%")
    logger.info(f"Capital: ${initial_capital:,.2f}")
    
    # Создаем бэктестер
    backtester = Backtester(
        symbol="BTCUSDT",
        timeframe="5m"
    )
    
    # Запускаем бэктест
    logger.info("\n🔄 Running backtest...")
    
    # Используем простую симуляцию (т.к. Backtester еще не полностью реализован)
    results = simulate_backtest(
        data=data,
        strategy=strategy,
        initial_capital=initial_capital,
        stop_loss_pct=stop_loss,
        take_profit_pct=take_profit,
        commission=0.001,
        slippage=0.0005
    )
    
    # Выводим результаты
    logger.info("\n" + "=" * 70)
    logger.info("📊 BACKTEST RESULTS")
    logger.info("=" * 70)
    
    metrics = results.get('metrics', {})
    
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
    logger.info(f"   Avg Duration: {metrics.get('avg_trade_duration_hours', 0):.1f} hours")
    
    logger.info(f"\n⚠️  RISK:")
    logger.info(f"   Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
    logger.info(f"   Best Trade: {metrics.get('best_trade', 0):.2f}%")
    logger.info(f"   Worst Trade: {metrics.get('worst_trade', 0):.2f}%")
    
    # Анализ по направлениям
    trades = results.get('trades', [])
    if trades:
        long_trades = [t for t in trades if t.get('side') == 'LONG']
        short_trades = [t for t in trades if t.get('side') == 'SHORT']
        
        logger.info(f"\n📊 DIRECTION ANALYSIS:")
        logger.info(f"   LONG Trades: {len(long_trades)}")
        if long_trades:
            long_wins = [t for t in long_trades if t.get('pnl_pct', 0) > 0]
            logger.info(f"   LONG Win Rate: {len(long_wins)/len(long_trades)*100:.1f}%")
        
        logger.info(f"   SHORT Trades: {len(short_trades)}")
        if short_trades:
            short_wins = [t for t in short_trades if t.get('pnl_pct', 0) > 0]
            logger.info(f"   SHORT Win Rate: {len(short_wins)/len(short_trades)*100:.1f}%")
    
    logger.info("\n" + "=" * 70)
    
    return results


def save_results(results: dict, output_path: str):
    """Сохранить результаты в JSON"""
    # Конвертируем Timestamp в строки
    for trade in results.get('trades', []):
        if 'entry_time' in trade:
            trade['entry_time'] = str(trade['entry_time'])
        if 'exit_time' in trade:
            trade['exit_time'] = str(trade['exit_time'])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.success(f"💾 Results saved to: {output_path}")


def main():
    """Основная функция"""
    
    # Путь к историческим данным
    data_dir = Path("data/binance_historical")
    csv_file = data_dir / "BTCUSDT_historical_2024-10-28_to_7days.csv"
    
    if not csv_file.exists():
        logger.error(f"❌ Data file not found: {csv_file}")
        logger.info("Run download_binance_data.py first!")
        return
    
    # Загружаем данные
    df_1m = load_binance_historical_data(str(csv_file))
    
    # Ресэмплируем в 5-минутки (как в оригинальных тестах)
    df_5m = resample_to_timeframe(df_1m, '5T')
    
    # Параметры стратегии V3 (BEST по предыдущим тестам)
    params = {
        'fast_ema': 9,
        'slow_ema': 21,
        'rsi_period': 14,
        'rsi_overbought': 70.0,
        'rsi_oversold': 30.0,
        'stop_loss': 0.02,      # 2% SL
        'take_profit': 0.04,    # 4% TP
        'initial_capital': 10000.0
    }
    
    # Запускаем бэктест
    results = run_backtest_with_params(df_5m, **params)
    
    # Добавляем метаданные
    results['strategy'] = 'EMA Crossover V3 (Original)'
    results['data_source'] = 'Binance Historical (Real Market Data)'
    results['period'] = f"{df_5m.index[0]} to {df_5m.index[-1]}"
    results['timeframe'] = '5m'
    results['parameters'] = params
    
    # Сохраняем результаты
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"backtest_v3_realdata_{timestamp}.json"
    save_results(results, output_file)
    
    logger.info("\n✅ Backtest complete!")
    logger.info(f"📄 Results file: {output_file}")
    logger.info(f"\n💡 Next step: Run AI analysis")
    logger.info(f"   python analyze_strategy_with_ai.py {output_file}")


if __name__ == "__main__":
    main()
