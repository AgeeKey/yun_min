# API Documentation

## Core Modules

### 1. Trading Engine (`yunmin.core.trading_engine`)

#### `TradingEngine`
Main orchestrator for live/dry-run trading.

**Constructor:**
```python
TradingEngine(
    strategy: BaseStrategy,
    connector: ExchangeConnector,
    risk_manager: RiskManager,
    executor: Executor,
    store: Store,
    config: TradingConfig,
    alert_manager: Optional[AlertManager] = None
)
```

**Methods:**

- `start() -> None`: Start trading loop
- `stop() -> None`: Stop trading gracefully
- `process_signal(signal: Signal) -> None`: Process strategy signal
- `get_status() -> Dict[str, Any]`: Get current engine status

**Example:**
```python
from yunmin.core.trading_engine import TradingEngine
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.connectors.binance_connector import BinanceConnector

engine = TradingEngine(
    strategy=EMACrossoverStrategy(),
    connector=BinanceConnector(),
    risk_manager=RiskManager(),
    executor=Executor(),
    store=SQLiteStore("./data/bot.db"),
    config=TradingConfig(mode="dry_run")
)

engine.start()
```

---

### 2. Risk Manager (`yunmin.risk.manager`)

#### `RiskManager`
Validates trades against risk policies.

**Constructor:**
```python
RiskManager(
    max_position_pct: float = 0.5,
    max_daily_loss: float = 1000,
    max_open_positions: int = 5
)
```

**Methods:**

- `can_open_position(size: float, price: float, balance: float) -> Tuple[bool, str]`: Check if position can be opened
- `check_daily_loss(trades: List[Trade]) -> bool`: Check daily loss limit
- `calculate_position_size(balance: float, risk_pct: float) -> float`: Calculate safe position size

**Example:**
```python
from yunmin.risk.manager import RiskManager

risk_mgr = RiskManager(
    max_position_pct=0.3,  # 30% max position
    max_daily_loss=500      # $500 max daily loss
)

can_trade, reason = risk_mgr.can_open_position(
    size=1000,
    price=45000,
    balance=10000
)

if can_trade:
    print("Trade approved")
else:
    print(f"Trade blocked: {reason}")
```

---

### 3. Alert Manager (`yunmin.core.alert_manager`)

#### `AlertManager`
Multi-channel notification system.

**Constructor:**
```python
AlertManager(config: AlertConfig)
```

**AlertConfig:**
```python
@dataclass
class AlertConfig:
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    
    email_enabled: bool = False
    email_from: str = ""
    email_to: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    
    webhook_enabled: bool = False
    webhook_url: str = ""
    
    log_enabled: bool = True
    rate_limit_seconds: int = 60
```

**Methods:**

- `async send_info(message: str, metadata: Dict = None) -> None`: Send INFO alert
- `async send_warning(message: str, metadata: Dict = None) -> None`: Send WARNING alert
- `async send_error(message: str, metadata: Dict = None) -> None`: Send ERROR alert
- `async send_critical(message: str, metadata: Dict = None) -> None`: Send CRITICAL alert

**Example:**
```python
import asyncio
from yunmin.core.alert_manager import AlertManager, AlertConfig

config = AlertConfig(
    telegram_enabled=True,
    telegram_bot_token="your_token",
    telegram_chat_id="your_chat_id"
)

manager = AlertManager(config)

# Send alerts
asyncio.run(manager.send_info("Bot started"))
asyncio.run(manager.send_error("Connection lost"))
asyncio.run(manager.send_critical("System failure!"))
```

#### `TradingAlerts`
Pre-configured trading alerts.

**Constructor:**
```python
TradingAlerts(alert_manager: AlertManager)
```

**Methods:**

- `async position_opened(symbol: str, side: str, size: float, price: float) -> None`
- `async position_closed(symbol: str, pnl: float, size: float, price: float) -> None`
- `async risk_limit_hit(limit_type: str, current: float, max_allowed: float) -> None`
- `async connection_lost(exchange: str, error: str) -> None`
- `async daily_summary(trades: int, pnl: float, win_rate: float) -> None`

**Example:**
```python
from yunmin.core.alert_manager import TradingAlerts, AlertManager, AlertConfig

manager = AlertManager(AlertConfig(telegram_enabled=True))
alerts = TradingAlerts(manager)

# Trading events
await alerts.position_opened("BTC/USDT", "LONG", 0.1, 45000)
await alerts.position_closed("BTC/USDT", pnl=123.45, size=0.1, price=46000)
await alerts.risk_limit_hit("max_position", current=6000, max_allowed=5000)
await alerts.daily_summary(trades=15, pnl=345.67, win_rate=60.0)
```

---

### 4. Error Recovery (`yunmin.core.error_recovery`)

#### `ErrorRecoveryManager`
Automatic retry with exponential backoff.

**Constructor:**
```python
ErrorRecoveryManager(config: RecoveryConfig)
```

**RecoveryConfig:**
```python
@dataclass
class RecoveryConfig:
    max_retries: int = 3
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
```

**Methods:**

- `async execute_with_retry(func: Callable, *args, **kwargs) -> Any`: Execute function with retry
- `async handle_connection_error(error: Exception) -> bool`: Handle connection errors
- `get_recovery_state() -> RecoveryState`: Get current recovery state

**Example:**
```python
from yunmin.core.error_recovery import ErrorRecoveryManager, RecoveryConfig

config = RecoveryConfig(max_retries=5, initial_backoff_seconds=2)
recovery = ErrorRecoveryManager(config)

async def fetch_balance():
    # May fail due to network issues
    return await exchange.get_balance()

# Automatic retry on failure
balance = await recovery.execute_with_retry(fetch_balance)
```

---

### 5. Backtester (`yunmin.backtesting.backtester`)

#### `Backtester`
Historical strategy testing.

**Constructor:**
```python
Backtester(
    strategy: BaseStrategy,
    initial_capital: float = 10000,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_position_pct: float = 1.0
)
```

**Methods:**

- `run(data: pd.DataFrame, symbol: str = "BTC/USDT") -> Dict[str, Any]`: Run backtest
- `get_equity_curve() -> pd.Series`: Get equity curve
- `get_trades() -> List[Dict]`: Get all trades

**Returns (from `run`):**
```python
{
    'total_trades': int,
    'winning_trades': int,
    'losing_trades': int,
    'win_rate': float,  # percentage
    'total_return': float,  # percentage
    'net_pnl': float,
    'sharpe_ratio': float,
    'max_drawdown': float,
    'max_drawdown_pct': float,
    'total_fees': float,
    'avg_win': float,
    'avg_loss': float,
    'best_trade': float,
    'worst_trade': float
}
```

**Example:**
```python
from yunmin.backtesting.backtester import Backtester
from yunmin.backtesting.data_loader import HistoricalDataLoader
from yunmin.strategy.ema_crossover import EMACrossoverStrategy

# Load data
loader = HistoricalDataLoader()
data = loader.load_csv("historical_data.csv")

# Run backtest
backtester = Backtester(
    strategy=EMACrossoverStrategy(),
    initial_capital=10000,
    commission_pct=0.001
)

metrics = backtester.run(data, symbol="BTC/USDT")
print(f"Total return: {metrics['total_return']:.2f}%")
print(f"Win rate: {metrics['win_rate']:.1f}%")
print(f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
```

---

### 6. Strategy Base (`yunmin.strategy.base`)

#### `BaseStrategy`
Abstract base class for strategies.

**Methods to Implement:**

- `generate_signal(data: pd.DataFrame) -> Signal`: Generate trading signal

**Signal Enum:**
```python
class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"
```

**Example Custom Strategy:**
```python
from yunmin.strategy.base import BaseStrategy, Signal
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self, threshold: float = 0.02):
        super().__init__()
        self.threshold = threshold
    
    def generate_signal(self, data: pd.DataFrame) -> Signal:
        if len(data) < 2:
            return Signal.HOLD
        
        price_change = (data['close'].iloc[-1] - data['close'].iloc[-2]) / data['close'].iloc[-2]
        
        if price_change > self.threshold:
            return Signal.LONG
        elif price_change < -self.threshold:
            return Signal.SHORT
        else:
            return Signal.HOLD
```

---

### 7. Exchange Connector (`yunmin.connectors.binance_connector`)

#### `BinanceConnector`
Binance exchange integration.

**Constructor:**
```python
BinanceConnector(
    api_key: str = None,
    api_secret: str = None,
    testnet: bool = True
)
```

**Methods:**

- `get_balance() -> Dict[str, float]`: Get account balance
- `get_ticker(symbol: str) -> Dict`: Get current price
- `place_market_order(symbol: str, side: str, quantity: float) -> Dict`: Place market order
- `place_limit_order(symbol: str, side: str, quantity: float, price: float) -> Dict`: Place limit order
- `cancel_order(symbol: str, order_id: str) -> Dict`: Cancel order
- `get_open_orders(symbol: str) -> List[Dict]`: Get open orders
- `get_order_status(symbol: str, order_id: str) -> Dict`: Get order status

**Example:**
```python
from yunmin.connectors.binance_connector import BinanceConnector

connector = BinanceConnector(testnet=True)

# Get balance
balance = connector.get_balance()
print(f"USDT: {balance['USDT']:.2f}")

# Place order
order = connector.place_market_order(
    symbol="BTC/USDT",
    side="BUY",
    quantity=0.001
)
print(f"Order ID: {order['id']}")

# Check status
status = connector.get_order_status("BTC/USDT", order['id'])
print(f"Status: {status['status']}")
```

---

### 8. Persistence (`yunmin.store.sqlite_store`)

#### `SQLiteStore`
Database persistence layer.

**Constructor:**
```python
SQLiteStore(db_path: str = "./data/yunmin.db")
```

**Methods:**

- `save_trade(trade: Trade) -> None`: Save trade to database
- `get_all_trades() -> List[Trade]`: Get all trades
- `save_position(position: Position) -> None`: Save position
- `get_open_positions() -> List[Position]`: Get open positions
- `save_checkpoint(state: Dict) -> None`: Save bot state
- `load_checkpoint() -> Optional[Dict]`: Load latest checkpoint

**Example:**
```python
from yunmin.store.sqlite_store import SQLiteStore
from yunmin.core.data_contracts import Trade

store = SQLiteStore("./data/production.db")

# Save trade
trade = Trade(
    symbol="BTC/USDT",
    side="BUY",
    size=0.1,
    entry_price=45000,
    exit_price=46000,
    pnl=100,
    timestamp="2024-12-20T10:00:00"
)

store.save_trade(trade)

# Query trades
all_trades = store.get_all_trades()
print(f"Total trades: {len(all_trades)}")
```

---

## Configuration Reference

### Trading Config (`config/production.yaml`)

```yaml
trading:
  mode: "live"  # "dry_run" | "live"
  symbol: "BTC/USDT"
  timeframe: "5m"
  initial_capital: 10000
  
risk:
  max_position_pct: 0.50
  max_daily_loss: 500
  max_open_positions: 3
  stop_loss_pct: 0.02
  take_profit_pct: 0.05
  
strategy:
  name: "EMACrossoverStrategy"
  params:
    fast_period: 9
    slow_period: 21
    
alerts:
  enabled: true
  channels: ["telegram", "email", "log"]
  rate_limit_seconds: 60
  
recovery:
  max_retries: 3
  initial_backoff_seconds: 1
  max_backoff_seconds: 60
```

---

## CLI Commands

```bash
# Start bot
yunmin run --config config/production.yaml --live

# Dry-run mode
yunmin run --config config/production.yaml --dry-run

# Run backtest
yunmin backtest --data historical.csv --strategy EMA --output results.json

# Check status
yunmin status

# Generate report
yunmin report --period daily

# Close all positions
yunmin close-all --confirm
```

---

## Event System

### Events Published:

- `SIGNAL_GENERATED`: Strategy generated signal
- `POSITION_OPENED`: New position opened
- `POSITION_CLOSED`: Position closed
- `ORDER_PLACED`: Order sent to exchange
- `ORDER_FILLED`: Order executed
- `RISK_LIMIT_HIT`: Risk limit triggered
- `ERROR_OCCURRED`: Error encountered

### Subscribe to Events:

```python
from yunmin.core.trading_engine import TradingEngine

engine = TradingEngine(...)

@engine.on("POSITION_OPENED")
def handle_position(event):
    print(f"Position opened: {event.symbol} {event.side}")

@engine.on("ERROR_OCCURRED")
def handle_error(event):
    print(f"Error: {event.error}")
```

---

## Error Codes

| Code | Description | Action |
|------|-------------|--------|
| `E001` | Exchange connection failed | Check network, API keys |
| `E002` | Insufficient balance | Add funds or reduce position size |
| `E003` | Risk limit exceeded | Wait for cooldown period |
| `E004` | Invalid order parameters | Check order size/price |
| `E005` | Database error | Check disk space, permissions |
| `E006` | Strategy error | Review strategy logic |

---

**Last Updated**: 2024-12-20  
**API Version**: 1.0  
**Python Version**: 3.11+
