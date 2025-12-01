"""
Демонстрация Dual-Brain AI Trader

Показывает работу двухуровневой системы:
1. Strategic Brain (o3-mini): Анализ каждый час
2. Tactical Brain (gpt-5-mini): Решения каждую свечу
"""

import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from loguru import logger
from datetime import datetime

from yunmin.strategy.dual_brain_trader import DualBrainTrader
from yunmin.data.binance_loader import BinanceDataLoader


def demo_dual_brain():
    """Демонстрация двухмозговой системы."""
    
    logger.info("=" * 100)
    logger.info("🧠🧠 DUAL-BRAIN AI TRADER DEMO")
    logger.info("=" * 100)
    
    # 1. Загрузить данные
    logger.info("\n📥 Loading BTC/USDT data...")
    loader = BinanceDataLoader()
    df = loader.load_data(
        symbol="BTCUSDT",
        interval="5m",
        start_date="2025-01-01",
        end_date="2025-01-10"
    )
    
    if df.empty:
        logger.error("❌ No data loaded!")
        return
    
    logger.success(f"✅ Loaded {len(df)} candles")
    logger.info(f"   Period: {df.index[0]} → {df.index[-1]}")
    logger.info(f"   Price range: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    
    # 2. Создать двухмозговую систему
    logger.info("\n🧠 Initializing Dual-Brain AI Trader...")
    logger.info("   Strategic Brain: o3-mini (reasoning model, глубокий анализ)")
    logger.info("   Tactical Brain: gpt-5-mini (fast, оперативные решения)")
    
    trader = DualBrainTrader(
        strategic_model="o3-mini",       # Глубокий анализ раз в час
        tactical_model="gpt-5-mini",     # Быстрые решения каждую свечу
        strategic_interval_minutes=60,   # Обновлять стратегию раз в час
        enable_reasoning=True
    )
    
    logger.success("✅ Dual-Brain system ready!\n")
    
    # 3. Симуляция торговли
    logger.info("=" * 100)
    logger.info("🎬 SIMULATION START")
    logger.info("=" * 100)
    
    # Точки для тестирования (каждые 2 часа)
    test_points = [
        100,   # +100 свечей (~8 часов)
        124,   # +2 часа (триггер strategic update)
        148,   # +2 часа
        172,   # +2 часа (триггер strategic update)
        196    # +2 часа
    ]
    
    decisions = []
    
    for i, point in enumerate(test_points, 1):
        if point >= len(df):
            break
        
        logger.info("\n" + "=" * 100)
        logger.info(f"📊 TIME POINT #{i}: Candle {point}")
        logger.info("=" * 100)
        
        # Текущие данные до этой точки
        current_df = df.iloc[:point].copy()
        current_time = df.index[point-1]
        current_price = df['close'].iloc[point-1]
        
        logger.info(f"⏰ Time: {current_time}")
        logger.info(f"💰 Price: ${current_price:,.2f}")
        
        # Анализ двухмозговой системой
        signal = trader.analyze(current_df)
        
        # Сохранить решение
        decision_info = {
            'time': current_time,
            'price': current_price,
            'decision': signal.type.value,
            'confidence': signal.confidence,
            'reason': signal.reason,
            'strategic_regime': signal.metadata.get('strategic_regime', 'N/A')
        }
        decisions.append(decision_info)
        
        # Вывод результата
        logger.info("\n" + "-" * 100)
        if signal.type.value == 'buy':
            emoji = "🟢 BUY"
        elif signal.type.value == 'sell':
            emoji = "🔴 SELL"
        else:
            emoji = "⚪ HOLD"
        
        logger.success(f"{emoji} | Confidence: {signal.confidence:.0%} | Market: {decision_info['strategic_regime']}")
        logger.info(f"💭 Reasoning: {signal.reason}")
        logger.info("-" * 100)
    
    # 4. Итоговая статистика
    logger.info("\n" + "=" * 100)
    logger.info("📊 FINAL STATISTICS")
    logger.info("=" * 100)
    
    stats = trader.get_stats()
    
    logger.info(f"🧠 Strategic Brain updates: {stats['strategic_updates']}")
    logger.info(f"⚡ Tactical Brain decisions: {stats['tactical_decisions']}")
    logger.info(f"📅 Last strategy update: {stats['last_strategy_update']}")
    logger.info(f"📈 Current market regime: {stats['current_market_regime']}")
    
    # Статистика решений
    buy_count = sum(1 for d in decisions if d['decision'] == 'buy')
    sell_count = sum(1 for d in decisions if d['decision'] == 'sell')
    hold_count = sum(1 for d in decisions if d['decision'] == 'hold')
    avg_confidence = sum(d['confidence'] for d in decisions) / len(decisions) if decisions else 0
    
    logger.info("\n📈 Decisions breakdown:")
    logger.info(f"   🟢 BUY:  {buy_count} ({buy_count/len(decisions)*100:.1f}%)")
    logger.info(f"   🔴 SELL: {sell_count} ({sell_count/len(decisions)*100:.1f}%)")
    logger.info(f"   ⚪ HOLD: {hold_count} ({hold_count/len(decisions)*100:.1f}%)")
    logger.info(f"   💪 Avg confidence: {avg_confidence:.1%}")
    
    # 5. Таблица решений
    logger.info("\n" + "=" * 100)
    logger.info("📋 DECISION LOG")
    logger.info("=" * 100)
    
    for i, dec in enumerate(decisions, 1):
        signal_emoji = {"buy": "🟢", "sell": "🔴", "hold": "⚪"}[dec['decision']]
        logger.info(f"{i}. {dec['time']} | ${dec['price']:,.2f} | {signal_emoji} {dec['decision'].upper()} ({dec['confidence']:.0%}) | {dec['strategic_regime']}")
        logger.info(f"   💭 {dec['reason'][:100]}...")
    
    logger.info("\n" + "=" * 100)
    logger.success("✅ Demo completed!")
    logger.info("=" * 100)
    
    # Объяснение преимуществ
    logger.info("\n💡 DUAL-BRAIN ADVANTAGES:")
    logger.info("   1. Strategic Brain (o3-mini) думает глубоко, но редко → экономия токенов")
    logger.info("   2. Tactical Brain (gpt-5-mini) быстрый и дешёвый → можно часто")
    logger.info("   3. Стратегия живёт в 'голове' ИИ, не в коде → гибкость")
    logger.info("   4. ИИ сам адаптируется к рынку → нет жёстких правил")
    logger.info("\n📊 Token usage estimate (24/7):")
    logger.info("   Strategic: 1 update/hour × 24h × 2000 tokens = 48,000 tokens/day")
    logger.info("   Tactical: 288 decisions/day × 800 tokens = 230,400 tokens/day")
    logger.info("   TOTAL: ~278,400 tokens/day (из 2,500,000 - 88.9% запас!) ✅")


if __name__ == "__main__":
    demo_dual_brain()
