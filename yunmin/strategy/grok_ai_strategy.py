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
        # PHASE 2.1: Relaxed thresholds for increased trading frequency (4% → 15-20%)
        self.fallback_rsi_oversold = 35  # Was 30 - more lenient for LONG entries
        self.fallback_rsi_overbought = 65  # Was 70 - more lenient for SHORT entries
        
        # Параметры индикаторов
        self.rsi_period = 14
        self.ema_fast_period = 9
        self.ema_slow_period = 21
        
        # PHASE 2.1: Relaxed filters for entry conditions
        self.volume_multiplier = 1.2  # Was 1.5 - easier volume threshold
        self.min_ema_distance = 0.003  # Was 0.005 (0.5%) - now 0.3%
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Вычислить технические индикаторы.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame с добавленными индикаторами (rsi, ema_fast, ema_slow, avg_volume)
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
        
        # Вычислить среднюю громкость за последние 20 периодов
        data['avg_volume'] = data['volume'].rolling(window=20).mean()
        
        return data
    
    def _check_volume_confirmation(self, current_volume: float, avg_volume: float, multiplier: float = 1.5) -> bool:
        """
        Проверить, что объём выше среднего (фильтр ликвидности).
        
        Args:
            current_volume: Текущий объём
            avg_volume: Средний объём
            multiplier: Множитель для порога (default: 1.5x)
            
        Returns:
            True if volume is sufficient
        """
        if avg_volume == 0:
            return False
        return current_volume > (avg_volume * multiplier)
    
    def _check_ema_crossover(self, df: pd.DataFrame) -> tuple[bool, str]:
        """
        Проверить кроссовер EMA (подтверждение тренда).
        
        Args:
            df: DataFrame with EMA indicators
            
        Returns:
            Tuple of (has_crossover, direction)
            direction: 'bullish' (fast > slow), 'bearish' (fast < slow), or 'none'
        """
        if len(df) < 2:
            return False, 'none'
        
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Bullish crossover: fast crosses above slow
        if previous['ema_fast'] <= previous['ema_slow'] and current['ema_fast'] > current['ema_slow']:
            return True, 'bullish'
        
        # Bearish crossover: fast crosses below slow
        if previous['ema_fast'] >= previous['ema_slow'] and current['ema_fast'] < current['ema_slow']:
            return True, 'bearish'
        
        # No recent crossover, but check current state
        if current['ema_fast'] > current['ema_slow']:
            return False, 'bullish'
        elif current['ema_fast'] < current['ema_slow']:
            return False, 'bearish'
        
        return False, 'none'
    
    def _check_divergence(self, df: pd.DataFrame) -> tuple[bool, str]:
        """
        Проверить дивергенцию RSI и цены (продвинутый фильтр).
        
        Дивергенция происходит когда:
        - Цена делает новый максимум, но RSI - нет (медвежья дивергенция)
        - Цена делает новый минимум, но RSI - нет (бычья дивергенция)
        
        Args:
            df: DataFrame with price and RSI
            
        Returns:
            Tuple of (has_divergence, type)
            type: 'bullish', 'bearish', or 'none'
        """
        if len(df) < 5:
            return False, 'none'
        
        # Смотрим последние 5 периодов
        recent = df.tail(5)
        prices = recent['close'].values
        rsi_values = recent['rsi'].values
        
        # Медвежья дивергенция: цена растёт, RSI падает
        if prices[-1] > prices[0] and rsi_values[-1] < rsi_values[0]:
            if rsi_values[-1] < rsi_values.max():
                return True, 'bearish'
        
        # Бычья дивергенция: цена падает, RSI растёт
        if prices[-1] < prices[0] and rsi_values[-1] > rsi_values[0]:
            if rsi_values[-1] > rsi_values.min():
                return True, 'bullish'
        
        return False, 'none'
    
    def _check_ema_distance(self, ema_fast: float, ema_slow: float, min_distance: float = 0.005) -> bool:
        """
        Проверить, что расстояние между EMA достаточное (фильтр слабых сигналов).
        
        Args:
            ema_fast: Быстрая EMA
            ema_slow: Медленная EMA
            min_distance: Минимальная дистанция (default: 0.5%)
            
        Returns:
            True if distance is sufficient
        """
        if ema_slow == 0:
            return False
        distance = abs(ema_fast - ema_slow) / ema_slow
        return distance >= min_distance
        
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Analyze market data using Grok AI with enhanced filters.
        
        UPDATED (Nov 2025): Added multiple confirmation filters to prevent false signals:
        - RSI must be at actual overbought/oversold levels (70/30, not 68/32)
        - Volume must be > 1.5x average
        - EMA crossover confirmation
        - Optional: Divergence detection
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Trading signal from Grok AI or fallback logic
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
        avg_volume = latest.get('avg_volume', volume)
        
        # Определить тренд
        if ema_fast > ema_slow:
            trend = "bullish"
        elif ema_fast < ema_slow:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Изменение цены
        price_change = ((current_price - prev['close']) / prev['close']) * 100
        
        # 🔥 НОВЫЕ ФИЛЬТРЫ (Critical Fix for Problem #4)
        # PHASE 2.1: Using relaxed thresholds for increased trading frequency
        # Check volume confirmation
        volume_ok = self._check_volume_confirmation(volume, avg_volume, multiplier=self.volume_multiplier)
        
        # Check EMA crossover
        has_crossover, crossover_direction = self._check_ema_crossover(df_with_indicators)
        
        # Check divergence (optional, experimental)
        has_divergence, divergence_type = self._check_divergence(df_with_indicators)
        
        # Check EMA distance
        ema_distance_ok = self._check_ema_distance(ema_fast, ema_slow, min_distance=self.min_ema_distance)
        
        # Prepare enhanced market data with filters
        enhanced_data = {
            'price': current_price,
            'rsi': rsi,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'trend': trend,
            'volume': volume,
            'price_change': price_change,
            'volume_ok': volume_ok,
            'has_crossover': has_crossover,
            'crossover_direction': crossover_direction,
            'has_divergence': has_divergence,
            'divergence_type': divergence_type,
            'ema_distance_ok': ema_distance_ok
        }
        
        # Log filter status
        logger.debug(f"📊 Filters: volume={volume_ok}, crossover={has_crossover}({crossover_direction}), "
                    f"divergence={has_divergence}({divergence_type}), ema_dist={ema_distance_ok}")
        
        # Если Grok доступен - спросить его (но с учётом фильтров)
        if self.grok and self.grok.enabled:
            return self._get_grok_decision_with_filters(enhanced_data, df_with_indicators)
        else:
            # Fallback: улучшенная логика с фильтрами
            return self._fallback_logic_with_filters(enhanced_data, df_with_indicators)
    
    def _get_grok_decision_with_filters(
        self, 
        enhanced_data: Dict[str, Any],
        df: pd.DataFrame
    ) -> Signal:
        """
        Получить торговое решение от LLM (OpenAI/Grok) с дополнительными фильтрами.
        
        UPDATED (Nov 2025): AI решение проверяется через фильтры для предотвращения
        ложных сигналов (Problem #4 fix).
        
        Args:
            enhanced_data: Enhanced market data with filter results
            df: Full DataFrame with indicators
            
        Returns:
            Signal from AI analyzer (filtered)
        """
        try:
            # Подготовить рыночные данные для AI
            market_data = {
                'symbol': 'BTC/USDT',
                'price': enhanced_data['price'],
                'rsi': enhanced_data['rsi'],
                'ema_fast': enhanced_data['ema_fast'],
                'ema_slow': enhanced_data['ema_slow'],
                'trend': enhanced_data['trend'],
                'volume': enhanced_data['volume'],
                'price_change': enhanced_data['price_change']
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
            
            # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Применить фильтры к AI решению
            # PHASE 2.1: Using relaxed RSI thresholds (35/65) for increased trading frequency
            # AI может предложить сделку, но мы проверим её через фильтры
            if signal_str == 'BUY':
                # Фильтры для LONG (relaxed RSI range: 35-65)
                if enhanced_data['rsi'] >= self.fallback_rsi_oversold and enhanced_data['rsi'] < self.fallback_rsi_overbought:
                    if enhanced_data['volume_ok']:  # Высокий объём
                        if enhanced_data['crossover_direction'] == 'bullish' or enhanced_data['trend'] == 'bullish':
                            if enhanced_data['ema_distance_ok']:  # EMA достаточно разошлись
                                signal_type = SignalType.BUY
                                logger.info(f"✅ BUY signal APPROVED by filters")
                            else:
                                signal_type = SignalType.HOLD
                                reasoning = f"BUY rejected: EMA distance too small. {reasoning}"
                                logger.warning("❌ BUY signal rejected: weak EMA separation")
                        else:
                            signal_type = SignalType.HOLD
                            reasoning = f"BUY rejected: no bullish trend/crossover. {reasoning}"
                            logger.warning("❌ BUY signal rejected: no bullish confirmation")
                    else:
                        signal_type = SignalType.HOLD
                        reasoning = f"BUY rejected: insufficient volume. {reasoning}"
                        logger.warning("❌ BUY signal rejected: low volume")
                else:
                    signal_type = SignalType.HOLD
                    reasoning = f"BUY rejected: RSI not in valid range ({self.fallback_rsi_oversold}-{self.fallback_rsi_overbought}). {reasoning}"
                    logger.warning(f"❌ BUY signal rejected: RSI={enhanced_data['rsi']:.1f}")
            
            elif signal_str == 'SELL':
                # Фильтры для SHORT (relaxed RSI range: 35-65)
                if enhanced_data['rsi'] > self.fallback_rsi_oversold and enhanced_data['rsi'] <= self.fallback_rsi_overbought:
                    if enhanced_data['volume_ok']:  # Высокий объём
                        if enhanced_data['crossover_direction'] == 'bearish' or enhanced_data['trend'] == 'bearish':
                            if enhanced_data['ema_distance_ok']:  # EMA достаточно разошлись
                                signal_type = SignalType.SELL
                                logger.info(f"✅ SELL signal APPROVED by filters")
                            else:
                                signal_type = SignalType.HOLD
                                reasoning = f"SELL rejected: EMA distance too small. {reasoning}"
                                logger.warning("❌ SELL signal rejected: weak EMA separation")
                        else:
                            signal_type = SignalType.HOLD
                            reasoning = f"SELL rejected: no bearish trend/crossover. {reasoning}"
                            logger.warning("❌ SELL signal rejected: no bearish confirmation")
                    else:
                        signal_type = SignalType.HOLD
                        reasoning = f"SELL rejected: insufficient volume. {reasoning}"
                        logger.warning("❌ SELL signal rejected: low volume")
                else:
                    signal_type = SignalType.HOLD
                    reasoning = f"SELL rejected: RSI not in valid range ({self.fallback_rsi_oversold}-{self.fallback_rsi_overbought}). {reasoning}"
                    logger.warning(f"❌ SELL signal rejected: RSI={enhanced_data['rsi']:.1f}")
            else:
                signal_type = SignalType.HOLD
            
            logger.info(f"📊 {analyzer_name} {model_used}: {signal_str} → {signal_type.value.upper()} "
                       f"(confidence={confidence:.0%})")
            if signal_str != signal_type.value.upper():
                logger.warning(f"   ⚠️  AI signal overridden by filters")
            logger.info(f"   💡 Reasoning: {reasoning[:100]}...")
            
            return Signal(
                type=signal_type,
                confidence=confidence if signal_str == signal_type.value.upper() else confidence * 0.5,
                reason=f"🤖 {analyzer_name} ({model_used}): {reasoning}"
            )
            
        except Exception as e:
            logger.error(f"AI decision failed: {e}", exc_info=True)
            logger.warning("Falling back to simple logic with filters")
            return self._fallback_logic_with_filters(enhanced_data, df)
    
    def _fallback_logic_with_filters(
        self, 
        enhanced_data: Dict[str, Any],
        df: pd.DataFrame
    ) -> Signal:
        """
        Улучшенная fallback логика с фильтрами если AI недоступен.
        
        UPDATED (Nov 2025): Применяет те же фильтры, что и AI решения.
        
        Args:
            enhanced_data: Enhanced market data with filter results
            df: Full DataFrame with indicators
            
        Returns:
            Filtered signal
        """
        price = enhanced_data['price']
        rsi = enhanced_data['rsi']
        trend = enhanced_data['trend']
        volume_ok = enhanced_data['volume_ok']
        ema_distance_ok = enhanced_data['ema_distance_ok']
        crossover_direction = enhanced_data['crossover_direction']
        
        # PHASE 2.1: Using relaxed thresholds for increased trading frequency
        # SELL сигнал (SHORT) - relaxed overbought threshold (65)
        if rsi > self.fallback_rsi_overbought:
            if volume_ok and ema_distance_ok:
                if crossover_direction == 'bearish' or trend == 'bearish':
                    return Signal(
                        type=SignalType.SELL,
                        confidence=0.65,
                        reason=f"Fallback: RSI overbought ({rsi:.1f}) + bearish trend + volume confirmation"
                    )
        
        # BUY сигнал (LONG) - relaxed oversold threshold (35)
        if rsi < self.fallback_rsi_oversold:
            if volume_ok and ema_distance_ok:
                if crossover_direction == 'bullish' or trend == 'bullish':
                    return Signal(
                        type=SignalType.BUY,
                        confidence=0.65,
                        reason=f"Fallback: RSI oversold ({rsi:.1f}) + bullish trend + volume confirmation"
                    )
        
        # Default: HOLD
        return Signal(
            type=SignalType.HOLD,
            confidence=0.5,
            reason=f"Fallback: No clear signal (RSI={rsi:.1f}, trend={trend}, vol_ok={volume_ok})"
        )
    
    def _fallback_logic(self, price: float, rsi: float, trend: str) -> Signal:
        """
        Простая fallback логика если Grok недоступен (DEPRECATED - use _fallback_logic_with_filters).
        
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
