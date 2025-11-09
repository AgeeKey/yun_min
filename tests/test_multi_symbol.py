"""
Tests for Multi-Symbol Trading Components.

Tests CorrelationAnalyzer and MultiSymbolPortfolioManager.
"""

import pytest
import pandas as pd
import numpy as np
from yunmin.analysis.correlation import CorrelationAnalyzer
from yunmin.agents.portfolio_manager import MultiSymbolPortfolioManager


class TestCorrelationAnalyzer:
    """Test CorrelationAnalyzer functionality."""
    
    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = CorrelationAnalyzer(window=100)
        
        assert analyzer.window == 100
    
    def test_calculate_rolling_correlation_basic(self):
        """Test basic correlation calculation."""
        analyzer = CorrelationAnalyzer(window=50)
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 3000
            }, index=dates)
        }
        
        correlations = analyzer.calculate_rolling_correlation(data)
        
        assert isinstance(correlations, dict)
        assert 'BTC/USDT_ETH/USDT' in correlations
        assert -1 <= correlations['BTC/USDT_ETH/USDT'] <= 1
    
    def test_calculate_rolling_correlation_high_corr(self):
        """Test correlation with highly correlated data."""
        analyzer = CorrelationAnalyzer(window=50)
        
        # Create highly correlated data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        base = np.random.randn(100).cumsum()
        
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': base + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': base * 0.06 + 3000  # Scaled version of base
            }, index=dates)
        }
        
        correlations = analyzer.calculate_rolling_correlation(data)
        
        # Should have high positive correlation
        assert correlations['BTC/USDT_ETH/USDT'] > 0.8
    
    def test_calculate_correlation_matrix(self):
        """Test correlation matrix calculation."""
        analyzer = CorrelationAnalyzer()
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 3000
            }, index=dates),
            'BNB/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 600
            }, index=dates)
        }
        
        matrix = analyzer.calculate_correlation_matrix(data)
        
        assert isinstance(matrix, pd.DataFrame)
        assert matrix.shape == (3, 3)
        assert all(matrix.columns == ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'])
        # Diagonal should be 1.0 (self-correlation)
        assert all(matrix.iloc[i, i] == 1.0 for i in range(3))
    
    def test_suggest_diversification(self):
        """Test diversification suggestions."""
        analyzer = CorrelationAnalyzer()
        
        positions = {
            'BTC/USDT': 0.4,
            'ETH/USDT': 0.3,
            'BNB/USDT': 0.2
        }
        
        # High correlation between BTC and ETH
        correlations = {
            'BTC/USDT_ETH/USDT': 0.85,
            'BTC/USDT_BNB/USDT': 0.55,
            'ETH/USDT_BNB/USDT': 0.50
        }
        
        suggestions = analyzer.suggest_diversification(positions, correlations)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0  # Should have at least one suggestion
        assert suggestions[0]['action'] == 'reduce'
        assert suggestions[0]['correlation'] > 0.8
    
    def test_calculate_diversification_score(self):
        """Test diversification score calculation."""
        analyzer = CorrelationAnalyzer()
        
        # Low correlation = high diversification
        correlations = {
            'BTC/USDT_ETH/USDT': 0.3,
            'BTC/USDT_BNB/USDT': 0.2,
            'ETH/USDT_BNB/USDT': 0.25
        }
        
        score = analyzer.calculate_diversification_score(correlations)
        
        assert 0 <= score <= 1
        assert score > 0.7  # Should be high with low correlations
    
    def test_get_correlation_report(self):
        """Test comprehensive correlation report."""
        analyzer = CorrelationAnalyzer(window=50)
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 3000
            }, index=dates)
        }
        
        positions = {
            'BTC/USDT': 0.5,
            'ETH/USDT': 0.4
        }
        
        report = analyzer.get_correlation_report(data, positions)
        
        assert 'correlations' in report
        assert 'correlation_matrix' in report
        assert 'diversification_score' in report
        assert 'suggestions' in report


class TestMultiSymbolPortfolioManager:
    """Test MultiSymbolPortfolioManager functionality."""
    
    def test_initialization_default(self):
        """Test initialization with default config."""
        manager = MultiSymbolPortfolioManager()
        
        assert len(manager.symbols) == 3
        assert 'BTC/USDT' in manager.capital_allocation
        assert manager.max_total_exposure == 0.50
    
    def test_initialization_custom_config(self):
        """Test initialization with custom config."""
        config = {
            'symbols': [
                {'symbol': 'BTC/USDT', 'allocation': 0.5, 'risk_limit': 0.15},
                {'symbol': 'ETH/USDT', 'allocation': 0.5, 'risk_limit': 0.15}
            ],
            'portfolio': {
                'total_capital': 20000,
                'max_total_exposure': 0.60,
                'rebalance_threshold': 0.15
            }
        }
        
        manager = MultiSymbolPortfolioManager(config)
        
        assert len(manager.symbols) == 2
        assert manager.capital_allocation['BTC/USDT'] == 0.5
        assert manager.max_total_exposure == 0.60
        assert manager.rebalance_threshold == 0.15
    
    def test_allocate_capital_basic(self):
        """Test basic capital allocation."""
        manager = MultiSymbolPortfolioManager()
        
        # Create mock signals using the actual SignalType enum
        from yunmin.strategy.base import Signal, SignalType
        
        signals = {
            'BTC/USDT': Signal(
                type=SignalType.BUY,
                confidence=0.8,
                reason='Test signal'
            ),
            'ETH/USDT': Signal(
                type=SignalType.BUY,
                confidence=0.7,
                reason='Test signal'
            )
        }
        
        allocations = manager.allocate_capital(signals)
        
        assert isinstance(allocations, dict)
        assert 'BTC/USDT' in allocations
        assert 'ETH/USDT' in allocations
        assert all(0 <= v <= 1 for v in allocations.values())
    
    def test_allocate_capital_max_exposure(self):
        """Test that max exposure is enforced."""
        manager = MultiSymbolPortfolioManager()
        
        # Create signals that would exceed max exposure
        from yunmin.strategy.base import Signal, SignalType
        
        signals = {
            'BTC/USDT': Signal(
                type=SignalType.BUY,
                confidence=1.0,
                reason='Test signal'
            ),
            'ETH/USDT': Signal(
                type=SignalType.BUY,
                confidence=1.0,
                reason='Test signal'
            ),
            'BNB/USDT': Signal(
                type=SignalType.BUY,
                confidence=1.0,
                reason='Test signal'
            )
        }
        
        allocations = manager.allocate_capital(signals)
        
        # Total should not exceed max exposure
        total = sum(allocations.values())
        assert total <= manager.max_total_exposure
    
    def test_check_correlation(self):
        """Test correlation checking."""
        manager = MultiSymbolPortfolioManager()
        
        # Create sample data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 3000
            }, index=dates)
        }
        
        symbols = ['BTC/USDT', 'ETH/USDT']
        corr_matrix = manager.check_correlation(symbols, data)
        
        assert isinstance(corr_matrix, pd.DataFrame)
        if not corr_matrix.empty:
            assert corr_matrix.shape == (2, 2)
    
    def test_suggest_rebalancing(self):
        """Test rebalancing suggestions."""
        manager = MultiSymbolPortfolioManager()
        
        # Current allocations drifted significantly from targets
        current_allocations = {
            'BTC/USDT': 0.55,  # Target is 0.40 - drift of 0.15 > threshold of 0.10
            'ETH/USDT': 0.20,  # Target is 0.35 - drift of 0.15 > threshold of 0.10
            'BNB/USDT': 0.25   # Target is 0.25 - no drift
        }
        
        target_allocations = {
            'BTC/USDT': 0.40,
            'ETH/USDT': 0.35,
            'BNB/USDT': 0.25
        }
        
        suggestions = manager.suggest_rebalancing(current_allocations, target_allocations)
        
        assert isinstance(suggestions, list)
        # Should suggest rebalancing for BTC (reduce) and ETH (increase)
        assert len(suggestions) >= 1
    
    def test_get_portfolio_metrics(self):
        """Test portfolio metrics calculation."""
        manager = MultiSymbolPortfolioManager()
        
        positions = {
            'BTC/USDT': 4000,
            'ETH/USDT': 3000,
            'BNB/USDT': 2000
        }
        
        total_capital = 10000
        
        metrics = manager.get_portfolio_metrics(positions, total_capital)
        
        assert 'total_exposure' in metrics
        assert 'num_positions' in metrics
        assert 'largest_position' in metrics
        assert 'smallest_position' in metrics
        
        assert metrics['num_positions'] == 3
        assert metrics['largest_position'] == 'BTC/USDT'
        assert metrics['smallest_position'] == 'BNB/USDT'
        assert metrics['total_exposure'] == 0.9  # 9000/10000
    
    def test_adjust_for_correlations(self):
        """Test correlation-based adjustment."""
        manager = MultiSymbolPortfolioManager()
        
        allocations = {
            'BTC/USDT': 0.4,
            'ETH/USDT': 0.3
        }
        
        # High correlation should trigger adjustment
        correlations = {
            'BTC/USDT_ETH/USDT': 0.85
        }
        
        adjusted = manager._adjust_for_correlations(allocations, correlations)
        
        # One of the allocations should be reduced
        assert adjusted['BTC/USDT'] != allocations['BTC/USDT'] or \
               adjusted['ETH/USDT'] != allocations['ETH/USDT']


class TestMultiSymbolIntegration:
    """Integration tests for multi-symbol components."""
    
    def test_end_to_end_workflow(self):
        """Test complete workflow from data to allocation."""
        # Initialize components
        analyzer = CorrelationAnalyzer(window=50)
        manager = MultiSymbolPortfolioManager()
        
        # Create sample market data
        dates = pd.date_range('2024-01-01', periods=100, freq='1h')
        data = {
            'BTC/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 50000
            }, index=dates),
            'ETH/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 3000
            }, index=dates),
            'BNB/USDT': pd.DataFrame({
                'close': np.random.randn(100).cumsum() + 600
            }, index=dates)
        }
        
        # Calculate correlations
        correlations = analyzer.calculate_rolling_correlation(data)
        assert isinstance(correlations, dict)
        
        # Create mock signals
        from yunmin.strategy.base import Signal, SignalType
        
        signals = {
            symbol: Signal(
                type=SignalType.BUY,
                confidence=0.75,
                reason='Test signal'
            )
            for symbol in data.keys()
        }
        
        # Allocate capital with correlations
        allocations = manager.allocate_capital(signals, correlations=correlations)
        
        # Verify allocations
        assert isinstance(allocations, dict)
        assert len(allocations) > 0
        assert sum(allocations.values()) <= manager.max_total_exposure
        
        # Get diversification report
        report = analyzer.get_correlation_report(data)
        assert 'diversification_score' in report
        assert 0 <= report['diversification_score'] <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
