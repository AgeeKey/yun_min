"""
Binance Exchange Connector

Adapted from Hummingbot's BinanceExchange (Apache-2.0)
Reference: hummingbot/connector/exchange/binance/binance_exchange.py

Implements REST API for:
  - Account balance queries
  - Order placement (LIMIT, MARKET)
  - Order cancellation
  - Order status tracking
  - Open orders listing
  - Trade history

WebSocket support added separately (WebSocketConnector).
"""

import hashlib
import hmac
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


class BinanceConnectorError(Exception):
    """Base Binance connector error."""
    pass


class BinanceAuth:
    """Handles Binance API authentication (signature generation)."""
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Binance authenticator.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
    def generate_signature(self, query_string: str) -> str:
        """
        Generate HMAC-SHA256 signature for request.
        
        Args:
            query_string: Query parameters as URL-encoded string
            
        Returns:
            Hex signature
        """
        return hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()


class BinanceConnector:
    """
    REST API connector for Binance (Spot trading).
    
    Supports testnet and live trading via 'testnet' flag.
    
    Usage:
        connector = BinanceConnector(
            api_key="your-key",
            api_secret="your-secret",
            testnet=True
        )
        balance = connector.get_balance()
        order = connector.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="LIMIT",
            qty=0.1,
            price=42000
        )
    """
    
    # Base URLs
    BASE_URL_MAINNET = "https://api.binance.com"
    BASE_URL_TESTNET = "https://testnet.binance.vision"
    
    # Endpoints
    PING_ENDPOINT = "/api/v3/ping"
    ACCOUNT_ENDPOINT = "/api/v3/account"
    ORDER_ENDPOINT = "/api/v3/order"
    OPEN_ORDERS_ENDPOINT = "/api/v3/openOrders"
    ALL_ORDERS_ENDPOINT = "/api/v3/allOrders"
    EXCHANGE_INFO_ENDPOINT = "/api/v3/exchangeInfo"
    
    # Order types
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_STOP_LOSS = "STOP_LOSS"
    ORDER_TYPE_TAKE_PROFIT = "TAKE_PROFIT"
    
    # Time in force
    TIME_IN_FORCE_GTC = "GTC"  # Good till cancelled
    TIME_IN_FORCE_IOC = "IOC"  # Immediate or cancel
    TIME_IN_FORCE_FOK = "FOK"  # Fill or kill
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = True,
        request_timeout: int = 10
    ):
        """
        Initialize Binance connector.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet if True, mainnet if False
            request_timeout: HTTP request timeout in seconds
        """
        if not requests:
            raise BinanceConnectorError("requests library not installed")
            
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.request_timeout = request_timeout
        self.auth = BinanceAuth(api_key, api_secret)
        
        self.base_url = self.BASE_URL_TESTNET if testnet else self.BASE_URL_MAINNET
        logger.info(f"Binance connector initialized: {'testnet' if testnet else 'mainnet'}")
        
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        signed: bool = False
    ) -> Dict:
        """
        Make HTTP request to Binance API.
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            params: Query/body parameters
            signed: Require authentication signature
            
        Returns:
            Response JSON as dict
            
        Raises:
            BinanceConnectorError: On API error
        """
        url = self.base_url + endpoint
        headers = {
            "Accept": "application/json",
            "User-Agent": "YunMin/1.0"
        }
        
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
            
        params = params or {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            query_string = urlencode(params)
            params["signature"] = self.auth.generate_signature(query_string)
            
        try:
            if method == "GET":
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.request_timeout
                )
            elif method == "POST":
                response = requests.post(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.request_timeout
                )
            elif method == "DELETE":
                response = requests.delete(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.request_timeout
                )
            else:
                raise BinanceConnectorError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise BinanceConnectorError(f"API request failed: {e}")
            
    def ping(self) -> bool:
        """
        Test API connectivity.
        
        Returns:
            True if connected
        """
        try:
            self._request("GET", self.PING_ENDPOINT)
            logger.info("Binance API ping successful")
            return True
        except BinanceConnectorError as e:
            logger.error(f"Ping failed: {e}")
            return False
            
    def get_server_time(self) -> int:
        """
        Get server time.
        
        Returns:
            Server timestamp in milliseconds
        """
        response = self._request("GET", "/api/v3/time")
        return response.get("serverTime", int(time.time() * 1000))
        
    def get_balance(self) -> Dict[str, float]:
        """
        Get account balance.
        
        Returns:
            Dict mapping asset → available balance
            Example: {"BTC": 1.5, "USDT": 10000.0}
        """
        response = self._request("GET", self.ACCOUNT_ENDPOINT, signed=True)
        
        balances = {}
        for item in response.get("balances", []):
            asset = item.get("asset")
            free = float(item.get("free", 0))
            if free > 0:
                balances[asset] = free
                
        logger.debug(f"Balance retrieved: {balances}")
        return balances
        
    def get_trading_pair_info(self, symbol: str) -> Dict:
        """
        Get trading pair info (min qty, price precision, etc.).
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            
        Returns:
            Dict with minQty, stepSize, minPrice, tickSize, maker fee, taker fee
        """
        response = self._request("GET", self.EXCHANGE_INFO_ENDPOINT)
        
        for symbol_info in response.get("symbols", []):
            if symbol_info.get("symbol") == symbol:
                filters_map = {}
                for f in symbol_info.get("filters", []):
                    filters_map[f.get("filterType")] = f
                    
                lot_size = filters_map.get("LOT_SIZE", {})
                price_filter = filters_map.get("PRICE_FILTER", {})
                
                return {
                    "symbol": symbol,
                    "baseAsset": symbol_info.get("baseAsset"),
                    "quoteAsset": symbol_info.get("quoteAsset"),
                    "minQty": float(lot_size.get("minQty", 0)),
                    "stepSize": float(lot_size.get("stepSize", 0)),
                    "minPrice": float(price_filter.get("minPrice", 0)),
                    "tickSize": float(price_filter.get("tickSize", 0)),
                    "makerCommission": float(symbol_info.get("makerCommission", 0.001)),
                    "takerCommission": float(symbol_info.get("takerCommission", 0.001)),
                }
                
        raise BinanceConnectorError(f"Symbol {symbol} not found")
        
    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float] = None,
        client_order_id: Optional[str] = None,
        time_in_force: str = TIME_IN_FORCE_GTC,
        test: bool = False
    ) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading pair (BTCUSDT)
            side: BUY or SELL
            order_type: LIMIT, MARKET, STOP_LOSS, TAKE_PROFIT
            qty: Order quantity
            price: Price (required for LIMIT, optional for MARKET)
            client_order_id: Custom order ID (optional)
            time_in_force: GTC, IOC, FOK (default GTC)
            test: Test order (doesn't execute) if True
            
        Returns:
            Order dict with orderId, clientOrderId, status, etc.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": qty,
            "timeInForce": time_in_force,
        }
        
        if price:
            params["price"] = price
        if client_order_id:
            params["newClientOrderId"] = client_order_id
            
        endpoint = "/api/v3/order/test" if test else self.ORDER_ENDPOINT
        response = self._request("POST", endpoint, params=params, signed=True)
        
        logger.info(
            f"Order placed: {side} {qty} {symbol} @ {price} "
            f"(id={response.get('clientOrderId')})"
        )
        return response
        
    def cancel_order(self, symbol: str, order_id: Optional[str] = None, 
                     client_order_id: Optional[str] = None) -> Dict:
        """
        Cancel an order.
        
        Args:
            symbol: Trading pair
            order_id: Exchange order ID
            client_order_id: Client order ID
            
        Returns:
            Cancelled order dict
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise BinanceConnectorError("Either order_id or client_order_id required")
            
        response = self._request("DELETE", self.ORDER_ENDPOINT, params=params, signed=True)
        logger.info(f"Order cancelled: {client_order_id or order_id}")
        return response
        
    def get_order_status(self, symbol: str, order_id: Optional[str] = None,
                        client_order_id: Optional[str] = None) -> Dict:
        """
        Get order status.
        
        Args:
            symbol: Trading pair
            order_id: Exchange order ID
            client_order_id: Client order ID
            
        Returns:
            Order dict with status, filled qty, etc.
        """
        params = {"symbol": symbol}
        
        if order_id:
            params["orderId"] = order_id
        elif client_order_id:
            params["origClientOrderId"] = client_order_id
        else:
            raise BinanceConnectorError("Either order_id or client_order_id required")
            
        response = self._request("GET", self.ORDER_ENDPOINT, params=params, signed=True)
        return response
        
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional filter by symbol
            
        Returns:
            List of open order dicts
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
            
        response = self._request("GET", self.OPEN_ORDERS_ENDPOINT, params=params, signed=True)
        logger.debug(f"Retrieved {len(response)} open orders")
        return response
        
    def get_order_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """
        Get order history.
        
        Args:
            symbol: Trading pair
            limit: Number of orders (default 100, max 1000)
            
        Returns:
            List of order dicts
        """
        params = {
            "symbol": symbol,
            "limit": min(limit, 1000)
        }
        response = self._request("GET", self.ALL_ORDERS_ENDPOINT, params=params, signed=True)
        return response
