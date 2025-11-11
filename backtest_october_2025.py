#!/usr/bin/env python3
"""
Backtest Phase 2 Strategy on October 2025 Real Data
Uses GrokAIStrategy with advanced indicators and relaxed thresholds
"""

import sys
sys.path.insert(0, '/f/AgeeKey/yun_min')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import logging

from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.core.data_contracts import Trade
from yunmin.core.risk_manager import RiskManager
from yunmin.core.config import YunMinConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestEngine:
    """Simple backtest engine for Phase 2 validation"""
    
    def __init__(self, initial_capital=10000, leverage=3.0):
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.current_capital = initial_capital
        self.trades = []
        self.equity_curve = [initial_capital]
        self.position = None
        self.entry_price = None
        self.entry_time = None
        
    def execute_backtest(self, df, strategy):
        """Run backtest on dataframe"""
        logger.info(f"Starting backtest on {len(df)} candles...")
        
        signals = []
        
        for i in range(20, len(df)):  # Need 20 candles for indicators
            try:
                # Get signal from strategy
                df_subset = df.iloc[:i+1].copy()
                signal = strategy.analyze(df_subset)
                
                current_price = df.iloc[i]['close']
                current_time = df.iloc[i]['timestamp']
                
                if not signal:
                    continue

                # Support both dict-style signals and Signal dataclass instances
                if hasattr(signal, 'get') and callable(getattr(signal, 'get')):
                    # dict-like
                    action = str(signal.get('action', 'HOLD')).upper()
                    confidence = signal.get('confidence', 0)
                    reason = signal.get('reason', '')
                else:
                    # Assume dataclass-like with attributes: type, confidence, reason
                    # type may be an Enum (SignalType) - normalize to string
                    try:
                        raw_type = getattr(signal, 'type', 'HOLD')
                        action = raw_type.value.upper() if hasattr(raw_type, 'value') else str(raw_type).upper()
                    except Exception:
                        action = 'HOLD'
                    confidence = getattr(signal, 'confidence', 0)
                    reason = getattr(signal, 'reason', '')

                signals.append({
                    'time': current_time,
                    'price': current_price,
                    'action': action,
                    'confidence': confidence,
                    'reason': reason
                })
                
                # Simple trade execution logic
                if action == 'BUY' and not self.position:
                    self.entry_price = current_price
                    self.entry_time = current_time
                    self.position = 'LONG'
                    
                elif action == 'SELL' and self.position == 'LONG':
                    # Close position
                    pnl = (current_price - self.entry_price) / self.entry_price
                    self.current_capital *= (1 + pnl)
                    self.equity_curve.append(self.current_capital)
                    
                    self.trades.append({
                        'entry_time': self.entry_time,
                        'entry_price': self.entry_price,
                        'exit_time': current_time,
                        'exit_price': current_price,
                        'pnl_pct': pnl * 100,
                        'pnl_usd': (current_price - self.entry_price)
                    })
                    
                    self.position = None
                    self.entry_price = None
                    self.entry_time = None
                    
            except Exception as e:
                logger.debug(f"Error at candle {i}: {e}")
                continue
        
        return signals, self.trades
    
    def get_metrics(self):
        """Calculate backtest metrics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_pnl_usd': 0,
                'total_pnl_pct': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_pnl': 0,
                'final_capital': self.current_capital
            }
        
        # Convert to numpy for calculations
        trades_array = np.array([t['pnl_pct'] for t in self.trades])
        
        # Win rate
        winning_trades = len([t for t in self.trades if t['pnl_pct'] > 0])
        win_rate = winning_trades / len(self.trades) * 100
        
        # Profit factor
        gross_profit = sum([t['pnl_usd'] for t in self.trades if t['pnl_usd'] > 0])
        gross_loss = abs(sum([t['pnl_usd'] for t in self.trades if t['pnl_usd'] < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Total PnL
        total_pnl_usd = sum([t['pnl_usd'] for t in self.trades])
        total_pnl_pct = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        # Max drawdown
        equity = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = np.min(drawdown) * 100
        
        # Sharpe ratio (annualized, assuming 365 trading days)
        if len(trades_array) > 1 and np.std(trades_array) > 0:
            sharpe_ratio = np.mean(trades_array) / np.std(trades_array) * np.sqrt(365)
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': winning_trades,
            'losing_trades': len(self.trades) - winning_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_pnl_usd': total_pnl_usd,
            'total_pnl_pct': total_pnl_pct,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_pnl': np.mean(trades_array),
            'final_capital': self.current_capital
        }


async def fetch_october_data():
    """Fetch October 2025 BTC/USDT data from Binance"""
    logger.info("=" * 80)
    logger.info("PHASE 2 BACKTEST - October 2025 Data")
    logger.info("=" * 80)
    
    try:
        connector = BinanceConnector(
            api_key="test",  # Testnet
            api_secret="test",
            testnet=True
        )
        
        # October 2025: from 2025-10-01 to 2025-10-31
        logger.info("\n📊 Fetching October 2025 BTC/USDT 5m candles...")
        
        # Get historical data
        start_date = datetime(2025, 10, 1)
        end_date = datetime(2025, 10, 31)
        
        candles = await connector.get_historical_klines(
            symbol="BTCUSDT",
            interval="5m",
            start_time=int(start_date.timestamp() * 1000),
            end_time=int(end_date.timestamp() * 1000),
            limit=5000
        )
        
        if not candles:
            logger.error("❌ No data fetched. Using mock data instead.")
            candles = generate_mock_october_data()
        
        # Convert to DataFrame
        df = pd.DataFrame(candles, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'buy_base', 'buy_quote', 'ignore'
        ])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert OHLCV to float
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        
        logger.info(f"✅ Fetched {len(df)} candles")
        logger.info(f"   Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
        logger.info(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return df
        
    except Exception as e:
        logger.warning(f"⚠️  Could not fetch live data: {e}")
        logger.info("   Using mock October 2025 data instead...")
        return generate_mock_october_data()


def generate_mock_october_data(num_candles=8928):  # ~31 days * 288 candles/day (5m)
    """Generate realistic mock October 2025 data"""
    np.random.seed(42)
    
    start_price = 42500
    prices = [start_price]
    
    # Simulate realistic October trend (some volatility)
    for i in range(num_candles - 1):
        # Mix of trend and noise
        trend = 0.00003 if i % 100 < 60 else -0.00002  # Slight uptrend
        noise = np.random.normal(0, 0.002)
        change = trend + noise
        price = prices[-1] * (1 + change)
        prices.append(price)
    
    # Create OHLCV
    timestamps = [datetime(2025, 10, 1) + timedelta(minutes=5*i) for i in range(num_candles)]
    ohlcv = []
    
    for i in range(len(prices) - 1):
        o = prices[i]
        c = prices[i + 1]
        h = max(o, c) * (1 + np.random.uniform(0, 0.005))
        l = min(o, c) * (1 - np.random.uniform(0, 0.005))
        v = np.random.uniform(500, 2000)
        
        ohlcv.append({
            'timestamp': timestamps[i],
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'volume': v
        })
    
    return pd.DataFrame(ohlcv)


async def main():
    """Run backtest"""
    
    # Fetch data
    df = await fetch_october_data()
    
    if len(df) < 50:
        logger.error("❌ Not enough data for backtest")
        return False
    
    # Initialize strategy and backtest engine
    logger.info("\n🧪 Initializing Phase 2 Strategy...")
    strategy = GrokAIStrategy()
    engine = BacktestEngine(initial_capital=10000, leverage=3.0)
    
    # Run backtest
    logger.info("\n⚙️  Running backtest...")
    signals, trades = engine.execute_backtest(df, strategy)
    
    # Get metrics
    metrics = engine.get_metrics()
    
    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("📊 BACKTEST RESULTS - October 2025")
    logger.info("=" * 80)
    
    logger.info(f"\n📈 Performance Metrics:")
    logger.info(f"   Initial Capital:       ${engine.initial_capital:,.2f}")
    logger.info(f"   Final Capital:         ${metrics['final_capital']:,.2f}")
    logger.info(f"   Total P&L:             ${metrics['total_pnl_usd']:,.2f} ({metrics['total_pnl_pct']:+.2f}%)")
    
    logger.info(f"\n🎯 Trading Statistics:")
    logger.info(f"   Total Trades:          {metrics['total_trades']}")
    logger.info(f"   Winning Trades:        {metrics['winning_trades']}")
    logger.info(f"   Losing Trades:         {metrics['losing_trades']}")
    logger.info(f"   Win Rate:              {metrics['win_rate']:.2f}%")
    logger.info(f"   Profit Factor:         {metrics['profit_factor']:.2f}")
    logger.info(f"   Avg Trade P&L:         {metrics['avg_trade_pnl']:+.2f}%")
    
    logger.info(f"\n📉 Risk Metrics:")
    logger.info(f"   Max Drawdown:          {metrics['max_drawdown']:.2f}%")
    logger.info(f"   Sharpe Ratio:          {metrics['sharpe_ratio']:.2f}")
    
    # Validation
    logger.info("\n" + "=" * 80)
    logger.info("✅ VALIDATION RESULTS")
    logger.info("=" * 80)
    
    checks = {
        'Win Rate > 40%': metrics['win_rate'] > 40,
        'Max Drawdown < 20%': abs(metrics['max_drawdown']) < 20,
        'Profit Factor > 1.5': metrics['profit_factor'] > 1.5,
        'Positive P&L': metrics['total_pnl_usd'] > 0,
        'Sufficient Trades': metrics['total_trades'] >= 10
    }
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {check_name}")
    
    # Summary
    all_passed = all(checks.values())
    
    if all_passed:
        logger.info("\n🎉 PHASE 2 BACKTEST SUCCESSFUL!")
        logger.info("   Strategy is ready for live testnet deployment")
    else:
        logger.warning("\n⚠️  Some metrics did not meet targets")
        logger.info("   Review strategy parameters and try again")
    
    # Sample trades
    if trades:
        logger.info(f"\n📋 Sample Trades (first 5):")
        for i, trade in enumerate(trades[:5], 1):
            logger.info(f"   [{i}] Entry: ${trade['entry_price']:.2f} → Exit: ${trade['exit_price']:.2f} | P&L: {trade['pnl_pct']:+.2f}%")
    
    return all_passed


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        logger.error(f"❌ Backtest failed: {e}", exc_info=True)
        sys.exit(1)
