"""
Backtest Dual-Brain Trader on real 2025 data

Tests Strategic + Tactical AI system on historical data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from loguru import logger
from datetime import datetime

from yunmin.strategy.dual_brain_trader import DualBrainTrader
from yunmin.strategy.base import SignalType


class SimpleBacktester:
    """Simple backtest engine for Dual-Brain."""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        position_size: float = 0.1,  # 10% per trade
        fee_rate: float = 0.0004      # 0.04% Binance futures
    ):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.fee_rate = fee_rate
        
        # State
        self.capital = initial_capital
        self.position = 0.0  # BTC amount
        self.entry_price = 0.0
        self.trades = []
        self.equity_curve = []
        
    def execute_signal(self, signal, price: float, timestamp):
        """Execute trading signal."""
        
        if signal.type == SignalType.HOLD:
            # Just track equity
            equity = self.capital
            if self.position != 0:
                equity += self.position * price
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': equity,
                'price': price,
                'action': 'HOLD'
            })
            return
        
        # Calculate trade size
        trade_capital = self.capital * self.position_size
        
        if signal.type == SignalType.BUY and self.position == 0:
            # Open long
            amount = trade_capital / price
            fee = trade_capital * self.fee_rate
            
            self.position = amount
            self.entry_price = price
            self.capital -= (trade_capital + fee)
            
            self.trades.append({
                'timestamp': timestamp,
                'type': 'BUY',
                'price': price,
                'amount': amount,
                'fee': fee,
                'reasoning': signal.reason
            })
            
            logger.info(f"🟢 BUY  | ${price:,.2f} | {amount:.4f} BTC | Fee: ${fee:.2f}")
            
        elif signal.type == SignalType.SELL and self.position > 0:
            # Close long
            sell_value = self.position * price
            fee = sell_value * self.fee_rate
            pnl = sell_value - (self.position * self.entry_price) - fee
            
            self.capital += sell_value - fee
            
            self.trades.append({
                'timestamp': timestamp,
                'type': 'SELL',
                'price': price,
                'amount': self.position,
                'fee': fee,
                'pnl': pnl,
                'reasoning': signal.reason
            })
            
            logger.info(f"🔴 SELL | ${price:,.2f} | {self.position:.4f} BTC | PnL: ${pnl:+,.2f}")
            
            self.position = 0.0
            self.entry_price = 0.0
        
        # Track equity
        equity = self.capital
        if self.position != 0:
            equity += self.position * price
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': equity,
            'price': price,
            'action': signal.type.value.upper()
        })
    
    def get_metrics(self):
        """Calculate backtest metrics."""
        # Filter only completed trades
        completed = [t for t in self.trades if 'pnl' in t]
        
        if not completed:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'roi': 0.0
            }
        
        # Calculate metrics
        wins = [t for t in completed if t['pnl'] > 0]
        losses = [t for t in completed if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in completed)
        win_rate = len(wins) / len(completed) if completed else 0.0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0.0
        
        # Max drawdown
        equity_series = pd.Series([e['equity'] for e in self.equity_curve])
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        # ROI
        final_equity = self.capital
        if self.position != 0:
            final_equity += self.position * self.equity_curve[-1]['price']
        roi = (final_equity / self.initial_capital - 1) * 100
        
        return {
            'total_trades': len(completed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate * 100,
            'total_pnl': total_pnl,
            'roi': roi,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_dd,
            'final_equity': final_equity
        }


def main():
    """Run backtest."""
    logger.info("=" * 100)
    logger.info("🧠🧠 DUAL-BRAIN BACKTEST - 2025 DATA")
    logger.info("=" * 100)
    
    # Load data
    data_file = Path("data/BTCUSDT_5m_2025.csv")
    if not data_file.exists():
        logger.error(f"❌ Data file not found: {data_file}")
        logger.info("   Run: python download_2025_data.py")
        return
    
    logger.info(f"📥 Loading data from {data_file}...")
    df = pd.read_csv(data_file, index_col='timestamp', parse_dates=True)
    logger.success(f"✅ Loaded {len(df):,} candles")
    logger.info(f"   Period: {df.index[0]} → {df.index[-1]}")
    
    # Initialize strategy
    logger.info("\n🧠 Initializing Dual-Brain Trader...")
    strategy = DualBrainTrader(
        strategic_model="o3-mini",       # Deep analysis
        tactical_model="gpt-5-mini",     # Fast decisions
        strategic_interval_minutes=60,   # Update strategy every hour
        enable_reasoning=True
    )
    logger.success("✅ Strategy ready!")
    
    # Initialize backtest engine
    backtest = SimpleBacktester(
        initial_capital=10000.0,
        position_size=0.1,  # 10% per trade
        fee_rate=0.0004     # Binance futures fee
    )
    
    logger.info("\n" + "=" * 100)
    logger.info("🎬 BACKTEST START")
    logger.info("=" * 100)
    logger.info(f"Capital: ${backtest.initial_capital:,.2f}")
    logger.info(f"Position size: {backtest.position_size * 100}%")
    logger.info(f"Fee rate: {backtest.fee_rate * 100}%")
    logger.info("=" * 100)
    
    # Run backtest (sample every 12 candles = 1 hour for speed)
    total_candles = len(df)
    step = 12  # Sample every hour
    
    for i in range(100, total_candles, step):  # Start from candle 100
        current_df = df.iloc[:i]
        current_price = df['close'].iloc[i]
        timestamp = df.index[i]
        
        # Get signal from strategy
        signal = strategy.analyze(current_df)
        
        # Execute
        backtest.execute_signal(signal, current_price, timestamp)
        
        # Progress
        if i % (step * 24) == 0:  # Every day
            progress = i / total_candles * 100
            logger.info(f"\n📊 Progress: {progress:.1f}% | {timestamp}")
    
    # Final metrics
    logger.info("\n" + "=" * 100)
    logger.info("📊 BACKTEST RESULTS")
    logger.info("=" * 100)
    
    metrics = backtest.get_metrics()
    
    logger.info(f"\n💰 P&L:")
    logger.info(f"   Initial capital: ${backtest.initial_capital:,.2f}")
    logger.info(f"   Final equity:    ${metrics['final_equity']:,.2f}")
    logger.info(f"   Total PnL:       ${metrics['total_pnl']:+,.2f}")
    logger.info(f"   ROI:             {metrics['roi']:+.2f}%")
    
    logger.info(f"\n📈 Trades:")
    logger.info(f"   Total:     {metrics['total_trades']}")
    logger.info(f"   Wins:      {metrics['wins']} ({metrics['win_rate']:.1f}%)")
    logger.info(f"   Losses:    {metrics['losses']}")
    logger.info(f"   Avg win:   ${metrics['avg_win']:+,.2f}")
    logger.info(f"   Avg loss:  ${metrics['avg_loss']:+,.2f}")
    
    logger.info(f"\n⚠️  Risk:")
    logger.info(f"   Max drawdown: {metrics['max_drawdown']:.2f}%")
    
    # Strategy stats
    stats = strategy.get_stats()
    logger.info(f"\n🧠 AI Stats:")
    logger.info(f"   Strategic updates: {stats['strategic_updates']}")
    logger.info(f"   Tactical decisions: {stats['tactical_decisions']}")
    
    logger.info("\n" + "=" * 100)
    
    if metrics['win_rate'] > 40 and metrics['roi'] > 0:
        logger.success("✅ BACKTEST PASSED! Strategy looks promising!")
    else:
        logger.warning("⚠️  BACKTEST FAILED. Strategy needs improvement.")
    
    logger.info("=" * 100)


if __name__ == "__main__":
    main()
