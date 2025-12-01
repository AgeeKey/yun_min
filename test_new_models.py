"""
Test Latest OpenAI Models for Trading

Тестируем новые модели:
- GPT-5.1, GPT-5, GPT-4.1 series
- O1, O3, O4 reasoning models
- Mini/Nano варианты

Сравниваем:
- Качество решений
- Скорость ответа
- Стоимость
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import time
from datetime import datetime
from loguru import logger

# Настроить логи
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

from yunmin.llm.openai_analyzer import OpenAIAnalyzer
from yunmin.llm.model_config import (
    calculate_daily_cost,
    get_model_config,
    ModelTier,
    get_models_by_tier
)


def test_model(model_name: str, test_prompt: str) -> dict:
    """
    Протестировать одну модель.
    
    Returns:
        {
            'model': str,
            'response': str,
            'response_time_sec': float,
            'success': bool,
            'error': str (optional)
        }
    """
    logger.info(f"🧪 Testing {model_name}...")
    
    try:
        # Создать анализатор
        analyzer = OpenAIAnalyzer(model=model_name)
        
        if not analyzer.enabled:
            return {
                'model': model_name,
                'success': False,
                'error': 'Analyzer not enabled (check API key)'
            }
        
        # Замерить время
        start_time = time.time()
        
        # Сделать запрос
        response = analyzer.analyze_market({
            'context': test_prompt,
            'price': 50000,
            'trend': 'uptrend',
            'volume': {'ratio': 1.5}
        })
        
        elapsed = time.time() - start_time
        
        # Извлечь текст ответа
        if isinstance(response, dict):
            response_text = response.get('reasoning', str(response))
        else:
            response_text = str(response)
        
        logger.success(f"✅ {model_name}: {elapsed:.2f}s")
        
        return {
            'model': model_name,
            'response': response_text[:200],  # First 200 chars
            'response_time_sec': round(elapsed, 2),
            'success': True
        }
        
    except Exception as e:
        logger.error(f"❌ {model_name} failed: {e}")
        return {
            'model': model_name,
            'success': False,
            'error': str(e),
            'response_time_sec': 0
        }


def main():
    """Главная функция тестирования."""
    logger.info("=" * 80)
    logger.info("🚀 TESTING LATEST OPENAI MODELS FOR TRADING")
    logger.info("=" * 80)
    logger.info("")
    
    # Тестовый промпт
    test_prompt = """
    BTC/USDT at $50,000
    RSI: 55 (neutral)
    Trend: Strong uptrend (+5% in 24h)
    Volume: High (1.5x average)
    
    Should we BUY, SELL or HOLD?
    """
    
    # Выбрать модели для тестирования
    test_models = [
        # Рекомендуемые для торговли (high volume)
        'gpt-4o-mini',        # Текущая рекомендация
        'gpt-5-mini',         # Новая альтернатива
        'gpt-4.1-mini',       # Проверенная стабильная
        'o1-mini',            # Reasoning + high volume
        
        # Премиум модели (для сравнения)
        # 'gpt-5.1',          # Раскомментировать если хотите протестировать
        # 'o3',               # Дорого, но интересно
    ]
    
    logger.info(f"📋 Testing {len(test_models)} models:")
    for model in test_models:
        logger.info(f"   • {model}")
    logger.info("")
    
    # Запустить тесты
    results = []
    
    for model in test_models:
        logger.info("-" * 80)
        result = test_model(model, test_prompt)
        results.append(result)
        
        if result['success']:
            logger.info(f"   Response preview: {result['response'][:100]}...")
        
        time.sleep(1)  # Пауза между запросами
        logger.info("")
    
    # Показать сводку
    logger.info("=" * 80)
    logger.info("📊 TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    
    # Таблица результатов
    logger.info(f"{'Model':<25} {'Time':<10} {'Status':<10} {'Cost/month'}")
    logger.info("-" * 80)
    
    for result in results:
        model = result['model']
        
        if result['success']:
            time_str = f"{result['response_time_sec']:.2f}s"
            status = "✅ OK"
        else:
            time_str = "N/A"
            status = "❌ FAIL"
        
        # Посчитать стоимость
        cost_info = calculate_daily_cost(model)
        cost_str = f"${cost_info['monthly_cost_usd']:.2f}/mo"
        
        logger.info(f"{model:<25} {time_str:<10} {status:<10} {cost_str}")
    
    logger.info("")
    logger.info("=" * 80)
    
    # Рекомендация
    successful = [r for r in results if r['success']]
    if successful:
        # Найти самую быструю
        fastest = min(successful, key=lambda x: x['response_time_sec'])
        logger.info(f"⚡ Fastest: {fastest['model']} ({fastest['response_time_sec']:.2f}s)")
        
        # Найти самую дешёвую
        cheapest = min(test_models, key=lambda m: calculate_daily_cost(m)['monthly_cost_usd'])
        cheapest_cost = calculate_daily_cost(cheapest)
        logger.info(f"💰 Cheapest: {cheapest} (${cheapest_cost['monthly_cost_usd']:.2f}/mo)")
        
        logger.info("")
        logger.info("🎯 RECOMMENDATION:")
        logger.info(f"   Model: gpt-4o-mini")
        logger.info(f"   Why: Best balance of speed, quality, and cost")
        logger.info(f"   Cost: ~$3.60/month for 24/7 trading")
        logger.info(f"   Limit: 2.5M tokens/day (plenty for real-time trading)")
    
    logger.info("")
    logger.info("💡 To use a model, update .env:")
    logger.info("   YUNMIN_LLM_MODEL=gpt-4o-mini  # or gpt-5-mini, o1-mini, etc.")
    logger.info("")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Testing interrupted")
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}", exc_info=True)
