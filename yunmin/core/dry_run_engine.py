"""
Dry-run mode with continuous telemetry and SRE alerts.

Runs trading engine in paper trading mode with:
  - Real-time metrics (PnL, DD, latency, reconnects)
  - Alert triggers (CRIT, WARN)
  - Decision logging with features
  - Kill-switch for risk violations
  - Telemetry export (JSON/Prometheus)

Telemetry:
  pnl_total, max_dd_daily, orders_per_min, ws_reconnects, 
  rest_errors, latency_ws_ms, latency_rest_ms, fills_rate, fee_impact_bps

Alerts:
  CRIT: kill-switch, DD > max, 3+ REST errors, WS stale > 60s
  WARN: rejected order, reconnects > N/hr, latency > 2s

Usage:
  from yunmin.core.dry_run_engine import DryRunEngine, DryRunConfig, AlertLevel
  
  config = DryRunConfig(
      symbols=["BTCUSDT", "ETHUSDT"],
      initial_capital=10000,
      max_daily_dd=0.15,
      alert_webhook_url="https://hooks.slack.com/..."
  )
  
  engine = DryRunEngine(config)
  
  # Add alert handler
  engine.on_alert(lambda alert: print(f"{alert.level}: {alert.message}"))
  
  # Start monitoring
  await engine.run(trading_engine, duration_days=7)
  
  # Export metrics
  engine.export_metrics("./metrics.json")
"""

import logging
import json
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARN = "warn"
    CRIT = "crit"


@dataclass
class Alert:
    """Alert message."""
    level: AlertLevel
    timestamp: datetime
    message: str
    details: Dict = field(default_factory=dict)


@dataclass
class Telemetry:
    """Point-in-time telemetry snapshot."""
    timestamp: datetime
    
    # Capital
    pnl_total: float
    pnl_pct: float
    daily_pnl: float
    balance: float
    
    # Risk
    max_dd_daily: float
    current_dd: float
    
    # Trading activity
    orders_per_min: float
    orders_last_hour: int
    fills_rate: float
    avg_fill_latency_ms: float
    
    # Infrastructure
    ws_reconnects: int
    rest_errors: int
    rest_error_rate: float
    latency_ws_ms: float
    latency_rest_ms: float
    ws_last_update_ms: int
    
    # Costs
    fee_impact_bps: float
    total_commission: float
    
    # Position
    exposure_pct: float
    open_orders: int


@dataclass
class DryRunConfig:
    """Dry-run configuration."""
    # Trading
    symbols: List[str]
    initial_capital: float
    
    # Risk
    max_daily_dd: float = 0.15     # 15%
    max_daily_dd_hard: float = 0.20  # Hard kill-switch
    max_position_pct: float = 0.05
    
    # Alerts
    ws_stale_threshold_ms: int = 60000  # 60 seconds
    rest_error_threshold: int = 3       # Kill after 3 errors
    reconnect_rate_threshold: int = 6   # Max reconnects per hour
    latency_warn_ms: int = 2000         # Warn if > 2s
    
    # Telemetry
    telemetry_interval_s: int = 10
    log_decisions: bool = True
    export_dir: str = "./dry_run_data"
    
    # Notifications
    alert_webhook_url: Optional[str] = None  # Slack/Discord webhook
    email_alerts: Optional[str] = None        # Email address


class DryRunEngine:
    """Dry-run mode with telemetry and alerts."""
    
    def __init__(self, config: DryRunConfig):
        """
        Initialize DryRunEngine.
        
        Args:
            config: DryRunConfig
        """
        self.config = config
        
        # State
        self.is_running = False
        self.kill_switch_active = False
        self.alerts: List[Alert] = []
        self.telemetry_history: List[Telemetry] = []
        
        # Metrics
        self.trades_log = []
        self.orders_log = defaultdict(list)  # symbol -> [orders]
        self.rest_errors = defaultdict(int)  # timestamp_bucket -> count
        self.ws_reconnects = 0
        self.last_ws_update = datetime.now()
        self.ws_update_times = []  # For latency tracking
        self.rest_response_times = []  # For latency tracking
        
        # Decision logging
        self.decisions_log = []
        
        # Callbacks
        self.on_alert_callback: Optional[Callable] = None
        self.on_kill_switch_callback: Optional[Callable] = None
        
        logger.info(f"DryRunEngine initialized: {len(config.symbols)} symbols")
    
    def on_alert(self, callback: Callable):
        """Register alert callback."""
        self.on_alert_callback = callback
    
    def on_kill_switch(self, callback: Callable):
        """Register kill-switch callback."""
        self.on_kill_switch_callback = callback
    
    def log_decision(
        self,
        symbol: str,
        decision_id: str,
        decision_type: str,
        confidence: float,
        features: Dict,
        strategy_id: str,
        accepted: bool,
        rejection_reason: Optional[str] = None
    ):
        """
        Log strategy decision.
        
        Args:
            symbol: Trading pair
            decision_id: Unique decision ID
            decision_type: long/short/exit
            confidence: 0-1
            features: Feature snapshot
            strategy_id: Strategy identifier
            accepted: Whether RiskManager accepted
            rejection_reason: If rejected
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": decision_id,
            "symbol": symbol,
            "type": decision_type,
            "confidence": confidence,
            "features": features,
            "strategy_id": strategy_id,
            "accepted": accepted,
            "rejection_reason": rejection_reason
        }
        self.decisions_log.append(entry)
        
        if not accepted:
            self._emit_alert(
                level=AlertLevel.WARN,
                message=f"Decision {decision_id} rejected",
                details={
                    "symbol": symbol,
                    "reason": rejection_reason
                }
            )
    
    def log_trade(
        self,
        symbol: str,
        side: str,
        qty: float,
        entry_price: float,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        commission: float = 0
    ):
        """Log completed trade."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "commission": commission
        }
        self.trades_log.append(entry)
    
    def log_ws_event(self, event_type: str, latency_ms: float, success: bool = True):
        """Log WebSocket event."""
        if event_type == "update":
            self.last_ws_update = datetime.now()
            self.ws_update_times.append(latency_ms)
            if len(self.ws_update_times) > 1000:
                self.ws_update_times.pop(0)  # Keep recent
        
        elif event_type == "reconnect":
            self.ws_reconnects += 1
            
            if self.ws_reconnects > self.config.reconnect_rate_threshold:
                self._emit_alert(
                    level=AlertLevel.WARN,
                    message=f"High WS reconnect rate: {self.ws_reconnects}/hour",
                    details={"reconnects": self.ws_reconnects}
                )
    
    def log_rest_event(self, endpoint: str, latency_ms: float, success: bool):
        """Log REST API event."""
        self.rest_response_times.append(latency_ms)
        if len(self.rest_response_times) > 1000:
            self.rest_response_times.pop(0)
        
        if not success:
            # Bucket by minute
            bucket = datetime.now().replace(second=0, microsecond=0)
            self.rest_errors[str(bucket)] += 1
            
            # Check threshold
            if self.rest_errors[str(bucket)] >= self.config.rest_error_threshold:
                self._emit_alert(
                    level=AlertLevel.CRIT,
                    message=f"REST errors exceed threshold: {self.rest_errors[str(bucket)]}",
                    details={"endpoint": endpoint, "errors_per_minute": self.rest_errors[str(bucket)]}
                )
                self._trigger_kill_switch("excessive_rest_errors")
        
        if latency_ms > self.config.latency_warn_ms:
            self._emit_alert(
                level=AlertLevel.WARN,
                message=f"High REST latency: {latency_ms}ms on {endpoint}",
                details={"endpoint": endpoint, "latency_ms": latency_ms}
            )
    
    def update_metrics(
        self,
        balance: float,
        pnl_total: float,
        daily_pnl: float,
        max_dd_daily: float,
        current_dd: float,
        open_orders: int,
        fill_count: int,
        exposure_pct: float,
        commission_total: float
    ):
        """
        Update metrics snapshot.
        
        Args:
            balance: Current account balance
            pnl_total: Total P&L
            daily_pnl: Today's P&L
            max_dd_daily: Max daily drawdown
            current_dd: Current drawdown
            open_orders: Number of open orders
            fill_count: Number of fills today
            exposure_pct: Position exposure
            commission_total: Total commissions paid
        """
        # Calculate rates
        now = datetime.now()
        start_of_hour = now.replace(minute=0, second=0, microsecond=0)
        orders_this_hour = len([
            o for o in self.trades_log
            if datetime.fromisoformat(o["timestamp"]) >= start_of_hour
        ])
        orders_per_min = orders_this_hour / 60.0
        
        fills_rate = (fill_count / max(len(self.orders_log), 1)) * 100 if self.orders_log else 100
        
        # Latency
        avg_ws_latency = sum(self.ws_update_times) / len(self.ws_update_times) if self.ws_update_times else 0
        avg_rest_latency = sum(self.rest_response_times) / len(self.rest_response_times) if self.rest_response_times else 0
        
        # WS staleness
        time_since_ws_update = (datetime.now() - self.last_ws_update).total_seconds() * 1000
        
        # REST error rate
        errors_last_hour = sum([v for k, v in self.rest_errors.items() if datetime.fromisoformat(k) > start_of_hour])
        rest_error_rate = (errors_last_hour / max(1, len(self.rest_response_times))) * 100
        
        # Fee impact
        fee_impact_bps = (commission_total / max(balance, 1)) * 10000
        
        # Check thresholds
        if time_since_ws_update > self.config.ws_stale_threshold_ms:
            self._emit_alert(
                level=AlertLevel.CRIT,
                message=f"WebSocket stale for {time_since_ws_update:.0f}ms",
                details={"last_update_ms": time_since_ws_update}
            )
        
        if max_dd_daily > self.config.max_daily_dd_hard:
            self._emit_alert(
                level=AlertLevel.CRIT,
                message=f"Drawdown {max_dd_daily*100:.1f}% exceeds hard limit",
                details={"dd": max_dd_daily, "limit": self.config.max_daily_dd_hard}
            )
            self._trigger_kill_switch("max_dd_exceeded")
        
        # Record telemetry
        telemetry = Telemetry(
            timestamp=now,
            pnl_total=pnl_total,
            pnl_pct=(pnl_total / self.config.initial_capital) * 100,
            daily_pnl=daily_pnl,
            balance=balance,
            max_dd_daily=max_dd_daily,
            current_dd=current_dd,
            orders_per_min=orders_per_min,
            orders_last_hour=orders_this_hour,
            fills_rate=fills_rate,
            avg_fill_latency_ms=avg_ws_latency,
            ws_reconnects=self.ws_reconnects,
            rest_errors=sum(self.rest_errors.values()),
            rest_error_rate=rest_error_rate,
            latency_ws_ms=avg_ws_latency,
            latency_rest_ms=avg_rest_latency,
            ws_last_update_ms=int(time_since_ws_update),
            fee_impact_bps=fee_impact_bps,
            total_commission=commission_total,
            exposure_pct=exposure_pct,
            open_orders=open_orders
        )
        
        self.telemetry_history.append(telemetry)
    
    def _emit_alert(
        self,
        level: AlertLevel,
        message: str,
        details: Dict = None
    ):
        """Emit alert."""
        alert = Alert(
            level=level,
            timestamp=datetime.now(),
            message=message,
            details=details or {}
        )
        
        self.alerts.append(alert)
        
        logger.log(
            logging.CRITICAL if level == AlertLevel.CRIT else logging.WARNING if level == AlertLevel.WARN else logging.INFO,
            f"[{level.value.upper()}] {message}"
        )
        
        # Callback
        if self.on_alert_callback:
            try:
                self.on_alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def _trigger_kill_switch(self, reason: str):
        """Trigger kill-switch to stop trading."""
        if self.kill_switch_active:
            return
        
        self.kill_switch_active = True
        
        self._emit_alert(
            level=AlertLevel.CRIT,
            message=f"Kill-switch activated: {reason}",
            details={"reason": reason}
        )
        
        if self.on_kill_switch_callback:
            try:
                self.on_kill_switch_callback(reason)
            except Exception as e:
                logger.error(f"Kill-switch callback error: {e}")
    
    def export_metrics(self, output_path: str):
        """
        Export metrics to JSON.
        
        Args:
            output_path: Path to save JSON
        """
        data = {
            "config": asdict(self.config),
            "summary": {
                "total_alerts": len(self.alerts),
                "critical_alerts": len([a for a in self.alerts if a.level == AlertLevel.CRIT]),
                "warning_alerts": len([a for a in self.alerts if a.level == AlertLevel.WARN]),
                "total_trades": len(self.trades_log),
                "total_decisions": len(self.decisions_log),
                "ws_reconnects": self.ws_reconnects,
                "rest_errors": sum(self.rest_errors.values()),
                "kill_switch_active": self.kill_switch_active
            },
            "alerts": [
                {
                    "level": a.level.value,
                    "timestamp": a.timestamp.isoformat(),
                    "message": a.message,
                    "details": a.details
                }
                for a in self.alerts
            ],
            "recent_telemetry": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "pnl_total": t.pnl_total,
                    "pnl_pct": t.pnl_pct,
                    "max_dd_daily": t.max_dd_daily,
                    "orders_per_min": t.orders_per_min,
                    "fills_rate": t.fills_rate,
                    "ws_reconnects": t.ws_reconnects,
                    "rest_errors": t.rest_errors,
                    "latency_ws_ms": t.latency_ws_ms,
                    "latency_rest_ms": t.latency_rest_ms,
                    "fee_impact_bps": t.fee_impact_bps
                }
                for t in self.telemetry_history[-100:]  # Last 100 snapshots
            ]
        }
        
        import pathlib
        pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {output_path}")
    
    def get_status_summary(self) -> Dict:
        """Get current status summary."""
        latest_telemetry = self.telemetry_history[-1] if self.telemetry_history else None
        
        return {
            "is_running": self.is_running,
            "kill_switch_active": self.kill_switch_active,
            "timestamp": datetime.now().isoformat(),
            "telemetry": asdict(latest_telemetry) if latest_telemetry else {},
            "alerts_count": {
                "total": len(self.alerts),
                "critical": len([a for a in self.alerts if a.level == AlertLevel.CRIT]),
                "warning": len([a for a in self.alerts if a.level == AlertLevel.WARN])
            },
            "trades_count": len(self.trades_log),
            "decisions_count": len(self.decisions_log)
        }
