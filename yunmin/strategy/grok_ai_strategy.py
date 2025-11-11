"""
AI Trading Strategy - Multi-Provider LLM Support

Использует LLM (OpenAI, Groq, etc.) для принятия торговых решений на основе:
- Технического анализа
- Рыночных условий
- Исторической статистики
- Паттернов поведения цены

PHASE 2 Enhancements:
- Relaxed entry conditions for 15-20% trading frequency
- Advanced indicators (MACD, Bollinger Bands, ATR, OBV, Ichimoku)
- Hybrid approach: Classical analysis + AI confirmation
"""

from typing import Dict, Any, Optional
import pandas as pd
from loguru import logger

from yunmin.strategy.base import BaseStrategy, Signal, SignalType
from yunmin.strategy.indicators import TechnicalIndicators, calculate_all_indicators


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
    
    def __init__(self, grok_analyzer=None, use_advanced_indicators=True, hybrid_mode=True,
                 confirmation_bars=0):
        """
        Initialize AI trading strategy.
        
        Args:
            grok_analyzer: Any LLM analyzer (OpenAIAnalyzer, GrokAnalyzer, etc.)
                          Compatible interface: analyze_market(), analyze_text()
            use_advanced_indicators: Enable MACD, Bollinger Bands, ATR, OBV, Ichimoku (Phase 2.3)
            hybrid_mode: Use classical analysis + AI confirmation (Phase 2.2)
            confirmation_bars: Require N consecutive bars with same signal before entry (0 = disabled)
        """
        super().__init__("AI")
        self.grok = grok_analyzer  # Generic LLM analyzer
        
        # PHASE 2 Configuration
        self.use_advanced_indicators = use_advanced_indicators
        self.hybrid_mode = hybrid_mode
        self.indicators = TechnicalIndicators()
        
        # Trade frequency controls
        self.confirmation_bars = confirmation_bars
        self.signal_history = []  # Track recent signals for confirmation
        
        if not self.grok or not self.grok.enabled:
            logger.warning("⚠️  LLM AI not available - strategy will use fallback logic")
        else:
            analyzer_type = self.grok.__class__.__name__
            mode_str = "Hybrid" if hybrid_mode else "AI-only"
            indicators_str = "Advanced" if use_advanced_indicators else "Basic"
            logger.info(f"🤖 AI Strategy initialized: {analyzer_type}, Mode={mode_str}, "
                       f"Indicators={indicators_str}, Confirmation={confirmation_bars} bars")
        
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
        
        PHASE 2.3: Includes advanced indicators when enabled.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame с добавленными индикаторами (rsi, ema_fast, ema_slow, avg_volume)
            + advanced indicators if enabled (MACD, BB, ATR, OBV, Ichimoku)
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
        
        # PHASE 2.3: Add advanced indicators if enabled
        if self.use_advanced_indicators and len(df) >= 52:
            try:
                data = calculate_all_indicators(data)
                logger.debug("✅ Advanced indicators calculated")
            except Exception as e:
                logger.warning(f"Failed to calculate advanced indicators: {e}")
        
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
    
    def _classical_analysis(self, df_with_indicators: pd.DataFrame) -> Signal:
        """
        PHASE 2.2: Classical technical analysis without AI.
        
        Uses voting system from multiple indicators to generate signal.
        
        Args:
            df_with_indicators: DataFrame with all calculated indicators
            
        Returns:
            Signal based on classical technical analysis
        """
        if df_with_indicators.empty:
            return Signal(type=SignalType.HOLD, confidence=0.0, reason="No data")
        
        latest = df_with_indicators.iloc[-1]
        current_price = latest['close']
        
        # Initialize voting system
        votes = {'buy': 0.0, 'sell': 0.0, 'hold': 0.0}
        reasons = []
        
        # 1. RSI Vote (weight: 1.0)
        rsi = latest.get('rsi', 50)
        if rsi < self.fallback_rsi_oversold:
            votes['buy'] += 1.0
            reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > self.fallback_rsi_overbought:
            votes['sell'] += 1.0
            reasons.append(f"RSI overbought ({rsi:.1f})")
        else:
            votes['hold'] += 0.5
        
        # 2. EMA Trend Vote (weight: 1.0)
        ema_fast = latest.get('ema_fast', current_price)
        ema_slow = latest.get('ema_slow', current_price)
        if ema_fast > ema_slow:
            votes['buy'] += 1.0
            reasons.append("EMA bullish")
        elif ema_fast < ema_slow:
            votes['sell'] += 1.0
            reasons.append("EMA bearish")
        
        # 3. MACD Vote (weight: 1.0) - if available
        if self.use_advanced_indicators and 'macd_histogram' in latest:
            macd_hist = latest.get('macd_histogram', 0)
            if not pd.isna(macd_hist):
                if macd_hist > 0:
                    votes['buy'] += 1.0
                    reasons.append("MACD bullish")
                elif macd_hist < 0:
                    votes['sell'] += 1.0
                    reasons.append("MACD bearish")
        
        # 4. Bollinger Bands Vote (weight: 1.0) - if available
        if self.use_advanced_indicators and 'bb_upper' in latest and 'bb_lower' in latest:
            bb_upper = latest.get('bb_upper')
            bb_lower = latest.get('bb_lower')
            if not pd.isna(bb_upper) and not pd.isna(bb_lower):
                if current_price <= bb_lower:
                    votes['buy'] += 1.0
                    reasons.append("Price at BB lower (oversold)")
                elif current_price >= bb_upper:
                    votes['sell'] += 1.0
                    reasons.append("Price at BB upper (overbought)")
        
        # 5. OBV Trend Vote (weight: 0.5) - if available
        if self.use_advanced_indicators and 'obv' in latest:
            obv = df_with_indicators['obv']
            if len(obv) >= 10:
                obv_trend, obv_strength = self.indicators.analyze_obv_trend(obv, period=10)
                if obv_trend == 'bullish':
                    votes['buy'] += 0.5
                    reasons.append("OBV bullish")
                elif obv_trend == 'bearish':
                    votes['sell'] += 0.5
                    reasons.append("OBV bearish")
        
        # 6. Ichimoku Vote (weight: 1.0) - if available
        if self.use_advanced_indicators and 'ichimoku_cloud_top' in latest:
            cloud_top = latest.get('ichimoku_cloud_top')
            cloud_bottom = latest.get('ichimoku_cloud_bottom')
            if not pd.isna(cloud_top) and not pd.isna(cloud_bottom):
                if current_price > cloud_top:
                    votes['buy'] += 1.0
                    reasons.append("Price above Ichimoku cloud")
                elif current_price < cloud_bottom:
                    votes['sell'] += 1.0
                    reasons.append("Price below Ichimoku cloud")
        
        # 7. Volume Confirmation (weight: 0.5)
        volume = latest.get('volume', 0)
        avg_volume = latest.get('avg_volume', volume)
        if self._check_volume_confirmation(volume, avg_volume, self.volume_multiplier):
            # Boost the leading vote
            max_vote = max(votes, key=votes.get)
            if max_vote != 'hold':
                votes[max_vote] += 0.5
                reasons.append("Volume confirmed")
        
        # Determine winner
        total_votes = sum(votes.values())
        if total_votes == 0:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason="Classical: No clear signal"
            )
        
        max_action = max(votes, key=votes.get)
        confidence = votes[max_action] / total_votes
        
        # Require minimum confidence threshold
        if confidence >= 0.55:  # At least 55% confidence
            signal_type = SignalType.BUY if max_action == 'buy' else (
                SignalType.SELL if max_action == 'sell' else SignalType.HOLD
            )
            reason = f"Classical: {', '.join(reasons[:3])}"  # Top 3 reasons
            
            logger.info(f"📊 Classical Analysis: {signal_type.value.upper()} "
                       f"(confidence={confidence:.0%}, votes={votes})")
            
            return Signal(
                type=signal_type,
                confidence=confidence,
                reason=reason
            )
        else:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"Classical: Low confidence ({confidence:.0%})"
            )
    
    def _merge_signals(self, classical: Signal, ai: Signal) -> Signal:
        """
        PHASE 2.2: Merge classical and AI signals.
        
        Strategy:
        - If both agree: High confidence
        - If disagree: Take higher confidence signal
        - If both HOLD: HOLD
        
        Args:
            classical: Signal from classical analysis
            ai: Signal from AI analysis
            
        Returns:
            Merged signal
        """
        # Both agree
        if classical.type == ai.type:
            merged_confidence = (classical.confidence + ai.confidence) / 2
            return Signal(
                type=classical.type,
                confidence=min(merged_confidence * 1.2, 1.0),  # Boost agreement
                reason=f"Classical + AI agree: {classical.reason[:50]} | {ai.reason[:50]}"
            )
        
        # Disagreement: take higher confidence
        if classical.confidence > ai.confidence:
            return Signal(
                type=classical.type,
                confidence=classical.confidence * 0.9,  # Slight penalty for disagreement
                reason=f"Classical stronger: {classical.reason[:80]}"
            )
        else:
            return Signal(
                type=ai.type,
                confidence=ai.confidence * 0.9,
                reason=f"AI stronger: {ai.reason[:80]}"
            )
        
    def _check_confirmation(self, signal: Signal) -> Signal:
        """
        Check if signal has required confirmation bars.
        
        Requires N consecutive bars with the same signal type (BUY/SELL) before
        allowing the signal to pass through. HOLD signals are always allowed.
        
        Args:
            signal: Current signal
            
        Returns:
            Signal (may be converted to HOLD if confirmation not met)
        """
        if self.confirmation_bars <= 0:
            return signal
            
        # HOLD signals don't need confirmation
        if signal.type == SignalType.HOLD:
            return signal
            
        # Add current signal to history
        self.signal_history.append(signal.type)
        
        # Keep only recent history (last confirmation_bars + 1)
        max_history = self.confirmation_bars + 1
        if len(self.signal_history) > max_history:
            self.signal_history = self.signal_history[-max_history:]
        
        # Check if we have enough history
        if len(self.signal_history) < self.confirmation_bars:
            logger.debug(f"Confirmation: {len(self.signal_history)}/{self.confirmation_bars} bars - waiting")
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"Awaiting confirmation: {len(self.signal_history)}/{self.confirmation_bars} bars"
            )
        
        # Check if last N signals are the same as current
        recent_signals = self.signal_history[-self.confirmation_bars:]
        if all(s == signal.type for s in recent_signals):
            logger.info(f"✅ Confirmation met: {self.confirmation_bars} consecutive {signal.type.value.upper()} signals")
            return signal
        else:
            logger.debug(f"Confirmation not met: mixed signals in last {self.confirmation_bars} bars")
            return Signal(
                type=SignalType.HOLD,
                confidence=0.5,
                reason=f"Confirmation not met: inconsistent signals"
            )
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Analyze market data using enhanced strategy.
        
        PHASE 2 UPDATES:
        - Relaxed thresholds (RSI 35/65, volume 1.2x, EMA 0.3%)
        - Advanced indicators (MACD, Bollinger Bands, ATR, OBV, Ichimoku)
        - Hybrid mode: Classical analysis + AI confirmation
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Trading signal (classical, AI, or hybrid)
        """
        if df.empty or len(df) < max(self.rsi_period, self.ema_slow_period) + 1:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for indicators"
            )
        
        # Calculate all indicators (basic + advanced if enabled)
        df_with_indicators = self._calculate_indicators(df)
        
        # PHASE 2.2: Hybrid Mode
        if self.hybrid_mode:
            # Step 1: Get classical analysis
            classical_signal = self._classical_analysis(df_with_indicators)
            
            # Step 2: If classical is high confidence, use it directly
            if classical_signal.confidence >= 0.70:
                logger.info(f"🎯 High-confidence classical signal, skipping AI: {classical_signal.type.value.upper()}")
                # Apply confirmation check
                return self._check_confirmation(classical_signal)
            
            # Step 3: Otherwise, get AI opinion and merge
            if self.grok and self.grok.enabled:
                logger.info(f"🤔 Classical confidence low ({classical_signal.confidence:.0%}), consulting AI...")
                # Use the existing AI analysis path
                enhanced_data = self._prepare_enhanced_data(df_with_indicators)
                ai_signal = self._get_grok_decision_with_filters(enhanced_data, df_with_indicators)
                
                # Merge signals
                merged_signal = self._merge_signals(classical_signal, ai_signal)
                logger.info(f"🔀 Hybrid decision: {merged_signal.type.value.upper()} (confidence={merged_signal.confidence:.0%})")
                # Apply confirmation check
                return self._check_confirmation(merged_signal)
            else:
                # No AI available, use classical
                return self._check_confirmation(classical_signal)
        
        # Non-hybrid mode: original AI-first approach with filters
        result = self._analyze_original_mode(df_with_indicators)
        # Apply confirmation check
        return self._check_confirmation(result)
    
    def _prepare_enhanced_data(self, df_with_indicators: pd.DataFrame) -> Dict[str, Any]:
        """
        Prepare enhanced market data with all indicators and filters.
        
        Args:
            df_with_indicators: DataFrame with calculated indicators
            
        Returns:
            Dictionary with all market data, indicators, and filter results
        """
        # Get latest and previous data
        latest = df_with_indicators.iloc[-1]
        prev = df_with_indicators.iloc[-2]
        
        current_price = latest['close']
        rsi = latest.get('rsi', 50)
        ema_fast = latest.get('ema_fast', current_price)
        ema_slow = latest.get('ema_slow', current_price)
        volume = latest.get('volume', 0)
        avg_volume = latest.get('avg_volume', volume)
        
        # Determine trend
        if ema_fast > ema_slow:
            trend = "bullish"
        elif ema_fast < ema_slow:
            trend = "bearish"
        else:
            trend = "neutral"
        
        # Price change
        price_change = ((current_price - prev['close']) / prev['close']) * 100
        
        # Apply filters
        volume_ok = self._check_volume_confirmation(volume, avg_volume, multiplier=self.volume_multiplier)
        has_crossover, crossover_direction = self._check_ema_crossover(df_with_indicators)
        has_divergence, divergence_type = self._check_divergence(df_with_indicators)
        ema_distance_ok = self._check_ema_distance(ema_fast, ema_slow, min_distance=self.min_ema_distance)
        
        return {
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
    
    def _analyze_original_mode(self, df_with_indicators: pd.DataFrame) -> Signal:
        """
        Original AI-first analysis mode (non-hybrid).
        
        Args:
            df_with_indicators: DataFrame with calculated indicators
            
        Returns:
            Signal from AI or fallback logic
        """
        # Prepare enhanced data
        enhanced_data = self._prepare_enhanced_data(df_with_indicators)
        
        # Log filter status
        logger.debug(f"📊 Filters: volume={enhanced_data['volume_ok']}, "
                    f"crossover={enhanced_data['has_crossover']}({enhanced_data['crossover_direction']}), "
                    f"divergence={enhanced_data['has_divergence']}({enhanced_data['divergence_type']}), "
                    f"ema_dist={enhanced_data['ema_distance_ok']}")
        
        # If AI available, use it with filters
        if self.grok and self.grok.enabled:
            return self._get_grok_decision_with_filters(enhanced_data, df_with_indicators)
        else:
            # Fallback: enhanced logic with filters
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
