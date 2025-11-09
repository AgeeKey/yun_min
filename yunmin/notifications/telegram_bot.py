"""
Telegram Bot for Trading Alerts.

Sends real-time notifications for:
- Trade execution (BUY/SELL)
- Critical alerts (errors, drawdowns)
- Daily performance summaries
- System status updates

Setup:
    1. Create bot at t.me/BotFather
    2. Get bot token and chat_id
    3. Configure in config/default.yaml
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Send trading alerts via Telegram.
    
    Uses direct Telegram Bot API for minimal dependencies.
    Async implementation for non-blocking notifications.
    
    Example:
        bot = TelegramBot(token="123:ABC", chat_id="456")
        await bot.alert_trade(
            side="BUY",
            symbol="BTC/USDT",
            price=50000,
            size=0.01,
            reason="RSI oversold",
            portfolio_pnl=100,
            portfolio_pnl_pct=1.5,
            open_positions=1
        )
    """
    
    def __init__(self, token: str, chat_id: str):
        """
        Initialize Telegram bot.
        
        Args:
            token: Bot token from @BotFather
            chat_id: Your Telegram chat ID from @userinfobot
        """
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.enabled = bool(token and chat_id and not token.startswith("YOUR_"))
        
        if not self.enabled:
            logger.warning("Telegram bot not configured - alerts disabled")
        else:
            logger.info(f"Telegram bot initialized for chat_id: {chat_id}")
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False
    ) -> bool:
        """
        Send text message via Telegram.
        
        Args:
            text: Message text (supports Markdown)
            parse_mode: Formatting mode (Markdown or HTML)
            disable_notification: Silent notification
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug(f"Alert (not sent): {text[:100]}...")
            return False
        
        try:
            # Import here to avoid issues if aiohttp not installed yet
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_notification": disable_notification
                }
                
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        logger.info("Telegram alert sent successfully")
                        return True
                    else:
                        error = await resp.text()
                        logger.error(f"Failed to send Telegram alert: {error}")
                        return False
        
        except ImportError:
            logger.error("aiohttp not installed - run: pip install aiohttp>=3.9.0")
            return False
        except asyncio.TimeoutError:
            logger.error("Telegram send timeout - check internet connection")
            return False
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    async def alert_trade(
        self,
        side: str,
        symbol: str,
        price: float,
        size: float,
        reason: str,
        portfolio_pnl: float,
        portfolio_pnl_pct: float,
        open_positions: int
    ):
        """
        Send trade execution alert.
        
        Args:
            side: BUY or SELL
            symbol: Trading pair (e.g., BTC/USDT)
            price: Execution price
            size: Position size
            reason: Trading signal reason
            portfolio_pnl: Today's P&L in dollars
            portfolio_pnl_pct: Today's P&L percentage
            open_positions: Number of open positions
        """
        emoji = "🟢" if side == "BUY" else "🔴"
        sign = "+" if portfolio_pnl >= 0 else ""
        
        text = f"""
{emoji} *{side} EXECUTED*

*Symbol:* {symbol}
*Price:* ${price:,.2f}
*Size:* {size:.8f} (${price * size:,.2f})
*Reason:* {reason}

*Portfolio:*
• P&L Today: {sign}${portfolio_pnl:,.2f} ({sign}{portfolio_pnl_pct:.2f}%)
• Open Positions: {open_positions}

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        await self.send_message(text.strip())
    
    async def alert_critical(
        self,
        title: str,
        message: str,
        action: Optional[str] = None
    ):
        """
        Send critical alert with sound notification.
        
        Args:
            title: Alert title
            message: Alert message
            action: Action taken (optional)
        """
        text = f"""
🔴 *{title}*

{message}
"""
        if action:
            text += f"\n*Action Taken:*\n{action}\n"
        
        text += f"\n_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        
        # Critical alerts with sound
        await self.send_message(text.strip(), disable_notification=False)
    
    async def alert_drawdown(
        self,
        current_drawdown: float,
        threshold: float,
        capital: float,
        peak: float,
        action_taken: str
    ):
        """
        Send drawdown warning alert.
        
        Args:
            current_drawdown: Current drawdown percentage
            threshold: Drawdown threshold percentage
            capital: Current capital
            peak: Peak capital
            action_taken: Action taken description
        """
        await self.alert_critical(
            title="DRAWDOWN WARNING",
            message=f"""
*Current Drawdown:* {current_drawdown:.1f}%
*Threshold:* {threshold:.1f}%

*Portfolio:*
• Capital: ${capital:,.2f}
• Peak: ${peak:,.2f}
• Loss: ${peak - capital:,.2f}
""",
            action=action_taken
        )
    
    async def alert_error(self, error_type: str, error_msg: str):
        """
        Send error alert.
        
        Args:
            error_type: Type of error
            error_msg: Error message
        """
        await self.alert_critical(
            title=f"ERROR: {error_type}",
            message=error_msg
        )
    
    async def alert_daily_summary(
        self,
        trades_today: int,
        win_rate: float,
        pnl_today: float,
        pnl_today_pct: float,
        total_capital: float,
        open_positions: int
    ):
        """
        Send daily performance summary.
        
        Args:
            trades_today: Number of trades executed today
            win_rate: Win rate percentage
            pnl_today: P&L for today in dollars
            pnl_today_pct: P&L percentage
            total_capital: Total capital
            open_positions: Number of open positions
        """
        sign = "+" if pnl_today >= 0 else ""
        emoji = "🎉" if pnl_today > 0 else "😐" if pnl_today == 0 else "😞"
        
        text = f"""
{emoji} *Daily Summary*

*Performance:*
• Trades: {trades_today}
• Win Rate: {win_rate:.1f}%
• P&L: {sign}${pnl_today:,.2f} ({sign}{pnl_today_pct:.2f}%)

*Portfolio:*
• Total Capital: ${total_capital:,.2f}
• Open Positions: {open_positions}

_Date: {datetime.now().strftime('%Y-%m-%d')}_
"""
        await self.send_message(text.strip(), disable_notification=True)
    
    async def alert_bot_started(self, mode: str, symbol: str, capital: float):
        """
        Send bot startup notification.
        
        Args:
            mode: Trading mode (dry_run, paper, live)
            symbol: Trading symbol
            capital: Initial capital
        """
        text = f"""
✅ *Bot Started*

*Mode:* {mode.upper()}
*Symbol:* {symbol}
*Capital:* ${capital:,.2f}

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        await self.send_message(text.strip(), disable_notification=True)
    
    async def alert_bot_stopped(self, reason: str = "Manual stop"):
        """
        Send bot shutdown notification.
        
        Args:
            reason: Shutdown reason
        """
        text = f"""
🛑 *Bot Stopped*

*Reason:* {reason}

_Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_
"""
        await self.send_message(text.strip(), disable_notification=False)
    
    async def test_connection(self) -> bool:
        """
        Test bot configuration by sending a test message.
        
        Returns:
            True if test successful
        """
        if not self.enabled:
            logger.error("Telegram bot not configured")
            return False
        
        success = await self.send_message(
            "✅ *YunMin Trading Bot*\n\nTelegram alerts are working!",
            disable_notification=True
        )
        return success


# Singleton instance for easy access
_bot_instance: Optional[TelegramBot] = None


def get_telegram_bot(token: str = None, chat_id: str = None) -> TelegramBot:
    """
    Get or create Telegram bot singleton instance.
    
    Args:
        token: Bot token (optional, uses existing if not provided)
        chat_id: Chat ID (optional, uses existing if not provided)
        
    Returns:
        TelegramBot instance
    """
    global _bot_instance
    
    if _bot_instance is None:
        _bot_instance = TelegramBot(token or "", chat_id or "")
    
    return _bot_instance
