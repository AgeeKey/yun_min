"""
AI Trading Strategy - Multi-Provider LLM Support

Использует LLM (OpenAI, Groq, etc.) для принятия торговых решений на основе:
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
    AI-driven trading strategy with multi-provider support.
    
    Works with:
    - OpenAI (GPT-5, GPT-4O-MINI, GPT-4O)
    - Groq (Llama 3.3 70B, Mixtral)
    - Any LLM analyzer with compatible interface
    
    AI анализирует рынок и принимает решения:
    - BUY: открыть LONG позицию
    - SELL: открыть SHORT позицию
    - HOLD: ждать
    """
    
    def __init__(self, grok_analyzer=None):
        """
        Initialize AI trading strategy.
        
        Args:
            grok_analyzer: Any LLM analyzer (OpenAIAnalyzer, GrokAnalyzer, etc.)
                          Compatible interface: analyze_market(), analyze_text()
        """
        super().__init__("AI")
        self.grok = grok_analyzer  # Generic LLM analyzer
        
        if not self.grok or not self.grok.enabled:
            logger.warning("⚠️  LLM AI not available - strategy will use fallback logic")
        else:
            analyzer_type = self.grok.__class__.__name__
            logger.info(f"🤖 AI Strategy initialized with {analyzer_type}")
        
        # Параметры для fallback (если LLM недоступен)
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
        Получить торговое решение от LLM (OpenAI/Grok).
        
        Args:
            price: Текущая цена
            rsi: RSI индикатор
            ema_fast: Быстрая EMA
            ema_slow: Медленная EMA
            trend: Тренд (bullish/bearish/neutral)
            volume: Объём торгов
            price_change: Изменение цены за последний период (%)
            
        Returns:
            Signal from AI analyzer
        """
        try:
            # Подготовить рыночные данные
            market_data = {
                'symbol': 'BTC/USDT',
                'price': price,
                'rsi': rsi,
                'ema_fast': ema_fast,
                'ema_slow': ema_slow,
                'trend': trend,
                'volume': volume,
                'price_change': price_change
            }
            
            # Определить тип анализатора для логирования
            analyzer_type = self.grok.__class__.__name__
            analyzer_name = "OpenAI" if "OpenAI" in analyzer_type else "Groq"
            
            logger.info(f"🤖 Asking {analyzer_name} for trading decision...")
            
            # Вызвать универсальный метод analyze_market()
            result = self.grok.analyze_market(market_data)
            
            # Обработать результат
            signal_str = result.get('signal', 'HOLD').upper()
            confidence = result.get('confidence', 0.5)
            reasoning = result.get('reasoning', 'No reasoning provided')
            model_used = result.get('model_used', 'unknown')
            
            # Конвертировать строку сигнала в SignalType
            if signal_str == 'BUY':
                signal_type = SignalType.BUY
            elif signal_str == 'SELL':
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.HOLD
            
            logger.info(f"📊 {analyzer_name} {model_used}: {signal_str} (confidence={confidence:.0%}, tokens=unknown)")
            logger.info(f"   💡 Reasoning: {reasoning[:100]}...")
            
            return Signal(
                type=signal_type,
                confidence=confidence,
                reason=f"🤖 {analyzer_name} ({model_used}): {reasoning}"
            )
            
        except Exception as e:
            logger.error(f"AI decision failed: {e}", exc_info=True)
            logger.warning("Falling back to simple logic")
            return self._fallback_logic(price, rsi, trend)
    
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
