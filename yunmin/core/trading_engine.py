"""
Trading Engine: Central orchestrator for live trading.

Coordinates:
  - RouteManager (strategy decisions)
  - WebSocketLayer (real-time market/order events)
  - Executor (order placement)
  - RiskManager (risk validation)
  - OrderTracker (order state)
  - BinanceConnector (API)

Architecture:
  RouteManager → Decision
              ↓
           Executor (with RiskManager)
              ↓
         BinanceConnector/OrderTracker
              ↓
         WebSocketLayer (fill events)
              ↓
         TradingEngine (event loop)

Adapted from Hummingbot:
  - hummingbot/client/hummingbot_application.py
  - hummingbot/strategy/strategy_base.py
"""

import logging
import asyncio
from typing import Optional, Dict, Callable

from yunmin.core.executor import Executor
from yunmin.core.websocket_layer import WebSocketLayer, OrderUpdateEvent, KlineUpdateEvent
from yunmin.core.order_tracker import OrderTracker
from yunmin.core.risk_manager import RiskManager
from yunmin.connectors.binance_connector import BinanceConnector

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Central command loop for live trading.
    
    Responsibilities:
      1. Run strategy decision loops (RouteManager)
      2. Process market events (klines from WebSocket)
      3. Process order updates (fills from WebSocket)
      4. Execute decisions with risk management
      5. Track positions and P&L
      6. Handle errors and reconnections
    
    Usage:
        engine = TradingEngine(
            connector=connector,
            tracker=tracker,
            risk_manager=risk_manager,
            websocket=websocket,
            executor=executor,
            symbols=["BTCUSDT", "ETHUSDT"]
        )
        
        # Start trading
        await engine.start()
    """
    
    def __init__(
        self,
        connector: BinanceConnector,
        tracker: OrderTracker,
        risk_manager: RiskManager,
        websocket: WebSocketLayer,
        executor: Executor,
        symbols: list,
        decision_interval: float = 1.0
    ):
        """
        Initialize TradingEngine.
        
        Args:
            connector: BinanceConnector instance
            tracker: OrderTracker instance
            risk_manager: RiskManager instance
            websocket: WebSocketLayer instance
            executor: Executor instance
            symbols: List of trading pairs
            decision_interval: Seconds between strategy decision calls
        """
        self.connector = connector
        self.tracker = tracker
        self.risk_manager = risk_manager
        self.websocket = websocket
        self.executor = executor
        self.symbols = symbols
        self.decision_interval = decision_interval
        
        # State
        self.is_running = False
        self.last_prices: Dict[str, float] = {}
        self.decision_callback: Optional[Callable] = None
        
        # Setup WebSocket callbacks
        self.websocket.register_order_update_callback(self._on_order_update)
        self.websocket.register_kline_callback(self._on_kline_update)
        self.websocket.register_error_callback(self._on_websocket_error)
        
        logger.info(f"TradingEngine initialized for {len(symbols)} symbols")
    
    async def start(self):
        """Start trading engine."""
        if self.is_running:
            logger.warning("TradingEngine already running")
            return
        
        self.is_running = True
        logger.info("TradingEngine starting...")
        
        try:
            # Connect WebSocket and subscribe to streams
            await self._connect_websocket()
            
            # Main event loop
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"TradingEngine error: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop trading engine."""
        logger.info("TradingEngine stopping...")
        self.is_running = False
        await self.websocket.close()
    
    async def _connect_websocket(self):
        """Connect WebSocket and subscribe to streams."""
        logger.info("Connecting WebSocket...")
        
        try:
            # Subscribe to user data stream (order fills)
            await self.websocket.subscribe_user_data()
            logger.info("Subscribed to user data stream")
            
            # Subscribe to kline streams
            for symbol in self.symbols:
                await self.websocket.subscribe_kline(symbol, "1m")
                logger.info(f"Subscribed to {symbol} 1m klines")
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
    
    async def _main_loop(self):
        """Main trading loop."""
        logger.info("Main loop started")
        
        # Start decision loop
        decision_task = asyncio.create_task(self._decision_loop())
        
        # Start WebSocket event loop
        websocket_task = asyncio.create_task(self.websocket.run())
        
        try:
            # Wait for any of them to fail
            await asyncio.gather(decision_task, websocket_task)
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            raise
    
    async def _decision_loop(self):
        """Strategy decision loop."""
        logger.info("Decision loop started")
        
        while self.is_running:
            try:
                # Call user's decision callback
                if self.decision_callback:
                    decisions = await self._call_async(
                        self.decision_callback,
                        self.last_prices,
                        self._get_positions()
                    )
                    
                    # Process decisions
                    for symbol, decision in decisions.items():
                        await self._process_decision(symbol, decision)
                
                # Sleep before next iteration
                await asyncio.sleep(self.decision_interval)
                
            except Exception as e:
                logger.error(f"Decision loop error: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_decision(self, symbol: str, decision):
        """
        Process a single trading decision.
        
        Args:
            symbol: Trading pair
            decision: Decision object from strategy
        """
        try:
            current_price = self.last_prices.get(symbol, 0)
            if current_price <= 0:
                logger.warning(f"No price available for {symbol}")
                return
            
            position = self._get_positions().get(symbol, 0)
            
            # Execute decision
            result = await self.executor.execute_decision(
                symbol=symbol,
                decision=decision,
                current_price=current_price,
                current_position=position
            )
            
            if not result.success:
                logger.warning(f"Decision execution failed: {result.error_message}")
            
        except Exception as e:
            logger.error(f"Error processing decision for {symbol}: {e}")
    
    async def _on_order_update(self, event: OrderUpdateEvent):
        """
        Handle order fill event from WebSocket.
        
        Args:
            event: OrderUpdateEvent with fill details
        """
        try:
            logger.info(
                f"Order update: {event.client_order_id} {event.status} "
                f"filled={event.cumulative_filled_qty} @ {event.last_executed_price}"
            )
            
            # Update tracker
            self.tracker.add_fill(
                client_order_id=event.client_order_id,
                qty=event.last_executed_qty,
                price=event.last_executed_price,
                fee=event.commission,
                fee_asset=event.commission_asset
            )
            
            # Update risk manager
            if event.side.upper() == "BUY":
                side = "BUY"
            else:
                side = "SELL"
            
            self.risk_manager.add_fill(
                symbol=event.symbol,
                side=side,
                qty=event.last_executed_qty,
                price=event.last_executed_price,
                commission=event.commission
            )
            
            # Log position update
            position = self._get_positions().get(event.symbol, 0)
            logger.info(f"Updated position: {event.symbol} = {position}")
            
        except Exception as e:
            logger.error(f"Error handling order update: {e}")
    
    async def _on_kline_update(self, event: KlineUpdateEvent):
        """
        Handle kline update from WebSocket.
        
        Args:
            event: KlineUpdateEvent with OHLCV data
        """
        try:
            # Update current price
            self.last_prices[event.symbol] = event.close
            
            if event.is_final:
                logger.debug(
                    f"Kline closed: {event.symbol} {event.timeframe} "
                    f"O={event.open} C={event.close} V={event.volume}"
                )
        
        except Exception as e:
            logger.error(f"Error handling kline update: {e}")
    
    async def _on_websocket_error(self, error: Exception):
        """
        Handle WebSocket error.
        
        Args:
            error: Exception from WebSocket
        """
        logger.error(f"WebSocket error: {error}")
        if self.is_running:
            logger.info("Attempting to reconnect...")
    
    def _get_positions(self) -> Dict[str, float]:
        """
        Get current positions from tracker.
        
        Returns:
            Dict of symbol -> position quantity
        """
        positions = {}
        for symbol in self.symbols:
            # Get position from risk manager
            qty = self.risk_manager.open_positions.get(symbol, 0)
            if qty != 0:
                positions[symbol] = qty
        return positions
    
    def set_decision_callback(self, callback: Callable):
        """
        Set strategy decision callback.
        
        Callback signature:
            async def strategy_decision(
                prices: Dict[str, float],
                positions: Dict[str, float]
            ) -> Dict[str, Decision]:
                # Return decisions for each symbol
                return {
                    "BTCUSDT": Decision(intent="long", confidence=0.85, ...),
                    "ETHUSDT": Decision(intent="exit", confidence=0.6, ...)
                }
        """
        self.decision_callback = callback
        logger.info("Strategy decision callback set")
    
    async def _call_async(self, func, *args, **kwargs):
        """Call async or sync function."""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback error: {e}")
            raise
    
    def get_trading_stats(self) -> Dict:
        """Get trading statistics."""
        daily_stats = self.risk_manager.get_daily_stats()
        positions = self._get_positions()
        
        return {
            "positions": positions,
            "daily_trades": daily_stats["trades_count"],
            "daily_pnl": daily_stats["net_pnl"],
            "daily_win_rate": daily_stats["win_rate"],
            "account_balance": daily_stats["balance"],
            "daily_drawdown": daily_stats["drawdown"]
        }
