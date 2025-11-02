"""
Route manager for synchronized multi-timeframe trading.

Inspired by jesse/routes patterns (MIT License).
Manages routes with per-route overrides and synchronized time steps (no look-ahead).

Data contracts:
  - Route: {exchange, symbol, timeframe, strategy_name, state}
  - State: {current_time, last_candle_close_time, position, pending_orders}
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RouteState(Enum):
    """Route execution state."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class Route:
    """
    Trading route = exchange + symbol + timeframe + strategy combination.
    
    Each route runs independently but synchronized globally on time.
    """
    exchange: str
    symbol: str
    timeframe: str
    strategy_name: str
    
    # State
    state: RouteState = RouteState.IDLE
    strategy_instance: Optional[object] = None
    
    # Overrides (per-route config)
    risk_config: Dict = field(default_factory=dict)
    order_config: Dict = field(default_factory=dict)
    
    # Runtime
    current_time: Optional[datetime] = None
    last_candle_ts: Optional[datetime] = None
    position: Optional[Dict] = None
    pending_orders: List[Dict] = field(default_factory=list)


class RouteManager:
    """
    Manages trading routes with synchronized multi-timeframe execution.
    
    Key features:
      - Multiple routes (exchange, symbol, tf, strategy) run independently
      - Global time synchronization (no look-ahead bias)
      - Per-route state and overrides
      - Formatted output (JSON-compatible)
    
    Usage:
        manager = RouteManager()
        route = manager.add_route(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="5m",
            strategy_name="ema_crossover"
        )
        enabled = manager.get_enabled_routes()
        manager.set_global_time(datetime.utcnow())
        manager.step_route(route)  # Process one candle for this route
    """
    
    def __init__(self):
        """Initialize route manager."""
        self.routes: Dict[str, Route] = {}
        self.global_time: Optional[datetime] = None  # Synchronized time for all routes
        
    def add_route(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        risk_config: Optional[Dict] = None,
        order_config: Optional[Dict] = None,
    ) -> Route:
        """
        Add a new trading route.
        
        Args:
            exchange: Exchange name (binance, kraken, etc.)
            symbol: Trading pair (BTC/USDT)
            timeframe: Candle timeframe (5m, 15m, 1h, etc.)
            strategy_name: Strategy class name
            risk_config: Override risk settings for this route
            order_config: Override order settings for this route
            
        Returns:
            Route object
        """
        route_key = f"{exchange}_{symbol}_{timeframe}_{strategy_name}"
        
        route = Route(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            risk_config=risk_config or {},
            order_config=order_config or {},
        )
        
        self.routes[route_key] = route
        logger.info(f"Route added: {route_key}")
        return route
        
    def remove_route(self, exchange: str, symbol: str, timeframe: str, strategy_name: str) -> bool:
        """Remove a route."""
        key = self._route_key(exchange, symbol, timeframe, strategy_name)
        if key in self.routes:
            del self.routes[key]
            logger.info(f"Route removed: {key}")
            return True
        return False
        
    def get_enabled_routes(self) -> List[Route]:
        """Get all enabled routes."""
        return [r for r in self.routes.values() if r.state in (RouteState.IDLE, RouteState.RUNNING)]
        
    def get_route(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        strategy_name: str
    ) -> Optional[Route]:
        """Get specific route by components."""
        key = self._route_key(exchange, symbol, timeframe, strategy_name)
        return self.routes.get(key)
        
    def set_global_time(self, dt: datetime):
        """Set global time for all routes (no look-ahead)."""
        self.global_time = dt
        
    def step_route(self, route: Route) -> bool:
        """
        Process one candle for a route.
        
        Returns:
            True if processed, False if skip (already processed this candle)
        """
        if not self.global_time:
            logger.warning("Global time not set")
            return False
            
        route.current_time = self.global_time
        
        # Skip if already processed this candle
        if route.last_candle_ts and route.last_candle_ts >= self.global_time:
            return False
            
        route.last_candle_ts = self.global_time
        return True
        
    def enable_route(self, exchange: str, symbol: str, timeframe: str, strategy_name: str):
        """Enable route for trading."""
        route = self.get_route(exchange, symbol, timeframe, strategy_name)
        if route:
            route.state = RouteState.RUNNING
            logger.info(f"Route enabled: {route.exchange}_{route.symbol}_{route.timeframe}")
            
    def disable_route(self, exchange: str, symbol: str, timeframe: str, strategy_name: str):
        """Disable route."""
        route = self.get_route(exchange, symbol, timeframe, strategy_name)
        if route:
            route.state = RouteState.PAUSED
            logger.info(f"Route disabled: {route.exchange}_{route.symbol}_{route.timeframe}")
            
    @property
    def formatted_routes(self) -> List[Dict]:
        """
        Get routes in JSON-serializable format.
        
        Returns:
            [{exchange, symbol, timeframe, strategy_name, state, position}, ...]
        """
        return [
            {
                "exchange": r.exchange,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "strategy": r.strategy_name,
                "state": r.state.value,
                "has_position": r.position is not None,
                "current_time": r.current_time.isoformat() if r.current_time else None,
            }
            for r in self.routes.values()
        ]
        
    @staticmethod
    def _route_key(exchange: str, symbol: str, timeframe: str, strategy_name: str) -> str:
        """Generate unique route key."""
        return f"{exchange}_{symbol}_{timeframe}_{strategy_name}"
