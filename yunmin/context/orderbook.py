"""
Order Book Analyzer - Market Depth Analysis

Analyzes order book depth to assess liquidity and price pressure.
"""

from typing import Dict, Any, Optional, List
from loguru import logger


class OrderBookAnalyzer:
    """
    Analyzes order book for liquidity and price pressure.
    
    Metrics:
    - Bid/ask depth
    - Order book imbalance
    - Liquidity score
    - Price walls
    """
    
    def __init__(self, exchange_connector: Optional[Any] = None, depth: int = 50):
        """
        Initialize order book analyzer.
        
        Args:
            exchange_connector: Exchange connector for fetching order book
            depth: Default depth for analysis (ignored if provided in analyze())
        """
        self.exchange = exchange_connector
        self.default_depth = depth
        logger.info(f"📖 Order Book Analyzer initialized (depth={depth})")
    
    def analyze(self, order_book: Dict[str, Any]) -> Dict[str, Any]:
        """
        Анализирует предоставленный order book (синхронная версия для тестов).
        
        Args:
            order_book: Dict с 'bids' и 'asks' (список [price, volume])
            
        Returns:
            Анализ order book
        """
        try:
            analysis = {
                'bid_depth': self._calculate_depth(order_book['bids']),
                'ask_depth': self._calculate_depth(order_book['asks']),
                'imbalance': self._calculate_imbalance(order_book),
                'spread': self._calculate_spread(order_book),
                'liquidity_score': self._calculate_liquidity_score(order_book),
                'price_walls': self._find_price_walls(order_book)
            }
            
            logger.debug(f"Order book analyzed: imbalance={analysis['imbalance']:.2f}")
            return analysis
        
        except Exception as e:
            logger.warning(f"Order book analysis failed: {e}")
            return self._default_analysis()
    
    async def analyze_async(
        self,
        symbol: str = 'BTC/USDT',
        depth: int = 50
    ) -> Dict[str, Any]:
        """
        Analyze order book (async version для продакшена).
        
        Args:
            symbol: Trading symbol
            depth: Number of levels to analyze
            
        Returns:
            Order book analysis
        """
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_order_book'):
                order_book = await self.exchange.fetch_order_book(symbol, limit=depth)
            else:
                order_book = self._generate_sample_orderbook(depth)
            
            return self.analyze(order_book)
        
        except Exception as e:
            logger.warning(f"Order book analysis failed: {e}")
            return self._default_analysis()
    
    def _calculate_depth(self, levels: List[List[float]]) -> float:
        """Calculate total depth (volume) at price levels."""
        if not levels:
            return 0.0
        return sum(level[1] for level in levels)
    
    def _calculate_imbalance(self, order_book: Dict[str, Any]) -> float:
        """
        Calculate order book imbalance (-1 to 1).
        
        Positive = more bids (buy pressure)
        Negative = more asks (sell pressure)
        """
        bid_depth = self._calculate_depth(order_book['bids'])
        ask_depth = self._calculate_depth(order_book['asks'])
        
        total = bid_depth + ask_depth
        if total == 0:
            return 0.0
        
        return (bid_depth - ask_depth) / total
    
    def _calculate_spread(self, order_book: Dict[str, Any]) -> float:
        """Calculate bid-ask spread as percentage."""
        if not order_book['bids'] or not order_book['asks']:
            return 0.0
        
        best_bid = order_book['bids'][0][0]
        best_ask = order_book['asks'][0][0]
        
        spread = (best_ask - best_bid) / best_bid
        return spread
    
    def _calculate_liquidity_score(self, order_book: Dict[str, Any]) -> float:
        """
        Calculate liquidity score (0-100).
        
        Higher score = better liquidity (tight spread, deep book)
        """
        spread = self._calculate_spread(order_book)
        bid_depth = self._calculate_depth(order_book['bids'])
        ask_depth = self._calculate_depth(order_book['asks'])
        
        # Lower spread is better
        spread_score = max(0, 100 - spread * 10000)
        
        # Higher depth is better
        depth_score = min(100, (bid_depth + ask_depth) / 100)
        
        # Combine scores
        liquidity_score = (spread_score * 0.6 + depth_score * 0.4)
        
        return liquidity_score
    
    def _find_price_walls(self, order_book: Dict[str, Any]) -> Dict[str, List[float]]:
        """
        Find significant price walls (large orders).
        """
        # Calculate average volume per level
        bid_volumes = [level[1] for level in order_book['bids']]
        ask_volumes = [level[1] for level in order_book['asks']]
        
        avg_bid_volume = sum(bid_volumes) / len(bid_volumes) if bid_volumes else 0
        avg_ask_volume = sum(ask_volumes) / len(ask_volumes) if ask_volumes else 0
        
        # Find walls (orders 3x larger than average)
        bid_walls = [
            level[0] for level in order_book['bids']
            if level[1] > avg_bid_volume * 3
        ][:3]
        
        ask_walls = [
            level[0] for level in order_book['asks']
            if level[1] > avg_ask_volume * 3
        ][:3]
        
        return {
            'support_walls': bid_walls,
            'resistance_walls': ask_walls
        }
    
    def _generate_sample_orderbook(self, depth: int) -> Dict[str, Any]:
        """Generate sample order book for testing."""
        import numpy as np
        
        mid_price = 50000.0
        
        bids = []
        for i in range(depth):
            price = mid_price - (i + 1) * 10
            volume = np.random.exponential(scale=0.5)
            bids.append([price, volume])
        
        asks = []
        for i in range(depth):
            price = mid_price + (i + 1) * 10
            volume = np.random.exponential(scale=0.5)
            asks.append([price, volume])
        
        return {'bids': bids, 'asks': asks}
    
    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis when data unavailable."""
        return {
            'bid_depth': 0.0,
            'ask_depth': 0.0,
            'imbalance': 0.0,
            'spread': 0.001,
            'liquidity_score': 50.0,
            'price_walls': {'support_walls': [], 'resistance_walls': []}
        }
