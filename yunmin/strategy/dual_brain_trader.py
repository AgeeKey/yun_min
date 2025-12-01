"""
Dual-Brain AI Trading System - Стратегический + Оперативный ИИ

Архитектура:
1. Strategic Brain (o3-mini/gpt-5.1): Общий анализ рынка раз в час
2. Tactical Brain (gpt-5-mini): Решения на каждую свечу

Преимущества:
- Глубокий анализ + быстрые решения
- Экономия токенов (стратегия редко, тактика часто)
- ИИ сам придумывает стратегию, код не знает правил
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType
from yunmin.llm.openai_analyzer import OpenAIAnalyzer


class DualBrainTrader(BaseStrategy):
    """
    Двухуровневая ИИ-система для торговли.
    
    Strategic Brain (редко, глубоко):
    - Модель: o3-mini (reasoning, 2.5M/day) или gpt-5.1 (250k/day)
    - Частота: Раз в 30-60 минут
    - Задача: Анализ рынка, определение сценария, лимиты риска
    
    Tactical Brain (часто, быстро):
    - Модель: gpt-5-mini (2.5M/day, быстрая)
    - Частота: Каждая свеча (5m)
    - Задача: BUY/SELL/HOLD с учётом стратегии
    
    Философия:
    - ИИ сам придумывает стратегию
    - Код не знает правил торговли
    - Стратегия живёт в "голове" модели
    """
    
    def __init__(
        self,
        strategic_model: str = "o3-mini",  # or "gpt-5.1"
        tactical_model: str = "gpt-5-mini",
        strategic_interval_minutes: int = 60,  # Раз в час
        enable_reasoning: bool = True
    ):
        """
        Инициализация двухмозговой системы.
        
        Args:
            strategic_model: Модель для стратегического анализа (o3-mini, gpt-5.1)
            tactical_model: Модель для оперативных решений (gpt-5-mini)
            strategic_interval_minutes: Как часто обновлять стратегию (30-60 мин)
            enable_reasoning: Показывать рассуждения ИИ
        """
        super().__init__("Dual_Brain_AI")
        
        # Создать два "мозга"
        self.strategic_brain = OpenAIAnalyzer(model=strategic_model)
        self.tactical_brain = OpenAIAnalyzer(model=tactical_model)
        
        self.strategic_interval = timedelta(minutes=strategic_interval_minutes)
        self.enable_reasoning = enable_reasoning
        
        # Текущая стратегия (создаётся Strategic Brain)
        self.current_strategy: Optional[Dict[str, Any]] = None
        self.strategy_updated_at: Optional[datetime] = None
        
        # Статистика
        self.strategic_updates = 0
        self.tactical_decisions = 0
        
        logger.info("🧠🧠 Dual-Brain AI Trader initialized:")
        logger.info(f"   Strategic Brain: {strategic_model} (every {strategic_interval_minutes}m)")
        logger.info(f"   Tactical Brain: {tactical_model} (every candle)")
        logger.success("✅ Two-level AI system ready!")
    
    def _needs_strategic_update(self) -> bool:
        """Проверить, нужно ли обновить стратегию."""
        if self.strategy_updated_at is None:
            return True
        
        elapsed = datetime.now() - self.strategy_updated_at
        return elapsed >= self.strategic_interval
    
    def _update_strategic_view(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Strategic Brain: Обновить общую стратегию.
        
        Анализирует:
        - Общий тренд рынка
        - Ключевые уровни
        - Рыночный режим (trending/ranging)
        - Риск-параметры
        - Сценарий на ближайший период
        """
        logger.info("🧠 STRATEGIC BRAIN: Analyzing market overview...")
        
        # Подготовить данные для стратегического анализа
        current_price = df['close'].iloc[-1]
        
        # Изменения за разные периоды
        change_1h = ((current_price - df['close'].iloc[-12]) / df['close'].iloc[-12]) * 100
        change_4h = ((current_price - df['close'].iloc[-48]) / df['close'].iloc[-48]) * 100
        change_24h = ((current_price - df['close'].iloc[-288]) / df['close'].iloc[-288]) * 100 if len(df) >= 288 else 0
        
        # Волатильность
        volatility = df['close'].tail(48).pct_change().std() * 100
        
        # Объём
        avg_volume = df['volume'].tail(48).mean()
        current_volume = df['volume'].iloc[-1]
        
        # Построить промпт для Strategic Brain
        strategic_prompt = f"""Ты — главный стратег торговой системы. Твоя задача: определить общую картину рынка и дать рекомендации для тактического уровня.

📊 ТЕКУЩАЯ РЫНОЧНАЯ СИТУАЦИЯ:

Актив: BTC/USDT
Цена: ${current_price:,.2f}

Изменения:
• 1 час:   {change_1h:+.2f}%
• 4 часа:  {change_4h:+.2f}%
• 24 часа: {change_24h:+.2f}%

Волатильность: {volatility:.2f}%
Объём: {current_volume / avg_volume:.2f}x от среднего

📈 ТВОЯ ЗАДАЧА:

1. Определи общий режим рынка:
   - Сильный тренд (вверх/вниз)?
   - Консолидация / флэт?
   - Разворот?

2. Определи сценарий на ближайший час:
   - Куда скорее всего пойдёт цена?
   - Какие ключевые уровни важны?

3. Дай рекомендации по риску:
   - Стоит ли вообще торговать сейчас?
   - Какой размер позиции разумен?
   - Где ставить стопы?

4. Инструкции для оперативного уровня:
   - На что обращать внимание при принятии решений?
   - Какие сигналы важны, какие игнорировать?

ФОРМАТ ОТВЕТА:
MARKET_REGIME: [trending_up/trending_down/ranging/volatile]
SCENARIO: [Краткое описание сценария на час]
KEY_LEVELS: [Важные уровни поддержки/сопротивления]
RISK_ADVICE: [Рекомендации по риску]
TACTICAL_GUIDANCE: [Инструкции для оперативного уровня]
CONFIDENCE: [0-100]%

Думай стратегически. Не торопись с решениями — ты определяешь план на час вперёд.
"""
        
        # Спросить Strategic Brain
        response = self.strategic_brain.analyze_market({
            'context': strategic_prompt,
            'price': current_price,
            'trend': 'analyzing',
            'volume': {'ratio': current_volume / avg_volume}
        })
        
        # Извлечь стратегию из ответа
        if isinstance(response, dict):
            reasoning_text = response.get('reasoning', str(response))
        else:
            reasoning_text = str(response)
        
        # Парсинг стратегии
        strategy = self._parse_strategic_response(reasoning_text)
        
        self.strategic_updates += 1
        self.strategy_updated_at = datetime.now()
        
        logger.success(f"✅ Strategic update #{self.strategic_updates}")
        logger.info(f"   Market Regime: {strategy.get('market_regime', 'unknown')}")
        logger.info(f"   Scenario: {strategy.get('scenario', 'N/A')[:80]}...")
        
        if self.enable_reasoning:
            logger.info(f"   Full reasoning: {reasoning_text[:200]}...")
        
        return strategy
    
    def _parse_strategic_response(self, response_text: str) -> Dict[str, Any]:
        """Распарсить ответ Strategic Brain."""
        lines = response_text.strip().split('\n')
        strategy = {
            'market_regime': 'unknown',
            'scenario': '',
            'key_levels': '',
            'risk_advice': '',
            'tactical_guidance': '',
            'confidence': 0.5,
            'raw_response': response_text
        }
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('MARKET_REGIME:'):
                strategy['market_regime'] = line.split(':', 1)[1].strip()
            elif line.startswith('SCENARIO:'):
                strategy['scenario'] = line.split(':', 1)[1].strip()
            elif line.startswith('KEY_LEVELS:'):
                strategy['key_levels'] = line.split(':', 1)[1].strip()
            elif line.startswith('RISK_ADVICE:'):
                strategy['risk_advice'] = line.split(':', 1)[1].strip()
            elif line.startswith('TACTICAL_GUIDANCE:'):
                strategy['tactical_guidance'] = line.split(':', 1)[1].strip()
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.split(':', 1)[1].strip().replace('%', '')
                    strategy['confidence'] = float(conf_str) / 100.0
                except:
                    pass
        
        return strategy
    
    def _make_tactical_decision(self, df: pd.DataFrame) -> Signal:
        """
        Tactical Brain: Принять оперативное решение.
        
        Использует:
        - Текущую стратегию от Strategic Brain
        - Последние свечи
        - Быстрый анализ
        """
        current_price = df['close'].iloc[-1]
        
        # Построить промпт для Tactical Brain
        tactical_prompt = f"""Ты — оперативный трейдер. Главный стратег дал тебе план, ты принимаешь быстрые решения на основе его рекомендаций.

📊 СТРАТЕГИЧЕСКИЙ КОНТЕКСТ (от главного мозга):

Режим рынка: {self.current_strategy['market_regime']}
Сценарий: {self.current_strategy['scenario']}
Ключевые уровни: {self.current_strategy['key_levels']}
Риск-рекомендации: {self.current_strategy['risk_advice']}
Инструкции: {self.current_strategy['tactical_guidance']}

📈 ТЕКУЩАЯ СИТУАЦИЯ:

Цена: ${current_price:,.2f}

Последние 5 свечей:
"""
        
        # Добавить последние свечи
        for i in range(-5, 0):
            candle = df.iloc[i]
            direction = "🟢" if candle['close'] > candle['open'] else "🔴"
            tactical_prompt += f"\n{direction} O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f}"
        
        tactical_prompt += f"""

⚡ ТВОЯ ЗАДАЧА:

С учётом стратегического плана и текущей ситуации, прими решение ПРЯМО СЕЙЧАС:

BUY - открыть длинную позицию
SELL - открыть короткую позицию  
HOLD - ждать лучшей возможности

Важно: стратег уже всё обдумал за тебя. Ты просто исполняешь план, реагируя на текущий момент.

ФОРМАТ ОТВЕТА:
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]%
REASONING: [Краткое объяснение в 1-2 предложениях]
ENTRY_PRICE: ${current_price:,.2f}

Решай быстро, но в рамках стратегического плана!
"""
        
        # Спросить Tactical Brain
        response = self.tactical_brain.analyze_market({
            'context': tactical_prompt,
            'price': current_price,
            'strategy': self.current_strategy
        })
        
        # Парсинг решения
        if isinstance(response, dict):
            reasoning_text = response.get('reasoning', str(response))
        else:
            reasoning_text = str(response)
        
        signal = self._parse_tactical_response(reasoning_text, current_price)
        
        self.tactical_decisions += 1
        
        logger.info(f"⚡ Tactical decision #{self.tactical_decisions}: {signal.type.value.upper()} ({signal.confidence:.0%})")
        logger.info(f"   Reasoning: {signal.reason}")
        
        return signal
    
    def _parse_tactical_response(self, response_text: str, current_price: float) -> Signal:
        """Распарсить ответ Tactical Brain."""
        lines = response_text.strip().split('\n')
        
        decision = SignalType.HOLD
        confidence = 0.5
        reasoning = "Tactical analysis"
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('DECISION:'):
                decision_str = line.split(':', 1)[1].strip().upper()
                if 'BUY' in decision_str or 'LONG' in decision_str:
                    decision = SignalType.BUY
                elif 'SELL' in decision_str or 'SHORT' in decision_str:
                    decision = SignalType.SELL
                else:
                    decision = SignalType.HOLD
            
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.split(':', 1)[1].strip().replace('%', '')
                    confidence = float(conf_str) / 100.0
                except:
                    pass
            
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()
        
        return Signal(
            type=decision,
            confidence=confidence,
            reason=reasoning,
            metadata={
                'entry_price': current_price,
                'strategic_regime': self.current_strategy['market_regime'],
                'tactical_response': response_text[:200]
            }
        )
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Главный метод: двухуровневый анализ.
        
        1. Проверить, нужно ли обновить стратегию
        2. Если да — Strategic Brain обновляет план
        3. Tactical Brain принимает решение на основе плана
        """
        if df.empty or len(df) < 100:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data"
            )
        
        try:
            # 1. Обновить стратегию если нужно
            if self._needs_strategic_update():
                logger.info("=" * 80)
                self.current_strategy = self._update_strategic_view(df)
                logger.info("=" * 80)
            
            # 2. Принять оперативное решение
            signal = self._make_tactical_decision(df)
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Dual-Brain analysis failed: {e}", exc_info=True)
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Analysis error: {str(e)}"
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика работы двухмозговой системы."""
        return {
            'strategic_updates': self.strategic_updates,
            'tactical_decisions': self.tactical_decisions,
            'last_strategy_update': self.strategy_updated_at,
            'current_market_regime': self.current_strategy.get('market_regime') if self.current_strategy else None,
            'current_scenario': self.current_strategy.get('scenario') if self.current_strategy else None
        }
