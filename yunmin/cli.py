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


def emergency_stop_command():
    """Handle emergency stop command."""
    setup_logging('INFO')
    
    logger.critical("🚨 EMERGENCY STOP COMMAND 🚨")
    response = input("Type 'EMERGENCY' to confirm emergency stop (this will close all positions): ")
    
    if response != 'EMERGENCY':
        logger.info("Emergency stop cancelled")
        return
    
    protocol = EmergencySafetyProtocol()
    success = protocol.emergency_stop(
        reason="Manual emergency stop via CLI",
        confirmed=True
    )
    
    if success:
        logger.info("Emergency stop activated. Bot will close all positions on next run.")
        logger.info("Run 'yunmin resume-trading' to resume normal operations.")
    else:
        logger.error("Failed to activate emergency stop")


def pause_trading_command():
    """Handle pause trading command."""
    setup_logging('INFO')
    
    logger.warning("⏸️  PAUSE TRADING COMMAND")
    logger.info("This will prevent new positions but keep existing ones.")
    response = input("Type 'PAUSE' to confirm: ")
    
    if response != 'PAUSE':
        logger.info("Pause cancelled")
        return
    
    protocol = EmergencySafetyProtocol()
    success = protocol.pause_trading(
        reason="Manual pause via CLI"
    )
    
    if success:
        logger.info("Trading paused. No new positions will be opened.")
        logger.info("Run 'yunmin resume-trading' to resume normal operations.")
    else:
        logger.error("Failed to pause trading")


def resume_trading_command():
    """Handle resume trading command."""
    setup_logging('INFO')
    
    logger.info("✅ RESUME TRADING COMMAND")
    
    protocol = EmergencySafetyProtocol()
    status = protocol.get_status_summary()
    
    logger.info(f"Current mode: {status['current_mode']}")
    
    if status['current_mode'] == 'normal':
        logger.info("Already in normal trading mode")
        return
    
    response = input("Type 'RESUME' to confirm resume trading: ")
    
    if response != 'RESUME':
        logger.info("Resume cancelled")
        return
    
    success = protocol.resume_trading(confirmed=True)
    
    if success:
        logger.info("Trading resumed. Bot will operate normally.")
    else:
        logger.error("Failed to resume trading")


def status_command():
    """Show current emergency protocol status."""
    setup_logging('INFO')
    
    protocol = EmergencySafetyProtocol()
    status = protocol.get_status_summary()
    
    logger.info("=" * 60)
    logger.info("Emergency Safety Protocol Status")
    logger.info("=" * 60)
    logger.info(f"Current Mode: {status['current_mode']}")
    logger.info(f"Trading Allowed: {status['trading_allowed']}")
    logger.info(f"New Positions Allowed: {status['new_positions_allowed']}")
    logger.info(f"Auto-trigger Enabled: {status['auto_trigger_enabled']}")
    logger.info(f"Total Events: {status['total_events']}")
    
    if status['recent_events']:
        logger.info("\nRecent Events:")
        for event in status['recent_events']:
            logger.info(f"  - {event['timestamp']}: {event['trigger']} -> {event['mode_after']}")
            logger.info(f"    Reason: {event['reason']}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Yun Min - AI-powered cryptocurrency trading agent",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command (default)
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
    
    # Emergency commands
    subparsers.add_parser('emergency-stop', help='Emergency stop - close all positions immediately')
    subparsers.add_parser('pause-trading', help='Pause trading - no new positions')
    subparsers.add_parser('resume-trading', help='Resume normal trading')
    subparsers.add_parser('status', help='Show emergency protocol status')
    
    args = parser.parse_args()
    
    # Handle emergency commands
    if args.command == 'emergency-stop':
        emergency_stop_command()
        return
    elif args.command == 'pause-trading':
        pause_trading_command()
        return
    elif args.command == 'resume-trading':
        resume_trading_command()
        return
    elif args.command == 'status':
        status_command()
        return
    
    # Default to run command if no command specified
    if args.command is None or args.command == 'run':
        # Setup logging
        setup_logging(getattr(args, 'log_level', 'INFO'))
        
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


if __name__ == '__main__':
    main()
