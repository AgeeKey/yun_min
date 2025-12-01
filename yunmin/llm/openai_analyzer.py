"""
OpenAI Analyzer - Professional Trading AI Integration

Supports all latest OpenAI models:
- GPT-5.1, GPT-5, GPT-4.1, GPT-4o series
- O1, O3, O4 reasoning models
- Mini/Nano variants for high-volume trading

Budget protection via OpenAI dashboard settings.
"""
import os
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIAnalyzer:
    """
    OpenAI LLM analyzer for cryptocurrency trading decisions.
    
    Features:
    - Supports all latest models (GPT-5.1, O3, etc.)
    - Budget protected via OpenAI dashboard
    - Model flexibility with automatic fallback
    - High-volume support (2.5M tokens/day with mini models)
    - Reasoning models for complex analysis
    
    Recommended models:
    - gpt-4o-mini: Best for 24/7 trading (2.5M tokens/day, low cost)
    - o1-mini: Reasoning + high volume (2.5M tokens/day)
    - gpt-5.1-codex-mini: Latest tech + high volume
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize OpenAI analyzer.
        
        Args:
            api_key: OpenAI API key (or from env OPENAI_API_KEY)
            model: Model name (gpt-4o-mini, gpt-5.1, o1-mini, etc.)
                   If None, reads from env YUNMIN_LLM_MODEL or defaults to gpt-4o-mini
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("⚠️ OpenAI API key not found - analyzer disabled")
            self.enabled = False
            return
        
        # Определить модель
        if model is None:
            model = os.getenv("YUNMIN_LLM_MODEL", "gpt-4o-mini")
        
        try:
            self.client = OpenAI(api_key=self.api_key)
            self.model = model
            self.enabled = True
            
            # Вывести информацию о модели
            self._log_model_info()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            self.enabled = False
    
    def _log_model_info(self):
        """Вывести информацию о выбранной модели."""
        model_info = {
            'gpt-5.1': '🚀 GPT-5.1 flagship (250k tokens/day)',
            'gpt-5.1-codex': '💻 GPT-5.1 codex (250k tokens/day)',
            'gpt-5.1-codex-mini': '⚡ GPT-5.1 codex mini (2.5M tokens/day)',
            'gpt-5': '🎯 GPT-5 standard (250k tokens/day)',
            'gpt-5-mini': '⚡ GPT-5 mini (2.5M tokens/day)',
            'gpt-5-nano': '💨 GPT-5 nano (2.5M tokens/day, ultra-fast)',
            'gpt-4.1': '✅ GPT-4.1 proven (250k tokens/day)',
            'gpt-4.1-mini': '⚡ GPT-4.1 mini (2.5M tokens/day)',
            'gpt-4.1-nano': '💨 GPT-4.1 nano (2.5M tokens/day)',
            'gpt-4o': '🎨 GPT-4o multimodal (250k tokens/day)',
            'gpt-4o-mini': '⭐ GPT-4o mini RECOMMENDED (2.5M tokens/day)',
            'o1': '🧠 O1 reasoning (250k tokens/day)',
            'o1-mini': '🧠⚡ O1-mini reasoning (2.5M tokens/day)',
            'o3': '🧠🚀 O3 advanced reasoning (250k tokens/day)',
            'o3-mini': '🧠⚡ O3-mini reasoning (2.5M tokens/day)',
            'o4-mini': '🧠🚀⚡ O4-mini next-gen (2.5M tokens/day)',
        }
        
        info = model_info.get(self.model, f'📡 {self.model} (custom)')
        logger.info(f"✅ OpenAI analyzer: {info}")
    
    def analyze_market(self, market_data: dict) -> dict:
        """
        Analyze market data and generate trading signal.
        
        Compatible with GrokAnalyzer interface for easy switching.
        
        Args:
            market_data: Current market conditions (price, rsi, ema, volume, etc.)
            
        Returns:
            {
                'signal': 'BUY' | 'SELL' | 'HOLD',
                'confidence': float (0-1),
                'reasoning': str,
                'model_used': str
            }
        """
        if not self.enabled:
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reasoning': 'OpenAI analyzer disabled',
                'model_used': None
            }
        
        # Build comprehensive prompt
        prompt = self._build_market_prompt(market_data)
        
        # ⚠️ DEBUG: Log request details
        try:
            with open("gpt_request_debug.txt", "w", encoding="utf-8") as f:
                f.write(f"MODEL: {self.model}\n")
                f.write(f"API KEY EXISTS: {bool(self.api_key)}\n")
                f.write(f"ENABLED: {self.enabled}\n")
                f.write(f"PROMPT:\n{prompt}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            logger.error(f"Debug request write failed: {e}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Expert crypto trader. Analyze technical data. Format: SIGNAL: [BUY/SELL/HOLD]\nCONFIDENCE: [0-1]\nREASONING: [brief analysis]"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=200  # Reduced from 400 for token economy
            )
            
            # Parse response
            raw_content = response.choices[0].message.content
            content = raw_content.strip() if raw_content else "EMPTY_RESPONSE"
            
            # ⚠️ TEMPORARY DEBUG: Save full response to file (avoid encoding issues)
            try:
                with open("gpt_response_debug.txt", "w", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"RAW OPENAI RESPONSE (gpt-4o-mini):\n")
                    f.write(f"{'='*60}\n")
                    f.write(f"TYPE: {type(raw_content)}\n")
                    f.write(f"LEN: {len(raw_content) if raw_content else 0}\n")
                    f.write(f"CONTENT: {content}\n")
                    f.write(f"{'='*60}\n")
            except Exception as e:
                logger.error(f"Debug file write failed: {e}")
            
            result = self._parse_response(content)
            result['model_used'] = self.model
            
            # Log usage
            tokens_used = response.usage.total_tokens if response.usage else 0
            logger.info(
                f"📊 OpenAI {self.model}: {result['signal']} "
                f"(confidence={result['confidence']:.2f}, tokens={tokens_used})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI analysis failed: {e}")
            return {
                'signal': 'HOLD',
                'confidence': 0.0,
                'reasoning': f'Analysis error: {str(e)}',
                'model_used': self.model
            }
    
    def analyze_market_conditions(self, market_data: Dict[str, Any]) -> str:
        """
        Analyze market conditions (text format for compatibility with Groq).
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Analysis text
        """
        result = self.analyze_market(market_data)
        return f"{result['signal']}: {result['reasoning']}"
    
    def explain_signal(self, signal_type: str, reason: str, market_data: Dict[str, Any]) -> str:
        """
        Generate detailed explanation for a trading signal.
        
        Args:
            signal_type: Signal type (BUY/SELL/HOLD)
            reason: Reason for signal
            market_data: Current market data
            
        Returns:
            Detailed explanation
        """
        if not self.enabled:
            return "OpenAI explanation disabled"
        
        prompt = f"""Explain this cryptocurrency trading signal in detail:

Signal: {signal_type}
Reason: {reason}

Market Context:
- Current Price: ${market_data.get('price', 'N/A')}
- RSI: {market_data.get('rsi', 'N/A')}
- Trend: {market_data.get('trend', 'unknown')}
- Volume: {market_data.get('volume', 'N/A')}

Provide a clear explanation covering:
1. Why this signal makes sense
2. Key technical indicators supporting it
3. Potential risks
4. Expected outcome"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional trading analyst explaining decisions clearly."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=300
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ OpenAI explain_signal failed: {e}")
            return f"Explanation unavailable: {str(e)}"
    
    def analyze_text(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Analyze arbitrary text/prompt using OpenAI (generic analysis method).
        
        Args:
            prompt: Text to analyze
            max_tokens: Maximum response length
            
        Returns:
            Analysis text
        """
        if not self.enabled:
            return "OpenAI analyzer disabled"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful cryptocurrency trading assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ OpenAI analyze_text failed: {e}")
            return f"Analysis failed: {str(e)}"
    
    def _build_market_prompt(self, market_data: dict) -> str:
        """Build compact market analysis prompt with trend awareness."""
        price = market_data.get('price', 0)
        rsi = market_data.get('rsi', 50)
        ema_fast = market_data.get('ema_fast', 0)
        ema_slow = market_data.get('ema_slow', 0)
        trend = market_data.get('trend', 'unknown')
        
        # Calculate trend strength
        trend_strength = "neutral"
        if ema_fast and ema_slow and price:
            price_above_slow = (price / ema_slow - 1) * 100 if ema_slow else 0
            if price_above_slow > 2:
                trend_strength = "strong uptrend"
            elif price_above_slow > 0.5:
                trend_strength = "moderate uptrend"
            elif price_above_slow < -2:
                trend_strength = "strong downtrend"
            elif price_above_slow < -0.5:
                trend_strength = "moderate downtrend"
        
        return f"""BTC Market Analysis:
Price: ${price}
RSI: {rsi}
EMA Fast: {ema_fast}
EMA Slow: {ema_slow}
Trend: {trend} ({trend_strength})
Volume: {market_data.get('volume', 'N/A')}

TRADING RULES:
1. BUY Signals:
   - RSI < 35 (oversold) in any trend
   - RSI 35-50 in moderate/strong uptrend
   - Price near EMA Fast support in uptrend

2. SELL Signals:
   - RSI > 70 (overbought) in any trend
   - RSI 60-70 in moderate/strong downtrend
   - Price at resistance in downtrend

3. HOLD Signals:
   - Unclear signals or conflicting indicators
   - RSI 45-60 in neutral/sideways market
   - Waiting for better entry/exit

4. Trend Considerations:
   - In strong uptrend (>2% above slow EMA): Favor BUY on dips
   - In strong downtrend (<-2% below slow EMA): Favor SELL on rallies
   - In neutral: Use RSI primarily

Analyze and decide: BUY/SELL/HOLD?"""
    
    def _parse_response(self, content: str) -> dict:
        """Parse LLM response into structured format."""
        lines = content.split('\n')
        result = {
            'signal': 'HOLD',
            'confidence': 0.5,
            'reasoning': content
        }
        
        for line in lines:
            line = line.strip()
            if line.startswith('SIGNAL:'):
                signal = line.split(':', 1)[1].strip().upper()
                if signal in ['BUY', 'SELL', 'HOLD']:
                    result['signal'] = signal
            elif line.startswith('CONFIDENCE:'):
                try:
                    conf_str = line.split(':', 1)[1].strip()
                    result['confidence'] = float(conf_str)
                except ValueError:
                    pass
            elif line.startswith('REASONING:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
        
        return result
    
    def get_usage_report(self) -> dict:
        """Get usage statistics (stub for compatibility)."""
        return {
            'model': self.model,
            'enabled': self.enabled,
            'provider': 'openai'
        }


if __name__ == "__main__":
    # Quick test
    analyzer = OpenAIAnalyzer()
    
    if analyzer.enabled:
        test_data = {
            'price': 102000,
            'rsi': 65,
            'ema_fast': 101500,
            'ema_slow': 101000,
            'volume': 25000000,
            'trend': 'bullish'
        }
        
        result = analyzer.analyze_market(test_data)
        print(f"\n🤖 OpenAI Analysis:")
        print(f"   Signal: {result['signal']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Reasoning: {result['reasoning'][:100]}...")
    else:
        print("⚠️ OpenAI analyzer not enabled (check API key)")
