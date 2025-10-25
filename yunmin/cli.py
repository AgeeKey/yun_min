"""
Yun Min CLI - Command Line Interface

Entry point for running the trading bot.
"""

import sys
import argparse
from pathlib import Path
from loguru import logger

from yunmin.core.config import load_config
from yunmin.bot import YunMinBot


def setup_logging(log_level: str = "INFO"):
    """Configure logging."""
    logger.remove()  # Remove default handler
    
    # Console output
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level
    )
    
    # File output
    logger.add(
        "logs/yunmin_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Yun Min - AI-powered cryptocurrency trading agent"
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/default.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['dry_run', 'paper', 'live'],
        help='Trading mode (overrides config)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        help='Number of iterations to run (default: infinite)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Seconds between iterations (default: 60)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger.info("=" * 60)
    logger.info("Yun Min Trading Agent v0.1.0")
    logger.info("=" * 60)
    
    # Load configuration
    config_path = args.config
    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
        
    config = load_config(config_path)
    
    # Override mode if specified
    if args.mode:
        config.trading.mode = args.mode
        
    # Create and run bot
    bot = YunMinBot(config)
    
    logger.info(f"Starting bot in {config.trading.mode} mode...")
    logger.info(f"Trading pair: {config.trading.symbol}")
    logger.info(f"Timeframe: {config.trading.timeframe}")
    
    if config.trading.mode == 'live':
        logger.critical("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
        response = input("Type 'YES' to confirm live trading: ")
        if response != 'YES':
            logger.info("Live trading cancelled")
            sys.exit(0)
    
    try:
        bot.run(iterations=args.iterations, interval=args.interval)
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("Yun Min agent shutdown complete")


if __name__ == '__main__':
    main()
