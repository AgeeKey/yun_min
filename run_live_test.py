"""
Extended Live Test on Binance Testnet
Runs for 100+ iterations with real-time market data.

Usage:
    # Session 1: Normal market (100 iterations, 5-min intervals)
    python run_live_test.py --session 1 --iterations 100 --interval 300
    
    # Session 2: Volatile market (50 iterations, 2-min intervals)
    python run_live_test.py --session 2 --iterations 50 --interval 120 --condition volatile
    
    # Session 3: Overnight test (50 iterations, 10-min intervals)
    python run_live_test.py --session 3 --iterations 50 --interval 600 --condition overnight
"""

import sys
import argparse
import time
from loguru import logger
from pathlib import Path

from yunmin.core.config import YunMinConfig, ExchangeConfig, TradingConfig, RiskConfig, StrategyConfig, LLMConfig
from yunmin.bot import YunMinBot
from live_test_monitor import LiveTestMonitor


def run_extended_test(
    session_id: int = 1,
    iterations: int = 100,
    interval: int = 300,
    market_condition: str = "normal",
    symbol: str = "BTC/USDT",
    initial_capital: float = 10000.0
):
    """
    Run extended live test on Binance testnet.
    
    Args:
        session_id: Session identifier (1, 2, 3, etc.)
        iterations: Number of iterations to run
        interval: Seconds between iterations
        market_condition: Market condition type (normal/volatile/overnight)
        symbol: Trading symbol
        initial_capital: Starting capital
        
    Returns:
        Test statistics
    """
    
    print("=" * 60)
    print("🚀 Yun Min Live Test - Extended Run")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"Iterations: {iterations}")
    print(f"Interval: {interval}s ({interval/60:.1f} min)")
    print(f"Market Condition: {market_condition}")
    print(f"Expected Duration: {iterations * interval / 3600:.1f} hours")
    print("=" * 60)
    
    # Initialize monitor
    monitor = LiveTestMonitor()
    monitor.start_session(session_id, market_condition)
    
    # Create configuration
    config = YunMinConfig(
        exchange=ExchangeConfig(
            name="binance",
            testnet=True,
            # API keys from environment variables if available
        ),
        trading=TradingConfig(
            mode="dry_run",  # Safe mode - no real orders
            symbol=symbol,
            timeframe="5m",
            initial_capital=initial_capital
        ),
        risk=RiskConfig(
            max_position_size=0.1,  # 10% per position
            max_leverage=1.0,
            max_daily_drawdown=0.05,  # 5% max daily loss
            stop_loss_pct=0.02,  # 2% stop loss
            take_profit_pct=0.03,  # 3% take profit
            enable_circuit_breaker=True
        ),
        strategy=StrategyConfig(
            name="ema_crossover",
            fast_ema=9,
            slow_ema=21,
            rsi_period=14,
            rsi_overbought=70.0,
            rsi_oversold=30.0
        ),
        llm=LLMConfig(
            enabled=True,
            provider="openai",  # or "grok"
            model="gpt-4o-mini"
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
    
    if config.llm.enabled:
        print(f"  - LLM: {config.llm.provider} ({config.llm.model})")
    
    print(f"\n🤖 Running bot for {iterations} iterations...")
    print(f"   Interval: {interval}s ({interval/60:.1f} minutes)")
    print(f"   Press Ctrl+C to stop early\n")
    
    # Run the test with monitoring
    try:
        iteration_count = 0
        bot.is_running = True
        
        while bot.is_running and iteration_count < iterations:
            iteration_count += 1
            
            print(f"\n{'='*60}")
            print(f"Iteration {iteration_count}/{iterations}")
            print(f"{'='*60}")
            
            # Run one iteration
            bot.run_once()
            
            # Get current price
            current_price = bot.get_current_price()
            
            # Get statistics from bot
            stats = bot.get_statistics()
            
            # Update monitor with signal
            signal_type = getattr(bot.strategy, '_last_signal_type', 'HOLD')
            confidence = getattr(bot.strategy, '_last_confidence', 0.5)
            reason = getattr(bot.strategy, '_last_reasoning', 'Analysis completed')
            
            # Check if any trade was closed this iteration
            pnl = None
            action = ""
            if stats['total_trades'] > len(monitor.trades):
                # New trade was closed
                recent_trades = bot.pnl_tracker.get_recent_trades(1)
                if recent_trades:
                    latest_trade = recent_trades[0]
                    pnl = latest_trade.pnl
                    action = "CLOSE"
                    monitor.record_trade({
                        'symbol': latest_trade.symbol,
                        'side': latest_trade.side,
                        'entry_price': latest_trade.entry_price,
                        'exit_price': latest_trade.exit_price,
                        'amount': latest_trade.amount,
                        'pnl': latest_trade.pnl,
                        'pnl_pct': latest_trade.pnl_pct,
                        'opened_at': latest_trade.opened_at.isoformat(),
                        'closed_at': latest_trade.closed_at.isoformat()
                    })
            elif stats['open_positions'] > 0 and len(monitor.signal_history) > 0:
                # Check if position was just opened
                if monitor.signal_history[-1].action != "OPEN":
                    action = "OPEN"
            
            monitor.record_signal(
                iteration=iteration_count,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price or 0.0,
                action=action,
                pnl=pnl,
                reason=reason
            )
            
            # Update drawdown
            current_capital = config.trading.initial_capital + stats['total_pnl']
            monitor.update_drawdown(current_capital)
            
            # Record API usage if LLM is enabled
            if hasattr(bot.llm_analyzer, 'enabled') and bot.llm_analyzer.enabled:
                # Approximate token count (will be more accurate with OpenAI response tracking)
                monitor.record_api_usage(tokens=500)  # Rough estimate per call
            
            # Progress report
            print(f"\n📊 Progress:")
            print(f"   Iteration: {iteration_count}/{iterations} ({iteration_count/iterations*100:.1f}%)")
            print(f"   Total Trades: {stats['total_trades']}")
            print(f"   Win Rate: {stats['win_rate']:.1f}%")
            print(f"   Total P&L: ${stats['total_pnl']:+.2f}")
            print(f"   Current Drawdown: {monitor.current_drawdown*100:.2f}%")
            print(f"   Signal Distribution: BUY={monitor.signals['BUY']}, SELL={monitor.signals['SELL']}, HOLD={monitor.signals['HOLD']}")
            
            # Save checkpoint every 10 iterations
            if iteration_count % 10 == 0:
                print(f"\n💾 Checkpoint at iteration {iteration_count}")
                monitor.save_log_csv()
                monitor.save_results_json()
            
            if iteration_count >= iterations:
                break
                
            # Wait for next iteration
            if iteration_count < iterations:
                print(f"\n⏳ Waiting {interval}s until next iteration...")
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print("\n\n⏹️  Test stopped by user")
    except Exception as e:
        logger.error(f"Test error: {e}")
        raise
    finally:
        # End session and save results
        monitor.end_session()
        
        print("\n" + "=" * 60)
        print("📊 Saving Results...")
        print("=" * 60)
        
        # Save all results
        monitor.save_log_csv()
        monitor.save_results_json()
        monitor.generate_report()
        
        # Stop bot
        bot.stop()
        
        # Print summary
        summary = monitor.get_summary()
        print("\n" + "=" * 60)
        print("✅ Test Complete - Summary")
        print("=" * 60)
        print(f"Session: {summary['session_id']}")
        print(f"Iterations: {summary['iterations_completed']}/{iterations}")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']*100:.1f}%")
        print(f"Total P&L: ${summary['total_pnl']:+.2f}")
        print(f"Max Drawdown: {summary['max_drawdown']*100:.1f}%")
        print(f"Signal Distribution:")
        for signal, count in summary['signal_distribution'].items():
            print(f"  - {signal}: {count}")
        if summary['openai_stats']['total_tokens'] > 0:
            print(f"OpenAI Usage:")
            print(f"  - Total Tokens: {summary['openai_stats']['total_tokens']:,}")
            print(f"  - API Calls: {summary['openai_stats']['api_calls']}")
            print(f"  - Est. Cost: ${summary['openai_stats']['estimated_cost_usd']:.4f}")
        print("=" * 60)
        
    return bot.get_statistics()


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="Run extended live test on Binance testnet")
    parser.add_argument(
        '--session',
        type=int,
        default=1,
        help='Session ID (default: 1)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=100,
        help='Number of iterations (default: 100)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Interval in seconds between iterations (default: 300 = 5 min)'
    )
    parser.add_argument(
        '--condition',
        type=str,
        default='normal',
        choices=['normal', 'volatile', 'overnight'],
        help='Market condition type (default: normal)'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTC/USDT',
        help='Trading symbol (default: BTC/USDT)'
    )
    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='Initial capital (default: 10000.0)'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add(
        f"data/live_test/session_{args.session}_{{time}}.log",
        rotation="100 MB",
        level="DEBUG"
    )
    
    # Run the test
    print(f"\n🚀 Starting Session {args.session}...")
    stats = run_extended_test(
        session_id=args.session,
        iterations=args.iterations,
        interval=args.interval,
        market_condition=args.condition,
        symbol=args.symbol,
        initial_capital=args.capital
    )
    
    print(f"\n✅ Session {args.session} complete!")
    print("\nNext steps:")
    print("  1. Review the live_test_log.csv for detailed iteration data")
    print("  2. Check live_test_results.json for session statistics")
    print("  3. Read LIVE_TEST_REPORT.md for analysis and recommendations")
    print("  4. Run additional sessions with different market conditions")
    print("  5. Aggregate results from multiple sessions for comprehensive testing\n")


if __name__ == "__main__":
    main()
