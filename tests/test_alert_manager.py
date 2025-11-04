"""
Tests for Alert Manager
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from yunmin.core.alert_manager import (
    AlertManager,
    AlertConfig,
    AlertLevel,
    AlertChannel,
    Alert,
    TradingAlerts
)


# ==================== AlertConfig Tests ====================

def test_alert_config_defaults():
    """Test default configuration"""
    config = AlertConfig()
    
    assert AlertChannel.LOG in config.enabled_channels
    assert config.min_alert_level == AlertLevel.WARNING
    assert config.rate_limit_seconds == 60


def test_alert_config_telegram():
    """Test Telegram configuration"""
    config = AlertConfig(
        telegram_bot_token="123456:ABC",
        telegram_chat_id="789",
        enabled_channels=[AlertChannel.TELEGRAM]
    )
    
    assert config.telegram_bot_token == "123456:ABC"
    assert config.telegram_chat_id == "789"
    assert AlertChannel.TELEGRAM in config.enabled_channels


# ==================== Alert Tests ====================

def test_alert_creation():
    """Test alert creation"""
    alert = Alert(
        level=AlertLevel.WARNING,
        title="Test Alert",
        message="This is a test"
    )
    
    assert alert.level == AlertLevel.WARNING
    assert alert.title == "Test Alert"
    assert "WARNING" in str(alert)


# ==================== AlertManager Tests ====================

@pytest.mark.asyncio
async def test_alert_manager_send_log():
    """Test sending to log channel"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await manager.send_info("Test", "Log message")
    
    assert len(manager.alert_history) == 1
    assert manager.alert_history[0].title == "Test"
    
    await manager.close()


@pytest.mark.asyncio
async def test_alert_manager_level_filtering():
    """Test alert level filtering"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.ERROR
    )
    manager = AlertManager(config)
    
    # Should be filtered out
    await manager.send_info("Info", "Should be filtered")
    await manager.send_warning("Warning", "Should be filtered")
    
    # Should pass
    await manager.send_error("Error", "Should pass")
    await manager.send_critical("Critical", "Should pass")
    
    assert len(manager.alert_history) == 2
    assert manager.alert_history[0].level == AlertLevel.ERROR
    assert manager.alert_history[1].level == AlertLevel.CRITICAL
    
    await manager.close()


@pytest.mark.asyncio
async def test_alert_manager_rate_limiting():
    """Test rate limiting"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO,
        rate_limit_seconds=1
    )
    manager = AlertManager(config)
    
    # First alert should go through
    await manager.send_info("Test", "Message 1")
    assert len(manager.alert_history) == 1
    
    # Immediate second alert should be rate limited
    await manager.send_info("Test", "Message 1")
    assert len(manager.alert_history) == 1
    
    # Different message should go through
    await manager.send_info("Test", "Message 2")
    assert len(manager.alert_history) == 2
    
    await manager.close()


@pytest.mark.asyncio
async def test_alert_manager_telegram():
    """Test Telegram delivery"""
    config = AlertConfig(
        telegram_bot_token="test_token",
        telegram_chat_id="test_chat",
        enabled_channels=[AlertChannel.TELEGRAM],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    # Mock aiohttp session
    with patch.object(manager, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        
        mock_post = AsyncMock(return_value=mock_response)
        mock_session.return_value.post = mock_post
        
        await manager.send_warning("Test Telegram", "This is a test alert")
        
        # Verify Telegram API was called
        assert mock_post.called
        call_args = mock_post.call_args
        assert "sendMessage" in call_args[0][0]
    
    await manager.close()


@pytest.mark.asyncio
async def test_alert_manager_webhook():
    """Test Webhook delivery"""
    config = AlertConfig(
        webhook_url="https://example.com/webhook",
        webhook_headers={"Authorization": "Bearer test"},
        enabled_channels=[AlertChannel.WEBHOOK],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    # Mock aiohttp session
    with patch.object(manager, '_get_session') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()
        
        mock_post = AsyncMock(return_value=mock_response)
        mock_session.return_value.post = mock_post
        
        await manager.send_error("Test Webhook", "Webhook alert test")
        
        # Verify webhook was called
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[0][0] == config.webhook_url
    
    await manager.close()


def test_alert_history():
    """Test alert history management"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    # Add alerts
    for i in range(5):
        manager.alert_history.append(Alert(
            level=AlertLevel.INFO if i < 3 else AlertLevel.ERROR,
            title=f"Alert {i}",
            message=f"Message {i}"
        ))
    
    # Get all history
    history = manager.get_alert_history()
    assert len(history) == 5
    
    # Get filtered by level
    errors = manager.get_alert_history(level=AlertLevel.ERROR)
    assert len(errors) == 2
    
    # Get limited
    recent = manager.get_alert_history(limit=3)
    assert len(recent) == 3


def test_alert_history_clear():
    """Test clearing alert history"""
    config = AlertConfig(enabled_channels=[AlertChannel.LOG])
    manager = AlertManager(config)
    
    manager.alert_history.append(Alert(
        level=AlertLevel.INFO,
        title="Test",
        message="Message"
    ))
    
    assert len(manager.alert_history) == 1
    
    manager.clear_history()
    assert len(manager.alert_history) == 0


# ==================== TradingAlerts Tests ====================

@pytest.mark.asyncio
async def test_position_opened_alert():
    """Test position opened alert"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.position_opened(
        manager,
        symbol="BTC/USDT",
        side="LONG",
        amount=0.01,
        price=50000.0
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.INFO
    assert "Position Opened" in alert.title
    assert "BTC/USDT" in alert.message
    
    await manager.close()


@pytest.mark.asyncio
async def test_position_closed_alert_profit():
    """Test position closed with profit"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.position_closed(
        manager,
        symbol="ETH/USDT",
        pnl=150.0,
        pnl_pct=3.0
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.INFO  # Profit = INFO
    assert "Position Closed" in alert.title
    
    await manager.close()


@pytest.mark.asyncio
async def test_position_closed_alert_loss():
    """Test position closed with loss"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.position_closed(
        manager,
        symbol="BNB/USDT",
        pnl=-75.0,
        pnl_pct=-1.5
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.WARNING  # Loss = WARNING
    
    await manager.close()


@pytest.mark.asyncio
async def test_risk_limit_hit_alert():
    """Test risk limit hit alert"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.risk_limit_hit(
        manager,
        limit_type="Max Position Size",
        current=5000.0,
        max_allowed=4000.0
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.ERROR
    assert "Risk Limit" in alert.title
    
    await manager.close()


@pytest.mark.asyncio
async def test_connection_lost_alert():
    """Test connection lost alert"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.connection_lost(
        manager,
        exchange="Binance"
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.CRITICAL
    assert "Connection Lost" in alert.title
    
    await manager.close()


@pytest.mark.asyncio
async def test_daily_summary_alert():
    """Test daily summary alert"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await TradingAlerts.daily_summary(
        manager,
        trades=25,
        pnl=450.0,
        win_rate=60.0,
        largest_win=200.0,
        largest_loss=-75.0
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.level == AlertLevel.INFO
    assert "Daily Summary" in alert.title
    assert "25" in alert.message  # trades count
    
    await manager.close()


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_multi_channel_delivery():
    """Test sending to multiple channels"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    await manager.send_alert(
        AlertLevel.ERROR,
        "Multi-channel Test",
        "Testing multiple channels",
        channels=[AlertChannel.LOG]
    )
    
    assert len(manager.alert_history) == 1
    
    await manager.close()


@pytest.mark.asyncio
async def test_alert_with_metadata():
    """Test alert with metadata"""
    config = AlertConfig(
        enabled_channels=[AlertChannel.LOG],
        min_alert_level=AlertLevel.INFO
    )
    manager = AlertManager(config)
    
    metadata = {
        "symbol": "BTC/USDT",
        "price": 50000.0,
        "volume": 1.5
    }
    
    await manager.send_info(
        "Metadata Test",
        "Testing metadata",
        **metadata
    )
    
    assert len(manager.alert_history) == 1
    alert = manager.alert_history[0]
    assert alert.metadata["symbol"] == "BTC/USDT"
    assert alert.metadata["price"] == 50000.0
    
    await manager.close()
