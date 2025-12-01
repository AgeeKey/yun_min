"""
Демонстрация Pure AI Agent - ИИ принимает решения автономно

Этот скрипт показывает:
1. Как ИИ анализирует рынок
2. Какие решения принимает (BUY/SELL/HOLD)
3. Почему он так решил (reasoning)
4. Сравнение с классической стратегией
"""

import sys
import os
from pathlib import Path

# Добавить путь к проекту
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime, timedelta

# Настроить логи
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

from yunmin.strategy.pure_ai_agent import PureAIAgent
from yunmin.llm.openai_analyzer import OpenAIAnalyzer


def generate_sample_data(days: int = 7) -> pd.DataFrame:
    """
    Сгенерировать тестовые данные (или загрузить реальные).
    """
    logger.info(f"📊 Generating {days} days of sample market data...")
    
    # Простая симуляция BTC цены
    np.random.seed(42)
    
    start_price = 50000
    num_candles = days * 24 * 12  # 5-минутные свечи
    
    prices = [start_price]
    for _ in range(num_candles - 1):
        change = np.random.normal(0, 50)  # Средняя волатильность
        new_price = prices[-1] + change
        prices.append(max(new_price, 1000))  # Минимум $1000
    
    # Создать DataFrame
    timestamps = [datetime.now() - timedelta(minutes=5*i) for i in range(num_candles)]
    timestamps.reverse()
    
    data = {
        'timestamp': timestamps,
        'open': [p + np.random.uniform(-20, 20) for p in prices],
        'high': [p + abs(np.random.uniform(10, 50)) for p in prices],
        'low': [p - abs(np.random.uniform(10, 50)) for p in prices],
        'close': prices,
        'volume': [np.random.uniform(100, 500) for _ in prices]
    }
    
    df = pd.DataFrame(data)
    
    logger.success(f"✅ Generated {len(df)} candles (${df['close'].iloc[0]:.0f} → ${df['close'].iloc[-1]:.0f})")
    
    return df


def load_real_data() -> pd.DataFrame:
    """
    Загрузить данные (для демо используем симуляцию).
    """
    logger.info("📊 Loading market data for demonstration...")
    return generate_sample_data(3)


def demo_ai_agent():
    """
    Главная демонстрация Pure AI Agent.
    """
    logger.info("=" * 80)
    logger.info("🧠 PURE AI AGENT DEMONSTRATION")
    logger.info("=" * 80)
    logger.info("")
    
    # 1. Загрузить данные
    logger.info("📥 Step 1: Loading market data...")
    df = load_real_data()
    
    if df.empty:
        logger.error("❌ No data available!")
        return
    
    logger.info(f"   Data range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
    logger.info(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    logger.info("")
    
    # 2. Инициализировать ИИ-агент
    logger.info("🤖 Step 2: Initializing Pure AI Agent...")
    
    try:
        # Создать OpenAI анализатор
        openai_analyzer = OpenAIAnalyzer()
        
        if not openai_analyzer.enabled:
            logger.error("❌ OpenAI Analyzer not enabled! Check OPENAI_API_KEY in .env")
            logger.info("💡 Hint: Ensure .env contains: OPENAI_API_KEY=sk-...")
            return
        
        # Создать AI агента
        ai_agent = PureAIAgent(
            llm_analyzer=openai_analyzer,
            lookback_candles=100,
            temperature=0.3,  # Консервативный режим
            enable_reasoning=True
        )
        
        logger.success("✅ AI Agent ready!")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI Agent: {e}")
        return
    
    # 3. Проанализировать последние 3 точки
    logger.info("🎯 Step 3: AI Agent making decisions at 3 different time points...")
    logger.info("")
    
    # Выбрать 3 точки: начало, середина, конец
    test_points = [
        len(df) // 4,      # 25% от данных
        len(df) // 2,      # 50% от данных
        len(df) - 100      # Последние данные
    ]
    
    decisions = []
    
    for i, point in enumerate(test_points, 1):
        logger.info("-" * 80)
        logger.info(f"🕐 Time Point {i}/3: Candle #{point}")
        
        # Взять данные до этой точки
        df_slice = df.iloc[:point + 1].copy()
        current_price = df_slice['close'].iloc[-1]
        
        logger.info(f"   Current price: ${current_price:,.2f}")
        logger.info(f"   Asking AI: What should we do?")
        logger.info("")
        
        # Спросить ИИ
        signal = ai_agent.analyze(df_slice)
        
        # Показать результат
        logger.info(f"   🎯 AI DECISION: {signal.type.value.upper()}")
        logger.info(f"   📊 Confidence: {signal.confidence:.0%}")
        logger.info(f"   💭 Reasoning: {signal.reason}")
        
        if signal.metadata:
            if signal.metadata.get('entry_price'):
                logger.info(f"   🎫 Entry: ${signal.metadata['entry_price']:,.2f}")
            if signal.metadata.get('stop_loss'):
                logger.info(f"   🛑 Stop Loss: ${signal.metadata['stop_loss']:,.2f}")
            if signal.metadata.get('take_profit'):
                logger.info(f"   🎯 Take Profit: ${signal.metadata['take_profit']:,.2f}")
        
        logger.info("")
        
        decisions.append({
            'point': i,
            'candle': point,
            'price': current_price,
            'decision': signal.type.value,
            'confidence': signal.confidence,
            'reasoning': signal.reason
        })
    
    # 4. Показать статистику
    logger.info("=" * 80)
    logger.info("📈 AGENT STATISTICS")
    logger.info("=" * 80)
    
    stats = ai_agent.get_stats()
    logger.info(f"   Total decisions made: {stats['decisions_made']}")
    logger.info(f"   BUY signals: {stats['buy_signals']}")
    logger.info(f"   SELL signals: {stats['sell_signals']}")
    logger.info(f"   HOLD signals: {stats['hold_signals']}")
    logger.info(f"   Average confidence: {stats['avg_confidence']:.0%}")
    logger.info("")
    
    # 5. Показать сравнение решений
    logger.info("📋 DECISION SUMMARY")
    logger.info("-" * 80)
    for dec in decisions:
        logger.info(f"   Point {dec['point']}: ${dec['price']:,.2f} → {dec['decision'].upper()} ({dec['confidence']:.0%})")
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ DEMONSTRATION COMPLETE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("💡 Key Insights:")
    logger.info("   1. AI analyzes market context (trend, volume, levels)")
    logger.info("   2. AI makes autonomous decisions without rigid rules")
    logger.info("   3. AI explains its reasoning for transparency")
    logger.info("   4. AI adapts to changing market conditions")
    logger.info("")
    logger.info("🚀 Next Steps:")
    logger.info("   • Run backtest: python run_ai_backtest.py")
    logger.info("   • Compare vs classic strategy: python compare_strategies.py")
    logger.info("   • Test live (paper): python run_testnet.py --strategy pure_ai")
    logger.info("")


if __name__ == "__main__":
    try:
        demo_ai_agent()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        logger.error(f"❌ Demonstration failed: {e}", exc_info=True)
