#!/usr/bin/env python3
"""
Быстрый тест стратегии без подключения к exchange
Проверяет, что LLM генерирует BUY/SELL сигналы (не только HOLD)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from yunmin.llm.openai_analyzer import OpenAIAnalyzer
from yunmin.llm.grok_analyzer import GrokAnalyzer
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
import pandas as pd
import numpy as np

logger.remove()
logger.add(sys.stdout, level="DEBUG")  # Enable DEBUG to see full GPT responses

def generate_fake_candles(num_candles=100, trend_type=None):
    """
    Generate fake market data for testing with different trends.
    
    Args:
        num_candles: Number of candles
        trend_type: "bullish", "bearish", "sideways", or None (random)
    """
    if trend_type is None:
        trend_type = np.random.choice(["bullish", "bearish", "sideways"])
    
    dates = pd.date_range(end=pd.Timestamp.now(), periods=num_candles, freq='5min')
    base_price = np.random.uniform(40000, 60000)
    
    # Different trend slopes
    if trend_type == "bullish":
        trend = np.linspace(0, 3000, num_candles)  # Uptrend
    elif trend_type == "bearish":
        trend = np.linspace(0, -3000, num_candles)  # Downtrend
    else:  # sideways
        trend = np.sin(np.linspace(0, 4 * np.pi, num_candles)) * 500  # Oscillation
    
    noise = np.random.randn(num_candles) * 250
    close = base_price + trend + noise
    open_price = close + np.random.randn(num_candles) * 50
    high = np.maximum(open_price, close) + np.abs(np.random.randn(num_candles) * 100)
    low = np.minimum(open_price, close) - np.abs(np.random.randn(num_candles) * 100)
    volume = np.random.uniform(1000, 5000, num_candles)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })
    
    return df

def test_strategy_signals(analyzer_name="openai", num_tests=10):
    """Test strategy with fake data to check signal diversity"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {analyzer_name.upper()} Strategy - {num_tests} iterations")
    logger.info(f"{'='*60}\n")
    
    # Initialize LLM analyzer
    if analyzer_name == "openai":
        analyzer = OpenAIAnalyzer()
    else:
        analyzer = GrokAnalyzer()
    
    if not analyzer.enabled:
        logger.error(f"❌ {analyzer_name} analyzer not available!")
        return
    
    logger.info(f"✅ {analyzer_name} analyzer initialized")
    
    # Initialize strategy
    strategy = GrokAIStrategy(grok_analyzer=analyzer)
    logger.info("✅ Strategy initialized\n")
    
    # Track signals
    signals = {"BUY": 0, "SELL": 0, "HOLD": 0}
    
    # Run multiple tests with different market conditions
    for i in range(num_tests):
        logger.info(f"Test {i+1}/{num_tests}:")
        
        # Generate fake data with random seed
        np.random.seed(i)
        df = generate_fake_candles(100)
        
        # Get signal
        try:
            signal = strategy.analyze(df)
            
            # Signal.type is SignalType enum, use .value to get string
            signal_type = signal.type.value.upper()
            
            if signal_type == "BUY":
                logger.info(f"  ✅ Signal: BUY (confidence={signal.confidence:.2f})")
                signals["BUY"] += 1
            elif signal_type == "SELL":
                logger.info(f"  ⬇️  Signal: SELL (confidence={signal.confidence:.2f})")
                signals["SELL"] += 1
            else:
                logger.info(f"  ⏸️  Signal: HOLD (confidence={signal.confidence:.2f})")
                signals["HOLD"] += 1
                    
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            signals["HOLD"] += 1
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("РЕЗУЛЬТАТЫ:")
    logger.info(f"{'='*60}")
    logger.info(f"BUY:  {signals['BUY']}/{num_tests} ({signals['BUY']/num_tests*100:.1f}%)")
    logger.info(f"SELL: {signals['SELL']}/{num_tests} ({signals['SELL']/num_tests*100:.1f}%)")
    logger.info(f"HOLD: {signals['HOLD']}/{num_tests} ({signals['HOLD']/num_tests*100:.1f}%)")
    
    # Evaluation
    if signals["BUY"] == 0 and signals["SELL"] == 0:
        logger.error("\n❌ ПРОВАЛ: 100% HOLD - стратегия не генерирует сигналы!")
        return False
    elif signals["HOLD"] > num_tests * 0.8:
        logger.warning(f"\n⚠️ ОСТОРОЖНО: {signals['HOLD']/num_tests*100:.1f}% HOLD - слишком консервативно")
        return False
    else:
        logger.success(f"\n✅ УСПЕХ: Стратегия генерирует разнообразные сигналы!")
        return True

if __name__ == "__main__":
    # Проверяем OpenAI (полная валидация - 15 итераций)
    logger.info("Проверка OpenAI GPT-4o-mini...")
    success = test_strategy_signals("openai", num_tests=15)
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✅ V4 ГОТОВ К 10-ЧАСОВОМУ ТЕСТУ!")
        logger.info("="*60)
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ ТРЕБУЕТСЯ ДОПОЛНИТЕЛЬНАЯ НАСТРОЙКА")
        logger.error("="*60)
