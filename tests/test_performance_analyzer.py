"""
Tests for Performance Analytics Engine
Tests trade analysis, attribution, risk metrics, and export functionality
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, UTC
import pandas as pd

from yunmin.analytics.performance_analyzer import (
    PerformanceAnalyzer,
    Trade,
    PerformanceMetrics,
    AttributionMetrics
)


@pytest.fixture
def analyzer():
    """Create performance analyzer"""
    return PerformanceAnalyzer()


@pytest.fixture
def sample_trades():
    """Create sample trades for testing"""
    now = datetime.now(UTC)
    
    trades = [
        # Winning trades
        Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now - timedelta(hours=10),
            exit_time=now - timedelta(hours=8),
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0,
            strategy="EMA_Crossover"
        ),
        Trade(
            symbol="ETH/USDT",
            side="SHORT",
            entry_time=now - timedelta(hours=7),
            exit_time=now - timedelta(hours=5),
            entry_price=3000.0,
            exit_price=2950.0,
            amount=1.0,
            pnl=50.0,
            pnl_pct=1.67,
            strategy="RSI_Mean_Reversion"
        ),
        Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now - timedelta(hours=4),
            exit_time=now - timedelta(hours=2),
            entry_price=51000.0,
            exit_price=51500.0,
            amount=0.1,
            pnl=50.0,
            pnl_pct=0.98,
            strategy="EMA_Crossover"
        ),
        # Losing trades
        Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now - timedelta(hours=6),
            exit_time=now - timedelta(hours=4),
            entry_price=50500.0,
            exit_price=50000.0,
            amount=0.1,
            pnl=-50.0,
            pnl_pct=-0.99,
            strategy="EMA_Crossover"
        ),
        Trade(
            symbol="ETH/USDT",
            side="LONG",
            entry_time=now - timedelta(hours=3),
            exit_time=now - timedelta(hours=1),
            entry_price=3000.0,
            exit_price=2970.0,
            amount=1.0,
            pnl=-30.0,
            pnl_pct=-1.0,
            strategy="RSI_Mean_Reversion"
        ),
    ]
    
    return trades


class TestTradeClass:
    """Test Trade data class"""
    
    def test_trade_creation(self):
        """Test creating a trade"""
        now = datetime.now(UTC)
        trade = Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now,
            exit_time=now + timedelta(hours=2),
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0
        )
        
        assert trade.symbol == "BTC/USDT"
        assert trade.pnl == 100.0
    
    def test_trade_duration(self):
        """Test trade duration calculation"""
        now = datetime.now(UTC)
        trade = Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=now,
            exit_time=now + timedelta(hours=3),
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0
        )
        
        assert trade.duration == timedelta(hours=3)
    
    def test_trade_is_win(self):
        """Test is_win property"""
        trade_win = Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=datetime.now(UTC),
            exit_time=datetime.now(UTC),
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0
        )
        
        trade_loss = Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=datetime.now(UTC),
            exit_time=datetime.now(UTC),
            entry_price=50000.0,
            exit_price=49000.0,
            amount=0.1,
            pnl=-100.0,
            pnl_pct=-2.0
        )
        
        assert trade_win.is_win is True
        assert trade_loss.is_win is False
    
    def test_trade_to_dict(self):
        """Test converting trade to dictionary"""
        trade = Trade(
            symbol="BTC/USDT",
            side="LONG",
            entry_time=datetime.now(UTC),
            exit_time=datetime.now(UTC),
            entry_price=50000.0,
            exit_price=51000.0,
            amount=0.1,
            pnl=100.0,
            pnl_pct=2.0
        )
        
        data = trade.to_dict()
        assert isinstance(data, dict)
        assert 'symbol' in data
        assert 'duration_hours' in data


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer class"""
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization"""
        assert len(analyzer.trades) == 0
        assert len(analyzer.equity_curve) == 0
        assert analyzer.initial_capital == 15000.0
    
    def test_add_trade(self, analyzer, sample_trades):
        """Test adding trades"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        assert len(analyzer.trades) == len(sample_trades)
    
    def test_add_equity_point(self, analyzer):
        """Test adding equity curve points"""
        now = datetime.now(UTC)
        analyzer.add_equity_point(now, 15000.0)
        analyzer.add_equity_point(now + timedelta(hours=1), 15100.0)
        
        assert len(analyzer.equity_curve) == 2


class TestTradeAnalysis:
    """Test trade analysis functionality"""
    
    def test_analyze_trades_empty(self, analyzer):
        """Test analyzing with no trades"""
        metrics = analyzer.analyze_trades()
        
        assert metrics.total_trades == 0
        assert metrics.total_pnl == 0.0
        assert metrics.win_rate == 0.0
    
    def test_analyze_trades_basic(self, analyzer, sample_trades):
        """Test basic trade analysis"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        assert metrics.win_rate == 60.0
    
    def test_analyze_trades_pnl(self, analyzer, sample_trades):
        """Test P&L calculations"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # Total P&L = 100 + 50 + 50 - 50 - 30 = 120
        assert metrics.total_pnl == 120.0
        assert metrics.gross_profit == 200.0  # 100 + 50 + 50
        assert metrics.gross_loss == 80.0     # 50 + 30
    
    def test_analyze_trades_profit_factor(self, analyzer, sample_trades):
        """Test profit factor calculation"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # Profit factor = 200 / 80 = 2.5
        assert abs(metrics.profit_factor - 2.5) < 0.01
    
    def test_analyze_trades_averages(self, analyzer, sample_trades):
        """Test average win/loss calculations"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # Avg win = (100 + 50 + 50) / 3 = 66.67
        assert abs(metrics.avg_win - 66.67) < 0.01
        
        # Avg loss = (50 + 30) / 2 = 40
        assert abs(metrics.avg_loss - 40.0) < 0.01
    
    def test_analyze_trades_largest(self, analyzer, sample_trades):
        """Test largest win/loss"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        assert metrics.largest_win == 100.0
        assert metrics.largest_loss == 50.0
    
    def test_analyze_trades_sharpe_ratio(self, analyzer, sample_trades):
        """Test Sharpe ratio calculation"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # Sharpe ratio should be calculated
        assert metrics.sharpe_ratio != 0.0
    
    def test_analyze_trades_duration(self, analyzer, sample_trades):
        """Test duration calculations"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # All sample trades are 2 hours
        assert metrics.avg_trade_duration_hours == 2.0


class TestAttributionAnalysis:
    """Test attribution analysis"""
    
    def test_attribution_analysis_empty(self, analyzer):
        """Test attribution with no trades"""
        attribution = analyzer.attribution_analysis()
        
        assert len(attribution.by_strategy) == 0
        assert len(attribution.by_symbol) == 0
    
    def test_attribution_by_strategy(self, analyzer, sample_trades):
        """Test attribution by strategy"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        attribution = analyzer.attribution_analysis()
        
        assert "EMA_Crossover" in attribution.by_strategy
        assert "RSI_Mean_Reversion" in attribution.by_strategy
        
        # EMA: 100 + 50 - 50 = 100
        assert attribution.by_strategy["EMA_Crossover"] == 100.0
        
        # RSI: 50 - 30 = 20
        assert attribution.by_strategy["RSI_Mean_Reversion"] == 20.0
    
    def test_attribution_by_symbol(self, analyzer, sample_trades):
        """Test attribution by symbol"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        attribution = analyzer.attribution_analysis()
        
        assert "BTC/USDT" in attribution.by_symbol
        assert "ETH/USDT" in attribution.by_symbol
        
        # BTC: 100 + 50 - 50 = 100
        assert attribution.by_symbol["BTC/USDT"] == 100.0
        
        # ETH: 50 - 30 = 20
        assert attribution.by_symbol["ETH/USDT"] == 20.0
    
    def test_attribution_by_hour(self, analyzer, sample_trades):
        """Test attribution by hour"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        attribution = analyzer.attribution_analysis()
        
        # Should have hourly data
        assert len(attribution.by_hour) > 0
    
    def test_attribution_by_day_of_week(self, analyzer, sample_trades):
        """Test attribution by day of week"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        attribution = analyzer.attribution_analysis()
        
        # Should have day data
        assert len(attribution.by_day_of_week) > 0


class TestBestWorstPerformers:
    """Test best/worst performer analysis"""
    
    def test_get_best_worst_performers(self, analyzer, sample_trades):
        """Test getting best and worst performers"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        performers = analyzer.get_best_worst_performers(top_n=2)
        
        assert len(performers['best']) == 2
        assert len(performers['worst']) == 2
        
        # Best should be highest P&L
        assert performers['best'][0].pnl == 100.0
        
        # Worst should be lowest P&L
        assert performers['worst'][0].pnl == -50.0


class TestWinLossDistribution:
    """Test win/loss distribution"""
    
    def test_get_win_loss_distribution(self, analyzer, sample_trades):
        """Test win/loss distribution"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        distribution = analyzer.get_win_loss_distribution(bins=5)
        
        assert 'wins' in distribution
        assert 'losses' in distribution


class TestBenchmarking:
    """Test benchmarking functionality"""
    
    def test_benchmark_vs_buy_hold(self, analyzer, sample_trades):
        """Test benchmark against buy & hold"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        benchmark = analyzer.benchmark_vs_buy_hold(
            symbol="BTC/USDT",
            start_price=50000.0,
            end_price=51000.0
        )
        
        assert 'strategy_return_pct' in benchmark
        assert 'buy_hold_return_pct' in benchmark
        assert 'outperformance_pct' in benchmark
        
        # Buy & hold: (51000 - 50000) / 50000 = 2%
        assert abs(benchmark['buy_hold_return_pct'] - 2.0) < 0.01


class TestExport:
    """Test export functionality"""
    
    def test_export_to_csv(self, analyzer, sample_trades):
        """Test exporting to CSV"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            csv_path = f.name
        
        try:
            analyzer.export_to_csv(csv_path)
            
            # Verify file exists and has data
            assert Path(csv_path).exists()
            
            # Read back and verify
            df = pd.read_csv(csv_path)
            assert len(df) == 5
        
        finally:
            Path(csv_path).unlink(missing_ok=True)
    
    def test_export_to_excel(self, analyzer, sample_trades):
        """Test exporting to Excel"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xlsx') as f:
            excel_path = f.name
        
        try:
            analyzer.export_to_excel(excel_path)
            
            # Verify file exists
            assert Path(excel_path).exists()
        
        except ImportError:
            # openpyxl not installed
            pytest.skip("openpyxl not installed")
        
        finally:
            Path(excel_path).unlink(missing_ok=True)
    
    def test_export_empty_trades(self, analyzer):
        """Test exporting with no trades"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            csv_path = f.name
        
        # Should not raise error
        analyzer.export_to_csv(csv_path)
        
        Path(csv_path).unlink(missing_ok=True)


class TestTextReport:
    """Test text report generation"""
    
    def test_generate_text_report(self, analyzer, sample_trades):
        """Test generating text report"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        report = analyzer.generate_text_report()
        
        assert isinstance(report, str)
        assert "PERFORMANCE REPORT" in report
        assert "OVERALL PERFORMANCE" in report
        assert "RISK METRICS" in report
        assert "ATTRIBUTION ANALYSIS" in report
    
    def test_text_report_contains_metrics(self, analyzer, sample_trades):
        """Test report contains key metrics"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        report = analyzer.generate_text_report()
        
        assert "Total Trades:" in report
        assert "Winning Trades:" in report
        assert "Total P&L:" in report
        assert "Sharpe Ratio:" in report


class TestRiskMetrics:
    """Test advanced risk metrics"""
    
    def test_var_calculation(self, analyzer, sample_trades):
        """Test Value at Risk calculation"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # VaR should be calculated
        assert hasattr(metrics, 'var_95')
    
    def test_cvar_calculation(self, analyzer, sample_trades):
        """Test Conditional VaR calculation"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # CVaR should be calculated
        assert hasattr(metrics, 'cvar_95')
    
    def test_max_drawdown(self, analyzer, sample_trades):
        """Test maximum drawdown calculation"""
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        metrics = analyzer.analyze_trades()
        
        # Max drawdown should be calculated
        assert hasattr(metrics, 'max_drawdown')
        assert hasattr(metrics, 'max_drawdown_pct')


class TestIntegration:
    """Integration tests"""
    
    def test_complete_analysis_flow(self, analyzer, sample_trades):
        """Test complete analysis flow"""
        # Add trades
        for trade in sample_trades:
            analyzer.add_trade(trade)
        
        # Analyze
        metrics = analyzer.analyze_trades()
        attribution = analyzer.attribution_analysis()
        performers = analyzer.get_best_worst_performers()
        benchmark = analyzer.benchmark_vs_buy_hold("BTC/USDT", 50000.0, 51000.0)
        report = analyzer.generate_text_report()
        
        # Verify all analyses complete
        assert metrics.total_trades == 5
        assert len(attribution.by_strategy) > 0
        assert len(performers['best']) > 0
        assert 'outperformance_pct' in benchmark
        assert len(report) > 0
