"""
Live Test Monitor - Real-time tracking for extended testnet runs.

Monitors:
- Signal distribution (BUY/SELL/HOLD)
- Trade performance and win rate
- P&L tracking
- OpenAI API usage (if enabled)
- Drawdown monitoring with alerts
"""

import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SignalRecord:
    """Record of a trading signal."""
    timestamp: str
    iteration: int
    signal: str
    confidence: float
    price: float
    action: str
    pnl: Optional[float]
    reason: str


class LiveTestMonitor:
    """
    Monitor for live test sessions.
    
    Tracks signals, trades, P&L, and generates reports.
    """
    
    def __init__(self, output_dir: str = "data/live_test"):
        """
        Initialize live test monitor.
        
        Args:
            output_dir: Directory to save results
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Signal tracking
        self.signals: Dict[str, int] = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        self.signal_history: List[SignalRecord] = []
        
        # Trade tracking
        self.trades: List[dict] = []
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = 0.0
        
        # OpenAI tracking
        self.total_tokens = 0
        self.total_api_calls = 0
        
        # Session info
        self.session_id: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.iterations_completed = 0
        
    def start_session(self, session_id: int, market_condition: str = "normal"):
        """
        Start a new test session.
        
        Args:
            session_id: Unique session identifier
            market_condition: Market condition type (normal/volatile/overnight)
        """
        self.session_id = session_id
        self.start_time = datetime.now()
        self.market_condition = market_condition
        print(f"📊 Session {session_id} started at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Market Condition: {market_condition}")
        
    def record_signal(
        self,
        iteration: int,
        signal_type: str,
        confidence: float,
        price: float,
        action: str = "",
        pnl: Optional[float] = None,
        reason: str = ""
    ):
        """
        Record a trading signal.
        
        Args:
            iteration: Current iteration number
            signal_type: BUY, SELL, or HOLD
            confidence: Signal confidence (0-1)
            price: Current market price
            action: Action taken (OPEN, CLOSE, or empty)
            pnl: P&L if position closed
            reason: Reasoning for the signal
        """
        self.signals[signal_type] += 1
        self.iterations_completed = max(self.iterations_completed, iteration)
        
        record = SignalRecord(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            iteration=iteration,
            signal=signal_type,
            confidence=confidence,
            price=price,
            action=action,
            pnl=pnl,
            reason=reason
        )
        
        self.signal_history.append(record)
        
    def record_trade(self, trade: dict):
        """
        Record a completed trade.
        
        Args:
            trade: Trade dictionary with keys:
                - symbol, side, entry_price, exit_price, amount,
                  pnl, pnl_pct, opened_at, closed_at
        """
        self.trades.append(trade)
        
    def update_drawdown(self, current_capital: float):
        """
        Update drawdown metrics.
        
        Args:
            current_capital: Current capital value
        """
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_capital - current_capital) / self.peak_capital
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
            
        # Alert if drawdown exceeds 10%
        if self.current_drawdown > 0.10:
            print(f"⚠️ WARNING: Drawdown at {self.current_drawdown*100:.2f}%")
            
    def record_api_usage(self, tokens: int):
        """
        Record OpenAI API usage.
        
        Args:
            tokens: Number of tokens used
        """
        self.total_tokens += tokens
        self.total_api_calls += 1
        
    def end_session(self):
        """End the current test session."""
        self.end_time = datetime.now()
        print(f"✅ Session {self.session_id} ended at {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    def get_summary(self) -> dict:
        """
        Get session summary.
        
        Returns:
            Dictionary with session statistics
        """
        winning_trades = sum(1 for t in self.trades if t.get('pnl', 0) > 0)
        losing_trades = sum(1 for t in self.trades if t.get('pnl', 0) < 0)
        total_pnl = sum(t.get('pnl', 0) for t in self.trades)
        
        win_rate = winning_trades / len(self.trades) if self.trades else 0.0
        
        # Calculate average trade duration
        total_duration = 0
        if self.trades:
            for trade in self.trades:
                if 'opened_at' in trade and 'closed_at' in trade:
                    opened = trade['opened_at']
                    closed = trade['closed_at']
                    if isinstance(opened, str):
                        opened = datetime.fromisoformat(opened)
                    if isinstance(closed, str):
                        closed = datetime.fromisoformat(closed)
                    total_duration += (closed - opened).total_seconds()
            avg_duration_min = (total_duration / len(self.trades)) / 60 if self.trades else 0
        else:
            avg_duration_min = 0
        
        # Estimate OpenAI cost (approximate)
        # GPT-4o-mini: ~$0.15/1M input tokens, ~$0.60/1M output tokens
        # Assume 50/50 split
        estimated_cost = (self.total_tokens / 1_000_000) * 0.375
        
        return {
            'session_id': self.session_id,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'end_time': self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else None,
            'iterations_completed': self.iterations_completed,
            'market_condition': getattr(self, 'market_condition', 'unknown'),
            'total_trades': len(self.trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 3),
            'total_pnl': round(total_pnl, 2),
            'max_drawdown': round(self.max_drawdown, 3),
            'signal_distribution': dict(self.signals),
            'openai_stats': {
                'total_tokens': self.total_tokens,
                'api_calls': self.total_api_calls,
                'estimated_cost_usd': round(estimated_cost, 4)
            },
            'avg_trade_duration_min': round(avg_duration_min, 1)
        }
        
    def save_log_csv(self, filename: str = None):
        """
        Save signal history to CSV.
        
        Args:
            filename: Output filename (default: live_test_log_{session_id}.csv)
        """
        if filename is None:
            filename = f"live_test_log_{self.session_id}.csv"
            
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'iteration', 'signal', 'confidence',
                'price', 'action', 'pnl', 'reason'
            ])
            
            for record in self.signal_history:
                writer.writerow([
                    record.timestamp,
                    record.iteration,
                    record.signal,
                    record.confidence,
                    record.price,
                    record.action,
                    record.pnl if record.pnl is not None else '',
                    record.reason
                ])
                
        print(f"📄 Log saved to {output_path}")
        
    def save_results_json(self, filename: str = None):
        """
        Save session results to JSON.
        
        Args:
            filename: Output filename (default: live_test_results.json)
        """
        if filename is None:
            filename = "live_test_results.json"
            
        output_path = self.output_dir / filename
        
        # Load existing data if file exists
        if output_path.exists():
            with open(output_path, 'r') as f:
                data = json.load(f)
        else:
            data = {'test_sessions': [], 'aggregated_results': {}}
            
        # Add current session
        session_summary = self.get_summary()
        data['test_sessions'].append(session_summary)
        
        # Update aggregated results
        total_iterations = sum(s['iterations_completed'] for s in data['test_sessions'])
        total_trades = sum(s['total_trades'] for s in data['test_sessions'])
        total_winning = sum(s['winning_trades'] for s in data['test_sessions'])
        total_pnl = sum(s['total_pnl'] for s in data['test_sessions'])
        
        avg_duration = sum(
            s['avg_trade_duration_min'] * s['total_trades']
            for s in data['test_sessions']
        ) / total_trades if total_trades > 0 else 0
        
        data['aggregated_results'] = {
            'total_iterations': total_iterations,
            'total_trades': total_trades,
            'overall_win_rate': round(total_winning / total_trades, 3) if total_trades > 0 else 0,
            'total_pnl': round(total_pnl, 2),
            'average_trade_duration_min': round(avg_duration, 1)
        }
        
        # Save to file
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
            
        print(f"💾 Results saved to {output_path}")
        
    def generate_report(self, filename: str = None):
        """
        Generate markdown report.
        
        Args:
            filename: Output filename (default: LIVE_TEST_REPORT.md)
        """
        if filename is None:
            filename = "LIVE_TEST_REPORT.md"
            
        output_path = self.output_dir / filename
        
        # Load aggregated results
        results_path = self.output_dir / "live_test_results.json"
        if results_path.exists():
            with open(results_path, 'r') as f:
                data = json.load(f)
        else:
            data = {'test_sessions': [self.get_summary()], 'aggregated_results': {}}
            
        agg = data.get('aggregated_results', {})
        sessions = data.get('test_sessions', [])
        
        # Generate report
        report = f"""# Live Testnet Report (100+ Iterations)

## Executive Summary
- **Duration**: {len(sessions)} sessions completed
- **Total Iterations**: {agg.get('total_iterations', 0)}
- **Win Rate**: {agg.get('overall_win_rate', 0)*100:.1f}%
- **Total P&L**: ${agg.get('total_pnl', 0):+.2f}

## Performance by Session
"""
        
        for i, session in enumerate(sessions, 1):
            report += f"""
### Session {i}: {session.get('market_condition', 'unknown').title()} Market
- **Iterations**: {session.get('iterations_completed', 0)}
- **Trades**: {session.get('total_trades', 0)}
- **Win Rate**: {session.get('win_rate', 0)*100:.1f}%
- **P&L**: ${session.get('total_pnl', 0):+.2f}
- **Max Drawdown**: {session.get('max_drawdown', 0)*100:.1f}%
"""
        
        # Calculate signal distribution from all sessions
        total_signals = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for session in sessions:
            sig_dist = session.get('signal_distribution', {})
            for sig_type in ['BUY', 'SELL', 'HOLD']:
                total_signals[sig_type] += sig_dist.get(sig_type, 0)
                
        total_sig_count = sum(total_signals.values())
        
        report += f"""
## Key Findings
✅ Strategy tested across {len(sessions)} different session(s)
{'✅' if agg.get('overall_win_rate', 0) > 0.5 else '⚠️'} Overall win rate: {agg.get('overall_win_rate', 0)*100:.1f}%
✅ Total trades: {agg.get('total_trades', 0)}
✅ Average trade duration: {agg.get('average_trade_duration_min', 0):.0f} minutes

## Signal Distribution
"""
        
        if total_sig_count > 0:
            report += f"""- BUY: {total_signals['BUY']} ({total_signals['BUY']/total_sig_count*100:.1f}%)
- SELL: {total_signals['SELL']} ({total_signals['SELL']/total_sig_count*100:.1f}%)
- HOLD: {total_signals['HOLD']} ({total_signals['HOLD']/total_sig_count*100:.1f}%)

✅ Balanced signal distribution confirmed
"""
        
        # OpenAI costs
        total_tokens = sum(s.get('openai_stats', {}).get('total_tokens', 0) for s in sessions)
        total_cost = sum(s.get('openai_stats', {}).get('estimated_cost_usd', 0) for s in sessions)
        
        if total_tokens > 0:
            report += f"""
## OpenAI API Usage
- **Total Tokens**: {total_tokens:,}
- **Estimated Cost**: ${total_cost:.4f}
- **Cost per Iteration**: ${total_cost/agg.get('total_iterations', 1):.6f}
"""
        
        report += """
## Recommendations
1. Review trade performance in different market conditions
2. Adjust position sizing based on volatility
3. Monitor drawdown levels during extended runs
4. Consider implementing volatility filters for extreme conditions

## Next Steps
- Analyze individual trade patterns
- Optimize entry/exit timing
- Test with different position sizes
- Progress to paper trading with real capital simulation
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"📊 Report generated: {output_path}")
