#!/usr/bin/env python3
"""
YunMin V3 Testnet Deployment Script

Safe deployment with:
- Real-time monitoring
- Emergency shutdown triggers
- Performance logging
- Trade history tracking
- Auto-reconnect on failures

Usage:
    python run_testnet.py --duration 48  # Run for 48 hours
    python run_testnet.py --dry-run      # Test mode (no real orders)
"""

import os
import sys
import argparse
import signal
import time
from pathlib import Path
from datetime import datetime, UTC, timedelta
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.risk.manager import RiskManager
from yunmin.core.config import RiskConfig
from yunmin.core.data_contracts import Order, OrderSide, OrderType


class TestnetMonitor:
    """Real-time monitoring and safety checks."""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.start_time = datetime.now(UTC)
        self.trades = []
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
        self.emergency_stop = False
        
        # Safety thresholds
        self.MAX_DRAWDOWN_PCT = 10.0  # Emergency stop at 10% loss
        self.MAX_CONSECUTIVE_LOSSES = 5
        self.consecutive_losses = 0
        
    def record_trade(self, trade_result: dict):
        """Record trade and update metrics."""
        self.trades.append({
            'timestamp': datetime.now(UTC),
            'symbol': trade_result['symbol'],
            'side': trade_result['side'],
            'pnl': trade_result.get('pnl', 0),
            'price': trade_result.get('price', 0)
        })
        
        # Update capital
        pnl = trade_result.get('pnl', 0)
        self.current_capital += pnl
        
        # Track peak and drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
            self.consecutive_losses = 0
        
        current_drawdown = ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # Track consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Check emergency conditions
        if current_drawdown > self.MAX_DRAWDOWN_PCT:
            logger.critical(f"🚨 EMERGENCY STOP: Drawdown {current_drawdown:.2f}% > {self.MAX_DRAWDOWN_PCT}%")
            self.emergency_stop = True
        
        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            logger.critical(f"🚨 EMERGENCY STOP: {self.consecutive_losses} consecutive losses")
            self.emergency_stop = True
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        runtime = (datetime.now(UTC) - self.start_time).total_seconds() / 3600
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        return {
            'runtime_hours': runtime,
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades) * 100) if self.trades else 0,
            'total_pnl': self.current_capital - self.initial_capital,
            'return_pct': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100,
            'current_capital': self.current_capital,
            'max_drawdown': self.max_drawdown,
            'consecutive_losses': self.consecutive_losses
        }
    
    def print_status(self):
        """Print current status."""
        stats = self.get_stats()
        
        logger.info("=" * 60)
        logger.info(f"⏱  Runtime: {stats['runtime_hours']:.1f}h")
        logger.info(f"📊 Trades: {stats['total_trades']} ({stats['winning_trades']}W / {stats['losing_trades']}L)")
        logger.info(f"📈 Win Rate: {stats['win_rate']:.1f}%")
        logger.info(f"💰 P&L: ${stats['total_pnl']:,.2f} ({stats['return_pct']:+.2f}%)")
        logger.info(f"💵 Capital: ${stats['current_capital']:,.2f}")
        logger.info(f"📉 Max DD: {stats['max_drawdown']:.2f}%")
        logger.info(f"🔁 Consecutive Losses: {stats['consecutive_losses']}")
        logger.info("=" * 60)


class TestnetBot:
    """Main testnet trading bot."""
    
    def __init__(
        self,
        connector: BinanceConnector,
        strategy: EMACrossoverStrategy,
        risk_manager: RiskManager,
        symbol: str,
        initial_capital: float,
        dry_run: bool = False
    ):
        self.connector = connector
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.symbol = symbol
        self.dry_run = dry_run
        
        self.monitor = TestnetMonitor(initial_capital)
        self.running = False
        self.last_check_time = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.warning(f"\n⚠️  Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    def start(self, duration_hours: Optional[float] = None):
        """Start the bot."""
        logger.info("=" * 60)
        logger.info("🚀 YUNMIN V3 TESTNET DEPLOYMENT STARTING")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Initial Capital: ${self.monitor.initial_capital:,.2f}")
        logger.info(f"Dry Run: {self.dry_run}")
        logger.info(f"Duration: {duration_hours}h" if duration_hours else "Duration: Indefinite")
        logger.info("=" * 60 + "\n")
        
        if self.dry_run:
            logger.warning("⚠️  DRY RUN MODE - No real orders will be placed\n")
        
        end_time = None
        if duration_hours:
            end_time = datetime.now(UTC) + timedelta(hours=duration_hours)
            logger.info(f"Will run until: {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        
        self.running = True
        check_interval = 60  # Check every 60 seconds
        status_interval = 300  # Print status every 5 minutes
        last_status_print = time.time()
        
        try:
            while self.running:
                # Check if duration expired
                if end_time and datetime.now(UTC) >= end_time:
                    logger.info("⏰ Duration completed, shutting down...")
                    break
                
                # Check emergency stop
                if self.monitor.emergency_stop:
                    logger.critical("🚨 EMERGENCY STOP TRIGGERED!")
                    break
                
                # Run trading logic
                self._trading_cycle()
                
                # Print status periodically
                if time.time() - last_status_print > status_interval:
                    self.monitor.print_status()
                    last_status_print = time.time()
                
                # Sleep before next check
                time.sleep(check_interval)
        
        except Exception as e:
            logger.exception(f"💥 Critical error: {e}")
        
        finally:
            self._shutdown()
    
    def _trading_cycle(self):
        """Single trading cycle."""
        try:
            # Fetch current market data
            # Note: In production, use WebSocket or REST API to get real candles
            # For now, using connector to check connectivity
            self.connector.ping()
            
            # TODO: Implement real market data fetching
            # data = self.connector.get_klines(self.symbol, interval='1m', limit=100)
            
            # Generate signal
            # signal = self.strategy.generate_signal(data)
            
            # For now, just log that we're alive
            if not self.last_check_time or (datetime.now(UTC) - self.last_check_time).seconds > 300:
                logger.info(f"✓ Bot alive - monitoring {self.symbol}")
                self.last_check_time = datetime.now(UTC)
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            time.sleep(10)  # Wait before retry
    
    def _shutdown(self):
        """Clean shutdown."""
        logger.info("\n" + "=" * 60)
        logger.info("🛑 SHUTTING DOWN")
        logger.info("=" * 60)
        
        # Cancel all open orders
        try:
            if not self.dry_run:
                open_orders = self.connector.get_open_orders(self.symbol)
                for order in open_orders:
                    logger.info(f"Cancelling order: {order['orderId']}")
                    self.connector.cancel_order(self.symbol, order['orderId'])
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
        
        # Final stats
        self.monitor.print_status()
        
        # Save trade log
        self._save_trade_log()
        
        logger.success("\n✅ Shutdown complete\n")
    
    def _save_trade_log(self):
        """Save trade history to file."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        log_file = project_root / f"testnet_trades_{timestamp}.json"
        
        import json
        
        log_data = {
            'session': {
                'start_time': self.monitor.start_time.isoformat(),
                'end_time': datetime.now(UTC).isoformat(),
                'initial_capital': self.monitor.initial_capital,
                'final_capital': self.monitor.current_capital,
            },
            'stats': self.monitor.get_stats(),
            'trades': self.monitor.trades
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        logger.info(f"💾 Trade log saved: {log_file}")


def main():
    parser = argparse.ArgumentParser(description="YunMin V3 Testnet Deployment")
    parser.add_argument('--duration', type=float, help='Run duration in hours (default: indefinite)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no real orders)')
    parser.add_argument('--symbol', default='BTCUSDT', help='Trading symbol (default: BTCUSDT)')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital (default: 10000)')
    
    args = parser.parse_args()
    
    # Load environment
    env_file = project_root / '.env.testnet'
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"✅ Loaded environment from {env_file}")
    else:
        logger.warning(f"⚠️  No .env.testnet file found")
    
    # Get credentials
    api_key = os.getenv('BINANCE_TESTNET_API_KEY')
    api_secret = os.getenv('BINANCE_TESTNET_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("❌ BINANCE_TESTNET_API_KEY/SECRET not set!")
        logger.info("Create .env.testnet file with your credentials")
        logger.info("Get testnet keys at: https://testnet.binance.vision/")
        return 1
    
    # Initialize components
    logger.info("Initializing components...")
    
    connector = BinanceConnector(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True
    )
    
    strategy = EMACrossoverStrategy(
        fast_period=9,
        slow_period=21,
        rsi_period=14,
        rsi_overbought=70,
        rsi_oversold=30
    )
    
    risk_config = RiskConfig(
        max_position_size=0.10,
        max_leverage=1.0,
        max_daily_drawdown=0.05
    )
    risk_manager = RiskManager(risk_config)
    
    # Create and start bot
    bot = TestnetBot(
        connector=connector,
        strategy=strategy,
        risk_manager=risk_manager,
        symbol=args.symbol,
        initial_capital=args.capital,
        dry_run=args.dry_run
    )
    
    bot.start(duration_hours=args.duration)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
