#!/usr/bin/env python3
"""
Полная валидация V4 архитектуры - все компоненты из RECONSTRUCTION_PLAN.md
Проверяет наличие и работоспособность каждого модуля.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
import traceback

logger.remove()
logger.add(sys.stdout, level="INFO", format="<level>{message}</level>")

# Счетчики
total_tests = 0
passed_tests = 0
failed_tests = 0

def test_component(name: str, test_func):
    """Обертка для тестирования компонента"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Тест {total_tests}: {name}")
    logger.info(f"{'='*70}")
    
    try:
        test_func()
        logger.success(f"✅ {name} - РАБОТАЕТ")
        passed_tests += 1
        return True
    except Exception as e:
        logger.error(f"❌ {name} - ОШИБКА")
        logger.error(f"   {str(e)}")
        logger.debug(traceback.format_exc())
        failed_tests += 1
        return False


# ============================================================================
# 1. AGENTS (AI агенты)
# ============================================================================

def test_market_analyst():
    """agents/market_analyst.py - Анализ рынка (GPT-4o-mini)"""
    from yunmin.agents.market_analyst import MarketAnalystAgent
    import asyncio
    
    analyst = MarketAnalystAgent()
    
    market_data = {
        'price': 50000.0,
        'indicators': {
            'rsi': 55,
            'macd': 100,
            'ema_fast': 50100,
            'ema_slow': 49900
        },
        'trend': 'bullish',
        'volume': 1000000
    }
    
    # Запускаем async функцию синхронно
    analysis = asyncio.run(analyst.analyze(market_data))
    
    assert 'decision' in analysis
    assert 'confidence' in analysis
    assert 'reasoning_chain' in analysis  # MarketAnalyst использует reasoning_chain, а не reasoning
    logger.info(f"   → Decision: {analysis['decision']}, Confidence: {analysis['confidence']:.2f}")


def test_risk_assessor():
    """agents/risk_assessor.py - Оценка рисков"""
    from yunmin.agents.risk_assessor import RiskAssessorAgent
    
    assessor = RiskAssessorAgent(max_position_size=0.1)
    
    proposed_trade = {'action': 'BUY', 'confidence': 0.8}
    market_context = {
        'price': 50000.0,
        'indicators': {'rsi': 50, 'volume_ratio': 1.1},
        'volatility': 0.02
    }
    portfolio = {
        'positions': [],
        'available_capital': 10000.0,
        'total_capital': 10000.0
    }
    
    result = assessor.evaluate(proposed_trade, market_context, portfolio)
    
    assert 'risk_score' in result
    assert 'recommended_position_size' in result
    logger.info(f"   → Risk Score: {result['risk_score']}, Position Size: {result['recommended_position_size']:.4f}")


def test_portfolio_manager():
    """agents/portfolio_manager.py - Управление портфелем"""
    from yunmin.agents.portfolio_manager import PortfolioManagerAgent
    
    manager = PortfolioManagerAgent(max_assets=5)
    
    trade_proposal = {
        'action': 'BUY',
        'confidence': 0.8,
        'recommended_position_size': 0.05
    }
    
    market_context = {
        'symbol': 'BTC/USDT',
        'price': 50000.0,
        'trend_strength': 0.7
    }
    
    portfolio = {
        'positions': [],
        'available_capital': 10000.0,
        'total_capital': 10000.0
    }
    
    result = manager.allocate(trade_proposal, market_context, portfolio)
    
    assert 'approved' in result
    assert 'size' in result  # Portfolio manager returns size directly
    logger.info(f"   → Approved: {result['approved']}, Size: {result.get('size', 0.0):.3f}")


def test_execution_agent():
    """agents/execution_agent.py - Исполнение сделок"""
    from yunmin.agents.execution_agent import ExecutionAgent
    
    agent = ExecutionAgent(slippage_tolerance=0.001)
    
    order = {
        'symbol': 'BTC/USDT',
        'action': 'BUY',
        'quantity': 0.01,
        'price': 50000.0
    }
    
    market_state = {
        'best_bid': 49990.0,
        'best_ask': 50010.0,
        'spread': 20.0,
        'volume': 1000000
    }
    
    result = agent.plan_execution(order, market_state)
    
    assert 'strategy' in result
    assert 'estimated_slippage' in result
    logger.info(f"   → Strategy: {result['strategy']}, Slippage: {result['estimated_slippage']:.4f}")


# ============================================================================
# 2. MEMORY (Система памяти)
# ============================================================================

def test_vector_store():
    """memory/vector_store.py - Chroma/FAISS для RAG"""
    import numpy as np
    from yunmin.memory.vector_store import VectorStore
    
    store = VectorStore(embedding_dim=10, use_faiss=False)
    
    # Добавить эмбеддинги
    for i in range(5):
        embedding = np.random.rand(10).astype('float32')
        metadata = {'test_id': i, 'value': f'test_{i}'}
        store.add(embedding, metadata)
    
    # Поиск
    query = np.random.rand(10).astype('float32')
    results = store.search(query, k=3)
    
    assert len(results) == 3
    logger.info(f"   → Stored: 5 vectors, Retrieved: {len(results)} nearest")


def test_trade_history():
    """memory/trade_history.py - История с эмбеддингами"""
    from yunmin.memory.trade_history import TradeHistory
    
    history = TradeHistory(embedding_model='simple')
    
    # Запомнить сделки
    for i in range(3):
        trade_context = {
            'price': 50000.0 + i * 100,
            'indicators': {'rsi': 45 + i},
            'trend': 'bullish',
            'volatility': 0.02
        }
        decision = {'action': 'BUY', 'confidence': 0.7}
        outcome = {'pnl': 100.0 * (i + 1)}
        
        history.remember_trade(trade_context, decision, outcome)
    
    # Вспомнить похожие
    similar = history.recall_similar({'price': 50100.0, 'indicators': {'rsi': 46}}, top_k=2)
    
    assert len(similar) <= 2
    logger.info(f"   → Stored: 3 trades, Recalled: {len(similar)} similar")


def test_pattern_library():
    """memory/pattern_library.py - База найденных паттернов"""
    from yunmin.memory.pattern_library import PatternLibrary, PatternType
    
    library = PatternLibrary()
    
    # Добавить паттерны
    patterns_added = 0
    for pattern_type in [PatternType.BREAKOUT, PatternType.TREND_REVERSAL, PatternType.CONSOLIDATION]:
        context = {'indicators': {'rsi': 30}, 'type': pattern_type.value}
        outcome = {'pnl': 150.0}
        
        pattern_id = library.add_pattern(pattern_type, context, outcome)
        if pattern_id is not None:
            patterns_added += 1
    
    # Статистика
    stats = library.get_pattern_statistics(PatternType.BREAKOUT)
    
    assert patterns_added > 0
    logger.info(f"   → Added: {patterns_added} patterns, Stats: {stats}")


# ============================================================================
# 3. CONTEXT (Расширенный контекст)
# ============================================================================

def test_market_data():
    """context/market_data.py - 500+ свечей, индикаторы"""
    from yunmin.context.market_data import MarketDataCollector
    
    collector = MarketDataCollector(history_length=500)
    
    # Симулируем добавление данных
    import pandas as pd
    import numpy as np
    
    fake_data = pd.DataFrame({
        'timestamp': pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min'),
        'open': np.random.uniform(49000, 51000, 100),
        'high': np.random.uniform(50000, 52000, 100),
        'low': np.random.uniform(48000, 50000, 100),
        'close': np.random.uniform(49500, 50500, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    collector.update(fake_data)
    context = collector.get_context()
    
    assert 'candles_count' in context
    assert 'indicators' in context
    logger.info(f"   → Candles: {context['candles_count']}, Indicators: {len(context['indicators'])}")


def test_orderbook():
    """context/orderbook.py - Стакан заявок"""
    from yunmin.context.orderbook import OrderBookAnalyzer
    
    analyzer = OrderBookAnalyzer(depth=10)
    
    # Симулируем orderbook
    orderbook = {
        'bids': [[50000.0 - i * 10, 0.1 + i * 0.01] for i in range(10)],
        'asks': [[50010.0 + i * 10, 0.1 + i * 0.01] for i in range(10)]
    }
    
    analysis = analyzer.analyze(orderbook)
    
    assert 'spread' in analysis
    assert 'imbalance' in analysis
    logger.info(f"   → Spread: {analysis['spread']:.2f}, Imbalance: {analysis['imbalance']:.3f}")


def test_sentiment():
    """context/sentiment.py - Новости, соцсети"""
    from yunmin.context.sentiment import SentimentAnalyzer
    
    analyzer = SentimentAnalyzer()
    
    # Симулируем новости
    news = [
        "Bitcoin breaks $50k resistance level",
        "Market shows strong bullish momentum",
        "Analysts warn of potential correction"
    ]
    
    sentiment = analyzer.analyze_batch(news)
    
    assert 'overall_score' in sentiment
    assert 'news_count' in sentiment
    logger.info(f"   → Sentiment Score: {sentiment['overall_score']:.2f}, News: {sentiment['news_count']}")


def test_correlations():
    """context/correlations.py - Связи между активами"""
    from yunmin.context.correlations import CorrelationAnalyzer
    
    analyzer = CorrelationAnalyzer()
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT']
    corr_matrix = analyzer.generate_sample_correlations(symbols)
    
    assert corr_matrix.shape == (4, 4)
    logger.info(f"   → Correlation Matrix: {corr_matrix.shape}, Symbols: {len(symbols)}")


# ============================================================================
# 4. REASONING (Логика принятия решений)
# ============================================================================

def test_chain_of_thought():
    """reasoning/chain_of_thought.py - Пошаговое рассуждение"""
    from yunmin.reasoning.chain_of_thought import ChainOfThoughtReasoning
    
    reasoning = ChainOfThoughtReasoning()
    
    market_context = {
        'price': 50000.0,
        'indicators': {'rsi': 45, 'macd': 50},
        'trend': 'bullish'
    }
    
    analyst_output = {
        'decision': 'BUY',
        'confidence': 0.75,
        'reasoning_chain': {'regime': 'trending_up'}
    }
    
    risk_assessment = {'risk_score': 75, 'approved': True}
    
    result = reasoning.reason(market_context, analyst_output, risk_assessment, memory=[])
    
    assert 'final_decision' in result
    assert 'steps' in result
    logger.info(f"   → Final Decision: {result['final_decision']}, Steps: {len(result['steps'])}")


def test_ensemble():
    """reasoning/ensemble.py - Комбинация нескольких моделей"""
    from yunmin.reasoning.ensemble import EnsembleDecisionMaker
    
    ensemble = EnsembleDecisionMaker(method='voting')
    
    decisions = [
        {'decision': 'BUY', 'confidence': 0.7},
        {'decision': 'BUY', 'confidence': 0.8},
        {'decision': 'HOLD', 'confidence': 0.6},
        {'decision': 'BUY', 'confidence': 0.75}
    ]
    
    result = ensemble.decide(decisions)
    
    assert result['decision'] in ['BUY', 'SELL', 'HOLD']
    assert 'confidence' in result
    logger.info(f"   → Ensemble Decision: {result['decision']} (confidence={result['confidence']:.2f})")


def test_confidence():
    """reasoning/confidence.py - Калибровка уверенности"""
    from yunmin.reasoning.confidence import ConfidenceCalibrator
    
    calibrator = ConfidenceCalibrator()
    
    raw_confidence = 0.85
    market_volatility = 0.03
    model_agreement = 0.75
    
    calibrated = calibrator.calibrate(
        raw_confidence=raw_confidence,
        market_volatility=market_volatility,
        model_agreement=model_agreement
    )
    
    assert 0.0 <= calibrated <= 1.0
    logger.info(f"   → Raw: {raw_confidence:.2f} → Calibrated: {calibrated:.2f}")


# ============================================================================
# 5. LEARNING (Обучение)
# ============================================================================

def test_backtest_analyzer():
    """learning/backtest_analyzer.py - Анализ прошлых сделок"""
    from yunmin.learning.backtest_analyzer import BacktestAnalyzer
    
    analyzer = BacktestAnalyzer()
    
    # Симулируем сделки
    trades = [
        {'entry_price': 50000, 'exit_price': 51000, 'pnl': 100, 'duration': 60},
        {'entry_price': 51000, 'exit_price': 50500, 'pnl': -50, 'duration': 30},
        {'entry_price': 50500, 'exit_price': 52000, 'pnl': 150, 'duration': 120}
    ]
    
    results = analyzer.analyze(trades)
    
    assert 'total_trades' in results
    assert 'win_rate' in results
    logger.info(f"   → Total Trades: {results['total_trades']}, Win Rate: {results['win_rate']:.1%}")


def test_strategy_optimizer():
    """learning/strategy_optimizer.py - Оптимизация параметров"""
    from yunmin.learning.strategy_optimizer import StrategyOptimizer
    
    optimizer = StrategyOptimizer()
    
    # Параметры для оптимизации
    param_space = {
        'rsi_threshold': (20, 80),
        'confidence_min': (0.5, 0.9)
    }
    
    # Симулируем результаты (принимает kwargs)
    def objective(**params):  # Изменено: теперь принимает kwargs
        return params['confidence_min'] * 0.1 + (80 - params['rsi_threshold']) * 0.01
    
    best_params = optimizer.optimize(param_space, objective, n_trials=5)
    
    # Optimize возвращает dict с 'best_params' ключом
    if 'best_params' in best_params:
        best_params = best_params['best_params']
    
    assert 'rsi_threshold' in best_params
    assert 'confidence_min' in best_params
    logger.info(f"   → Best Params: {best_params}")


def test_performance_tracker():
    """learning/performance_tracker.py - Отслеживание производительности"""
    from yunmin.learning.performance_tracker import PerformanceTracker
    
    tracker = PerformanceTracker()
    
    # Добавить метрики
    tracker.record_trade(pnl=100, confidence=0.8, duration=60)
    tracker.record_trade(pnl=-50, confidence=0.7, duration=30)
    tracker.record_trade(pnl=150, confidence=0.85, duration=120)
    
    metrics = tracker.get_metrics()
    
    assert 'total_pnl' in metrics
    assert 'avg_confidence' in metrics
    logger.info(f"   → Total PnL: {metrics['total_pnl']}, Avg Confidence: {metrics['avg_confidence']:.2f}")


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    logger.info("\n" + "="*70)
    logger.info("🚀 ПОЛНАЯ ВАЛИДАЦИЯ V4 АРХИТЕКТУРЫ")
    logger.info("="*70)
    
    # 1. AGENTS
    logger.info("\n" + "🤖 1. AI AGENTS")
    test_component("Market Analyst", test_market_analyst)
    test_component("Risk Assessor", test_risk_assessor)
    test_component("Portfolio Manager", test_portfolio_manager)
    test_component("Execution Agent", test_execution_agent)
    
    # 2. MEMORY
    logger.info("\n" + "🧠 2. MEMORY SYSTEM")
    test_component("Vector Store", test_vector_store)
    test_component("Trade History", test_trade_history)
    test_component("Pattern Library", test_pattern_library)
    
    # 3. CONTEXT
    logger.info("\n" + "📊 3. CONTEXT BUILDERS")
    test_component("Market Data", test_market_data)
    test_component("OrderBook", test_orderbook)
    test_component("Sentiment", test_sentiment)
    test_component("Correlations", test_correlations)
    
    # 4. REASONING
    logger.info("\n" + "🧩 4. REASONING")
    test_component("Chain of Thought", test_chain_of_thought)
    test_component("Ensemble", test_ensemble)
    test_component("Confidence Calibrator", test_confidence)
    
    # 5. LEARNING
    logger.info("\n" + "📚 5. LEARNING")
    test_component("Backtest Analyzer", test_backtest_analyzer)
    test_component("Strategy Optimizer", test_strategy_optimizer)
    test_component("Performance Tracker", test_performance_tracker)
    
    # SUMMARY
    logger.info("\n" + "="*70)
    logger.info("📋 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("="*70)
    logger.info(f"Всего тестов: {total_tests}")
    logger.success(f"✅ Успешно: {passed_tests}")
    
    if failed_tests > 0:
        logger.error(f"❌ Провалено: {failed_tests}")
        logger.warning("\nНекоторые компоненты требуют доработки!")
        sys.exit(1)
    else:
        logger.success("\n🎉 ВСЕ КОМПОНЕНТЫ V4 АРХИТЕКТУРЫ РАБОТАЮТ!")
        logger.success("\n✅ V4 готов к продакшену!")
        sys.exit(0)
