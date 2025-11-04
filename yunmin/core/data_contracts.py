"""
Data Contracts & Specifications
================================

All data exchanged between modules follows strict contracts.
This ensures compatibility and prevents bugs.

CANDLE (OHLCV)
--------------
Dict with keys:
  ts_open:     datetime - Candle open timestamp (UTC)
  ts_close:    datetime - Candle close timestamp (UTC)
  o, h, l, c:  float - Open, High, Low, Close prices
  v:           float - Volume
  symbol:      str - Trading pair (e.g., "BTC/USDT")
  timeframe:   str - Candle timeframe (e.g., "5m", "1h")
  source:      str - Data source (e.g., "binance", "backtest")

Example:
  {
    "ts_open": datetime(2025, 1, 1, 12, 0),
    "ts_close": datetime(2025, 1, 1, 12, 5),
    "o": 42000.0,
    "h": 42150.0,
    "l": 41950.0,
    "c": 42100.0,
    "v": 1250.5,
    "symbol": "BTC/USDT",
    "timeframe": "5m",
    "source": "binance"
  }


ORDER
-----
Dict with keys:
  client_oid:      str - Unique order ID (client-side)
  exchange_order_id: Optional[str] - Exchange order ID (None until confirmed)
  symbol:          str - Trading pair
  side:            str - "BUY" or "SELL"
  type:            str - "MARKET", "LIMIT", "STOP"
  qty:             float - Quantity
  price:           Optional[float] - Price (for limit/stop orders)
  tif:             str - Time in force ("GTC", "IOC", "FOK")
  ts_created:      datetime - Creation timestamp
  ts_filled:       Optional[datetime] - Fill timestamp
  status:          str - "PENDING", "OPEN", "CLOSED", "CANCELLED"

Example:
  {
    "client_oid": "ym_ord_123456",
    "exchange_order_id": None,
    "symbol": "BTC/USDT",
    "side": "BUY",
    "type": "LIMIT",
    "qty": 0.5,
    "price": 42000.0,
    "tif": "GTC",
    "ts_created": datetime.now(UTC),
    "ts_filled": None,
    "status": "PENDING"
  }


FILL
----
Dict with keys:
  order_id:    str - Reference to order.client_oid or order.exchange_order_id
  ts:          datetime - Fill timestamp
  price:       float - Fill price
  qty:         float - Filled quantity
  fee:         float - Fee paid (in quote currency)
  fee_asset:   str - Fee asset (usually quote currency)

Example:
  {
    "order_id": "ym_ord_123456",
    "ts": datetime.now(UTC),
    "price": 42000.0,
    "qty": 0.5,
    "fee": 21.0,  # 0.05% fee on 0.5 BTC @ 42000
    "fee_asset": "USDT"
  }


TRADE (CLOSED)
---------------
Dict with keys:
  entry_ts:        datetime - Entry time
  exit_ts:         datetime - Exit time
  side:            str - "LONG" or "SHORT"
  qty:             float - Position quantity
  avg_entry_price: float - Average entry price
  avg_exit_price:  float - Average exit price
  pnl:             float - Profit/loss in quote currency
  pnl_pct:         float - Profit/loss percent (0.05 = 5%)
  commission:      float - Total commissions paid
  duration_sec:    int - Trade duration in seconds

Example:
  {
    "entry_ts": datetime(2025, 1, 1, 12, 0),
    "exit_ts": datetime(2025, 1, 1, 12, 30),
    "side": "LONG",
    "qty": 0.5,
    "avg_entry_price": 42000.0,
    "avg_exit_price": 42150.0,
    "pnl": 75.0,  # 0.5 * (42150 - 42000)
    "pnl_pct": 0.00357,  # 75 / 21000
    "commission": 21.0,
    "duration_sec": 1800
  }


DECISION (STRATEGY OUTPUT)
--------------------------
Dict with keys (from StrategyBase.Decision):
  intent:      str - "BUY", "SELL", "EXIT", or "HOLD"
  confidence:  float - 0.0 to 1.0 confidence level
  size_hint:   Optional[float] - Suggested position size as % of capital
  reason:      str - Explanation of decision

Example:
  {
    "intent": "BUY",
    "confidence": 0.85,
    "size_hint": 0.02,  # 2% of capital
    "reason": "EMA(9) crossed above EMA(21)"
  }


POSITION (LIVE)
---------------
Dict with keys:
  side:             str - "LONG" or "SHORT"
  qty:              float - Current quantity
  entry_price:      float - Entry price
  entry_ts:         datetime - Entry time
  unrealized_pnl:   float - Unrealized profit/loss
  unrealized_pnl_pct: float - Unrealized PnL percent
  mark_price:       float - Current market price
  liquidation_price: Optional[float] - Liquidation price (futures)

Example:
  {
    "side": "LONG",
    "qty": 0.5,
    "entry_price": 42000.0,
    "entry_ts": datetime.now(UTC),
    "unrealized_pnl": 75.0,
    "unrealized_pnl_pct": 0.00357,
    "mark_price": 42150.0,
    "liquidation_price": None
  }


ROUTE STATE
-----------
Route (from RouteManager) contains:
  exchange:      str - Exchange name
  symbol:        str - Trading pair
  timeframe:     str - Candle timeframe
  strategy_name: str - Strategy class name
  state:         RouteState - Enum: IDLE, RUNNING, PAUSED, ERROR
  strategy_instance: Optional[object] - Loaded strategy
  current_time:  Optional[datetime] - Latest candle time
  last_candle_ts: Optional[datetime] - Last processed candle time
  position:      Optional[Dict] - Current position (POSITION contract)
  pending_orders: List[Dict] - Pending orders (ORDER contracts)


BACKTESTER RESULT
------------------
Dict with keys:
  trades:          List[Dict] - Closed trades (TRADE contracts)
  total_profit:    float - Total P&L
  win_rate:        float - Winning trades / total trades
  max_drawdown:    float - Largest peak-to-trough decline
  sharpe_ratio:    Optional[float] - Risk-adjusted return
  sortino_ratio:   Optional[float] - Downside risk-adjusted return
  profit_factor:   Optional[float] - Gross profit / gross loss
  cagr:            Optional[float] - Compound annual growth rate
  total_fees:      float - Total commissions paid

Example:
  {
    "trades": [...],
    "total_profit": 1250.0,
    "win_rate": 0.62,
    "max_drawdown": -0.08,
    "sharpe_ratio": 1.45,
    "sortino_ratio": 2.15,
    "profit_factor": 2.5,
    "cagr": 0.35,
    "total_fees": 125.0
  }
"""

from typing import Dict, Any

# Type aliases for clarity
Candle = Dict[str, Any]
Order = Dict[str, Any]
Fill = Dict[str, Any]
Trade = Dict[str, Any]
Decision = Dict[str, Any]
Position = Dict[str, Any]
BacktestResult = Dict[str, Any]
