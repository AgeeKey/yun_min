"""
WebSocket layer for Binance real-time order updates and candle streams.

Adapted from Hummingbot patterns (Apache-2.0):
  - hummingbot/connector/exchange_base.py
  - hummingbot/core/event_forwarder.py

Provides:
  - User data stream (order fills, position updates)
  - Kline stream (candle updates for multi-timeframe strategies)
  - Event-driven architecture with callbacks
  - Automatic reconnection and health monitoring
  - Message queueing for async processing
"""

import asyncio
import json
import logging
from typing import Dict, List, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

try:
    import aiohttp
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

logger = logging.getLogger(__name__)


class WebSocketEvent(Enum):
    """WebSocket event types."""
    ORDER_UPDATE = "ORDER_UPDATE"           # Order fill/cancel event
    KLINE_UPDATE = "KLINE_UPDATE"           # Candle update
    ORDER_REJECTED = "ORDER_REJECTED"       # Order rejected
    ORDER_CANCELLED = "ORDER_CANCELLED"     # Order cancelled
    POSITION_UPDATE = "POSITION_UPDATE"     # Position changed
    BALANCE_UPDATE = "BALANCE_UPDATE"       # Balance changed
    CONNECTION_OPENED = "CONNECTION_OPENED"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"
    RECONNECTING = "RECONNECTING"


@dataclass
class OrderUpdateEvent:
    """Order update event from user data stream."""
    client_order_id: str
    exchange_order_id: str
    symbol: str
    side: str  # BUY or SELL
    order_type: str
    quantity: float
    price: float
    status: str  # NEW, PARTIALLY_FILLED, FILLED, CANCELLED
    filled_qty: float
    filled_value: float  # Total value filled
    commission: float
    commission_asset: str
    ts: datetime
    
    @classmethod
    def from_binance_update(cls, data: Dict) -> "OrderUpdateEvent":
        """Parse Binance user data stream update."""
        return cls(
            client_order_id=data.get("c", ""),
            exchange_order_id=str(data.get("i", "")),
            symbol=data.get("s", ""),
            side=data.get("S", ""),
            order_type=data.get("o", ""),
            quantity=float(data.get("q", 0)),
            price=float(data.get("p", 0)),
            status=data.get("X", ""),
            filled_qty=float(data.get("z", 0)),
            filled_value=float(data.get("Z", 0)),
            commission=float(data.get("n", 0)),
            commission_asset=data.get("N", "USDT"),
            ts=datetime.utcfromtimestamp(data.get("T", 0) / 1000)
        )


@dataclass
class KlineUpdateEvent:
    """Kline (candle) update event."""
    symbol: str
    timeframe: str  # 1m, 5m, 15m, 1h, etc.
    ts_open: datetime
    ts_close: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    is_final: bool  # True if candle is closed
    
    @classmethod
    def from_binance_kline(cls, data: Dict) -> "KlineUpdateEvent":
        """Parse Binance kline stream update."""
        k = data.get("k", {})
        return cls(
            symbol=data.get("s", ""),
            timeframe=k.get("i", ""),
            ts_open=datetime.utcfromtimestamp(k.get("t", 0) / 1000),
            ts_close=datetime.utcfromtimestamp(k.get("T", 0) / 1000),
            open=float(k.get("o", 0)),
            high=float(k.get("h", 0)),
            low=float(k.get("l", 0)),
            close=float(k.get("c", 0)),
            volume=float(k.get("v", 0)),
            quote_volume=float(k.get("q", 0)),
            is_final=k.get("x", False)
        )


@dataclass
class TradeUpdateEvent:
    """Trade update event."""
    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool  # True if the buyer is the market maker
    
    @classmethod
    def from_binance_trade(cls, data: Dict) -> "TradeUpdateEvent":
        """Parse Binance trade stream update."""
        return cls(
            symbol=data.get("s", ""),
            price=float(data.get("p", 0)),
            quantity=float(data.get("q", 0)),
            timestamp=datetime.utcfromtimestamp(data.get("T", 0) / 1000),
            is_buyer_maker=data.get("m", False)
        )


@dataclass
class TickerUpdateEvent:
    """24hr ticker update event."""
    symbol: str
    price: float
    price_change: float
    price_change_pct: float
    volume: float
    quote_volume: float
    timestamp: datetime
    
    @classmethod
    def from_binance_ticker(cls, data: Dict) -> "TickerUpdateEvent":
        """Parse Binance 24hr ticker stream update."""
        return cls(
            symbol=data.get("s", ""),
            price=float(data.get("c", 0)),
            price_change=float(data.get("p", 0)),
            price_change_pct=float(data.get("P", 0)),
            volume=float(data.get("v", 0)),
            quote_volume=float(data.get("q", 0)),
            timestamp=datetime.utcfromtimestamp(data.get("E", 0) / 1000)
        )


class WebSocketLayer:
    """
    Real-time WebSocket layer for Binance.
    
    Handles:
      - User data stream (order fills, position updates)
      - Kline streams (candles for multiple symbols/timeframes)
      - Event callbacks to OrderTracker and RouteManager
      - Automatic reconnection
      - Health monitoring
    
    Usage:
        layer = WebSocketLayer(
            api_key="key",
            api_secret="secret",
            testnet=True
        )
        
        # Register callbacks
        layer.register_order_update_callback(on_order_update)
        layer.register_kline_callback(on_kline)
        
        # Start streams
        await layer.subscribe_user_data()
        await layer.subscribe_kline("BTCUSDT", "1m")
        
        # Run event loop (blocking)
        await layer.run()
    """
    
    # Binance WebSocket URLs
    TESTNET_BASE = "wss://stream.testnet.binance.vision/ws"
    MAINNET_BASE = "wss://stream.binance.com:9443/ws"
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0
    ):
        """
        Initialize WebSocket layer.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet (True) or mainnet (False)
            max_reconnect_attempts: Max reconnection attempts
            reconnect_delay: Base delay for exponential backoff (seconds)
        """
        if not HAS_WS:
            raise ImportError("websockets or aiohttp not installed")
            
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = self.TESTNET_BASE if testnet else self.MAINNET_BASE
        
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        
        # Event callbacks
        self.order_update_callbacks: List[Callable] = []
        self.kline_callbacks: List[Callable] = []
        self.trade_callbacks: List[Callable] = []
        self.ticker_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # Connection management
        self.ws_connection = None
        self.listen_key = None
        self.listen_key_refresh_task = None
        self.reconnect_count = 0
        self.is_running = False
        
        # Message queue for async processing
        self.message_queue = asyncio.Queue()
        self.subscribed_streams: Dict[str, str] = {}  # stream_name -> stream_id
        
        logger.info(f"WebSocketLayer initialized (testnet={testnet})")
    
    def register_order_update_callback(self, callback: Callable[[OrderUpdateEvent], None]):
        """Register callback for order updates."""
        self.order_update_callbacks.append(callback)
        logger.debug(f"Registered order update callback: {callback.__name__}")
    
    def register_kline_callback(self, callback: Callable[[KlineUpdateEvent], None]):
        """Register callback for kline updates."""
        self.kline_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', repr(callback))
        logger.debug(f"Registered kline callback: {callback_name}")
    
    def register_trade_callback(self, callback: Callable[[TradeUpdateEvent], None]):
        """Register callback for trade updates."""
        self.trade_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', repr(callback))
        logger.debug(f"Registered trade callback: {callback_name}")
    
    def register_ticker_callback(self, callback: Callable[[TickerUpdateEvent], None]):
        """Register callback for ticker updates."""
        self.ticker_callbacks.append(callback)
        callback_name = getattr(callback, '__name__', repr(callback))
        logger.debug(f"Registered ticker callback: {callback_name}")
    
    
    def register_error_callback(self, callback: Callable[[Exception], None]):
        """Register callback for errors."""
        self.error_callbacks.append(callback)
    
    async def _get_listen_key(self) -> str:
        """
        Get user data stream listen key from REST API.
        
        Returns:
            Listen key for user data stream subscription
        """
        url = "https://testnet.binance.vision/api/v3/userDataStream" if self.testnet \
              else "https://api.binance.com/api/v3/userDataStream"
        
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        key = data.get("listenKey")
                        logger.info(f"Got listen key: {key[:8]}...")
                        return key
                    else:
                        raise Exception(f"Failed to get listen key: {resp.status}")
        except Exception as e:
            logger.error(f"Error getting listen key: {e}")
            await self._emit_error(e)
            raise
    
    async def subscribe_user_data(self):
        """
        Subscribe to user data stream (order updates, fills).
        
        Must call _get_listen_key() first to get the stream key.
        """
        try:
            self.listen_key = await self._get_listen_key()
            stream_name = f"{self.listen_key}"
            
            logger.info("Subscribing to user data stream...")
            self.subscribed_streams["user_data"] = stream_name
            
            # Start listen key refresh task (refresh every 30 minutes)
            self.listen_key_refresh_task = asyncio.create_task(self._refresh_listen_key())
            
        except Exception as e:
            logger.error(f"Failed to subscribe to user data: {e}")
            await self._emit_error(e)
    
    async def subscribe_kline(self, symbol: str, timeframe: str = "1m"):
        """
        Subscribe to kline (candle) stream.
        
        Args:
            symbol: Trading pair (BTCUSDT)
            timeframe: Candle interval (1m, 5m, 15m, 1h, etc.)
        """
        stream_name = f"{symbol.lower()}@kline_{timeframe}"
        stream_url = f"{self.base_url}/{stream_name}"
        
        logger.info(f"Subscribing to kline stream: {symbol} {timeframe}")
        self.subscribed_streams[f"kline_{symbol}_{timeframe}"] = stream_name
    
    async def subscribe_trades(self, symbol: str):
        """
        Subscribe to real-time trade stream.
        
        Args:
            symbol: Trading pair (BTCUSDT)
        
        Example:
            async def on_trade(trade):
                print(f"Trade: {trade['price']}")
            
            await ws.subscribe_trades('BTCUSDT')
        """
        stream_name = f"{symbol.lower()}@trade"
        
        logger.info(f"Subscribing to trade stream: {symbol}")
        self.subscribed_streams[f"trade_{symbol}"] = stream_name
    
    async def subscribe_ticker(self, symbol: str):
        """
        Subscribe to 24hr ticker stream.
        
        Args:
            symbol: Trading pair (BTCUSDT)
        
        Example:
            async def on_ticker(ticker):
                print(f"24hr ticker: {ticker['price']}")
            
            await ws.subscribe_ticker('BTCUSDT')
        """
        stream_name = f"{symbol.lower()}@ticker"
        
        logger.info(f"Subscribing to ticker stream: {symbol}")
        self.subscribed_streams[f"ticker_{symbol}"] = stream_name
    
    async def _refresh_listen_key(self):
        """
        Periodically refresh listen key (every 30 minutes).
        
        Binance listen keys expire after 60 minutes of inactivity,
        so we refresh every 30 minutes to be safe.
        """
        while self.is_running:
            try:
                await asyncio.sleep(1800)  # 30 minutes
                url = "https://testnet.binance.vision/api/v3/userDataStream" if self.testnet \
                      else "https://api.binance.com/api/v3/userDataStream"
                
                headers = {
                    "X-MBX-APIKEY": self.api_key
                }
                params = {"listenKey": self.listen_key}
                
                async with aiohttp.ClientSession() as session:
                    async with session.put(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            logger.debug("Listen key refreshed")
                        else:
                            logger.warning(f"Failed to refresh listen key: {resp.status}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error refreshing listen key: {e}")
    
    async def _connect_websocket(self):
        """
        Connect to WebSocket and subscribe to all streams.
        
        Returns:
            WebSocket connection
        """
        try:
            # Build stream names
            stream_names = list(self.subscribed_streams.values())
            
            if not stream_names:
                logger.warning("No streams subscribed")
                return None
            
            # Single stream vs multiple streams
            if len(stream_names) == 1:
                stream_url = f"{self.base_url}/{stream_names[0]}"
            else:
                streams_param = "/".join(stream_names)
                stream_url = f"{self.base_url}/stream?streams={streams_param}"
            
            logger.info(f"Connecting to WebSocket: {stream_url[:80]}...")
            
            ws = await websockets.connect(stream_url, ping_interval=30, ping_timeout=10)
            self.reconnect_count = 0
            logger.info("WebSocket connected successfully")
            
            await self._emit_event(WebSocketEvent.CONNECTION_OPENED)
            return ws
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            await self._emit_error(e)
            return None
    
    async def _handle_message(self, message: str):
        """
        Process incoming WebSocket message.
        
        Args:
            message: Raw JSON message from WebSocket
        """
        try:
            data = json.loads(message)
            
            # Handle user data stream updates
            if "e" in data:
                event_type = data.get("e")
                
                if event_type == "executionReport":
                    # Order update
                    event = OrderUpdateEvent.from_binance_update(data)
                    await self._emit_order_update(event)
                
                elif event_type == "kline":
                    # Kline/Candle update
                    event = KlineUpdateEvent.from_binance_kline(data)
                    await self._emit_kline_update(event)
                    
                elif event_type == "trade":
                    # Trade update
                    event = TradeUpdateEvent.from_binance_trade(data)
                    await self._emit_trade_update(event)
                
                elif event_type == "24hrTicker":
                    # Ticker update
                    event = TickerUpdateEvent.from_binance_ticker(data)
                    await self._emit_ticker_update(event)
                    
                elif event_type == "outbidEvent":
                    # Outbid notification
                    pass
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from WebSocket: {e}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._emit_error(e)
    
    async def _emit_order_update(self, event: OrderUpdateEvent):
        """Emit order update event to all registered callbacks."""
        for callback in self.order_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in order update callback: {e}")
                await self._emit_error(e)
    
    async def _emit_kline_update(self, event: KlineUpdateEvent):
        """Emit kline update event to all registered callbacks."""
        for callback in self.kline_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in kline callback: {e}")
                await self._emit_error(e)
    
    async def _emit_trade_update(self, event: TradeUpdateEvent):
        """Emit trade update event to all registered callbacks."""
        for callback in self.trade_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in trade callback: {e}")
                await self._emit_error(e)
    
    async def _emit_ticker_update(self, event: TickerUpdateEvent):
        """Emit ticker update event to all registered callbacks."""
        for callback in self.ticker_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in ticker callback: {e}")
                await self._emit_error(e)
    
    async def _emit_event(self, event: WebSocketEvent):
        """Emit connection event."""
        logger.debug(f"WebSocket event: {event.value}")
    
    async def _emit_error(self, error: Exception):
        """Emit error to callbacks."""
        for callback in self.error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error)
                else:
                    callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    async def _reconnect(self):
        """Attempt to reconnect with exponential backoff."""
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            await self._emit_error(Exception("Max reconnection attempts exceeded"))
            self.is_running = False
            return False
        
        self.reconnect_count += 1
        wait_time = self.reconnect_delay * (2 ** (self.reconnect_count - 1))
        
        logger.info(f"Reconnecting in {wait_time:.1f}s (attempt {self.reconnect_count}/{self.max_reconnect_attempts})")
        await self._emit_event(WebSocketEvent.RECONNECTING)
        
        await asyncio.sleep(wait_time)
        return True
    
    async def run(self):
        """
        Main event loop for WebSocket connection.
        
        Maintains connection, handles reconnections, processes messages.
        This is a blocking call - run it in an asyncio event loop.
        """
        if not self.subscribed_streams:
            logger.error("No streams subscribed. Call subscribe_user_data() and subscribe_kline() first")
            return
        
        self.is_running = True
        
        try:
            while self.is_running:
                try:
                    ws = await self._connect_websocket()
                    
                    if ws is None:
                        if not await self._reconnect():
                            break
                        continue
                    
                    self.ws_connection = ws
                    
                    # Listen for messages
                    async for message in ws:
                        if self.is_running:
                            await self._handle_message(message)
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed")
                    await self._emit_event(WebSocketEvent.CONNECTION_CLOSED)
                    
                    if self.is_running and not await self._reconnect():
                        break
                        
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    await self._emit_error(e)
                    
                    if self.is_running and not await self._reconnect():
                        break
        
        finally:
            await self.close()
    
    async def close(self):
        """Close WebSocket connection and cleanup."""
        logger.info("Closing WebSocket layer")
        
        self.is_running = False
        
        if self.listen_key_refresh_task:
            self.listen_key_refresh_task.cancel()
            try:
                await self.listen_key_refresh_task
            except asyncio.CancelledError:
                pass
        
        if self.ws_connection:
            await self.ws_connection.close()
        
        logger.info("WebSocket layer closed")
