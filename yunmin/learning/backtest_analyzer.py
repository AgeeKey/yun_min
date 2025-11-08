"""
Backtest Analyzer - Analyzes Historical Trading Performance

Analyzes backtest results to extract insights and patterns.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger


class BacktestAnalyzer:
    """
    Analyzes backtest results to learn from past performance.
    
    Extracts:
    - Winning patterns
    - Common mistakes
    - Optimal parameters
    - Market regime performance
    """
    
    def __init__(self):
        """Initialize backtest analyzer."""
        self.trade_results: List[Dict[str, Any]] = []
        logger.info("📈 Backtest Analyzer initialized")
    
    def add_trade_result(self, trade: Dict[str, Any]):
        """
        Add a completed trade for analysis.
        
        Args:
            trade: Trade details with entry, exit, pnl, context
        """
        self.trade_results.append(trade)
    
    def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyze overall backtest performance.
        
        Returns:
            Performance metrics dictionary
        """
        if not self.trade_results:
            return self._empty_analysis()
        
        df = pd.DataFrame(self.trade_results)
        
        # Basic metrics
        total_trades = len(df)
        winning_trades = len(df[df['pnl'] > 0])
        losing_trades = len(df[df['pnl'] < 0])
        
        total_pnl = df['pnl'].sum()
        avg_win = df[df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = df[df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Risk metrics
        returns = df['pnl'].values
        sharpe_ratio = self._calculate_sharpe(returns)
        max_drawdown = self._calculate_max_drawdown(returns)
        
        # Profit factor
        total_wins = df[df['pnl'] > 0]['pnl'].sum()
        total_losses = abs(df[df['pnl'] < 0]['pnl'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'expectancy': df['pnl'].mean()
        }
    
    def find_winning_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """
        Find patterns that consistently lead to wins.
        
        Args:
            min_occurrences: Minimum number of occurrences
            
        Returns:
            List of winning patterns
        """
        if not self.trade_results:
            return []
        
        df = pd.DataFrame(self.trade_results)
        winning_df = df[df['pnl'] > 0]
        
        patterns = []
        
        # Pattern 1: RSI levels
        rsi_patterns = self._analyze_rsi_patterns(winning_df, min_occurrences)
        patterns.extend(rsi_patterns)
        
        # Pattern 2: Trend conditions
        trend_patterns = self._analyze_trend_patterns(winning_df, min_occurrences)
        patterns.extend(trend_patterns)
        
        # Pattern 3: Volatility conditions
        vol_patterns = self._analyze_volatility_patterns(winning_df, min_occurrences)
        patterns.extend(vol_patterns)
        
        logger.info(f"Found {len(patterns)} winning patterns")
        return patterns
    
    def find_common_mistakes(self) -> List[Dict[str, Any]]:
        """
        Identify common mistakes in losing trades.
        
        Returns:
            List of common mistakes
        """
        if not self.trade_results:
            return []
        
        df = pd.DataFrame(self.trade_results)
        losing_df = df[df['pnl'] < 0]
        
        if len(losing_df) == 0:
            return []
        
        mistakes = []
        
        # Mistake 1: Trading in high volatility
        high_vol_losses = losing_df[losing_df.get('volatility', 0) > 0.04]
        if len(high_vol_losses) > len(losing_df) * 0.3:
            mistakes.append({
                'type': 'high_volatility',
                'description': 'Too many losses in high volatility conditions',
                'frequency': len(high_vol_losses) / len(losing_df),
                'avg_loss': high_vol_losses['pnl'].mean()
            })
        
        # Mistake 2: Trading against trend
        if 'trend' in losing_df.columns:
            against_trend = losing_df[
                ((losing_df['side'] == 'BUY') & (losing_df['trend'] == 'bearish')) |
                ((losing_df['side'] == 'SELL') & (losing_df['trend'] == 'bullish'))
            ]
            if len(against_trend) > 0:
                mistakes.append({
                    'type': 'against_trend',
                    'description': 'Trading against the trend',
                    'frequency': len(against_trend) / len(losing_df),
                    'avg_loss': against_trend['pnl'].mean()
                })
        
        # Mistake 3: Low volume trades
        if 'volume_ratio' in losing_df.columns:
            low_volume = losing_df[losing_df['volume_ratio'] < 0.7]
            if len(low_volume) > len(losing_df) * 0.3:
                mistakes.append({
                    'type': 'low_volume',
                    'description': 'Trading on low volume',
                    'frequency': len(low_volume) / len(losing_df),
                    'avg_loss': low_volume['pnl'].mean()
                })
        
        logger.info(f"Identified {len(mistakes)} common mistakes")
        return mistakes
    
    def _analyze_rsi_patterns(
        self,
        winning_df: pd.DataFrame,
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """Analyze RSI-based winning patterns."""
        patterns = []
        
        if 'rsi' not in winning_df.columns:
            return patterns
        
        # Oversold bounces
        oversold_buys = winning_df[
            (winning_df['side'] == 'BUY') & (winning_df['rsi'] < 35)
        ]
        if len(oversold_buys) >= min_occurrences:
            patterns.append({
                'name': 'oversold_bounce',
                'condition': 'RSI < 35 + BUY',
                'occurrences': len(oversold_buys),
                'win_rate': 1.0,  # All in winning_df
                'avg_pnl': oversold_buys['pnl'].mean()
            })
        
        # Overbought shorts
        overbought_sells = winning_df[
            (winning_df['side'] == 'SELL') & (winning_df['rsi'] > 65)
        ]
        if len(overbought_sells) >= min_occurrences:
            patterns.append({
                'name': 'overbought_short',
                'condition': 'RSI > 65 + SELL',
                'occurrences': len(overbought_sells),
                'win_rate': 1.0,
                'avg_pnl': overbought_sells['pnl'].mean()
            })
        
        return patterns
    
    def _analyze_trend_patterns(
        self,
        winning_df: pd.DataFrame,
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """Analyze trend-based winning patterns."""
        patterns = []
        
        if 'trend' not in winning_df.columns:
            return patterns
        
        # Trend following
        trend_following = winning_df[
            ((winning_df['side'] == 'BUY') & (winning_df['trend'] == 'bullish')) |
            ((winning_df['side'] == 'SELL') & (winning_df['trend'] == 'bearish'))
        ]
        if len(trend_following) >= min_occurrences:
            patterns.append({
                'name': 'trend_following',
                'condition': 'Trade with the trend',
                'occurrences': len(trend_following),
                'win_rate': 1.0,
                'avg_pnl': trend_following['pnl'].mean()
            })
        
        return patterns
    
    def _analyze_volatility_patterns(
        self,
        winning_df: pd.DataFrame,
        min_occurrences: int
    ) -> List[Dict[str, Any]]:
        """Analyze volatility-based winning patterns."""
        patterns = []
        
        if 'volatility' not in winning_df.columns:
            return patterns
        
        # Moderate volatility trades
        moderate_vol = winning_df[
            (winning_df['volatility'] > 0.015) & (winning_df['volatility'] < 0.04)
        ]
        if len(moderate_vol) >= min_occurrences:
            patterns.append({
                'name': 'moderate_volatility',
                'condition': '1.5% < volatility < 4%',
                'occurrences': len(moderate_vol),
                'win_rate': 1.0,
                'avg_pnl': moderate_vol['pnl'].mean()
            })
        
        return patterns
    
    def _calculate_sharpe(self, returns: np.ndarray, risk_free: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        
        excess_returns = returns - risk_free
        return np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown."""
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        
        return float(np.min(drawdown)) if len(drawdown) > 0 else 0.0
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis when no data."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'expectancy': 0.0
        }
