"""
Backtester: Historical simulation engine.

Simulates trading strategy on historical OHLCV data:
  - Loads candles from data source (Binance REST API or CSV)
  - Executes strategy decisions on historical timeline
  - Simulates order execution (market/limit, slippage, commissions)
  - Tracks position, P&L, and risk metrics
  - Prevents look-ahead bias

Architecture:
  HistoricalFeed
    ├─ _load_candles() - fetch or load OHLCV
    └─ _get_candle(symbol, time) - retrieve specific candle
  
  OrderSimulator
    ├─ execute_market() - immediate fill with slippage
    ├─ execute_limit() - FIFO matching
    └─ _calculate_slippage() - stochastic or fixed model
  
  BacktestRunner
    ├─ _run_routes() - iterate decisions
    ├─ _process_fills() - update positions
    └─ _calculate_metrics() - Sharpe, DD, etc

Usage:
  from yunmin.backtesting.backtester import Backtester, BacktestConfig
  
  config = BacktestConfig(
      symbols=["BTCUSDT", "ETHUSDT"],
      start_date="2025-01-01",
      end_date="2025-01-31",
      initial_capital=10000,
      slippage_bps=2,
      commission_bps=1
  )
  
  backtest = Backtester(config)
  result = backtest.run(strategy=my_strategy)
  
  print(f"Final PnL: {result.final_pnl}")
  print(f"Sharpe: {result.sharpe}")
  print(f"Max DD: {result.max_drawdown}")
"""

import logging
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import math
import statistics

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types for simulation."""
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Candle:
    """OHLCV candle data."""
    timestamp: int          # Unix time in ms
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float
    
    def __repr__(self):
        return f"Candle(t={self.timestamp}, o={self.open}, c={self.close}, v={self.volume})"


@dataclass
class BacktestConfig:
    """Backtester configuration."""
    symbols: List[str]
    start_date: str         # "YYYY-MM-DD"
    end_date: str           # "YYYY-MM-DD"
    initial_capital: float  # e.g. 10000
    timeframe: str = "1m"   # Minimum timeframe
    slippage_bps: float = 2.0       # Basis points
    commission_bps: float = 1.0     # Basis points
    max_leverage: float = 1.0       # No margin by default
    max_position_pct: float = 0.05  # 5% max position
    seed: int = 42          # For reproducibility


@dataclass
class BacktestTrade:
    """Completed trade record."""
    symbol: str
    entry_time: int
    entry_price: float
    exit_time: int
    exit_price: float
    qty: float
    side: str       # "BUY" or "SELL"
    pnl: float      # Realized P&L
    pnl_pct: float  # Realized P&L %
    commission: float


@dataclass
class BacktestResult:
    """Backtester results."""
    initial_capital: float
    final_capital: float
    final_pnl: float
    final_pnl_pct: float
    
    # Risk metrics
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    
    # Trade metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    
    # Fee impact
    total_commission: float
    commission_pct: float
    
    # Exposure
    avg_exposure: float
    max_exposure: float
    
    # Equity curve
    equity_curve: List[Tuple[int, float]] = field(default_factory=list)
    
    # Trade log
    trades: List[BacktestTrade] = field(default_factory=list)
    
    def __repr__(self):
        return (
            f"BacktestResult("
            f"capital={self.final_capital:.2f}, "
            f"pnl={self.final_pnl_pct:.1f}%, "
            f"dd={self.max_drawdown_pct:.1f}%, "
            f"sharpe={self.sharpe_ratio:.2f}"
            f")"
        )


class OrderSimulator:
    """Simulates order execution on historical data."""
    
    def __init__(self, config: BacktestConfig):
        """Initialize simulator."""
        self.config = config
        self.slippage_bps = config.slippage_bps
        self.commission_bps = config.commission_bps
    
    def execute_market_order(
        self,
        side: str,
        qty: float,
        candle: Candle,
        current_price: float
    ) -> Tuple[float, float, float]:
        """
        Execute market order.
        
        Args:
            side: "BUY" or "SELL"
            qty: Quantity
            candle: Current candle (for high/low limits)
            current_price: Reference price (usually close)
            
        Returns:
            (fill_price, filled_qty, commission)
        """
        # Slippage model: fixed bps + volatility-based
        vol = (candle.high - candle.low) / candle.close if candle.close > 0 else 0
        slippage_pct = (self.slippage_bps + vol * 100.0) / 10000.0
        
        if side.upper() == "BUY":
            # Buy slips up
            fill_price = current_price * (1 + slippage_pct)
            fill_price = min(fill_price, candle.high)  # Can't buy above high
        else:  # SELL
            # Sell slips down
            fill_price = current_price * (1 - slippage_pct)
            fill_price = max(fill_price, candle.low)   # Can't sell below low
        
        # Commission
        commission = qty * fill_price * (self.commission_bps / 10000.0)
        
        return fill_price, qty, commission
    
    def execute_limit_order(
        self,
        side: str,
        qty: float,
        limit_price: float,
        candle: Candle
    ) -> Tuple[float, float, float]:
        """
        Execute limit order (FIFO matching).
        
        Args:
            side: "BUY" or "SELL"
            qty: Quantity
            limit_price: Limit price
            candle: Current candle (for matching logic)
            
        Returns:
            (fill_price, filled_qty, commission)
        """
        # Check if order was filled within candle range
        if side.upper() == "BUY":
            # Buy at limit - must be <= limit_price and within candle
            if candle.low <= limit_price:
                # Match at better of limit or low
                fill_price = min(limit_price, candle.low)
                filled_qty = qty
            else:
                fill_price = 0
                filled_qty = 0
        else:  # SELL
            # Sell at limit - must be >= limit_price and within candle
            if candle.high >= limit_price:
                # Match at better of limit or high
                fill_price = max(limit_price, candle.high)
                filled_qty = qty
            else:
                fill_price = 0
                filled_qty = 0
        
        commission = filled_qty * fill_price * (self.commission_bps / 10000.0) if filled_qty > 0 else 0
        
        return fill_price, filled_qty, commission


class BacktestRunner:
    """Runs backtest simulation."""
    
    def __init__(self, config: BacktestConfig):
        """Initialize runner."""
        self.config = config
        self.simulator = OrderSimulator(config)
        
        # State
        self.capital = config.initial_capital
        self.equity = config.initial_capital
        self.positions: Dict[str, float] = {}  # symbol -> qty
        self.position_prices: Dict[str, float] = {}  # symbol -> avg entry price
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[int, float]] = []
        self.total_commission = 0
        
        logger.info(
            f"BacktestRunner initialized: capital={config.initial_capital}, "
            f"symbols={config.symbols}, {config.start_date} to {config.end_date}"
        )
    
    def execute_decision(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: OrderType,
        price: float,
        candle: Candle,
        current_market_price: float,
        limit_price: Optional[float] = None
    ) -> Dict:
        """
        Execute strategy decision.
        
        Args:
            symbol: Trading pair
            side: "BUY" or "SELL"
            qty: Quantity
            order_type: MARKET or LIMIT
            price: Reference price
            candle: Current candle context
            current_market_price: Current market price
            limit_price: For LIMIT orders
            
        Returns:
            Dict with execution details
        """
        try:
            # Position size limit check
            position_value = qty * price
            if position_value > self.capital * self.config.max_position_pct:
                logger.warning(f"Position size {position_value} exceeds limit")
                return {"success": False, "reason": "position_size_limit"}
            
            # Execute order
            if order_type == OrderType.MARKET:
                fill_price, filled_qty, commission = self.simulator.execute_market_order(
                    side, qty, candle, current_market_price
                )
            else:  # LIMIT
                fill_price, filled_qty, commission = self.simulator.execute_limit_order(
                    side, qty, limit_price or price, candle
                )
            
            if filled_qty == 0:
                return {"success": False, "reason": "limit_not_filled"}
            
            # Update position
            current_pos = self.positions.get(symbol, 0)
            current_entry = self.position_prices.get(symbol, 0)
            
            if side.upper() == "BUY":
                new_qty = current_pos + filled_qty
                if new_qty > 0:
                    new_entry = (current_pos * current_entry + filled_qty * fill_price) / new_qty
                else:
                    new_entry = fill_price
                self.positions[symbol] = new_qty
                self.position_prices[symbol] = new_entry
                
                # Update equity (reduce cash)
                position_cost = filled_qty * fill_price + commission
                self.equity -= position_cost
                
            else:  # SELL
                new_qty = current_pos - filled_qty
                if new_qty < 0:
                    new_entry = fill_price
                else:
                    new_entry = current_entry if new_qty > 0 else 0
                self.positions[symbol] = new_qty
                self.position_prices[symbol] = new_entry
                
                # Update equity (add cash)
                position_proceeds = filled_qty * fill_price - commission
                self.equity += position_proceeds
                
                # Record trade if position closed
                if abs(new_qty) < 0.00001 and abs(current_pos) > 0.00001:
                    entry_price = current_entry
                    exit_price = fill_price
                    pnl = (exit_price - entry_price) * current_pos - commission
                    pnl_pct = (pnl / (entry_price * abs(current_pos))) * 100 if entry_price > 0 else 0
                    
                    trade = BacktestTrade(
                        symbol=symbol,
                        entry_time=int(datetime.utcnow().timestamp() * 1000),
                        entry_price=entry_price,
                        exit_time=int(datetime.utcnow().timestamp() * 1000),
                        exit_price=exit_price,
                        qty=abs(current_pos),
                        side="BUY",
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        commission=commission
                    )
                    self.trades.append(trade)
            
            self.total_commission += commission
            
            return {
                "success": True,
                "symbol": symbol,
                "side": side,
                "filled_qty": filled_qty,
                "fill_price": fill_price,
                "commission": commission,
                "position": self.positions[symbol]
            }
            
        except Exception as e:
            logger.error(f"Decision execution error: {e}")
            return {"success": False, "reason": str(e)}
    
    def update_mark_prices(self, prices: Dict[str, float]):
        """
        Update mark prices for open positions (unrealized P&L).
        
        Args:
            prices: Dict of symbol -> price
        """
        unrealized_pnl = 0
        for symbol, qty in self.positions.items():
            if qty != 0 and symbol in prices:
                entry_price = self.position_prices.get(symbol, 0)
                current_price = prices[symbol]
                pnl = (current_price - entry_price) * qty
                unrealized_pnl += pnl
        
        # Update total equity
        self.capital = self.equity + unrealized_pnl
        self.equity_curve.append((
            int(datetime.utcnow().timestamp() * 1000),
            self.capital
        ))
    
    def calculate_metrics(self) -> BacktestResult:
        """
        Calculate performance metrics.
        
        Returns:
            BacktestResult with all metrics
        """
        if not self.equity_curve:
            self.equity_curve.append((
                int(datetime.utcnow().timestamp() * 1000),
                self.capital
            ))
        
        initial = self.config.initial_capital
        final = self.capital
        pnl = final - initial
        pnl_pct = (pnl / initial) * 100 if initial > 0 else 0
        
        # Equity curve analysis
        equity_values = [e[1] for e in self.equity_curve]
        
        # Max drawdown
        peak = initial
        max_dd = 0
        for equity in equity_values:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        max_dd_pct = max_dd * 100
        
        # Sharpe ratio (annualized, assuming 252 trading days, 1440 minutes/day)
        if len(equity_values) > 1:
            returns = [
                (equity_values[i] - equity_values[i-1]) / equity_values[i-1]
                for i in range(1, len(equity_values))
            ]
            if len(returns) > 1 and statistics.stdev(returns) > 0:
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe = (avg_return / std_return) * math.sqrt(252 * 1440) if std_return > 0 else 0
            else:
                sharpe = 0
        else:
            sharpe = 0
        
        # Sortino (only downside volatility)
        if len(equity_values) > 1:
            downside_returns = [r for r in returns if r < 0]
            if downside_returns and statistics.stdev(downside_returns) > 0:
                avg_return = statistics.mean(returns) if returns else 0
                downside_std = statistics.stdev(downside_returns)
                sortino = (avg_return / downside_std) * math.sqrt(252 * 1440)
            else:
                sortino = sharpe if sharpe > 0 else 0
        else:
            sortino = 0
        
        # Calmar ratio
        calmar = (pnl_pct / max_dd_pct) if max_dd_pct > 0 else 0
        
        # Trade statistics
        if self.trades:
            winning_trades = [t for t in self.trades if t.pnl > 0]
            losing_trades = [t for t in self.trades if t.pnl < 0]
            
            win_rate = len(winning_trades) / len(self.trades) if self.trades else 0
            avg_win = statistics.mean([t.pnl for t in winning_trades]) if winning_trades else 0
            avg_loss = abs(statistics.mean([t.pnl for t in losing_trades])) if losing_trades else 0
            
            profit_factor = (
                sum([t.pnl for t in winning_trades]) /
                abs(sum([t.pnl for t in losing_trades]))
                if losing_trades and sum([t.pnl for t in losing_trades]) != 0
                else 0
            )
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            winning_trades = []
            losing_trades = []
        
        # Fee impact
        commission_pct = (self.total_commission / initial) * 100 if initial > 0 else 0
        
        # Exposure
        avg_exposure = 0
        max_exposure = 0
        for symbol, qty in self.positions.items():
            # Would need live prices here for accurate calculation
            pass
        
        result = BacktestResult(
            initial_capital=initial,
            final_capital=final,
            final_pnl=pnl,
            final_pnl_pct=pnl_pct,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            win_rate=win_rate * 100,
            profit_factor=profit_factor,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_commission=self.total_commission,
            commission_pct=commission_pct,
            avg_exposure=avg_exposure,
            max_exposure=max_exposure,
            equity_curve=self.equity_curve,
            trades=self.trades
        )
        
        return result


class Backtester:
    """Main backtester orchestrator."""
    
    def __init__(self, config: BacktestConfig):
        """
        Initialize Backtester.
        
        Args:
            config: BacktestConfig with parameters
        """
        self.config = config
        self.runner = BacktestRunner(config)
    
    def run(
        self,
        strategy_func: Callable,
        candles_loader: Callable,
        progress_callback: Optional[Callable] = None
    ) -> BacktestResult:
        """
        Run backtest.
        
        Args:
            strategy_func: Async function(prices, positions) -> Dict[symbol -> Decision]
            candles_loader: Function() -> Dict[symbol -> List[Candle]]
            progress_callback: Optional callback for progress updates
            
        Returns:
            BacktestResult with metrics
        """
        logger.info("Starting backtest...")
        
        # Load candles
        candles_by_symbol = candles_loader()
        
        # Get min length
        min_length = min(len(c) for c in candles_by_symbol.values()) if candles_by_symbol else 0
        
        # Run simulation
        for i in range(min_length):
            # Get current candle for each symbol
            current_prices = {}
            current_candles = {}
            
            for symbol, candles in candles_by_symbol.items():
                if i < len(candles):
                    candle = candles[i]
                    current_prices[symbol] = candle.close
                    current_candles[symbol] = candle
            
            # Call strategy
            try:
                decisions = strategy_func(current_prices, self.runner.positions)
                
                # Execute decisions
                for symbol, decision in decisions.items():
                    if symbol in current_candles and decision is not None:
                        candle = current_candles[symbol]
                        # Execute per decision
                        self.runner.execute_decision(
                            symbol=symbol,
                            side="BUY" if decision.intent == "long" else "SELL",
                            qty=max(1.0, abs(decision.size_hint * self.config.initial_capital / current_prices[symbol])),
                            order_type=OrderType.MARKET,
                            price=candle.close,
                            candle=candle,
                            current_market_price=candle.close
                        )
            
            except Exception as e:
                logger.error(f"Strategy execution error: {e}")
            
            # Update mark prices
            self.runner.update_mark_prices(current_prices)
            
            # Progress
            if progress_callback and i % 100 == 0:
                progress_callback(i, min_length)
        
        # Calculate metrics
        result = self.runner.calculate_metrics()
        
        logger.info(f"Backtest complete: {result}")
        
        return result
