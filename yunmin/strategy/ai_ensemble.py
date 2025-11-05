"""
Multi-Model AI Ensemble Strategy

Combines predictions from multiple LLM models (Groq, OpenRouter, OpenAI) 
for more reliable trading signals through consensus-based decision making.
"""

import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from loguru import logger
import requests

from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class ModelProvider(Enum):
    """Available LLM providers."""
    GROQ = "groq"
    OPENROUTER = "openrouter"
    OPENAI = "openai"


@dataclass
class ModelPrediction:
    """Prediction from a single model."""
    provider: ModelProvider
    signal_type: SignalType
    confidence: float
    reasoning: str
    success: bool = True
    error: Optional[str] = None


class AIEnsembleStrategy(BaseStrategy):
    """
    Multi-model AI ensemble trading strategy.
    
    Features:
    - Aggregates predictions from 3+ LLM models
    - Confidence-based weighted voting
    - Disagreement detection with fallback logic
    - Meta-analysis for consensus signals
    """
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        enable_groq: bool = True,
        enable_openrouter: bool = True,
        enable_openai: bool = True,
        consensus_threshold: float = 0.6,
        min_models: int = 2
    ):
        """
        Initialize AI Ensemble strategy.
        
        Args:
            groq_api_key: Groq API key (defaults to env GROQ_API_KEY)
            openrouter_api_key: OpenRouter API key (defaults to env OPENROUTER_API_KEY)
            openai_api_key: OpenAI API key (defaults to env OPENAI_API_KEY)
            enable_groq: Enable Groq Llama 3.3 70B
            enable_openrouter: Enable OpenRouter Llama 3.3 70B
            enable_openai: Enable OpenAI GPT-4o-mini
            consensus_threshold: Minimum agreement ratio for HIGH confidence (0.0-1.0)
            min_models: Minimum number of models required for consensus
        """
        super().__init__("AI_Ensemble")
        
        # API keys
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # Model configuration
        self.enabled_models: List[ModelProvider] = []
        if enable_groq and self.groq_api_key:
            self.enabled_models.append(ModelProvider.GROQ)
            logger.info("✓ Groq (Llama 3.3 70B) enabled")
        if enable_openrouter and self.openrouter_api_key:
            self.enabled_models.append(ModelProvider.OPENROUTER)
            logger.info("✓ OpenRouter (Llama 3.3 70B) enabled")
        if enable_openai and self.openai_api_key:
            self.enabled_models.append(ModelProvider.OPENAI)
            logger.info("✓ OpenAI (GPT-4o-mini) enabled")
        
        if len(self.enabled_models) < min_models:
            logger.warning(
                f"⚠️  Only {len(self.enabled_models)} models enabled. "
                f"Minimum {min_models} recommended for ensemble."
            )
        
        self.consensus_threshold = consensus_threshold
        self.min_models = min_models
        
        # Model endpoints
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.openai_url = "https://api.openai.com/v1/chat/completions"
        
        # Model names
        self.groq_model = "llama-3.3-70b-versatile"
        self.openrouter_model = "meta-llama/llama-3.3-70b-instruct"
        self.openai_model = "gpt-4o-mini"
        
        # Disagreement tracking
        self.disagreements: List[Dict[str, Any]] = []
        
        logger.info(f"🤖 AI Ensemble initialized with {len(self.enabled_models)} models")
    
    def analyze(self, df: pd.DataFrame) -> Signal:
        """
        Analyze market data using ensemble of AI models.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Consensus trading signal
        """
        if df.empty or len(df) < 20:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="Insufficient data for AI analysis"
            )
        
        # Prepare market context
        market_data = self._prepare_market_context(df)
        
        # Get predictions from all enabled models
        predictions = self._get_all_predictions(market_data)
        
        # Filter successful predictions
        valid_predictions = [p for p in predictions if p.success]
        
        if len(valid_predictions) < self.min_models:
            logger.warning(
                f"Only {len(valid_predictions)}/{len(self.enabled_models)} models responded. "
                "Using fallback logic."
            )
            return self._fallback_signal(market_data, predictions)
        
        # Perform meta-analysis and generate consensus
        consensus_signal = self._meta_analysis(valid_predictions, market_data)
        
        return consensus_signal
    
    def _prepare_market_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Prepare market context for AI analysis.
        
        Args:
            df: Market data DataFrame
            
        Returns:
            Dictionary with market indicators and context
        """
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Calculate basic indicators
        close_prices = df['close'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        
        # Simple moving averages
        sma_20 = df['close'].rolling(window=20).mean().iloc[-1]
        sma_50 = df['close'].rolling(window=min(50, len(df))).mean().iloc[-1]
        
        # Volatility
        returns = df['close'].pct_change()
        volatility = returns.std() * 100
        
        # Price change
        price_change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100
        
        return {
            'price': latest['close'],
            'prev_price': prev['close'],
            'price_change_pct': price_change_pct,
            'high_24h': df['high'].tail(288).max() if len(df) >= 288 else df['high'].max(),
            'low_24h': df['low'].tail(288).min() if len(df) >= 288 else df['low'].min(),
            'volume': latest['volume'],
            'sma_20': sma_20,
            'sma_50': sma_50,
            'volatility': volatility,
            'trend': 'bullish' if latest['close'] > sma_20 else 'bearish'
        }
    
    def _get_all_predictions(self, market_data: Dict[str, Any]) -> List[ModelPrediction]:
        """
        Get predictions from all enabled models.
        
        Args:
            market_data: Market context dictionary
            
        Returns:
            List of model predictions
        """
        predictions = []
        
        for provider in self.enabled_models:
            try:
                prediction = self._get_model_prediction(provider, market_data)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Error getting prediction from {provider.value}: {e}")
                predictions.append(ModelPrediction(
                    provider=provider,
                    signal_type=SignalType.HOLD,
                    confidence=0.0,
                    reasoning=f"Error: {str(e)}",
                    success=False,
                    error=str(e)
                ))
        
        return predictions
    
    def _get_model_prediction(
        self, 
        provider: ModelProvider, 
        market_data: Dict[str, Any]
    ) -> ModelPrediction:
        """
        Get prediction from a specific model.
        
        Args:
            provider: Model provider
            market_data: Market context
            
        Returns:
            Model prediction
        """
        prompt = self._create_trading_prompt(market_data)
        
        try:
            response_text = self._call_llm(provider, prompt)
            signal_type, confidence, reasoning = self._parse_llm_response(response_text)
            
            return ModelPrediction(
                provider=provider,
                signal_type=signal_type,
                confidence=confidence,
                reasoning=reasoning,
                success=True
            )
        except Exception as e:
            logger.error(f"{provider.value} prediction failed: {e}")
            return ModelPrediction(
                provider=provider,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="",
                success=False,
                error=str(e)
            )
    
    def _create_trading_prompt(self, market_data: Dict[str, Any]) -> str:
        """
        Create trading prompt for LLM.
        
        Args:
            market_data: Market context
            
        Returns:
            Formatted prompt string
        """
        return f"""Analyze this crypto market data and provide a trading signal.

Market Data:
- Current Price: ${market_data['price']:.2f}
- Price Change: {market_data['price_change_pct']:.2f}%
- 24h High: ${market_data['high_24h']:.2f}
- 24h Low: ${market_data['low_24h']:.2f}
- SMA 20: ${market_data['sma_20']:.2f}
- SMA 50: ${market_data['sma_50']:.2f}
- Volatility: {market_data['volatility']:.2f}%
- Trend: {market_data['trend']}

Provide your analysis in this exact format:
SIGNAL: [BUY/SELL/HOLD]
CONFIDENCE: [0-100]
REASONING: [Brief explanation in 1-2 sentences]

Consider:
1. Trend direction and momentum
2. Support/resistance levels
3. Volatility and risk
4. Market sentiment

Be decisive but realistic. Only recommend BUY/SELL with high confidence if conditions are clear."""
    
    def _call_llm(self, provider: ModelProvider, prompt: str, timeout: int = 30) -> str:
        """
        Call LLM API.
        
        Args:
            provider: Model provider
            prompt: User prompt
            timeout: Request timeout in seconds
            
        Returns:
            LLM response text
        """
        if provider == ModelProvider.GROQ:
            return self._call_groq(prompt, timeout)
        elif provider == ModelProvider.OPENROUTER:
            return self._call_openrouter(prompt, timeout)
        elif provider == ModelProvider.OPENAI:
            return self._call_openai(prompt, timeout)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _call_groq(self, prompt: str, timeout: int) -> str:
        """Call Groq API with proper error handling."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}"
        }
        
        payload = {
            "model": self.groq_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional cryptocurrency trading analyst. Provide clear, actionable trading signals."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        try:
            response = requests.post(self.groq_url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception(f"Groq API request timed out after {timeout}s")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Groq API request failed: {str(e)}")
    
    def _call_openrouter(self, prompt: str, timeout: int) -> str:
        """Call OpenRouter API with proper error handling."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": "https://github.com/AgeeKey/yun_min",
            "X-Title": "YunMin Trading Bot"
        }
        
        payload = {
            "model": self.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional cryptocurrency trading analyst. Provide clear, actionable trading signals."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        try:
            response = requests.post(self.openrouter_url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception(f"OpenRouter API request timed out after {timeout}s")
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API request failed: {str(e)}")
    
    def _call_openai(self, prompt: str, timeout: int) -> str:
        """Call OpenAI API with proper error handling."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}"
        }
        
        payload = {
            "model": self.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional cryptocurrency trading analyst. Provide clear, actionable trading signals."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 300
        }
        
        try:
            response = requests.post(self.openai_url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise Exception(f"OpenAI API request timed out after {timeout}s")
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
    
    def _parse_llm_response(self, response: str) -> Tuple[SignalType, float, str]:
        """
        Parse LLM response into structured format.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        lines = response.strip().split('\n')
        
        signal_type = SignalType.HOLD
        confidence = 0.5
        reasoning = "No clear reasoning provided"
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("SIGNAL:"):
                signal_str = line.split(":", 1)[1].strip().upper()
                if "BUY" in signal_str:
                    signal_type = SignalType.BUY
                elif "SELL" in signal_str:
                    signal_type = SignalType.SELL
                else:
                    signal_type = SignalType.HOLD
            
            elif line.startswith("CONFIDENCE:"):
                conf_str = line.split(":", 1)[1].strip()
                # Extract number from string
                conf_str = ''.join(c for c in conf_str if c.isdigit() or c == '.')
                if conf_str:
                    confidence = float(conf_str) / 100.0  # Convert to 0-1 range
                    confidence = max(0.0, min(1.0, confidence))
            
            elif line.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()
        
        return signal_type, confidence, reasoning
    
    def _meta_analysis(
        self, 
        predictions: List[ModelPrediction], 
        market_data: Dict[str, Any]
    ) -> Signal:
        """
        Perform meta-analysis on model predictions to generate consensus.
        
        Args:
            predictions: List of valid predictions
            market_data: Market context
            
        Returns:
            Consensus signal
        """
        if not predictions:
            return Signal(
                type=SignalType.HOLD,
                confidence=0.0,
                reason="No valid predictions available"
            )
        
        # Count votes for each signal type
        votes = {SignalType.BUY: 0, SignalType.SELL: 0, SignalType.HOLD: 0}
        weighted_votes = {SignalType.BUY: 0.0, SignalType.SELL: 0.0, SignalType.HOLD: 0.0}
        
        for pred in predictions:
            votes[pred.signal_type] += 1
            weighted_votes[pred.signal_type] += pred.confidence
        
        # Determine consensus
        total_votes = len(predictions)
        max_votes = max(votes.values())
        consensus_signal = max(votes, key=votes.get)
        
        # Calculate consensus strength
        agreement_ratio = max_votes / total_votes
        avg_confidence = weighted_votes[consensus_signal] / max_votes if max_votes > 0 else 0.0
        
        # Detect disagreement
        if agreement_ratio < self.consensus_threshold:
            # Split vote - reduce position or hold
            logger.warning(
                f"⚠️  Split vote detected: {votes}. "
                f"Agreement ratio: {agreement_ratio:.2f} < threshold: {self.consensus_threshold}"
            )
            self.disagreements.append({
                'timestamp': pd.Timestamp.now(),
                'votes': votes,
                'predictions': [
                    {
                        'provider': p.provider.value,
                        'signal': p.signal_type.value,
                        'confidence': p.confidence
                    } for p in predictions
                ],
                'market_data': market_data
            })
            
            # On disagreement, prefer HOLD or reduce confidence
            if consensus_signal != SignalType.HOLD:
                final_confidence = avg_confidence * 0.5  # Reduce confidence by 50%
            else:
                final_confidence = avg_confidence
        else:
            # Strong consensus
            final_confidence = avg_confidence
        
        # Build consensus reasoning
        reasoning_parts = [f"{p.provider.value}: {p.signal_type.value}" for p in predictions]
        consensus_reasoning = (
            f"Ensemble consensus ({agreement_ratio:.0%} agreement): "
            f"{', '.join(reasoning_parts)}. "
            f"Avg confidence: {avg_confidence:.2f}"
        )
        
        return Signal(
            type=consensus_signal,
            confidence=final_confidence,
            reason=consensus_reasoning,
            metadata={
                'votes': votes,
                'agreement_ratio': agreement_ratio,
                'model_count': len(predictions),
                'predictions': [
                    {
                        'provider': p.provider.value,
                        'signal': p.signal_type.value,
                        'confidence': p.confidence,
                        'reasoning': p.reasoning
                    } for p in predictions
                ]
            }
        )
    
    def _fallback_signal(
        self, 
        market_data: Dict[str, Any], 
        predictions: List[ModelPrediction]
    ) -> Signal:
        """
        Generate fallback signal when not enough models respond.
        
        Args:
            market_data: Market context
            predictions: List of all predictions (including failed ones)
            
        Returns:
            Fallback signal
        """
        # Use simple technical analysis as fallback
        price = market_data['price']
        sma_20 = market_data['sma_20']
        trend = market_data['trend']
        
        # Check which models succeeded
        successful = [p.provider.value for p in predictions if p.success]
        failed = [p.provider.value for p in predictions if not p.success]
        
        reason = (
            f"Fallback mode: {len(successful)}/{len(predictions)} models responded. "
            f"Failed: {', '.join(failed)}. "
            f"Using technical analysis: Price ${price:.2f}, SMA20 ${sma_20:.2f}, Trend: {trend}"
        )
        
        # Conservative approach: prefer HOLD when models fail
        if trend == 'bullish' and price > sma_20 * 1.01:
            return Signal(type=SignalType.BUY, confidence=0.3, reason=reason)
        elif trend == 'bearish' and price < sma_20 * 0.99:
            return Signal(type=SignalType.SELL, confidence=0.3, reason=reason)
        else:
            return Signal(type=SignalType.HOLD, confidence=0.5, reason=reason)
    
    def get_disagreement_log(self) -> List[Dict[str, Any]]:
        """
        Get log of model disagreements for analysis.
        
        Returns:
            List of disagreement records
        """
        return self.disagreements
    
    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return {
            'consensus_threshold': self.consensus_threshold,
            'min_models': self.min_models,
            'enabled_models': [m.value for m in self.enabled_models],
            'model_count': len(self.enabled_models)
        }
