"""
Multi-Currency Trading CLI

Launch multiple bots for different cryptocurrencies.
"""

import argparse
from loguru import logger

from yunmin.core.config import load_config
from yunmin.multi_bot import MultiCurrencyBot


def main():
    """Main entry point for multi-currency trading."""
    parser = argparse.ArgumentParser(description="Yun Min Multi-Currency Trading Agent")
    
    parser.add_argument(
        '--symbols',
        nargs='+',
        default=['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
        help='Trading symbols (default: BTC/USDT ETH/USDT BNB/USDT)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/default.yaml',
        help='Configuration file path'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Print header
    logger.info("=" * 60)
    logger.info("🌐 Yun Min Multi-Currency Trading Agent")
    logger.info("=" * 60)
    logger.info(f"Symbols: {', '.join(args.symbols)}")
    logger.info(f"Mode: {config.trading.mode}")
    logger.info(f"Interval: {args.interval}s")
    logger.info(f"Total Capital: ${config.trading.initial_capital:.2f}")
    logger.info(f"Capital per symbol: ${config.trading.initial_capital / len(args.symbols):.2f}")
    logger.info("=" * 60)
    
    # Create and start multi-bot
    multi_bot = MultiCurrencyBot(config, args.symbols)
    multi_bot.start(interval=args.interval)


if __name__ == "__main__":
    main()
