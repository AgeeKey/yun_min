# 📱 Telegram Bot Alerts - Quick Start Guide

Get instant trading notifications on your phone in under 5 minutes!

## ✨ Features

- **🟢 Trade Alerts**: Real-time BUY/SELL notifications with P&L
- **🔴 Critical Alerts**: Errors, drawdowns, system failures (with sound)
- **📊 Daily Summaries**: Performance reports twice daily (silent)
- **🤖 Bot Lifecycle**: Startup/shutdown notifications
- **⚙️ Configurable**: Choose which alerts you want to receive

## 🚀 Quick Setup (5 minutes)

### Step 1: Create Your Bot

1. Open Telegram and search for **@BotFather**
2. Send: `/newbot`
3. Choose a name: `YunMin Trading Alerts` (or your preference)
4. Choose username: `yunmin_alerts_bot` (must end with 'bot')
5. **Copy the bot token** you receive (looks like `123456:ABCdefgh...`)

### Step 2: Get Your Chat ID

1. Open Telegram and search for **@userinfobot**
2. Start a chat and send any message
3. **Copy your ID** (the number shown)

### Step 3: Configure YunMin

Run the interactive setup wizard:

```bash
python setup_telegram.py
```

Or manually edit `config/default.yaml`:

```yaml
telegram:
  enabled: true
  bot_token: "YOUR_BOT_TOKEN_HERE"  # From @BotFather
  chat_id: "YOUR_CHAT_ID_HERE"      # From @userinfobot
  
  alerts:
    trade_execution: true      # Alert on every trade
    daily_summary: true        # Daily performance report
    critical_only: false       # Only critical alerts
    drawdown_threshold: 10.0   # Alert if drawdown > 10%
    error_alerts: true         # Alert on errors
    startup_alert: true        # Alert when bot starts
    shutdown_alert: true       # Alert when bot stops
```

### Step 4: Test It!

```bash
python -c "
import asyncio
from yunmin.notifications.telegram_bot import TelegramBot

async def test():
    bot = TelegramBot('YOUR_TOKEN', 'YOUR_CHAT_ID')
    await bot.test_connection()

asyncio.run(test())
"
```

You should receive a test message on Telegram! 🎉

## 📱 Alert Examples

### Trade Execution Alert

```
🟢 BUY EXECUTED

Symbol: BTC/USDT
Price: $50,000.00
Size: 0.01000000 ($500.00)
Reason: RSI oversold at 28

Portfolio:
• P&L Today: +$245.00 (+2.45%)
• Open Positions: 1

Time: 2025-11-09 14:23:45
```

### Critical Drawdown Alert (with 🔔)

```
🔴 DRAWDOWN WARNING

Current Drawdown: 12.5%
Threshold: 10.0%

Portfolio:
• Capital: $8,750.00
• Peak: $10,000.00
• Loss: $1,250.00

Action Taken:
✅ Reduced position sizes to 50%
✅ No new trades until recovery

Time: 2025-11-09 15:45:30
```

### Daily Summary (silent)

```
🎉 Daily Summary

Performance:
• Trades: 15
• Win Rate: 66.7%
• P&L: +$450.75 (+4.5%)

Portfolio:
• Total Capital: $10,450.75
• Open Positions: 2

Date: 2025-11-09
```

## ⚙️ Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `enabled` | `false` | Enable/disable Telegram alerts |
| `bot_token` | - | Your bot token from @BotFather |
| `chat_id` | - | Your Telegram chat ID |
| `trade_execution` | `true` | Alert on every trade |
| `daily_summary` | `true` | Send daily performance report |
| `critical_only` | `false` | Only send critical alerts |
| `drawdown_threshold` | `10.0` | Alert if drawdown exceeds % |
| `error_alerts` | `true` | Alert on system errors |
| `startup_alert` | `true` | Alert when bot starts |
| `shutdown_alert` | `true` | Alert when bot stops |

## 🧪 Testing

Run the unit tests:

```bash
pytest tests/test_telegram.py -v
```

Run manual verification:

```bash
python test_telegram_manual.py
```

## 🛠️ Integration

The Telegram bot is automatically integrated into the trading bot. Alerts are sent for:

- **Trade Execution** (BUY/SELL)
- **Position Opened/Closed**
- **Bot Started/Stopped**
- **Errors and Exceptions**
- **Drawdown Warnings**

No additional code required - just configure and run!

## 📚 API Reference

### TelegramBot Class

```python
from yunmin.notifications.telegram_bot import TelegramBot

bot = TelegramBot(token="123:ABC", chat_id="456")

# Send trade alert
await bot.alert_trade(
    side="BUY",
    symbol="BTC/USDT",
    price=50000.0,
    size=0.01,
    reason="RSI oversold",
    portfolio_pnl=100.0,
    portfolio_pnl_pct=1.5,
    open_positions=1
)

# Send critical alert (with sound)
await bot.alert_critical(
    title="System Error",
    message="Exchange API connection lost",
    action="Retrying in 30 seconds..."
)

# Send daily summary (silent)
await bot.alert_daily_summary(
    trades_today=10,
    win_rate=60.0,
    pnl_today=250.0,
    pnl_today_pct=2.5,
    total_capital=10250.0,
    open_positions=2
)
```

### Singleton Pattern

```python
from yunmin.notifications.telegram_bot import get_telegram_bot

# Get the global instance
bot = get_telegram_bot()

# Or initialize with credentials
bot = get_telegram_bot(token="123:ABC", chat_id="456")
```

## 🔒 Security

- ✅ Bot token and chat ID stored in config (not hardcoded)
- ✅ No external dependencies except `aiohttp`
- ✅ Graceful degradation if Telegram unavailable
- ✅ No sensitive data in alerts (only trading info)
- ✅ Passed CodeQL security scan

## 🐛 Troubleshooting

### "Bot not configured" message

Make sure:
1. `telegram.enabled: true` in config
2. Valid `bot_token` and `chat_id`
3. Token doesn't start with "YOUR_"

### No messages received

1. Start a chat with your bot (press START button)
2. Verify chat_id is correct (use @userinfobot)
3. Check bot token is valid
4. Verify internet connection

### "aiohttp not installed" error

```bash
pip install aiohttp>=3.9.0
```

Or reinstall dependencies:

```bash
pip install -r requirements.txt
```

## 📝 Notes

- Telegram API is **100% free forever**
- No rate limits for personal use
- Messages delivered within 1-2 seconds
- Works globally (no geographic restrictions)
- Can mute specific alert types in config

## 🎯 Next Steps

1. ✅ Complete setup using this guide
2. ✅ Test with manual script
3. ✅ Configure alert preferences
4. ✅ Start trading bot
5. ✅ Receive instant notifications!

---

**Need Help?**
- Check logs for detailed error messages
- Run tests to verify setup
- Review config file syntax
- Ensure bot started successfully

**Ready to Trade?**

Your bot is now configured to send real-time alerts! Start the trading bot and watch notifications arrive on your phone. Happy trading! 🚀
