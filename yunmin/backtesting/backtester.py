"""Backtesting engine for strategy testing"""
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
from yunmin.strategy.base import BaseStrategy, SignalType
from yunmin.risk.manager import RiskManager
from yunmin.risk.policies import OrderRequest
from .metrics import PerformanceMetrics, TradeResult

class Backtester:
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000.0,
                 maker_fee: float = 0.0002, taker_fee: float = 0.0004,
                 slippage_rate: float = 0.0002, use_risk_manager: bool = True,
                 position_size_pct: float = 0.01, leverage: float = 1.0,
                 stop_loss_pct: float = 0.02, take_profit_pct: float = 0.05,
                 cooldown_bars: int = 0, confirmation_bars: int = 0, 
                 min_holding_bars: int = 0):
        """
        Initialize backtester with realistic execution model.
        
        Args:
            strategy: Trading strategy to test
            initial_capital: Starting capital
            maker_fee: Maker fee rate (default 0.02%)
            taker_fee: Taker fee rate (default 0.04%)
            slippage_rate: Slippage rate (default 0.02%)
            use_risk_manager: Enable risk management validation
            position_size_pct: Position size as % of capital (default 1%)
            leverage: Leverage to use (default 1.0x)
            stop_loss_pct: Stop loss percentage (default 2%)
            take_profit_pct: Take profit percentage (default 5%)
            cooldown_bars: Minimum bars between trades (default 0)
            confirmation_bars: Bars to confirm signal before entry (default 0)
            min_holding_bars: Minimum bars to hold position (default 0)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_rate = slippage_rate
        self.position_size_pct = position_size_pct
        self.leverage = leverage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.capital = initial_capital
        self.current_position = None
        self.metrics = PerformanceMetrics()
        self.trade_log: List[Dict[str, Any]] = []
        self.rejected_trades: List[Dict[str, Any]] = []
        
        # Trade frequency controls (Issue #39)
        self.cooldown_bars = cooldown_bars
        self.confirmation_bars = confirmation_bars
        self.min_holding_bars = min_holding_bars
        self.last_exit_bar: Optional[int] = None
        self.signal_confirmation: Optional[Dict[str, Any]] = None
        
        if use_risk_manager:
            from yunmin.core.config import RiskConfig
            self.risk_manager = RiskManager(RiskConfig())
        else:
            self.risk_manager = None
        logger.info(f"Backtester initialized - Capital: ${initial_capital:,.0f}, "
                   f"Position: {position_size_pct*100:.1f}%, Leverage: {leverage}x, "
                   f"Fees: Maker={maker_fee*100:.3f}% Taker={taker_fee*100:.3f}%, "
                   f"Frequency: cooldown={cooldown_bars}, confirm={confirmation_bars}, min_hold={min_holding_bars}")

    def run(self, data: pd.DataFrame, symbol: str = 'BTC/USDT') -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Args:
            data: DataFrame with OHLCV data
            symbol: Trading symbol
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest for {symbol} ({len(data)} candles)")
        self.capital = self.initial_capital
        self.current_position = None
        self.metrics = PerformanceMetrics()
        self.trade_log = []
        self.rejected_trades = []
        self.last_exit_bar = None
        self.signal_confirmation = None
        
        for idx in range(len(data)):
            if idx < 50:
                continue
            historical_df = data.iloc[:idx+1]
            signal = self.strategy.analyze(historical_df)
            
            # Check if we can trade (cooldown period)
            if self.last_exit_bar is not None and self.cooldown_bars > 0:
                bars_since_exit = idx - self.last_exit_bar
                if bars_since_exit < self.cooldown_bars:
                    # Still in cooldown period
                    if self.current_position:
                        self._check_sl_tp(data.iloc[idx]['close'], data.iloc[idx]['timestamp'], idx)
                    continue
            
            if signal is None or signal.type == SignalType.HOLD:
                # Clear signal confirmation if signal changes
                if self.signal_confirmation is not None:
                    self.signal_confirmation = None
                if self.current_position:
                    self._check_sl_tp(data.iloc[idx]['close'], data.iloc[idx]['timestamp'], idx)
                continue
            
            price = data.iloc[idx]['close']
            ts = data.iloc[idx]['timestamp']
            
            # Handle signal confirmation
            if signal.type in [SignalType.BUY, SignalType.SELL] and not self.current_position:
                if self.confirmation_bars > 0:
                    # Check if we're confirming an existing signal
                    if self.signal_confirmation is None:
                        # New signal - start confirmation
                        self.signal_confirmation = {
                            'signal_type': signal.type,
                            'first_bar': idx,
                            'count': 1
                        }
                        continue
                    elif self.signal_confirmation['signal_type'] == signal.type:
                        # Same signal - increment confirmation
                        self.signal_confirmation['count'] += 1
                        if self.signal_confirmation['count'] >= self.confirmation_bars:
                            # Signal confirmed - proceed to open position
                            self.signal_confirmation = None
                        else:
                            # Still confirming
                            continue
                    else:
                        # Signal changed - reset confirmation
                        self.signal_confirmation = {
                            'signal_type': signal.type,
                            'first_bar': idx,
                            'count': 1
                        }
                        continue
                
                # Open position (confirmation passed or not required)
                if signal.type == SignalType.BUY:
                    self._open_long(price, ts, symbol, idx)
                elif signal.type == SignalType.SELL:
                    self._open_short(price, ts, symbol, idx)
                    
            elif signal.type == SignalType.CLOSE and self.current_position:
                # Check minimum holding period
                if self.min_holding_bars > 0:
                    bars_held = idx - self.current_position['entry_bar']
                    if bars_held < self.min_holding_bars:
                        # Haven't held long enough - skip close signal
                        self._check_sl_tp(price, ts, idx)
                        continue
                
                self._close_pos(price, ts, 'Signal', idx)
            
            if self.current_position:
                self._check_sl_tp(price, ts, idx)
        
        if self.current_position:
            self._close_pos(data.iloc[-1]['close'], data.iloc[-1]['timestamp'], 'End', len(data)-1)
        
        results = self.metrics.calculate_metrics(self.initial_capital)
        results['rejected_trades'] = len(self.rejected_trades)
        logger.info(f"Backtest done - {results['total_trades']} trades, {results['win_rate']:.1f}% WR, "
                   f"{len(self.rejected_trades)} rejected")
        return results

    def _open_long(self, price, ts, symbol, bar_index):
        """Open a long position with leverage."""
        position_value = self.capital * self.position_size_pct * self.leverage
        amt = position_value / price
        exe_price = price * (1 + self.slippage_rate)
        fee = position_value * self.taker_fee  # Taker fee for market order
        
        # Risk management validation
        if self.risk_manager:
            order = OrderRequest(symbol=symbol, side='buy', order_type='market',
                               amount=amt, price=exe_price, leverage=self.leverage)
            ok, messages = self.risk_manager.validate_order(
                order, {'capital': self.capital, 'current_price': price}
            )
            if not ok:
                self.rejected_trades.append({
                    'timestamp': ts,
                    'bar_index': bar_index,
                    'side': 'LONG',
                    'price': price,
                    'reason': '; '.join(messages)
                })
                logger.warning(f"Trade rejected at {ts}: {messages}")
                return
        
        # Deduct margin and fees
        margin_required = position_value / self.leverage
        self.capital -= (margin_required + fee)
        
        # Calculate stop loss and take profit
        stop_loss = exe_price * (1 - self.stop_loss_pct)
        take_profit = exe_price * (1 + self.take_profit_pct)
        
        self.current_position = {
            'side': 'LONG',
            'entry_price': exe_price,
            'entry_time': ts,
            'entry_bar': bar_index,
            'amount': amt,
            'entry_fee': fee,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'leverage': self.leverage,
            'margin': margin_required,
            'symbol': symbol
        }
        logger.debug(f"Opened LONG at {exe_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}")

    def _open_short(self, price, ts, symbol, bar_index):
        """Open a short position with leverage."""
        position_value = self.capital * self.position_size_pct * self.leverage
        amt = position_value / price
        exe_price = price * (1 - self.slippage_rate)
        fee = position_value * self.taker_fee  # Taker fee for market order
        
        # Risk management validation
        if self.risk_manager:
            order = OrderRequest(symbol=symbol, side='sell', order_type='market',
                               amount=amt, price=exe_price, leverage=self.leverage)
            ok, messages = self.risk_manager.validate_order(
                order, {'capital': self.capital, 'current_price': price}
            )
            if not ok:
                self.rejected_trades.append({
                    'timestamp': ts,
                    'bar_index': bar_index,
                    'side': 'SHORT',
                    'price': price,
                    'reason': '; '.join(messages)
                })
                logger.warning(f"Trade rejected at {ts}: {messages}")
                return
        
        # Deduct margin and fees
        margin_required = position_value / self.leverage
        self.capital -= (margin_required + fee)
        
        # Calculate stop loss and take profit
        stop_loss = exe_price * (1 + self.stop_loss_pct)
        take_profit = exe_price * (1 - self.take_profit_pct)
        
        self.current_position = {
            'side': 'SHORT',
            'entry_price': exe_price,
            'entry_time': ts,
            'entry_bar': bar_index,
            'amount': amt,
            'entry_fee': fee,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'leverage': self.leverage,
            'margin': margin_required,
            'symbol': symbol
        }
        logger.debug(f"Opened SHORT at {exe_price:.2f}, SL={stop_loss:.2f}, TP={take_profit:.2f}")

    def _close_pos(self, price, ts, reason, bar_index):
        """Close current position."""
        if not self.current_position:
            return
        pos = self.current_position
        
        # Calculate execution price with slippage
        exe_price = price * (1 - self.slippage_rate) if pos['side'] == 'LONG' else price * (1 + self.slippage_rate)
        
        # Calculate P&L
        if pos['side'] == 'LONG':
            pnl = (exe_price - pos['entry_price']) * pos['amount'] * pos['leverage']
        else:
            pnl = (pos['entry_price'] - exe_price) * pos['amount'] * pos['leverage']
        
        pnl_pct = (pnl / (pos['entry_price'] * pos['amount'])) * 100
        
        # Exit fee (using maker fee if TP/SL, taker if signal/end)
        exit_val = exe_price * pos['amount']
        exit_fee = exit_val * (self.maker_fee if reason in ['SL', 'TP'] else self.taker_fee)
        
        # Return margin and net P&L
        self.capital += (pos['margin'] + pnl - exit_fee)
        
        # Record trade
        trade = TradeResult(
            entry_time=pos['entry_time'],
            exit_time=ts,
            entry_price=pos['entry_price'],
            exit_price=exe_price,
            side=pos['side'],
            amount=pos['amount'],
            pnl=pnl - exit_fee,  # Net P&L after fees
            pnl_pct=pnl_pct,
            fees=pos['entry_fee'] + exit_fee
        )
        self.metrics.add_trade(trade)
        
        # Log trade details
        self.trade_log.append({
            'entry_time': pos['entry_time'],
            'exit_time': ts,
            'entry_bar': pos['entry_bar'],
            'exit_bar': bar_index,
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': exe_price,
            'amount': pos['amount'],
            'leverage': pos['leverage'],
            'pnl': pnl - exit_fee,
            'pnl_pct': pnl_pct,
            'fees': pos['entry_fee'] + exit_fee,
            'exit_reason': reason,
            'symbol': pos['symbol'],
            'capital_after': self.capital
        })
        
        # Track last exit bar for cooldown period
        self.last_exit_bar = bar_index
        
        logger.debug(f"Closed {pos['side']} at {exe_price:.2f}, P&L: ${pnl-exit_fee:.2f} ({pnl_pct:.2f}%), Reason: {reason}")
        self.current_position = None

    def _check_sl_tp(self, price, ts, bar_index):
        """Check if stop loss or take profit is hit."""
        if not self.current_position:
            return
        pos = self.current_position
        if pos['side'] == 'LONG':
            if price <= pos['stop_loss']:
                self._close_pos(price, ts, 'SL', bar_index)
            elif price >= pos['take_profit']:
                self._close_pos(price, ts, 'TP', bar_index)
        else:
            if price >= pos['stop_loss']:
                self._close_pos(price, ts, 'SL', bar_index)
            elif price <= pos['take_profit']:
                self._close_pos(price, ts, 'TP', bar_index)

    def get_equity_curve(self):
        """Get equity curve as DataFrame."""
        return pd.DataFrame({'equity': self.metrics.equity_curve})

    def get_trade_log(self) -> pd.DataFrame:
        """Get detailed trade log as DataFrame."""
        if not self.trade_log:
            return pd.DataFrame()
        df = pd.DataFrame(self.trade_log)
        df['duration_hours'] = (df['exit_time'] - df['entry_time']).dt.total_seconds() / 3600
        df['duration_bars'] = df['exit_bar'] - df['entry_bar']
        return df
    
    def save_trade_log(self, filepath: str):
        """
        Save trade log to CSV file.
        
        Args:
            filepath: Path to save CSV file
        """
        df = self.get_trade_log()
        if not df.empty:
            df.to_csv(filepath, index=False)
            logger.info(f"Trade log saved to {filepath} ({len(df)} trades)")
        else:
            logger.warning("No trades to save")
    
    def get_rejected_trades(self) -> pd.DataFrame:
        """Get log of rejected trades."""
        if not self.rejected_trades:
            return pd.DataFrame()
        return pd.DataFrame(self.rejected_trades)
