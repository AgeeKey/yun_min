"""
Tests for Portfolio Hedging Strategy
"""

import pytest
from yunmin.strategy.hedging_strategy import (
    HedgingStrategy,
    HedgingRules,
    CostBenefitAnalyzer,
    HedgePosition,
    HedgingDecision,
    HedgeType
)


class TestHedgePosition:
    """Test HedgePosition dataclass."""
    
    def test_hedge_position_creation(self):
        """Test hedge position creation."""
        hedge = HedgePosition(
            symbol='BTC/BUSD',
            size=0.5,
            hedge_ratio=0.25,
            hedge_type=HedgeType.INVERSE_PAIR,
            main_position_symbol='BTC/USDT',
            main_position_size=2.0
        )
        
        assert hedge.symbol == 'BTC/BUSD'
        assert hedge.size == 0.5
        assert hedge.hedge_ratio == 0.25
        assert hedge.hedge_type == HedgeType.INVERSE_PAIR
        assert hedge.is_active
    
    def test_hedge_position_inactive(self):
        """Test inactive hedge position."""
        hedge = HedgePosition(
            symbol='BTC/BUSD',
            size=0.0,
            hedge_ratio=0.0,
            hedge_type=HedgeType.NONE
        )
        
        assert not hedge.is_active


class TestHedgingDecision:
    """Test HedgingDecision dataclass."""
    
    def test_beneficial_hedge(self):
        """Test hedge is beneficial when benefit > cost."""
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test",
            cost_estimate=10.0,
            benefit_estimate=50.0
        )
        
        assert decision.is_beneficial
        assert decision.should_hedge
    
    def test_not_beneficial_hedge(self):
        """Test hedge is not beneficial when cost > benefit."""
        decision = HedgingDecision(
            should_hedge=False,
            hedge_ratio=0.0,
            hedge_symbol='',
            hedge_type=HedgeType.NONE,
            reason="Not beneficial",
            cost_estimate=50.0,
            benefit_estimate=10.0
        )
        
        assert not decision.is_beneficial


class TestCostBenefitAnalyzer:
    """Test CostBenefitAnalyzer."""
    
    def test_calculate_hedge_cost(self):
        """Test hedge cost calculation."""
        analyzer = CostBenefitAnalyzer(
            trading_fee_rate=0.001,
            slippage_rate=0.0005
        )
        
        # Hedge size: 0.1, price: 50000
        # Position value: 5000
        # Fee: 5000 * 0.001 = 5
        # Slippage: 5000 * 0.0005 = 2.5
        # Total: 7.5
        cost = analyzer.calculate_hedge_cost(hedge_size=0.1, price=50000)
        
        assert abs(cost - 7.5) < 0.01
    
    def test_estimate_hedge_benefit(self):
        """Test hedge benefit estimation."""
        analyzer = CostBenefitAnalyzer()
        
        # Position value: 10000, hedge ratio: 0.25, volatility: 0.02
        # Unhedged risk: 10000 * 0.02 = 200
        # Risk reduction: 200 * 0.25 = 50
        benefit = analyzer.estimate_hedge_benefit(
            position_value=10000,
            hedge_ratio=0.25,
            expected_volatility=0.02,
            time_horizon_days=1.0
        )
        
        assert benefit > 0
        assert abs(benefit - 50) < 5  # Allow some tolerance
    
    def test_full_analysis(self):
        """Test full cost-benefit analysis."""
        analyzer = CostBenefitAnalyzer()
        
        cost, benefit, net = analyzer.analyze(
            position_value=10000,
            hedge_ratio=0.25,
            hedge_size=0.05,  # 0.05 BTC
            price=50000,
            volatility=0.02
        )
        
        assert cost > 0
        assert benefit > 0
        assert net == benefit - cost


class TestHedgingRules:
    """Test HedgingRules."""
    
    def test_default_rules(self):
        """Test default hedging rules."""
        rules = HedgingRules()
        
        assert rules.min_position_size_for_hedge == 0.50
        assert rules.base_hedge_ratio == 0.25
        assert rules.high_uncertainty_threshold == 0.7
        assert rules.max_hedge_ratio == 0.50
    
    def test_custom_rules(self):
        """Test custom hedging rules."""
        rules = HedgingRules(
            min_position_size_for_hedge=0.30,
            base_hedge_ratio=0.30,
            max_hedge_ratio=0.60
        )
        
        assert rules.min_position_size_for_hedge == 0.30
        assert rules.base_hedge_ratio == 0.30
        assert rules.max_hedge_ratio == 0.60


class TestHedgingStrategy:
    """Test HedgingStrategy."""
    
    def test_initialization(self):
        """Test hedging strategy initialization."""
        strategy = HedgingStrategy(enable_auto_hedge=True)
        
        assert strategy.enable_auto_hedge
        assert strategy.rules is not None
        assert strategy.analyzer is not None
        assert len(strategy.active_hedges) == 0
    
    def test_get_hedge_symbol_inverse_pair(self):
        """Test getting hedge symbol for inverse pairs."""
        strategy = HedgingStrategy()
        
        assert strategy.get_hedge_symbol('BTC/USDT') == 'BTC/BUSD'
        assert strategy.get_hedge_symbol('ETH/USDT') == 'ETH/BUSD'
        assert strategy.get_hedge_symbol('BTC/BUSD') == 'BTC/USDT'
    
    def test_get_hedge_symbol_same_pair(self):
        """Test getting hedge symbol for non-mapped pairs."""
        strategy = HedgingStrategy()
        
        # For unmapped pairs, should return same symbol
        result = strategy.get_hedge_symbol('DOGE/USDT')
        assert result == 'DOGE/USDT'
    
    def test_should_not_hedge_small_position(self):
        """Test that small positions are not hedged."""
        strategy = HedgingStrategy()
        
        decision = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.01,
            position_value=500,  # Only 5% of portfolio
            portfolio_value=10000,
            volatility=0.02,
            price=50000
        )
        
        assert not decision.should_hedge
        assert "below minimum threshold" in decision.reason
    
    def test_should_hedge_large_position(self):
        """Test that large positions trigger hedging."""
        strategy = HedgingStrategy()
        
        decision = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,  # 75% of portfolio
            portfolio_value=10000,
            volatility=0.02,
            price=50000
        )
        
        assert decision.should_hedge
        assert decision.hedge_ratio > 0
        assert decision.hedge_symbol == 'BTC/BUSD'
        assert decision.hedge_type == HedgeType.INVERSE_PAIR
    
    def test_hedge_ratio_increases_with_uncertainty(self):
        """Test hedge ratio increases in high uncertainty."""
        strategy = HedgingStrategy()
        
        # Low uncertainty
        decision_low = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,
            portfolio_value=10000,
            volatility=0.02,
            uncertainty=0.5,
            price=50000
        )
        
        # High uncertainty
        decision_high = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,
            portfolio_value=10000,
            volatility=0.02,
            uncertainty=0.8,
            price=50000
        )
        
        assert decision_high.hedge_ratio > decision_low.hedge_ratio
        assert "High uncertainty" in decision_high.reason
    
    def test_hedge_ratio_increases_with_volatility(self):
        """Test hedge ratio increases with high volatility."""
        strategy = HedgingStrategy()
        
        # Normal volatility
        decision_normal = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,
            portfolio_value=10000,
            volatility=0.01,
            price=50000
        )
        
        # High volatility
        decision_high = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,
            portfolio_value=10000,
            volatility=0.05,
            price=50000
        )
        
        assert decision_high.hedge_ratio > decision_normal.hedge_ratio
    
    def test_create_hedge(self):
        """Test creating a hedge position."""
        strategy = HedgingStrategy()
        
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        
        hedge = strategy.create_hedge(
            main_symbol='BTC/USDT',
            main_size=1.0,
            decision=decision
        )
        
        assert hedge.symbol == 'BTC/BUSD'
        assert hedge.size == 0.25
        assert hedge.hedge_ratio == 0.25
        assert hedge.main_position_symbol == 'BTC/USDT'
        assert hedge.main_position_size == 1.0
        
        # Check it's stored in active hedges
        assert 'BTC/USDT' in strategy.active_hedges
    
    def test_adjust_hedge_not_needed(self):
        """Test hedge adjustment when not needed."""
        strategy = HedgingStrategy()
        
        # Create initial hedge
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision)
        
        # Try to adjust with similar size (no change needed)
        result = strategy.adjust_hedge(
            main_symbol='BTC/USDT',
            new_main_size=1.02,  # Only 2% change
            price=50000,
            volatility=0.02
        )
        
        assert result is None  # No adjustment needed
    
    def test_adjust_hedge_needed(self):
        """Test hedge adjustment when needed."""
        strategy = HedgingStrategy()
        
        # Create initial hedge
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision)
        
        # Adjust with significantly different size
        result = strategy.adjust_hedge(
            main_symbol='BTC/USDT',
            new_main_size=2.0,  # Doubled
            price=50000,
            volatility=0.02
        )
        
        assert result is not None
        assert result.size == 0.5  # Should be 25% of 2.0
        assert result.main_position_size == 2.0
    
    def test_close_hedge(self):
        """Test closing a hedge."""
        strategy = HedgingStrategy()
        
        # Create hedge
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision)
        
        # Close hedge
        result = strategy.close_hedge('BTC/USDT')
        
        assert result is True
        assert 'BTC/USDT' not in strategy.active_hedges
    
    def test_close_nonexistent_hedge(self):
        """Test closing a hedge that doesn't exist."""
        strategy = HedgingStrategy()
        
        result = strategy.close_hedge('BTC/USDT')
        
        assert result is False
    
    def test_get_active_hedges(self):
        """Test getting active hedges."""
        strategy = HedgingStrategy()
        
        assert len(strategy.get_active_hedges()) == 0
        
        # Create a hedge
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision)
        
        hedges = strategy.get_active_hedges()
        assert len(hedges) == 1
        assert hedges[0].symbol == 'BTC/BUSD'
    
    def test_get_hedge_summary(self):
        """Test getting hedge summary."""
        strategy = HedgingStrategy(enable_auto_hedge=True)
        
        # Create a hedge
        decision = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision)
        
        summary = strategy.get_hedge_summary()
        
        assert summary['auto_hedge_enabled'] is True
        assert summary['active_hedges_count'] == 1
        assert len(summary['active_hedges']) == 1
        assert summary['active_hedges'][0]['main_symbol'] == 'BTC/USDT'
        assert summary['active_hedges'][0]['hedge_symbol'] == 'BTC/BUSD'
        assert 'rules' in summary
    
    def test_not_beneficial_hedge_rejected(self):
        """Test that non-beneficial hedges are rejected."""
        # Create analyzer with very high costs
        analyzer = CostBenefitAnalyzer(
            trading_fee_rate=0.1,  # 10% fee (unrealistic)
            slippage_rate=0.05  # 5% slippage (unrealistic)
        )
        
        rules = HedgingRules(min_hedge_benefit=1.0)
        strategy = HedgingStrategy(rules=rules, analyzer=analyzer)
        
        decision = strategy.should_hedge_position(
            position_symbol='BTC/USDT',
            position_size=0.15,
            position_value=7500,
            portfolio_value=10000,
            volatility=0.01,  # Low volatility = low benefit
            price=50000
        )
        
        # Should not hedge because cost > benefit
        assert not decision.should_hedge
        assert "not beneficial" in decision.reason.lower()
    
    def test_multiple_hedges(self):
        """Test managing multiple hedges."""
        strategy = HedgingStrategy()
        
        # Create first hedge
        decision1 = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='BTC/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('BTC/USDT', 1.0, decision1)
        
        # Create second hedge
        decision2 = HedgingDecision(
            should_hedge=True,
            hedge_ratio=0.25,
            hedge_symbol='ETH/BUSD',
            hedge_type=HedgeType.INVERSE_PAIR,
            reason="Test"
        )
        strategy.create_hedge('ETH/USDT', 2.0, decision2)
        
        assert len(strategy.active_hedges) == 2
        assert 'BTC/USDT' in strategy.active_hedges
        assert 'ETH/USDT' in strategy.active_hedges
        
        summary = strategy.get_hedge_summary()
        assert summary['active_hedges_count'] == 2
