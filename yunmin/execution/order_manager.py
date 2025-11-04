"""
Order Manager

Manages order execution with support for dry-run, paper trading, and live trading.
"""

from typing import Dict, Any, Optional
from enum import Enum
from loguru import logger
from datetime import datetime, UTC

from yunmin.data_ingest.exchange_adapter import ExchangeAdapter
from yunmin.risk.policies import OrderRequest
from yunmin.execution.market_simulator import MarketSimulator


class TradingMode(Enum):
    """Trading mode enumeration."""
    DRY_RUN = "dry_run"  # No actual orders, just logging
    PAPER = "paper"  # Simulated orders with real market data
    LIVE = "live"  # Real orders with real money


class OrderManager:
    """
    Manages order execution across different trading modes.
    
    Safety-first approach:
    - DRY_RUN: Only logs orders, no execution
    - PAPER: Simulates orders for testing
    - LIVE: Executes real orders (requires explicit confirmation)
    """
    
    def __init__(
        self,
        exchange: Optional[ExchangeAdapter] = None,
        mode: str = "dry_run"
    ):
        """
        Initialize order manager.
        
        Args:
            exchange: Exchange adapter (required for paper and live modes)
            mode: Trading mode (dry_run, paper, live)
        """
        self.exchange = exchange
        self.mode = TradingMode(mode)
        self.orders_log = []
        self.paper_positions = {}  # For paper trading
        
        # Market simulator for realistic DRY RUN
        self.market_simulator = MarketSimulator(exchange=exchange)
        
        logger.info(f"OrderManager initialized in {self.mode.value} mode")
        
        if self.mode == TradingMode.LIVE:
            logger.warning("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
            
    def execute_order(
        self,
        order: OrderRequest,
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute an order based on the trading mode.
        
        Args:
            order: Order request
            current_price: Current market price (for paper trading)
            
        Returns:
            Order result dictionary
        """
        if self.mode == TradingMode.DRY_RUN:
            return self._dry_run_order(order, current_price)
        elif self.mode == TradingMode.PAPER:
            return self._paper_trade_order(order, current_price)
        elif self.mode == TradingMode.LIVE:
            return self._live_trade_order(order)
        else:
            raise ValueError(f"Unknown trading mode: {self.mode}")
            
    def _dry_run_order(
        self,
        order: OrderRequest,
        current_price: Optional[float]
    ) -> Dict[str, Any]:
        """
        Execute order in dry-run mode with realistic market simulation.
        
        Использует MarketSimulator для:
        - Точных комиссий (0.1%)
        - Реалистичного проскальзывания
        - Синхронизации с реальными ценами
        """
        # Получить реальную цену если не передана
        if current_price is None and self.exchange:
            real_price = self.market_simulator.get_real_price(order.symbol)
            if real_price:
                current_price = real_price
                logger.debug(f"Using real market price: ${current_price:.2f}")
        
        if current_price is None:
            logger.error("Cannot execute DRY RUN order without price")
            raise ValueError("Price required for dry-run simulation")
        
        # Исполнить через MarketSimulator
        execution = self.market_simulator.execute_market_order(
            symbol=order.symbol,
            side=order.side,
            amount=order.amount,
            current_price=current_price,
            is_maker=False  # Market orders = taker
        )
        
        logger.info(
            f"[DRY-RUN] {order.side.upper()} {order.amount:.6f} {order.symbol} "
            f"@ ${execution.executed_price:.2f} "
            f"(slippage {execution.slippage_pct*100:.3f}%, fee ${execution.commission:.2f})"
        )
        
        result = {
            'id': f"dry_{len(self.orders_log)}",
            'symbol': order.symbol,
            'side': order.side,
            'type': order.order_type,
            'amount': order.amount,
            'requested_price': execution.requested_price,
            'executed_price': execution.executed_price,
            'total_cost': execution.total_cost,
            'commission': execution.commission,
            'slippage': execution.slippage,
            'slippage_pct': execution.slippage_pct,
            'status': 'simulated',
            'timestamp': datetime.now(UTC).isoformat(),
            'mode': 'dry_run'
        }
        
        self.orders_log.append(result)
        return result
        
    def _paper_trade_order(
        self,
        order: OrderRequest,
        current_price: Optional[float]
    ) -> Dict[str, Any]:
        """Execute order in paper trading mode (simulated with real prices)."""
        execution_price = order.price or current_price
        
        if execution_price is None:
            logger.error("Cannot execute paper order without price")
            raise ValueError("Price required for paper trading")
            
        logger.info(
            f"[PAPER] {order.side.upper()} {order.amount} {order.symbol} "
            f"@ {execution_price}"
        )
        
        # Update paper positions
        position_key = f"{order.symbol}_{order.side}"
        if position_key not in self.paper_positions:
            self.paper_positions[position_key] = {
                'symbol': order.symbol,
                'side': order.side,
                'amount': 0,
                'avg_price': 0,
                'total_value': 0
            }
            
        pos = self.paper_positions[position_key]
        
        if order.side == 'buy':
            new_amount = pos['amount'] + order.amount
            pos['total_value'] += order.amount * execution_price
            pos['avg_price'] = pos['total_value'] / new_amount if new_amount > 0 else 0
            pos['amount'] = new_amount
        else:  # sell
            pos['amount'] = max(0, pos['amount'] - order.amount)
            if pos['amount'] == 0:
                pos['total_value'] = 0
                pos['avg_price'] = 0
                
        result = {
            'id': f"paper_{len(self.orders_log)}",
            'symbol': order.symbol,
            'side': order.side,
            'type': order.order_type,
            'amount': order.amount,
            'price': execution_price,
            'status': 'filled',
            'timestamp': datetime.now(UTC).isoformat(),
            'mode': 'paper',
            'position': pos.copy()
        }
        
        self.orders_log.append(result)
        return result
        
    def _live_trade_order(self, order: OrderRequest) -> Dict[str, Any]:
        """Execute order in live trading mode (real orders)."""
        if self.exchange is None:
            raise ValueError("Exchange adapter required for live trading")
            
        logger.warning(
            f"[LIVE] Executing REAL order: {order.side.upper()} "
            f"{order.amount} {order.symbol}"
        )
        
        try:
            # Set leverage if specified
            if order.leverage > 1:
                self.exchange.set_leverage(order.symbol, int(order.leverage))
                
            # Execute order
            if order.order_type == 'market':
                result = self.exchange.create_market_order(
                    symbol=order.symbol,
                    side=order.side,
                    amount=order.amount
                )
            elif order.order_type == 'limit':
                if order.price is None:
                    raise ValueError("Limit order requires price")
                result = self.exchange.create_limit_order(
                    symbol=order.symbol,
                    side=order.side,
                    amount=order.amount,
                    price=order.price
                )
            else:
                raise ValueError(f"Unknown order type: {order.order_type}")
                
            result['mode'] = 'live'
            self.orders_log.append(result)
            
            logger.info(f"[LIVE] Order executed: {result.get('id')}")
            return result
            
        except Exception as e:
            logger.error(f"[LIVE] Order execution failed: {e}")
            raise
            
    def get_orders_history(self) -> list:
        """Get history of all orders."""
        return self.orders_log.copy()
        
    def get_paper_positions(self) -> Dict[str, Any]:
        """Get current paper trading positions."""
        return self.paper_positions.copy()
        
    def close_paper_position(self, symbol: str, current_price: float):
        """
        Close paper position (called by PositionMonitor)
        
        Args:
            symbol: Symbol to close (e.g., 'BTC/USDT')
            current_price: Current price for closing
        """
        # Найти позицию для этого символа
        positions_to_close = [
            key for key in self.paper_positions.keys()
            if key.startswith(symbol)
        ]
        
        for position_key in positions_to_close:
            pos = self.paper_positions[position_key]
            
            if pos['amount'] > 0:
                # Создать ордер на закрытие
                close_side = 'sell' if pos['side'] == 'buy' else 'buy'
                
                order = OrderRequest(
                    symbol=symbol,
                    side=close_side,
                    order_type='market',
                    amount=pos['amount'],
                    price=current_price,
                    leverage=1.0
                )
                
                # Выполнить закрытие
                result = self._paper_trade_order(order, current_price)
                
                logger.info(
                    f"💰 PAPER: Closed position {position_key}, "
                    f"entry: {pos['avg_price']:.2f}, exit: {current_price:.2f}"
                )
        
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Cancel an order."""
        if self.mode == TradingMode.LIVE and self.exchange:
            return self.exchange.cancel_order(order_id, symbol)
        else:
            logger.info(f"[{self.mode.value.upper()}] Cancel order {order_id}")
            return {'status': 'cancelled', 'mode': self.mode.value}
