#!/usr/bin/env python3
"""
24-Hour DRY RUN Test - YunMin Trading Bot
==========================================

Запускает бота в DRY_RUN режиме на 24 часа с мониторингом:
- Логирование каждые 5 минут
- Сохранение снапшотов каждый час
- Отчёт о состоянии позиций, P&L, ошибках
- Автоматическое завершение через 24 часа

Usage:
    python run_24h_dry_run.py
"""

import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

# Настройка логирования для 24-часового теста
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Главный лог файл
logger.remove()  # Удалить стандартный вывод
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    level="INFO"
)
logger.add(
    log_dir / f"dry_run_24h_{datetime.now():%Y%m%d_%H%M%S}.log",
    rotation="500 MB",
    retention="7 days",
    level="DEBUG"
)

from yunmin.core.config import load_config
from yunmin.bot import YunMinBot


def get_grok_analysis(bot: YunMinBot, elapsed_hours: float, analysis_dir: Path):
    """
    Получить анализ от Grok AI
    
    Args:
        bot: Экземпляр бота
        elapsed_hours: Прошедшие часы
        analysis_dir: Директория для сохранения анализов
    """
    if not hasattr(bot, 'grok') or not bot.grok or not bot.grok.enabled:
        logger.debug("Grok AI not enabled, skipping analysis")
        return None
    
    try:
        # Собрать данные для анализа
        summary = bot.pnl_tracker.get_summary() if bot.pnl_tracker.total_trades > 0 else {
            'total_pnl': 0,
            'total_trades': 0,
            'win_rate': 0,
            'total_realized_pnl': 0,
            'total_unrealized_pnl': 0
        }
        
        # Последние 5 сделок
        recent_trades = bot.pnl_tracker.closed_positions[-5:] if bot.pnl_tracker.closed_positions else []
        
        # Текущие позиции
        open_positions = bot.pnl_tracker.open_positions
        
        # Сформировать промпт для Grok
        analysis_prompt = f"""
🤖 GROK AI - Анализ торговли YunMin Bot

⏰ ВРЕМЯ: {elapsed_hours:.1f} часов с начала теста
📊 СТАТИСТИКА:
- Всего сделок: {summary['total_trades']}
- Win Rate: {summary['win_rate']:.1f}%
- Общий P&L: ${summary['total_pnl']:+.2f}
- Реализованный P&L: ${summary['total_realized_pnl']:+.2f}
- Нереализованный P&L: ${summary['total_unrealized_pnl']:+.2f}

💼 ОТКРЫТЫЕ ПОЗИЦИИ: {len(open_positions)}
{chr(10).join([f"- {sym}: {pos['side']} @ {pos['entry_price']:.2f}" for sym, pos in open_positions.items()]) if open_positions else "Нет открытых позиций"}

📜 ПОСЛЕДНИЕ 5 СДЕЛОК:
{chr(10).join([f"- {t.get('symbol', 'N/A')}: {t.get('side', 'N/A')} | P&L: ${t.get('pnl', 0):+.2f} ({t.get('pnl_pct', 0):+.1f}%)" for t in recent_trades]) if recent_trades else "Нет завершённых сделок"}

❓ ВОПРОСЫ ДЛЯ АНАЛИЗА:
1. Как оценить текущую стратегию? Что работает, что нет?
2. Какие паттерны видишь в сделках?
3. Есть ли признаки переторговли или недостаточной активности?
4. Рекомендации для улучшения (1-3 конкретных совета)?
5. Оценка рисков: что может пойти не так?

Дай краткий анализ (до 300 слов) с конкретными выводами.
"""
        
        logger.info("🤖 Requesting Grok AI analysis...")
        
        # Вызвать Grok
        analysis = bot.grok.analyze_text(analysis_prompt)
        
        if analysis:
            logger.info("=" * 80)
            logger.info(f"🤖 GROK AI ANALYSIS ({elapsed_hours:.1f}h)")
            logger.info("=" * 80)
            logger.info(analysis)
            logger.info("=" * 80)
            
            # Сохранить анализ
            analysis_file = analysis_dir / f"grok_analysis_hour_{int(elapsed_hours):02d}.txt"
            analysis_file.write_text(
                f"Timestamp: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
                f"Elapsed: {elapsed_hours:.1f} hours\n"
                f"{'=' * 80}\n\n"
                f"{analysis}\n\n"
                f"{'=' * 80}\n"
                f"Stats: {summary}\n"
                f"Open Positions: {len(open_positions)}\n"
                f"Recent Trades: {len(recent_trades)}\n",
                encoding='utf-8'
            )
            logger.info(f"💾 Grok analysis saved to {analysis_file}")
            
            return analysis
        else:
            logger.warning("Grok AI returned empty analysis")
            return None
            
    except Exception as e:
        logger.error(f"Failed to get Grok analysis: {e}", exc_info=True)
        return None


def print_status_report(bot: YunMinBot, elapsed_hours: float):
    """Вывести детальный статус бота"""
    logger.info("=" * 80)
    logger.info(f"📊 STATUS REPORT - {elapsed_hours:.1f} hours elapsed")
    logger.info("=" * 80)
    
    # P&L Summary
    if bot.pnl_tracker.total_trades > 0 or bot.pnl_tracker.open_positions:
        summary = bot.pnl_tracker.get_summary()
        logger.info(f"💰 Total P&L: ${summary['total_pnl']:+.2f}")
        logger.info(f"   Realized: ${summary['total_realized_pnl']:+.2f}")
        logger.info(f"   Unrealized: ${summary['total_unrealized_pnl']:+.2f}")
        logger.info(f"📈 Trades: {summary['total_trades']} (Win Rate: {summary['win_rate']:.1f}%)")
        logger.info(f"   Wins: {bot.pnl_tracker.winning_trades} | Losses: {bot.pnl_tracker.losing_trades}")
    else:
        logger.info("💰 No trades yet")
    
    # Open Positions
    open_count = len(bot.pnl_tracker.open_positions)
    if open_count > 0:
        logger.info(f"📊 Open Positions: {open_count}")
        for symbol, pos in bot.pnl_tracker.open_positions.items():
            logger.info(
                f"   {symbol}: {pos['side']} @ {pos['entry_price']:.2f} "
                f"(Amount: {pos['amount']:.4f})"
            )
    else:
        logger.info("📊 No open positions")
    
    # PositionMonitor status
    if hasattr(bot, 'position_monitor') and bot.position_monitor:
        monitor_count = len(bot.position_monitor.positions)
        logger.info(f"🔍 PositionMonitor: {monitor_count} positions tracked")
    
    # Risk Manager status
    if bot.risk_manager.is_circuit_breaker_triggered():
        logger.warning("⚠️  Circuit Breaker: TRIGGERED")
    else:
        logger.info("✅ Circuit Breaker: OK")
    
    logger.info("=" * 80)
    

def create_hourly_snapshot(bot: YunMinBot, hour: int):
    """Создать снапшот состояния"""
    snapshot_dir = Path('data/snapshots')
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        backup_name = f"hour_{hour:02d}_{datetime.now():%Y%m%d_%H%M}"
        bot.state_manager.backup_state(backup_name)
        logger.info(f"📸 Snapshot created: {backup_name}")
    except Exception as e:
        logger.error(f"Failed to create snapshot: {e}")


def run_24h_test():
    """Запуск 24-часового теста"""
    logger.info("🚀 Starting 24-Hour DRY RUN Test")
    logger.info(f"Start time: {datetime.now():%Y-%m-%d %H:%M:%S}")
    
    # Загрузить конфигурацию
    config = load_config()
    
    # Проверить режим
    if config.trading.mode != 'dry_run':
        logger.error(f"❌ WRONG MODE: {config.trading.mode} (expected 'dry_run')")
        logger.error("Please set YUNMIN_TRADING_MODE=dry_run in .env")
        return False
    
    if not config.exchange.testnet:
        logger.error("❌ Testnet not enabled! Set YUNMIN_EXCHANGE_TESTNET=true")
        return False
    
    logger.info(f"✅ Mode: {config.trading.mode} (Testnet: {config.exchange.testnet})")
    logger.info(f"📊 Symbol: {config.trading.symbol}")
    logger.info(f"💵 Initial Capital: ${config.trading.initial_capital:,.2f}")
    
    # Создать бота
    logger.info("Initializing bot...")
    bot = YunMinBot(config)
    
    # Проверить Grok AI
    if hasattr(bot, 'grok') and bot.grok and bot.grok.enabled:
        logger.info("🤖 Grok AI enabled - will analyze trading every hour")
    else:
        logger.warning("⚠️  Grok AI not enabled - no AI analysis during test")
    
    # Создать директорию для Grok-анализов
    analysis_dir = Path('data/grok_analysis')
    analysis_dir.mkdir(parents=True, exist_ok=True)
    
    # Параметры теста
    test_duration = timedelta(hours=24)
    start_time = datetime.now()
    end_time = start_time + test_duration
    
    # Интервалы
    status_interval = timedelta(minutes=5)  # Статус каждые 5 минут
    snapshot_interval = timedelta(hours=1)  # Снапшот каждый час
    grok_interval = timedelta(hours=1)  # Grok анализ каждый час
    
    next_status = start_time + status_interval
    next_snapshot = start_time + snapshot_interval
    next_grok = start_time + grok_interval
    
    iteration = 0
    last_snapshot_hour = 0
    last_grok_hour = 0
    
    logger.info(f"⏰ Test will run until: {end_time:%Y-%m-%d %H:%M:%S}")
    logger.info("=" * 80)
    
    try:
        while datetime.now() < end_time:
            iteration += 1
            current_time = datetime.now()
            elapsed = current_time - start_time
            elapsed_hours = elapsed.total_seconds() / 3600
            
            # Запустить одну итерацию бота
            try:
                bot.run_once()
            except Exception as e:
                logger.error(f"❌ Bot iteration failed: {e}", exc_info=True)
            
            # Проверить статус
            if current_time >= next_status:
                print_status_report(bot, elapsed_hours)
                next_status = current_time + status_interval
            
            # Создать снапшот
            if current_time >= next_snapshot:
                current_hour = int(elapsed_hours)
                if current_hour > last_snapshot_hour:
                    create_hourly_snapshot(bot, current_hour)
                    last_snapshot_hour = current_hour
                next_snapshot = current_time + snapshot_interval
            
            # 🤖 Grok AI анализ каждый час
            if current_time >= next_grok:
                current_hour = int(elapsed_hours)
                if current_hour > last_grok_hour and current_hour > 0:  # Не запускать в час 0
                    get_grok_analysis(bot, elapsed_hours, analysis_dir)
                    last_grok_hour = current_hour
                next_grok = current_time + grok_interval
            
            # Пауза между итерациями (60 секунд = 1 минута)
            time.sleep(60)
        
        # Финальный отчёт
        logger.info("=" * 80)
        logger.info("🏁 24-HOUR TEST COMPLETED")
        logger.info("=" * 80)
        print_status_report(bot, 24.0)
        
        # 🤖 Финальный Grok-анализ (ВАЖНО!)
        logger.info("")
        logger.info("🤖 Requesting FINAL Grok AI analysis...")
        final_analysis = get_grok_analysis(bot, 24.0, analysis_dir)
        if final_analysis:
            # Сохранить финальный анализ отдельно
            final_file = analysis_dir / "FINAL_24H_ANALYSIS.txt"
            final_file.write_text(
                f"{'='*80}\n"
                f"ФИНАЛЬНЫЙ АНАЛИЗ GROK AI - 24 ЧАСА DRY RUN\n"
                f"{'='*80}\n\n"
                f"Дата: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                f"{final_analysis}\n\n"
                f"{'='*80}\n",
                encoding='utf-8'
            )
            logger.info(f"💾 Final Grok analysis saved to {final_file}")
        
        # Финальный снапшот
        create_hourly_snapshot(bot, 24)
        
        # Сохранить финальное состояние
        logger.info("Saving final state...")
        try:
            bot.state_manager.save_positions(bot.pnl_tracker.open_positions)
            bot.state_manager.save_trades(bot.pnl_tracker.closed_positions)
            
            stats = {
                'total_pnl': bot.pnl_tracker.total_realized_pnl,
                'total_trades': bot.pnl_tracker.total_trades,
                'winning_trades': bot.pnl_tracker.winning_trades,
                'losing_trades': bot.pnl_tracker.losing_trades,
                'win_rate': bot.pnl_tracker.get_win_rate()
            }
            bot.state_manager.save_statistics(stats)
            logger.info("✅ Final state saved")
        except Exception as e:
            logger.error(f"Failed to save final state: {e}")
        
        logger.info(f"End time: {datetime.now():%Y-%m-%d %H:%M:%S}")
        logger.info("=" * 80)
        
        return True
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Test interrupted by user (Ctrl+C)")
        elapsed = datetime.now() - start_time
        elapsed_hours = elapsed.total_seconds() / 3600
        logger.info(f"Test ran for {elapsed_hours:.1f} hours")
        print_status_report(bot, elapsed_hours)
        return False
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return False
    
    finally:
        # Остановить PositionMonitor
        if hasattr(bot, 'position_monitor') and bot.position_monitor:
            logger.info("Stopping PositionMonitor...")
            bot.position_monitor.stop()


if __name__ == '__main__':
    logger.info("YunMin 24-Hour DRY RUN Test")
    logger.info("=" * 80)
    
    success = run_24h_test()
    
    if success:
        logger.info("✅ Test completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Test failed or interrupted")
        sys.exit(1)
