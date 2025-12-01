"""
Pure AI Trading Agent - Full Autonomous Decision Making

ИИ-агент принимает ВСЕ решения самостоятельно на основе:
- Анализа графика и паттернов
- Понимания рыночной ситуации
- Собственной логики и рассуждений
- Исторического контекста

НЕТ жёстких правил! ИИ думает как трейдер-человек.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from datetime import datetime

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class PureAIAgent(BaseStrategy):
    """
    Полностью автономный ИИ-агент для торговли.
    
    Философия:
    - ИИ сам анализирует данные
    - ИИ сам придумывает стратегию для каждой сделки
    - ИИ объясняет свои рассуждения
    - Нет жёстких правил RSI/EMA/MACD
    
    Процесс принятия решения:
    1. Показать ИИ последние 100 свечей
    2. Показать ключевые уровни и паттерны
    3. Спросить: "Что делать? BUY/SELL/HOLD?"
    4. ИИ отвечает с объяснением
    """
    
    def __init__(
        self,
        llm_analyzer,
        lookback_candles: int = 100,
        max_response_tokens: int = 800,
        temperature: float = 0.3,  # Низкая = более консервативный
        enable_reasoning: bool = True  # Показывать цепочку рассуждений
    ):
        """
        Инициализация Pure AI Agent.
        
        Args:
            llm_analyzer: OpenAI/Groq/любой LLM анализатор
            lookback_candles: Сколько свечей показывать ИИ (100-200)
            max_response_tokens: Макс. токенов для ответа ИИ
            temperature: 0.0-1.0, насколько креативен ИИ (0.3 = консервативный)
            enable_reasoning: Включить подробные рассуждения ИИ
        """
        super().__init__("Pure_AI_Agent")
        
        self.llm = llm_analyzer
        self.lookback_candles = lookback_candles
        self.max_tokens = max_response_tokens
        self.temperature = temperature
        self.enable_reasoning = enable_reasoning
        
        # Счётчики для статистики
        self.decisions_made = 0
        self.ai_reasoning_history = []
        
        if not self.llm or not self.llm.enabled:
            raise ValueError("❌ Pure AI Agent requires active LLM! Check OPENAI_API_KEY or GROQ_API_KEY")
        
        logger.info(f"🧠 Pure AI Agent initialized:")
        logger.info(f"   LLM: {self.llm.__class__.__name__}")
        logger.info(f"   Lookback: {lookback_candles} candles")
        logger.info(f"   Temperature: {temperature} ({'Conservative' if temperature < 0.5 else 'Balanced' if temperature < 0.8 else 'Aggressive'})")
        logger.info(f"   Reasoning: {'Enabled' if enable_reasoning else 'Disabled'}")
        logger.success("✅ AI Agent ready to trade autonomously!")
    
    def _prepare_market_snapshot(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Подготовить снимок рынка для ИИ.
        
        Включает:
        - Последние N свечей (OHLC)
        - Ключевые уровни поддержки/сопротивления
        - Волатильность
        - Тренд и импульс
        - Объём и ликвидность
        """
        # Взять последние N свечей
        recent_data = df.tail(self.lookback_candles).copy()
        
        # Текущие значения
        current_price = recent_data['close'].iloc[-1]
        open_price = recent_data['open'].iloc[-1]
        high_24h = recent_data['high'].max()
        low_24h = recent_data['low'].min()
        
        # Изменение цены
        price_change_1h = ((current_price - recent_data['close'].iloc[-12]) / recent_data['close'].iloc[-12]) * 100
        price_change_4h = ((current_price - recent_data['close'].iloc[-48]) / recent_data['close'].iloc[-48]) * 100
        price_change_24h = ((current_price - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]) * 100
        
        # Волатильность (стандартное отклонение)
        volatility = recent_data['close'].pct_change().std() * 100
        
        # Уровни поддержки/сопротивления (локальные экстремумы)
        resistance_levels = self._find_resistance_levels(recent_data)
        support_levels = self._find_support_levels(recent_data)
        
        # Объём
        avg_volume = recent_data['volume'].mean()
        current_volume = recent_data['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Направление тренда (простой анализ)
        trend_direction = self._detect_simple_trend(recent_data)
        
        # Последние 10 свечей для паттернов
        last_10_candles = []
        for i in range(-10, 0):
            candle = recent_data.iloc[i]
            candle_type = "🟢 Bullish" if candle['close'] > candle['open'] else "🔴 Bearish"
            candle_size = abs(candle['close'] - candle['open'])
            last_10_candles.append({
                'time': str(candle.get('timestamp', f"T{i}")),
                'open': round(candle['open'], 2),
                'high': round(candle['high'], 2),
                'low': round(candle['low'], 2),
                'close': round(candle['close'], 2),
                'type': candle_type,
                'body_size': round(candle_size, 2)
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': 'BTC/USDT',
            'timeframe': '5m',
            'current_price': round(current_price, 2),
            'price_change': {
                '1h': round(price_change_1h, 2),
                '4h': round(price_change_4h, 2),
                '24h': round(price_change_24h, 2)
            },
            'range_24h': {
                'high': round(high_24h, 2),
                'low': round(low_24h, 2),
                'range_pct': round((high_24h - low_24h) / low_24h * 100, 2)
            },
            'volatility_pct': round(volatility, 2),
            'volume': {
                'current': int(current_volume),
                'average': int(avg_volume),
                'ratio': round(volume_ratio, 2),
                'activity': 'High' if volume_ratio > 1.5 else 'Normal' if volume_ratio > 0.8 else 'Low'
            },
            'key_levels': {
                'resistance': [round(r, 2) for r in resistance_levels[:3]],
                'support': [round(s, 2) for s in support_levels[:3]]
            },
            'trend': trend_direction,
            'last_10_candles': last_10_candles
        }
    
    def _find_resistance_levels(self, df: pd.DataFrame) -> list:
        """Найти уровни сопротивления (локальные максимумы)."""
        highs = df['high'].values
        resistance = []
        
        for i in range(5, len(highs) - 5):
            if highs[i] == max(highs[i-5:i+6]):
                resistance.append(highs[i])
        
        # Сгруппировать близкие уровни
        resistance = sorted(set(resistance), reverse=True)
        return resistance
    
    def _find_support_levels(self, df: pd.DataFrame) -> list:
        """Найти уровни поддержки (локальные минимумы)."""
        lows = df['low'].values
        support = []
        
        for i in range(5, len(lows) - 5):
            if lows[i] == min(lows[i-5:i+6]):
                support.append(lows[i])
        
        # Сгруппировать близкие уровни
        support = sorted(set(support))
        return support
    
    def _detect_simple_trend(self, df: pd.DataFrame) -> str:
        """Определить направление тренда (простой метод)."""
        recent = df.tail(20)
        
        # Посчитать, сколько свечей закрылись выше/ниже
        closes = recent['close'].values
        highs_count = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
        
        if highs_count >= 14:  # 70%+ ростущих
            return "📈 Strong Uptrend"
        elif highs_count >= 11:  # 55%+ ростущих
            return "🟢 Uptrend"
        elif highs_count <= 6:  # 30%- ростущих
            return "📉 Strong Downtrend"
        elif highs_count <= 9:  # 45%- ростущих
            return "🔴 Downtrend"
        else:
            return "↔️  Sideways / Consolidation"
    
    def _build_ai_prompt(self, market_snapshot: Dict[str, Any]) -> str:
        """
        Построить промпт для ИИ-агента.
        
        Промпт объясняет ИИ его роль и даёт полный контекст рынка.
        """
        prompt = f"""Вы — профессиональный криптовалютный трейдер с опытом торговли фьючерсами.
Ваша задача: принять решение BUY (LONG), SELL (SHORT) или HOLD на основе текущей рыночной ситуации.

📊 ТЕКУЩАЯ РЫНОЧНАЯ СИТУАЦИЯ:

Символ: {market_snapshot['symbol']} | Таймфрейм: {market_snapshot['timeframe']}
Текущая цена: ${market_snapshot['current_price']:,.2f}

📈 Изменение цены:
  • 1 час:  {market_snapshot['price_change']['1h']:+.2f}%
  • 4 часа: {market_snapshot['price_change']['4h']:+.2f}%
  • 24 часа: {market_snapshot['price_change']['24h']:+.2f}%

📊 Диапазон 24 часа:
  • Максимум: ${market_snapshot['range_24h']['high']:,.2f}
  • Минимум:  ${market_snapshot['range_24h']['low']:,.2f}
  • Размах:   {market_snapshot['range_24h']['range_pct']:.2f}%

⚡ Волатильность: {market_snapshot['volatility_pct']:.2f}%

📦 Объём торговли:
  • Текущий: {market_snapshot['volume']['current']:,}
  • Средний:  {market_snapshot['volume']['average']:,}
  • Соотношение: {market_snapshot['volume']['ratio']:.2f}x ({market_snapshot['volume']['activity']})

🎯 Ключевые уровни:
  • Сопротивление: {', '.join([f'${x:,.2f}' for x in market_snapshot['key_levels']['resistance']])}
  • Поддержка:     {', '.join([f'${x:,.2f}' for x in market_snapshot['key_levels']['support']])}

📊 Тренд: {market_snapshot['trend']}

🕯️ Последние 10 свечей:
"""
        
        for i, candle in enumerate(market_snapshot['last_10_candles'], 1):
            prompt += f"  {i}. {candle['type']}: O=${candle['open']}, H=${candle['high']}, L=${candle['low']}, C=${candle['close']}\n"
        
        prompt += f"""

📝 ВАША ЗАДАЧА:
Проанализируйте эту ситуацию как опытный трейдер и примите решение:

1. Определите текущий контекст рынка (тренд, консолидация, разворот?)
2. Оцените риски и возможности
3. Примите решение: BUY, SELL или HOLD
4. Обоснуйте своё решение

ФОРМАТ ОТВЕТА (СТРОГО):
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]%
REASONING: [Ваше подробное объяснение в 2-3 предложениях]
ENTRY_PRICE: [Рекомендуемая цена входа]
STOP_LOSS: [Цена стоп-лосса]
TAKE_PROFIT: [Целевая цена]

Будьте честны и осторожны. Лучше пропустить сомнительную сделку (HOLD), чем потерять деньги.
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str, current_price: float) -> Signal:
        """
        Распарсить ответ ИИ в торговый сигнал.
        
        Ожидаемый формат:
        DECISION: BUY
        CONFIDENCE: 75%
        REASONING: Сильный апренд с подтверждением объёма...
        ENTRY_PRICE: 50500
        STOP_LOSS: 49800
        TAKE_PROFIT: 51500
        """
        try:
            lines = response_text.strip().split('\n')
            decision = None
            confidence = 0.5
            reasoning = "AI analysis"
            entry_price = current_price
            stop_loss = None
            take_profit = None
            
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
                    conf_str = line.split(':', 1)[1].strip().replace('%', '')
                    try:
                        confidence = float(conf_str) / 100.0
                    except:
                        confidence = 0.5
                
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()
                
                elif line.startswith('ENTRY_PRICE:'):
                    try:
                        entry_price = float(line.split(':', 1)[1].strip().replace('$', '').replace(',', ''))
                    except:
                        pass
                
                elif line.startswith('STOP_LOSS:'):
                    try:
                        stop_loss = float(line.split(':', 1)[1].strip().replace('$', '').replace(',', ''))
                    except:
                        pass
                
                elif line.startswith('TAKE_PROFIT:'):
                    try:
                        take_profit = float(line.split(':', 1)[1].strip().replace('$', '').replace(',', ''))
                    except:
                        pass
            
            # Если решение не найдено, по умолчанию HOLD
            if decision is None:
                decision = SignalType.HOLD
                confidence = 0.3
                reasoning = "AI response unclear, defaulting to HOLD"
            
            # Создать сигнал
            signal = Signal(
                type=decision,
                confidence=confidence,
                reason=reasoning,
                metadata={
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'ai_raw_response': response_text[:200]  # First 200 chars
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason=f"AI response parsing error: {str(e)}"
            )
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Главный метод: Спросить ИИ, что делать.
        
        Process:
        1. Подготовить снимок рынка
        2. Построить промпт для ИИ
        3. Получить решение от ИИ
        4. Распарсить и вернуть сигнал
        """
        if df.empty or len(df) < self.lookback_candles:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Insufficient data: need {self.lookback_candles} candles, got {len(df)}"
            )
        
        try:
            # 1. Подготовить данные
            logger.info("🧠 Pure AI Agent: Preparing market snapshot...")
            market_snapshot = self._prepare_market_snapshot(df)
            
            # 2. Построить промпт
            ai_prompt = self._build_ai_prompt(market_snapshot)
            
            if self.enable_reasoning:
                logger.info(f"📝 AI Prompt preview:\n{ai_prompt[:300]}...")
            
            # 3. Спросить ИИ
            logger.info(f"🤖 Asking AI: What should we do at ${market_snapshot['current_price']:,.2f}?")
            
            # Для OpenAI используем analyze_market вместо analyze_text
            # Преобразуем prompt в market_data формат
            ai_response_data = self.llm.analyze_market({
                'context': ai_prompt,
                'price': market_snapshot['current_price'],
                'trend': market_snapshot['trend'],
                'volume': market_snapshot['volume']
            })
            
            # Если вернулся словарь с полями signal/confidence/reasoning
            if isinstance(ai_response_data, dict) and 'signal' in ai_response_data:
                # Преобразовать в текстовый формат для парсинга
                ai_response = f"""DECISION: {ai_response_data['signal']}
CONFIDENCE: {int(ai_response_data['confidence'] * 100)}%
REASONING: {ai_response_data['reasoning']}
ENTRY_PRICE: {market_snapshot['current_price']}
"""
            else:
                # Если вернулась строка
                ai_response = str(ai_response_data)
            
            # 4. Распарсить ответ
            signal = self._parse_ai_response(ai_response, market_snapshot['current_price'])
            
            # Логирование
            self.decisions_made += 1
            logger.success(f"✅ AI Decision #{self.decisions_made}: {signal.type.value.upper()} "
                          f"(confidence={signal.confidence:.0%})")
            logger.info(f"💭 AI Reasoning: {signal.reason}")
            
            if self.enable_reasoning:
                logger.debug(f"📊 AI Full Response:\n{ai_response}")
            
            # Сохранить в историю
            self.ai_reasoning_history.append({
                'timestamp': datetime.now(),
                'price': market_snapshot['current_price'],
                'decision': signal.type.value,
                'confidence': signal.confidence,
                'reasoning': signal.reason
            })
            
            # Ограничить историю последними 100 решениями
            if len(self.ai_reasoning_history) > 100:
                self.ai_reasoning_history = self.ai_reasoning_history[-100:]
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Pure AI Agent failed: {e}", exc_info=True)
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason=f"AI agent error: {str(e)}"
            )
    
    def get_reasoning_history(self, last_n: int = 10) -> list:
        """Получить историю последних N решений ИИ."""
        return self.ai_reasoning_history[-last_n:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику работы агента."""
        if not self.ai_reasoning_history:
            return {'decisions_made': 0}
        
        buy_count = sum(1 for d in self.ai_reasoning_history if d['decision'] == 'buy')
        sell_count = sum(1 for d in self.ai_reasoning_history if d['decision'] == 'sell')
        hold_count = sum(1 for d in self.ai_reasoning_history if d['decision'] == 'hold')
        
        avg_confidence = sum(d['confidence'] for d in self.ai_reasoning_history) / len(self.ai_reasoning_history)
        
        return {
            'decisions_made': self.decisions_made,
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'hold_signals': hold_count,
            'avg_confidence': round(avg_confidence, 2),
            'last_decision': self.ai_reasoning_history[-1] if self.ai_reasoning_history else None
        }
