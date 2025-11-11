"""
Telemetry module for saving backtest artifacts.

Saves:
- Per-trade CSV with detailed trade information
- Equity curve CSV
- Summary JSON with performance metrics
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class BacktestTelemetry:
    """
    Handles saving backtest artifacts to disk.
    
    Creates:
    - artifacts/trades_YYYYMMDD_HHMMSS.csv
    - artifacts/equity_curve_YYYYMMDD_HHMMSS.csv
    - artifacts/summary_YYYYMMDD_HHMMSS.json
    """
    
    def __init__(self, output_dir: str = "artifacts"):
        """
        Initialize telemetry with output directory.
        
        Args:
            output_dir: Directory to save artifacts (default: "artifacts")
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Telemetry initialized - artifacts will be saved to {self.output_dir}")
    
    def save_trades(
        self,
        trades: List[Dict[str, Any]],
        filename: Optional[str] = None
    ) -> Path:
        """
        Save per-trade data to CSV.
        
        Args:
            trades: List of trade dictionaries
            filename: Optional custom filename (default: trades_{timestamp}.csv)
            
        Returns:
            Path to saved CSV file
        """
        if not trades:
            logger.warning("No trades to save")
            return None
        
        # Convert trades to DataFrame
        trades_data = []
        for trade in trades:
            trade_record = {
                'entry_time': trade.get('entry_time', ''),
                'entry_price': trade.get('entry_price', 0.0),
                'exit_time': trade.get('exit_time', ''),
                'exit_price': trade.get('exit_price', 0.0),
                'size': trade.get('amount', trade.get('size', 0.0)),
                'pnl_usd': trade.get('pnl', 0.0),
                'pnl_pct': trade.get('pnl_pct', trade.get('return', 0.0) * 100),
                'confidence': trade.get('signal_confidence', trade.get('confidence', 0.0)),
                'reasons': trade.get('reasons', trade.get('signal_reason', ''))
            }
            trades_data.append(trade_record)
        
        df = pd.DataFrame(trades_data)
        
        # Save to CSV
        if filename is None:
            filename = f"trades_{self.timestamp}.csv"
        
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        
        logger.info(f"Saved {len(trades)} trades to {output_path}")
        return output_path
    
    def save_equity_curve(
        self,
        equity_curve: List[float],
        filename: Optional[str] = None
    ) -> Path:
        """
        Save equity curve to CSV.
        
        Args:
            equity_curve: List of equity values
            filename: Optional custom filename (default: equity_curve_{timestamp}.csv)
            
        Returns:
            Path to saved CSV file
        """
        if not equity_curve:
            logger.warning("No equity curve to save")
            return None
        
        # Create DataFrame
        df = pd.DataFrame({
            'step': range(len(equity_curve)),
            'equity': equity_curve
        })
        
        # Save to CSV
        if filename is None:
            filename = f"equity_curve_{self.timestamp}.csv"
        
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        
        logger.info(f"Saved equity curve ({len(equity_curve)} points) to {output_path}")
        return output_path
    
    def save_summary(
        self,
        summary: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Save summary metrics to JSON.
        
        Args:
            summary: Dictionary with performance metrics
            filename: Optional custom filename (default: summary_{timestamp}.json)
            
        Returns:
            Path to saved JSON file
        """
        if not summary:
            logger.warning("No summary to save")
            return None
        
        # Add metadata
        full_summary = {
            'metadata': {
                'timestamp': self.timestamp,
                'generated_at': datetime.now().isoformat()
            },
            'metrics': summary
        }
        
        # Save to JSON
        if filename is None:
            filename = f"summary_{self.timestamp}.json"
        
        output_path = self.output_dir / filename
        with open(output_path, 'w') as f:
            json.dump(full_summary, f, indent=2, default=str)
        
        logger.info(f"Saved summary to {output_path}")
        return output_path
    
    def save_all(
        self,
        trades: List[Dict[str, Any]],
        equity_curve: List[float],
        summary: Dict[str, Any]
    ) -> Dict[str, Path]:
        """
        Save all backtest artifacts at once.
        
        Args:
            trades: List of trade dictionaries
            equity_curve: List of equity values
            summary: Dictionary with performance metrics
            
        Returns:
            Dictionary with paths to all saved files
        """
        paths = {}
        
        paths['trades'] = self.save_trades(trades)
        paths['equity_curve'] = self.save_equity_curve(equity_curve)
        paths['summary'] = self.save_summary(summary)
        
        logger.info("All artifacts saved successfully")
        return paths
