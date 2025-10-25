"""
Risk Manager

Central risk management system that enforces all risk policies.
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from yunmin.risk.policies import (
    RiskPolicy,
    RiskCheckResult,
    OrderRequest,
    PositionInfo,
    MaxPositionSizePolicy,
    MaxLeveragePolicy,
    MaxDailyDrawdownPolicy,
    StopLossPolicy,
    MarginCheckPolicy,
    CircuitBreakerPolicy
)
from yunmin.core.config import RiskConfig


class RiskManager:
    """
    Manages all risk policies and validates trading decisions.
    
    This is the CRITICAL safety component - all orders must pass through here.
    """
    
    def __init__(self, config: RiskConfig):
        """
        Initialize risk manager with policies.
        
        Args:
            config: Risk configuration
        """
        self.config = config
        self.policies: List[RiskPolicy] = []
        self._setup_policies()
        
        logger.info("Risk Manager initialized with {} policies", len(self.policies))
        
    def _setup_policies(self):
        """Setup default risk policies based on configuration."""
        self.policies = [
            MaxPositionSizePolicy(self.config.max_position_size),
            MaxLeveragePolicy(self.config.max_leverage),
            MaxDailyDrawdownPolicy(self.config.max_daily_drawdown),
            StopLossPolicy(self.config.stop_loss_pct),
            MarginCheckPolicy(),
        ]
        
        # Circuit breaker is always enabled if configured
        if self.config.enable_circuit_breaker:
            self.circuit_breaker = CircuitBreakerPolicy()
            self.policies.append(self.circuit_breaker)
        else:
            self.circuit_breaker = None
            
    def add_policy(self, policy: RiskPolicy):
        """Add a custom risk policy."""
        self.policies.append(policy)
        logger.info(f"Added custom risk policy: {policy.name}")
        
    def validate_order(
        self, 
        order: OrderRequest, 
        context: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate an order against all risk policies.
        
        Args:
            order: Order to validate
            context: Trading context (capital, positions, etc.)
            
        Returns:
            Tuple of (is_approved, messages)
        """
        messages = []
        warnings = []
        approved = True
        
        logger.debug(f"Validating order: {order.side} {order.amount} {order.symbol}")
        
        for policy in self.policies:
            result, message = policy.check(order, context)
            
            if result == RiskCheckResult.REJECTED:
                approved = False
                messages.append(f"[{policy.name}] REJECTED: {message}")
                logger.warning(f"Order rejected by {policy.name}: {message}")
            elif result == RiskCheckResult.WARNING:
                warnings.append(f"[{policy.name}] WARNING: {message}")
                logger.warning(f"Order warning from {policy.name}: {message}")
            else:
                logger.debug(f"Order passed {policy.name}")
                
        # Add warnings to messages but don't reject
        messages.extend(warnings)
        
        if approved:
            logger.info(f"Order APPROVED: {order.side} {order.amount} {order.symbol}")
        else:
            logger.error(f"Order REJECTED: {order.side} {order.amount} {order.symbol}")
            
        return approved, messages
        
    def check_position(self, position: PositionInfo) -> tuple[bool, str]:
        """
        Check if an open position should be closed due to risk limits.
        
        Args:
            position: Current position information
            
        Returns:
            Tuple of (should_close, reason)
        """
        # Check stop loss
        for policy in self.policies:
            if isinstance(policy, StopLossPolicy):
                result, message = policy.check_position(position)
                if result == RiskCheckResult.REJECTED:
                    logger.error(f"Position {position.symbol} hit stop loss: {message}")
                    return True, message
                    
        # Check take profit (if configured)
        if self.config.take_profit_pct > 0:
            if position.pnl_percentage >= self.config.take_profit_pct * 100:
                message = f"Position hit take profit: {position.pnl_percentage:.2f}%"
                logger.info(message)
                return True, message
                
        return False, "Position within risk limits"
        
    def trigger_circuit_breaker(self, reason: str):
        """
        Trigger emergency circuit breaker to halt all trading.
        
        Args:
            reason: Reason for triggering circuit breaker
        """
        if self.circuit_breaker:
            self.circuit_breaker.trigger(reason)
            logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")
        else:
            logger.error("Circuit breaker not enabled but trigger requested")
            
    def reset_circuit_breaker(self):
        """Reset the circuit breaker to resume trading."""
        if self.circuit_breaker:
            self.circuit_breaker.reset()
            logger.warning("Circuit breaker reset - trading resumed")
            
    def is_circuit_breaker_triggered(self) -> bool:
        """Check if circuit breaker is currently triggered."""
        if self.circuit_breaker:
            return self.circuit_breaker.is_triggered
        return False
        
    def get_risk_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of current risk status.
        
        Args:
            context: Trading context
            
        Returns:
            Risk summary dictionary
        """
        summary = {
            "circuit_breaker_active": self.is_circuit_breaker_triggered(),
            "policies_count": len(self.policies),
            "max_position_size": self.config.max_position_size,
            "max_leverage": self.config.max_leverage,
            "max_daily_drawdown": self.config.max_daily_drawdown,
        }
        
        # Add daily drawdown status
        for policy in self.policies:
            if isinstance(policy, MaxDailyDrawdownPolicy):
                if policy.daily_start_capital:
                    current_capital = context.get('capital', 0)
                    current_drawdown = (policy.daily_start_capital - current_capital) / policy.daily_start_capital
                    summary['current_daily_drawdown'] = current_drawdown
                    summary['daily_start_capital'] = policy.daily_start_capital
                    
        return summary
