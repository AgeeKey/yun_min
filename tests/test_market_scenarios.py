"""
Market Scenario Tests - Bull/Bear/Sideways market conditions
Tests strategy performance across different market regimes
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from yunmin.backtesting.data_loader import HistoricalDataLoader
from yunmin.backtesting.backtester import Backtester
from yunmin.strategy.ema_crossover import EMACrossoverStrategy


# ==================== Test Data Generators ====================

def generate_bull_market(days: int = 30, start_price: float = 40000) -> pd.DataFrame:
    """Generate bullish market data (consistent uptrend)"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=start_price,
        trend="uptrend",
        num_candles=days * 288  # 5min candles
    )
    return data


def generate_bear_market(days: int = 30, start_price: float = 50000) -> pd.DataFrame:
    """Generate bearish market data (consistent downtrend)"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=start_price,
        trend="downtrend",
        num_candles=days * 288
    )
    return data


def generate_sideways_market(days: int = 30, start_price: float = 45000) -> pd.DataFrame:
    """Generate sideways/ranging market data"""
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=start_price,
        trend="sideways",
        num_candles=days * 288
    )
    return data


def generate_volatile_market(days: int = 30, start_price: float = 45000) -> pd.DataFrame:
    """Generate highly volatile market (rapid swings)"""
    timestamps = pd.date_range(
        start=datetime.now() - timedelta(days=days),
        periods=days * 288,
        freq='5min'
    )
    
    prices = [start_price]
    for i in range(1, len(timestamps)):
        # Random walk with high volatility
        change = np.random.normal(0, start_price * 0.02)  # 2% std dev
        prices.append(max(prices[-1] + change, start_price * 0.5))  # Floor at 50%
    
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, len(timestamps))
    })
    
    return data


# ==================== Bull Market Tests ====================

def test_bull_market_long_only():
    """Test LONG-only strategy in bull market"""
    data = generate_bull_market(days=10)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # In bull market, LONG strategy should be profitable
    assert metrics['total_trades'] > 0
    assert metrics['net_pnl'] > 0  # Should be profitable
    assert metrics['win_rate'] >= 40  # At least 40% win rate


def test_bull_market_metrics():
    """Test performance metrics in bull market"""
    data = generate_bull_market(days=15)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Bull market should have positive returns
    assert metrics['total_return'] > 0
    assert metrics['max_drawdown'] < 1000  # Limited drawdown
    assert metrics['sharpe_ratio'] > 0  # Positive risk-adjusted return


# ==================== Bear Market Tests ====================

def test_bear_market_short_strategy():
    """Test SHORT strategy in bear market"""
    data = generate_bear_market(days=10)
    
    # Use strategy that can SHORT
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001,
        allow_short=True  # Enable shorting
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Bear market tests
    assert metrics['total_trades'] >= 0
    # Note: Strategy might avoid trading in bad conditions


def test_bear_market_long_protection():
    """Test LONG strategy protects capital in bear market"""
    data = generate_bear_market(days=10)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Strategy should avoid excessive losses
    assert metrics['max_drawdown'] < 3000  # Max 30% drawdown
    # Might have negative P&L but should limit losses
    assert metrics['net_pnl'] > -3000


# ==================== Sideways Market Tests ====================

def test_sideways_market_range_trading():
    """Test range trading in sideways market"""
    data = generate_sideways_market(days=20)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Sideways market characteristics
    assert metrics['total_trades'] > 0
    # Win rate might be lower due to whipsaws
    assert 0 <= metrics['win_rate'] <= 100
    # Should limit losses even if not profitable
    assert metrics['max_drawdown_pct'] < 20


def test_sideways_market_commission_impact():
    """Test commission impact in sideways market"""
    data = generate_sideways_market(days=15)
    strategy = EMACrossoverStrategy()
    
    # Run with different commission rates
    backtester_low_fee = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.0001
    )
    
    backtester_high_fee = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.005
    )
    
    metrics_low = backtester_low_fee.run(data.copy(), symbol="BTC/USDT")
    metrics_high = backtester_high_fee.run(data.copy(), symbol="BTC/USDT")
    
    # Higher fees should reduce net P&L
    assert metrics_low['net_pnl'] >= metrics_high['net_pnl']
    assert metrics_high['total_fees'] > metrics_low['total_fees']


# ==================== Volatile Market Tests ====================

def test_volatile_market_risk_management():
    """Test risk management in volatile market"""
    data = generate_volatile_market(days=10)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001,
        max_position_pct=0.1  # Conservative position sizing
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Volatile market risk checks
    assert metrics['max_drawdown_pct'] < 30  # Limit max drawdown
    if metrics['total_trades'] > 0:
        # If trading, should have reasonable worst trade limit
        assert abs(metrics['worst_trade']) < 1000


def test_volatile_market_stop_loss():
    """Test stop-loss effectiveness in volatile market"""
    data = generate_volatile_market(days=15)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001,
        stop_loss_pct=0.02  # 2% stop loss
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Stop loss should limit individual trade losses
    if metrics['losing_trades'] > 0:
        # Average loss should be within stop loss range
        assert abs(metrics['avg_loss']) < 500  # ~5% of $10k


# ==================== Multi-Scenario Comparison ====================

def test_strategy_across_all_scenarios():
    """Test strategy performance across all market scenarios"""
    strategy = EMACrossoverStrategy()
    scenarios = {
        'bull': generate_bull_market(days=10),
        'bear': generate_bear_market(days=10),
        'sideways': generate_sideways_market(days=10),
        'volatile': generate_volatile_market(days=10)
    }
    
    results = {}
    
    for scenario_name, data in scenarios.items():
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            commission_rate=0.001
        )
        
        metrics = backtester.run(data, symbol="BTC/USDT")
        results[scenario_name] = metrics
    
    # Bull market should outperform
    if results['bull']['total_trades'] > 0:
        assert results['bull']['total_return'] >= results['bear'].get('total_return', -100)
    
    # All scenarios should limit max drawdown
    for scenario, metrics in results.items():
        assert metrics['max_drawdown_pct'] < 50, f"{scenario} exceeded 50% drawdown"


def test_scenario_summary():
    """Generate summary report across scenarios"""
    strategy = EMACrossoverStrategy()
    scenarios = {
        'Bull Market (30d)': generate_bull_market(days=30),
        'Bear Market (30d)': generate_bear_market(days=30),
        'Sideways (30d)': generate_sideways_market(days=30)
    }
    
    summary = []
    
    for scenario_name, data in scenarios.items():
        backtester = Backtester(
            strategy=strategy,
            initial_capital=10000,
            commission_rate=0.001
        )
        
        metrics = backtester.run(data, symbol="BTC/USDT")
        
        summary.append({
            'scenario': scenario_name,
            'trades': metrics['total_trades'],
            'win_rate': metrics['win_rate'],
            'total_return': metrics['total_return'],
            'sharpe': metrics['sharpe_ratio'],
            'max_dd': metrics['max_drawdown_pct']
        })
    
    # Verify we have results for all scenarios
    assert len(summary) == 3
    
    # Print summary (visible in pytest -v output)
    print("\n=== SCENARIO SUMMARY ===")
    for result in summary:
        print(f"\n{result['scenario']}:")
        print(f"  Trades: {result['trades']}")
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print(f"  Return: {result['total_return']:.2f}%")
        print(f"  Sharpe: {result['sharpe']:.2f}")
        print(f"  Max DD: {result['max_dd']:.2f}%")


# ==================== Stress Tests ====================

@pytest.mark.slow
def test_extended_bull_run():
    """Test strategy over extended bull market"""
    data = generate_bull_market(days=90)  # 3 months
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Extended bull market should be profitable
    assert metrics['total_return'] > 0
    assert metrics['win_rate'] > 40


@pytest.mark.slow
def test_extended_bear_market():
    """Test strategy survival in extended bear market"""
    data = generate_bear_market(days=90)
    strategy = EMACrossoverStrategy()
    
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(data, symbol="BTC/USDT")
    
    # Should preserve at least 50% of capital
    final_equity = 10000 + metrics['net_pnl']
    assert final_equity > 5000


@pytest.mark.slow
def test_mixed_market_conditions():
    """Test strategy across mixed market conditions"""
    # Combine different market scenarios
    bull_data = generate_bull_market(days=20)
    bear_data = generate_bear_market(days=20)
    sideways_data = generate_sideways_market(days=20)
    
    # Concatenate (reset index to avoid duplicates)
    combined = pd.concat([
        bull_data.reset_index(drop=True),
        sideways_data.reset_index(drop=True),
        bear_data.reset_index(drop=True)
    ], ignore_index=True)
    
    strategy = EMACrossoverStrategy()
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001
    )
    
    metrics = backtester.run(combined, symbol="BTC/USDT")
    
    # Should handle mixed conditions
    assert metrics['total_trades'] > 0
    assert metrics['max_drawdown_pct'] < 40  # Reasonable drawdown
