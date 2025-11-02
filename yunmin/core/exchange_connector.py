"""
Exchange connector for interacting with cryptocurrency exchanges.

Inspired by hummingbot/connector/exchange patterns.
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order types."""
    LIMIT = "limit"
    MARKET = "market"
    STOP = "stop"


class ExchangeConnector:
    """
    Base exchange connector for trading.
    
    Implementations: BinanceConnector, KrakenConnector, etc.
    
    Usage:
        connector = BinanceConnector(api_key, api_secret)
        balance = connector.get_balance()
        order = connector.place_order(symbol="BTC/USDT", side="buy", amount=0.1)
    """
    
    def __init__(self, exchange_name: str, api_key: str, api_secret: str):
        """Initialize connector."""
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        
    def get_balance(self) -> Dict[str, float]:
        """
        Get account balance.
        
        Returns:
            Dict with currency balances {symbol: amount}
        """
        raise NotImplementedError
        
    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: float,
        price: Optional[float] = None
    ) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading pair (e.g., BTC/USDT)
            side: BUY or SELL
            order_type: LIMIT, MARKET, or STOP
            amount: Amount to trade
            price: Price for limit orders
            
        Returns:
            Order info dict
        """
        raise NotImplementedError
        
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel order by ID."""
        raise NotImplementedError
        
    def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """Get order status."""
        raise NotImplementedError
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open orders."""
        raise NotImplementedError
