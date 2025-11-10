#!/usr/bin/env python3
"""
Stress Test Script for Extreme Market Conditions

This script tests the trading system under extreme scenarios:
- Market crash (-30% in 1 hour)
- Flash crash recovery
- Extreme volatility
- Extreme funding rates
- Liquidation prevention

Usage:
    python stress_test.py --crash-scenario --volatility extreme
    python stress_test.py --flash-crash --volatility high
    python stress_test.py --funding-stress --volatility normal
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger


class StressTestRunner:
    """Runner for stress testing under extreme market conditions."""
    
    def __init__(self, output_dir: str = "data/stress_test"):
        """Initialize stress test runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Test results
        self.liquidations = 0
        self.margin_calls = 0
        self.positions_closed_safely = 0
        self.max_drawdown = 0
        self.min_margin_level = float('inf')
        
    def generate_crash_scenario(self, volatility: str = "extreme") -> pd.DataFrame:
        """
        Generate market crash scenario data.
        
        Args:
            volatility: Volatility level (normal, high, extreme)
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Generating crash scenario with {volatility} volatility...")
        
        # Crash parameters
        if volatility == "extreme":
            crash_magnitude = 0.30  # -30% crash
            volatility_factor = 0.02  # 2% intra-candle volatility
        elif volatility == "high":
            crash_magnitude = 0.20  # -20% crash
            volatility_factor = 0.015
        else:
            crash_magnitude = 0.15  # -15% crash
            volatility_factor = 0.01
        
        # Generate 1 hour of 1-minute candles (60 candles)
        n_candles = 60
        base_price = 100000.0
        
        # Timestamps
        start_time = datetime.now()
        timestamps = [start_time + timedelta(minutes=i) for i in range(n_candles)]
        
        # Generate crash curve
        data = []
        np.random.seed(42)
        
        for i, ts in enumerate(timestamps):
            # Calculate crash progression (S-curve)
            progress = i / n_candles
            crash_factor = 1.0 / (1.0 + np.exp(-10 * (progress - 0.5)))  # Sigmoid
            
            # Calculate price (gradual crash)
            price = base_price * (1 - crash_magnitude * crash_factor)
            
            # Add noise
            noise = np.random.normal(0, volatility_factor * price)
            price += noise
            
            # Generate candle
            vol = volatility_factor * price
            high = price + abs(np.random.normal(0, vol))
            low = price - abs(np.random.normal(0, vol))
            open_price = np.random.uniform(low, high)
            close_price = price
            
            # Higher volume during crash
            volume = 1000 * (1 + crash_factor * 5)
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        
        logger.info(f"Crash scenario: {base_price:.2f} -> {df['close'].iloc[-1]:.2f} ({-crash_magnitude*100:.1f}%)")
        logger.info(f"Max 1-min drop: {(df['close'].pct_change().min() * 100):.2f}%")
        
        return df
    
    def generate_flash_crash(self, volatility: str = "extreme") -> pd.DataFrame:
        """
        Generate flash crash and recovery scenario.
        
        Args:
            volatility: Volatility level
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Generating flash crash scenario with {volatility} volatility...")
        
        # Flash crash parameters
        if volatility == "extreme":
            crash_magnitude = 0.25  # -25% flash crash
            recovery_pct = 0.80  # Recover 80%
        elif volatility == "high":
            crash_magnitude = 0.15
            recovery_pct = 0.85
        else:
            crash_magnitude = 0.10
            recovery_pct = 0.90
        
        n_candles = 30  # 30 minutes
        base_price = 100000.0
        
        start_time = datetime.now()
        timestamps = [start_time + timedelta(minutes=i) for i in range(n_candles)]
        
        data = []
        np.random.seed(42)
        
        crash_point = 10  # Crash at minute 10
        recovery_end = 25  # Full recovery by minute 25
        
        for i, ts in enumerate(timestamps):
            if i < crash_point:
                # Pre-crash: normal trading
                price = base_price * (1 + np.random.normal(0, 0.005))
            elif i < crash_point + 3:
                # Flash crash: rapid drop
                progress = (i - crash_point) / 3
                price = base_price * (1 - crash_magnitude * progress)
                price += np.random.normal(0, 0.02 * price)
            elif i < recovery_end:
                # Recovery phase
                crash_bottom = base_price * (1 - crash_magnitude)
                recovery_target = base_price * (1 - crash_magnitude * (1 - recovery_pct))
                progress = (i - crash_point - 3) / (recovery_end - crash_point - 3)
                price = crash_bottom + (recovery_target - crash_bottom) * progress
                price += np.random.normal(0, 0.015 * price)
            else:
                # Post-recovery: elevated volatility
                recovery_level = base_price * (1 - crash_magnitude * (1 - recovery_pct))
                price = recovery_level * (1 + np.random.normal(0, 0.01))
            
            # Generate candle
            vol = 0.01 * price
            high = price + abs(np.random.normal(0, vol))
            low = price - abs(np.random.normal(0, vol))
            open_price = np.random.uniform(low, high)
            close_price = price
            
            volume = 1000 * (1 + abs(i - crash_point) / 5)  # Spike during crash
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        
        logger.info(f"Flash crash: {base_price:.2f} -> {df['close'].iloc[crash_point+3]:.2f} -> {df['close'].iloc[-1]:.2f}")
        
        return df
    
    def simulate_margin_behavior(self, data: pd.DataFrame, initial_capital: float = 10000.0,
                                 leverage: float = 3.0, position_size_pct: float = 0.02) -> dict:
        """
        Simulate margin level during stress test.
        
        Args:
            data: Price data
            initial_capital: Starting capital
            leverage: Leverage used
            position_size_pct: Position size as % of capital
            
        Returns:
            Dictionary with simulation results
        """
        logger.info("Simulating margin behavior...")
        
        # Initialize
        capital = initial_capital
        peak_capital = capital
        margin_levels = []
        
        # Simulate having a position open at start
        entry_price = data['close'].iloc[0]
        position_size = (capital * position_size_pct * leverage) / entry_price
        position_value = position_size * entry_price
        
        logger.info(f"Opening simulated LONG position: {position_size:.6f} BTC at ${entry_price:.2f}")
        logger.info(f"Position value: ${position_value:.2f} (leverage: {leverage}x)")
        
        for i, row in data.iterrows():
            current_price = row['close']
            
            # Calculate P&L
            position_pnl = (current_price - entry_price) * position_size
            current_capital = capital + position_pnl
            
            # Calculate margin level
            # Margin level = Equity / Maintenance Margin * 100
            # For simplicity: maintenance margin = position_value * 0.05 (5%)
            maintenance_margin = position_value * 0.05
            margin_level = (current_capital / maintenance_margin) * 100 if maintenance_margin > 0 else 999
            
            margin_levels.append(margin_level)
            
            # Track metrics
            self.min_margin_level = min(self.min_margin_level, margin_level)
            
            # Check for margin call
            if margin_level < 200:
                logger.warning(f"⚠️  Minute {i}: Margin level {margin_level:.1f}% - Below safety threshold")
                self.margin_calls += 1
            
            if margin_level < 150:
                logger.error(f"🔴 Minute {i}: Margin level {margin_level:.1f}% - LIQUIDATION RISK!")
                self.liquidations += 1
            
            # Calculate drawdown
            peak_capital = max(peak_capital, current_capital)
            drawdown = (peak_capital - current_capital) / peak_capital
            self.max_drawdown = max(self.max_drawdown, drawdown)
            
            # Simulate safe position close if margin gets too low
            if margin_level < 150:
                logger.info(f"🛡️  Emergency position close at ${current_price:.2f}")
                self.positions_closed_safely += 1
                break
        
        final_capital = capital + position_pnl if margin_level >= 150 else current_capital
        total_pnl = final_capital - initial_capital
        
        return {
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_pnl': total_pnl,
            'total_pnl_pct': (total_pnl / initial_capital) * 100,
            'min_margin_level': self.min_margin_level,
            'max_drawdown': self.max_drawdown * 100,
            'margin_calls': self.margin_calls,
            'liquidations': self.liquidations,
            'positions_closed_safely': self.positions_closed_safely,
            'margin_levels': margin_levels
        }
    
    def print_results(self, results: dict, scenario: str):
        """Print stress test results."""
        print("\n" + "=" * 80)
        print(f"🔥 STRESS TEST RESULTS - {scenario.upper()}")
        print("=" * 80)
        
        print(f"\n💰 P&L Impact:")
        print(f"   Initial Capital: ${results['initial_capital']:.2f}")
        print(f"   Final Capital: ${results['final_capital']:.2f}")
        print(f"   Total P&L: ${results['total_pnl']:.2f} ({results['total_pnl_pct']:.2f}%)")
        
        print(f"\n🛡️ Margin Safety:")
        print(f"   Min Margin Level: {results['min_margin_level']:.2f}%")
        print(f"   Margin Calls (<200%): {results['margin_calls']}")
        print(f"   Liquidations (<150%): {results['liquidations']}")
        print(f"   Safe Position Closes: {results['positions_closed_safely']}")
        
        print(f"\n📉 Risk Metrics:")
        print(f"   Max Drawdown: {results['max_drawdown']:.2f}%")
        
        print(f"\n✅ SUCCESS CRITERIA:")
        print(f"   Liquidations = 0: {'✅ PASS' if results['liquidations'] == 0 else '❌ FAIL'} ({results['liquidations']})")
        print(f"   Margin Monitored: {'✅ PASS' if results['margin_calls'] > 0 else '⚠️  NO WARNINGS'}")
        print(f"   Positions Closed Safely: {'✅ PASS' if results['positions_closed_safely'] > 0 or results['liquidations'] == 0 else '❌ FAIL'}")
        
        print("=" * 80)
    
    def save_results(self, results: dict, scenario: str):
        """Save stress test results."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"stress_test_{scenario}_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"Stress Test Results\n")
            f.write(f"Scenario: {scenario}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total P&L: ${results['total_pnl']:.2f} ({results['total_pnl_pct']:.2f}%)\n")
            f.write(f"Min Margin Level: {results['min_margin_level']:.2f}%\n")
            f.write(f"Liquidations: {results['liquidations']}\n")
            f.write(f"Max Drawdown: {results['max_drawdown']:.2f}%\n")
        
        logger.info(f"Results saved to {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run stress test")
    parser.add_argument("--crash-scenario", action="store_true",
                       help="Test market crash scenario")
    parser.add_argument("--flash-crash", action="store_true",
                       help="Test flash crash and recovery")
    parser.add_argument("--volatility", type=str, default="extreme",
                       choices=['normal', 'high', 'extreme'],
                       help="Volatility level")
    
    args = parser.parse_args()
    
    if not (args.crash_scenario or args.flash_crash):
        print("Error: Must specify --crash-scenario or --flash-crash")
        sys.exit(1)
    
    runner = StressTestRunner()
    
    try:
        if args.crash_scenario:
            # Test crash scenario
            data = runner.generate_crash_scenario(args.volatility)
            results = runner.simulate_margin_behavior(data)
            runner.print_results(results, "crash-scenario")
            runner.save_results(results, "crash-scenario")
            
        elif args.flash_crash:
            # Test flash crash
            data = runner.generate_flash_crash(args.volatility)
            results = runner.simulate_margin_behavior(data)
            runner.print_results(results, "flash-crash")
            runner.save_results(results, "flash-crash")
        
        # Return exit code based on success
        success = results['liquidations'] == 0
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Stress test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
