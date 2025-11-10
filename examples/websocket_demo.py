"""
WebSocket Demo - Real-time Market Data Streaming

Demonstrates how to use the WebSocket layer for real-time market data:
  - Kline/Candle updates (5-minute intervals)
  - Trade updates (every trade)
  - Ticker updates (24hr statistics)

Example usage:
    python examples/websocket_demo.py
"""

import asyncio
import logging
from datetime import datetime
from yunmin.core.websocket_layer import (
    WebSocketLayer,
    KlineUpdateEvent,
    TradeUpdateEvent,
    TickerUpdateEvent
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketDemo:
    """Demonstration of WebSocket streaming capabilities."""
    
    def __init__(self, symbol: str = "BTCUSDT", testnet: bool = True):
        """
        Initialize demo.
        
        Args:
            symbol: Trading pair to monitor
            testnet: Use testnet (True) or mainnet (False)
        """
        self.symbol = symbol
        self.testnet = testnet
        
        # Statistics
        self.trade_count = 0
        self.kline_count = 0
        self.ticker_count = 0
        self.last_price = 0.0
        
    async def on_kline_update(self, event: KlineUpdateEvent):
        """
        Handle kline/candle updates.
        
        Args:
            event: Kline update event
        """
        self.kline_count += 1
        
        if event.is_final:
            logger.info(
                f"🕯️  Candle CLOSED | {event.symbol} {event.timeframe} | "
                f"O: {event.open:.2f} H: {event.high:.2f} "
                f"L: {event.low:.2f} C: {event.close:.2f} | "
                f"Vol: {event.volume:.2f}"
            )
        else:
            # Log every 10th update to avoid spam
            if self.kline_count % 10 == 0:
                logger.debug(
                    f"🕯️  Candle update #{self.kline_count} | "
                    f"{event.symbol} @ {event.close:.2f}"
                )
    
    async def on_trade_update(self, event: TradeUpdateEvent):
        """
        Handle real-time trade updates.
        
        Args:
            event: Trade update event
        """
        self.trade_count += 1
        self.last_price = event.price
        
        # Calculate price change
        if self.trade_count > 1:
            change = event.price - self.last_price
            change_pct = (change / self.last_price) * 100 if self.last_price else 0
            arrow = "🔼" if change >= 0 else "🔽"
        else:
            arrow = "💰"
            change_pct = 0
        
        # Log every 5th trade to reduce noise
        if self.trade_count % 5 == 0:
            logger.info(
                f"{arrow} Trade #{self.trade_count} | {event.symbol} | "
                f"Price: ${event.price:,.2f} | "
                f"Qty: {event.quantity:.6f} | "
                f"Change: {change_pct:+.2f}%"
            )
    
    async def on_ticker_update(self, event: TickerUpdateEvent):
        """
        Handle 24hr ticker updates.
        
        Args:
            event: Ticker update event
        """
        self.ticker_count += 1
        
        logger.info(
            f"📈 Ticker #{self.ticker_count} | {event.symbol} | "
            f"Price: ${event.price:,.2f} | "
            f"24h Change: {event.price_change:+.2f} ({event.price_change_pct:+.2f}%) | "
            f"24h Volume: {event.volume:,.2f}"
        )
    
    async def run(self, duration_seconds: int = 30):
        """
        Run demo for specified duration.
        
        Args:
            duration_seconds: How long to run (default: 30 seconds)
        """
        logger.info("=" * 70)
        logger.info(f"WebSocket Demo - Monitoring {self.symbol}")
        logger.info(f"Mode: {'Testnet' if self.testnet else 'Mainnet'}")
        logger.info(f"Duration: {duration_seconds} seconds")
        logger.info("=" * 70)
        
        # Initialize WebSocket layer
        # Note: API key/secret not required for public market data streams
        ws_layer = WebSocketLayer(
            api_key="",
            api_secret="",
            testnet=self.testnet,
            max_reconnect_attempts=3,
            reconnect_delay=1.0
        )
        
        # Register callbacks
        ws_layer.register_kline_callback(self.on_kline_update)
        ws_layer.register_trade_callback(self.on_trade_update)
        ws_layer.register_ticker_callback(self.on_ticker_update)
        
        # Subscribe to streams
        await ws_layer.subscribe_kline(self.symbol, "5m")
        await ws_layer.subscribe_trades(self.symbol)
        await ws_layer.subscribe_ticker(self.symbol)
        
        logger.info("✅ Subscribed to all streams, starting...")
        
        # Run WebSocket in background
        ws_task = asyncio.create_task(ws_layer.run())
        
        try:
            # Wait for specified duration
            await asyncio.sleep(duration_seconds)
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Interrupted by user")
        
        finally:
            # Stop WebSocket
            logger.info("Closing WebSocket connection...")
            await ws_layer.close()
            
            # Cancel WebSocket task
            ws_task.cancel()
            try:
                await ws_task
            except asyncio.CancelledError:
                pass
            
            # Print statistics
            logger.info("=" * 70)
            logger.info("Demo Statistics:")
            logger.info(f"  • Kline updates: {self.kline_count}")
            logger.info(f"  • Trade updates: {self.trade_count}")
            logger.info(f"  • Ticker updates: {self.ticker_count}")
            logger.info(f"  • Last price: ${self.last_price:,.2f}")
            logger.info("=" * 70)


async def main():
    """Main entry point."""
    # Create demo
    demo = WebSocketDemo(
        symbol="BTCUSDT",
        testnet=False  # Use mainnet for real data
    )
    
    # Run for 30 seconds
    await demo.run(duration_seconds=30)


if __name__ == "__main__":
    # Run demo
    asyncio.run(main())
