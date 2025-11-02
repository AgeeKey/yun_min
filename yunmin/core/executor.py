"""
Order execution pipeline: Decision → Order placement.

Converts trading strategy decisions into actual orders,
with risk validation, position sizing, and error handling.

Adapted from Hummingbot patterns:
  - hummingbot/connector/order_state_manager.py
  - hummingbot/strategy/strategy_base.py
"""

import logging
import asyncio
from typing import Optional, Callable, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from yunmin.core.data_contracts import Decision
from yunmin.connectors.binance_connector import BinanceConnector
from yunmin.core.order_tracker import OrderTracker
from yunmin.core.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution mode."""
    DRY_RUN = "dry_run"         # No real orders
    PAPER = "paper"             # Simulated fills (random)
    LIVE = "live"               # Real orders


class ExecutionStatus(Enum):
    """Order execution status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ExecutionResult:
    """Result of order execution."""
    success: bool
    status: ExecutionStatus
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    filled_qty: float = 0
    avg_price: float = 0
    commission: float = 0
    error_message: Optional[str] = None


class Executor:
    """
    Order execution engine.
    
    Converts strategy Decision → Order placement with:
      - Risk validation (via RiskManager)
      - Position sizing
      - Order placement and tracking
      - Error handling and retries
      - Dry-run and paper trading modes
    
    Usage:
        executor = Executor(
            connector=connector,
            tracker=tracker,
            risk_manager=risk_manager,
            mode=ExecutionMode.PAPER
        )
        
        # Convert decision to order
        decision = Decision(
            intent="long",
            confidence=0.85,
            size_hint=0.1,
            reason="EMA crossover"
        )
        
        result = await executor.execute_decision(
            symbol="BTCUSDT",
            decision=decision,
            entry_price=42000,
            stop_loss_pct=0.02,
            take_profit_pct=0.05
        )
        
        if result.success:
            logger.info(f"Order {result.order_id} placed")
        else:
            logger.error(f"Execution failed: {result.error_message}")
    """
    
    def __init__(
        self,
        connector: BinanceConnector,
        tracker: OrderTracker,
        risk_manager: RiskManager,
        mode: ExecutionMode = ExecutionMode.DRY_RUN,
        max_retries: int = 3
    ):
        """
        Initialize Executor.
        
        Args:
            connector: BinanceConnector instance
            tracker: OrderTracker instance
            risk_manager: RiskManager instance
            mode: Execution mode (dry_run, paper, live)
            max_retries: Max retries for failed orders
        """
        self.connector = connector
        self.tracker = tracker
        self.risk_manager = risk_manager
        self.mode = mode
        self.max_retries = max_retries
        
        # Callbacks
        self.on_order_placed: Optional[Callable] = None
        self.on_order_filled: Optional[Callable] = None
        self.on_order_error: Optional[Callable] = None
        
        logger.info(f"Executor initialized (mode={mode.value})")
    
    async def execute_decision(
        self,
        symbol: str,
        decision: Decision,
        current_price: float,
        stop_loss_pct: Optional[float] = None,
        take_profit_pct: Optional[float] = None,
        current_position: float = 0
    ) -> ExecutionResult:
        """
        Execute trading decision.
        
        Args:
            symbol: Trading pair
            decision: Strategy Decision
            current_price: Current market price
            stop_loss_pct: Stop loss as % below entry
            take_profit_pct: Take profit as % above entry
            current_position: Current position quantity
            
        Returns:
            ExecutionResult with order details
        """
        try:
            # Determine side from decision intent
            if decision.intent == "long":
                side = "BUY"
            elif decision.intent == "short":
                side = "SELL"
            elif decision.intent == "exit":
                # Exit current position
                if current_position > 0:
                    side = "SELL"
                elif current_position < 0:
                    side = "BUY"
                else:
                    return ExecutionResult(
                        success=False,
                        status=ExecutionStatus.ERROR,
                        error_message="No position to exit"
                    )
            else:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.ERROR,
                    error_message=f"Invalid intent: {decision.intent}"
                )
            
            # Suggest position size
            qty = self.risk_manager.suggest_position_size(
                symbol,
                current_price,
                risk_pct=decision.size_hint
            )
            
            if qty <= 0:
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.ERROR,
                    error_message="Invalid position size"
                )
            
            # Validate with risk manager
            is_valid, reason = self.risk_manager.validate_order(
                symbol=symbol,
                side=side,
                quantity=qty,
                price=current_price,
                current_position_qty=abs(current_position)
            )
            
            if not is_valid:
                logger.warning(f"Order rejected by risk manager: {reason}")
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.ERROR,
                    error_message=f"Risk validation failed: {reason}"
                )
            
            # Execute based on mode
            if self.mode == ExecutionMode.DRY_RUN:
                result = await self._execute_dry_run(
                    symbol, side, qty, current_price, decision, 
                    stop_loss_pct, take_profit_pct
                )
            elif self.mode == ExecutionMode.PAPER:
                result = await self._execute_paper(
                    symbol, side, qty, current_price, decision,
                    stop_loss_pct, take_profit_pct
                )
            else:  # LIVE
                result = await self._execute_live(
                    symbol, side, qty, current_price, decision,
                    stop_loss_pct, take_profit_pct
                )
            
            # Callback on success
            if result.success and self.on_order_placed:
                await self._call_callback(self.on_order_placed, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            if self.on_order_error:
                await self._call_callback(self.on_order_error, e)
            return ExecutionResult(
                success=False,
                status=ExecutionStatus.ERROR,
                error_message=str(e)
            )
    
    async def _execute_dry_run(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        decision: Decision,
        sl_pct: Optional[float],
        tp_pct: Optional[float]
    ) -> ExecutionResult:
        """
        Dry-run execution (no real orders).
        
        Creates order in tracker but doesn't place on exchange.
        """
        client_oid = f"dry_{symbol}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        self.tracker.create_order(
            client_order_id=client_oid,
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            qty=qty,
            price=price
        )
        
        logger.info(f"Dry-run order created: {client_oid} {side} {qty} {symbol} @ {price}")
        
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.SUBMITTED,
            order_id=client_oid,
            filled_qty=0
        )
    
    async def _execute_paper(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        decision: Decision,
        sl_pct: Optional[float],
        tp_pct: Optional[float]
    ) -> ExecutionResult:
        """
        Paper trading execution (simulated fills).
        
        Creates order and immediately simulates a fill.
        """
        client_oid = f"paper_{symbol}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Create order
        self.tracker.create_order(
            client_order_id=client_oid,
            symbol=symbol,
            side=side,
            order_type="LIMIT",
            qty=qty,
            price=price
        )
        
        # Simulate exchange confirmation
        exchange_oid = f"sim_{client_oid}"
        self.tracker.set_exchange_id(client_oid, exchange_oid)
        
        # Simulate immediate fill
        commission = qty * price * 0.001  # 0.1% fee
        self.tracker.add_fill(
            client_order_id=client_oid,
            qty=qty,
            price=price,
            fee=commission,
            fee_asset="USDT"
        )
        
        # Update risk manager
        self.risk_manager.add_fill(symbol, side, qty, price, commission)
        
        logger.info(
            f"Paper order filled: {client_oid} {side} {qty} {symbol} "
            f"@ {price} (simulated)"
        )
        
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.FILLED,
            order_id=client_oid,
            exchange_order_id=exchange_oid,
            filled_qty=qty,
            avg_price=price,
            commission=commission
        )
    
    async def _execute_live(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        decision: Decision,
        sl_pct: Optional[float],
        tp_pct: Optional[float]
    ) -> ExecutionResult:
        """
        Live execution (real orders on exchange).
        
        Places order on Binance and tracks via OrderTracker.
        """
        client_oid = f"ym_{symbol}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        # Try to place order with retries
        for attempt in range(self.max_retries):
            try:
                # Create local order first
                order = self.tracker.create_order(
                    client_order_id=client_oid,
                    symbol=symbol,
                    side=side,
                    order_type="LIMIT",
                    qty=qty,
                    price=price
                )
                
                # Place on exchange
                response = self.connector.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="LIMIT",
                    qty=qty,
                    price=price,
                    client_order_id=client_oid
                )
                
                # Map exchange order ID
                exchange_oid = response.get("orderId")
                self.tracker.set_exchange_id(client_oid, exchange_oid)
                
                logger.info(
                    f"Live order placed: {client_oid} → {exchange_oid} "
                    f"{side} {qty} {symbol} @ {price}"
                )
                
                return ExecutionResult(
                    success=True,
                    status=ExecutionStatus.SUBMITTED,
                    order_id=client_oid,
                    exchange_order_id=exchange_oid,
                    filled_qty=0
                )
                
            except Exception as e:
                logger.warning(
                    f"Order placement attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                else:
                    return ExecutionResult(
                        success=False,
                        status=ExecutionStatus.ERROR,
                        error_message=str(e)
                    )
    
    async def _call_callback(self, callback: Callable, arg):
        """Call async or sync callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(arg)
            else:
                callback(arg)
        except Exception as e:
            logger.error(f"Callback error: {e}")
    
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel open order.
        
        Args:
            symbol: Trading pair
            order_id: Client order ID
            
        Returns:
            True if cancelled, False otherwise
        """
        try:
            if self.mode == ExecutionMode.DRY_RUN:
                self.tracker.cancel_order(order_id)
                logger.info(f"Dry-run order cancelled: {order_id}")
                return True
            
            elif self.mode == ExecutionMode.LIVE:
                # Cancel on exchange
                self.connector.cancel_order(symbol, order_id)
                self.tracker.cancel_order(order_id)
                logger.info(f"Live order cancelled: {order_id}")
                return True
            
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Get order status."""
        order = self.tracker.get_order(order_id)
        if not order:
            return {"status": "not_found"}
        
        return {
            "order_id": order_id,
            "status": order.state.value,
            "symbol": symbol,
            "side": order.side,
            "filled_qty": order.total_filled_qty,
            "avg_price": order.avg_fill_price,
            "commission": order.total_commission
        }
