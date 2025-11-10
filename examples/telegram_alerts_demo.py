#!/usr/bin/env python
"""
Example: Telegram Bot Integration Demo

Demonstrates how the Telegram bot integrates with the trading bot.
Shows all alert types in action.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def demo_telegram_alerts():
    """Demo all Telegram alert types."""
    print("=" * 70)
    print("📱 TELEGRAM BOT ALERTS - INTEGRATION DEMO")
    print("=" * 70)
    print()

    # Import after path setup
    from yunmin.notifications.telegram_bot import TelegramBot

    # Create bot instance (disabled for demo)
    bot = TelegramBot("", "")

    print("This demo shows all alert types that will be sent to Telegram")
    print("when the bot is properly configured.")
    print()
    print("To enable alerts:")
    print("  1. Run: python setup_telegram.py")
    print("  2. Configure your token and chat_id in config/default.yaml")
    print("  3. Set telegram.enabled: true")
    print()
    print("-" * 70)
    print()

    # 1. Bot Startup
    print("🤖 BOT STARTUP ALERT")
    print("-" * 70)
    await bot.alert_bot_started(mode="dry_run", symbol="BTC/USDT", capital=10000.0)
    print("✓ Sent when bot starts trading")
    print()

    await asyncio.sleep(1)

    # 2. Trade Execution (BUY)
    print("🟢 TRADE EXECUTION ALERT - BUY")
    print("-" * 70)
    await bot.alert_trade(
        side="BUY",
        symbol="BTC/USDT",
        price=50000.0,
        size=0.01,
        reason="RSI oversold at 28, EMA bullish cross",
        portfolio_pnl=0.0,
        portfolio_pnl_pct=0.0,
        open_positions=1,
    )
    print("✓ Sent immediately after BUY order executed")
    print()

    await asyncio.sleep(1)

    # 3. Trade Execution (SELL)
    print("🔴 TRADE EXECUTION ALERT - SELL")
    print("-" * 70)
    await bot.alert_trade(
        side="SELL",
        symbol="BTC/USDT",
        price=51500.0,
        size=0.01,
        reason="Take profit hit at +3%",
        portfolio_pnl=150.0,
        portfolio_pnl_pct=1.5,
        open_positions=0,
    )
    print("✓ Sent immediately after SELL order executed")
    print()

    await asyncio.sleep(1)

    # 4. Error Alert
    print("⚠️ ERROR ALERT")
    print("-" * 70)
    await bot.alert_error(
        error_type="API Connection", error_msg="Failed to connect to exchange API. Retrying in 30s..."
    )
    print("✓ Sent when critical error occurs (with sound)")
    print()

    await asyncio.sleep(1)

    # 5. Drawdown Warning
    print("🔴 DRAWDOWN WARNING (CRITICAL)")
    print("-" * 70)
    await bot.alert_drawdown(
        current_drawdown=12.5,
        threshold=10.0,
        capital=8750.0,
        peak=10000.0,
        action_taken="✅ Reduced position sizes to 50%\n✅ No new trades until recovery",
    )
    print("✓ Sent when portfolio drawdown exceeds threshold (with sound)")
    print()

    await asyncio.sleep(1)

    # 6. Daily Summary
    print("📊 DAILY PERFORMANCE SUMMARY")
    print("-" * 70)
    await bot.alert_daily_summary(
        trades_today=15,
        win_rate=66.7,
        pnl_today=450.75,
        pnl_today_pct=4.5,
        total_capital=10450.75,
        open_positions=2,
    )
    print("✓ Sent twice daily at 8am and 8pm (silent)")
    print()

    await asyncio.sleep(1)

    # 7. Bot Shutdown
    print("🛑 BOT SHUTDOWN ALERT")
    print("-" * 70)
    await bot.alert_bot_stopped(reason="Manual stop by user")
    print("✓ Sent when bot stops (with sound)")
    print()

    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Alert Frequency:")
    print("  • Trade alerts: Every trade (instant)")
    print("  • Error alerts: As they occur (instant)")
    print("  • Drawdown warnings: When threshold exceeded (instant)")
    print("  • Daily summaries: Twice daily (8am, 8pm)")
    print("  • Bot lifecycle: Startup/shutdown (instant)")
    print()
    print("Notification Types:")
    print("  • 🔴 Critical alerts: WITH sound (drawdown, errors, shutdown)")
    print("  • 🟢 Trade alerts: WITH sound (buy/sell)")
    print("  • 📊 Summaries: Silent (daily reports)")
    print("  • 🤖 Startup: Silent (bot started)")
    print()
    print("Setup Instructions:")
    print("  1. python setup_telegram.py")
    print("  2. Edit config/default.yaml")
    print("  3. Start your bot!")
    print()


if __name__ == "__main__":
    print()
    asyncio.run(demo_telegram_alerts())
