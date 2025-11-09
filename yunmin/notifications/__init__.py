"""
Notification system for YunMin Trading Bot.

Supports multiple notification channels:
- Telegram: Real-time trading alerts
- Discord: Community notifications (future)
- Email: Daily reports (future)
"""

from yunmin.notifications.telegram_bot import TelegramBot, get_telegram_bot

__all__ = ['TelegramBot', 'get_telegram_bot']
