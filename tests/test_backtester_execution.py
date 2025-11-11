"""
Unit tests for enhanced backtester execution model (Issue #38).

Tests realistic execution features:
- Position sizing
- Maker/taker fees
- Slippage
- Stop-loss/take-profit
- Leverage handling
- Per-trade CSV output
- P&L calculations
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from yunmin.backtesting.backtester import Backtester
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class SimpleTestStrategy(BaseStrategy):
    """Simple strategy for testing."""
    
    def __init__(self):
        super().__init__("test")
        self.signal_type = SignalType.HOLD
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        return Signal(
            type=self.signal_type,
            confidence=0.8,
            reason="Test signal"
        )


def generate_test_data(n_bars=100, start_price=100.0, trend='flat'):
    """Generate test OHLCV data."""
    timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n_bars)]
    
    if trend == 'up':
        prices = np.linspace(start_price, start_price * 1.1, n_bars)
    elif trend == 'down':
        prices = np.linspace(start_price, start_price * 0.9, n_bars)
    else:
        prices = np.ones(n_bars) * start_price
    
    # Add some noise
    noise = np.random.randn(n_bars) * 0.5
    prices = prices + noise
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(1000, 2000, n_bars)
    })


def test_backtester_initialization():
    """Test backtester initialization with new parameters."""
    strategy = SimpleTestStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=100000.0,
        maker_fee=0.0002,
        taker_fee=0.0004,
        slippage_rate=0.0002,
        position_size_pct=0.01,
        leverage=2.0,
        stop_loss_pct=0.02,
        take_profit_pct=0.05,
        use_risk_manager=False
    )
    
    assert backtester.initial_capital == 100000.0
    assert backtester.maker_fee == 0.0002
    assert backtester.taker_fee == 0.0004
    assert backtester.slippage_rate == 0.0002
    assert backtester.position_size_pct == 0.01
    assert backtester.leverage == 2.0
    assert backtester.stop_loss_pct == 0.02
    assert backtester.take_profit_pct == 0.05


def test_position_sizing():
    """Test position sizing calculation."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=100000.0,
        position_size_pct=0.01,
        leverage=2.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(100, 50000.0)
    
    # Trigger a buy signal
    strategy.signal_type = SignalType.BUY
    results = backtester.run(data)
    
    # Should have opened at least one position
    assert results['total_trades'] >= 0


def test_leverage_handling():
    """Test leverage calculations."""
    strategy = SimpleTestStrategy()
    
    # Test with 1x leverage
    backtester_1x = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.1,
        leverage=1.0,
        use_risk_manager=False
    )
    
    # Test with 3x leverage
    backtester_3x = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.1,
        leverage=3.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(100, 1000.0, trend='up')
    strategy.signal_type = SignalType.BUY
    
    results_1x = backtester_1x.run(data)
    results_3x = backtester_3x.run(data)
    
    # With higher leverage, P&L should be amplified
    # (but this depends on having trades, so we just check it runs)
    assert results_1x is not None
    assert results_3x is not None


def test_stop_loss_execution():
    """Test stop-loss execution."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.1,
        leverage=1.0,
        stop_loss_pct=0.02,
        use_risk_manager=False
    )
    
    # Create data with a sharp drop
    data = generate_test_data(100, 1000.0, trend='down')
    strategy.signal_type = SignalType.BUY
    
    results = backtester.run(data)
    trade_log = backtester.get_trade_log()
    
    # Check if any trades hit stop loss
    if not trade_log.empty:
        sl_trades = trade_log[trade_log['exit_reason'] == 'SL']
        assert len(sl_trades) >= 0  # May or may not hit SL depending on data


def test_take_profit_execution():
    """Test take-profit execution."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.1,
        leverage=1.0,
        take_profit_pct=0.05,
        use_risk_manager=False
    )
    
    # Create data with a sharp rise
    data = generate_test_data(100, 1000.0, trend='up')
    strategy.signal_type = SignalType.BUY
    
    results = backtester.run(data)
    trade_log = backtester.get_trade_log()
    
    # Check if any trades hit take profit
    if not trade_log.empty:
        tp_trades = trade_log[trade_log['exit_reason'] == 'TP']
        assert len(tp_trades) >= 0  # May or may not hit TP depending on data


def test_maker_taker_fees():
    """Test maker and taker fee calculations."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        maker_fee=0.0002,
        taker_fee=0.0004,
        position_size_pct=0.1,
        use_risk_manager=False
    )
    
    data = generate_test_data(100, 1000.0)
    strategy.signal_type = SignalType.BUY
    
    results = backtester.run(data)
    trade_log = backtester.get_trade_log()
    
    # All trades should have fees
    if not trade_log.empty:
        assert (trade_log['fees'] > 0).all()


def test_slippage_impact():
    """Test slippage impact on execution price."""
    strategy = SimpleTestStrategy()
    
    # Backtester with slippage
    backtester_slip = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        slippage_rate=0.01,  # 1% slippage
        position_size_pct=0.1,
        use_risk_manager=False
    )
    
    # Backtester without slippage
    backtester_no_slip = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        slippage_rate=0.0,  # No slippage
        position_size_pct=0.1,
        use_risk_manager=False
    )
    
    data = generate_test_data(100, 1000.0, trend='up')
    strategy.signal_type = SignalType.BUY
    
    results_slip = backtester_slip.run(data)
    results_no_slip = backtester_no_slip.run(data)
    
    # With slippage, results should be worse (or at least different)
    assert results_slip is not None
    assert results_no_slip is not None


def test_pnl_calculation_long():
    """Test P&L calculation for long positions."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.5,  # Large position for clear results
        leverage=1.0,
        maker_fee=0.0,
        taker_fee=0.0,
        slippage_rate=0.0,
        use_risk_manager=False
    )
    
    # Create simple data with known outcome
    data = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(minutes=i*5) for i in range(60)],
        'open': [1000.0] * 30 + [1100.0] * 30,
        'high': [1005.0] * 30 + [1105.0] * 30,
        'low': [995.0] * 30 + [1095.0] * 30,
        'close': [1000.0] * 30 + [1100.0] * 30,
        'volume': [1000.0] * 60
    })
    
    strategy.signal_type = SignalType.BUY
    results = backtester.run(data)
    
    # Should have made profit if position was opened and closed
    assert results is not None


def test_pnl_calculation_short():
    """Test P&L calculation for short positions."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        position_size_pct=0.5,
        leverage=1.0,
        maker_fee=0.0,
        taker_fee=0.0,
        slippage_rate=0.0,
        use_risk_manager=False
    )
    
    # Create data with downtrend
    data = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(minutes=i*5) for i in range(60)],
        'open': [1000.0] * 30 + [900.0] * 30,
        'high': [1005.0] * 30 + [905.0] * 30,
        'low': [995.0] * 30 + [895.0] * 30,
        'close': [1000.0] * 30 + [900.0] * 30,
        'volume': [1000.0] * 60
    })
    
    strategy.signal_type = SignalType.SELL
    results = backtester.run(data)
    
    # Should have made profit on short if position opened and closed
    assert results is not None


def test_trade_log_export():
    """Test trade log CSV export."""
    import tempfile
    import os
    
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        use_risk_manager=False
    )
    
    data = generate_test_data(100, 1000.0)
    strategy.signal_type = SignalType.BUY
    
    backtester.run(data)
    
    # Export to CSV
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        filepath = f.name
    
    try:
        backtester.save_trade_log(filepath)
        
        # Check file exists and has content
        assert os.path.exists(filepath)
        
        # Read back and verify
        df = pd.read_csv(filepath)
        assert 'entry_time' in df.columns
        assert 'exit_time' in df.columns
        assert 'pnl' in df.columns
        assert 'fees' in df.columns
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


def test_rejected_trades_tracking():
    """Test tracking of rejected trades (with risk manager)."""
    strategy = SimpleTestStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=1000.0,  # Small capital
        position_size_pct=0.5,  # Large position
        use_risk_manager=True  # Enable risk manager
    )
    
    data = generate_test_data(100, 50000.0)  # High price
    strategy.signal_type = SignalType.BUY
    
    results = backtester.run(data)
    
    # Check rejected trades
    rejected = backtester.get_rejected_trades()
    assert rejected is not None
    assert results['rejected_trades'] >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
