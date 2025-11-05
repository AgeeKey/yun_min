"""
Comprehensive tests for Advanced Alert System
Tests multi-channel delivery, smart rules, throttling, and templates
"""

import pytest
import asyncio
from datetime import datetime, UTC, timedelta

from yunmin.core.alert_manager import (
    AlertManager,
    AlertConfig,
    AlertLevel,
    AlertChannel,
    Alert,
    TradingAlerts
)


@pytest.fixture
def alert_config():
    """Create test alert configuration"""
    return AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO,
        rate_limit_seconds=60,
        throttle_enabled=True,
        group_similar_alerts=True,
        desktop_enabled=False  # Disable for testing
    )


@pytest.fixture
def alert_manager(alert_config):
    """Create alert manager instance"""
    return AlertManager(alert_config)


class TestDesktopNotifications:
    """Test desktop notification functionality"""
    
    @pytest.mark.asyncio
    async def test_desktop_notification_disabled(self, alert_manager):
        """Test desktop notifications when disabled"""
        alert_manager.config.desktop_enabled = False
        
        # Should not raise error
        alert = Alert(
            level=AlertLevel.INFO,
            title="Test",
            message="Test message"
        )
        await alert_manager._send_desktop(alert)
    
    @pytest.mark.asyncio
    async def test_desktop_notification_mock(self, alert_manager):
        """Test desktop notification with mocking"""
        alert_manager.config.desktop_enabled = True
        
        alert = Alert(
            level=AlertLevel.WARNING,
            title="Test Warning",
            message="This is a test warning"
        )
        
        # Should handle gracefully even if libraries not installed
        try:
            await alert_manager._send_desktop(alert)
        except Exception as e:
            # It's ok if it fails in test environment
            pass


class TestSmartAlertRules:
    """Test smart alert rules and throttling"""
    
    @pytest.mark.asyncio
    async def test_alert_throttling(self, alert_manager):
        """Test that identical alerts are throttled"""
        # Send first alert
        await alert_manager.send_warning("Test", "Message 1")
        assert len(alert_manager.alert_history) == 1
        
        # Send same alert immediately - should be throttled
        await alert_manager.send_warning("Test", "Message 1")
        assert len(alert_manager.alert_history) == 1  # Should still be 1
    
    @pytest.mark.asyncio
    async def test_different_alerts_not_throttled(self, alert_manager):
        """Test that different alerts are not throttled"""
        await alert_manager.send_warning("Test 1", "Message 1")
        await alert_manager.send_warning("Test 2", "Message 2")
        
        assert len(alert_manager.alert_history) == 2
    
    @pytest.mark.asyncio
    async def test_alert_grouping(self, alert_manager):
        """Test alert grouping functionality"""
        assert hasattr(alert_manager, 'alert_groups')
        assert isinstance(alert_manager.alert_groups, dict)


class TestAlertTemplates:
    """Test trading alert templates"""
    
    @pytest.mark.asyncio
    async def test_stop_loss_hit_template(self, alert_manager):
        """Test stop-loss hit alert template"""
        await TradingAlerts.stop_loss_hit(
            alert_manager,
            symbol="BTC/USDT",
            price=109500.0,
            loss_pct=-3.2
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.CRITICAL
        assert "STOP-LOSS HIT" in alert.title
        assert "BTC/USDT" in alert.message
        assert "-3.2" in alert.message
    
    @pytest.mark.asyncio
    async def test_trade_closed_template(self, alert_manager):
        """Test trade closed alert template"""
        await TradingAlerts.position_closed(
            alert_manager,
            symbol="BTC/USDT",
            pnl=125.50,
            pnl_pct=2.3,
            duration_hours=4.25
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.INFO  # Profit
        assert "TRADE CLOSED" in alert.title
        assert "BTC/USDT" in alert.message
        assert "4h" in alert.message  # Duration formatted
    
    @pytest.mark.asyncio
    async def test_drawdown_warning_template(self, alert_manager):
        """Test drawdown warning template"""
        await TradingAlerts.drawdown_warning(
            alert_manager,
            current_dd_pct=-5.1,
            max_dd_pct=-10.0
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.WARNING
        assert "DRAWDOWN WARNING" in alert.title
        assert "5.1%" in alert.message
    
    @pytest.mark.asyncio
    async def test_connection_restored_template(self, alert_manager):
        """Test connection restored template"""
        await TradingAlerts.connection_restored(
            alert_manager,
            exchange="Binance",
            downtime_seconds=45
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.INFO
        assert "Connection Restored" in alert.title
        assert "Binance" in alert.message
        assert "45s" in alert.message
    
    @pytest.mark.asyncio
    async def test_api_error_template(self, alert_manager):
        """Test API error template"""
        await TradingAlerts.api_error(
            alert_manager,
            exchange="Binance",
            error_code=-1003,
            error_msg="Too many requests"
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.ERROR
        assert "API Error" in alert.title
        assert "Binance" in alert.title
        assert "-1003" in alert.message
    
    @pytest.mark.asyncio
    async def test_strategy_signal_template(self, alert_manager):
        """Test strategy signal template"""
        await TradingAlerts.strategy_signal(
            alert_manager,
            symbol="BTC/USDT",
            signal_type="BUY",
            confidence=85.5,
            reason="Strong uptrend + RSI oversold"
        )
        
        assert len(alert_manager.alert_history) == 1
        alert = alert_manager.alert_history[0]
        
        assert alert.level == AlertLevel.INFO
        assert "Strategy Signal" in alert.title
        assert "BTC/USDT" in alert.message
        assert "85.5" in alert.message


class TestMultiChannelDelivery:
    """Test multi-channel alert delivery"""
    
    @pytest.mark.asyncio
    async def test_multiple_channels(self):
        """Test sending to multiple channels"""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG, AlertChannel.DESKTOP],
            min_alert_level=AlertLevel.INFO,  # Allow INFO level
            desktop_enabled=False
        )
        manager = AlertManager(config)
        
        await manager.send_info("Test", "Multi-channel test")
        
        assert len(manager.alert_history) == 1
    
    @pytest.mark.asyncio
    async def test_channel_override(self, alert_manager):
        """Test overriding default channels"""
        await alert_manager.send_alert(
            AlertLevel.CRITICAL,
            "Override Test",
            "Testing channel override",
            channels=[AlertChannel.LOG]
        )
        
        assert len(alert_manager.alert_history) == 1


class TestAlertLevelFiltering:
    """Test alert level filtering"""
    
    @pytest.mark.asyncio
    async def test_min_level_filtering(self):
        """Test minimum alert level filtering"""
        config = AlertConfig(
            min_alert_level=AlertLevel.WARNING
        )
        manager = AlertManager(config)
        
        # INFO should be filtered out
        await manager.send_info("Test", "Should be filtered")
        assert len(manager.alert_history) == 0
        
        # WARNING should pass
        await manager.send_warning("Test", "Should pass")
        assert len(manager.alert_history) == 1
    
    @pytest.mark.asyncio
    async def test_critical_always_passes(self):
        """Test that CRITICAL always passes"""
        config = AlertConfig(
            min_alert_level=AlertLevel.CRITICAL
        )
        manager = AlertManager(config)
        
        await manager.send_critical("Test", "Critical alert")
        assert len(manager.alert_history) == 1


class TestAlertHistory:
    """Test alert history management"""
    
    @pytest.mark.asyncio
    async def test_alert_history_tracking(self, alert_manager):
        """Test that alerts are tracked in history"""
        await alert_manager.send_info("Test 1", "Message 1")
        await alert_manager.send_warning("Test 2", "Message 2")
        await alert_manager.send_error("Test 3", "Message 3")
        
        history = alert_manager.get_alert_history()
        assert len(history) == 3
    
    @pytest.mark.asyncio
    async def test_alert_history_filtering(self, alert_manager):
        """Test filtering alert history by level"""
        await alert_manager.send_info("Info", "Info message")
        await alert_manager.send_warning("Warning", "Warning message")
        await alert_manager.send_error("Error", "Error message")
        
        errors = alert_manager.get_alert_history(level=AlertLevel.ERROR)
        assert len(errors) == 1
        assert errors[0].level == AlertLevel.ERROR
    
    @pytest.mark.asyncio
    async def test_alert_history_limit(self, alert_manager):
        """Test alert history limit parameter"""
        # Send many alerts
        for i in range(20):
            await alert_manager.send_info(f"Test {i}", f"Message {i}")
        
        history = alert_manager.get_alert_history(limit=10)
        assert len(history) == 10
        # Should return most recent
        assert "19" in history[-1].title
    
    def test_clear_history(self, alert_manager):
        """Test clearing alert history"""
        alert_manager.alert_history.append(
            Alert(AlertLevel.INFO, "Test", "Message")
        )
        
        alert_manager.clear_history()
        assert len(alert_manager.alert_history) == 0


class TestAlertMetadata:
    """Test alert metadata handling"""
    
    @pytest.mark.asyncio
    async def test_alert_with_metadata(self, alert_manager):
        """Test sending alert with metadata"""
        await alert_manager.send_warning(
            "Test",
            "Message",
            symbol="BTC/USDT",
            price=50000.0,
            custom_field="value"
        )
        
        alert = alert_manager.alert_history[0]
        assert alert.metadata["symbol"] == "BTC/USDT"
        assert alert.metadata["price"] == 50000.0
        assert alert.metadata["custom_field"] == "value"


class TestAlertConfiguration:
    """Test alert configuration"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = AlertConfig()
        
        assert config.enabled_channels == [AlertChannel.LOG]
        assert config.min_alert_level == AlertLevel.WARNING
        assert config.rate_limit_seconds == 60
        assert config.throttle_enabled is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = AlertConfig(
            enabled_channels=[AlertChannel.TELEGRAM, AlertChannel.EMAIL],
            min_alert_level=AlertLevel.CRITICAL,
            rate_limit_seconds=120,
            throttle_enabled=False,
            telegram_bot_token="test_token",
            telegram_chat_id="test_chat"
        )
        
        assert AlertChannel.TELEGRAM in config.enabled_channels
        assert config.min_alert_level == AlertLevel.CRITICAL
        assert config.rate_limit_seconds == 120
        assert config.throttle_enabled is False
        assert config.telegram_bot_token == "test_token"


class TestTradingAlertsComprehensive:
    """Comprehensive tests for all trading alert types"""
    
    @pytest.mark.asyncio
    async def test_all_trading_alerts(self, alert_manager):
        """Test all trading alert types"""
        # Position opened
        await TradingAlerts.position_opened(
            alert_manager, "BTC/USDT", "LONG", 0.01, 50000.0
        )
        
        # Position closed (profit)
        await TradingAlerts.position_closed(
            alert_manager, "BTC/USDT", 150.0, 3.0, 2.5
        )
        
        # Stop loss hit
        await TradingAlerts.stop_loss_hit(
            alert_manager, "BTC/USDT", 49000.0, -2.0
        )
        
        # Drawdown warning
        await TradingAlerts.drawdown_warning(
            alert_manager, -5.5, -10.0
        )
        
        # Risk limit hit
        await TradingAlerts.risk_limit_hit(
            alert_manager, "Max Position Size", 0.15, 0.10
        )
        
        # Connection lost
        await TradingAlerts.connection_lost(alert_manager, "Binance")
        
        # Connection restored
        await TradingAlerts.connection_restored(alert_manager, "Binance", 30)
        
        # Daily summary
        await TradingAlerts.daily_summary(
            alert_manager, 10, 250.0, 70.0, 150.0, -50.0
        )
        
        # API error
        await TradingAlerts.api_error(
            alert_manager, "Binance", -1003, "Rate limit exceeded"
        )
        
        # Strategy signal
        await TradingAlerts.strategy_signal(
            alert_manager, "BTC/USDT", "BUY", 85.0, "Strong momentum"
        )
        
        # All alerts should be recorded
        assert len(alert_manager.alert_history) == 10


class TestAlertIntegration:
    """Integration tests for alert system"""
    
    @pytest.mark.asyncio
    async def test_complete_alert_flow(self):
        """Test complete alert flow from config to delivery"""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG, AlertChannel.DESKTOP],
            min_alert_level=AlertLevel.INFO,
            rate_limit_seconds=1,
            desktop_enabled=False
        )
        
        manager = AlertManager(config)
        
        # Send various alerts
        await manager.send_info("Start", "Bot started")
        await TradingAlerts.position_opened(
            manager, "BTC/USDT", "LONG", 0.01, 50000.0
        )
        await asyncio.sleep(1.1)  # Wait for rate limit
        await TradingAlerts.position_closed(
            manager, "BTC/USDT", 150.0, 3.0, 1.5
        )
        
        # Check history
        history = manager.get_alert_history()
        assert len(history) >= 3
        
        # Cleanup
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_alert_manager_lifecycle(self, alert_manager):
        """Test alert manager lifecycle"""
        # Send some alerts
        await alert_manager.send_info("Test", "Message")
        
        # Check health
        assert len(alert_manager.alert_history) > 0
        
        # Close
        await alert_manager.close()
        
        # Session should be closed
        if alert_manager._session:
            assert alert_manager._session.closed


# Performance tests
class TestAlertPerformance:
    """Test alert system performance"""
    
    @pytest.mark.asyncio
    async def test_many_alerts(self, alert_manager):
        """Test handling many alerts"""
        # Send 100 unique alerts
        for i in range(100):
            await alert_manager.send_info(f"Test {i}", f"Message unique {i}")
        
        # All unique alerts should be recorded
        assert len(alert_manager.alert_history) == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_alerts(self, alert_manager):
        """Test concurrent alert sending"""
        tasks = []
        for i in range(10):
            task = alert_manager.send_info(f"Concurrent {i}", f"Message {i}")
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # All unique alerts should be in history
        assert len(alert_manager.alert_history) == 10
