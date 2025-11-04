"""Backtesting engine for strategy testing"""
import pandas as pd
from typing import Dict, Any
from loguru import logger
from yunmin.strategy.base import BaseStrategy, SignalType
from yunmin.risk.manager import RiskManager
from yunmin.risk.policies import OrderRequest
from .metrics import PerformanceMetrics, TradeResult

class Backtester:
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000.0,
                 commission_rate: float = 0.001, slippage_rate: float = 0.0005,
                 use_risk_manager: bool = True):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.capital = initial_capital
        self.current_position = None
        self.metrics = PerformanceMetrics()
        if use_risk_manager:
            from yunmin.core.config import RiskConfig
            self.risk_manager = RiskManager(RiskConfig())
        else:
            self.risk_manager = None
        logger.info(f"Backtester initialized - Capital: ${initial_capital:,.0f}")

    def run(self, data: pd.DataFrame, symbol: str = 'BTC/USDT',
            position_size_pct: float = 0.1) -> Dict[str, Any]:
        logger.info(f"Starting backtest for {symbol} ({len(data)} candles)")
        self.capital = self.initial_capital
        self.current_position = None
        self.metrics = PerformanceMetrics()
        
        for idx in range(len(data)):
            if idx < 50:
                continue
            historical_df = data.iloc[:idx+1]
            signal = self.strategy.analyze(historical_df)
            
            if signal is None or signal.type == SignalType.HOLD:
                if self.current_position:
                    self._check_sl_tp(data.iloc[idx]['close'], data.iloc[idx]['timestamp'])
                continue
            
            price = data.iloc[idx]['close']
            ts = data.iloc[idx]['timestamp']
            
            if signal.type == SignalType.BUY and not self.current_position:
                self._open_long(price, ts, symbol, position_size_pct)
            elif signal.type == SignalType.SELL and not self.current_position:
                self._open_short(price, ts, symbol, position_size_pct)
            elif signal.type == SignalType.CLOSE and self.current_position:
                self._close_pos(price, ts, 'Signal')
            
            if self.current_position:
                self._check_sl_tp(price, ts)
        
        if self.current_position:
            self._close_pos(data.iloc[-1]['close'], data.iloc[-1]['timestamp'], 'End')
        
        results = self.metrics.calculate_metrics(self.initial_capital)
        logger.info(f"Backtest done - {results['total_trades']} trades, {results['win_rate']:.1f}% WR")
        return results

    def _open_long(self, price, ts, symbol, pct):
        val = self.capital * pct
        amt = val / price
        exe_price = price * (1 + self.slippage_rate)
        fee = val * self.commission_rate
        if self.risk_manager:
            order = OrderRequest(symbol=symbol, side='buy', order_type='market',
                               amount=amt, price=exe_price, leverage=1.0)
            ok, _ = self.risk_manager.validate_order(order, {'capital': self.capital, 'current_price': price})
            if not ok:
                return
        self.capital -= (val + fee)
        self.current_position = {'side': 'LONG', 'entry_price': exe_price, 'entry_time': ts,
                                'amount': amt, 'entry_fee': fee, 'stop_loss': exe_price * 0.95,
                                'take_profit': exe_price * 1.10}

    def _open_short(self, price, ts, symbol, pct):
        val = self.capital * pct
        amt = val / price
        exe_price = price * (1 - self.slippage_rate)
        fee = val * self.commission_rate
        if self.risk_manager:
            order = OrderRequest(symbol=symbol, side='sell', order_type='market',
                               amount=amt, price=exe_price, leverage=1.0)
            ok, _ = self.risk_manager.validate_order(order, {'capital': self.capital, 'current_price': price})
            if not ok:
                return
        self.capital -= (val + fee)
        self.current_position = {'side': 'SHORT', 'entry_price': exe_price, 'entry_time': ts,
                                'amount': amt, 'entry_fee': fee, 'stop_loss': exe_price * 1.05,
                                'take_profit': exe_price * 0.90}

    def _close_pos(self, price, ts, reason):
        if not self.current_position:
            return
        pos = self.current_position
        exe_price = price * (1 - self.slippage_rate) if pos['side'] == 'LONG' else price * (1 + self.slippage_rate)
        pnl = (exe_price - pos['entry_price']) * pos['amount'] if pos['side'] == 'LONG' else (pos['entry_price'] - exe_price) * pos['amount']
        pnl_pct = (pnl / (pos['entry_price'] * pos['amount'])) * 100
        exit_val = exe_price * pos['amount']
        exit_fee = exit_val * self.commission_rate
        self.capital += (exit_val + pnl - exit_fee)
        trade = TradeResult(entry_time=pos['entry_time'], exit_time=ts, entry_price=pos['entry_price'],
                          exit_price=exe_price, side=pos['side'], amount=pos['amount'],
                          pnl=pnl, pnl_pct=pnl_pct, fees=pos['entry_fee'] + exit_fee)
        self.metrics.add_trade(trade)
        self.current_position = None

    def _check_sl_tp(self, price, ts):
        if not self.current_position:
            return
        pos = self.current_position
        if pos['side'] == 'LONG':
            if price <= pos['stop_loss']:
                self._close_pos(price, ts, 'SL')
            elif price >= pos['take_profit']:
                self._close_pos(price, ts, 'TP')
        else:
            if price >= pos['stop_loss']:
                self._close_pos(price, ts, 'SL')
            elif price <= pos['take_profit']:
                self._close_pos(price, ts, 'TP')

    def get_equity_curve(self):
        return pd.DataFrame({'equity': self.metrics.equity_curve})

    def get_trade_log(self):
        if not self.metrics.trades:
            return pd.DataFrame()
        return pd.DataFrame([{
            'entry_time': t.entry_time, 'exit_time': t.exit_time, 'side': t.side,
            'entry_price': t.entry_price, 'exit_price': t.exit_price, 'amount': t.amount,
            'pnl': t.pnl, 'pnl_pct': t.pnl_pct, 'fees': t.fees,
            'duration_hours': (t.exit_time - t.entry_time).total_seconds() / 3600
        } for t in self.metrics.trades])
