"""
Alert Manager - Monitoring and Notifications System
Sends alerts via Telegram, Email, and Webhooks
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, UTC
from loguru import logger


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    TELEGRAM = "telegram"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class AlertConfig:
    """Configuration for alert manager"""
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Email
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    
    # Webhook
    webhook_url: Optional[str] = None
    webhook_headers: Dict[str, str] = field(default_factory=dict)
    
    # Alert settings
    enabled_channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG])
    min_alert_level: AlertLevel = AlertLevel.WARNING
    rate_limit_seconds: int = 60  # Don't spam same alert
    retry_attempts: int = 3


@dataclass
class Alert:
    """Alert message"""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"[{self.level.value.upper()}] {self.title}: {self.message}"


class AlertManager:
    """
    Manages alerts and notifications across multiple channels.
    
    Features:
    - Multi-channel delivery (Telegram, Email, Webhook, Logs)
    - Rate limiting to prevent spam
    - Alert level filtering
    - Async delivery with retries
    - Health monitoring integration
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig()
        self.alert_history: List[Alert] = []
        self.last_alert_time: Dict[str, datetime] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[AlertChannel]] = None
    ):
        """
        Send alert through configured channels.
        
        Args:
            level: Alert severity level
            title: Alert title
            message: Alert message
            metadata: Additional context
            channels: Override default channels
        """
        # Filter by minimum level
        if not self._should_send_alert(level):
            logger.debug(f"Alert below minimum level: {level.value} < {self.config.min_alert_level.value}")
            return
        
        # Rate limiting
        alert_key = f"{title}:{message}"
        if self._is_rate_limited(alert_key):
            logger.debug(f"Alert rate limited: {alert_key}")
            return
        
        # Create alert
        alert = Alert(
            level=level,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        self.alert_history.append(alert)
        self.last_alert_time[alert_key] = datetime.now(UTC)
        
        # Determine channels
        target_channels = channels or self.config.enabled_channels
        
        # Send to each channel
        tasks = []
        for channel in target_channels:
            if channel == AlertChannel.TELEGRAM:
                tasks.append(self._send_telegram(alert))
            elif channel == AlertChannel.EMAIL:
                tasks.append(self._send_email(alert))
            elif channel == AlertChannel.WEBHOOK:
                tasks.append(self._send_webhook(alert))
            elif channel == AlertChannel.LOG:
                self._send_log(alert)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_info(self, title: str, message: str, **metadata):
        """Send INFO level alert"""
        await self.send_alert(AlertLevel.INFO, title, message, metadata)
    
    async def send_warning(self, title: str, message: str, **metadata):
        """Send WARNING level alert"""
        await self.send_alert(AlertLevel.WARNING, title, message, metadata)
    
    async def send_error(self, title: str, message: str, **metadata):
        """Send ERROR level alert"""
        await self.send_alert(AlertLevel.ERROR, title, message, metadata)
    
    async def send_critical(self, title: str, message: str, **metadata):
        """Send CRITICAL level alert"""
        await self.send_alert(AlertLevel.CRITICAL, title, message, metadata)
    
    def _should_send_alert(self, level: AlertLevel) -> bool:
        """Check if alert level meets minimum threshold"""
        levels = [AlertLevel.INFO, AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL]
        return levels.index(level) >= levels.index(self.config.min_alert_level)
    
    def _is_rate_limited(self, alert_key: str) -> bool:
        """Check if alert is rate limited"""
        if alert_key not in self.last_alert_time:
            return False
        
        time_since_last = (datetime.now(UTC) - self.last_alert_time[alert_key]).total_seconds()
        return time_since_last < self.config.rate_limit_seconds
    
    async def _send_telegram(self, alert: Alert):
        """Send alert via Telegram"""
        if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
            logger.warning("Telegram not configured")
            return
        
        url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
        
        # Format message with emoji
        emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨"
        }
        
        text = (
            f"{emoji.get(alert.level, '📢')} *{alert.title}*\n\n"
            f"{alert.message}\n\n"
            f"_Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}_"
        )
        
        if alert.metadata:
            text += f"\n\n*Details:*\n"
            for key, value in alert.metadata.items():
                text += f"• {key}: `{value}`\n"
        
        payload = {
            "chat_id": self.config.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            async with self._get_session().post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.success(f"✅ Telegram alert sent: {alert.title}")
                else:
                    logger.error(f"❌ Telegram failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Telegram error: {e}")
    
    async def _send_email(self, alert: Alert):
        """Send alert via Email"""
        if not all([self.config.smtp_server, self.config.email_from, self.config.email_to]):
            logger.warning("Email not configured")
            return
        
        try:
            import aiosmtplib
            from email.message import EmailMessage
            
            msg = EmailMessage()
            msg["From"] = self.config.email_from
            msg["To"] = ", ".join(self.config.email_to)
            msg["Subject"] = f"[{alert.level.value.upper()}] {alert.title}"
            
            body = (
                f"Alert Level: {alert.level.value.upper()}\n"
                f"Title: {alert.title}\n"
                f"Message: {alert.message}\n"
                f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            )
            
            if alert.metadata:
                body += "\nDetails:\n"
                for key, value in alert.metadata.items():
                    body += f"  {key}: {value}\n"
            
            msg.set_content(body)
            
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.smtp_username,
                password=self.config.smtp_password,
                start_tls=True
            )
            
            logger.success(f"✅ Email alert sent: {alert.title}")
        
        except ImportError:
            logger.error("❌ aiosmtplib not installed. Install with: pip install aiosmtplib")
        except Exception as e:
            logger.error(f"❌ Email error: {e}")
    
    async def _send_webhook(self, alert: Alert):
        """Send alert via Webhook"""
        if not self.config.webhook_url:
            logger.warning("Webhook not configured")
            return
        
        payload = {
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }
        
        try:
            async with self._get_session().post(
                self.config.webhook_url,
                json=payload,
                headers=self.config.webhook_headers
            ) as resp:
                if resp.status in (200, 201, 204):
                    logger.success(f"✅ Webhook alert sent: {alert.title}")
                else:
                    logger.error(f"❌ Webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
    
    def _send_log(self, alert: Alert):
        """Send alert to logs"""
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }
        
        func = log_func.get(alert.level, logger.info)
        func(str(alert))
    
    def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_alert_history(
        self,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get alert history with optional filtering"""
        alerts = self.alert_history
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        return alerts[-limit:]
    
    def clear_history(self):
        """Clear alert history"""
        self.alert_history.clear()
        self.last_alert_time.clear()


# Trading-specific alert helpers
class TradingAlerts:
    """Pre-configured alerts for trading scenarios"""
    
    @staticmethod
    async def position_opened(manager: AlertManager, symbol: str, side: str, amount: float, price: float):
        """Alert when position is opened"""
        await manager.send_info(
            "Position Opened",
            f"{side} {amount} {symbol} @ ${price:,.2f}",
            symbol=symbol,
            side=side,
            amount=amount,
            price=price
        )
    
    @staticmethod
    async def position_closed(manager: AlertManager, symbol: str, pnl: float, pnl_pct: float):
        """Alert when position is closed"""
        level = AlertLevel.INFO if pnl > 0 else AlertLevel.WARNING
        emoji = "💰" if pnl > 0 else "📉"
        
        await manager.send_alert(
            level,
            f"{emoji} Position Closed",
            f"{symbol}: P&L ${pnl:,.2f} ({pnl_pct:+.2f}%)",
            metadata={
                "symbol": symbol,
                "pnl": pnl,
                "pnl_pct": pnl_pct
            }
        )
    
    @staticmethod
    async def risk_limit_hit(manager: AlertManager, limit_type: str, current: float, max_allowed: float):
        """Alert when risk limit is hit"""
        await manager.send_error(
            "Risk Limit Hit",
            f"{limit_type}: {current:.2f} exceeds max {max_allowed:.2f}",
            limit_type=limit_type,
            current=current,
            max_allowed=max_allowed
        )
    
    @staticmethod
    async def connection_lost(manager: AlertManager, exchange: str):
        """Alert when exchange connection is lost"""
        await manager.send_critical(
            "Connection Lost",
            f"Lost connection to {exchange}. Attempting reconnection...",
            exchange=exchange
        )
    
    @staticmethod
    async def daily_summary(
        manager: AlertManager,
        trades: int,
        pnl: float,
        win_rate: float,
        largest_win: float,
        largest_loss: float
    ):
        """Send daily trading summary"""
        await manager.send_info(
            "📊 Daily Summary",
            f"Trades: {trades} | P&L: ${pnl:,.2f} | Win Rate: {win_rate:.1f}%",
            trades=trades,
            pnl=pnl,
            win_rate=win_rate,
            largest_win=largest_win,
            largest_loss=largest_loss
        )


# Example usage
if __name__ == "__main__":
    async def test_alerts():
        """Test alert manager"""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG],
            min_alert_level=AlertLevel.INFO
        )
        
        manager = AlertManager(config)
        
        # Test different alert levels
        await manager.send_info("Test Info", "This is an info message")
        await manager.send_warning("Test Warning", "This is a warning")
        await manager.send_error("Test Error", "This is an error")
        await manager.send_critical("Test Critical", "This is critical!")
        
        # Test trading alerts
        await TradingAlerts.position_opened(
            manager, "BTC/USDT", "LONG", 0.01, 50000.0
        )
        
        await TradingAlerts.position_closed(
            manager, "BTC/USDT", 150.0, 3.0
        )
        
        # Show history
        print("\nAlert History:")
        for alert in manager.get_alert_history():
            print(f"  {alert}")
        
        await manager.close()
    
    asyncio.run(test_alerts())
