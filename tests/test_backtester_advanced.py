"""
Tests for Advanced Backtester
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock
from yunmin.core.backtester import (
    AdvancedBacktester,
    Backtester,
    BacktestResult,
    OptimizationMethod,
    OptimizationResult,
    TradeType
)
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class SimpleTestStrategy(BaseStrategy):
    """Simple strategy for testing."""
    
    def __init__(self, buy_threshold: float = 0.3, sell_threshold: float = 0.7):
        super().__init__("TestStrategy")
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.signal_index = 0
        
    def analyze(self, df: pd.DataFrame) -> Signal:
        """Generate alternating buy/sell signals for testing."""
        if len(df) < 20:
            return Signal(SignalType.HOLD, 0.5, "Insufficient data")
        
        # Simple oscillating logic
        if self.signal_index % 3 == 0:
            self.signal_index += 1
            return Signal(SignalType.BUY, 0.8, "Buy signal")
        elif self.signal_index % 3 == 1:
            self.signal_index += 1
            return Signal(SignalType.HOLD, 0.6, "Hold to close")
        else:
            self.signal_index += 1
            return Signal(SignalType.SELL, 0.7, "Sell signal")


class TestAdvancedBacktester:
    """Test suite for Advanced Backtester."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
        
        # Trending data with some noise
        base_price = 50000
        trend = np.linspace(0, 2000, 200)
        noise = np.random.randn(200) * 100
        prices = base_price + trend + noise
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.abs(np.random.randn(200) * 50),
            'low': prices - np.abs(np.random.randn(200) * 50),
            'close': prices,
            'volume': np.random.rand(200) * 1000
        })
    
    @pytest.fixture
    def backtester(self):
        """Create backtester instance."""
        return AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
    
    def test_initialization(self):
        """Test backtester initialization."""
        backtester = AdvancedBacktester(symbol="BTC/USDT", timeframe="5m")
        
        assert backtester.symbol == "BTC/USDT"
        assert backtester.timeframe == "5m"
        assert backtester.trades == []
    
    def test_backward_compatibility(self):
        """Test that Backtester alias exists for backward compatibility."""
        backtester = Backtester(symbol="BTC/USDT", timeframe="5m")
        assert isinstance(backtester, AdvancedBacktester)
    
    def test_run_basic_backtest(self, backtester, sample_data):
        """Test basic backtest execution."""
        strategy = SimpleTestStrategy()
        
        result = backtester.run(
            strategy, 
            sample_data, 
            initial_capital=10000.0
        )
        
        assert isinstance(result, BacktestResult)
        assert isinstance(result.trades, list)
        assert isinstance(result.total_profit, float)
        assert isinstance(result.win_rate, float)
        assert 0.0 <= result.win_rate <= 1.0
        assert isinstance(result.max_drawdown, float)
        assert result.max_drawdown >= 0.0
    
    def test_backtest_result_metrics(self, backtester, sample_data):
        """Test that all expected metrics are calculated."""
        strategy = SimpleTestStrategy()
        result = backtester.run(strategy, sample_data, initial_capital=10000.0)
        
        assert hasattr(result, 'total_trades')
        assert hasattr(result, 'winning_trades')
        assert hasattr(result, 'losing_trades')
        assert hasattr(result, 'avg_win')
        assert hasattr(result, 'avg_loss')
        assert hasattr(result, 'profit_factor')
        assert hasattr(result, 'expectancy')
        assert hasattr(result, 'sharpe_ratio')
        assert hasattr(result, 'sortino_ratio')
        assert hasattr(result, 'calmar_ratio')
        assert hasattr(result, 'equity_curve')
    
    def test_equity_curve_generation(self, backtester, sample_data):
        """Test that equity curve is properly generated."""
        strategy = SimpleTestStrategy()
        result = backtester.run(strategy, sample_data, initial_capital=10000.0)
        
        assert len(result.equity_curve) > 0
        assert result.equity_curve[0] == 10000.0  # Starts at initial capital
    
    def test_commission_and_slippage(self, backtester, sample_data):
        """Test that commission and slippage are applied."""
        strategy = SimpleTestStrategy()
        
        # Run with no commission/slippage
        result1 = backtester.run(strategy, sample_data, commission=0.0, slippage=0.0)
        
        # Run with commission/slippage
        strategy2 = SimpleTestStrategy()  # Fresh instance
        result2 = backtester.run(strategy2, sample_data, commission=0.01, slippage=0.001)
        
        # With costs, profit should be lower (or loss higher)
        if result1.total_profit > 0 and result2.total_profit > 0:
            assert result2.total_profit <= result1.total_profit
    
    def test_walk_forward_validation(self, backtester, sample_data):
        """Test walk-forward validation."""
        results = backtester.walk_forward_validation(
            SimpleTestStrategy,
            sample_data,
            train_ratio=0.7,
            n_splits=3,
            initial_capital=10000.0
        )
        
        assert len(results) == 3
        assert all(isinstance(r, BacktestResult) for r in results)
        assert all(r.is_out_of_sample for r in results)
        assert all(r.validation_period is not None for r in results)
    
    def test_monte_carlo_simulation(self, backtester):
        """Test Monte Carlo simulation."""
        # Create mock trades
        trades = [
            {'pnl': 100},
            {'pnl': -50},
            {'pnl': 75},
            {'pnl': -25},
            {'pnl': 150}
        ]
        
        mc_result = backtester.monte_carlo_simulation(
            trades,
            n_simulations=100,
            initial_capital=10000.0
        )
        
        assert 'final_capital_mean' in mc_result
        assert 'final_capital_median' in mc_result
        assert 'final_capital_std' in mc_result
        assert 'percentile_5' in mc_result
        assert 'percentile_95' in mc_result
        assert 'max_dd_mean' in mc_result
        assert mc_result['n_simulations'] == 100
    
    def test_monte_carlo_empty_trades(self, backtester):
        """Test Monte Carlo with no trades."""
        result = backtester.monte_carlo_simulation([], n_simulations=100)
        assert 'error' in result
    
    def test_grid_search_optimization(self, backtester, sample_data):
        """Test parameter optimization using grid search."""
        param_grid = {
            'buy_threshold': [0.2, 0.3],
            'sell_threshold': [0.6, 0.7]
        }
        
        opt_result = backtester.optimize_parameters(
            SimpleTestStrategy,
            sample_data,
            param_grid,
            optimization_metric='sharpe_ratio',
            method=OptimizationMethod.GRID_SEARCH
        )
        
        assert isinstance(opt_result, OptimizationResult)
        assert opt_result.best_params is not None
        assert isinstance(opt_result.best_score, float)
        assert len(opt_result.all_results) == 4  # 2x2 combinations
        assert opt_result.optimization_method == 'grid_search'
        assert opt_result.metric_optimized == 'sharpe_ratio'
    
    def test_optimization_result_structure(self, backtester, sample_data):
        """Test that optimization results have proper structure."""
        param_grid = {'buy_threshold': [0.3]}
        
        opt_result = backtester.optimize_parameters(
            SimpleTestStrategy,
            sample_data,
            param_grid
        )
        
        assert 'buy_threshold' in opt_result.best_params
        assert all('params' in r for r in opt_result.all_results)
        assert all('score' in r for r in opt_result.all_results)
    
    def test_html_report_generation(self, backtester, sample_data, tmp_path):
        """Test HTML report generation."""
        strategy = SimpleTestStrategy()
        result = backtester.run(strategy, sample_data, initial_capital=10000.0)
        
        output_path = tmp_path / "test_report.html"
        generated_path = backtester.generate_html_report(
            result,
            strategy_name="Test Strategy",
            output_path=str(output_path)
        )
        
        assert output_path.exists()
        assert generated_path == str(output_path)
        
        # Check content
        content = output_path.read_text()
        assert "Test Strategy" in content
        assert "Total Profit" in content
        assert "Win Rate" in content
        assert "Sharpe Ratio" in content
    
    def test_calculate_metrics_no_trades(self, backtester):
        """Test metrics calculation with no trades."""
        result = backtester._calculate_metrics([], [10000.0] * 10, 10000.0)
        
        assert result.total_profit == 0.0
        assert result.win_rate == 0.0
        assert result.total_trades == 0
    
    def test_calculate_metrics_with_trades(self, backtester):
        """Test metrics calculation with trades."""
        trades = [
            {'pnl': 100, 'return': 0.01},
            {'pnl': -50, 'return': -0.005},
            {'pnl': 150, 'return': 0.015},
            {'pnl': -25, 'return': -0.0025}
        ]
        
        equity_curve = [10000, 10100, 10050, 10200, 10175]
        
        result = backtester._calculate_metrics(trades, equity_curve, 10000.0)
        
        assert result.total_trades == 4
        assert result.winning_trades == 2
        assert result.losing_trades == 2
        assert result.win_rate == 0.5
        assert result.total_profit == 175
    
    def test_profit_factor_calculation(self, backtester):
        """Test profit factor calculation."""
        trades = [
            {'pnl': 100, 'return': 0.01},
            {'pnl': 200, 'return': 0.02},
            {'pnl': -50, 'return': -0.005}
        ]
        
        equity_curve = [10000] * 5
        result = backtester._calculate_metrics(trades, equity_curve, 10000.0)
        
        # Profit factor = gross_profit / gross_loss = 300 / 50 = 6.0
        assert result.profit_factor == 6.0
    
    def test_expectancy_calculation(self, backtester):
        """Test expectancy calculation."""
        trades = [
            {'pnl': 100, 'return': 0.01},
            {'pnl': -50, 'return': -0.005}
        ]
        
        equity_curve = [10000] * 5
        result = backtester._calculate_metrics(trades, equity_curve, 10000.0)
        
        # Expectancy = (0.5 * 100) - (0.5 * 50) = 25
        assert result.expectancy == 25.0
    
    def test_max_drawdown_calculation(self, backtester):
        """Test maximum drawdown calculation."""
        # Equity curve with known drawdown
        equity_curve = [10000, 11000, 10000, 9000, 10500, 12000]
        
        result = backtester._calculate_metrics([], equity_curve, 10000.0)
        
        # Peak at 11000, trough at 9000 -> drawdown = 2000/11000 ≈ 0.1818
        assert result.max_drawdown > 0.15
        assert result.max_drawdown < 0.20
    
    def test_sharpe_ratio_positive_returns(self, backtester):
        """Test Sharpe ratio with positive returns."""
        # Create equity curve with positive trend
        equity_curve = list(np.linspace(10000, 12000, 100))
        
        result = backtester._calculate_metrics([], equity_curve, 10000.0)
        
        assert result.sharpe_ratio is not None
        # Positive trend should give positive Sharpe
        assert result.sharpe_ratio > 0
    
    def test_sortino_ratio_calculation(self, backtester):
        """Test Sortino ratio calculation."""
        # Create equity curve with some volatility
        equity_curve = [10000 + i * 10 + np.random.randn() * 50 for i in range(100)]
        
        result = backtester._calculate_metrics([], equity_curve, 10000.0)
        
        assert result.sortino_ratio is not None
    
    def test_calmar_ratio_calculation(self, backtester):
        """Test Calmar ratio calculation."""
        # Equity curve with profit and drawdown
        equity_curve = [10000, 11000, 10500, 12000]
        
        result = backtester._calculate_metrics([], equity_curve, 10000.0)
        
        assert result.calmar_ratio is not None
        if result.max_drawdown > 0:
            assert result.calmar_ratio > 0
    
    def test_recovery_factor_calculation(self, backtester):
        """Test recovery factor calculation."""
        trades = [{'pnl': 100, 'return': 0.01}]
        equity_curve = [10000, 9500, 10100]  # Has drawdown and recovery
        
        result = backtester._calculate_metrics(trades, equity_curve, 10000.0)
        
        assert result.recovery_factor is not None
        if result.max_drawdown > 0:
            assert result.recovery_factor > 0
    
    def test_multiple_optimization_parameters(self, backtester, sample_data):
        """Test optimization with multiple parameters."""
        param_grid = {
            'buy_threshold': [0.2, 0.3, 0.4],
            'sell_threshold': [0.5, 0.6, 0.7]
        }
        
        opt_result = backtester.optimize_parameters(
            SimpleTestStrategy,
            sample_data,
            param_grid
        )
        
        # Should test 3*3 = 9 combinations
        assert len(opt_result.all_results) == 9
        assert opt_result.best_params is not None
    
    def test_optimization_different_metrics(self, backtester, sample_data):
        """Test optimization with different target metrics."""
        param_grid = {'buy_threshold': [0.2, 0.3]}
        
        # Optimize for total profit
        opt1 = backtester.optimize_parameters(
            SimpleTestStrategy,
            sample_data,
            param_grid,
            optimization_metric='total_profit'
        )
        
        # Optimize for win rate
        opt2 = backtester.optimize_parameters(
            SimpleTestStrategy,
            sample_data,
            param_grid,
            optimization_metric='win_rate'
        )
        
        assert opt1.metric_optimized == 'total_profit'
        assert opt2.metric_optimized == 'win_rate'
        # Results might differ
        # (best params for profit might not be best for win rate)
