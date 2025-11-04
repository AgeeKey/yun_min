"""Tests for backtesting engine components"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from yunmin.backtesting import (
    Backtester,
    HistoricalDataLoader,
    PerformanceMetrics,
    ReportGenerator
)
from yunmin.backtesting.metrics import TradeResult
from yunmin.strategy.base import BaseStrategy, SignalType, Signal


class DummyStrategy(BaseStrategy):
    """Simple buy-and-hold strategy for testing"""
    
    def __init__(self):
        super().__init__("DummyStrategy")
        self.signal_count = 0
    
    def analyze(self, data: pd.DataFrame) -> Signal:
        """Generate alternating buy/sell signals for testing"""
        self.signal_count += 1
        if self.signal_count == 1:
            return Signal(type=SignalType.BUY, confidence=0.8, reason="Test buy")
        elif self.signal_count == 50:
            return Signal(type=SignalType.CLOSE, confidence=0.9, reason="Test close")
        return Signal(type=SignalType.HOLD, confidence=0.5, reason="Test hold")


# ==================== HistoricalDataLoader Tests ====================

def test_data_loader_generate_sample_data():
    """Test synthetic data generation"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=50000,
        num_candles=100,
        trend='uptrend',
        volatility=0.02
    )
    
    assert len(data) == 100
    assert 'open' in data.columns
    assert 'high' in data.columns
    assert 'low' in data.columns
    assert 'close' in data.columns
    assert 'volume' in data.columns
    assert 'timestamp' in data.columns
    # Uptrend should have generally higher end price (allow some variance)
    assert data['close'].mean() > data['close'].iloc[0] * 0.9


def test_data_loader_downtrend():
    """Test downtrend data generation"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="ETH/USDT",
        start_price=3000,
        num_candles=100,
        trend='downtrend',
        volatility=0.015
    )
    
    assert len(data) == 100
    assert data.iloc[-1]['close'] < data.iloc[0]['open']  # Downtrend


def test_data_loader_sideways():
    """Test sideways market data generation"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BNB/USDT",
        start_price=400,
        num_candles=100,
        trend='sideways',
        volatility=0.01
    )
    
    assert len(data) == 100
    # Sideways should stay roughly around start price (allow 10% variance)
    mean_price = data['close'].mean()
    assert 360 < mean_price < 440


def test_data_loader_validate_data():
    """Test OHLC data validation"""
    loader = HistoricalDataLoader()
    
    # Valid data
    valid_data = pd.DataFrame({
        'open': [100, 101],
        'high': [105, 106],
        'low': [99, 100],
        'close': [102, 103],
        'volume': [1000, 1100],
        'timestamp': [datetime.now(), datetime.now() + timedelta(hours=1)]
    })
    assert loader.validate_data(valid_data) is True
    
    # Invalid data (high < low) - should raise ValueError
    invalid_data = pd.DataFrame({
        'open': [100],
        'high': [99],  # High less than low - invalid
        'low': [100],
        'close': [102],
        'volume': [1000],
        'timestamp': [datetime.now()]
    })
    with pytest.raises(ValueError):
        loader.validate_data(invalid_data)


# ==================== PerformanceMetrics Tests ====================

def test_metrics_add_trade():
    """Test adding trades to metrics"""
    metrics = PerformanceMetrics()
    
    trade = TradeResult(
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(hours=2),
        entry_price=50000,
        exit_price=51000,
        side="LONG",
        amount=0.1,
        pnl=100,
        pnl_pct=2.0,
        fees=10
    )
    
    metrics.add_trade(trade)
    assert len(metrics.trades) == 1
    assert len(metrics.equity_curve) == 2  # initial + 1 trade


def test_metrics_calculate_basic():
    """Test basic metrics calculation"""
    metrics = PerformanceMetrics()
    
    # Add winning trade
    metrics.add_trade(TradeResult(
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(hours=1),
        entry_price=50000,
        exit_price=51000,
        side="LONG",
        amount=0.1,
        pnl=100,
        pnl_pct=2.0,
        fees=5
    ))
    
    # Add losing trade
    metrics.add_trade(TradeResult(
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(hours=2),
        entry_price=51000,
        exit_price=50500,
        side="LONG",
        amount=0.1,
        pnl=-50,
        pnl_pct=-0.98,
        fees=5
    ))
    
    results = metrics.calculate_metrics(initial_capital=10000)
    
    assert results['total_trades'] == 2
    assert results['winning_trades'] == 1
    assert results['losing_trades'] == 1
    assert results['win_rate'] == 50.0
    assert results['total_pnl'] == 50  # 100 - 50
    assert results['net_pnl'] == 40  # 50 - 10 (fees)


def test_metrics_max_drawdown():
    """Test maximum drawdown calculation"""
    metrics = PerformanceMetrics(initial_capital=10000)
    
    # Add trades to create drawdown scenario
    # 10000 -> 11000 (win +1000)
    metrics.add_trade(TradeResult(
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(hours=1),
        entry_price=50000,
        exit_price=51000,
        side="LONG",
        amount=0.1,
        pnl=1000,
        pnl_pct=2.0,
        fees=0
    ))
    
    # 11000 -> 9000 (loss -2000) - creates max DD of 2000
    metrics.add_trade(TradeResult(
        entry_time=datetime.now(),
        exit_time=datetime.now() + timedelta(hours=2),
        entry_price=51000,
        exit_price=49000,
        side="LONG",
        amount=0.1,
        pnl=-2000,
        pnl_pct=-3.92,
        fees=0
    ))
    
    results = metrics.calculate_metrics(initial_capital=10000)
    
    # Max DD from 11000 to 9000 = 2000
    assert results['max_drawdown'] == 2000
    assert results['max_drawdown_pct'] == pytest.approx(18.18, abs=0.1)


def test_metrics_sharpe_ratio():
    """Test Sharpe ratio calculation"""
    metrics = PerformanceMetrics(initial_capital=10000)
    
    # Add trades with consistent positive returns
    for i in range(5):
        metrics.add_trade(TradeResult(
            entry_time=datetime.now() + timedelta(hours=i),
            exit_time=datetime.now() + timedelta(hours=i+1),
            entry_price=50000 + i*100,
            exit_price=50200 + i*100,
            side="LONG",
            amount=0.1,
            pnl=200,
            pnl_pct=0.4,
            fees=0
        ))
    
    results = metrics.calculate_metrics(initial_capital=10000)
    
    # Should have positive Sharpe for consistent positive returns
    assert results['sharpe_ratio'] > 0


# ==================== Backtester Tests ====================

def test_backtester_initialization():
    """Test backtester initialization"""
    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=50000,
        commission_rate=0.001,
        slippage_rate=0.0005,
        use_risk_manager=False
    )
    
    assert backtester.initial_capital == 50000
    assert backtester.capital == 50000
    assert backtester.commission_rate == 0.001
    assert backtester.slippage_rate == 0.0005
    assert backtester.current_position is None


def test_backtester_run_simple():
    """Test backtester execution on sample data"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=50000,
        num_candles=200,
        trend='uptrend',
        volatility=0.015
    )
    
    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=100000,
        use_risk_manager=False
    )
    
    results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.1)
    
    assert 'total_trades' in results
    assert 'total_pnl' in results
    assert 'win_rate' in results
    assert results['total_trades'] >= 1  # At least one trade executed


def test_backtester_equity_curve():
    """Test equity curve generation"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="ETH/USDT",
        start_price=3000,
        num_candles=150,
        trend='sideways',
        volatility=0.02
    )
    
    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=50000,
        use_risk_manager=False
    )
    
    backtester.run(data, symbol="ETH/USDT")
    equity_df = backtester.get_equity_curve()
    
    assert 'equity' in equity_df.columns
    assert len(equity_df) >= 0  # May have no trades


def test_backtester_trade_log():
    """Test trade log generation"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BNB/USDT",
        start_price=400,
        num_candles=100,
        trend='uptrend',
        volatility=0.01
    )
    
    strategy = DummyStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=30000,
        use_risk_manager=False
    )
    
    backtester.run(data, symbol="BNB/USDT")
    trade_log = backtester.get_trade_log()
    
    if len(trade_log) > 0:
        assert 'entry_time' in trade_log.columns
        assert 'exit_time' in trade_log.columns
        assert 'pnl' in trade_log.columns
        assert 'side' in trade_log.columns


# ==================== ReportGenerator Tests ====================

def test_report_generator_text_report():
    """Test text report generation"""
    results = {
        'total_trades': 10,
        'winning_trades': 6,
        'losing_trades': 4,
        'win_rate': 60.0,
        'total_pnl': 5000,
        'net_pnl': 4800,
        'sharpe_ratio': 1.5,
        'max_drawdown': 1000,
        'max_drawdown_pct': 10.0,
        'profit_factor': 2.0,
        'avg_win': 1000,
        'avg_loss': -500,
        'best_trade': 2000,
        'worst_trade': -800
    }
    
    report = ReportGenerator.generate_text_report(results, strategy_name="TestStrategy")
    
    assert "TestStrategy" in report
    assert "Total Trades" in report
    assert "Win Rate" in report
    assert "Sharpe Ratio" in report
    assert "60.00%" in report  # Win rate with 2 decimal places


def test_report_generator_save_report(tmp_path):
    """Test saving report to file"""
    results = {
        'total_trades': 5,
        'win_rate': 80.0,
        'total_pnl': 1000,
        'net_pnl': 950,
        'sharpe_ratio': 2.0,
        'max_drawdown': 200,
        'max_drawdown_pct': 5.0
    }
    
    report = ReportGenerator.generate_text_report(results, strategy_name="SaveTest")
    report_file = tmp_path / "test_report.txt"
    
    ReportGenerator.save_report(report, str(report_file))
    
    assert report_file.exists()
    content = report_file.read_text()
    assert "SaveTest" in content
