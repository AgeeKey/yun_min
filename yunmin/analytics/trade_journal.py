"""
Trade Journal & Post-Trade Analysis

Comprehensive logging and analysis of all trades with post-mortem insights.
Tracks trade metadata, pre/post-trade state, and generates weekly reviews.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
from loguru import logger


class TradeOutcome(Enum):
    """Trade outcome classification."""
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


class CloseReason(Enum):
    """Reason for closing a trade."""
    TAKE_PROFIT = "take_profit"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"
    TIMEOUT = "timeout"
    STRATEGY_SIGNAL = "strategy_signal"
    EMERGENCY = "emergency"
    RISK_LIMIT = "risk_limit"


@dataclass
class PreTradeState:
    """State captured before opening a trade."""
    timestamp: datetime
    capital: float
    portfolio_value: float
    open_positions_count: int
    
    # Market conditions
    price: float
    volatility: float
    market_regime: str
    
    # Indicators
    indicators: Dict[str, float] = field(default_factory=dict)
    
    # AI signals (if available)
    ai_confidence: Optional[float] = None
    ai_reasoning: Optional[str] = None
    
    # Why this trade?
    entry_reason: str = ""


@dataclass
class PostTradeState:
    """State captured after closing a trade."""
    timestamp: datetime
    capital: float
    portfolio_value: float
    
    # Exit conditions
    exit_price: float
    close_reason: CloseReason
    
    # Performance
    pnl: float
    pnl_percentage: float
    holding_duration_seconds: float
    
    # What happened?
    what_went_right: List[str] = field(default_factory=list)
    what_went_wrong: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)


@dataclass
class TradeRecord:
    """Complete record of a trade."""
    trade_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    
    # Trade lifecycle
    pre_trade: PreTradeState
    post_trade: Optional[PostTradeState] = None
    
    # Categorization
    outcome: Optional[TradeOutcome] = None
    tags: List[str] = field(default_factory=list)
    
    @property
    def is_closed(self) -> bool:
        """Check if trade is closed."""
        return self.post_trade is not None
    
    @property
    def duration_hours(self) -> float:
        """Get trade duration in hours."""
        if self.post_trade:
            return self.post_trade.holding_duration_seconds / 3600
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.pre_trade:
            data['pre_trade']['timestamp'] = self.pre_trade.timestamp.isoformat()
        if self.post_trade:
            data['post_trade']['timestamp'] = self.post_trade.timestamp.isoformat()
            data['post_trade']['close_reason'] = self.post_trade.close_reason.value
        if self.outcome:
            data['outcome'] = self.outcome.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        pre_trade_data = data['pre_trade']
        pre_trade_data['timestamp'] = datetime.fromisoformat(pre_trade_data['timestamp'])
        pre_trade = PreTradeState(**pre_trade_data)
        
        post_trade = None
        if data.get('post_trade'):
            post_trade_data = data['post_trade']
            post_trade_data['timestamp'] = datetime.fromisoformat(post_trade_data['timestamp'])
            post_trade_data['close_reason'] = CloseReason(post_trade_data['close_reason'])
            post_trade = PostTradeState(**post_trade_data)
        
        outcome = TradeOutcome(data['outcome']) if data.get('outcome') else None
        
        return cls(
            trade_id=data['trade_id'],
            symbol=data['symbol'],
            side=data['side'],
            size=data['size'],
            pre_trade=pre_trade,
            post_trade=post_trade,
            outcome=outcome,
            tags=data.get('tags', [])
        )


@dataclass
class WeeklyReview:
    """Weekly trading performance review."""
    week_start: datetime
    week_end: datetime
    
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    
    total_pnl: float
    win_rate: float
    
    best_trades: List[TradeRecord] = field(default_factory=list)
    worst_trades: List[TradeRecord] = field(default_factory=list)
    
    common_mistakes: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            f"# Weekly Trading Review",
            f"**Period:** {self.week_start.strftime('%Y-%m-%d')} to {self.week_end.strftime('%Y-%m-%d')}",
            "",
            "## Summary",
            f"- **Total Trades:** {self.total_trades}",
            f"- **Win Rate:** {self.win_rate:.1%}",
            f"- **Total P&L:** ${self.total_pnl:.2f}",
            f"- **Winners:** {self.winning_trades}",
            f"- **Losers:** {self.losing_trades}",
            f"- **Breakeven:** {self.breakeven_trades}",
            "",
        ]
        
        if self.best_trades:
            lines.append("## 🏆 Top 5 Winners")
            for i, trade in enumerate(self.best_trades[:5], 1):
                if trade.post_trade:
                    lines.append(
                        f"{i}. **{trade.symbol}** - P&L: ${trade.post_trade.pnl:.2f} "
                        f"({trade.post_trade.pnl_percentage:.2f}%) - "
                        f"{trade.pre_trade.entry_reason}"
                    )
            lines.append("")
        
        if self.worst_trades:
            lines.append("## 📉 Top 5 Losers")
            for i, trade in enumerate(self.worst_trades[:5], 1):
                if trade.post_trade:
                    lines.append(
                        f"{i}. **{trade.symbol}** - P&L: ${trade.post_trade.pnl:.2f} "
                        f"({trade.post_trade.pnl_percentage:.2f}%) - "
                        f"Reason: {trade.post_trade.close_reason.value}"
                    )
            lines.append("")
        
        if self.common_mistakes:
            lines.append("## ⚠️ Common Mistakes")
            for mistake in self.common_mistakes:
                lines.append(f"- {mistake}")
            lines.append("")
        
        if self.improvement_suggestions:
            lines.append("## 💡 Improvement Suggestions")
            for suggestion in self.improvement_suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")
        
        return "\n".join(lines)


class TradeJournal:
    """
    Comprehensive trade journal for logging and analyzing trades.
    
    Features:
    - Detailed pre-trade and post-trade logging
    - Automated trade analysis
    - Weekly performance reviews
    - Export to markdown/JSON
    """
    
    def __init__(self, storage_path: str = "data/trade_journal"):
        """
        Initialize trade journal.
        
        Args:
            storage_path: Path to store trade records
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self.trades: Dict[str, TradeRecord] = {}
        
        # Load existing trades
        self._load_trades()
        
        logger.info("TradeJournal initialized with {} trades", len(self.trades))
    
    def _get_trade_file(self, trade_id: str) -> Path:
        """Get file path for a trade."""
        return self.storage_path / f"{trade_id}.json"
    
    def _save_trade(self, trade: TradeRecord):
        """Save trade to disk."""
        file_path = self._get_trade_file(trade.trade_id)
        with open(file_path, 'w') as f:
            json.dump(trade.to_dict(), f, indent=2)
    
    def _load_trades(self):
        """Load all trades from disk."""
        if not self.storage_path.exists():
            return
        
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    trade = TradeRecord.from_dict(data)
                    self.trades[trade.trade_id] = trade
            except Exception as e:
                logger.error(f"Failed to load trade from {file_path}: {e}")
    
    def log_trade_entry(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        size: float,
        price: float,
        capital: float,
        portfolio_value: float,
        open_positions_count: int,
        volatility: float = 0.0,
        market_regime: str = "normal",
        indicators: Optional[Dict[str, float]] = None,
        ai_confidence: Optional[float] = None,
        ai_reasoning: Optional[str] = None,
        entry_reason: str = ""
    ) -> TradeRecord:
        """
        Log trade entry with pre-trade state.
        
        Args:
            trade_id: Unique trade identifier
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Position size
            price: Entry price
            capital: Available capital
            portfolio_value: Total portfolio value
            open_positions_count: Number of open positions
            volatility: Market volatility
            market_regime: Market regime (normal, high_vol, etc.)
            indicators: Technical indicators at entry
            ai_confidence: AI confidence score
            ai_reasoning: AI reasoning
            entry_reason: Why this trade was taken
            
        Returns:
            TradeRecord
        """
        pre_trade = PreTradeState(
            timestamp=datetime.now(),
            capital=capital,
            portfolio_value=portfolio_value,
            open_positions_count=open_positions_count,
            price=price,
            volatility=volatility,
            market_regime=market_regime,
            indicators=indicators or {},
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            entry_reason=entry_reason
        )
        
        trade = TradeRecord(
            trade_id=trade_id,
            symbol=symbol,
            side=side,
            size=size,
            pre_trade=pre_trade
        )
        
        self.trades[trade_id] = trade
        self._save_trade(trade)
        
        logger.info(
            "Trade entry logged: {} {} {} @ {:.2f} - {}",
            trade_id, side, symbol, price, entry_reason
        )
        
        return trade
    
    def log_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        close_reason: CloseReason,
        capital: float,
        portfolio_value: float,
        what_went_right: Optional[List[str]] = None,
        what_went_wrong: Optional[List[str]] = None,
        lessons_learned: Optional[List[str]] = None
    ) -> Optional[TradeRecord]:
        """
        Log trade exit with post-trade analysis.
        
        Args:
            trade_id: Trade identifier
            exit_price: Exit price
            close_reason: Reason for closing
            capital: Capital after close
            portfolio_value: Portfolio value after close
            what_went_right: What worked well
            what_went_wrong: What didn't work
            lessons_learned: Lessons from this trade
            
        Returns:
            Updated TradeRecord or None if trade not found
        """
        if trade_id not in self.trades:
            logger.error("Trade {} not found", trade_id)
            return None
        
        trade = self.trades[trade_id]
        
        # Calculate P&L
        entry_value = trade.pre_trade.price * trade.size
        exit_value = exit_price * trade.size
        
        if trade.side == 'buy':
            pnl = exit_value - entry_value
        else:  # sell/short
            pnl = entry_value - exit_value
        
        pnl_percentage = (pnl / entry_value * 100) if entry_value > 0 else 0
        
        # Determine outcome
        if pnl > 0:
            outcome = TradeOutcome.WIN
        elif pnl < 0:
            outcome = TradeOutcome.LOSS
        else:
            outcome = TradeOutcome.BREAKEVEN
        
        # Calculate duration
        duration = (datetime.now() - trade.pre_trade.timestamp).total_seconds()
        
        post_trade = PostTradeState(
            timestamp=datetime.now(),
            capital=capital,
            portfolio_value=portfolio_value,
            exit_price=exit_price,
            close_reason=close_reason,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            holding_duration_seconds=duration,
            what_went_right=what_went_right or [],
            what_went_wrong=what_went_wrong or [],
            lessons_learned=lessons_learned or []
        )
        
        trade.post_trade = post_trade
        trade.outcome = outcome
        
        self._save_trade(trade)
        
        logger.info(
            "Trade exit logged: {} - P&L: ${:.2f} ({:.2f}%) - {}",
            trade_id, pnl, pnl_percentage, outcome.value
        )
        
        return trade
    
    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """Get a specific trade."""
        return self.trades.get(trade_id)
    
    def get_all_trades(self, closed_only: bool = False) -> List[TradeRecord]:
        """
        Get all trades.
        
        Args:
            closed_only: Only return closed trades
            
        Returns:
            List of TradeRecords
        """
        trades = list(self.trades.values())
        if closed_only:
            trades = [t for t in trades if t.is_closed]
        return trades
    
    def get_trades_by_symbol(self, symbol: str) -> List[TradeRecord]:
        """Get all trades for a specific symbol."""
        return [t for t in self.trades.values() if t.symbol == symbol]
    
    def generate_weekly_review(
        self,
        week_start: Optional[datetime] = None
    ) -> WeeklyReview:
        """
        Generate weekly review report.
        
        Args:
            week_start: Start of week (defaults to last Monday)
            
        Returns:
            WeeklyReview
        """
        if week_start is None:
            # Default to last Monday
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=7)
        
        # Filter trades for this week
        week_trades = [
            t for t in self.trades.values()
            if t.is_closed and week_start <= t.post_trade.timestamp < week_end
        ]
        
        if not week_trades:
            return WeeklyReview(
                week_start=week_start,
                week_end=week_end,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                total_pnl=0.0,
                win_rate=0.0
            )
        
        # Calculate statistics
        winning_trades = [t for t in week_trades if t.outcome == TradeOutcome.WIN]
        losing_trades = [t for t in week_trades if t.outcome == TradeOutcome.LOSS]
        breakeven_trades = [t for t in week_trades if t.outcome == TradeOutcome.BREAKEVEN]
        
        total_pnl = sum(t.post_trade.pnl for t in week_trades)
        win_rate = len(winning_trades) / len(week_trades) if week_trades else 0
        
        # Get best and worst trades
        sorted_by_pnl = sorted(
            week_trades,
            key=lambda t: t.post_trade.pnl,
            reverse=True
        )
        best_trades = sorted_by_pnl[:5]
        worst_trades = sorted_by_pnl[-5:][::-1]  # Bottom 5, reversed
        
        # Analyze common mistakes
        common_mistakes = self._analyze_common_mistakes(losing_trades)
        improvement_suggestions = self._generate_improvement_suggestions(
            week_trades, winning_trades, losing_trades
        )
        
        review = WeeklyReview(
            week_start=week_start,
            week_end=week_end,
            total_trades=len(week_trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            breakeven_trades=len(breakeven_trades),
            total_pnl=total_pnl,
            win_rate=win_rate,
            best_trades=best_trades,
            worst_trades=worst_trades,
            common_mistakes=common_mistakes,
            improvement_suggestions=improvement_suggestions
        )
        
        logger.info(
            "Weekly review generated: {} trades, {:.1%} win rate, ${:.2f} P&L",
            review.total_trades, review.win_rate, review.total_pnl
        )
        
        return review
    
    def _analyze_common_mistakes(self, losing_trades: List[TradeRecord]) -> List[str]:
        """Analyze losing trades for common mistakes."""
        mistakes = []
        
        if not losing_trades:
            return mistakes
        
        # Check for common close reasons
        stop_loss_count = sum(
            1 for t in losing_trades
            if t.post_trade.close_reason == CloseReason.STOP_LOSS
        )
        if stop_loss_count > len(losing_trades) * 0.5:
            mistakes.append(f"Frequent stop-loss hits ({stop_loss_count}/{len(losing_trades)} trades)")
        
        # Check for short holding times
        short_duration_count = sum(
            1 for t in losing_trades
            if t.duration_hours < 1
        )
        if short_duration_count > len(losing_trades) * 0.3:
            mistakes.append("Too many quick exits - possible premature stop-loss")
        
        # Collect explicit mistakes from post-trade analysis
        all_mistakes = []
        for trade in losing_trades:
            if trade.post_trade:
                all_mistakes.extend(trade.post_trade.what_went_wrong)
        
        # Find most common
        from collections import Counter
        if all_mistakes:
            common = Counter(all_mistakes).most_common(3)
            for mistake, count in common:
                if count > 1:
                    mistakes.append(f"{mistake} ({count} occurrences)")
        
        return mistakes
    
    def _generate_improvement_suggestions(
        self,
        all_trades: List[TradeRecord],
        winning_trades: List[TradeRecord],
        losing_trades: List[TradeRecord]
    ) -> List[str]:
        """Generate improvement suggestions based on trade analysis."""
        suggestions = []
        
        if not all_trades:
            return suggestions
        
        # Analyze win rate
        win_rate = len(winning_trades) / len(all_trades)
        if win_rate < 0.4:
            suggestions.append("Win rate below 40% - review entry criteria and market conditions")
        
        # Analyze average holding time
        avg_duration_hours = sum(t.duration_hours for t in all_trades) / len(all_trades)
        if avg_duration_hours < 2:
            suggestions.append("Average trade duration very short - consider longer timeframes")
        
        # Compare winners vs losers
        if winning_trades and losing_trades:
            avg_win = sum(t.post_trade.pnl for t in winning_trades) / len(winning_trades)
            avg_loss = abs(sum(t.post_trade.pnl for t in losing_trades) / len(losing_trades))
            
            if avg_loss > avg_win * 1.5:
                suggestions.append("Average loss > average win - tighten stop-loss or widen take-profit")
        
        return suggestions
    
    def export_to_markdown(
        self,
        output_path: str,
        week_start: Optional[datetime] = None
    ):
        """
        Export weekly review to markdown file.
        
        Args:
            output_path: Output file path
            week_start: Start of week (defaults to last Monday)
        """
        review = self.generate_weekly_review(week_start)
        markdown = review.to_markdown()
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(markdown)
        
        logger.info("Weekly review exported to {}", output_path)
