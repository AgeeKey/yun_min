"""
Execution Agent - Smart Order Execution

Handles intelligent order placement to minimize slippage and market impact.
Supports TWAP, VWAP, iceberg orders, and adaptive execution.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class ExecutionAgent:
    """
    Smart order execution agent.
    
    Execution strategies:
    - Immediate: Market order
    - TWAP: Time-weighted average price
    - VWAP: Volume-weighted average price
    - Iceberg: Hidden large orders
    - Adaptive: Adjusts based on market conditions
    """
    
    def __init__(
        self,
        default_strategy: str = "adaptive",
        max_slippage: float = 0.001,  # 0.1%
        split_threshold: float = 0.01,  # 1% of position size
        slippage_tolerance: float = None  # Backwards compatibility
    ):
        """
        Initialize execution agent.
        
        Args:
            default_strategy: Default execution strategy
            max_slippage: Maximum acceptable slippage
            split_threshold: Threshold for splitting large orders
            slippage_tolerance: Alternative name for max_slippage (backwards compat)
        """
        # Backwards compatibility
        if slippage_tolerance is not None:
            max_slippage = slippage_tolerance
        
        self.default_strategy = default_strategy
        self.max_slippage = max_slippage
        self.split_threshold = split_threshold
        
        logger.info(f"⚡ Execution Agent initialized (strategy={default_strategy})")
    
    def plan_execution(
        self,
        order: Dict[str, Any],
        market_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Plan execution strategy for an order (sync version for testing).
        
        Args:
            order: Order details
            market_state: Current market state
            
        Returns:
            Execution plan with strategy and estimates
        """
        symbol = order.get('symbol', 'UNKNOWN')
        quantity = order.get('quantity', 0.0)
        spread = market_state.get('spread', 0.0)
        volume = market_state.get('volume', 0.0)
        
        # Select strategy based on market conditions
        strategy = self.default_strategy
        if spread > 50 or volume < 100000:
            strategy = 'iceberg'
        
        # Estimate slippage
        estimated_slippage = min(spread / 2, quantity / volume * 100) if volume > 0 else 0.01
        
        return {
            'strategy': strategy,
            'estimated_slippage': estimated_slippage,
            'symbol': symbol,
            'quantity': quantity,
            'split_orders': quantity > 1.0
        }
    
    async def execute(
        self,
        allocation: Dict[str, Any],
        market_context: Dict[str, Any],
        exchange_connector: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a trade allocation.
        
        Args:
            allocation: Trade allocation from portfolio manager
            market_context: Current market conditions
            exchange_connector: Exchange connector for actual execution
            
        Returns:
            Execution result
        """
        if not allocation.get('approved', False):
            logger.warning("⚠️  Allocation not approved, skipping execution")
            return {
                'executed': False,
                'reason': 'not_approved'
            }
        
        symbol = allocation.get('symbol', 'UNKNOWN')
        action = allocation.get('action', 'HOLD')
        size = allocation.get('amount', 0.0)
        
        logger.info(f"⚡ Executing: {symbol} {action} ${size:.2f}")
        
        # Select execution strategy
        strategy = self._select_strategy(allocation, market_context)
        logger.debug(f"Selected execution strategy: {strategy}")
        
        # Prepare order parameters
        order_params = self._prepare_order(
            symbol=symbol,
            action=action,
            size=size,
            strategy=strategy,
            market_context=market_context
        )
        
        # Execute order (dry run if no connector)
        if exchange_connector:
            result = await self._execute_on_exchange(
                order_params,
                exchange_connector
            )
        else:
            result = self._simulate_execution(order_params)
        
        logger.info(f"✅ Execution complete: {result.get('status', 'unknown')}")
        return result
    
    def _select_strategy(
        self,
        allocation: Dict[str, Any],
        market_context: Dict[str, Any]
    ) -> str:
        """
        Select optimal execution strategy based on conditions.
        """
        size = allocation.get('size', 0.0)
        volatility = market_context.get('volatility', 0.02)
        volume_ratio = market_context.get('indicators', {}).get('volume_ratio', 1.0)
        
        # Use adaptive strategy by default
        if self.default_strategy == "adaptive":
            # Large orders in low volume -> TWAP
            if size > self.split_threshold and volume_ratio < 0.8:
                return "twap"
            
            # High volatility -> limit order
            if volatility > 0.04:
                return "limit"
            
            # Normal conditions -> immediate
            return "immediate"
        
        return self.default_strategy
    
    def _prepare_order(
        self,
        symbol: str,
        action: str,
        size: float,
        strategy: str,
        market_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare order parameters based on strategy.
        """
        price = market_context.get('price', 0.0)
        
        order = {
            'symbol': symbol,
            'side': 'buy' if action == 'BUY' else 'sell',
            'type': 'market',
            'amount': size,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        }
        
        # Adjust based on strategy
        if strategy == "limit":
            # Place limit order with small buffer
            if action == 'BUY':
                limit_price = price * 0.999  # 0.1% below market
            else:
                limit_price = price * 1.001  # 0.1% above market
            
            order['type'] = 'limit'
            order['price'] = limit_price
        
        elif strategy == "twap":
            # Split into smaller orders over time
            num_splits = 5
            order['type'] = 'twap'
            order['splits'] = num_splits
            order['split_amount'] = size / num_splits
            order['interval_seconds'] = 60  # 1 minute between splits
        
        elif strategy == "iceberg":
            # Show only part of the order
            visible_amount = size * 0.2  # 20% visible
            order['type'] = 'iceberg'
            order['visible_amount'] = visible_amount
        
        # Add slippage protection
        order['max_slippage'] = self.max_slippage
        
        return order
    
    async def _execute_on_exchange(
        self,
        order_params: Dict[str, Any],
        exchange_connector: Any
    ) -> Dict[str, Any]:
        """
        Execute order on real exchange.
        """
        try:
            # Get exchange method
            if not hasattr(exchange_connector, 'create_order'):
                raise AttributeError("Exchange connector missing create_order method")
            
            # Execute based on strategy
            strategy = order_params.get('strategy', 'immediate')
            
            if strategy == "twap":
                # Execute TWAP splits
                results = []
                for i in range(order_params['splits']):
                    split_order = {
                        'symbol': order_params['symbol'],
                        'type': 'market',
                        'side': order_params['side'],
                        'amount': order_params['split_amount']
                    }
                    
                    result = await exchange_connector.create_order(**split_order)
                    results.append(result)
                    
                    # Wait between splits
                    if i < order_params['splits'] - 1:
                        await asyncio.sleep(order_params['interval_seconds'])
                
                # Aggregate results
                return self._aggregate_twap_results(results)
            
            else:
                # Simple order execution
                result = await exchange_connector.create_order(
                    symbol=order_params['symbol'],
                    type=order_params['type'],
                    side=order_params['side'],
                    amount=order_params['amount'],
                    price=order_params.get('price')
                )
                
                return {
                    'executed': True,
                    'order_id': result.get('id'),
                    'status': result.get('status'),
                    'filled': result.get('filled', 0),
                    'average_price': result.get('average', 0),
                    'timestamp': result.get('timestamp')
                }
        
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                'executed': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _simulate_execution(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate order execution (for testing/dry-run).
        """
        # Simulate immediate execution at market price
        return {
            'executed': True,
            'simulated': True,
            'order_id': f"SIM-{datetime.now().timestamp()}",
            'status': 'filled',
            'symbol': order_params['symbol'],
            'side': order_params['side'],
            'amount': order_params['amount'],
            'average_price': 50000.0,  # Placeholder
            'strategy': order_params['strategy'],
            'timestamp': order_params['timestamp']
        }
    
    def _aggregate_twap_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from TWAP splits.
        """
        total_filled = sum(r.get('filled', 0) for r in results)
        total_cost = sum(r.get('filled', 0) * r.get('average', 0) for r in results)
        
        average_price = total_cost / total_filled if total_filled > 0 else 0
        
        return {
            'executed': True,
            'order_ids': [r.get('id') for r in results],
            'status': 'filled',
            'filled': total_filled,
            'average_price': average_price,
            'splits': len(results),
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_slippage(
        self,
        expected_price: float,
        executed_price: float,
        side: str
    ) -> float:
        """
        Calculate slippage percentage.
        
        Args:
            expected_price: Expected execution price
            executed_price: Actual execution price
            side: Order side ('buy' or 'sell')
            
        Returns:
            Slippage as percentage (positive = worse than expected)
        """
        if expected_price == 0:
            return 0.0
        
        if side == 'buy':
            # Slippage is positive if we paid more
            slippage = (executed_price - expected_price) / expected_price
        else:  # sell
            # Slippage is positive if we got less
            slippage = (expected_price - executed_price) / expected_price
        
        return slippage
    
    def estimate_market_impact(
        self,
        order_size: float,
        market_context: Dict[str, Any]
    ) -> float:
        """
        Estimate market impact of an order.
        
        Args:
            order_size: Size of order
            market_context: Market conditions
            
        Returns:
            Estimated price impact as percentage
        """
        # Get average daily volume
        volume_24h = market_context.get('volume_24h', 1000000.0)
        
        # Impact is roughly proportional to order size / daily volume
        impact = (order_size / volume_24h) * 0.1  # 10% factor
        
        # Adjust for volatility
        volatility = market_context.get('volatility', 0.02)
        impact *= (1 + volatility / 0.02)  # More volatile = more impact
        
        return min(impact, 0.05)  # Cap at 5%
