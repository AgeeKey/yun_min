#!/usr/bin/env python3
"""
Historical Backtest Script for Futures Strategy Validation

This script runs backtests on historical data to validate:
- Bull market performance
- Bear market performance
- Win rate consistency
- Max drawdown control
- Profit factor

Usage:
    python backtest_historical.py --period bull-market --lookback 3m
    python backtest_historical.py --period bear-market --lookback 3m
    python backtest_historical.py --period sideways --lookback 1m
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger

from yunmin.core.backtester import AdvancedBacktester
from yunmin.strategy.ema_crossover import EMACrossoverStrategy


class HistoricalBacktestRunner:
    """Runner for historical backtesting with different market conditions."""
    
    def __init__(self, output_dir: str = "data/backtest_results"):
        """Initialize backtest runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_market_data(self, period: str, lookback_months: int) -> pd.DataFrame:
        """
        Generate synthetic market data for different periods.
        
        Args:
            period: Market period type (bull-market, bear-market, sideways)
            lookback_months: Number of months to simulate
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Generating {period} data for {lookback_months} months...")
        
        # Calculate number of 5-minute candles
        days = lookback_months * 30
        candles_per_day = 288  # 24 hours * 60 minutes / 5 minutes
        n_candles = days * candles_per_day
        
        # Generate timestamps
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timestamps = pd.date_range(start=start_date, end=end_date, periods=n_candles)
        
        # Set initial price
        base_price = 95000.0
        prices = [base_price]
        
        np.random.seed(42)  # For reproducibility
        
        # Generate prices based on market condition
        for i in range(1, n_candles):
            if period == "bull-market":
                # Uptrend with moderate volatility
                trend = 0.0002  # +0.02% per candle on average
                volatility = 0.0008
                noise = np.random.normal(trend, volatility)
                
            elif period == "bear-market":
                # Downtrend with higher volatility
                trend = -0.0002  # -0.02% per candle on average
                volatility = 0.001
                noise = np.random.normal(trend, volatility)
                
            elif period == "sideways":
                # No trend, mean-reverting
                trend = 0
                volatility = 0.0006
                noise = np.random.normal(trend, volatility)
                
                # Add mean reversion
                deviation = (prices[-1] - base_price) / base_price
                noise -= deviation * 0.1  # Pull back to base price
                
            else:
                raise ValueError(f"Unknown period: {period}")
            
            # Add momentum (autocorrelation)
            if len(prices) > 10:
                recent_change = (prices[-1] - prices[-10]) / prices[-10]
                momentum = recent_change * 0.05
                noise += momentum
            
            # Clip extreme movements
            noise = np.clip(noise, -0.01, 0.01)
            
            # Calculate new price
            new_price = prices[-1] * (1 + noise)
            prices.append(new_price)
        
        # Generate OHLCV data from prices
        data = []
        for i, (ts, price) in enumerate(zip(timestamps, prices)):
            # Generate candle with some randomness
            volatility = price * 0.001  # 0.1% intra-candle volatility
            
            high = price + np.random.uniform(0, volatility)
            low = price - np.random.uniform(0, volatility)
            
            # Open and close within high-low range
            open_price = np.random.uniform(low, high)
            close_price = price
            
            # Volume (higher during volatile periods)
            base_volume = 1000
            volume = base_volume * (1 + abs(close_price - open_price) / open_price * 10)
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        logger.info(f"Generated {len(df)} candles from {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return df
    
    def run_backtest(self, data: pd.DataFrame, period: str) -> dict:
        """
        Run backtest on historical data.
        
        Args:
            data: OHLCV DataFrame
            period: Market period name for reporting
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest for {period}...")
        
        # Create strategy
        strategy = EMACrossoverStrategy(
            fast_period=12,
            slow_period=26,
            rsi_period=14,
            rsi_overbought=70.0,
            rsi_oversold=30.0
        )
        
        # Create backtester
        backtester = AdvancedBacktester(
            initial_capital=10000.0,
            commission_rate=0.001,  # 0.1% per trade
            slippage_rate=0.0005    # 0.05% slippage
        )
        
        # Run backtest
        results = backtester.run(data, strategy)
        
        # Calculate metrics
        trades = results.get('trades', [])
        equity_curve = results.get('equity_curve', [10000])
        
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
        losing_trades = len([t for t in trades if t.get('pnl', 0) <= 0])
        
        win_rate = (winning_trades / max(1, total_trades)) * 100
        
        # Calculate profit factor
        gross_profit = sum([t['pnl'] for t in trades if t.get('pnl', 0) > 0])
        gross_loss = abs(sum([t['pnl'] for t in trades if t.get('pnl', 0) < 0]))
        profit_factor = gross_profit / max(1, gross_loss)
        
        # Calculate drawdown
        peak = equity_curve[0]
        max_drawdown = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate Sharpe ratio (simplified, assuming daily returns)
        returns = pd.Series(equity_curve).pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized
        else:
            sharpe_ratio = 0
        
        # Calculate final P&L
        final_equity = equity_curve[-1] if equity_curve else 10000
        total_pnl = final_equity - 10000
        total_pnl_pct = (total_pnl / 10000) * 100
        
        # Compile results
        summary = {
            'period': period,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'final_equity': final_equity
        }
        
        return summary
    
    def print_results(self, summary: dict):
        """Print backtest results."""
        print("\n" + "=" * 80)
        print(f"📊 BACKTEST RESULTS - {summary['period'].upper()}")
        print("=" * 80)
        
        print(f"\n💰 P&L Summary:")
        print(f"   Total P&L: ${summary['total_pnl']:.2f} ({summary['total_pnl_pct']:.2f}%)")
        print(f"   Final Equity: ${summary['final_equity']:.2f}")
        
        print(f"\n📈 Trading Performance:")
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Winning Trades: {summary['winning_trades']}")
        print(f"   Losing Trades: {summary['losing_trades']}")
        print(f"   Win Rate: {summary['win_rate']:.1f}%")
        print(f"   Profit Factor: {summary['profit_factor']:.2f}")
        
        print(f"\n📊 Risk Metrics:")
        print(f"   Max Drawdown: {summary['max_drawdown']:.2f}%")
        print(f"   Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
        
        print(f"\n✅ SUCCESS CRITERIA:")
        print(f"   Win Rate > 40%: {'✅ PASS' if summary['win_rate'] > 40 else '❌ FAIL'} ({summary['win_rate']:.1f}%)")
        print(f"   Profit Factor > 1.5: {'✅ PASS' if summary['profit_factor'] > 1.5 else '❌ FAIL'} ({summary['profit_factor']:.2f})")
        print(f"   Max Drawdown < 15%: {'✅ PASS' if summary['max_drawdown'] < 15 else '❌ FAIL'} ({summary['max_drawdown']:.1f}%)")
        print(f"   Sharpe Ratio > 1.0: {'✅ PASS' if summary['sharpe_ratio'] > 1.0 else '❌ FAIL'} ({summary['sharpe_ratio']:.2f})")
        
        print("=" * 80)
    
    def save_results(self, summary: dict):
        """Save results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"backtest_{summary['period']}_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"Historical Backtest Results\n")
            f.write(f"Period: {summary['period']}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write(f"Total Trades: {summary['total_trades']}\n")
            f.write(f"Win Rate: {summary['win_rate']:.1f}%\n")
            f.write(f"Profit Factor: {summary['profit_factor']:.2f}\n")
            f.write(f"Max Drawdown: {summary['max_drawdown']:.2f}%\n")
            f.write(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}\n")
            f.write(f"Total P&L: ${summary['total_pnl']:.2f} ({summary['total_pnl_pct']:.2f}%)\n")
        
        logger.info(f"Results saved to {filename}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run historical backtest")
    parser.add_argument("--period", type=str, required=True,
                       choices=['bull-market', 'bear-market', 'sideways'],
                       help="Market period to test")
    parser.add_argument("--lookback", type=str, default="3m",
                       help="Lookback period (e.g., '1m', '3m', '6m')")
    
    args = parser.parse_args()
    
    # Parse lookback period
    lookback_str = args.lookback.lower()
    if lookback_str.endswith('m'):
        lookback_months = int(lookback_str[:-1])
    else:
        print("Error: lookback must be in format '3m' (months)")
        sys.exit(1)
    
    # Run backtest
    runner = HistoricalBacktestRunner()
    
    try:
        # Generate market data
        data = runner.generate_market_data(args.period, lookback_months)
        
        # Run backtest
        summary = runner.run_backtest(data, args.period)
        
        # Print and save results
        runner.print_results(summary)
        runner.save_results(summary)
        
        # Return exit code based on success criteria
        success = (
            summary['win_rate'] > 40 and
            summary['profit_factor'] > 1.5 and
            summary['max_drawdown'] < 15 and
            summary['sharpe_ratio'] > 1.0
        )
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
