"""
Correlation Analyzer - Cross-Asset Correlation Analysis

Analyzes correlations between different assets for portfolio diversification.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from loguru import logger


class CorrelationAnalyzer:
    """
    Analyzes correlations between trading assets.
    
    Used for:
    - Portfolio diversification
    - Risk assessment
    - Market regime detection
    """
    
    def __init__(self):
        """Initialize correlation analyzer."""
        self.correlation_cache: Dict[str, pd.DataFrame] = {}
        logger.info("🔗 Correlation Analyzer initialized")
    
    def calculate_correlation(
        self,
        prices_data: Dict[str, pd.Series],
        method: str = 'pearson'
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix between assets.
        
        Args:
            prices_data: Dictionary of {symbol: price_series}
            method: Correlation method ('pearson', 'spearman', 'kendall')
            
        Returns:
            Correlation matrix as DataFrame
        """
        if not prices_data or len(prices_data) < 2:
            return pd.DataFrame()
        
        # Combine into DataFrame
        df = pd.DataFrame(prices_data)
        
        # Calculate returns
        returns = df.pct_change().dropna()
        
        # Calculate correlation
        correlation_matrix = returns.corr(method=method)
        
        logger.debug(f"Calculated correlation for {len(prices_data)} assets")
        return correlation_matrix
    
    def get_diversification_score(
        self,
        symbols: List[str],
        correlation_matrix: pd.DataFrame
    ) -> float:
        """
        Calculate diversification score for a set of symbols.
        
        Args:
            symbols: List of symbols in portfolio
            correlation_matrix: Pre-calculated correlation matrix
            
        Returns:
            Diversification score (0-100, higher is better)
        """
        if len(symbols) < 2:
            return 100.0  # Single asset is "perfectly diversified" by definition
        
        # Get correlations for selected symbols
        try:
            subset_corr = correlation_matrix.loc[symbols, symbols]
            
            # Calculate average correlation (excluding diagonal)
            mask = ~np.eye(len(symbols), dtype=bool)
            avg_correlation = subset_corr.values[mask].mean()
            
            # Score: 100 = uncorrelated (0), 0 = perfectly correlated (1)
            score = (1 - avg_correlation) * 100
            
            return max(0, min(100, score))
        
        except Exception as e:
            logger.warning(f"Could not calculate diversification score: {e}")
            return 50.0  # Neutral score
    
    def find_uncorrelated_assets(
        self,
        base_symbol: str,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.3,
        top_k: int = 3
    ) -> List[str]:
        """
        Find assets least correlated with base symbol.
        
        Args:
            base_symbol: Reference symbol
            correlation_matrix: Pre-calculated correlation matrix
            threshold: Maximum correlation threshold
            top_k: Number of assets to return
            
        Returns:
            List of uncorrelated symbols
        """
        if base_symbol not in correlation_matrix.index:
            return []
        
        # Get correlations with base symbol
        correlations = correlation_matrix[base_symbol].abs()
        
        # Exclude self
        correlations = correlations[correlations.index != base_symbol]
        
        # Find least correlated
        uncorrelated = correlations[correlations < threshold].sort_values()
        
        return uncorrelated.head(top_k).index.tolist()
    
    def detect_market_regime(
        self,
        correlation_matrix: pd.DataFrame,
        historical_avg: float = 0.5
    ) -> str:
        """
        Detect market regime based on average correlation.
        
        High correlation = risk-off, crisis mode
        Low correlation = normal market conditions
        
        Args:
            correlation_matrix: Current correlation matrix
            historical_avg: Historical average correlation
            
        Returns:
            Market regime ('crisis', 'risk_off', 'normal', 'risk_on')
        """
        # Calculate average correlation
        mask = ~np.eye(len(correlation_matrix), dtype=bool)
        avg_corr = correlation_matrix.values[mask].mean()
        
        if avg_corr > 0.8:
            regime = 'crisis'
        elif avg_corr > historical_avg + 0.2:
            regime = 'risk_off'
        elif avg_corr < historical_avg - 0.2:
            regime = 'risk_on'
        else:
            regime = 'normal'
        
        logger.debug(f"Market regime: {regime} (avg_corr={avg_corr:.2f})")
        return regime
    
    def generate_sample_correlations(
        self,
        symbols: List[str]
    ) -> pd.DataFrame:
        """
        Generate sample correlation matrix for testing.
        
        Args:
            symbols: List of symbols
            
        Returns:
            Random correlation matrix
        """
        n = len(symbols)
        
        # Generate random correlation matrix
        random_matrix = np.random.rand(n, n)
        # Make symmetric
        random_matrix = (random_matrix + random_matrix.T) / 2
        # Set diagonal to 1
        np.fill_diagonal(random_matrix, 1.0)
        
        # Scale to realistic range (0.2 to 0.8)
        random_matrix = 0.2 + random_matrix * 0.6
        np.fill_diagonal(random_matrix, 1.0)
        
        df = pd.DataFrame(random_matrix, index=symbols, columns=symbols)
        
        return df
