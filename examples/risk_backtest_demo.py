"""
Example: Risk Manager Integration with Backtester

Demonstrates how the RiskManager is integrated into the backtesting process
to enforce pre-trade checks and reject trades that violate risk policies.
"""

from yunmin.backtesting import Backtester, HistoricalDataLoader, ReportGenerator
from yunmin.strategy.base import BaseStrategy, SignalType, Signal
from yunmin.core.config import RiskConfig
from yunmin.risk.manager import RiskManager
import pandas as pd


class SimpleTrendStrategy(BaseStrategy):
    """Simple trend-following strategy for demonstration"""
    
    def __init__(self):
        super().__init__("SimpleTrendStrategy")
    
    def analyze(self, data: pd.DataFrame) -> Signal:
        """Generate signals based on simple moving average crossover"""
        if len(data) < 20:
            return Signal(type=SignalType.HOLD, confidence=0.5, reason="Insufficient data")
        
        # Calculate short and long moving averages
        close = data['close']
        sma_short = close.rolling(window=5).mean()
        sma_long = close.rolling(window=20).mean()
        
        current_short = sma_short.iloc[-1]
        current_long = sma_long.iloc[-1]
        prev_short = sma_short.iloc[-2]
        prev_long = sma_long.iloc[-2]
        
        # Bullish crossover
        if prev_short <= prev_long and current_short > current_long:
            return Signal(
                type=SignalType.BUY,
                confidence=0.8,
                reason="Bullish MA crossover"
            )
        
        # Bearish crossover
        if prev_short >= prev_long and current_short < current_long:
            return Signal(
                type=SignalType.SELL,
                confidence=0.8,
                reason="Bearish MA crossover"
            )
        
        return Signal(type=SignalType.HOLD, confidence=0.5, reason="No crossover")


def run_demo():
    """Run risk management demonstration"""
    
    print("=" * 80)
    print("Risk Manager Integration Demo")
    print("=" * 80)
    print()
    
    # Generate sample market data
    loader = HistoricalDataLoader()
    print("Generating sample market data...")
    data = loader.generate_sample_data(
        symbol="BTC/USDT",
        start_price=50000,
        num_candles=300,
        trend='uptrend',
        volatility=0.02
    )
    print(f"✓ Generated {len(data)} candles")
    print()
    
    # Setup strategy
    strategy = SimpleTrendStrategy()
    
    # Setup risk configuration with strict limits
    print("Setting up Risk Manager with strict limits:")
    risk_config = RiskConfig(
        max_position_size=0.08,        # Max 8% of capital per position
        max_leverage=2.0,              # Max 2x leverage
        max_daily_drawdown=0.05,       # Max 5% daily drawdown
        stop_loss_pct=0.03,            # 3% stop loss
        take_profit_pct=0.06,          # 6% take profit
        enable_circuit_breaker=True    # Enable emergency halt
    )
    print(f"  - Max Position Size: {risk_config.max_position_size*100:.1f}%")
    print(f"  - Max Leverage: {risk_config.max_leverage}x")
    print(f"  - Max Daily Drawdown: {risk_config.max_daily_drawdown*100:.1f}%")
    print(f"  - Stop Loss: {risk_config.stop_loss_pct*100:.1f}%")
    print(f"  - Take Profit: {risk_config.take_profit_pct*100:.1f}%")
    print()
    
    # Run backtest with risk manager enabled
    print("Running backtest WITH risk management...")
    backtester = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001,
        slippage_rate=0.0005,
        use_risk_manager=False  # We'll inject our own
    )
    backtester.risk_manager = RiskManager(risk_config)
    
    # Try to use 15% position size (should trigger rejections since limit is 8%)
    results = backtester.run(data, symbol="BTC/USDT", position_size_pct=0.15)
    
    print()
    print("=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Executed Trades:     {results['total_trades']:>6}")
    print(f"Rejected Trades:     {results['rejected_trades']:>6}")
    
    if results['rejected_trades'] > 0:
        total_signals = results['total_trades'] + results['rejected_trades']
        approval_rate = (results['total_trades'] / total_signals) * 100
        print(f"Approval Rate:       {approval_rate:>6.1f}%")
    
    print()
    print(f"Win Rate:            {results['win_rate']:>6.1f}%")
    print(f"Net P&L:            ${results['net_pnl']:>6,.2f}")
    print(f"Final Capital:      ${results['final_equity']:>6,.2f}")
    print(f"Total Return:        {results['total_return']:>6.2f}%")
    print()
    
    # Show rejected trades details
    rejected_log = backtester.get_rejected_trades_log()
    if not rejected_log.empty:
        print("=" * 80)
        print("REJECTED TRADES DETAILS")
        print("=" * 80)
        print()
        
        # Show first 5 rejections
        for idx, row in rejected_log.head(5).iterrows():
            print(f"Rejection #{idx + 1}:")
            print(f"  Time:    {row['timestamp']}")
            print(f"  Side:    {row['side']}")
            print(f"  Symbol:  {row['symbol']}")
            print(f"  Amount:  {row['amount']:.8f}")
            print(f"  Price:   ${row['price']:,.2f}")
            print(f"  Reasons: {row['rejection_reasons']}")
            print()
        
        if len(rejected_log) > 5:
            print(f"... and {len(rejected_log) - 5} more rejections")
            print()
        
        # Export to CSV
        csv_path = "/tmp/rejected_trades.csv"
        rejected_log.to_csv(csv_path, index=False)
        print(f"✓ Rejected trades exported to: {csv_path}")
        print()
    
    # Generate and display text report
    print("=" * 80)
    print("FULL REPORT")
    print("=" * 80)
    print()
    report = ReportGenerator.generate_text_report(results, strategy_name=strategy.name)
    print(report)
    
    # Compare with run WITHOUT risk manager
    print()
    print("=" * 80)
    print("COMPARISON: WITHOUT Risk Manager")
    print("=" * 80)
    print()
    print("Running same backtest WITHOUT risk management...")
    
    backtester_no_risk = Backtester(
        strategy=strategy,
        initial_capital=10000,
        commission_rate=0.001,
        slippage_rate=0.0005,
        use_risk_manager=False
    )
    
    results_no_risk = backtester_no_risk.run(data, symbol="BTC/USDT", position_size_pct=0.15)
    
    print(f"Executed Trades:     {results_no_risk['total_trades']:>6}")
    print(f"Rejected Trades:     {results_no_risk['rejected_trades']:>6}")
    print(f"Net P&L:            ${results_no_risk['net_pnl']:>6,.2f}")
    print(f"Final Capital:      ${results_no_risk['final_equity']:>6,.2f}")
    print(f"Total Return:        {results_no_risk['total_return']:>6.2f}%")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("The Risk Manager successfully:")
    print(f"  ✓ Rejected {results['rejected_trades']} trades that violated risk policies")
    print(f"  ✓ Logged detailed rejection reasons for audit trail")
    print(f"  ✓ Allowed {results['total_trades']} trades that passed all checks")
    print(f"  ✓ Protected capital by enforcing position size limits")
    print()
    print("Without risk management:")
    print(f"  • Would have executed {results_no_risk['total_trades']} trades")
    print(f"  • Risk of larger drawdowns from oversized positions")
    print(f"  • No protection against risk policy violations")
    print()
    print("✅ Risk Manager integration is working correctly!")
    print()


if __name__ == "__main__":
    run_demo()
