"""
Multi-asset correlation analysis.

Helps avoid over-concentration in correlated assets and provides
diversification recommendations for portfolio management.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from loguru import logger


class CorrelationAnalyzer:
    """
    Analyzes correlation between multiple trading symbols.
    
    Helps portfolio managers avoid over-concentration in highly
    correlated assets and optimize diversification.
    """
    
    def __init__(self, window: int = 100):
        """
        Initialize correlation analyzer.
        
        Args:
            window: Rolling window size for correlation calculation
        """
        self.window = window
        logger.info(f"📊 Correlation Analyzer initialized (window={window})")
    
    def calculate_rolling_correlation(
        self, 
        data: Dict[str, pd.DataFrame]
    ) -> Dict[str, float]:
        """
        Calculate rolling correlation between symbols.
        
        Args:
            data: Dictionary of {symbol: DataFrame with 'close' column}
            
        Returns:
            Dictionary of correlation pairs and their values
            Format: {f"{sym1}_{sym2}": correlation_value}
        """
        if not data or len(data) < 2:
            logger.warning("Not enough symbols for correlation analysis")
            return {}
        
        correlations = {}
        symbols = list(data.keys())
        
        try:
            for i, sym1 in enumerate(symbols):
                for sym2 in symbols[i+1:]:  # Avoid duplicates and self-correlation
                    if 'close' not in data[sym1].columns or 'close' not in data[sym2].columns:
                        logger.warning(f"Missing 'close' column for {sym1} or {sym2}")
                        continue
                    
                    # Align dataframes by index
                    df1 = data[sym1]['close']
                    df2 = data[sym2]['close']
                    
                    # Calculate rolling correlation
                    if len(df1) >= self.window and len(df2) >= self.window:
                        corr = df1.rolling(window=self.window).corr(df2)
                        
                        # Get the most recent correlation value
                        if not corr.empty and not pd.isna(corr.iloc[-1]):
                            pair_key = f"{sym1}_{sym2}"
                            correlations[pair_key] = float(corr.iloc[-1])
                            logger.debug(f"Correlation {pair_key}: {correlations[pair_key]:.3f}")
                        else:
                            logger.warning(f"Could not calculate correlation for {sym1}_{sym2}")
                    else:
                        logger.warning(
                            f"Insufficient data for {sym1}_{sym2}: "
                            f"need {self.window}, have {len(df1)}/{len(df2)}"
                        )
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            return {}
    
    def calculate_correlation_matrix(
        self, 
        data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Calculate full correlation matrix for all symbols.
        
        Args:
            data: Dictionary of {symbol: DataFrame with 'close' column}
            
        Returns:
            Correlation matrix as DataFrame
        """
        if not data or len(data) < 2:
            return pd.DataFrame()
        
        try:
            # Create a DataFrame with all close prices
            prices = pd.DataFrame({
                symbol: df['close'] 
                for symbol, df in data.items()
                if 'close' in df.columns
            })
            
            # Calculate correlation matrix
            if not prices.empty:
                corr_matrix = prices.corr()
                logger.info(f"Calculated correlation matrix for {len(prices.columns)} symbols")
                return corr_matrix
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()
    
    def suggest_diversification(
        self, 
        positions: Dict[str, float],
        correlations: Dict[str, float],
        threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Suggest position adjustments based on correlation.
        
        If two symbols are highly correlated (>threshold), suggests
        reducing one position to avoid concentration risk.
        
        Args:
            positions: Dictionary of {symbol: position_size}
            correlations: Dictionary of {pair: correlation_value}
            threshold: Correlation threshold for high correlation warning
            
        Returns:
            List of diversification suggestions
        """
        suggestions = []
        
        if not positions or not correlations:
            return suggestions
        
        try:
            for pair, corr_value in correlations.items():
                if corr_value > threshold:
                    # Split pair into individual symbols
                    parts = pair.split('_')
                    if len(parts) == 2:
                        sym1, sym2 = parts[0], parts[1]
                        
                        # Check if both symbols are in positions
                        if sym1 in positions and sym2 in positions:
                            # Suggest reducing the smaller position
                            if positions[sym1] > positions[sym2]:
                                reduce_symbol = sym2
                            else:
                                reduce_symbol = sym1
                            
                            suggestion = {
                                'action': 'reduce',
                                'symbol': reduce_symbol,
                                'reason': f'High {sym1}-{sym2} correlation ({corr_value:.2f})',
                                'recommendation': f'Reduce {reduce_symbol} position by 20%',
                                'correlation': corr_value,
                                'pair': [sym1, sym2]
                            }
                            suggestions.append(suggestion)
                            logger.info(
                                f"⚠️  Diversification alert: {sym1}-{sym2} "
                                f"correlation {corr_value:.2f} > {threshold}"
                            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating diversification suggestions: {e}")
            return []
    
    def calculate_diversification_score(
        self,
        correlations: Dict[str, float]
    ) -> float:
        """
        Calculate overall portfolio diversification score.
        
        Score ranges from 0 (all assets perfectly correlated) to 1 
        (all assets perfectly uncorrelated).
        
        Args:
            correlations: Dictionary of correlation pairs
            
        Returns:
            Diversification score (0-1)
        """
        if not correlations:
            return 0.0
        
        try:
            # Average absolute correlation
            avg_corr = np.mean([abs(v) for v in correlations.values()])
            
            # Diversification score is inverse of correlation
            # 0 correlation = 1.0 score (perfect diversification)
            # 1 correlation = 0.0 score (no diversification)
            score = 1.0 - avg_corr
            
            logger.debug(f"Diversification score: {score:.3f} (avg corr: {avg_corr:.3f})")
            return float(score)
            
        except Exception as e:
            logger.error(f"Error calculating diversification score: {e}")
            return 0.0
    
    def get_correlation_report(
        self,
        data: Dict[str, pd.DataFrame],
        positions: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive correlation report.
        
        Args:
            data: Dictionary of {symbol: DataFrame}
            positions: Optional dictionary of current positions
            
        Returns:
            Correlation report with metrics and suggestions
        """
        correlations = self.calculate_rolling_correlation(data)
        corr_matrix = self.calculate_correlation_matrix(data)
        diversification_score = self.calculate_diversification_score(correlations)
        
        report = {
            'correlations': correlations,
            'correlation_matrix': corr_matrix.to_dict() if not corr_matrix.empty else {},
            'diversification_score': diversification_score,
            'suggestions': []
        }
        
        if positions:
            report['suggestions'] = self.suggest_diversification(
                positions, 
                correlations
            )
        
        logger.info(f"📊 Correlation report generated: {len(correlations)} pairs analyzed")
        return report
