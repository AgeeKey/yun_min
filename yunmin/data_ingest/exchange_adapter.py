"""
Exchange Adapter

Unified interface for interacting with cryptocurrency exchanges.
Uses CCXT library for exchange connectivity.
"""

from typing import List, Dict, Any, Optional
import ccxt
from loguru import logger
from datetime import datetime

from yunmin.core.config import ExchangeConfig


class ExchangeAdapter:
    """
    Adapter for connecting to cryptocurrency exchanges.
    
    Provides unified interface for:
    - Fetching market data (OHLCV, orderbook, trades)
    - Placing and managing orders
    - Account/balance queries
    """
    
    def __init__(self, config: ExchangeConfig):
        """
        Initialize exchange adapter.
        
        Args:
            config: Exchange configuration
        """
        self.config = config
        self.exchange = None
        self._connect()
        
    def _connect(self):
        """Connect to the exchange."""
        try:
            # Get exchange class from ccxt
            exchange_class = getattr(ccxt, self.config.name)
            
            # Configure exchange
            exchange_params = {
                'apiKey': self.config.api_key,
                'secret': self.config.api_secret,
                'enableRateLimit': self.config.enable_rate_limit,
            }
            
            # Use testnet if configured
            if self.config.testnet:
                if self.config.name == 'binance':
                    exchange_params['options'] = {
                        'defaultType': 'future',
                        'testnet': True
                    }
                    exchange_params['urls'] = {
                        'api': {
                            'public': 'https://testnet.binancefuture.com/fapi/v1',
                            'private': 'https://testnet.binancefuture.com/fapi/v1',
                        }
                    }
            
            self.exchange = exchange_class(exchange_params)
            
            # Load markets
            self.exchange.load_markets()
            
            logger.info(
                f"Connected to {self.config.name} "
                f"({'testnet' if self.config.testnet else 'mainnet'})"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.config.name}: {e}")
            raise
            
    def fetch_ohlcv(
        self, 
        symbol: str, 
        timeframe: str = '5m', 
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[List]:
        """
        Fetch OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            limit: Number of candles to fetch
            since: Timestamp in milliseconds
            
        Returns:
            List of OHLCV candles [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            logger.debug(f"Fetched {len(ohlcv)} {timeframe} candles for {symbol}")
            return ohlcv
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            raise
            
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker dictionary with current price, volume, etc.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise
            
    def fetch_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch order book.
        
        Args:
            symbol: Trading pair symbol
            limit: Depth of order book
            
        Returns:
            Order book with bids and asks
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            logger.error(f"Failed to fetch orderbook for {symbol}: {e}")
            raise
            
    def fetch_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance.
        
        Returns:
            Balance dictionary
        """
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            raise
            
    def create_market_order(
        self, 
        symbol: str, 
        side: str, 
        amount: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a market order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            params: Additional parameters (leverage, etc.)
            
        Returns:
            Order result dictionary
        """
        try:
            logger.info(f"Creating market order: {side} {amount} {symbol}")
            order = self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                params=params or {}
            )
            logger.info(f"Market order created: {order.get('id')}")
            return order
        except Exception as e:
            logger.error(f"Failed to create market order: {e}")
            raise
            
    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a limit order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Limit price
            params: Additional parameters
            
        Returns:
            Order result dictionary
        """
        try:
            logger.info(f"Creating limit order: {side} {amount} {symbol} @ {price}")
            order = self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            logger.info(f"Limit order created: {order.get('id')}")
            return order
        except Exception as e:
            logger.error(f"Failed to create limit order: {e}")
            raise
            
    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch order status.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order information
        """
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise
            
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Cancellation result
        """
        try:
            logger.info(f"Cancelling order {order_id}")
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order {order_id} cancelled")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
            
    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Fetch open positions (for futures).
        
        Args:
            symbols: List of symbols to fetch positions for
            
        Returns:
            List of position dictionaries
        """
        try:
            if hasattr(self.exchange, 'fetch_positions'):
                positions = self.exchange.fetch_positions(symbols)
                return positions
            else:
                logger.warning(f"{self.config.name} does not support fetch_positions")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            raise
            
    def set_leverage(self, symbol: str, leverage: int) -> Dict[str, Any]:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading pair symbol
            leverage: Leverage multiplier
            
        Returns:
            Result dictionary
        """
        try:
            if hasattr(self.exchange, 'set_leverage'):
                logger.info(f"Setting leverage to {leverage}x for {symbol}")
                result = self.exchange.set_leverage(leverage, symbol)
                return result
            else:
                logger.warning(f"{self.config.name} does not support set_leverage")
                return {}
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            raise
            
    def close(self):
        """Close exchange connection."""
        if self.exchange:
            logger.info(f"Closing connection to {self.config.name}")
            # CCXT doesn't require explicit close, but we log it
