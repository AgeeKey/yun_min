"""
Test exchange margin and funding rate monitoring policies.

Tests for Problem #2 fixes: Margin level and funding rate monitoring.
"""

import pytest
from yunmin.risk.policies import (
    ExchangeMarginLevelPolicy,
    FundingRateLimitPolicy,
    OrderRequest,
    RiskCheckResult
)


class TestExchangeMarginLevelPolicy:
    """Test exchange margin level monitoring."""
    
    def test_healthy_margin_level(self):
        """Test approval with healthy margin level."""
        policy = ExchangeMarginLevelPolicy(
            min_margin_level=200.0,
            critical_margin_level=150.0
        )
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'exchange_balance': {
                'margin_level': 300.0  # Healthy level
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED
        assert 'healthy' in message.lower()
    
    def test_low_margin_level_warning(self):
        """Test warning with low margin level."""
        policy = ExchangeMarginLevelPolicy(
            min_margin_level=200.0,
            critical_margin_level=150.0
        )
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'exchange_balance': {
                'margin_level': 180.0  # Low but not critical
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.WARNING
        assert 'low margin level' in message.lower()
    
    def test_critical_margin_level_rejection(self):
        """Test rejection with critical margin level."""
        policy = ExchangeMarginLevelPolicy(
            min_margin_level=200.0,
            critical_margin_level=150.0
        )
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'exchange_balance': {
                'margin_level': 140.0  # Critical!
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.REJECTED
        assert 'critical' in message.lower()
        assert 'liquidation' in message.lower()
    
    def test_no_margin_data_warning(self):
        """Test warning when margin data is missing."""
        policy = ExchangeMarginLevelPolicy()
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'exchange_balance': None  # No data
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.WARNING
        assert 'no exchange balance data' in message.lower()
    
    def test_margin_level_not_applicable(self):
        """Test approval when margin level not applicable (spot trading)."""
        policy = ExchangeMarginLevelPolicy()
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=1.0
        )
        
        context = {
            'capital': 10000,
            'exchange_balance': {
                'margin_level': None  # Not applicable
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED
        assert 'not applicable' in message.lower()


class TestFundingRateLimitPolicy:
    """Test funding rate limit policy."""
    
    def test_acceptable_funding_rate(self):
        """Test approval with acceptable funding rate."""
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'funding_rate': {
                'rate': 0.0001  # 0.01% - acceptable
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED
        assert 'acceptable' in message.lower()
    
    def test_high_positive_funding_rate_rejection(self):
        """Test rejection with high positive funding rate."""
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'funding_rate': {
                'rate': 0.002  # 0.2% - too high!
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.REJECTED
        assert 'too high' in message.lower()
        assert 'funding' in message.lower()
    
    def test_high_negative_funding_rate_rejection(self):
        """Test rejection with high negative funding rate."""
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='sell',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'funding_rate': {
                'rate': -0.0015  # -0.15% - too high in absolute terms
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.REJECTED
        assert 'too high' in message.lower()
    
    def test_no_funding_data_warning(self):
        """Test warning when funding data is missing."""
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'funding_rate': None  # No data
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.WARNING
        assert 'no funding rate data' in message.lower()
    
    def test_zero_funding_rate(self):
        """Test approval with zero funding rate."""
        policy = FundingRateLimitPolicy(max_funding_rate=0.001)
        
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.01,
            leverage=3.0
        )
        
        context = {
            'capital': 10000,
            'funding_rate': {
                'rate': 0.0  # No funding
            }
        }
        
        result, message = policy.check(order, context)
        assert result == RiskCheckResult.APPROVED


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
