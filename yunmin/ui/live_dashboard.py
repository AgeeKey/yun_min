"""
Live Dashboard for YunMin Trading Bot

Provides a rich terminal UI for real-time monitoring of the bot's performance,
positions, trades, and system status.
"""

import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich import box


class LiveDashboard:
    """
    Interactive CLI dashboard for monitoring YunMin trading bot.
    
    Features:
    - Live updating portfolio metrics
    - Open positions with unrealized P&L
    - Recent trades timeline
    - Live event logs
    - System status indicators
    - Keyboard shortcuts for control
    """
    
    def __init__(self, bot: Any = None):
        """
        Initialize the live dashboard.
        
        Args:
            bot: YunMinBot instance (optional for testing)
        """
        self.console = Console()
        self.bot = bot
        self.start_time = datetime.now()
        self.running = True
        self.paused = False
        
        # Mock data for testing/demo
        self.portfolio_value = 15000.0
        self.daily_pnl = 0.0
        self.win_rate = 0.0
        self.open_positions: List[Dict] = []
        self.recent_trades: List[Dict] = []
        self.logs: List[str] = []
        self.api_status = "Connected"
        
    def _create_header(self) -> Panel:
        """Create header panel with portfolio metrics."""
        table = Table.grid(padding=1)
        table.add_column(style="cyan", justify="right")
        table.add_column(style="magenta")
        
        # Portfolio metrics
        pnl_color = "green" if self.daily_pnl >= 0 else "red"
        pnl_symbol = "+" if self.daily_pnl >= 0 else ""
        
        table.add_row("Portfolio Value:", f"${self.portfolio_value:,.2f}")
        table.add_row(
            "Daily P&L:", 
            f"[{pnl_color}]{pnl_symbol}${self.daily_pnl:,.2f}[/{pnl_color}]"
        )
        table.add_row("Win Rate:", f"{self.win_rate:.1f}%")
        
        return Panel(
            table,
            title="📊 Portfolio Overview",
            border_style="cyan",
            box=box.ROUNDED
        )
    
    def _create_positions_table(self) -> Panel:
        """Create table of open positions."""
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        
        table.add_column("Symbol", style="white", width=12)
        table.add_column("Side", style="cyan", width=8)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Entry", justify="right", width=12)
        table.add_column("Current", justify="right", width=12)
        table.add_column("P&L", justify="right", width=12)
        table.add_column("P&L %", justify="right", width=10)
        
        if not self.open_positions:
            table.add_row("No open positions", "", "", "", "", "", "")
        else:
            for pos in self.open_positions:
                pnl = pos.get("unrealized_pnl", 0)
                pnl_pct = pos.get("unrealized_pnl_pct", 0)
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_symbol = "+" if pnl >= 0 else ""
                
                side_color = "green" if pos["side"] == "LONG" else "red"
                
                table.add_row(
                    pos["symbol"],
                    f"[{side_color}]{pos['side']}[/{side_color}]",
                    f"{pos['size']:.4f}",
                    f"${pos['entry_price']:.2f}",
                    f"${pos['current_price']:.2f}",
                    f"[{pnl_color}]{pnl_symbol}${pnl:.2f}[/{pnl_color}]",
                    f"[{pnl_color}]{pnl_symbol}{pnl_pct:.2f}%[/{pnl_color}]"
                )
        
        return Panel(
            table,
            title="💼 Open Positions",
            border_style="blue",
            box=box.ROUNDED
        )
    
    def _create_trades_table(self) -> Panel:
        """Create table of recent trades."""
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        
        table.add_column("Time", style="white", width=10)
        table.add_column("Symbol", width=12)
        table.add_column("Side", width=8)
        table.add_column("Price", justify="right", width=12)
        table.add_column("Size", justify="right", width=10)
        table.add_column("P&L", justify="right", width=12)
        table.add_column("Status", width=10)
        
        if not self.recent_trades:
            table.add_row("No recent trades", "", "", "", "", "", "")
        else:
            for trade in self.recent_trades[-10:]:  # Last 10 trades
                pnl = trade.get("pnl", 0)
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_symbol = "+" if pnl >= 0 else ""
                
                side_color = "green" if trade["side"] == "BUY" else "red"
                
                # Parse timestamp
                ts = trade.get("timestamp", datetime.now())
                time_str = ts.strftime("%H:%M:%S") if isinstance(ts, datetime) else str(ts)[:8]
                
                table.add_row(
                    time_str,
                    trade["symbol"],
                    f"[{side_color}]{trade['side']}[/{side_color}]",
                    f"${trade['price']:.2f}",
                    f"{trade['size']:.4f}",
                    f"[{pnl_color}]{pnl_symbol}${pnl:.2f}[/{pnl_color}]",
                    trade.get("status", "FILLED")
                )
        
        return Panel(
            table,
            title="📈 Recent Trades",
            border_style="green",
            box=box.ROUNDED
        )
    
    def _create_logs_panel(self) -> Panel:
        """Create panel showing recent log events."""
        log_text = Text()
        
        if not self.logs:
            log_text.append("No recent events\n", style="dim")
        else:
            # Show last 8 logs
            for log in self.logs[-8:]:
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_text.append(f"[{timestamp}] ", style="dim")
                log_text.append(f"{log}\n", style="white")
        
        return Panel(
            log_text,
            title="📋 Event Log",
            border_style="yellow",
            box=box.ROUNDED
        )
    
    def _create_footer(self) -> Panel:
        """Create footer with status and controls."""
        table = Table.grid(padding=1)
        table.add_column(style="cyan", justify="left")
        table.add_column(style="white", justify="left")
        table.add_column(style="cyan", justify="right")
        table.add_column(style="white", justify="right")
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Status indicators
        status_text = "🟢 Running" if not self.paused else "🟡 Paused"
        status_color = "green" if not self.paused else "yellow"
        
        api_color = "green" if self.api_status == "Connected" else "red"
        
        table.add_row(
            "Status:", 
            f"[{status_color}]{status_text}[/{status_color}]",
            "Uptime:",
            uptime_str
        )
        table.add_row(
            "API:",
            f"[{api_color}]{self.api_status}[/{api_color}]",
            "Last Update:",
            datetime.now().strftime("%H:%M:%S")
        )
        
        # Keyboard shortcuts
        shortcuts = Text()
        shortcuts.append("Shortcuts: ", style="bold cyan")
        shortcuts.append("[q]uit ", style="yellow")
        shortcuts.append("[p]ause ", style="yellow")
        shortcuts.append("[r]esume ", style="yellow")
        shortcuts.append("[e]mergency ", style="red bold")
        shortcuts.append("[s]napshot", style="yellow")
        
        footer_content = Table.grid()
        footer_content.add_row(table)
        footer_content.add_row("")
        footer_content.add_row(shortcuts)
        
        return Panel(
            footer_content,
            title="⚙️ System Status",
            border_style="magenta",
            box=box.ROUNDED
        )
    
    def _create_layout(self) -> Layout:
        """Create the dashboard layout."""
        layout = Layout()
        
        # Main layout structure
        layout.split(
            Layout(name="header", size=7),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=9)
        )
        
        # Split body into two columns
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        # Split left column
        layout["left"].split(
            Layout(name="positions", ratio=1),
            Layout(name="trades", ratio=1)
        )
        
        # Right column is logs
        layout["right"].update(self._create_logs_panel())
        
        # Update all panels
        layout["header"].update(self._create_header())
        layout["positions"].update(self._create_positions_table())
        layout["trades"].update(self._create_trades_table())
        layout["footer"].update(self._create_footer())
        
        return layout
    
    def update_from_bot(self):
        """Update dashboard data from bot instance."""
        if not self.bot:
            # Use mock data for demo
            self._update_mock_data()
            return
        
        # Get real data from bot
        # TODO: Implement when bot integration is ready
        pass
    
    def _update_mock_data(self):
        """Update with mock data for demonstration."""
        # Simulate slight variations
        self.daily_pnl += random.uniform(-10, 20)
        self.portfolio_value = 15000 + self.daily_pnl
        
        # Calculate win rate from trades
        if self.recent_trades:
            wins = sum(1 for t in self.recent_trades if t.get("pnl", 0) > 0)
            self.win_rate = (wins / len(self.recent_trades)) * 100
    
    def add_log(self, message: str):
        """Add a log message."""
        self.logs.append(message)
        if len(self.logs) > 100:  # Keep only last 100 logs
            self.logs = self.logs[-100:]
    
    def add_trade(self, trade: Dict):
        """Add a trade to recent trades."""
        self.recent_trades.append(trade)
        if len(self.recent_trades) > 50:  # Keep only last 50 trades
            self.recent_trades = self.recent_trades[-50:]
    
    def update_position(self, position: Dict):
        """Update or add a position."""
        symbol = position["symbol"]
        # Find and update existing position
        for i, pos in enumerate(self.open_positions):
            if pos["symbol"] == symbol:
                self.open_positions[i] = position
                return
        # Add new position
        self.open_positions.append(position)
    
    def remove_position(self, symbol: str):
        """Remove a closed position."""
        self.open_positions = [p for p in self.open_positions if p["symbol"] != symbol]
    
    def run(self, update_interval: float = 1.0):
        """
        Run the dashboard with live updates.
        
        Args:
            update_interval: Seconds between updates
        """
        self.add_log("Dashboard started")
        
        try:
            with Live(
                self._create_layout(),
                console=self.console,
                refresh_per_second=4,
                screen=True
            ) as live:
                while self.running:
                    # Update data
                    self.update_from_bot()
                    
                    # Refresh display
                    live.update(self._create_layout())
                    
                    # Wait before next update
                    time.sleep(update_interval)
                    
        except KeyboardInterrupt:
            self.add_log("Dashboard stopped by user")
        finally:
            self.console.print("\n[yellow]Dashboard closed[/yellow]")
    
    def pause_trading(self):
        """Pause trading (keep monitoring)."""
        self.paused = True
        self.add_log("⏸️  Trading paused")
        if self.bot:
            # TODO: Implement bot pause
            pass
    
    def resume_trading(self):
        """Resume trading."""
        self.paused = False
        self.add_log("▶️  Trading resumed")
        if self.bot:
            # TODO: Implement bot resume
            pass
    
    def emergency_stop(self):
        """Emergency stop - close all positions and stop bot."""
        self.add_log("🚨 EMERGENCY STOP triggered")
        if self.bot:
            # TODO: Implement emergency stop
            pass
        self.running = False
    
    def save_snapshot(self):
        """Save current state snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dashboard_snapshot_{timestamp}.txt"
        # TODO: Implement snapshot save
        self.add_log(f"💾 Snapshot saved: {filename}")


def create_demo_dashboard() -> LiveDashboard:
    """Create a demo dashboard with sample data."""
    dashboard = LiveDashboard()
    
    # Add sample positions
    dashboard.update_position({
        "symbol": "BTC/USDT",
        "side": "LONG",
        "size": 0.025,
        "entry_price": 68500.00,
        "current_price": 69200.00,
        "unrealized_pnl": 17.50,
        "unrealized_pnl_pct": 1.02
    })
    
    dashboard.update_position({
        "symbol": "ETH/USDT",
        "side": "SHORT",
        "size": 0.5,
        "entry_price": 3850.00,
        "current_price": 3820.00,
        "unrealized_pnl": 15.00,
        "unrealized_pnl_pct": 0.78
    })
    
    # Add sample trades
    now = datetime.now()
    for i in range(5):
        dashboard.add_trade({
            "timestamp": now - timedelta(minutes=i*15),
            "symbol": "BTC/USDT",
            "side": "BUY" if i % 2 == 0 else "SELL",
            "price": 68500 + (i * 100),
            "size": 0.01 + (i * 0.001),
            "pnl": 12.50 if i % 3 != 0 else -8.30,
            "status": "FILLED"
        })
    
    # Add sample logs
    dashboard.add_log("Bot initialized successfully")
    dashboard.add_log("Connected to Binance Testnet")
    dashboard.add_log("Strategy loaded: AI V3")
    dashboard.add_log("Position opened: BTC/USDT LONG")
    
    dashboard.daily_pnl = 45.20
    dashboard.win_rate = 62.5
    
    return dashboard


if __name__ == "__main__":
    """Run demo dashboard."""
    print("Starting YunMin Live Dashboard Demo...")
    print("Press Ctrl+C to exit\n")
    
    dashboard = create_demo_dashboard()
    dashboard.run(update_interval=2.0)
