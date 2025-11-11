"""
Base LLM Analyzer Interface

Defines the interface that all LLM analyzers (OpenAI, Groq, etc.) must implement.
This allows strategies to work with any LLM provider without modification.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMAnalyzer(ABC):
    """
    Abstract base class for LLM analyzers.
    
    All LLM providers (OpenAI, Groq, Claude, etc.) should implement this interface
    to be compatible with trading strategies.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.enabled = False
    
    @abstractmethod
    def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market conditions and generate trading signal.
        
        Args:
            market_data: Dictionary with market data (price, rsi, ema, volume, etc.)
            
        Returns:
            Dictionary with:
                - signal: 'BUY' | 'SELL' | 'HOLD'
                - confidence: float (0-1)
                - reasoning: str
                - model_used: str (optional)
        """
        pass
    
    @abstractmethod
    def analyze_market_conditions(self, market_data: Dict[str, Any]) -> str:
        """
        Analyze market conditions and return text description.
        
        Args:
            market_data: Dictionary with market data
            
        Returns:
            Text description of market analysis
        """
        pass
    
    @abstractmethod
    def explain_signal(self, signal_type: str, reason: str, 
                      market_data: Dict[str, Any]) -> str:
        """
        Generate detailed explanation for a trading signal.
        
        Args:
            signal_type: Signal type (BUY/SELL/HOLD)
            reason: Reason for signal
            market_data: Current market data
            
        Returns:
            Detailed explanation text
        """
        pass
    
    @abstractmethod
    def analyze_text(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Analyze arbitrary text/prompt.
        
        Args:
            prompt: Text to analyze
            max_tokens: Maximum response length
            
        Returns:
            Analysis text
        """
        pass


def create_llm_analyzer(provider: str = 'openai', **kwargs) -> Optional[LLMAnalyzer]:
    """
    Factory function to create LLM analyzer based on provider.
    
    Args:
        provider: LLM provider ('openai', 'groq', 'grok')
        **kwargs: Provider-specific arguments (api_key, model, etc.)
        
    Returns:
        LLMAnalyzer instance or None if provider not available
    """
    if provider.lower() in ['openai', 'gpt']:
        from yunmin.llm.openai_analyzer import OpenAIAnalyzer
        return OpenAIAnalyzer(**kwargs)
    elif provider.lower() in ['groq', 'grok']:
        from yunmin.llm.grok_analyzer import GrokAnalyzer
        return GrokAnalyzer(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. "
                        f"Supported: 'openai', 'groq'")
