"""
Risk management and pre-order validation.

Adapted from Hummingbot patterns:
  - hummingbot/connector/position_mode_calculator.py
  - hummingbot/client/config/risk_profile.py

Provides:
  - Position size validation
  - Daily drawdown tracking
  - Leverage limits
  - Trade frequency limits
  - Risk rules interface for custom validation
"""

import logging
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "conservative"    # 2% risk per trade, 10% max DD
    MODERATE = "moderate"           # 5% risk per trade, 15% max DD
    AGGRESSIVE = "aggressive"       # 10% risk per trade, 20% max DD
    CUSTOM = "custom"               # User-defined


@dataclass
class RiskRule:
    """Single risk rule for validation."""
    name: str
    description: str
    
    def validate(self, context: "RiskContext") -> tuple[bool, str]:
        """
        Validate rule.
        
        Returns:
            (is_valid, reason) tuple
        """
        raise NotImplementedError


@dataclass
class RiskContext:
    """Context for risk validation."""
    symbol: str
    side: str  # BUY or SELL
    quantity: float
    price: float
    account_balance: float
    current_position_qty: float = 0
    current_position_value: float = 0
    open_orders_count: int = 0
    daily_trades_count: int = 0
    daily_profit: float = 0
    daily_loss: float = 0
    daily_max_drawdown: float = 0
    metadata: Dict = field(default_factory=dict)
    
    @property
    def order_value(self) -> float:
        """Calculate total order value."""
        return self.quantity * self.price


@dataclass
class TradeRecord:
    """Record of a closed trade."""
    entry_ts: datetime
    exit_ts: datetime
    symbol: str
    side: str
    entry_qty: float
    entry_price: float
    exit_qty: float
    exit_price: float
    pnl: float
    pnl_pct: float
    commission: float


class RiskManager:
    """
    Manages pre-order risk validation and position tracking.
    
    Controls:
      - Maximum position size per symbol
      - Daily drawdown limits
      - Leverage/margin limits
      - Trade frequency limits
      - Custom risk rules
    
    Usage:
        risk_mgr = RiskManager(
            account_balance=10000,
            max_position_pct=0.05,  # 5% max position
            max_daily_dd=0.15,      # 15% max daily DD
            risk_level=RiskLevel.MODERATE
        )
        
        # Before placing order
        is_valid, reason = risk_mgr.validate_order(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=42000,
            current_position_qty=0
        )
        
        if is_valid:
            # Place order
            connector.place_order(...)
            # Record after fill
            risk_mgr.add_fill(symbol, qty, price, commission)
        else:
            logger.warning(f"Order rejected: {reason}")
    """
    
    def __init__(
        self,
        account_balance: float,
        max_position_pct: float = 0.05,  # 5% max position
        max_daily_dd: float = 0.15,       # 15% max daily drawdown
        max_daily_trades: int = 100,      # Max trades per day
        max_open_orders: int = 10,        # Max concurrent orders
        risk_level: RiskLevel = RiskLevel.MODERATE,
        leverage: float = 1.0             # Margin leverage (1.0 = no margin)
    ):
        """
        Initialize RiskManager.
        
        Args:
            account_balance: Starting account balance
            max_position_pct: Max position size as % of balance (0.05 = 5%)
            max_daily_dd: Max daily drawdown as % (0.15 = 15%)
            max_daily_trades: Max trades per day
            max_open_orders: Max concurrent open orders
            risk_level: Risk tolerance level
            leverage: Margin leverage multiplier
        """
        self.account_balance = account_balance
        self.initial_balance = account_balance
        self.max_position_pct = max_position_pct
        self.max_daily_dd = max_daily_dd
        self.max_daily_trades = max_daily_trades
        self.max_open_orders = max_open_orders
        self.risk_level = risk_level
        self.leverage = leverage
        
        # Track current day
        self.day_start = datetime.now(UTC).date()
        self.daily_trades: List[TradeRecord] = []
        self.daily_profit = 0
        self.daily_loss = 0
        self.peak_balance = account_balance
        
        # Custom risk rules
        self.custom_rules: List[RiskRule] = []
        
        # Position tracking
        self.open_positions: Dict[str, float] = {}  # symbol -> quantity
        self.position_prices: Dict[str, float] = {}  # symbol -> avg price
        
        logger.info(
            f"RiskManager initialized: balance={account_balance}, "
            f"max_position={max_position_pct*100}%, "
            f"max_dd={max_daily_dd*100}%, "
            f"risk_level={risk_level.value}"
        )
    
    def add_custom_rule(self, rule: RiskRule):
        """Add custom risk rule."""
        self.custom_rules.append(rule)
        logger.debug(f"Added custom risk rule: {rule.name}")
    
    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        current_position_qty: float = 0
    ) -> tuple[bool, str]:
        """
        Validate order before execution.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Order price
            current_position_qty: Current position quantity
            
        Returns:
            (is_valid, reason_if_invalid) tuple
        """
        # Check if new day started
        self._check_day_reset()
        
        # Build context
        context = RiskContext(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            account_balance=self.account_balance,
            current_position_qty=current_position_qty,
            daily_trades_count=len(self.daily_trades),
            daily_profit=self.daily_profit,
            daily_loss=self.daily_loss,
            open_orders_count=len(self.open_positions)
        )
        
        # Run built-in checks
        checks = [
            self._check_position_size(context),
            self._check_daily_trades(context),
            self._check_open_orders(context),
            self._check_margin_available(context),
            self._check_daily_drawdown(context),
        ]
        
        # Run custom rules
        for rule in self.custom_rules:
            is_valid, reason = rule.validate(context)
            if not is_valid:
                return False, f"Custom rule '{rule.name}': {reason}"
        
        # Check all built-in validations
        for is_valid, reason in checks:
            if not is_valid:
                logger.warning(f"Order validation failed: {reason}")
                return False, reason
        
        logger.debug(f"Order validation passed: {symbol} {side} {quantity}@{price}")
        return True, ""
    
    def _check_position_size(self, context: RiskContext) -> tuple[bool, str]:
        """Check if position size is within limits."""
        max_position_value = self.account_balance * self.max_position_pct
        order_value = context.order_value
        
        if order_value > max_position_value:
            return False, (
                f"Position size {order_value:.2f} exceeds limit {max_position_value:.2f} "
                f"({self.max_position_pct*100}% of balance)"
            )
        
        return True, ""
    
    def _check_daily_trades(self, context: RiskContext) -> tuple[bool, str]:
        """Check if daily trade limit is exceeded."""
        if context.daily_trades_count >= self.max_daily_trades:
            return False, f"Daily trade limit ({self.max_daily_trades}) reached"
        
        return True, ""
    
    def _check_open_orders(self, context: RiskContext) -> tuple[bool, str]:
        """Check if max concurrent orders exceeded."""
        if context.open_orders_count >= self.max_open_orders:
            return False, f"Max open orders ({self.max_open_orders}) reached"
        
        return True, ""
    
    def _check_margin_available(self, context: RiskContext) -> tuple[bool, str]:
        """Check if sufficient margin is available (if using leverage)."""
        if self.leverage <= 1.0:
            return True, ""
        
        required_margin = context.order_value / self.leverage
        available_balance = self.account_balance
        
        if required_margin > available_balance:
            return False, (
                f"Insufficient margin: need {required_margin:.2f}, "
                f"have {available_balance:.2f}"
            )
        
        return True, ""
    
    def _check_daily_drawdown(self, context: RiskContext) -> tuple[bool, str]:
        """Check if daily drawdown limit is exceeded."""
        current_dd = self._calculate_current_drawdown()
        
        if current_dd > self.max_daily_dd:
            return False, (
                f"Daily drawdown {current_dd*100:.2f}% exceeds limit {self.max_daily_dd*100:.2f}%"
            )
        
        return True, ""
    
    def add_fill(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        commission: float = 0
    ):
        """
        Record order fill.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Filled quantity
            price: Fill price
            commission: Commission paid
        """
        # Update position
        if side == "BUY":
            if symbol not in self.open_positions:
                self.open_positions[symbol] = 0
                self.position_prices[symbol] = 0
            
            # Average price calculation
            old_qty = self.open_positions[symbol]
            old_price = self.position_prices[symbol]
            new_qty = old_qty + quantity
            self.position_prices[symbol] = (old_price * old_qty + price * quantity) / new_qty if new_qty > 0 else 0
            self.open_positions[symbol] = new_qty
            
        elif side == "SELL":
            if symbol in self.open_positions:
                self.open_positions[symbol] -= quantity
                if self.open_positions[symbol] <= 0:
                    del self.open_positions[symbol]
                    del self.position_prices[symbol]
        
        logger.debug(f"Recorded fill: {symbol} {side} {quantity}@{price}")
    
    def record_trade_result(self, trade: TradeRecord):
        """
        Record closed trade for daily stats.
        
        Args:
            trade: Closed TradeRecord
        """
        self.daily_trades.append(trade)
        
        if trade.pnl > 0:
            self.daily_profit += trade.pnl
        else:
            self.daily_loss += abs(trade.pnl)
        
        # Update account balance
        self.account_balance += trade.pnl
        self.peak_balance = max(self.peak_balance, self.account_balance)
        
        logger.info(
            f"Trade recorded: {trade.symbol} {trade.side} "
            f"entry={trade.entry_price:.2f}, exit={trade.exit_price:.2f}, "
            f"pnl={trade.pnl:.2f} ({trade.pnl_pct*100:.2f}%)"
        )
    
    def get_daily_stats(self) -> Dict:
        """Get daily trading statistics."""
        return {
            "date": self.day_start,
            "trades_count": len(self.daily_trades),
            "daily_profit": self.daily_profit,
            "daily_loss": self.daily_loss,
            "net_pnl": self.daily_profit - self.daily_loss,
            "current_drawdown": self._calculate_current_drawdown(),
            "account_balance": self.account_balance,
            "win_rate": self._calculate_win_rate(),
        }
    
    def _calculate_current_drawdown(self) -> float:
        """Calculate current drawdown from peak."""
        if self.peak_balance == 0:
            return 0
        return max(0, (self.peak_balance - self.account_balance) / self.peak_balance)
    
    def _calculate_win_rate(self) -> float:
        """Calculate daily win rate."""
        if not self.daily_trades:
            return 0
        wins = sum(1 for t in self.daily_trades if t.pnl > 0)
        return wins / len(self.daily_trades)
    
    def _check_day_reset(self):
        """Reset daily stats if new day started."""
        today = datetime.now(UTC).date()
        if today > self.day_start:
            logger.info(
                f"New day started. Daily stats: "
                f"trades={len(self.daily_trades)}, "
                f"profit={self.daily_profit:.2f}, "
                f"loss={self.daily_loss:.2f}"
            )
            self.day_start = today
            self.daily_trades = []
            self.daily_profit = 0
            self.daily_loss = 0
            self.peak_balance = self.account_balance
    
    def get_position(self, symbol: str) -> float:
        """Get current position quantity for symbol."""
        return self.open_positions.get(symbol, 0)
    
    def get_position_value(self, symbol: str, current_price: float) -> float:
        """Get current position value at given price."""
        qty = self.get_position(symbol)
        return qty * current_price
    
    def calculate_max_position_size(self, symbol: str, price: float) -> float:
        """
        Calculate maximum position size for symbol.
        
        Args:
            symbol: Trading pair
            price: Current price
            
        Returns:
            Maximum quantity that can be purchased
        """
        max_value = self.account_balance * self.max_position_pct
        max_qty = max_value / price
        return max_qty
    
    def suggest_position_size(
        self,
        symbol: str,
        price: float,
        risk_pct: float = None
    ) -> float:
        """
        Suggest position size based on risk percentage.
        
        Args:
            symbol: Trading pair
            price: Entry price
            risk_pct: Risk as % of balance (None = use risk_level)
            
        Returns:
            Suggested quantity
        """
        if risk_pct is None:
            # Use default from risk level
            if self.risk_level == RiskLevel.CONSERVATIVE:
                risk_pct = 0.02
            elif self.risk_level == RiskLevel.MODERATE:
                risk_pct = 0.05
            elif self.risk_level == RiskLevel.AGGRESSIVE:
                risk_pct = 0.10
            else:
                risk_pct = self.max_position_pct
        
        risk_amount = self.account_balance * risk_pct
        suggested_qty = risk_amount / price
        
        # Don't exceed max position
        max_qty = self.calculate_max_position_size(symbol, price)
        return min(suggested_qty, max_qty)
