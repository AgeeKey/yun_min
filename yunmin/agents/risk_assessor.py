"""
Risk Assessor Agent - Trade Risk Evaluation

Evaluates risk for proposed trades and calculates optimal position sizes.
Uses Kelly Criterion and risk metrics.
"""

from typing import Dict, Any, Optional
from loguru import logger


class RiskAssessorAgent:
    """
    Risk assessment agent for trade evaluation.
    
    Evaluates:
    - Trade-specific risk score (0-100)
    - Optimal position size using Kelly Criterion
    - Risk/reward ratio
    - Portfolio impact
    """
    
    def __init__(
        self,
        max_position_size: float = 0.1,
        max_leverage: float = 3.0,
        risk_free_rate: float = 0.0
    ):
        """
        Initialize risk assessor.
        
        Args:
            max_position_size: Maximum position size as fraction of capital
            max_leverage: Maximum allowed leverage
            risk_free_rate: Risk-free rate for Sharpe calculation
        """
        self.max_position_size = max_position_size
        self.max_leverage = max_leverage
        self.risk_free_rate = risk_free_rate
        
        logger.info("🛡️  Risk Assessor Agent initialized")
    
    def evaluate(
        self,
        proposed_trade: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate risk for a proposed trade.
        
        Args:
            proposed_trade: Trade proposal (action, confidence, rationale)
            market_context: Current market conditions
            portfolio: Current portfolio state
            
        Returns:
            Risk assessment with score and recommended position size
        """
        logger.debug("🛡️  Evaluating trade risk...")
        
        # Calculate risk components
        market_risk = self._assess_market_risk(market_context)
        confidence_score = proposed_trade.get('confidence', 0.5) * 100
        volatility_risk = self._assess_volatility_risk(market_context)
        portfolio_risk = self._assess_portfolio_risk(proposed_trade, portfolio)
        
        # Combine into overall risk score (0-100, higher is better)
        risk_score = (
            confidence_score * 0.4 +
            (100 - market_risk) * 0.3 +
            (100 - volatility_risk) * 0.2 +
            (100 - portfolio_risk) * 0.1
        )
        
        # Calculate position size
        position_size = self._calculate_position_size(
            confidence=proposed_trade.get('confidence', 0.5),
            risk_score=risk_score / 100,
            market_context=market_context
        )
        
        # Calculate risk/reward
        risk_reward = self._calculate_risk_reward(proposed_trade, market_context)
        
        result = {
            'risk_score': risk_score,
            'recommended_position_size': position_size,
            'risk_reward_ratio': risk_reward,
            'components': {
                'confidence': confidence_score,
                'market_risk': market_risk,
                'volatility_risk': volatility_risk,
                'portfolio_risk': portfolio_risk
            },
            'approved': risk_score >= 70  # Approval threshold
        }
        
        logger.info(f"✅ Risk assessment: score={risk_score:.1f}, size={position_size:.3f}, approved={result['approved']}")
        return result
    
    def _assess_market_risk(self, context: Dict[str, Any]) -> float:
        """
        Assess overall market risk (0-100, lower is better).
        """
        indicators = context.get('indicators', {})
        
        # RSI extremes indicate risk
        rsi = indicators.get('rsi', 50)
        rsi_risk = 0
        if rsi < 20 or rsi > 80:
            rsi_risk = 50
        elif rsi < 30 or rsi > 70:
            rsi_risk = 30
        
        # Volume analysis
        volume_ratio = indicators.get('volume_ratio', 1.0)
        volume_risk = 0
        if volume_ratio < 0.5:  # Low volume is risky
            volume_risk = 40
        elif volume_ratio < 0.8:
            volume_risk = 20
        
        # Trend strength
        ema_fast = indicators.get('ema_fast', 0)
        ema_slow = indicators.get('ema_slow', 0)
        trend_strength = abs(ema_fast - ema_slow) / ema_slow if ema_slow > 0 else 0
        trend_risk = 30 if trend_strength < 0.005 else 10  # Weak trend is risky
        
        market_risk = (rsi_risk + volume_risk + trend_risk) / 3
        return market_risk
    
    def _assess_volatility_risk(self, context: Dict[str, Any]) -> float:
        """
        Assess volatility-based risk (0-100, lower is better).
        """
        volatility = context.get('volatility', 0.02)
        
        # High volatility increases risk
        if volatility > 0.05:
            return 80
        elif volatility > 0.03:
            return 50
        elif volatility > 0.02:
            return 30
        else:
            return 10
    
    def _assess_portfolio_risk(
        self,
        proposed_trade: Dict[str, Any],
        portfolio: Optional[Dict[str, Any]]
    ) -> float:
        """
        Assess risk from portfolio perspective (0-100, lower is better).
        """
        if not portfolio:
            return 20  # Neutral risk if no portfolio info
        
        positions = portfolio.get('positions', [])
        
        # Check if already have position in same direction
        action = proposed_trade.get('action', 'HOLD')
        same_direction = sum(1 for p in positions if p.get('side', '') == action)
        
        if same_direction >= 2:
            return 60  # High risk - too concentrated
        elif same_direction >= 1:
            return 30  # Medium risk
        else:
            return 10  # Low risk - diversified
    
    def _calculate_position_size(
        self,
        confidence: float,
        risk_score: float,
        market_context: Dict[str, Any]
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Args:
            confidence: Decision confidence (0-1)
            risk_score: Overall risk score (0-1)
            market_context: Market conditions
            
        Returns:
            Position size as fraction of capital (0-max_position_size)
        """
        # Kelly Criterion: f = (bp - q) / b
        # where:
        # - b = odds (risk/reward ratio)
        # - p = probability of win (confidence)
        # - q = probability of loss (1 - p)
        
        # Estimate win probability from confidence and risk
        win_probability = (confidence + risk_score) / 2
        
        # Assume risk/reward ratio of 2:1 (conservative)
        risk_reward = 2.0
        
        # Kelly fraction
        kelly_fraction = (risk_reward * win_probability - (1 - win_probability)) / risk_reward
        
        # Use fractional Kelly (25% of full Kelly for safety)
        fractional_kelly = max(0, kelly_fraction * 0.25)
        
        # Cap at maximum position size
        position_size = min(fractional_kelly, self.max_position_size)
        
        # Reduce size in high volatility
        volatility = market_context.get('volatility', 0.02)
        if volatility > 0.04:
            position_size *= 0.5
        elif volatility > 0.03:
            position_size *= 0.75
        
        return position_size
    
    def _calculate_risk_reward(
        self,
        proposed_trade: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> float:
        """
        Calculate expected risk/reward ratio.
        """
        # Use ATR or volatility to estimate potential move
        volatility = market_context.get('volatility', 0.02)
        price = market_context.get('price', 50000)
        
        # Expected move: 2x daily volatility
        expected_move = price * volatility * 2
        
        # Stop loss: 1x daily volatility
        stop_loss = price * volatility
        
        # Risk/reward ratio
        risk_reward = expected_move / stop_loss if stop_loss > 0 else 1.0
        
        return risk_reward
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        market_context: Dict[str, Any]
    ) -> float:
        """
        Calculate optimal stop loss price.
        
        Args:
            entry_price: Entry price
            side: Trade side ('BUY' or 'SELL')
            market_context: Market conditions
            
        Returns:
            Stop loss price
        """
        volatility = market_context.get('volatility', 0.02)
        
        # Stop loss at 1x ATR or 2% (whichever is larger)
        stop_distance = max(entry_price * volatility, entry_price * 0.02)
        
        if side == 'BUY':
            stop_loss = entry_price - stop_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        market_context: Dict[str, Any],
        risk_reward: float = 2.0
    ) -> float:
        """
        Calculate optimal take profit price.
        
        Args:
            entry_price: Entry price
            side: Trade side ('BUY' or 'SELL')
            market_context: Market conditions
            risk_reward: Desired risk/reward ratio
            
        Returns:
            Take profit price
        """
        # Calculate stop loss first
        stop_loss = self.calculate_stop_loss(entry_price, side, market_context)
        
        # Calculate risk
        risk = abs(entry_price - stop_loss)
        
        # Take profit at risk * risk_reward ratio
        reward = risk * risk_reward
        
        if side == 'BUY':
            take_profit = entry_price + reward
        else:  # SELL
            take_profit = entry_price - reward
        
        return take_profit
