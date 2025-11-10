"""
Portfolio Manager Agent - Multi-Asset Portfolio Management

Manages allocation across multiple assets (3-5 coins).
Handles diversification, rebalancing, and capital allocation.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from loguru import logger

# Import for Signal type hint
try:
    from yunmin.strategy.base import Signal, SignalType
except ImportError:
    # Fallback if not available
    Signal = Any
    SignalType = Any


class PortfolioManagerAgent:
    """
    Portfolio management agent for multi-asset trading.
    
    Responsibilities:
    - Asset selection (which coin to trade now?)
    - Capital allocation across assets
    - Portfolio rebalancing
    - Risk diversification
    """
    
    def __init__(
        self,
        max_assets: int = 5,
        max_total_exposure: float = 0.5,
        rebalance_threshold: float = 0.2
    ):
        """
        Initialize portfolio manager.
        
        Args:
            max_assets: Maximum number of simultaneous positions
            max_total_exposure: Maximum total portfolio exposure
            rebalance_threshold: Threshold for rebalancing (fraction)
        """
        self.max_assets = max_assets
        self.max_total_exposure = max_total_exposure
        self.rebalance_threshold = rebalance_threshold
        
        logger.info(f"💼 Portfolio Manager Agent initialized (max_assets={max_assets})")
    
    def allocate(
        self,
        trade_proposal: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Allocate capital for a proposed trade.
        
        Args:
            trade_proposal: Proposed trade from analyst
            market_context: Current market conditions
            portfolio: Current portfolio state
            
        Returns:
            Allocation decision with size and priority
        """
        logger.debug("💼 Calculating portfolio allocation...")
        
        # Get current positions
        positions = portfolio.get('positions', [])
        available_capital = portfolio.get('available_capital', 10000.0)
        total_capital = portfolio.get('total_capital', 10000.0)
        
        # Check if we can add more positions
        if len(positions) >= self.max_assets:
            logger.warning(f"⚠️  Maximum positions reached ({self.max_assets}), need to close one first")
            return {
                'approved': False,
                'reason': 'max_positions_reached',
                'suggested_action': 'close_weakest_position'
            }
        
        # Check total exposure
        current_exposure = sum(p.get('size', 0) for p in positions) / total_capital
        if current_exposure >= self.max_total_exposure:
            logger.warning(f"⚠️  Maximum exposure reached ({self.max_total_exposure:.1%})")
            return {
                'approved': False,
                'reason': 'max_exposure_reached',
                'current_exposure': current_exposure
            }
        
        # Calculate allocation size
        symbol = market_context.get('symbol', 'UNKNOWN')
        recommended_size = trade_proposal.get('recommended_position_size', 0.05)
        
        # Adjust based on diversification
        diversification_factor = self._calculate_diversification_factor(positions, symbol)
        adjusted_size = recommended_size * diversification_factor
        
        # Calculate actual amount
        allocation_amount = available_capital * adjusted_size
        
        allocation = {
            'approved': True,
            'symbol': symbol,
            'action': trade_proposal.get('action', 'HOLD'),
            'size': adjusted_size,
            'amount': allocation_amount,
            'priority': self._calculate_priority(trade_proposal, market_context, portfolio),
            'diversification_factor': diversification_factor
        }
        
        logger.info(f"✅ Allocation: {symbol} {allocation['action']} size={adjusted_size:.3f} (${allocation_amount:.2f})")
        return allocation
    
    def select_next_asset(
        self,
        available_assets: List[str],
        market_conditions: Dict[str, Dict[str, Any]],
        portfolio: Dict[str, Any]
    ) -> Optional[str]:
        """
        Select next asset to analyze/trade.
        
        Args:
            available_assets: List of tradeable assets
            market_conditions: Market conditions for each asset
            portfolio: Current portfolio state
            
        Returns:
            Symbol of selected asset or None
        """
        if not available_assets:
            return None
        
        # Get current positions
        positions = portfolio.get('positions', [])
        current_symbols = [p.get('symbol') for p in positions]
        
        # Score each asset
        scores = {}
        for symbol in available_assets:
            if symbol in current_symbols:
                continue  # Skip assets we already have
            
            context = market_conditions.get(symbol, {})
            score = self._score_asset(symbol, context, portfolio)
            scores[symbol] = score
        
        if not scores:
            return None
        
        # Select highest scoring asset
        best_symbol = max(scores.items(), key=lambda x: x[1])[0]
        logger.info(f"📊 Selected asset: {best_symbol} (score={scores[best_symbol]:.2f})")
        
        return best_symbol
    
    def check_rebalancing_needed(
        self,
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if portfolio needs rebalancing.
        
        Args:
            portfolio: Current portfolio state
            
        Returns:
            Rebalancing recommendation
        """
        positions = portfolio.get('positions', [])
        
        if len(positions) < 2:
            return {'needed': False, 'reason': 'insufficient_positions'}
        
        # Calculate position weights
        total_value = sum(p.get('value', 0) for p in positions)
        if total_value == 0:
            return {'needed': False, 'reason': 'zero_value'}
        
        weights = [p.get('value', 0) / total_value for p in positions]
        
        # Check if any position is too large
        max_weight = max(weights)
        target_weight = 1.0 / len(positions)
        
        if max_weight > target_weight * (1 + self.rebalance_threshold):
            return {
                'needed': True,
                'reason': 'unbalanced_weights',
                'max_weight': max_weight,
                'target_weight': target_weight,
                'action': 'reduce_largest_position'
            }
        
        return {'needed': False}
    
    def _calculate_diversification_factor(
        self,
        positions: List[Dict[str, Any]],
        new_symbol: str
    ) -> float:
        """
        Calculate diversification factor (1.0 = no adjustment).
        
        Reduces size if we already have correlated positions.
        """
        if not positions:
            return 1.0
        
        # Simple correlation check based on asset type
        # In production, would use actual correlation matrix
        
        # Check if we have many positions
        if len(positions) >= self.max_assets - 1:
            return 0.7  # Reduce size when near capacity
        
        # Check if similar asset already exists
        # (e.g., BTC/USDT and ETH/USDT are correlated)
        base_asset = new_symbol.split('/')[0]
        similar_positions = [
            p for p in positions
            if p.get('symbol', '').split('/')[0].startswith(base_asset[:2])
        ]
        
        if similar_positions:
            return 0.8  # Reduce size for correlated assets
        
        return 1.0  # Full size for diversified position
    
    def _calculate_priority(
        self,
        trade_proposal: Dict[str, Any],
        market_context: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> int:
        """
        Calculate trade priority (1-10, higher is more urgent).
        """
        base_priority = 5
        
        # Increase priority for high confidence trades
        confidence = trade_proposal.get('confidence', 0.5)
        if confidence > 0.8:
            base_priority += 2
        elif confidence > 0.7:
            base_priority += 1
        
        # Increase priority for underutilized portfolio
        positions = portfolio.get('positions', [])
        if len(positions) < self.max_assets / 2:
            base_priority += 1
        
        # Increase priority in strong trends
        trend_strength = market_context.get('trend_strength', 0.5)
        if trend_strength > 0.7:
            base_priority += 1
        
        return min(10, max(1, base_priority))
    
    def _score_asset(
        self,
        symbol: str,
        context: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> float:
        """
        Score an asset for trading priority.
        """
        score = 0.0
        
        indicators = context.get('indicators', {})
        
        # Trend strength
        ema_fast = indicators.get('ema_fast', 0)
        ema_slow = indicators.get('ema_slow', 0)
        if ema_slow > 0:
            trend_strength = abs(ema_fast - ema_slow) / ema_slow
            score += trend_strength * 30
        
        # Volume
        volume_ratio = indicators.get('volume_ratio', 1.0)
        if volume_ratio > 1.0:
            score += (volume_ratio - 1.0) * 20
        
        # Volatility (moderate is good)
        volatility = context.get('volatility', 0.02)
        if 0.02 <= volatility <= 0.04:
            score += 20
        elif volatility > 0.04:
            score += 10
        
        # RSI in tradeable range
        rsi = indicators.get('rsi', 50)
        if 30 <= rsi <= 70:
            score += 15
        
        # Diversification bonus
        positions = portfolio.get('positions', [])
        base_asset = symbol.split('/')[0]
        if not any(p.get('symbol', '').startswith(base_asset[:2]) for p in positions):
            score += 15
        
        return score
    
    def get_portfolio_summary(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get portfolio summary statistics.
        
        Args:
            portfolio: Current portfolio state
            
        Returns:
            Summary statistics
        """
        positions = portfolio.get('positions', [])
        total_capital = portfolio.get('total_capital', 10000.0)
        
        if not positions:
            return {
                'num_positions': 0,
                'total_exposure': 0.0,
                'utilization': 0.0,
                'largest_position': None
            }
        
        # Calculate metrics
        total_value = sum(p.get('value', 0) for p in positions)
        largest_position = max(positions, key=lambda p: p.get('value', 0))
        
        return {
            'num_positions': len(positions),
            'total_exposure': total_value / total_capital,
            'utilization': len(positions) / self.max_assets,
            'largest_position': largest_position.get('symbol'),
            'largest_position_weight': largest_position.get('value', 0) / total_value if total_value > 0 else 0
        }


class MultiSymbolPortfolioManager:
    """
    Enhanced portfolio manager for multi-symbol trading.
    
    Manages capital allocation across multiple trading symbols with
    consideration for correlations and diversification.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize multi-symbol portfolio manager.
        
        Args:
            config: Configuration dictionary with symbol allocations
        """
        if config and 'symbols' in config:
            self.symbols = config['symbols']
            self.capital_allocation = {
                s['symbol']: s['allocation'] 
                for s in self.symbols
            }
            self.risk_limits = {
                s['symbol']: s.get('risk_limit', 0.10)
                for s in self.symbols
            }
        else:
            # Default configuration
            self.symbols = [
                {'symbol': 'BTC/USDT', 'allocation': 0.4, 'risk_limit': 0.10},
                {'symbol': 'ETH/USDT', 'allocation': 0.35, 'risk_limit': 0.10},
                {'symbol': 'BNB/USDT', 'allocation': 0.25, 'risk_limit': 0.10}
            ]
            self.capital_allocation = {s['symbol']: s['allocation'] for s in self.symbols}
            self.risk_limits = {s['symbol']: s['risk_limit'] for s in self.symbols}
        
        # Portfolio settings
        self.max_total_exposure = config.get('portfolio', {}).get('max_total_exposure', 0.50) if config else 0.50
        self.rebalance_threshold = config.get('portfolio', {}).get('rebalance_threshold', 0.10) if config else 0.10
        
        logger.info(f"💼 Multi-Symbol Portfolio Manager initialized with {len(self.symbols)} symbols")
    
    def allocate_capital(
        self, 
        signals: Dict[str, Any],
        current_positions: Dict[str, float] = None,
        correlations: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Allocate capital across multiple symbols based on signals.
        
        Args:
            signals: Dict of {symbol: Signal} with trading signals
            current_positions: Dict of {symbol: current_position_size}
            correlations: Dict of correlation pairs for adjustment
            
        Returns:
            Dict of {symbol: position_size} allocations
        """
        allocations = {}
        current_positions = current_positions or {}
        
        try:
            for symbol, signal in signals.items():
                # Check if this is a buy signal
                if hasattr(signal, 'type'):
                    signal_type = signal.type
                    if hasattr(SignalType, 'BUY'):
                        is_buy = signal_type == SignalType.BUY
                    else:
                        is_buy = str(signal_type).upper() == 'BUY'
                else:
                    # Fallback for dict-like signals
                    is_buy = signal.get('action', '').upper() == 'BUY'
                
                if is_buy:
                    # Get base allocation for this symbol
                    base_allocation = self.capital_allocation.get(symbol, 0.0)
                    
                    # Adjust by confidence
                    if hasattr(signal, 'confidence'):
                        confidence = signal.confidence
                    elif isinstance(signal, dict):
                        confidence = signal.get('confidence', 1.0)
                    else:
                        confidence = 1.0
                    
                    confidence_adjusted = base_allocation * confidence
                    
                    allocations[symbol] = confidence_adjusted
                    logger.debug(f"Allocated {confidence_adjusted:.2%} to {symbol}")
            
            # Normalize if total exceeds max exposure
            total = sum(allocations.values())
            if total > self.max_total_exposure:
                scale_factor = self.max_total_exposure / total
                allocations = {k: v * scale_factor for k, v in allocations.items()}
                logger.info(f"Scaled allocations by {scale_factor:.2f} to respect max exposure")
            
            # Apply correlation adjustments if provided
            if correlations:
                allocations = self._adjust_for_correlations(allocations, correlations)
            
            return allocations
            
        except Exception as e:
            logger.error(f"Error allocating capital: {e}")
            return {}
    
    def _adjust_for_correlations(
        self,
        allocations: Dict[str, float],
        correlations: Dict[str, float],
        threshold: float = 0.8
    ) -> Dict[str, float]:
        """
        Adjust allocations based on correlation to reduce concentration risk.
        
        Args:
            allocations: Original allocation dict
            correlations: Correlation pairs
            threshold: Correlation threshold for adjustment
            
        Returns:
            Adjusted allocations
        """
        adjusted = allocations.copy()
        
        for pair, corr in correlations.items():
            if corr > threshold:
                parts = pair.split('_')
                if len(parts) == 2:
                    sym1, sym2 = parts[0], parts[1]
                    
                    # If both are allocated, reduce the smaller one
                    if sym1 in adjusted and sym2 in adjusted:
                        if adjusted[sym1] > adjusted[sym2]:
                            adjusted[sym2] *= 0.8  # Reduce by 20%
                            logger.info(f"Reduced {sym2} allocation due to high correlation with {sym1}")
                        else:
                            adjusted[sym1] *= 0.8
                            logger.info(f"Reduced {sym1} allocation due to high correlation with {sym2}")
        
        return adjusted
    
    def check_correlation(
        self,
        symbols: List[str],
        data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix to avoid over-concentration.
        
        Args:
            symbols: List of symbols to analyze
            data: Dict of {symbol: DataFrame with price data}
            
        Returns:
            Correlation matrix as DataFrame
        """
        try:
            # Build price dataframe
            prices = {}
            for symbol in symbols:
                if symbol in data and 'close' in data[symbol].columns:
                    prices[symbol] = data[symbol]['close']
            
            if len(prices) < 2:
                logger.warning("Not enough data for correlation analysis")
                return pd.DataFrame()
            
            # Calculate correlation
            prices_df = pd.DataFrame(prices)
            corr_matrix = prices_df.corr()
            
            logger.info(f"Calculated correlation matrix for {len(symbols)} symbols")
            return corr_matrix
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return pd.DataFrame()
    
    def suggest_rebalancing(
        self,
        current_allocations: Dict[str, float],
        target_allocations: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Suggest rebalancing actions if portfolio drifted from targets.
        
        Args:
            current_allocations: Current allocation percentages
            target_allocations: Target allocation percentages
            
        Returns:
            List of rebalancing suggestions
        """
        suggestions = []
        
        for symbol in target_allocations:
            current = current_allocations.get(symbol, 0.0)
            target = target_allocations[symbol]
            
            drift = abs(current - target)
            
            if drift > self.rebalance_threshold:
                if current > target:
                    action = 'reduce'
                    amount = current - target
                else:
                    action = 'increase'
                    amount = target - current
                
                suggestions.append({
                    'symbol': symbol,
                    'action': action,
                    'current': current,
                    'target': target,
                    'drift': drift,
                    'amount': amount,
                    'reason': f'Allocation drift {drift:.1%} exceeds threshold {self.rebalance_threshold:.1%}'
                })
        
        if suggestions:
            logger.info(f"Generated {len(suggestions)} rebalancing suggestions")
        
        return suggestions
    
    def get_portfolio_metrics(
        self,
        positions: Dict[str, float],
        total_capital: float
    ) -> Dict[str, Any]:
        """
        Calculate portfolio-level metrics.
        
        Args:
            positions: Dict of {symbol: position_value}
            total_capital: Total portfolio capital
            
        Returns:
            Portfolio metrics dictionary
        """
        if not positions:
            return {
                'total_exposure': 0.0,
                'num_positions': 0,
                'largest_position': None,
                'smallest_position': None,
                'average_position': 0.0
            }
        
        total_value = sum(positions.values())
        exposure = total_value / total_capital if total_capital > 0 else 0.0
        
        largest_symbol = max(positions.items(), key=lambda x: x[1])[0]
        smallest_symbol = min(positions.items(), key=lambda x: x[1])[0]
        
        return {
            'total_exposure': exposure,
            'num_positions': len(positions),
            'largest_position': largest_symbol,
            'largest_position_value': positions[largest_symbol],
            'smallest_position': smallest_symbol,
            'smallest_position_value': positions[smallest_symbol],
            'average_position': total_value / len(positions)
        }
