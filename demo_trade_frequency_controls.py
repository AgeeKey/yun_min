#!/usr/bin/env python
"""
Demonstration script showing trade frequency controls in action.

This script demonstrates how cooldown_bars, confirmation_bars, and min_holding_bars
reduce churning by limiting trade frequency.
"""

from yunmin.backtesting import Backtester, HistoricalDataLoader
from yunmin.strategy.base import BaseStrategy, Signal, SignalType


class AggressiveStrategy(BaseStrategy):
    """Strategy that generates frequent trading signals."""
    
    def __init__(self):
        super().__init__("Aggressive")
        self.bar_count = 0
    
    def analyze(self, data):
        self.bar_count += 1
        
        # Warmup
        if len(data) < 50:
            return Signal(type=SignalType.HOLD, confidence=0.5, reason="Warmup")
        
        # Generate BUY signal every 5 bars (very aggressive)
        if self.bar_count % 5 == 0:
            return Signal(type=SignalType.BUY, confidence=0.7, reason="Buy signal")
        
        return Signal(type=SignalType.HOLD, confidence=0.5, reason="Hold")


def main():
    print("=" * 70)
    print("TRADE FREQUENCY CONTROLS DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Generate sample data
    print("Generating sample market data...")
    loader = HistoricalDataLoader()
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=50000,
        num_candles=300,
        trend='sideways',
        volatility=0.02
    )
    print(f"✓ Generated {len(data)} candles\n")
    
    # Test 1: Baseline (no controls)
    print("-" * 70)
    print("TEST 1: BASELINE (No Frequency Controls)")
    print("-" * 70)
    strategy1 = AggressiveStrategy()
    backtester1 = Backtester(
        strategy=strategy1,
        initial_capital=100000,
        use_risk_manager=False,
        cooldown_bars=0,
        min_holding_bars=0
    )
    results1 = backtester1.run(data, symbol="BTC/USDT", position_size_pct=0.1)
    print(f"Total Trades: {results1['total_trades']}")
    print(f"Win Rate: {results1['win_rate']:.1f}%")
    print(f"Total PnL: ${results1['total_pnl']:.2f}")
    print()
    
    # Test 2: With cooldown
    print("-" * 70)
    print("TEST 2: WITH COOLDOWN (10 bars between trades)")
    print("-" * 70)
    strategy2 = AggressiveStrategy()
    backtester2 = Backtester(
        strategy=strategy2,
        initial_capital=100000,
        use_risk_manager=False,
        cooldown_bars=10,
        min_holding_bars=0
    )
    results2 = backtester2.run(data, symbol="BTC/USDT", position_size_pct=0.1)
    print(f"Total Trades: {results2['total_trades']}")
    print(f"Win Rate: {results2['win_rate']:.1f}%")
    print(f"Total PnL: ${results2['total_pnl']:.2f}")
    
    if results1['total_trades'] > 0:
        reduction = ((results1['total_trades'] - results2['total_trades']) 
                     / results1['total_trades'] * 100)
        print(f"Trade Reduction: {reduction:.1f}%")
    print()
    
    # Test 3: With min holding period
    print("-" * 70)
    print("TEST 3: WITH MIN HOLDING PERIOD (15 bars minimum)")
    print("-" * 70)
    strategy3 = AggressiveStrategy()
    backtester3 = Backtester(
        strategy=strategy3,
        initial_capital=100000,
        use_risk_manager=False,
        cooldown_bars=0,
        min_holding_bars=15
    )
    results3 = backtester3.run(data, symbol="BTC/USDT", position_size_pct=0.1)
    print(f"Total Trades: {results3['total_trades']}")
    print(f"Win Rate: {results3['win_rate']:.1f}%")
    print(f"Total PnL: ${results3['total_pnl']:.2f}")
    
    if results1['total_trades'] > 0:
        reduction = ((results1['total_trades'] - results3['total_trades']) 
                     / results1['total_trades'] * 100)
        print(f"Trade Reduction: {reduction:.1f}%")
    print()
    
    # Test 4: With all controls
    print("-" * 70)
    print("TEST 4: WITH ALL CONTROLS (cooldown=5, min_hold=10)")
    print("-" * 70)
    strategy4 = AggressiveStrategy()
    backtester4 = Backtester(
        strategy=strategy4,
        initial_capital=100000,
        use_risk_manager=False,
        cooldown_bars=5,
        min_holding_bars=10
    )
    results4 = backtester4.run(data, symbol="BTC/USDT", position_size_pct=0.1)
    print(f"Total Trades: {results4['total_trades']}")
    print(f"Win Rate: {results4['win_rate']:.1f}%")
    print(f"Total PnL: ${results4['total_pnl']:.2f}")
    
    if results1['total_trades'] > 0:
        reduction = ((results1['total_trades'] - results4['total_trades']) 
                     / results1['total_trades'] * 100)
        print(f"Trade Reduction: {reduction:.1f}%")
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Configuration':<40} {'Trades':<10} {'Reduction':<15}")
    print("-" * 70)
    print(f"{'Baseline (no controls)':<40} {results1['total_trades']:<10} {'-':<15}")
    
    if results1['total_trades'] > 0:
        r2 = ((results1['total_trades'] - results2['total_trades']) / results1['total_trades'] * 100)
        r3 = ((results1['total_trades'] - results3['total_trades']) / results1['total_trades'] * 100)
        r4 = ((results1['total_trades'] - results4['total_trades']) / results1['total_trades'] * 100)
        
        print(f"{'Cooldown (10 bars)':<40} {results2['total_trades']:<10} {r2:>6.1f}%")
        print(f"{'Min Hold (15 bars)':<40} {results3['total_trades']:<10} {r3:>6.1f}%")
        print(f"{'Combined (cooldown=5, min_hold=10)':<40} {results4['total_trades']:<10} {r4:>6.1f}%")
    
    print("=" * 70)
    print()
    print("✅ Demonstration complete!")
    print()
    print("CONFIGURATION:")
    print("  These parameters can be set in config/default.yaml:")
    print("    strategy.cooldown_bars: 0-50 (bars to wait after closing position)")
    print("    strategy.confirmation_bars: 0-10 (consecutive bars with same signal)")
    print("    strategy.min_holding_bars: 0-100 (minimum bars to hold position)")


if __name__ == "__main__":
    main()
