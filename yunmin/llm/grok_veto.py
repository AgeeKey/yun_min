"""
Grok AI Veto System - проверка торговых сигналов перед исполнением

Интеграция с Grok (xAI) для анализа торговых сигналов:
1. Анализирует рыночную ситуацию
2. Проверяет риски сделки
3. Может наложить veto на опасные сигналы
4. Даёт объяснение решения
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from loguru import logger
from openai import OpenAI


@dataclass
class SignalAnalysis:
    """Результат анализа торгового сигнала"""
    approved: bool  # True если сигнал одобрен, False если veto
    confidence: float  # Уверенность в решении (0.0 - 1.0)
    reasoning: str  # Объяснение решения
    risk_factors: list[str]  # Выявленные риски
    
    # Метрики рисков
    market_condition_score: float  # Оценка рыночных условий (0-10)
    signal_quality_score: float  # Качество сигнала (0-10)
    risk_reward_ratio: float  # Соотношение риск/доходность


class GrokVetoSystem:
    """
    Система контроля торговых сигналов с помощью Grok AI
    
    Grok анализирует:
    - Рыночные условия (тренд, волатильность, объём)
    - Качество сигнала (надёжность индикаторов)
    - Соотношение риск/доходность
    - Макроэкономический контекст
    
    Может наложить veto если:
    - Слишком высокий риск
    - Плохие рыночные условия
    - Сомнительное качество сигнала
    - Неблагоприятный макроконтекст
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "grok-beta",
        min_approval_confidence: float = 0.7,
        max_risk_score: float = 7.0
    ):
        """
        Args:
            api_key: xAI API ключ (или из GROK_API_KEY env var)
            model: Модель Grok ('grok-beta')
            min_approval_confidence: Мин уверенность для одобрения (0.7 = 70%)
            max_risk_score: Макс допустимый риск (0-10 шкала)
        """
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Grok API key required. Set GROK_API_KEY env var or pass api_key"
            )
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        self.model = model
        self.min_approval_confidence = min_approval_confidence
        self.max_risk_score = max_risk_score
        
        logger.info(
            f"GrokVetoSystem initialized "
            f"(min confidence: {min_approval_confidence*100}%, "
            f"max risk: {max_risk_score}/10)"
        )
    
    def analyze_signal(
        self,
        symbol: str,
        side: str,  # 'buy' или 'sell'
        current_price: float,
        signal_reason: str,
        market_data: Dict[str, Any]
    ) -> SignalAnalysis:
        """
        Проанализировать торговый сигнал
        
        Args:
            symbol: Торговая пара (e.g., 'BTC/USDT')
            side: 'buy' или 'sell'
            current_price: Текущая цена
            signal_reason: Причина сигнала (e.g., "RSI oversold + MACD bullish")
            market_data: Дополнительные данные (volume, volatility, trend, etc.)
        
        Returns:
            SignalAnalysis с решением
        """
        logger.info(
            f"Analyzing {side.upper()} signal for {symbol} @ ${current_price:,.2f}"
        )
        
        # Создать промпт для Grok
        prompt = self._create_analysis_prompt(
            symbol, side, current_price, signal_reason, market_data
        )
        
        try:
            # Запросить анализ у Grok
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Низкая температура для консистентности
                max_tokens=1000
            )
            
            # Парсить ответ
            analysis = self._parse_grok_response(
                response.choices[0].message.content
            )
            
            # Логировать решение
            if analysis.approved:
                logger.success(
                    f"✅ APPROVED {side.upper()} {symbol} "
                    f"(confidence: {analysis.confidence*100:.0f}%, "
                    f"risk: {analysis.market_condition_score:.1f}/10)"
                )
            else:
                logger.warning(
                    f"❌ VETO {side.upper()} {symbol}: {analysis.reasoning}"
                )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Grok analysis failed: {e}")
            # В случае ошибки - осторожно отклонить
            return SignalAnalysis(
                approved=False,
                confidence=0.0,
                reasoning=f"Analysis failed: {str(e)}",
                risk_factors=["API_ERROR"],
                market_condition_score=0.0,
                signal_quality_score=0.0,
                risk_reward_ratio=0.0
            )
    
    def _get_system_prompt(self) -> str:
        """Системный промпт для Grok"""
        return f"""You are a professional cryptocurrency trading risk analyst.

Your job is to analyze trading signals and decide whether to APPROVE or VETO them.

Guidelines:
1. Consider market conditions (trend, volatility, volume)
2. Evaluate signal quality (indicator reliability, confluence)
3. Assess risk/reward ratio
4. Check for macro risks (news, events, correlations)

Decision criteria:
- APPROVE if confidence >= {self.min_approval_confidence*100}% AND risk <= {self.max_risk_score}/10
- VETO if risk is too high or confidence is low

Respond in this exact JSON format:
{{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Clear explanation",
  "risk_factors": ["factor1", "factor2"],
  "market_condition_score": 0-10,
  "signal_quality_score": 0-10,
  "risk_reward_ratio": float
}}

Be conservative - when in doubt, VETO."""
    
    def _create_analysis_prompt(
        self,
        symbol: str,
        side: str,
        price: float,
        reason: str,
        market_data: Dict[str, Any]
    ) -> str:
        """Создать промпт для анализа"""
        # Извлечь данные
        volume_24h = market_data.get('volume_24h', 'N/A')
        volatility = market_data.get('volatility', 'N/A')
        trend = market_data.get('trend', 'N/A')
        rsi = market_data.get('rsi', 'N/A')
        macd = market_data.get('macd', 'N/A')
        
        prompt = f"""Analyze this trading signal:

📊 SIGNAL DETAILS:
- Symbol: {symbol}
- Side: {side.upper()}
- Price: ${price:,.2f}
- Reason: {reason}

📈 MARKET DATA:
- 24h Volume: {volume_24h}
- Volatility: {volatility}
- Trend: {trend}
- RSI: {rsi}
- MACD: {macd}

Should I execute this trade or veto it?
Provide analysis in JSON format."""
        
        return prompt
    
    def _parse_grok_response(self, response: str) -> SignalAnalysis:
        """
        Парсить ответ Grok
        
        Ожидается JSON формат:
        {
          "approved": bool,
          "confidence": float,
          "reasoning": str,
          "risk_factors": [str],
          "market_condition_score": float,
          "signal_quality_score": float,
          "risk_reward_ratio": float
        }
        """
        import json
        
        try:
            # Извлечь JSON из ответа (может быть обёрнут в markdown)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]  # Убрать ```json
            if response.startswith("```"):
                response = response[3:]  # Убрать ```
            if response.endswith("```"):
                response = response[:-3]
            
            data = json.loads(response.strip())
            
            # Валидировать и создать SignalAnalysis
            return SignalAnalysis(
                approved=bool(data.get('approved', False)),
                confidence=float(data.get('confidence', 0.0)),
                reasoning=str(data.get('reasoning', 'No reason provided')),
                risk_factors=list(data.get('risk_factors', [])),
                market_condition_score=float(data.get('market_condition_score', 0.0)),
                signal_quality_score=float(data.get('signal_quality_score', 0.0)),
                risk_reward_ratio=float(data.get('risk_reward_ratio', 0.0))
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Grok response: {e}")
            logger.debug(f"Raw response: {response}")
            
            # Резервный парсинг по ключевым словам
            approved = 'approve' in response.lower() and 'veto' not in response.lower()
            
            return SignalAnalysis(
                approved=approved,
                confidence=0.5,
                reasoning=response[:200],  # Первые 200 символов
                risk_factors=['PARSE_ERROR'],
                market_condition_score=5.0,
                signal_quality_score=5.0,
                risk_reward_ratio=1.0
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику работы (placeholder для будущего)"""
        return {
            'total_signals_analyzed': 0,
            'approved': 0,
            'vetoed': 0,
            'avg_confidence': 0.0
        }
