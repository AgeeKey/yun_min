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
    CircuitBreakerPolicy,
    ExchangeMarginLevelPolicy,
    FundingRateLimitPolicy
)
from yunmin.risk.dynamic_limits import DynamicRiskLimits
from yunmin.core.config import RiskConfig


class RiskManager:
    """
    Manages all risk policies and validates trading decisions.
    
    This is the CRITICAL safety component - all orders must pass through here.
    """
    
    def __init__(self, config: RiskConfig, enable_dynamic_limits: bool = True):
        """
        Initialize risk manager with policies.
        
        Args:
            config: Risk configuration
            enable_dynamic_limits: Enable dynamic risk limits (default: True)
        """
        self.config = config
        self.policies: List[RiskPolicy] = []
        self._setup_policies()
        
        # Initialize dynamic risk limits
        self.dynamic_limits: Optional[DynamicRiskLimits] = None
        if enable_dynamic_limits:
            self.dynamic_limits = DynamicRiskLimits(
                max_daily_risk=0.02,
                normal_max_position=config.max_position_size,
                high_vol_max_position=config.max_position_size * 0.5,
                max_total_exposure=0.50
            )
            logger.info("Dynamic risk limits enabled")
        
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
        
        # Add exchange margin level monitoring (CRITICAL - Problem #2 fix)
        if hasattr(self.config, 'min_margin_level') and hasattr(self.config, 'critical_margin_level'):
            self.policies.append(
                ExchangeMarginLevelPolicy(
                    min_margin_level=self.config.min_margin_level,
                    critical_margin_level=self.config.critical_margin_level
                )
            )
            logger.info("Exchange margin level monitoring enabled")
        
        # Add funding rate limit (CRITICAL - Problem #2 fix)
        if hasattr(self.config, 'max_funding_rate'):
            self.policies.append(
                FundingRateLimitPolicy(max_funding_rate=self.config.max_funding_rate)
            )
            logger.info("Funding rate limit policy enabled")
        
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
        
    def update_dynamic_limits(self, capital: float, volatility: float):
        """
        Update dynamic risk limits with current market state.
        
        Args:
            capital: Current portfolio capital
            volatility: Current market volatility
        """
        if self.dynamic_limits:
            self.dynamic_limits.update_state(capital, volatility)
            
            # Check for emergency exit condition
            should_exit, reason = self.dynamic_limits.should_emergency_exit()
            if should_exit:
                self.trigger_circuit_breaker(reason)
                logger.critical("Dynamic limits triggered emergency exit: {}", reason)
    
    def get_dynamic_max_position_size(
        self,
        capital: float,
        volatility: float,
        price: float
    ) -> Optional[float]:
        """
        Get dynamic maximum position size.
        
        Args:
            capital: Current capital
            volatility: Asset volatility
            price: Current price
            
        Returns:
            Max position size or None if dynamic limits not enabled
        """
        if self.dynamic_limits:
            return self.dynamic_limits.calculate_max_position_size(capital, volatility, price)
        return None
    
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
        
        # Add dynamic limits summary
        if self.dynamic_limits:
            summary['dynamic_limits'] = self.dynamic_limits.get_state_summary()
                    
        return summary
