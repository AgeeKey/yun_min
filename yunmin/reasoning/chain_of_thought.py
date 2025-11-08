"""
Chain of Thought Reasoning - Step-by-Step Decision Making

Implements chain-of-thought reasoning for transparent AI decisions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class ChainOfThoughtReasoning:
    """
    Chain-of-thought reasoning for trading decisions.
    
    Steps:
    1. Observation: What do we see?
    2. Analysis: What does it mean?
    3. Hypothesis: What could happen?
    4. Decision: What should we do?
    5. Confidence: How sure are we?
    """
    
    def __init__(self):
        """Initialize chain-of-thought reasoning."""
        logger.info("🧠 Chain-of-Thought Reasoning initialized")
    
    def reason(
        self,
        market_context: Dict[str, Any],
        analyst_output: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        memory: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Apply chain-of-thought reasoning to trading decision.
        
        Args:
            market_context: Market conditions
            analyst_output: Market analyst's analysis
            risk_assessment: Risk assessor's evaluation
            memory: Similar past situations
            
        Returns:
            Reasoning chain with final decision
        """
        logger.debug("🧠 Starting chain-of-thought reasoning...")
        
        reasoning_chain = {
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }
        
        # Step 1: Observation
        observation = self._step_observe(market_context)
        reasoning_chain['steps'].append(observation)
        
        # Step 2: Analysis
        analysis = self._step_analyze(market_context, analyst_output)
        reasoning_chain['steps'].append(analysis)
        
        # Step 3: Memory recall
        memory_step = self._step_recall_memory(memory)
        reasoning_chain['steps'].append(memory_step)
        
        # Step 4: Hypothesis generation
        hypothesis = self._step_hypothesize(analysis, memory_step)
        reasoning_chain['steps'].append(hypothesis)
        
        # Step 5: Risk evaluation
        risk_step = self._step_evaluate_risk(hypothesis, risk_assessment)
        reasoning_chain['steps'].append(risk_step)
        
        # Step 6: Final decision
        decision = self._step_decide(risk_step, analyst_output)
        reasoning_chain['steps'].append(decision)
        
        # Extract final values
        reasoning_chain['final_decision'] = decision['decision']
        reasoning_chain['confidence'] = decision['confidence']
        reasoning_chain['rationale'] = decision['rationale']
        
        logger.info(f"✅ Reasoning complete: {decision['decision']} (confidence: {decision['confidence']:.2f})")
        return reasoning_chain
    
    def _step_observe(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1: Observe market conditions."""
        indicators = context.get('indicators', {})
        
        observations = []
        
        # Price and trend
        price = context.get('price', 0)
        trend = context.get('trend', 'neutral')
        observations.append(f"Price: ${price:.2f}, Trend: {trend}")
        
        # RSI
        rsi = indicators.get('rsi', 50)
        rsi_state = 'oversold' if rsi < 30 else 'overbought' if rsi > 70 else 'neutral'
        observations.append(f"RSI: {rsi:.1f} ({rsi_state})")
        
        # Volume
        volume_ratio = indicators.get('volume_ratio', 1.0)
        volume_state = 'high' if volume_ratio > 1.2 else 'low' if volume_ratio < 0.8 else 'normal'
        observations.append(f"Volume: {volume_state} ({volume_ratio:.2f}x average)")
        
        # Volatility
        volatility = context.get('volatility', 0.02)
        vol_state = 'high' if volatility > 0.04 else 'low' if volatility < 0.015 else 'moderate'
        observations.append(f"Volatility: {vol_state} ({volatility:.3f})")
        
        return {
            'step': 1,
            'name': 'Observation',
            'observations': observations,
            'summary': f"Market is {trend} with {rsi_state} RSI and {vol_state} volatility"
        }
    
    def _step_analyze(
        self,
        context: Dict[str, Any],
        analyst_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 2: Analyze what the observations mean."""
        analysis_points = []
        
        # Trend analysis
        trend = context.get('trend', 'neutral')
        if trend == 'bullish':
            analysis_points.append("Uptrend suggests buying pressure")
        elif trend == 'bearish':
            analysis_points.append("Downtrend suggests selling pressure")
        else:
            analysis_points.append("Sideways market, waiting for breakout")
        
        # Momentum analysis
        indicators = context.get('indicators', {})
        macd = indicators.get('macd', 0)
        if macd > 0:
            analysis_points.append("Positive MACD indicates bullish momentum")
        else:
            analysis_points.append("Negative MACD indicates bearish momentum")
        
        # Market regime
        regime = analyst_output.get('reasoning_chain', {}).get('regime', 'unknown')
        analysis_points.append(f"Market regime: {regime}")
        
        return {
            'step': 2,
            'name': 'Analysis',
            'analysis_points': analysis_points,
            'summary': '; '.join(analysis_points[:2])
        }
    
    def _step_recall_memory(
        self,
        memory: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Step 3: Recall similar situations from memory."""
        if not memory:
            return {
                'step': 3,
                'name': 'Memory Recall',
                'findings': ['No similar situations found in memory'],
                'summary': 'No historical precedent'
            }
        
        findings = []
        successful = [m for m in memory if m.get('outcome', {}).get('pnl', 0) > 0]
        
        if successful:
            findings.append(f"Found {len(successful)} successful similar trades")
            
            # Most common action
            actions = [m.get('decision', {}).get('action', 'HOLD') for m in successful]
            if actions:
                most_common = max(set(actions), key=actions.count)
                findings.append(f"Most successful action: {most_common}")
        else:
            findings.append("Similar situations mostly resulted in losses")
        
        return {
            'step': 3,
            'name': 'Memory Recall',
            'findings': findings,
            'summary': findings[0] if findings else 'No memory'
        }
    
    def _step_hypothesize(
        self,
        analysis: Dict[str, Any],
        memory: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 4: Generate hypotheses about what to do."""
        hypotheses = []
        
        # Based on analysis
        analysis_summary = analysis.get('summary', '')
        if 'bullish' in analysis_summary.lower():
            hypotheses.append("Consider opening LONG position")
        elif 'bearish' in analysis_summary.lower():
            hypotheses.append("Consider opening SHORT position")
        
        # Based on memory
        memory_summary = memory.get('summary', '')
        if 'successful' in memory_summary:
            hypotheses.append("Historical patterns support trading this setup")
        
        if not hypotheses:
            hypotheses.append("Wait for clearer signals")
        
        return {
            'step': 4,
            'name': 'Hypothesis',
            'hypotheses': hypotheses,
            'summary': hypotheses[0] if hypotheses else 'No clear hypothesis'
        }
    
    def _step_evaluate_risk(
        self,
        hypothesis: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 5: Evaluate risk of hypothesis."""
        risk_score = risk_assessment.get('risk_score', 50)
        approved = risk_assessment.get('approved', False)
        
        evaluation = []
        
        if risk_score >= 70:
            evaluation.append(f"Risk score is acceptable ({risk_score:.1f}/100)")
        else:
            evaluation.append(f"Risk score is low ({risk_score:.1f}/100)")
        
        if approved:
            evaluation.append("Trade is approved from risk perspective")
        else:
            evaluation.append("Trade is rejected due to risk concerns")
        
        return {
            'step': 5,
            'name': 'Risk Evaluation',
            'evaluation': evaluation,
            'approved': approved,
            'summary': evaluation[0]
        }
    
    def _step_decide(
        self,
        risk_step: Dict[str, Any],
        analyst_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Step 6: Make final decision."""
        if not risk_step.get('approved', False):
            return {
                'step': 6,
                'name': 'Decision',
                'decision': 'HOLD',
                'confidence': 0.5,
                'rationale': 'Insufficient risk score, waiting for better opportunity'
            }
        
        # Use analyst's decision
        decision = analyst_output.get('decision', 'HOLD')
        confidence = analyst_output.get('confidence', 0.5)
        
        return {
            'step': 6,
            'name': 'Decision',
            'decision': decision,
            'confidence': confidence,
            'rationale': f'All checks passed, proceeding with {decision}'
        }
    
    def format_reasoning_chain(self, chain: Dict[str, Any]) -> str:
        """Format reasoning chain as human-readable text."""
        lines = ["🧠 Reasoning Chain:"]
        
        for step in chain.get('steps', []):
            lines.append(f"\n{step['step']}. {step['name']}")
            lines.append(f"   → {step['summary']}")
        
        lines.append(f"\n✅ Final Decision: {chain.get('final_decision', 'HOLD')}")
        lines.append(f"   Confidence: {chain.get('confidence', 0.5):.1%}")
        
        return '\n'.join(lines)
