"""
Grok AI Analyzer - Trading Intelligence

Uses xAI's Grok model for market analysis and trading insights.
"""

import os
from typing import Dict, Any, Optional
from loguru import logger
import requests


class GrokAnalyzer:
    """
    Grok AI integration for trading analysis.
    
    Capabilities:
    - Market sentiment analysis
    - Trade signal explanation
    - Risk assessment
    - Pattern recognition
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Grok analyzer.
        
        Args:
            api_key: Grok API key (from env if not provided)
        """
        self.api_key = api_key or os.getenv("GROK_API_KEY")
        if not self.api_key:
            logger.warning("Grok API key not found - AI features disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Grok AI analyzer initialized")
            
        # xAI API endpoint
        self.api_url = "https://api.x.ai/v1/chat/completions"
        
    def analyze_market_conditions(self, market_data: Dict[str, Any]) -> str:
        """
        Analyze current market conditions using Grok.
        
        Args:
            market_data: Dictionary with price, indicators, etc.
            
        Returns:
            AI analysis as string
        """
        if not self.enabled:
            return "AI analysis disabled (no API key)"
            
        prompt = f"""Analyze these crypto market conditions:

Price: ${market_data.get('price', 'N/A')}
RSI: {market_data.get('rsi', 'N/A')}
EMA Fast: {market_data.get('ema_fast', 'N/A')}
EMA Slow: {market_data.get('ema_slow', 'N/A')}
Trend: {market_data.get('trend', 'N/A')}
Volume: {market_data.get('volume', 'N/A')}

Provide a brief (2-3 sentences) market analysis focusing on:
1. Current trend strength
2. Key support/resistance levels
3. Trading recommendation (buy/sell/hold)

Be concise and actionable."""

        try:
            response = self._call_grok(prompt)
            logger.info(f"Grok analysis: {response[:100]}...")
            return response
        except Exception as e:
            logger.error(f"Grok analysis failed: {e}")
            return f"Analysis error: {str(e)}"
            
    def explain_signal(self, signal_type: str, reason: str, market_data: Dict[str, Any]) -> str:
        """
        Get AI explanation for a trading signal.
        
        Args:
            signal_type: 'buy', 'sell', or 'hold'
            reason: Original signal reason
            market_data: Market conditions
            
        Returns:
            AI explanation
        """
        if not self.enabled:
            return reason
            
        prompt = f"""Trading signal generated: {signal_type.upper()}

Original reason: {reason}

Market context:
- Price: ${market_data.get('price', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- Trend: {market_data.get('trend', 'N/A')}

Explain why this signal makes sense (or doesn't) in 1-2 sentences. Be direct."""

        try:
            response = self._call_grok(prompt)
            return f"{reason} | Grok: {response}"
        except Exception as e:
            logger.warning(f"Grok explanation failed: {e}")
            return reason
            
    def assess_risk(self, position_size: float, market_volatility: float, account_balance: float) -> str:
        """
        AI-powered risk assessment.
        
        Args:
            position_size: Size of proposed position
            market_volatility: Current volatility (e.g., ATR)
            account_balance: Total account balance
            
        Returns:
            Risk assessment
        """
        if not self.enabled:
            return "Risk analysis unavailable"
            
        risk_pct = (position_size / account_balance) * 100
        
        prompt = f"""Assess this trading risk:

Position Size: ${position_size:.2f}
Account Balance: ${account_balance:.2f}
Risk %: {risk_pct:.2f}%
Market Volatility: {market_volatility}

Rate the risk (Low/Medium/High) and suggest adjustments if needed. 1 sentence."""

        try:
            response = self._call_grok(prompt)
            return response
        except Exception as e:
            logger.warning(f"Grok risk assessment failed: {e}")
            return "Risk assessment unavailable"
            
    def _call_grok(self, prompt: str, max_tokens: int = 150) -> str:
        """
        Call Grok API.
        
        Args:
            prompt: User prompt
            max_tokens: Max response length
            
        Returns:
            Grok response
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional cryptocurrency trading analyst. Provide concise, actionable insights."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "grok-2-1212",
            "stream": False,
            "temperature": 0
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=120  # 2 минуты для больших запросов
        )
        
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
        
    def get_trading_insight(self, context: str) -> str:
        """
        Get general trading insight based on context.
        
        Args:
            context: Trading context/question
            
        Returns:
            AI insight
        """
        if not self.enabled:
            return "AI insights disabled"
            
        try:
            response = self._call_grok(context, max_tokens=200)
            return response
        except Exception as e:
            logger.error(f"Grok insight failed: {e}")
            return "Insight unavailable"
    
    def analyze_text(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Analyze arbitrary text/prompt using Grok.
        
        Args:
            prompt: Text to analyze
            max_tokens: Maximum response length
            
        Returns:
            Grok's analysis
        """
        if not self.enabled:
            return "Grok AI disabled (no API key)"
        
        try:
            response = self._call_grok(prompt, max_tokens=max_tokens)
            return response
        except Exception as e:
            logger.error(f"Grok text analysis failed: {e}")
            return f"Analysis failed: {str(e)}"
