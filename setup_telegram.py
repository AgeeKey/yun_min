"""
Quick setup for Telegram bot.

This interactive script helps you configure Telegram notifications
for the YunMin Trading Bot in just a few minutes.

Usage:
    python setup_telegram.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yunmin.notifications.telegram_bot import TelegramBot


async def setup():
    """Interactive Telegram bot setup."""
    print("=" * 60)
    print("📱 YunMin Trading Bot - Telegram Setup")
    print("=" * 60)
    print()

    print("This wizard will help you set up Telegram notifications.")
    print("You'll need:")
    print("  1. A Telegram bot token (from @BotFather)")
    print("  2. Your Telegram chat ID (from @userinfobot)")
    print()

    # Step 1: Bot Token
    print("-" * 60)
    print("STEP 1: Create Telegram Bot")
    print("-" * 60)
    print()
    print("1. Open Telegram and search for @BotFather")
    print("2. Send: /newbot")
    print("3. Choose a name: 'YunMin Trading Alerts' (or your preference)")
    print("4. Choose a username: 'yunmin_alerts_bot' (must end with 'bot')")
    print("5. Copy the bot token you receive")
    print()

    token = input("Enter your bot token: ").strip()

    if not token or token.startswith("YOUR_"):
        print("❌ Invalid token. Please get a valid token from @BotFather")
        return

    print()

    # Step 2: Chat ID
    print("-" * 60)
    print("STEP 2: Get Your Chat ID")
    print("-" * 60)
    print()
    print("1. Open Telegram and search for @userinfobot")
    print("2. Start a chat and send any message")
    print("3. Copy your 'Id' (the number)")
    print()

    chat_id = input("Enter your chat ID: ").strip()

    if not chat_id or not chat_id.replace("-", "").isdigit():
        print("❌ Invalid chat ID. Please enter a valid numeric ID")
        return

    print()

    # Step 3: Test Connection
    print("-" * 60)
    print("STEP 3: Testing Connection")
    print("-" * 60)
    print()
    print("Sending test message to your Telegram...")

    bot = TelegramBot(token, chat_id)

    if not bot.enabled:
        print("❌ Bot not properly configured")
        return

    try:
        success = await bot.test_connection()

        if success:
            print()
            print("✅ SUCCESS! Check your Telegram for a test message!")
            print()
            print("=" * 60)
            print("CONFIGURATION")
            print("=" * 60)
            print()
            print("Add this to your config/default.yaml:")
            print()
            print("telegram:")
            print("  enabled: true")
            print(f'  bot_token: "{token}"')
            print(f'  chat_id: "{chat_id}"')
            print("  alerts:")
            print("    trade_execution: true")
            print("    daily_summary: true")
            print("    critical_only: false")
            print("    drawdown_threshold: 10.0")
            print("    error_alerts: true")
            print()
            print("=" * 60)
            print()
            print("🚀 Your bot is ready! Start trading and receive alerts!")
            print()
        else:
            print()
            print("❌ Failed to send test message.")
            print()
            print("Troubleshooting:")
            print("  1. Check your bot token is correct")
            print("  2. Check your chat ID is correct")
            print("  3. Make sure you started a chat with your bot")
            print("     (search for your bot in Telegram and press START)")
            print("  4. Check your internet connection")
            print()

    except Exception as e:
        print()
        print(f"❌ Error: {e}")
        print()
        print("Make sure you have installed aiohttp:")
        print("  pip install aiohttp>=3.9.0")
        print()


def main():
    """Run the setup wizard."""
    try:
        asyncio.run(setup())
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
