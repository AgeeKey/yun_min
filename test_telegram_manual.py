#!/usr/bin/env python
"""
Test script for Telegram Bot alerts.

Tests the functionality without actually sending messages to Telegram.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yunmin.notifications.telegram_bot import TelegramBot


async def test_telegram_alerts():
    """Test all Telegram alert types."""
    print("=" * 60)
    print("🧪 Testing Telegram Bot Alerts")
    print("=" * 60)
    print()
    
    # Test 1: Disabled bot (no token)
    print("Test 1: Disabled Bot")
    print("-" * 60)
    bot = TelegramBot("", "")
    print(f"Bot enabled: {bot.enabled}")
    result = await bot.send_message("This should not be sent")
    print(f"Send result: {result}")
    print()
    
    # Test 2: Enabled bot (with fake credentials)
    print("Test 2: Enabled Bot (fake credentials)")
    print("-" * 60)
    bot = TelegramBot("123:ABC", "456")
    print(f"Bot enabled: {bot.enabled}")
    print(f"Base URL: {bot.base_url}")
    print()
    
    # Test 3: Trade alert formatting
    print("Test 3: Trade Alert Format")
    print("-" * 60)
    bot_disabled = TelegramBot("", "")
    await bot_disabled.alert_trade(
        side="BUY",
        symbol="BTC/USDT",
        price=50000.0,
        size=0.01,
        reason="RSI oversold at 28",
        portfolio_pnl=245.50,
        portfolio_pnl_pct=2.45,
        open_positions=1
    )
    print("✓ Trade alert formatted (check logs)")
    print()
    
    # Test 4: Critical alert formatting
    print("Test 4: Critical Alert Format")
    print("-" * 60)
    await bot_disabled.alert_critical(
        title="TEST ALERT",
        message="This is a test critical alert",
        action="✅ Test action taken"
    )
    print("✓ Critical alert formatted (check logs)")
    print()
    
    # Test 5: Drawdown alert
    print("Test 5: Drawdown Alert Format")
    print("-" * 60)
    await bot_disabled.alert_drawdown(
        current_drawdown=12.5,
        threshold=10.0,
        capital=8750.0,
        peak=10000.0,
        action_taken="✅ Reduced position sizes\n✅ Stopped new trades"
    )
    print("✓ Drawdown alert formatted (check logs)")
    print()
    
    # Test 6: Error alert
    print("Test 6: Error Alert Format")
    print("-" * 60)
    await bot_disabled.alert_error(
        error_type="API Connection",
        error_msg="Failed to connect to exchange API"
    )
    print("✓ Error alert formatted (check logs)")
    print()
    
    # Test 7: Daily summary
    print("Test 7: Daily Summary Format")
    print("-" * 60)
    await bot_disabled.alert_daily_summary(
        trades_today=15,
        win_rate=66.7,
        pnl_today=450.75,
        pnl_today_pct=4.5,
        total_capital=10450.75,
        open_positions=2
    )
    print("✓ Daily summary formatted (check logs)")
    print()
    
    # Test 8: Bot lifecycle alerts
    print("Test 8: Bot Lifecycle Alerts")
    print("-" * 60)
    await bot_disabled.alert_bot_started(
        mode="dry_run",
        symbol="BTC/USDT",
        capital=10000.0
    )
    print("✓ Bot started alert formatted")
    
    await bot_disabled.alert_bot_stopped(
        reason="Testing complete"
    )
    print("✓ Bot stopped alert formatted")
    print()
    
    # Test 9: Singleton pattern
    print("Test 9: Singleton Pattern")
    print("-" * 60)
    from yunmin.notifications.telegram_bot import get_telegram_bot
    
    bot1 = get_telegram_bot("token1", "chat1")
    bot2 = get_telegram_bot()
    
    print(f"bot1 is bot2: {bot1 is bot2}")
    print(f"bot1.token: {bot1.token}")
    print()
    
    print("=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print()
    print("To test with real Telegram:")
    print("1. Run: python setup_telegram.py")
    print("2. Follow the instructions to get token and chat_id")
    print("3. Update config/default.yaml with your credentials")
    print()


if __name__ == "__main__":
    asyncio.run(test_telegram_alerts())
