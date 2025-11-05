"""
Tests for Trade Journal & Post-Trade Analysis
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
from yunmin.analytics.trade_journal import (
    TradeJournal,
    TradeRecord,
    PreTradeState,
    PostTradeState,
    TradeOutcome,
    CloseReason,
    WeeklyReview
)


@pytest.fixture
def temp_journal_path():
    """Create temporary directory for trade journal."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def journal(temp_journal_path):
    """Create a trade journal instance."""
    return TradeJournal(storage_path=temp_journal_path)


class TestPreTradeState:
    """Test PreTradeState dataclass."""
    
    def test_pre_trade_state_creation(self):
        """Test pre-trade state creation."""
        state = PreTradeState(
            timestamp=datetime.now(),
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0,
            price=50000,
            volatility=0.02,
            market_regime="normal",
            entry_reason="EMA crossover"
        )
        
        assert state.capital == 10000
        assert state.price == 50000
        assert state.entry_reason == "EMA crossover"


class TestPostTradeState:
    """Test PostTradeState dataclass."""
    
    def test_post_trade_state_creation(self):
        """Test post-trade state creation."""
        state = PostTradeState(
            timestamp=datetime.now(),
            capital=10100,
            portfolio_value=10100,
            exit_price=51000,
            close_reason=CloseReason.TAKE_PROFIT,
            pnl=100,
            pnl_percentage=1.0,
            holding_duration_seconds=3600
        )
        
        assert state.pnl == 100
        assert state.pnl_percentage == 1.0
        assert state.close_reason == CloseReason.TAKE_PROFIT


class TestTradeRecord:
    """Test TradeRecord dataclass."""
    
    def test_trade_record_creation(self):
        """Test trade record creation."""
        pre_trade = PreTradeState(
            timestamp=datetime.now(),
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0,
            price=50000,
            volatility=0.02,
            market_regime="normal",
            entry_reason="Test"
        )
        
        record = TradeRecord(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            pre_trade=pre_trade
        )
        
        assert record.trade_id == "trade_001"
        assert record.symbol == "BTC/USDT"
        assert not record.is_closed
        assert record.duration_hours == 0.0
    
    def test_trade_record_serialization(self):
        """Test trade record to/from dict."""
        pre_trade = PreTradeState(
            timestamp=datetime.now(),
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0,
            price=50000,
            volatility=0.02,
            market_regime="normal",
            entry_reason="Test"
        )
        
        record = TradeRecord(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            pre_trade=pre_trade,
            outcome=TradeOutcome.WIN
        )
        
        # Convert to dict and back
        data = record.to_dict()
        restored = TradeRecord.from_dict(data)
        
        assert restored.trade_id == record.trade_id
        assert restored.symbol == record.symbol
        assert restored.outcome == record.outcome


class TestTradeJournal:
    """Test TradeJournal functionality."""
    
    def test_initialization(self, journal):
        """Test journal initialization."""
        assert len(journal.trades) == 0
        assert journal.storage_path.exists()
    
    def test_log_trade_entry(self, journal):
        """Test logging trade entry."""
        trade = journal.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0,
            volatility=0.02,
            entry_reason="EMA crossover bullish"
        )
        
        assert trade.trade_id == "trade_001"
        assert trade.symbol == "BTC/USDT"
        assert trade.pre_trade.price == 50000
        assert not trade.is_closed
        
        # Check it's stored
        assert "trade_001" in journal.trades
    
    def test_log_trade_exit(self, journal):
        """Test logging trade exit."""
        # First, log entry
        journal.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        # Then log exit
        trade = journal.log_trade_exit(
            trade_id="trade_001",
            exit_price=51000,
            close_reason=CloseReason.TAKE_PROFIT,
            capital=10100,
            portfolio_value=10100,
            what_went_right=["Good entry timing"],
            lessons_learned=["Wait for confirmation"]
        )
        
        assert trade is not None
        assert trade.is_closed
        assert trade.post_trade.exit_price == 51000
        assert trade.post_trade.pnl == 100  # (51000 - 50000) * 0.1
        assert trade.outcome == TradeOutcome.WIN
    
    def test_log_trade_exit_loss(self, journal):
        """Test logging losing trade."""
        journal.log_trade_entry(
            trade_id="trade_002",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        trade = journal.log_trade_exit(
            trade_id="trade_002",
            exit_price=49000,
            close_reason=CloseReason.STOP_LOSS,
            capital=9900,
            portfolio_value=9900
        )
        
        assert trade.post_trade.pnl == -100
        assert trade.outcome == TradeOutcome.LOSS
    
    def test_log_trade_exit_nonexistent(self, journal):
        """Test logging exit for nonexistent trade."""
        result = journal.log_trade_exit(
            trade_id="nonexistent",
            exit_price=50000,
            close_reason=CloseReason.MANUAL,
            capital=10000,
            portfolio_value=10000
        )
        
        assert result is None
    
    def test_get_trade(self, journal):
        """Test getting a specific trade."""
        journal.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        trade = journal.get_trade("trade_001")
        assert trade is not None
        assert trade.trade_id == "trade_001"
        
        trade = journal.get_trade("nonexistent")
        assert trade is None
    
    def test_get_all_trades(self, journal):
        """Test getting all trades."""
        # Log some trades
        for i in range(3):
            journal.log_trade_entry(
                trade_id=f"trade_{i}",
                symbol="BTC/USDT",
                side="buy",
                size=0.1,
                price=50000,
                capital=10000,
                portfolio_value=10000,
                open_positions_count=0
            )
        
        # Close one trade
        journal.log_trade_exit(
            trade_id="trade_0",
            exit_price=51000,
            close_reason=CloseReason.TAKE_PROFIT,
            capital=10100,
            portfolio_value=10100
        )
        
        all_trades = journal.get_all_trades()
        assert len(all_trades) == 3
        
        closed_trades = journal.get_all_trades(closed_only=True)
        assert len(closed_trades) == 1
    
    def test_get_trades_by_symbol(self, journal):
        """Test filtering trades by symbol."""
        journal.log_trade_entry(
            trade_id="trade_btc",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        journal.log_trade_entry(
            trade_id="trade_eth",
            symbol="ETH/USDT",
            side="buy",
            size=1.0,
            price=3000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        btc_trades = journal.get_trades_by_symbol("BTC/USDT")
        assert len(btc_trades) == 1
        assert btc_trades[0].symbol == "BTC/USDT"
    
    def test_persistence(self, temp_journal_path):
        """Test trade persistence across journal instances."""
        # Create journal and log trade
        journal1 = TradeJournal(storage_path=temp_journal_path)
        journal1.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        # Create new journal instance
        journal2 = TradeJournal(storage_path=temp_journal_path)
        
        # Should load existing trades
        assert len(journal2.trades) == 1
        assert "trade_001" in journal2.trades
    
    def test_generate_weekly_review_empty(self, journal):
        """Test generating weekly review with no trades."""
        review = journal.generate_weekly_review()
        
        assert review.total_trades == 0
        assert review.win_rate == 0.0
        assert review.total_pnl == 0.0
    
    def test_generate_weekly_review_with_trades(self, journal):
        """Test generating weekly review with trades."""
        # Log and close multiple trades
        for i in range(5):
            journal.log_trade_entry(
                trade_id=f"trade_{i}",
                symbol="BTC/USDT",
                side="buy",
                size=0.1,
                price=50000,
                capital=10000,
                portfolio_value=10000,
                open_positions_count=0
            )
            
            # Close with varying outcomes
            exit_price = 51000 if i < 3 else 49000  # 3 winners, 2 losers
            journal.log_trade_exit(
                trade_id=f"trade_{i}",
                exit_price=exit_price,
                close_reason=CloseReason.TAKE_PROFIT if i < 3 else CloseReason.STOP_LOSS,
                capital=10000,
                portfolio_value=10000
            )
        
        review = journal.generate_weekly_review()
        
        assert review.total_trades == 5
        assert review.winning_trades == 3
        assert review.losing_trades == 2
        assert review.win_rate == 0.6  # 60%
        assert review.total_pnl == 100  # 3 * 100 - 2 * 100
        assert len(review.best_trades) <= 5
        assert len(review.worst_trades) <= 5
    
    def test_weekly_review_to_markdown(self, journal):
        """Test markdown export of weekly review."""
        # Create some trades
        journal.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0,
            entry_reason="Test trade"
        )
        
        journal.log_trade_exit(
            trade_id="trade_001",
            exit_price=51000,
            close_reason=CloseReason.TAKE_PROFIT,
            capital=10100,
            portfolio_value=10100
        )
        
        review = journal.generate_weekly_review()
        markdown = review.to_markdown()
        
        assert "Weekly Trading Review" in markdown
        assert "Total Trades" in markdown
        assert "Win Rate" in markdown
        assert "BTC/USDT" in markdown
    
    def test_export_to_markdown(self, journal, temp_journal_path):
        """Test exporting review to markdown file."""
        # Create a trade
        journal.log_trade_entry(
            trade_id="trade_001",
            symbol="BTC/USDT",
            side="buy",
            size=0.1,
            price=50000,
            capital=10000,
            portfolio_value=10000,
            open_positions_count=0
        )
        
        journal.log_trade_exit(
            trade_id="trade_001",
            exit_price=51000,
            close_reason=CloseReason.TAKE_PROFIT,
            capital=10100,
            portfolio_value=10100
        )
        
        output_path = f"{temp_journal_path}/review.md"
        journal.export_to_markdown(output_path)
        
        # Check file was created
        assert Path(output_path).exists()
        
        # Check content
        with open(output_path, 'r') as f:
            content = f.read()
            assert "Weekly Trading Review" in content
    
    def test_common_mistakes_analysis(self, journal):
        """Test common mistakes analysis."""
        # Create multiple losing trades with stop-loss
        for i in range(5):
            journal.log_trade_entry(
                trade_id=f"trade_{i}",
                symbol="BTC/USDT",
                side="buy",
                size=0.1,
                price=50000,
                capital=10000,
                portfolio_value=10000,
                open_positions_count=0
            )
            
            journal.log_trade_exit(
                trade_id=f"trade_{i}",
                exit_price=49000,
                close_reason=CloseReason.STOP_LOSS,
                capital=9900,
                portfolio_value=9900,
                what_went_wrong=["Entered too early"]
            )
        
        review = journal.generate_weekly_review()
        
        # Should detect frequent stop-loss hits
        assert len(review.common_mistakes) > 0
        assert any("stop-loss" in m.lower() for m in review.common_mistakes)
    
    def test_improvement_suggestions(self, journal):
        """Test improvement suggestions generation."""
        # Create trades with low win rate
        for i in range(10):
            journal.log_trade_entry(
                trade_id=f"trade_{i}",
                symbol="BTC/USDT",
                side="buy",
                size=0.1,
                price=50000,
                capital=10000,
                portfolio_value=10000,
                open_positions_count=0
            )
            
            # Only 2 winners, 8 losers (20% win rate)
            exit_price = 51000 if i < 2 else 49000
            journal.log_trade_exit(
                trade_id=f"trade_{i}",
                exit_price=exit_price,
                close_reason=CloseReason.TAKE_PROFIT if i < 2 else CloseReason.STOP_LOSS,
                capital=10000,
                portfolio_value=10000
            )
        
        review = journal.generate_weekly_review()
        
        # Should suggest improvements for low win rate
        assert len(review.improvement_suggestions) > 0
