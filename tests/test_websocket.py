"""
Unit tests for WebSocket layer.

Tests the WebSocket streaming functionality including:
  - Connection handling
  - Stream subscriptions
  - Message parsing
  - Callback execution
  - Reconnection logic
"""

import asyncio
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from yunmin.core.websocket_layer import (
    WebSocketLayer,
    KlineUpdateEvent,
    TradeUpdateEvent,
    TickerUpdateEvent,
    OrderUpdateEvent,
    WebSocketEvent
)


@pytest.fixture
def ws_layer():
    """Create WebSocket layer instance for testing."""
    return WebSocketLayer(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True,
        max_reconnect_attempts=3,
        reconnect_delay=0.1  # Fast reconnection for tests
    )


def test_websocket_layer_initialization(ws_layer):
    """Test WebSocket layer initialization."""
    assert ws_layer.api_key == "test_key"
    assert ws_layer.api_secret == "test_secret"
    assert ws_layer.testnet is True
    assert ws_layer.max_reconnect_attempts == 3
    assert ws_layer.reconnect_delay == 0.1
    assert ws_layer.is_running is False
    assert len(ws_layer.subscribed_streams) == 0


def test_kline_event_parsing():
    """Test parsing of Binance kline data."""
    data = {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1699545600000,
            "T": 1699545900000,
            "s": "BTCUSDT",
            "i": "5m",
            "o": "103500.00",
            "h": "103600.00",
            "l": "103400.00",
            "c": "103550.00",
            "v": "150.5",
            "q": "15556275.0",
            "x": True
        }
    }
    
    event = KlineUpdateEvent.from_binance_kline(data)
    
    assert event.symbol == "BTCUSDT"
    assert event.timeframe == "5m"
    assert event.open == 103500.00
    assert event.high == 103600.00
    assert event.low == 103400.00
    assert event.close == 103550.00
    assert event.volume == 150.5
    assert event.is_final is True


def test_trade_event_parsing():
    """Test parsing of Binance trade data."""
    data = {
        "e": "trade",
        "s": "BTCUSDT",
        "p": "103550.25",
        "q": "0.05",
        "T": 1699545700000,
        "m": False
    }
    
    event = TradeUpdateEvent.from_binance_trade(data)
    
    assert event.symbol == "BTCUSDT"
    assert event.price == 103550.25
    assert event.quantity == 0.05
    assert event.is_buyer_maker is False
    assert isinstance(event.timestamp, datetime)


def test_ticker_event_parsing():
    """Test parsing of Binance ticker data."""
    data = {
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "103550.00",
        "p": "500.00",
        "P": "0.48",
        "v": "10000.5",
        "q": "1035550000.0",
        "E": 1699545700000
    }
    
    event = TickerUpdateEvent.from_binance_ticker(data)
    
    assert event.symbol == "BTCUSDT"
    assert event.price == 103550.00
    assert event.price_change == 500.00
    assert event.price_change_pct == 0.48
    assert event.volume == 10000.5
    assert isinstance(event.timestamp, datetime)


def test_register_callbacks(ws_layer):
    """Test callback registration."""
    kline_callback = Mock()
    trade_callback = Mock()
    ticker_callback = Mock()
    error_callback = Mock()
    
    ws_layer.register_kline_callback(kline_callback)
    ws_layer.register_trade_callback(trade_callback)
    ws_layer.register_ticker_callback(ticker_callback)
    ws_layer.register_error_callback(error_callback)
    
    assert kline_callback in ws_layer.kline_callbacks
    assert trade_callback in ws_layer.trade_callbacks
    assert ticker_callback in ws_layer.ticker_callbacks
    assert error_callback in ws_layer.error_callbacks


@pytest.mark.asyncio
async def test_subscribe_kline(ws_layer):
    """Test kline stream subscription."""
    await ws_layer.subscribe_kline("BTCUSDT", "5m")
    
    assert "kline_BTCUSDT_5m" in ws_layer.subscribed_streams
    assert ws_layer.subscribed_streams["kline_BTCUSDT_5m"] == "btcusdt@kline_5m"


@pytest.mark.asyncio
async def test_subscribe_trades(ws_layer):
    """Test trade stream subscription."""
    await ws_layer.subscribe_trades("BTCUSDT")
    
    assert "trade_BTCUSDT" in ws_layer.subscribed_streams
    assert ws_layer.subscribed_streams["trade_BTCUSDT"] == "btcusdt@trade"


@pytest.mark.asyncio
async def test_subscribe_ticker(ws_layer):
    """Test ticker stream subscription."""
    await ws_layer.subscribe_ticker("BTCUSDT")
    
    assert "ticker_BTCUSDT" in ws_layer.subscribed_streams
    assert ws_layer.subscribed_streams["ticker_BTCUSDT"] == "btcusdt@ticker"


@pytest.mark.asyncio
async def test_kline_callback_execution(ws_layer):
    """Test that kline callbacks are executed."""
    callback_called = asyncio.Event()
    received_event = None
    
    async def kline_callback(event: KlineUpdateEvent):
        nonlocal received_event
        received_event = event
        callback_called.set()
    
    ws_layer.register_kline_callback(kline_callback)
    
    # Simulate kline message
    message = json.dumps({
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1699545600000,
            "T": 1699545900000,
            "s": "BTCUSDT",
            "i": "5m",
            "o": "103500.00",
            "h": "103600.00",
            "l": "103400.00",
            "c": "103550.00",
            "v": "150.5",
            "q": "15556275.0",
            "x": True
        }
    })
    
    await ws_layer._handle_message(message)
    
    # Wait for callback with timeout
    try:
        await asyncio.wait_for(callback_called.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Callback was not called")
    
    assert received_event is not None
    assert received_event.symbol == "BTCUSDT"
    assert received_event.close == 103550.00


@pytest.mark.asyncio
async def test_trade_callback_execution(ws_layer):
    """Test that trade callbacks are executed."""
    callback_called = asyncio.Event()
    received_event = None
    
    async def trade_callback(event: TradeUpdateEvent):
        nonlocal received_event
        received_event = event
        callback_called.set()
    
    ws_layer.register_trade_callback(trade_callback)
    
    # Simulate trade message
    message = json.dumps({
        "e": "trade",
        "s": "BTCUSDT",
        "p": "103550.25",
        "q": "0.05",
        "T": 1699545700000,
        "m": False
    })
    
    await ws_layer._handle_message(message)
    
    # Wait for callback with timeout
    try:
        await asyncio.wait_for(callback_called.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Callback was not called")
    
    assert received_event is not None
    assert received_event.symbol == "BTCUSDT"
    assert received_event.price == 103550.25


@pytest.mark.asyncio
async def test_ticker_callback_execution(ws_layer):
    """Test that ticker callbacks are executed."""
    callback_called = asyncio.Event()
    received_event = None
    
    async def ticker_callback(event: TickerUpdateEvent):
        nonlocal received_event
        received_event = event
        callback_called.set()
    
    ws_layer.register_ticker_callback(ticker_callback)
    
    # Simulate ticker message
    message = json.dumps({
        "e": "24hrTicker",
        "s": "BTCUSDT",
        "c": "103550.00",
        "p": "500.00",
        "P": "0.48",
        "v": "10000.5",
        "q": "1035550000.0",
        "E": 1699545700000
    })
    
    await ws_layer._handle_message(message)
    
    # Wait for callback with timeout
    try:
        await asyncio.wait_for(callback_called.wait(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Callback was not called")
    
    assert received_event is not None
    assert received_event.symbol == "BTCUSDT"
    assert received_event.price == 103550.00


@pytest.mark.asyncio
async def test_invalid_json_handling(ws_layer):
    """Test handling of invalid JSON messages."""
    error_called = asyncio.Event()
    
    async def error_callback(error: Exception):
        error_called.set()
    
    ws_layer.register_error_callback(error_callback)
    
    # Send invalid JSON (should not raise exception)
    await ws_layer._handle_message("invalid json {{{")
    
    # Should not crash, error callback may or may not be called
    # depending on implementation


@pytest.mark.asyncio
async def test_reconnection_logic(ws_layer):
    """Test reconnection with exponential backoff."""
    ws_layer.reconnect_count = 0
    
    # Test successful reconnection within limits
    result = await ws_layer._reconnect()
    assert result is True
    assert ws_layer.reconnect_count == 1
    
    # Test max reconnection attempts
    ws_layer.reconnect_count = ws_layer.max_reconnect_attempts
    result = await ws_layer._reconnect()
    assert result is False
    assert ws_layer.is_running is False


def test_multiple_stream_subscriptions(ws_layer):
    """Test subscribing to multiple streams."""
    asyncio.run(ws_layer.subscribe_kline("BTCUSDT", "5m"))
    asyncio.run(ws_layer.subscribe_kline("ETHUSDT", "5m"))
    asyncio.run(ws_layer.subscribe_trades("BTCUSDT"))
    asyncio.run(ws_layer.subscribe_ticker("BTCUSDT"))
    
    assert len(ws_layer.subscribed_streams) == 4
    assert "kline_BTCUSDT_5m" in ws_layer.subscribed_streams
    assert "kline_ETHUSDT_5m" in ws_layer.subscribed_streams
    assert "trade_BTCUSDT" in ws_layer.subscribed_streams
    assert "ticker_BTCUSDT" in ws_layer.subscribed_streams


@pytest.mark.asyncio
async def test_sync_callback_support(ws_layer):
    """Test that both sync and async callbacks are supported."""
    sync_called = False
    async_called = False
    
    def sync_callback(event: KlineUpdateEvent):
        nonlocal sync_called
        sync_called = True
    
    async def async_callback(event: KlineUpdateEvent):
        nonlocal async_called
        async_called = True
    
    ws_layer.register_kline_callback(sync_callback)
    ws_layer.register_kline_callback(async_callback)
    
    # Simulate kline message
    message = json.dumps({
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1699545600000,
            "T": 1699545900000,
            "s": "BTCUSDT",
            "i": "5m",
            "o": "103500.00",
            "h": "103600.00",
            "l": "103400.00",
            "c": "103550.00",
            "v": "150.5",
            "q": "15556275.0",
            "x": True
        }
    })
    
    await ws_layer._handle_message(message)
    
    # Give callbacks time to execute
    await asyncio.sleep(0.1)
    
    assert sync_called is True
    assert async_called is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
