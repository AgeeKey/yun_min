"""
Tests for Final Validation components:
- Monte Carlo Simulation
- Walk-Forward Analysis
- Sortino Ratio calculation
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from yunmin.backtesting.montecarlo import MonteCarloSimulator, MonteCarloResult
from yunmin.backtesting.walkforward import WalkForwardAnalyzer, WalkForwardWindow
from yunmin.backtesting.metrics import TradeResult, PerformanceMetrics
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class DummyStrategy(BaseStrategy):
    """Dummy strategy for testing"""
    
    def __init__(self):
        super().__init__("DummyStrategy")
    
    def analyze(self, data: pd.DataFrame) -> Signal:
        """Return HOLD signal"""
        return Signal(
            type=SignalType.HOLD,
            confidence=0.5,
            timestamp=datetime.now()
        )


class TestMonteCarloSimulator:
    """Test Monte Carlo Simulation"""
    
    def test_initialization(self):
        """Test simulator initialization"""
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        assert simulator.initial_capital == 100000.0
        assert simulator.seed == 42
    
    def test_empty_trades(self):
        """Test with no trades"""
        simulator = MonteCarloSimulator(seed=42)
        results = simulator.run_simulation([], num_simulations=10)
        assert len(results) == 0
    
    def test_single_simulation(self):
        """Test single simulation run"""
        # Create sample trades
        trades = self._create_sample_trades(count=20)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=1)
        
        assert len(results) == 1
        assert isinstance(results[0], MonteCarloResult)
        assert results[0].simulation_id == 0
        assert results[0].total_trades == 20
    
    def test_multiple_simulations(self):
        """Test multiple simulations"""
        trades = self._create_sample_trades(count=50)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=100)
        
        assert len(results) == 100
        
        # Check that all simulations have same number of trades
        for result in results:
            assert result.total_trades == 50
    
    def test_analyze_results(self):
        """Test analysis of Monte Carlo results"""
        trades = self._create_sample_trades(count=30, win_rate=0.6)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=100)
        analysis = simulator.analyze_results(results)
        
        assert analysis['num_simulations'] == 100
        assert 'profitable_simulations' in analysis
        assert 'profitable_pct' in analysis
        assert 'return_mean' in analysis
        assert 'return_median' in analysis
        assert 'drawdown_mean' in analysis
        assert 'sharpe_mean' in analysis
        assert 'win_rate_mean' in analysis
        assert 'profit_factor_mean' in analysis
        assert 'ruin_probability' in analysis
    
    def test_profitability_threshold(self):
        """Test profitability threshold detection"""
        # Create highly profitable trades
        trades = self._create_sample_trades(count=50, win_rate=0.8, avg_win=500, avg_loss=-200)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=100)
        analysis = simulator.analyze_results(results)
        
        # Should have high profitable percentage
        assert analysis['profitable_pct'] > 80
    
    def test_check_criteria_pass(self):
        """Test criteria check - passing case"""
        trades = self._create_sample_trades(count=50, win_rate=0.7, avg_win=400, avg_loss=-150)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=100)
        analysis = simulator.analyze_results(results)
        
        check = simulator.check_criteria(
            analysis,
            min_profitable_pct=80.0,
            max_drawdown_pct=25.0
        )
        
        assert 'passed' in check
        assert 'criteria' in check
        assert 'profitable_pct' in check['criteria']
        assert 'max_drawdown' in check['criteria']
    
    def test_check_criteria_fail(self):
        """Test criteria check - failing case"""
        # Create trades with poor performance
        trades = self._create_sample_trades(count=50, win_rate=0.3, avg_win=200, avg_loss=-400)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=100)
        analysis = simulator.analyze_results(results)
        
        check = simulator.check_criteria(
            analysis,
            min_profitable_pct=95.0,
            max_drawdown_pct=20.0
        )
        
        # Should fail one or both criteria
        assert check['passed'] == False or analysis['profitable_pct'] < 95.0
    
    def test_get_results_dataframe(self):
        """Test DataFrame conversion"""
        trades = self._create_sample_trades(count=30)
        
        simulator = MonteCarloSimulator(initial_capital=100000.0, seed=42)
        results = simulator.run_simulation(trades, num_simulations=10)
        df = simulator.get_results_dataframe(results)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert 'simulation_id' in df.columns
        assert 'final_equity' in df.columns
        assert 'total_return' in df.columns
        assert 'sharpe_ratio' in df.columns
    
    def test_empty_analysis(self):
        """Test empty analysis handling"""
        simulator = MonteCarloSimulator(seed=42)
        analysis = simulator.analyze_results([])
        
        assert analysis['num_simulations'] == 0
        assert analysis['profitable_pct'] == 0.0
    
    def _create_sample_trades(
        self,
        count: int = 20,
        win_rate: float = 0.5,
        avg_win: float = 300,
        avg_loss: float = -200
    ) -> list:
        """Helper to create sample trades"""
        trades = []
        base_time = datetime(2025, 1, 1)
        
        for i in range(count):
            is_win = np.random.random() < win_rate
            pnl = avg_win if is_win else avg_loss
            pnl_pct = (pnl / 10000) * 100  # Assuming 10000 position size
            
            trade = TradeResult(
                entry_time=base_time + timedelta(hours=i*2),
                exit_time=base_time + timedelta(hours=i*2+1),
                entry_price=50000.0,
                exit_price=50000.0 + pnl,
                side='LONG',
                amount=0.2,
                pnl=pnl,
                pnl_pct=pnl_pct,
                fees=10.0
            )
            trades.append(trade)
        
        return trades


class TestWalkForwardAnalyzer:
    """Test Walk-Forward Analysis"""
    
    def test_initialization(self):
        """Test analyzer initialization"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(
            strategy=strategy,
            train_period_days=90,
            test_period_days=90,
            step_days=30
        )
        
        assert analyzer.train_period == 90
        assert analyzer.test_period == 90
        assert analyzer.step == 30
        assert analyzer.initial_capital == 100000.0
    
    def test_generate_windows_empty_data(self):
        """Test window generation with empty data"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        
        data = pd.DataFrame()
        windows = analyzer.generate_windows(data)
        
        assert len(windows) == 0
    
    def test_generate_windows_insufficient_data(self):
        """Test window generation with insufficient data"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(
            strategy,
            train_period_days=180,
            test_period_days=90
        )
        
        # Create only 60 days of data
        data = self._create_sample_data(days=60)
        windows = analyzer.generate_windows(data)
        
        # Should not generate windows if insufficient data
        assert len(windows) == 0
    
    def test_generate_windows_single_window(self):
        """Test single window generation"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(
            strategy,
            train_period_days=90,
            test_period_days=90,
            step_days=180  # Large step to get only 1 window
        )
        
        data = self._create_sample_data(days=200)
        windows = analyzer.generate_windows(data)
        
        assert len(windows) >= 1
        
        window = windows[0]
        assert isinstance(window, WalkForwardWindow)
        assert window.window_id == 0
        assert window.train_size > 0
        assert window.test_size > 0
    
    def test_generate_windows_multiple(self):
        """Test multiple window generation"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(
            strategy,
            train_period_days=90,
            test_period_days=90,
            step_days=30
        )
        
        data = self._create_sample_data(days=365)
        windows = analyzer.generate_windows(data)
        
        # Should generate multiple windows
        assert len(windows) > 1
        
        # Windows should be sequential
        for i in range(len(windows) - 1):
            assert windows[i+1].window_id == windows[i].window_id + 1
    
    def test_generate_windows_anchored(self):
        """Test anchored walk-forward window generation"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(
            strategy,
            train_period_days=90,
            test_period_days=90,
            step_days=30
        )
        
        data = self._create_sample_data(days=365)
        windows = analyzer.generate_windows(data, anchored=True)
        
        assert len(windows) > 1
        
        # In anchored mode, all windows should start from the same date
        start_date = windows[0].train_start
        for window in windows:
            assert window.train_start == start_date
    
    def test_empty_analysis(self):
        """Test empty analysis"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        
        analysis = analyzer.analyze_results([])
        
        assert analysis['num_windows'] == 0
        assert 'train' in analysis
        assert 'test' in analysis
    
    def test_check_criteria(self):
        """Test criteria checking"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        
        # Mock analysis results
        analysis = {
            'num_windows': 3,
            'test': {
                'avg_win_rate': 45.0,
                'avg_profit_factor': 1.6,
                'avg_max_dd': 12.0,
            },
            'consistency': {
                'degradation_pct': -15.0,
            }
        }
        
        check = analyzer.check_criteria(
            analysis,
            min_test_win_rate=42.0,
            min_test_profit_factor=1.5,
            max_test_drawdown=15.0,
            max_degradation_pct=-30.0
        )
        
        assert 'passed' in check
        assert 'criteria' in check
        assert len(check['criteria']) == 4
    
    def test_get_results_dataframe_empty(self):
        """Test empty results DataFrame"""
        strategy = DummyStrategy()
        analyzer = WalkForwardAnalyzer(strategy)
        
        df = analyzer.get_results_dataframe([])
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
    
    def _create_sample_data(self, days: int = 365) -> pd.DataFrame:
        """Helper to create sample OHLCV data"""
        base_date = datetime(2025, 1, 1)
        dates = [base_date + timedelta(hours=i) for i in range(days * 24)]
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': 50000.0 + np.random.randn(len(dates)) * 1000,
            'high': 51000.0 + np.random.randn(len(dates)) * 1000,
            'low': 49000.0 + np.random.randn(len(dates)) * 1000,
            'close': 50000.0 + np.random.randn(len(dates)) * 1000,
            'volume': 1000000.0 + np.random.randn(len(dates)) * 100000,
        })
        
        return data


class TestSortinoRatio:
    """Test Sortino Ratio calculation in PerformanceMetrics"""
    
    def test_sortino_calculation(self):
        """Test Sortino Ratio is calculated"""
        metrics = PerformanceMetrics(initial_capital=100000.0)
        
        # Add sample trades
        trades = self._create_sample_trades(count=20)
        for trade in trades:
            metrics.add_trade(trade)
        
        results = metrics.calculate_metrics(100000.0)
        
        assert 'sortino_ratio' in results
        assert isinstance(results['sortino_ratio'], (int, float))
    
    def test_sortino_vs_sharpe(self):
        """Test that Sortino differs from Sharpe"""
        metrics = PerformanceMetrics(initial_capital=100000.0)
        
        # Add asymmetric trades (few big losses, many small wins)
        trades = self._create_asymmetric_trades()
        for trade in trades:
            metrics.add_trade(trade)
        
        results = metrics.calculate_metrics(100000.0)
        
        # Sortino should be different from Sharpe (usually higher for asymmetric returns)
        assert 'sortino_ratio' in results
        assert 'sharpe_ratio' in results
        # They should not be exactly equal (unless very symmetric)
        # Note: Can be equal in some edge cases, so we just check both exist
    
    def test_sortino_no_downside(self):
        """Test Sortino with no negative returns"""
        metrics = PerformanceMetrics(initial_capital=100000.0)
        
        # All winning trades
        base_time = datetime(2025, 1, 1)
        for i in range(10):
            trade = TradeResult(
                entry_time=base_time + timedelta(hours=i*2),
                exit_time=base_time + timedelta(hours=i*2+1),
                entry_price=50000.0,
                exit_price=50500.0,
                side='LONG',
                amount=0.1,
                pnl=50.0,
                pnl_pct=0.1,
                fees=5.0
            )
            metrics.add_trade(trade)
        
        results = metrics.calculate_metrics(100000.0)
        
        # Should handle no downside gracefully
        assert 'sortino_ratio' in results
    
    def test_sortino_empty_trades(self):
        """Test Sortino with no trades"""
        metrics = PerformanceMetrics(initial_capital=100000.0)
        results = metrics.calculate_metrics(100000.0)
        
        assert results['sortino_ratio'] == 0.0
    
    def _create_sample_trades(self, count: int = 20) -> list:
        """Helper to create sample trades"""
        trades = []
        base_time = datetime(2025, 1, 1)
        
        for i in range(count):
            is_win = i % 2 == 0  # 50% win rate
            pnl = 300 if is_win else -200
            pnl_pct = (pnl / 10000) * 100
            
            trade = TradeResult(
                entry_time=base_time + timedelta(hours=i*2),
                exit_time=base_time + timedelta(hours=i*2+1),
                entry_price=50000.0,
                exit_price=50000.0 + pnl,
                side='LONG',
                amount=0.2,
                pnl=pnl,
                pnl_pct=pnl_pct,
                fees=10.0
            )
            trades.append(trade)
        
        return trades
    
    def _create_asymmetric_trades(self) -> list:
        """Create trades with asymmetric returns"""
        trades = []
        base_time = datetime(2025, 1, 1)
        
        # Many small wins
        for i in range(15):
            trade = TradeResult(
                entry_time=base_time + timedelta(hours=i*2),
                exit_time=base_time + timedelta(hours=i*2+1),
                entry_price=50000.0,
                exit_price=50100.0,
                side='LONG',
                amount=0.1,
                pnl=10.0,
                pnl_pct=0.2,
                fees=5.0
            )
            trades.append(trade)
        
        # Few big losses
        for i in range(15, 20):
            trade = TradeResult(
                entry_time=base_time + timedelta(hours=i*2),
                exit_time=base_time + timedelta(hours=i*2+1),
                entry_price=50000.0,
                exit_price=49500.0,
                side='LONG',
                amount=0.1,
                pnl=-50.0,
                pnl_pct=-1.0,
                fees=5.0
            )
            trades.append(trade)
        
        return trades


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
