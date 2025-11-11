"""
AI Trading Strategy - Multi-Provider LLM Support

DEPRECATED: This file is maintained for backward compatibility.
Use yunmin.strategy.llm_strategy.LLMStrategy instead.

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

from yunmin.strategy.llm_strategy import LLMStrategy


class GrokAIStrategy(LLMStrategy):
    """
    DEPRECATED: Use LLMStrategy instead.
    
    This class is maintained for backward compatibility with existing code.
    It's simply an alias for LLMStrategy.
    """
    
    def __init__(self, grok_analyzer=None, **kwargs):
        """
        Initialize AI trading strategy.
        
        Args:
            grok_analyzer: DEPRECATED parameter name. Use llm_analyzer in LLMStrategy.
                          Any LLM analyzer (OpenAIAnalyzer, GrokAnalyzer, etc.)
            **kwargs: Additional arguments passed to LLMStrategy
        """
        # Map old parameter name to new one
        super().__init__(llm_analyzer=grok_analyzer, **kwargs)
