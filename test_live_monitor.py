"""
Quick test script for live test infrastructure.
Tests the monitor and basic functionality without running the full bot.
"""

from live_test_monitor import LiveTestMonitor
import time
from datetime import datetime


def test_monitor():
    """Test the LiveTestMonitor class."""
    print("=" * 60)
    print("Testing Live Test Monitor")
    print("=" * 60)
    
    # Initialize monitor
    monitor = LiveTestMonitor(output_dir="data/live_test")
    print("✅ Monitor initialized")
    
    # Start a test session
    monitor.start_session(session_id=99, market_condition="test")
    print("✅ Session started")
    
    # Simulate some signals
    print("\n📊 Simulating 5 iterations...")
    for i in range(1, 6):
        signal = ['BUY', 'SELL', 'HOLD'][i % 3]
        monitor.record_signal(
            iteration=i,
            signal_type=signal,
            confidence=0.75,
            price=100000 + i * 100,
            action="OPEN" if signal in ['BUY', 'SELL'] else "",
            reason=f"Test signal {i}"
        )
        print(f"  Iteration {i}: {signal}")
        time.sleep(0.1)
    
    # Simulate a trade
    print("\n💼 Recording a test trade...")
    monitor.record_trade({
        'symbol': 'BTC/USDT',
        'side': 'LONG',
        'entry_price': 100100,
        'exit_price': 100500,
        'amount': 0.1,
        'pnl': 40.0,
        'pnl_pct': 0.4,
        'opened_at': datetime.now().isoformat(),
        'closed_at': datetime.now().isoformat()
    })
    print("✅ Trade recorded")
    
    # Test drawdown
    print("\n📉 Testing drawdown tracking...")
    monitor.update_drawdown(10000)  # Peak
    monitor.update_drawdown(9500)   # 5% drawdown
    monitor.update_drawdown(9000)   # 10% drawdown
    print(f"  Max Drawdown: {monitor.max_drawdown * 100:.1f}%")
    
    # Test API usage
    print("\n🤖 Recording API usage...")
    monitor.record_api_usage(tokens=500)
    monitor.record_api_usage(tokens=500)
    print(f"  Total Tokens: {monitor.total_tokens}")
    
    # End session
    monitor.end_session()
    print("✅ Session ended")
    
    # Get summary
    print("\n📊 Session Summary:")
    summary = monitor.get_summary()
    print(f"  - Iterations: {summary['iterations_completed']}")
    print(f"  - Signals: {summary['signal_distribution']}")
    print(f"  - Trades: {summary['total_trades']}")
    print(f"  - Win Rate: {summary['win_rate'] * 100:.1f}%")
    print(f"  - P&L: ${summary['total_pnl']:+.2f}")
    print(f"  - Max Drawdown: {summary['max_drawdown'] * 100:.1f}%")
    print(f"  - API Tokens: {summary['openai_stats']['total_tokens']}")
    
    # Save files
    print("\n💾 Saving results...")
    monitor.save_log_csv(filename="test_log.csv")
    monitor.save_results_json(filename="test_results.json")
    monitor.generate_report(filename="TEST_REPORT.md")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - data/live_test/test_log.csv")
    print("  - data/live_test/test_results.json")
    print("  - data/live_test/TEST_REPORT.md")
    print("\nYou can now run the full live test with:")
    print("  python run_live_test.py --session 1 --iterations 3 --interval 10")


if __name__ == "__main__":
    test_monitor()
