"""
Pattern Library - Recurring Market Patterns Database

Stores and classifies recurring market patterns discovered through analysis.
Provides pattern recognition and success statistics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from loguru import logger


class PatternType(Enum):
    """Types of market patterns."""
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    TREND_REVERSAL = "trend_reversal"  # Alias for REVERSAL
    CONSOLIDATION = "consolidation"
    TREND_CONTINUATION = "trend_continuation"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_shoulders"
    TRIANGLE = "triangle"
    FLAG = "flag"
    WEDGE = "wedge"
    UNKNOWN = "unknown"


class PatternLibrary:
    """
    Library of recurring market patterns.
    
    Stores patterns discovered through backtesting and live trading.
    Tracks success rates and optimal parameters for each pattern.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize pattern library.
        
        Args:
            storage_path: Path to persist pattern library
        """
        self.storage_path = Path(storage_path) if storage_path else Path("data/patterns")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Pattern storage
        self.patterns: Dict[str, Dict[str, Any]] = {}
        
        # Load existing patterns
        self._load()
        
        logger.info(f"📖 Pattern library initialized with {len(self.patterns)} patterns")
    
    def add_pattern(
        self,
        pattern_type: PatternType,
        context: Dict[str, Any],
        outcome: Dict[str, Any],
        pattern_id: Optional[str] = None
    ) -> str:
        """
        Add a new pattern occurrence.
        
        Args:
            pattern_type: Type of pattern
            context: Market context when pattern occurred
            outcome: Outcome of trading this pattern
            pattern_id: Optional specific ID for the pattern instance
            
        Returns:
            Pattern ID
        """
        if pattern_id is None:
            pattern_id = f"{pattern_type.value}_{len(self.patterns)}"
        
        pattern_data = {
            'type': pattern_type.value,
            'context': context,
            'outcome': outcome,
            'timestamp': datetime.now().isoformat(),
            'occurrences': 1,
            'total_pnl': outcome.get('pnl', 0.0),
            'successes': 1 if outcome.get('pnl', 0.0) > 0 else 0
        }
        
        # If pattern already exists, update statistics
        if pattern_id in self.patterns:
            existing = self.patterns[pattern_id]
            existing['occurrences'] += 1
            existing['total_pnl'] += outcome.get('pnl', 0.0)
            if outcome.get('pnl', 0.0) > 0:
                existing['successes'] += 1
            existing['last_seen'] = datetime.now().isoformat()
        else:
            self.patterns[pattern_id] = pattern_data
        
        logger.debug(f"📝 Added pattern occurrence: {pattern_id}")
        return pattern_id
    
    def get_pattern_statistics(self, pattern_type: PatternType) -> Dict[str, Any]:
        """
        Get statistics for a specific pattern type.
        
        Args:
            pattern_type: Type of pattern
            
        Returns:
            Statistics dictionary
        """
        matching_patterns = [
            p for p in self.patterns.values()
            if p['type'] == pattern_type.value
        ]
        
        if not matching_patterns:
            return {
                'pattern_type': pattern_type.value,
                'count': 0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'total_occurrences': 0
            }
        
        total_occurrences = sum(p['occurrences'] for p in matching_patterns)
        total_successes = sum(p['successes'] for p in matching_patterns)
        total_pnl = sum(p['total_pnl'] for p in matching_patterns)
        
        return {
            'pattern_type': pattern_type.value,
            'count': len(matching_patterns),
            'win_rate': total_successes / total_occurrences if total_occurrences > 0 else 0.0,
            'avg_pnl': total_pnl / total_occurrences if total_occurrences > 0 else 0.0,
            'total_occurrences': total_occurrences
        }
    
    def find_matching_patterns(
        self,
        current_context: Dict[str, Any],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find patterns matching current market context.
        
        Args:
            current_context: Current market conditions
            top_k: Number of matches to return
            
        Returns:
            List of matching patterns with statistics
        """
        # Simple matching based on similar indicators
        matches = []
        
        current_rsi = current_context.get('indicators', {}).get('rsi', 50)
        current_trend = current_context.get('trend', 'neutral')
        
        for pattern_id, pattern in self.patterns.items():
            pattern_context = pattern.get('context', {})
            pattern_rsi = pattern_context.get('indicators', {}).get('rsi', 50)
            pattern_trend = pattern_context.get('trend', 'neutral')
            
            # Simple similarity score
            similarity = 0.0
            
            # RSI similarity (0-1)
            rsi_diff = abs(current_rsi - pattern_rsi) / 100.0
            similarity += (1.0 - rsi_diff) * 0.4
            
            # Trend similarity
            if current_trend == pattern_trend:
                similarity += 0.6
            
            if similarity > 0.3:  # Threshold
                win_rate = pattern['successes'] / pattern['occurrences']
                matches.append({
                    'pattern_id': pattern_id,
                    'pattern_type': pattern['type'],
                    'similarity': similarity,
                    'win_rate': win_rate,
                    'avg_pnl': pattern['total_pnl'] / pattern['occurrences'],
                    'occurrences': pattern['occurrences'],
                    'context': pattern['context']
                })
        
        # Sort by similarity * win_rate
        matches.sort(key=lambda x: x['similarity'] * x['win_rate'], reverse=True)
        
        return matches[:top_k]
    
    def get_best_patterns(self, min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """
        Get best performing patterns.
        
        Args:
            min_occurrences: Minimum number of occurrences to be considered
            
        Returns:
            List of best patterns sorted by win rate
        """
        reliable_patterns = [
            {
                'pattern_id': pid,
                'pattern_type': p['type'],
                'win_rate': p['successes'] / p['occurrences'],
                'avg_pnl': p['total_pnl'] / p['occurrences'],
                'occurrences': p['occurrences'],
                'context': p['context']
            }
            for pid, p in self.patterns.items()
            if p['occurrences'] >= min_occurrences
        ]
        
        # Sort by win rate
        reliable_patterns.sort(key=lambda x: x['win_rate'], reverse=True)
        
        return reliable_patterns
    
    def save(self) -> None:
        """Save pattern library to disk."""
        try:
            with open(self.storage_path / 'patterns.json', 'w') as f:
                json.dump(self.patterns, f, indent=2)
            
            logger.info(f"💾 Pattern library saved ({len(self.patterns)} patterns)")
        except Exception as e:
            logger.error(f"Failed to save pattern library: {e}")
    
    def _load(self) -> None:
        """Load pattern library from disk."""
        try:
            pattern_file = self.storage_path / 'patterns.json'
            if pattern_file.exists():
                with open(pattern_file, 'r') as f:
                    self.patterns = json.load(f)
                
                logger.info(f"📂 Loaded pattern library with {len(self.patterns)} patterns")
            else:
                logger.info("No existing pattern library found, starting fresh")
        except Exception as e:
            logger.warning(f"Could not load pattern library: {e}, starting fresh")
    
    def clear(self) -> None:
        """Clear all patterns."""
        self.patterns = {}
        logger.info("🧹 Pattern library cleared")
    
    def __len__(self) -> int:
        """Return number of unique patterns."""
        return len(self.patterns)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PatternLibrary(patterns={len(self.patterns)})"
