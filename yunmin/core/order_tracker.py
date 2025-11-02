"""
Order tracker for monitoring active orders and their states.

Adapted from Hummingbot patterns (Apache-2.0):
  - hummingbot/connector/in_flight_order_base.pyx
  - hummingbot/connector/client_order_tracker.py

Tracks:
  - In-flight orders (client_oid ↔ exchange_id mapping)
  - Partial fills and commission
  - Order state transitions
  - Trade fill details
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderState(Enum):
    """Order state transitions."""
    PENDING = "pending"          # Created, awaiting exchange confirmation
    OPEN = "open"                # Confirmed by exchange, waiting for fill
    PARTIALLY_FILLED = "partially_filled"  # Partially filled
    FILLED = "filled"            # Fully filled
    CANCELLED = "cancelled"      # Cancelled by user
    REJECTED = "rejected"        # Rejected by exchange
    EXPIRED = "expired"          # Expired (GTC timeout, etc.)
    FAILED = "failed"            # Failed to create


@dataclass
class OrderFill:
    """Single fill for an order (partial or full)."""
    ts: datetime
    qty: float
    price: float
    fee: float
    fee_asset: str
    
    def __post_init__(self):
        self.commission = self.qty * self.price * (self.fee / 100) if self.fee < 1 else self.fee


@dataclass
class InFlightOrder:
    """
    Tracks an in-flight order from creation to closure.
    
    Handles client_oid ↔ exchange_id mapping, partial fills, and state.
    """
    client_order_id: str
    symbol: str
    side: str  # BUY or SELL
    order_type: str  # LIMIT, MARKET, STOP, etc.
    qty: float
    price: Optional[float]  # None for MARKET orders
    time_in_force: str = "GTC"
    
    # Exchange mapping
    exchange_order_id: Optional[str] = None
    exchange_ts: Optional[datetime] = None
    
    # Fills
    fills: List[OrderFill] = field(default_factory=list)
    
    # State
    state: OrderState = OrderState.PENDING
    created_ts: datetime = field(default_factory=datetime.utcnow)
    updated_ts: datetime = field(default_factory=datetime.utcnow)
    last_check_ts: Optional[datetime] = None
    
    # Metadata
    metadata: Dict = field(default_factory=dict)
    
    @property
    def total_filled_qty(self) -> float:
        """Total quantity filled across all partial fills."""
        return sum(f.qty for f in self.fills)
        
    @property
    def total_commission(self) -> float:
        """Total commission paid."""
        return sum(f.commission for f in self.fills)
        
    @property
    def avg_fill_price(self) -> Optional[float]:
        """Average price of fills."""
        if not self.fills:
            return None
        total_value = sum(f.qty * f.price for f in self.fills)
        return total_value / self.total_filled_qty if self.total_filled_qty > 0 else None
        
    @property
    def is_open(self) -> bool:
        """Check if order is still open (pending fill)."""
        return self.state in (OrderState.PENDING, OrderState.OPEN, OrderState.PARTIALLY_FILLED)
        
    @property
    def is_completed(self) -> bool:
        """Check if order is completed (filled, cancelled, or failed)."""
        return self.state in (
            OrderState.FILLED, OrderState.CANCELLED, 
            OrderState.REJECTED, OrderState.EXPIRED, OrderState.FAILED
        )
        
    def add_fill(self, qty: float, price: float, fee: float, 
                 fee_asset: str, ts: Optional[datetime] = None) -> "InFlightOrder":
        """
        Record a fill event.
        
        Args:
            qty: Filled quantity
            price: Fill price
            fee: Commission amount or percentage
            fee_asset: Commission asset (usually quote)
            ts: Fill timestamp
            
        Returns:
            Self for chaining
        """
        self.fills.append(OrderFill(
            ts=ts or datetime.utcnow(),
            qty=qty,
            price=price,
            fee=fee,
            fee_asset=fee_asset
        ))
        
        if self.total_filled_qty >= self.qty:
            self.state = OrderState.FILLED
        else:
            self.state = OrderState.PARTIALLY_FILLED
            
        self.updated_ts = datetime.utcnow()
        logger.debug(
            f"Fill recorded: {self.client_order_id} +{qty} @ {price} "
            f"(total: {self.total_filled_qty}/{self.qty})"
        )
        return self
        
    def cancel(self) -> "InFlightOrder":
        """Cancel order."""
        if not self.is_open:
            logger.warning(f"Cannot cancel non-open order: {self.client_order_id}")
            return self
        self.state = OrderState.CANCELLED
        self.updated_ts = datetime.utcnow()
        logger.info(f"Order cancelled: {self.client_order_id}")
        return self
        
    def set_exchange_id(self, exchange_order_id: str, ts: Optional[datetime] = None) -> "InFlightOrder":
        """
        Set exchange order ID (when confirmed by exchange).
        
        Args:
            exchange_order_id: Exchange order ID
            ts: Confirmation timestamp
            
        Returns:
            Self for chaining
        """
        self.exchange_order_id = exchange_order_id
        self.exchange_ts = ts or datetime.utcnow()
        if self.state == OrderState.PENDING:
            self.state = OrderState.OPEN
        self.updated_ts = datetime.utcnow()
        logger.debug(f"Exchange ID set: {self.client_order_id} → {exchange_order_id}")
        return self


class OrderTracker:
    """
    Tracks all in-flight orders and order history.
    
    Maintains:
      - In-flight orders (client_oid → InFlightOrder)
      - Historical orders for reporting
      - Client ↔ exchange ID mapping
      - Retry logic for failed orders
    
    Usage:
        tracker = OrderTracker()
        
        # Create order
        order = tracker.create_order(
            client_oid="ym_123",
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=42000
        )
        
        # Exchange confirms
        tracker.set_exchange_id("ym_123", "123456789")
        
        # Fill arrives
        tracker.add_fill("ym_123", qty=0.05, price=42000, fee=0.05)
        
        # Check status
        if tracker.is_filled("ym_123"):
            tracker.close_order("ym_123")
    """
    
    def __init__(self):
        """Initialize order tracker."""
        self.in_flight_orders: Dict[str, InFlightOrder] = {}
        self.order_history: List[InFlightOrder] = []
        self.client_to_exchange_id: Dict[str, str] = {}  # Mapping cache
        
    def create_order(
        self,
        client_order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float],
        time_in_force: str = "GTC"
    ) -> InFlightOrder:
        """
        Create and track new order.
        
        Args:
            client_order_id: Unique client-side order ID
            symbol: Trading pair (BTCUSDT)
            side: BUY or SELL
            order_type: LIMIT, MARKET, STOP, etc.
            qty: Order quantity
            price: Order price (None for MARKET)
            time_in_force: GTC, IOC, FOK
            
        Returns:
            InFlightOrder object
        """
        if client_order_id in self.in_flight_orders:
            logger.warning(f"Order already exists: {client_order_id}")
            return self.in_flight_orders[client_order_id]
            
        order = InFlightOrder(
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            time_in_force=time_in_force
        )
        
        self.in_flight_orders[client_order_id] = order
        logger.info(
            f"Order created: {client_order_id} {side} {qty} {symbol} @ {price}"
        )
        return order
        
    def set_exchange_id(self, client_order_id: str, exchange_order_id: str) -> bool:
        """
        Set exchange order ID when confirmed by exchange.
        
        Args:
            client_order_id: Client order ID
            exchange_order_id: Exchange order ID
            
        Returns:
            True if set, False if order not found
        """
        order = self.in_flight_orders.get(client_order_id)
        if not order:
            logger.warning(f"Order not found: {client_order_id}")
            return False
            
        order.set_exchange_id(exchange_order_id)
        self.client_to_exchange_id[client_order_id] = exchange_order_id
        return True
        
    def add_fill(
        self,
        client_order_id: str,
        qty: float,
        price: float,
        fee: float,
        fee_asset: str
    ) -> bool:
        """
        Record a fill for order.
        
        Args:
            client_order_id: Client order ID
            qty: Filled quantity
            price: Fill price
            fee: Commission
            fee_asset: Commission asset
            
        Returns:
            True if fill added, False if order not found
        """
        order = self.in_flight_orders.get(client_order_id)
        if not order:
            logger.warning(f"Order not found for fill: {client_order_id}")
            return False
            
        order.add_fill(qty, price, fee, fee_asset)
        return True
        
    def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel order.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            True if cancelled, False if not found or not cancellable
        """
        order = self.in_flight_orders.get(client_order_id)
        if not order:
            logger.warning(f"Order not found: {client_order_id}")
            return False
            
        order.cancel()
        return True
        
    def get_order(self, client_order_id: str) -> Optional[InFlightOrder]:
        """Get order by client ID."""
        return self.in_flight_orders.get(client_order_id)
        
    def get_order_by_exchange_id(self, exchange_order_id: str) -> Optional[InFlightOrder]:
        """Find order by exchange ID."""
        for order in self.in_flight_orders.values():
            if order.exchange_order_id == exchange_order_id:
                return order
        return None
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[InFlightOrder]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional filter by symbol
            
        Returns:
            List of open InFlightOrder objects
        """
        orders = [
            o for o in self.in_flight_orders.values()
            if o.is_open and (symbol is None or o.symbol == symbol)
        ]
        return orders
        
    def is_filled(self, client_order_id: str) -> bool:
        """Check if order is fully filled."""
        order = self.in_flight_orders.get(client_order_id)
        return order.state == OrderState.FILLED if order else False
        
    def close_order(self, client_order_id: str) -> Optional[InFlightOrder]:
        """
        Close and move order to history.
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Closed order, or None if not found
        """
        order = self.in_flight_orders.pop(client_order_id, None)
        if order:
            self.order_history.append(order)
            logger.info(
                f"Order closed: {client_order_id} ({order.state.value}) "
                f"filled={order.total_filled_qty}/{order.qty} "
                f"commission={order.total_commission:.4f}"
            )
        return order
        
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[InFlightOrder]:
        """
        Get order history.
        
        Args:
            symbol: Optional filter by symbol
            limit: Maximum number to return
            
        Returns:
            List of historical InFlightOrder objects (newest first)
        """
        history = [
            o for o in reversed(self.order_history)
            if symbol is None or o.symbol == symbol
        ]
        return history[:limit]
        
    def get_stats(self) -> Dict:
        """
        Get tracker statistics.
        
        Returns:
            Dict with counts and metrics
        """
        return {
            "open_orders": len([o for o in self.in_flight_orders.values() if o.is_open]),
            "total_orders_created": len(self.in_flight_orders) + len(self.order_history),
            "total_orders_closed": len(self.order_history),
            "total_filled": sum(o.total_filled_qty for o in self.order_history),
            "total_commission": sum(o.total_commission for o in self.order_history),
        }
