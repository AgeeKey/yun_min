"""
Yun Min CLI - Command Line Interface

Entry point for running the trading bot and emergency commands.
"""

import sys
import argparse
from pathlib import Path
from loguru import logger

from yunmin.core.config import load_config
from yunmin.bot import YunMinBot
from yunmin.core.emergency import EmergencySafetyProtocol


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


def cmd_dashboard(args):
    """Run the live dashboard."""
    from yunmin.ui.live_dashboard import create_demo_dashboard
    
    logger.info("Starting YunMin Live Dashboard...")
    
    # TODO: When bot instance is available, pass it to dashboard
    # For now, use demo dashboard
    dashboard = create_demo_dashboard()
    
    try:
        dashboard.run(update_interval=args.update_interval)
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")


def cmd_setup_wizard(args):
    """Run the setup wizard."""
    from yunmin.cli_wizard import run_wizard
    
    logger.info("Starting Configuration Wizard...")
    config_path = run_wizard()
    
    if config_path:
        logger.info(f"Configuration saved to {config_path}")


def cmd_run(args):
    """Run the trading bot."""
    logger.info("=" * 60)
    logger.info("Yun Min Trading Agent v0.1.0")
    logger.info("=" * 60)
    
    # Load configuration
    config_path = args.config
    if not Path(config_path).exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("Yun Min Trading Agent v0.1.0")
        logger.info("=" * 60)
        
        # Load configuration
        config_path = getattr(args, 'config', 'config/default.yaml')
        if not Path(config_path).exists():
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
            
        config = load_config(config_path)
        
        # Override mode if specified
        if hasattr(args, 'mode') and args.mode:
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
            bot.run(
                iterations=getattr(args, 'iterations', None),
                interval=getattr(args, 'interval', 60)
            )
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)
        finally:
            logger.info("Yun Min agent shutdown complete")
    else:
        parser.print_help()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Yun Min - AI-powered cryptocurrency trading agent"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command (default behavior)
    run_parser = subparsers.add_parser('run', help='Run the trading bot')
    run_parser.add_argument(
        '--config',
        type=str,
        default='config/default.yaml',
        help='Path to configuration file'
    )
    run_parser.add_argument(
        '--mode',
        type=str,
        choices=['dry_run', 'paper', 'live'],
        help='Trading mode (overrides config)'
    )
    run_parser.add_argument(
        '--iterations',
        type=int,
        help='Number of iterations to run (default: infinite)'
    )
    run_parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Seconds between iterations (default: 60)'
    )
    run_parser.add_argument(
        '--log-level',
        type=str,
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    run_parser.set_defaults(func=cmd_run)
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Launch live monitoring dashboard')
    dashboard_parser.add_argument(
        '--update-interval',
        type=float,
        default=1.0,
        help='Dashboard update interval in seconds (default: 1.0)'
    )
    dashboard_parser.set_defaults(func=cmd_dashboard)
    
    # Setup wizard command
    wizard_parser = subparsers.add_parser('setup-wizard', help='Interactive configuration wizard')
    wizard_parser.set_defaults(func=cmd_setup_wizard)
    
    args = parser.parse_args()
    
    # If no command specified, default to run with old argument style for backward compatibility
    if not args.command:
        # Add legacy arguments for backward compatibility
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
        args.func = cmd_run
    
    # Setup logging
    log_level = getattr(args, 'log_level', 'INFO')
    setup_logging(log_level)
    
    # Execute command
    args.func(args)


if __name__ == '__main__':
    main()
