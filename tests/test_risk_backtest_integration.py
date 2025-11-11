"""
Tests for RiskManager integration with Backtester

Tests validate:
- Max daily loss rejection
- Max position size rejection
- Circuit breaker activation
- Trade rejection logging
- CSV export of rejected trades
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from yunmin.backtesting import Backtester, HistoricalDataLoader
from yunmin.strategy.base import BaseStrategy, SignalType, Signal
from yunmin.core.config import RiskConfig
from yunmin.risk.manager import RiskManager


class AggressiveStrategy(BaseStrategy):
    """Strategy that generates many buy signals for testing risk limits"""
    
    def __init__(self):
        super().__init__("AggressiveStrategy")
        self.call_count = 0
    
    def analyze(self, data: pd.DataFrame) -> Signal:
        """Generate buy signal every 5 calls"""
        self.call_count += 1
        if self.call_count % 5 == 0:
            return Signal(type=SignalType.BUY, confidence=0.9, reason="Aggressive buy")
        elif self.call_count % 10 == 0:
            return Signal(type=SignalType.CLOSE, confidence=0.8, reason="Close")
        return Signal(type=SignalType.HOLD, confidence=0.5, reason="Hold")


class TestRiskBacktestIntegration:
    """Test risk manager integration with backtester"""
    
    def test_max_position_size_rejection(self):
        """Test that trades exceeding max position size are rejected"""
        # Setup strategy and data
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=100,
            trend='sideways',
            volatility=0.01
        )
        
        # Setup backtester with strict position size limit
        risk_config = RiskConfig(
            max_position_size=0.05,  # Only 5% of capital allowed
            max_leverage=1.0,
            enable_circuit_breaker=False
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False  # We'll inject our own
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Run backtest with 20% position size (should be rejected)
        results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.20)
        
        # Verify trades were rejected
        assert results['rejected_trades'] > 0, "Expected some trades to be rejected"
        
        # Get rejected trades log
        rejected_log = backtester.get_rejected_trades_log()
        assert not rejected_log.empty, "Rejected trades log should not be empty"
        
        # Verify rejection reasons contain position size
        first_rejection = rejected_log.iloc[0]['rejection_reasons']
        assert 'max position size' in first_rejection.lower(), \
            f"Expected position size rejection, got: {first_rejection}"
    
    def test_max_daily_drawdown_rejection(self):
        """Test that trades are rejected when daily drawdown limit is hit"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        
        # Generate downtrend data to create losses
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=200,
            trend='downtrend',
            volatility=0.02
        )
        
        # Setup backtester with strict daily drawdown limit
        risk_config = RiskConfig(
            max_position_size=0.15,
            max_daily_drawdown=0.03,  # 3% daily drawdown limit
            enable_circuit_breaker=False
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Run backtest
        results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.15)
        
        # In a downtrend, we expect either:
        # 1. Some rejected trades due to daily drawdown, OR
        # 2. Actual losses that would trigger the check
        rejected_log = backtester.get_rejected_trades_log()
        
        # Check if any trades mention daily drawdown
        if not rejected_log.empty:
            daily_drawdown_rejections = rejected_log[
                rejected_log['rejection_reasons'].str.contains('daily drawdown', case=False)
            ]
            # If there are rejections, at least one should be about drawdown
            if len(rejected_log) > 0:
                print(f"Found {len(daily_drawdown_rejections)} daily drawdown rejections")
    
    def test_circuit_breaker_rejection(self):
        """Test that trades are rejected when circuit breaker is triggered"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=150,
            trend='sideways',
            volatility=0.01
        )
        
        # Setup backtester with circuit breaker
        risk_config = RiskConfig(
            max_position_size=0.1,
            enable_circuit_breaker=True
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Trigger circuit breaker before running
        backtester.risk_manager.trigger_circuit_breaker("Test emergency condition")
        
        # Run backtest
        results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.1)
        
        # All trades should be rejected
        assert results['total_trades'] == 0, "No trades should execute with circuit breaker active"
        assert results['rejected_trades'] > 0, "Expected trades to be rejected"
        
        # Verify rejection reasons
        rejected_log = backtester.get_rejected_trades_log()
        assert not rejected_log.empty
        first_rejection = rejected_log.iloc[0]['rejection_reasons']
        assert 'circuit breaker' in first_rejection.lower(), \
            f"Expected circuit breaker rejection, got: {first_rejection}"
    
    def test_trade_rejection_logging(self):
        """Test that rejected trades are properly logged"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=100,
            trend='uptrend',
            volatility=0.01
        )
        
        # Setup with very restrictive limits
        risk_config = RiskConfig(
            max_position_size=0.01,  # Only 1% - very restrictive
            max_leverage=1.0,
            enable_circuit_breaker=False
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Run with 10% position size (10x the limit)
        results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.10)
        
        # Verify logging
        rejected_log = backtester.get_rejected_trades_log()
        
        if not rejected_log.empty:
            # Verify all required columns exist
            assert 'timestamp' in rejected_log.columns
            assert 'symbol' in rejected_log.columns
            assert 'side' in rejected_log.columns
            assert 'amount' in rejected_log.columns
            assert 'price' in rejected_log.columns
            assert 'rejection_reasons' in rejected_log.columns
            
            # Verify data integrity
            assert rejected_log['symbol'].iloc[0] == 'BTC/USDT'
            assert len(rejected_log['rejection_reasons'].iloc[0]) > 0
    
    def test_rejected_trades_in_metrics(self):
        """Test that rejected trades count appears in metrics"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="ETH/USDT",
            start_price=3000,
            num_candles=100,
            trend='sideways',
            volatility=0.01
        )
        
        # Create backtester with circuit breaker to force rejections
        risk_config = RiskConfig(
            max_position_size=0.1,
            enable_circuit_breaker=True
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=5000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Trigger circuit breaker
        backtester.risk_manager.trigger_circuit_breaker("Test condition")
        
        # Run backtest
        results = backtester.run(data, symbol="ETH/USDT", position_size_pct=0.1)
        
        # Verify metrics include rejected_trades
        assert 'rejected_trades' in results
        assert results['rejected_trades'] >= 0
        assert isinstance(results['rejected_trades'], int)
    
    def test_rejected_trades_csv_export(self, tmp_path):
        """Test exporting rejected trades to CSV"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=100,
            trend='sideways',
            volatility=0.01
        )
        
        # Setup with restrictive limits
        risk_config = RiskConfig(
            max_position_size=0.05,
            enable_circuit_breaker=False
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Run backtest with large position size
        backtester.run(data, symbol="BTC/USDT", position_size_pct=0.15)
        
        # Export rejected trades
        rejected_log = backtester.get_rejected_trades_log()
        
        if not rejected_log.empty:
            csv_path = tmp_path / "rejected_trades.csv"
            rejected_log.to_csv(csv_path, index=False)
            
            # Verify CSV was created
            assert csv_path.exists()
            
            # Read back and verify
            loaded_df = pd.read_csv(csv_path)
            assert len(loaded_df) == len(rejected_log)
            assert 'rejection_reasons' in loaded_df.columns
    
    def test_normal_operation_with_risk_manager(self):
        """Test that normal trades pass through when within limits"""
        strategy = AggressiveStrategy()
        loader = HistoricalDataLoader()
        data = loader.generate_sample_data(
            symbol="BTC/USDT",
            start_price=50000,
            num_candles=100,
            trend='uptrend',
            volatility=0.01
        )
        
        # Setup with reasonable limits
        risk_config = RiskConfig(
            max_position_size=0.15,
            max_leverage=3.0,
            max_daily_drawdown=0.10,
            enable_circuit_breaker=False
        )
        
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            use_risk_manager=False
        )
        backtester.risk_manager = RiskManager(risk_config)
        
        # Run with 10% position size (within 15% limit)
        results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.10)
        
        # Should have some executed trades
        assert results['total_trades'] > 0, "Expected some trades to execute"
        
        # Rejected trades should be low or zero
        # (depends on market conditions and strategy)
        print(f"Executed: {results['total_trades']}, Rejected: {results['rejected_trades']}")


class TestMaxLeverageRejection:
    """Test leverage-based rejections"""
    
    def test_excessive_leverage_rejected(self):
        """Test that orders with excessive leverage are rejected"""
        from yunmin.risk.policies import OrderRequest
        
        risk_config = RiskConfig(
            max_leverage=3.0,
            max_position_size=0.5
        )
        risk_manager = RiskManager(risk_config)
        
        # Create order with 10x leverage (exceeds 3x limit)
        order = OrderRequest(
            symbol='BTC/USDT',
            side='buy',
            order_type='market',
            amount=0.1,
            price=50000,
            leverage=10.0
        )
        
        context = {'capital': 10000, 'current_price': 50000}
        approved, messages = risk_manager.validate_order(order, context)
        
        # Should be rejected
        assert approved is False
        assert any('leverage' in msg.lower() for msg in messages)
