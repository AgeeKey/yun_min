"""
Grok AI Trading Strategy - AI-Driven Decision Making

Использует Grok AI для принятия торговых решений на основе:
- Технического анализа
- Рыночных условий
- Исторической статистики
- Паттернов поведения цены
"""

from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class GrokAIStrategy(BaseStrategy):
    """
    AI-driven trading strategy powered by Grok.
    
    Grok анализирует рынок и принимает решения:
    - BUY: открыть LONG позицию
    - SELL: открыть SHORT позицию
    - HOLD: ждать
    """
    
    def __init__(self, grok_analyzer=None):
        """
        Initialize Grok AI strategy.
        
        Args:
            grok_analyzer: GrokAnalyzer instance
        """
        super().__init__("GrokAI")
        self.grok = grok_analyzer
        
        if not self.grok or not self.grok.enabled:
            logger.warning("⚠️  Grok AI not available - strategy will use fallback logic")
        else:
            logger.info("🤖 Grok AI Strategy initialized - AI will make all trading decisions")
        
        # Параметры для fallback (если Grok недоступен)
        self.fallback_rsi_oversold = 30
        self.fallback_rsi_overbought = 70
        
        # Параметры индикаторов
        self.rsi_period = 14
        self.ema_fast_period = 9
        self.ema_slow_period = 21
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Вычислить технические индикаторы.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame с добавленными индикаторами (rsi, ema_fast, ema_slow)
        """
        data = df.copy()
        
        # Вычислить RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Вычислить EMA
        data['ema_fast'] = data['close'].ewm(span=self.ema_fast_period, adjust=False).mean()
        data['ema_slow'] = data['close'].ewm(span=self.ema_slow_period, adjust=False).mean()
        
        return data
        
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Analyze market data using Grok AI.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Trading signal from Grok AI
        """
        if df.empty or len(df) < max(self.rsi_period, self.ema_slow_period) + 1:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for indicators"
            )
        
        # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Вычислить индикаторы!
        df_with_indicators = self._calculate_indicators(df)
        
        # Получить последние данные
        latest = df_with_indicators.iloc[-1]
        prev = df_with_indicators.iloc[-2]
        
        current_price = latest['close']
        rsi = latest.get('rsi', 50)  # Теперь RSI будет реальным!
        ema_fast = latest.get('ema_fast', current_price)
        ema_slow = latest.get('ema_slow', current_price)
        volume = latest.get('volume', 0)
        
        # Определить тренд
        if ema_fast > ema_slow:
            trend = "bullish"
        elif ema_fast < ema_slow:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Изменение цены
        price_change = ((current_price - prev['close']) / prev['close']) * 100
        
        # Если Grok доступен - спросить его!
        if self.grok and self.grok.enabled:
            return self._get_grok_decision(
                current_price, rsi, ema_fast, ema_slow, 
                trend, volume, price_change
            )
        else:
            # Fallback: простая логика
            return self._fallback_logic(current_price, rsi, trend)
    
    def _get_grok_decision(
        self, 
        price: float, 
        rsi: float, 
        ema_fast: float, 
        ema_slow: float,
        trend: str, 
        volume: float,
        price_change: float
    ) -> Signal:
        """
        Получить торговое решение от Grok AI.
        
        Args:
            price: Текущая цена
            rsi: RSI индикатор
            ema_fast: Быстрая EMA
            ema_slow: Медленная EMA
            trend: Тренд (bullish/bearish/neutral)
            volume: Объём торгов
            price_change: Изменение цены за последний период (%)
            
        Returns:
            Signal from Grok AI
        """
        # Составить промпт для Grok
        prompt = f"""АКТИВНЫЙ ТРЕЙДИНГ - Bitcoin (BTC/USDT)

📊 РЫНОЧНЫЕ ДАННЫЕ:
💰 Цена: ${price:.2f}
📈 RSI: {rsi:.1f}
🔵 EMA Fast: ${ema_fast:.2f}
🔴 EMA Slow: ${ema_slow:.2f}
📊 Тренд: {trend}
📉 Изменение: {price_change:+.2f}%
📦 Объём: {volume:.0f}

🎯 ТЫ - АКТИВНЫЙ AI ТРЕЙДЕР!

Твоя цель: Найти торговые возможности и зарабатывать.

✅ ТОРГУЙ АКТИВНО:
- Даже движения 0.3-0.5% - это возможности!
- Короткие позиции (scalping) - твой друг
- Не бойся рисковать при хорошем соотношении риск/прибыль

📋 РЕШЕНИЯ:
1. BUY (LONG) - если ожидаешь рост (уверенность ≥50%)
2. SELL (SHORT) - если ожидаешь падение (уверенность ≥50%)  
3. HOLD - только если действительно НЕТ сигналов

🎓 КОГДА ТОРГОВАТЬ:
✅ RSI < 45 и тренд меняется → BUY
✅ RSI > 55 и тренд меняется → SELL
✅ Цена отскочила от EMA → ТОРГУЙ
✅ Изменение > 0.3% → ИСПОЛЬЗУЙ импульс
✅ EMA Fast пересекает EMA Slow → СИЛЬНЫЙ сигнал

⚠️ НЕ ТОРГОВАТЬ только если:
❌ RSI ровно 50 И нет движения И EMA плоские
❌ Волатильность < 0.1% И нет объёма

📝 ОТВЕТ (СТРОГО в формате):
DECISION: [BUY/SELL/HOLD]
CONFIDENCE: [50-95]%
REASON: [Почему торгуем, 1 предложение]

Решение:"""

        try:
            # Вызвать Grok AI
            logger.info("🤖 Asking Grok AI for trading decision...")
            response = self.grok.analyze_text(prompt, max_tokens=150)
            
            if not response:
                logger.warning("Grok returned empty response, using fallback")
                return self._fallback_logic(price, rsi, trend)
            
            # Парсить ответ Grok
            decision_type, confidence, reason = self._parse_grok_response(response)
            
            logger.info(f"🤖 Grok Decision: {decision_type} (confidence: {confidence}%)")
            logger.info(f"   Reason: {reason}")
            
            return Signal(
                type=decision_type,
                confidence=confidence / 100.0,
                reason=f"🤖 Grok AI: {reason}"
            )
            
        except Exception as e:
            logger.error(f"Grok AI decision failed: {e}", exc_info=True)
            logger.warning("Falling back to simple logic")
            return self._fallback_logic(price, rsi, trend)
    
    def _parse_grok_response(self, response: str) -> tuple:
        """
        Парсить ответ Grok AI.
        
        Args:
            response: Текст ответа от Grok
            
        Returns:
            (SignalType, confidence, reason)
        """
        # Поиск ключевых слов
        response_upper = response.upper()
        
        # Определить тип решения
        if "DECISION: BUY" in response_upper or "DECISION:BUY" in response_upper:
            decision_type = SignalType.BUY
        elif "DECISION: SELL" in response_upper or "DECISION:SELL" in response_upper:
            decision_type = SignalType.SELL
        elif "DECISION: HOLD" in response_upper or "DECISION:HOLD" in response_upper:
            decision_type = SignalType.HOLD
        else:
            # Попробовать найти по содержанию
            if "BUY" in response_upper and "LONG" in response_upper:
                decision_type = SignalType.BUY
            elif "SELL" in response_upper and "SHORT" in response_upper:
                decision_type = SignalType.SELL
            else:
                decision_type = SignalType.HOLD
        
        # Извлечь уверенность (confidence)
        confidence = 50  # default
        try:
            if "CONFIDENCE:" in response_upper:
                conf_line = [line for line in response.split('\n') if 'CONFIDENCE' in line.upper()][0]
                # Найти число
                import re
                numbers = re.findall(r'(\d+)', conf_line)
                if numbers:
                    confidence = int(numbers[0])
                    confidence = max(0, min(100, confidence))  # clamp 0-100
        except:
            pass
        
        # Извлечь причину (reason)
        reason = "AI decision"
        try:
            if "REASON:" in response_upper:
                reason_lines = response.split("REASON:")
                if len(reason_lines) > 1:
                    reason = reason_lines[1].strip().split('\n')[0][:200]  # Первая строка, макс 200 символов
        except:
            pass
        
        return decision_type, confidence, reason
    
    def _fallback_logic(self, price: float, rsi: float, trend: str) -> Signal:
        """
        Простая fallback логика если Grok недоступен.
        
        Args:
            price: Current price
            rsi: RSI indicator
            trend: Market trend
            
        Returns:
            Simple signal
        """
        # Очень консервативная логика
        if rsi < self.fallback_rsi_oversold and trend == "bullish":
            return Signal(
                type=SignalType.BUY,
                confidence=0.6,
                reason=f"Fallback: RSI oversold ({rsi:.1f}) + bullish trend"
            )
        elif rsi > self.fallback_rsi_overbought and trend == "bearish":
            return Signal(
                type=SignalType.SELL,
                confidence=0.6,
                reason=f"Fallback: RSI overbought ({rsi:.1f}) + bearish trend"
            )
        else:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason="Fallback: No clear signal"
            )
