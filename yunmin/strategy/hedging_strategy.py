"""
Portfolio Hedging Strategy

Automatic position hedging through inverse positions or correlated pairs.
Implements delta hedging, cost-benefit analysis, and dynamic hedge ratio adjustment.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from loguru import logger
from enum import Enum


class HedgeType(Enum):
    """Type of hedge position."""
    INVERSE_PAIR = "inverse_pair"  # SHORT on correlated pair
    SHORT_SAME = "short_same"  # SHORT on same asset
    NONE = "none"


@dataclass
class HedgePosition:
    """Represents a hedge position."""
    symbol: str  # Hedging symbol
    size: float  # Hedge size in base currency
    hedge_ratio: float  # Ratio of hedge to main position (0.0 to 1.0)
    hedge_type: HedgeType
    cost: float = 0.0  # Cost to open hedge (fees, slippage)
    main_position_symbol: str = ""  # Symbol of the main position being hedged
    main_position_size: float = 0.0  # Size of main position
    
    @property
    def is_active(self) -> bool:
        """Check if hedge is active."""
        return self.size > 0


@dataclass
class HedgingDecision:
    """Decision about whether to hedge."""
    should_hedge: bool
    hedge_ratio: float  # Recommended hedge ratio
    hedge_symbol: str  # Symbol to use for hedging
    hedge_type: HedgeType
    reason: str
    cost_estimate: float = 0.0
    benefit_estimate: float = 0.0
    
    @property
    def is_beneficial(self) -> bool:
        """Check if hedge is beneficial (benefits > costs)."""
        return self.benefit_estimate > self.cost_estimate


class HedgingRules:
    """Hedging rules and thresholds."""
    
    def __init__(
        self,
        min_position_size_for_hedge: float = 0.50,  # Minimum 50% portfolio exposure to consider hedging
        base_hedge_ratio: float = 0.25,  # Base hedge ratio (25% SHORT)
        high_uncertainty_threshold: float = 0.7,  # Uncertainty threshold
        max_hedge_ratio: float = 0.50,  # Maximum hedge ratio
        min_hedge_benefit: float = 0.001,  # Minimum benefit to justify hedge
    ):
        """
        Initialize hedging rules.
        
        Args:
            min_position_size_for_hedge: Minimum position size to trigger hedging
            base_hedge_ratio: Base hedge ratio to use
            high_uncertainty_threshold: Threshold for high uncertainty
            max_hedge_ratio: Maximum allowed hedge ratio
            min_hedge_benefit: Minimum net benefit required
        """
        self.min_position_size_for_hedge = min_position_size_for_hedge
        self.base_hedge_ratio = base_hedge_ratio
        self.high_uncertainty_threshold = high_uncertainty_threshold
        self.max_hedge_ratio = max_hedge_ratio
        self.min_hedge_benefit = min_hedge_benefit


class CostBenefitAnalyzer:
    """Analyzes cost vs benefit of hedging."""
    
    def __init__(
        self,
        trading_fee_rate: float = 0.001,  # 0.1% trading fee
        slippage_rate: float = 0.0005,  # 0.05% slippage
    ):
        """
        Initialize cost-benefit analyzer.
        
        Args:
            trading_fee_rate: Trading fee as fraction
            slippage_rate: Expected slippage as fraction
        """
        self.trading_fee_rate = trading_fee_rate
        self.slippage_rate = slippage_rate
    
    def calculate_hedge_cost(
        self,
        hedge_size: float,
        price: float
    ) -> float:
        """
        Calculate cost to open hedge position.
        
        Args:
            hedge_size: Size of hedge position
            price: Current price
            
        Returns:
            Total cost (fees + slippage)
        """
        position_value = hedge_size * price
        
        # Trading fees
        fee_cost = position_value * self.trading_fee_rate
        
        # Slippage cost
        slippage_cost = position_value * self.slippage_rate
        
        total_cost = fee_cost + slippage_cost
        
        logger.debug(
            "Hedge cost: fees={:.2f}, slippage={:.2f}, total={:.2f}",
            fee_cost, slippage_cost, total_cost
        )
        
        return total_cost
    
    def estimate_hedge_benefit(
        self,
        position_value: float,
        hedge_ratio: float,
        expected_volatility: float,
        time_horizon_days: float = 1.0
    ) -> float:
        """
        Estimate benefit of hedging (risk reduction value).
        
        Args:
            position_value: Value of position being hedged
            hedge_ratio: Hedge ratio
            expected_volatility: Expected volatility (as fraction)
            time_horizon_days: Time horizon in days
            
        Returns:
            Estimated benefit in currency units
        """
        # Calculate potential loss without hedge
        potential_loss_unhedged = position_value * expected_volatility * (time_horizon_days ** 0.5)
        
        # Calculate potential loss with hedge
        # Hedge reduces risk proportionally to hedge ratio
        risk_reduction_factor = 1.0 - hedge_ratio
        potential_loss_hedged = potential_loss_unhedged * risk_reduction_factor
        
        # Benefit is the risk reduction
        benefit = potential_loss_unhedged - potential_loss_hedged
        
        logger.debug(
            "Hedge benefit: unhedged_risk={:.2f}, hedged_risk={:.2f}, benefit={:.2f}",
            potential_loss_unhedged, potential_loss_hedged, benefit
        )
        
        return benefit
    
    def analyze(
        self,
        position_value: float,
        hedge_ratio: float,
        hedge_size: float,
        price: float,
        volatility: float
    ) -> Tuple[float, float, float]:
        """
        Full cost-benefit analysis.
        
        Args:
            position_value: Value of main position
            hedge_ratio: Proposed hedge ratio
            hedge_size: Size of hedge
            price: Current price
            volatility: Market volatility
            
        Returns:
            Tuple of (cost, benefit, net_benefit)
        """
        cost = self.calculate_hedge_cost(hedge_size, price)
        benefit = self.estimate_hedge_benefit(position_value, hedge_ratio, volatility)
        net_benefit = benefit - cost
        
        logger.info(
            "Cost-benefit analysis: cost={:.2f}, benefit={:.2f}, net={:.2f}",
            cost, benefit, net_benefit
        )
        
        return cost, benefit, net_benefit


class HedgingStrategy:
    """
    Portfolio hedging strategy for risk management.
    
    Features:
    - Delta hedging for crypto positions
    - Automatic hedge ratio calculation
    - Cost-benefit analysis
    - Dynamic hedge adjustment
    """
    
    # Inverse pair mapping (for hedging BTC/USDT with BTC/BUSD, etc.)
    INVERSE_PAIRS = {
        'BTC/USDT': 'BTC/BUSD',
        'ETH/USDT': 'ETH/BUSD',
        'BTC/BUSD': 'BTC/USDT',
        'ETH/BUSD': 'ETH/USDT',
    }
    
    def __init__(
        self,
        rules: Optional[HedgingRules] = None,
        analyzer: Optional[CostBenefitAnalyzer] = None,
        enable_auto_hedge: bool = False
    ):
        """
        Initialize hedging strategy.
        
        Args:
            rules: Hedging rules (uses defaults if None)
            analyzer: Cost-benefit analyzer (uses defaults if None)
            enable_auto_hedge: Enable automatic hedging
        """
        self.rules = rules or HedgingRules()
        self.analyzer = analyzer or CostBenefitAnalyzer()
        self.enable_auto_hedge = enable_auto_hedge
        
        # Track active hedges
        self.active_hedges: Dict[str, HedgePosition] = {}
        
        logger.info("HedgingStrategy initialized with auto_hedge={}", enable_auto_hedge)
    
    def get_hedge_symbol(self, main_symbol: str) -> Optional[str]:
        """
        Get appropriate symbol for hedging.
        
        Args:
            main_symbol: Main position symbol
            
        Returns:
            Hedge symbol or None if no suitable pair
        """
        # Try to find inverse pair
        if main_symbol in self.INVERSE_PAIRS:
            return self.INVERSE_PAIRS[main_symbol]
        
        # Could extend to find correlated pairs
        # For now, return same symbol for SHORT on same asset
        return main_symbol
    
    def should_hedge_position(
        self,
        position_symbol: str,
        position_size: float,
        position_value: float,
        portfolio_value: float,
        volatility: float,
        uncertainty: Optional[float] = None,
        price: float = 0.0
    ) -> HedgingDecision:
        """
        Determine if a position should be hedged.
        
        Args:
            position_symbol: Symbol of the position
            position_size: Position size in base currency
            position_value: Value of the position
            portfolio_value: Total portfolio value
            volatility: Current market volatility
            uncertainty: Market uncertainty level (0-1)
            price: Current price of the asset
            
        Returns:
            HedgingDecision
        """
        # Calculate position exposure as fraction of portfolio
        exposure = position_value / portfolio_value if portfolio_value > 0 else 0
        
        # Check if position is large enough to hedge
        if exposure < self.rules.min_position_size_for_hedge:
            return HedgingDecision(
                should_hedge=False,
                hedge_ratio=0.0,
                hedge_symbol="",
                hedge_type=HedgeType.NONE,
                reason=f"Position exposure {exposure:.1%} below minimum threshold {self.rules.min_position_size_for_hedge:.1%}"
            )
        
        # Determine hedge ratio based on uncertainty and volatility
        base_ratio = self.rules.base_hedge_ratio
        
        # Increase hedge ratio in high uncertainty
        if uncertainty and uncertainty > self.rules.high_uncertainty_threshold:
            hedge_ratio = min(base_ratio * 1.5, self.rules.max_hedge_ratio)
            reason = f"High uncertainty ({uncertainty:.1%}) - increased hedge ratio"
        else:
            hedge_ratio = base_ratio
            reason = f"Normal conditions - standard hedge ratio"
        
        # Adjust for high volatility
        if volatility > 0.03:  # High volatility
            hedge_ratio = min(hedge_ratio * 1.25, self.rules.max_hedge_ratio)
            reason += " with volatility adjustment"
        
        # Get hedge symbol
        hedge_symbol = self.get_hedge_symbol(position_symbol)
        
        # Determine hedge type
        if hedge_symbol and hedge_symbol != position_symbol:
            hedge_type = HedgeType.INVERSE_PAIR
        else:
            hedge_type = HedgeType.SHORT_SAME
            hedge_symbol = position_symbol
        
        # Calculate hedge size
        hedge_size = position_size * hedge_ratio
        
        # Perform cost-benefit analysis
        if price > 0:
            cost, benefit, net_benefit = self.analyzer.analyze(
                position_value, hedge_ratio, hedge_size, price, volatility
            )
            
            # Only hedge if beneficial
            if net_benefit < self.rules.min_hedge_benefit:
                return HedgingDecision(
                    should_hedge=False,
                    hedge_ratio=hedge_ratio,
                    hedge_symbol=hedge_symbol,
                    hedge_type=hedge_type,
                    reason=f"Hedge not beneficial: net benefit {net_benefit:.2f} below threshold",
                    cost_estimate=cost,
                    benefit_estimate=benefit
                )
            
            return HedgingDecision(
                should_hedge=True,
                hedge_ratio=hedge_ratio,
                hedge_symbol=hedge_symbol,
                hedge_type=hedge_type,
                reason=reason,
                cost_estimate=cost,
                benefit_estimate=benefit
            )
        
        # If no price provided, just return recommendation without cost analysis
        return HedgingDecision(
            should_hedge=True,
            hedge_ratio=hedge_ratio,
            hedge_symbol=hedge_symbol,
            hedge_type=hedge_type,
            reason=reason
        )
    
    def create_hedge(
        self,
        main_symbol: str,
        main_size: float,
        decision: HedgingDecision
    ) -> HedgePosition:
        """
        Create a hedge position based on decision.
        
        Args:
            main_symbol: Main position symbol
            main_size: Main position size
            decision: Hedging decision
            
        Returns:
            HedgePosition object
        """
        hedge_size = main_size * decision.hedge_ratio
        
        hedge = HedgePosition(
            symbol=decision.hedge_symbol,
            size=hedge_size,
            hedge_ratio=decision.hedge_ratio,
            hedge_type=decision.hedge_type,
            cost=decision.cost_estimate,
            main_position_symbol=main_symbol,
            main_position_size=main_size
        )
        
        # Store active hedge
        self.active_hedges[main_symbol] = hedge
        
        logger.info(
            "Created hedge: {} {} SHORT on {} (ratio={:.1%}, type={})",
            hedge_size, decision.hedge_symbol, main_symbol,
            decision.hedge_ratio, decision.hedge_type.value
        )
        
        return hedge
    
    def adjust_hedge(
        self,
        main_symbol: str,
        new_main_size: float,
        price: float,
        volatility: float
    ) -> Optional[HedgePosition]:
        """
        Adjust existing hedge based on main position changes.
        
        Args:
            main_symbol: Main position symbol
            new_main_size: New size of main position
            price: Current price
            volatility: Current volatility
            
        Returns:
            Updated HedgePosition or None if no adjustment needed
        """
        if main_symbol not in self.active_hedges:
            logger.debug("No active hedge for {}", main_symbol)
            return None
        
        hedge = self.active_hedges[main_symbol]
        
        # Calculate required hedge size for current ratio
        required_hedge_size = new_main_size * hedge.hedge_ratio
        
        # Check if adjustment is needed (>5% difference)
        size_diff = abs(required_hedge_size - hedge.size) / hedge.size if hedge.size > 0 else 1.0
        
        if size_diff < 0.05:
            logger.debug("Hedge adjustment not needed (diff={:.1%})", size_diff)
            return None
        
        # Update hedge size
        old_size = hedge.size
        hedge.size = required_hedge_size
        hedge.main_position_size = new_main_size
        
        logger.info(
            "Adjusted hedge for {}: {:.4f} -> {:.4f} (main position: {:.4f})",
            main_symbol, old_size, hedge.size, new_main_size
        )
        
        return hedge
    
    def close_hedge(self, main_symbol: str) -> bool:
        """
        Close hedge for a position.
        
        Args:
            main_symbol: Main position symbol
            
        Returns:
            True if hedge was closed, False if no hedge existed
        """
        if main_symbol in self.active_hedges:
            hedge = self.active_hedges.pop(main_symbol)
            logger.info("Closed hedge for {}: {} {}", main_symbol, hedge.size, hedge.symbol)
            return True
        
        return False
    
    def get_active_hedges(self) -> List[HedgePosition]:
        """
        Get all active hedge positions.
        
        Returns:
            List of active HedgePosition objects
        """
        return list(self.active_hedges.values())
    
    def get_hedge_summary(self) -> Dict[str, Any]:
        """
        Get summary of hedging status.
        
        Returns:
            Summary dictionary
        """
        active_count = len(self.active_hedges)
        total_hedge_value = sum(
            hedge.size for hedge in self.active_hedges.values()
        )
        
        return {
            "auto_hedge_enabled": self.enable_auto_hedge,
            "active_hedges_count": active_count,
            "active_hedges": [
                {
                    "main_symbol": hedge.main_position_symbol,
                    "hedge_symbol": hedge.symbol,
                    "hedge_size": hedge.size,
                    "hedge_ratio": hedge.hedge_ratio,
                    "hedge_type": hedge.hedge_type.value,
                }
                for hedge in self.active_hedges.values()
            ],
            "total_hedge_value": total_hedge_value,
            "rules": {
                "min_position_for_hedge": self.rules.min_position_size_for_hedge,
                "base_hedge_ratio": self.rules.base_hedge_ratio,
                "max_hedge_ratio": self.rules.max_hedge_ratio,
            }
        }
