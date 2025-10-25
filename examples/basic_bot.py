"""
Example: Basic Trading Bot Usage

This example demonstrates how to set up and run the Yun Min trading bot
in dry-run mode for safe testing.
"""

from yunmin.core.config import YunMinConfig, ExchangeConfig, TradingConfig, RiskConfig, StrategyConfig
from yunmin.bot import YunMinBot
from loguru import logger
import sys


def main():
    """Run a simple example of the trading bot."""
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    print("=" * 60)
    print("Yun Min Trading Bot - Basic Example")
    print("=" * 60)
    
    # Create configuration programmatically
    config = YunMinConfig(
        exchange=ExchangeConfig(
            name="binance",
            testnet=True,
            # No API keys needed for dry-run mode
        ),
        trading=TradingConfig(
            mode="dry_run",  # Safe mode - no real orders
            symbol="BTC/USDT",
            timeframe="5m",
            initial_capital=10000.0
        ),
        risk=RiskConfig(
            max_position_size=0.1,  # 10% per position
            max_leverage=2.0,
            max_daily_drawdown=0.05,  # 5% max daily loss
            stop_loss_pct=0.02,
            take_profit_pct=0.03,
            enable_circuit_breaker=True
        ),
        strategy=StrategyConfig(
            name="ema_crossover",
            fast_ema=9,
            slow_ema=21,
            rsi_period=14,
            rsi_overbought=70.0,
            rsi_oversold=30.0
        )
    )
    
    # Create bot instance
    bot = YunMinBot(config)
    
    print("\n📊 Configuration:")
    print(f"  - Mode: {config.trading.mode}")
    print(f"  - Symbol: {config.trading.symbol}")
    print(f"  - Timeframe: {config.trading.timeframe}")
    print(f"  - Initial Capital: ${config.trading.initial_capital:,.2f}")
    print(f"  - Max Position Size: {config.risk.max_position_size * 100}%")
    print(f"  - Stop Loss: {config.risk.stop_loss_pct * 100}%")
    print(f"  - Take Profit: {config.risk.take_profit_pct * 100}%")
    
    print("\n🤖 Running bot for 3 iterations (dry-run mode)...")
    print("   Note: No exchange connection, using simulated data\n")
    
    # Run for 3 iterations with 5 second intervals
    try:
        bot.run(iterations=3, interval=5)
    except KeyboardInterrupt:
        print("\n\n⏹️  Bot stopped by user")
    
    print("\n✅ Example completed successfully!")
    print("\nNext steps:")
    print("  1. Review the logs to understand bot behavior")
    print("  2. Configure exchange API keys in .env file")
    print("  3. Test with real market data in dry-run mode")
    print("  4. Progress to paper trading when confident")
    print("  5. Only use live mode after extensive testing!\n")


if __name__ == "__main__":
    main()
