"""
Market Analyst Agent - AI-Powered Market Analysis

Analyzes market conditions using chain-of-thought reasoning.
Uses GPT-4o-mini for fast, cost-efficient analysis.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from loguru import logger

from yunmin.memory.trade_history import TradeHistory


class MarketAnalystAgent:
    """
    Market analyst agent with step-by-step reasoning.
    
    Analyzes market using:
    1. Market regime identification
    2. Pattern recognition from memory
    3. Hypothesis generation
    4. Risk-adjusted decision
    """
    
    def __init__(
        self,
        memory: Optional[TradeHistory] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize market analyst agent.
        
        Args:
            memory: TradeHistory for RAG
            api_key: OpenAI API key (from env if not provided)
            model: Model to use (gpt-4o-mini recommended)
        """
        self.memory = memory or TradeHistory()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("⚠️  OpenAI API key not found - agent will use rule-based fallback")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"🤖 Market Analyst Agent initialized with {model}")
    
    async def analyze(
        self,
        market_context: Dict[str, Any],
        risk_tolerance: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze market and make trading decision.
        
        Args:
            market_context: Rich market context (price, indicators, orderbook, etc.)
            risk_tolerance: Risk tolerance level (0-1)
            
        Returns:
            Analysis result with decision, confidence, and reasoning chain
        """
        logger.info("🔍 Starting market analysis...")
        
        # Step 1: Identify market regime
        regime = self._identify_regime(market_context)
        logger.debug(f"Step 1: Market regime = {regime}")
        
        # Step 2: Find similar situations in memory
        similar_cases = self.memory.recall_similar(market_context, top_k=5)
        logger.debug(f"Step 2: Found {len(similar_cases)} similar cases")
        
        # Step 3: Generate hypotheses
        hypotheses = self._generate_hypotheses(regime, similar_cases, market_context)
        logger.debug(f"Step 3: Generated {len(hypotheses)} hypotheses")
        
        # Step 4: Evaluate each hypothesis
        evaluated = [self._evaluate_hypothesis(h, market_context) for h in hypotheses]
        logger.debug(f"Step 4: Evaluated {len(evaluated)} hypotheses")
        
        # Step 5: Select best with risk consideration
        best = self._select_best(evaluated, risk_tolerance)
        logger.debug(f"Step 5: Selected best action = {best['action']}")
        
        result = {
            'decision': best['action'],
            'confidence': best['confidence'],
            'reasoning_chain': {
                'regime': regime,
                'similar_cases': similar_cases,
                'hypotheses': hypotheses,
                'evaluation': evaluated,
                'selected': best
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"✅ Analysis complete: {result['decision']} (confidence: {result['confidence']:.2f})")
        return result
    
    def _identify_regime(self, context: Dict[str, Any]) -> str:
        """
        Identify current market regime.
        
        Regimes: trending_up, trending_down, ranging, high_volatility, low_volatility
        """
        indicators = context.get('indicators', {})
        
        # Get key indicators
        rsi = indicators.get('rsi', 50)
        ema_fast = indicators.get('ema_fast', 0)
        ema_slow = indicators.get('ema_slow', 0)
        volatility = context.get('volatility', 0.02)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        
        # Determine regime
        if volatility > 0.05:
            regime = "high_volatility"
        elif volatility < 0.015:
            regime = "low_volatility"
        elif ema_fast > ema_slow * 1.01 and rsi > 50:
            regime = "trending_up"
        elif ema_fast < ema_slow * 0.99 and rsi < 50:
            regime = "trending_down"
        else:
            regime = "ranging"
        
        return regime
    
    def _generate_hypotheses(
        self,
        regime: str,
        similar_cases: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate trading hypotheses based on regime and history.
        """
        hypotheses = []
        
        # Hypothesis 1: Follow the trend
        if regime in ["trending_up", "trending_down"]:
            action = "BUY" if regime == "trending_up" else "SELL"
            hypotheses.append({
                'name': 'trend_following',
                'action': action,
                'rationale': f'Market is {regime}, follow the trend',
                'base_confidence': 0.7
            })
        
        # Hypothesis 2: Mean reversion in ranging market
        if regime == "ranging":
            indicators = context.get('indicators', {})
            rsi = indicators.get('rsi', 50)
            
            if rsi < 30:
                hypotheses.append({
                    'name': 'mean_reversion_buy',
                    'action': 'BUY',
                    'rationale': 'Oversold in ranging market, expect bounce',
                    'base_confidence': 0.6
                })
            elif rsi > 70:
                hypotheses.append({
                    'name': 'mean_reversion_sell',
                    'action': 'SELL',
                    'rationale': 'Overbought in ranging market, expect pullback',
                    'base_confidence': 0.6
                })
        
        # Hypothesis 3: Learn from similar cases
        if similar_cases:
            successful_cases = [c for c in similar_cases if c['outcome'].get('pnl', 0) > 0]
            if successful_cases:
                # Most common successful action
                actions = [c['decision'].get('action', 'HOLD') for c in successful_cases]
                if actions:
                    most_common = max(set(actions), key=actions.count)
                    hypotheses.append({
                        'name': 'historical_pattern',
                        'action': most_common,
                        'rationale': f'Similar situations in the past: {len(successful_cases)} successes',
                        'base_confidence': 0.8
                    })
        
        # Hypothesis 4: Stay out in high volatility
        if regime == "high_volatility":
            hypotheses.append({
                'name': 'high_volatility_caution',
                'action': 'HOLD',
                'rationale': 'High volatility, reduce risk',
                'base_confidence': 0.5
            })
        
        # Always have a HOLD option
        if not any(h['action'] == 'HOLD' for h in hypotheses):
            hypotheses.append({
                'name': 'cautious_hold',
                'action': 'HOLD',
                'rationale': 'No clear signal, wait for better opportunity',
                'base_confidence': 0.5
            })
        
        return hypotheses
    
    def _evaluate_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a hypothesis against current context.
        """
        # Start with base confidence
        confidence = hypothesis['base_confidence']
        
        # Adjust based on additional factors
        indicators = context.get('indicators', {})
        
        # RSI confirmation
        rsi = indicators.get('rsi', 50)
        if hypothesis['action'] == 'BUY' and rsi < 40:
            confidence += 0.1
        elif hypothesis['action'] == 'SELL' and rsi > 60:
            confidence += 0.1
        
        # Volume confirmation
        volume_ratio = indicators.get('volume_ratio', 1.0)
        if volume_ratio > 1.2:
            confidence += 0.05
        
        # Price momentum
        price_change = context.get('price_change_pct', 0.0)
        if hypothesis['action'] == 'BUY' and price_change > 0:
            confidence += 0.05
        elif hypothesis['action'] == 'SELL' and price_change < 0:
            confidence += 0.05
        
        # Cap confidence at 0.95
        confidence = min(confidence, 0.95)
        
        return {
            **hypothesis,
            'confidence': confidence
        }
    
    def _select_best(
        self,
        evaluated: List[Dict[str, Any]],
        risk_tolerance: float
    ) -> Dict[str, Any]:
        """
        Select best hypothesis considering risk tolerance.
        """
        if not evaluated:
            return {
                'action': 'HOLD',
                'confidence': 0.5,
                'rationale': 'No clear signal'
            }
        
        # Filter by risk tolerance
        acceptable = [h for h in evaluated if h['confidence'] >= risk_tolerance]
        
        if not acceptable:
            # If nothing meets risk tolerance, HOLD
            return {
                'action': 'HOLD',
                'confidence': 0.5,
                'rationale': 'Insufficient confidence for action'
            }
        
        # Select highest confidence
        best = max(acceptable, key=lambda x: x['confidence'])
        
        return best
    
    def _use_llm_analysis(
        self,
        market_context: Dict[str, Any],
        similar_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Use LLM for more sophisticated analysis (optional, more expensive).
        
        This would use OpenAI API for deeper reasoning.
        Currently not implemented to keep costs low.
        """
        # TODO: Implement LLM-based analysis for production
        # This would create a prompt with market context and similar cases
        # and ask GPT-4o-mini for analysis
        
        logger.warning("LLM-based analysis not yet implemented, using rule-based")
        return {'action': 'HOLD', 'confidence': 0.5, 'rationale': 'LLM not available'}
