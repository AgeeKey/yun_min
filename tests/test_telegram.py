"""
Unit tests for Telegram Bot notifications.

Tests the Telegram bot functionality for sending alerts.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from yunmin.notifications.telegram_bot import TelegramBot, get_telegram_bot


class TestTelegramBot:
    """Test cases for TelegramBot class."""
    
    def test_initialization_disabled(self):
        """Test bot initialization when disabled."""
        bot = TelegramBot("", "")
        assert not bot.enabled
        
        bot2 = TelegramBot("YOUR_BOT_TOKEN", "123456")
        assert not bot2.enabled
    
    def test_initialization_enabled(self):
        """Test bot initialization when properly configured."""
        bot = TelegramBot("123:ABC", "456")
        assert bot.enabled
        assert bot.token == "123:ABC"
        assert bot.chat_id == "456"
        assert "123:ABC" in bot.base_url
    
    @pytest.mark.asyncio
    async def test_send_message_disabled(self):
        """Test sending message when bot is disabled."""
        bot = TelegramBot("", "")
        result = await bot.send_message("Test message")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        bot = TelegramBot("123:ABC", "456")
        
        # Create a proper async context manager mock
        class MockResponse:
            status = 200
            async def text(self):
                return "OK"
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None
        
        class MockSession:
            def post(self, *args, **kwargs):
                return MockResponse()
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None
        
        with patch('aiohttp.ClientSession', return_value=MockSession()):
            result = await bot.send_message("Test message")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self):
        """Test failed message sending."""
        bot = TelegramBot("123:ABC", "456")
        
        # Create a proper async context manager mock for error
        class MockResponse:
            status = 400
            async def text(self):
                return "Bad Request"
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None
        
        class MockSession:
            def post(self, *args, **kwargs):
                return MockResponse()
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return None
        
        with patch('aiohttp.ClientSession', return_value=MockSession()):
            result = await bot.send_message("Test message")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_alert_trade(self):
        """Test trade execution alert."""
        bot = TelegramBot("123:ABC", "456")
        
        # Mock send_message
        bot.send_message = AsyncMock(return_value=True)
        
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
        
        # Verify send_message was called
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        # Check message contains key information
        assert "BUY" in message
        assert "BTC/USDT" in message
        assert "50,000" in message
        assert "0.01" in message
        assert "RSI oversold" in message
    
    @pytest.mark.asyncio
    async def test_alert_critical(self):
        """Test critical alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_critical(
            title="Test Alert",
            message="This is a test",
            action="Action taken"
        )
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "Test Alert" in message
        assert "This is a test" in message
        assert "Action taken" in message
    
    @pytest.mark.asyncio
    async def test_alert_drawdown(self):
        """Test drawdown warning alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_drawdown(
            current_drawdown=12.5,
            threshold=10.0,
            capital=8750.0,
            peak=10000.0,
            action_taken="Reduced positions"
        )
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "DRAWDOWN WARNING" in message
        assert "12.5" in message
        assert "10.0" in message
    
    @pytest.mark.asyncio
    async def test_alert_error(self):
        """Test error alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_error(
            error_type="API Error",
            error_msg="Connection failed"
        )
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "API Error" in message
        assert "Connection failed" in message
    
    @pytest.mark.asyncio
    async def test_alert_daily_summary(self):
        """Test daily summary alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_daily_summary(
            trades_today=10,
            win_rate=60.0,
            pnl_today=250.0,
            pnl_today_pct=2.5,
            total_capital=10250.0,
            open_positions=2
        )
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "Daily Summary" in message
        assert "10" in message  # trades
        assert "60" in message  # win rate
    
    @pytest.mark.asyncio
    async def test_alert_bot_started(self):
        """Test bot startup alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_bot_started(
            mode="dry_run",
            symbol="BTC/USDT",
            capital=10000.0
        )
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "Bot Started" in message
        assert "DRY_RUN" in message.upper()
        assert "BTC/USDT" in message
    
    @pytest.mark.asyncio
    async def test_alert_bot_stopped(self):
        """Test bot shutdown alert."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        await bot.alert_bot_stopped(reason="Manual stop")
        
        assert bot.send_message.called
        call_args = bot.send_message.call_args[0]
        message = call_args[0]
        
        assert "Bot Stopped" in message
        assert "Manual stop" in message
    
    @pytest.mark.asyncio
    async def test_test_connection_disabled(self):
        """Test connection test when disabled."""
        bot = TelegramBot("", "")
        result = await bot.test_connection()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self):
        """Test successful connection test."""
        bot = TelegramBot("123:ABC", "456")
        bot.send_message = AsyncMock(return_value=True)
        
        result = await bot.test_connection()
        assert result is True
        assert bot.send_message.called
    
    def test_get_telegram_bot_singleton(self):
        """Test singleton pattern for get_telegram_bot."""
        bot1 = get_telegram_bot("123:ABC", "456")
        bot2 = get_telegram_bot()
        
        # Both should be the same instance
        assert bot1 is bot2
        assert bot1.token == "123:ABC"


class TestTelegramBotIntegration:
    """Integration tests for Telegram bot (require aiohttp)."""
    
    @pytest.mark.asyncio
    async def test_send_message_no_aiohttp(self):
        """Test behavior when aiohttp is not installed."""
        bot = TelegramBot("123:ABC", "456")
        
        # Mock import error
        with patch('builtins.__import__', side_effect=ImportError("No module named 'aiohttp'")):
            result = await bot.send_message("Test")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_timeout(self):
        """Test timeout handling."""
        bot = TelegramBot("123:ABC", "456")
        
        # Mock timeout
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.post.side_effect = asyncio.TimeoutError()
            
            result = await bot.send_message("Test")
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_message_generic_error(self):
        """Test generic error handling."""
        bot = TelegramBot("123:ABC", "456")
        
        # Mock generic exception
        with patch('aiohttp.ClientSession', side_effect=Exception("Network error")):
            result = await bot.send_message("Test")
            assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
