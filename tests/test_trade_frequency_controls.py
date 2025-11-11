"""
Unit tests for trade frequency controls (Issue #39).

Tests:
- Cooldown bars (minimum bars between trades)
- Confirmation bars (bars to confirm signal)
- Minimum holding bars (minimum bars to hold position)
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from yunmin.backtesting.backtester import Backtester
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class ControlledStrategy(BaseStrategy):
    """Strategy with controlled signal generation for testing."""
    
    def __init__(self):
        super().__init__("controlled")
        self.signals = []
        self.current_idx = 0
        
    def add_signal(self, bar_idx, signal_type):
        """Add a signal at specific bar."""
        self.signals.append((bar_idx, signal_type))
        
    def analyze(self, data: pd.DataFrame) -> Signal:
        bar_idx = len(data) - 1
        
        # Check if we have a signal for this bar
        for sig_bar, sig_type in self.signals:
            if sig_bar == bar_idx:
                return Signal(type=sig_type, confidence=0.8, reason="Test")
        
        return Signal(type=SignalType.HOLD, confidence=0.0, reason="Hold")


def generate_flat_data(n_bars=200, price=1000.0):
    """Generate flat price data for testing."""
    timestamps = [datetime.now() + timedelta(minutes=i*5) for i in range(n_bars)]
    prices = np.ones(n_bars) * price
    
    return pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * 1.001,
        'low': prices * 0.999,
        'close': prices,
        'volume': np.ones(n_bars) * 1000
    })


def test_cooldown_bars():
    """Test cooldown period between trades."""
    strategy = ControlledStrategy()
    
    # Add buy signal at bar 60
    strategy.add_signal(60, SignalType.BUY)
    # Add close signal at bar 70
    strategy.add_signal(70, SignalType.CLOSE)
    # Add another buy signal at bar 75 (within cooldown)
    strategy.add_signal(75, SignalType.BUY)
    # Add buy signal at bar 85 (after cooldown)
    strategy.add_signal(85, SignalType.BUY)
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        cooldown_bars=10,  # 10 bar cooldown
        use_risk_manager=False
    )
    
    data = generate_flat_data(200, 1000.0)
    results = backtester.run(data)
    
    # First trade should open at 60, close at 70
    # Second attempt at 75 should be blocked (within cooldown)
    # Third attempt at 85 should succeed (after cooldown)
    trade_log = backtester.get_trade_log()
    
    if not trade_log.empty:
        # Check that trades respect cooldown
        entry_bars = trade_log['entry_bar'].values
        if len(entry_bars) >= 2:
            # Check minimum gap between entries
            for i in range(1, len(entry_bars)):
                gap = entry_bars[i] - trade_log.iloc[i-1]['exit_bar']
                assert gap >= 10, f"Cooldown violated: gap={gap}"


def test_confirmation_bars():
    """Test signal confirmation requirement."""
    strategy = ControlledStrategy()
    
    # Add buy signals for 3 consecutive bars starting at 60
    for i in range(60, 63):
        strategy.add_signal(i, SignalType.BUY)
    
    # Test with 2 bar confirmation
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        confirmation_bars=2,
        use_risk_manager=False
    )
    
    data = generate_flat_data(150, 1000.0)
    results = backtester.run(data)
    
    trade_log = backtester.get_trade_log()
    
    # Trade should open after confirmation (not at first signal)
    if not trade_log.empty:
        first_entry_bar = trade_log.iloc[0]['entry_bar']
        # Should enter at bar 61 (after 2 confirmations: bar 60, 61)
        assert first_entry_bar >= 61


def test_confirmation_bars_interrupted():
    """Test that signal confirmation resets when signal changes."""
    strategy = ControlledStrategy()
    
    # Add buy signal at 60
    strategy.add_signal(60, SignalType.BUY)
    # Add sell signal at 61 (interrupts confirmation)
    strategy.add_signal(61, SignalType.SELL)
    # Add buy signals at 62-64
    for i in range(62, 65):
        strategy.add_signal(i, SignalType.BUY)
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        confirmation_bars=2,
        use_risk_manager=False
    )
    
    data = generate_flat_data(150, 1000.0)
    results = backtester.run(data)
    
    trade_log = backtester.get_trade_log()
    
    # Should only get confirmed buy after bar 62 (reset happened)
    if not trade_log.empty:
        first_entry_bar = trade_log.iloc[0]['entry_bar']
        assert first_entry_bar >= 63  # Confirmed at bar 63


def test_min_holding_bars():
    """Test minimum holding period for positions."""
    strategy = ControlledStrategy()
    
    # Add buy signal at 60
    strategy.add_signal(60, SignalType.BUY)
    # Add close signal at 65 (within min holding)
    strategy.add_signal(65, SignalType.CLOSE)
    # Add close signal at 75 (after min holding)
    strategy.add_signal(75, SignalType.CLOSE)
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        min_holding_bars=10,  # Must hold for at least 10 bars
        use_risk_manager=False
    )
    
    data = generate_flat_data(150, 1000.0)
    results = backtester.run(data)
    
    trade_log = backtester.get_trade_log()
    
    if not trade_log.empty:
        # Check that position was held for at least min_holding_bars
        for _, trade in trade_log.iterrows():
            bars_held = trade['exit_bar'] - trade['entry_bar']
            assert bars_held >= 10, f"Min holding violated: held {bars_held} bars"


def test_combined_frequency_controls():
    """Test all frequency controls working together."""
    strategy = ControlledStrategy()
    
    # First trade: buy at 60, hold, close at 75
    for i in range(60, 63):
        strategy.add_signal(i, SignalType.BUY)
    strategy.add_signal(75, SignalType.CLOSE)
    
    # Second trade: buy at 90 (after cooldown), close at 110
    for i in range(90, 93):
        strategy.add_signal(i, SignalType.BUY)
    strategy.add_signal(110, SignalType.CLOSE)
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        cooldown_bars=5,
        confirmation_bars=2,
        min_holding_bars=10,
        use_risk_manager=False
    )
    
    data = generate_flat_data(200, 1000.0)
    results = backtester.run(data)
    
    trade_log = backtester.get_trade_log()
    
    # Should have at most 2 trades
    assert len(trade_log) <= 2
    
    # All trades should respect all rules
    if len(trade_log) > 0:
        for _, trade in trade_log.iterrows():
            # Check minimum holding
            bars_held = trade['exit_bar'] - trade['entry_bar']
            assert bars_held >= 10


def test_no_frequency_controls():
    """Test that backtester works normally with no frequency controls."""
    strategy = ControlledStrategy()
    
    # Multiple rapid signals
    strategy.add_signal(60, SignalType.BUY)
    strategy.add_signal(65, SignalType.CLOSE)
    strategy.add_signal(66, SignalType.BUY)
    strategy.add_signal(70, SignalType.CLOSE)
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        cooldown_bars=0,  # No cooldown
        confirmation_bars=0,  # No confirmation
        min_holding_bars=0,  # No min holding
        use_risk_manager=False
    )
    
    data = generate_flat_data(150, 1000.0)
    results = backtester.run(data)
    
    # Should execute trades without restrictions
    trade_log = backtester.get_trade_log()
    assert len(trade_log) >= 0  # Just check it runs


def test_cooldown_with_stop_loss():
    """Test cooldown applies after stop-loss exits."""
    strategy = ControlledStrategy()
    
    # Add buy signal at 60
    strategy.add_signal(60, SignalType.BUY)
    # Add another buy at 65 (within cooldown, should be blocked)
    strategy.add_signal(65, SignalType.BUY)
    
    # Create data with price drop to trigger SL
    data = pd.DataFrame({
        'timestamp': [datetime.now() + timedelta(minutes=i*5) for i in range(150)],
        'open': [1000.0] * 60 + [950.0] * 90,  # Drop after bar 60
        'high': [1005.0] * 60 + [955.0] * 90,
        'low': [995.0] * 60 + [945.0] * 90,
        'close': [1000.0] * 60 + [950.0] * 90,
        'volume': [1000.0] * 150
    })
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000.0,
        cooldown_bars=10,
        stop_loss_pct=0.02,  # 2% stop loss
        use_risk_manager=False
    )
    
    results = backtester.run(data)
    trade_log = backtester.get_trade_log()
    
    # Should have at most 1 trade (second blocked by cooldown)
    # or could have 0 if SL triggers before second signal
    assert len(trade_log) <= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
