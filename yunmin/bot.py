"""
Yun Min Trading Bot - Main Entry Point

Coordinates all components: data ingestion, strategy, risk management, and execution.
"""

import os
import time
from typing import Optional
import pandas as pd
from loguru import logger

from yunmin.core.config import YunMinConfig, load_config
from yunmin.data_ingest.exchange_adapter import ExchangeAdapter
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.strategy.base import SignalType
from yunmin.risk.manager import RiskManager
from yunmin.risk.policies import OrderRequest, PositionInfo
from yunmin.execution.order_manager import OrderManager
from yunmin.llm.grok_analyzer import GrokAnalyzer
from yunmin.llm.openai_analyzer import OpenAIAnalyzer
from yunmin.core.pnl_tracker import PnLTracker
from yunmin.store import (
    init_db, get_session, close_db,
    PositionRepository, TradeRepository, PortfolioRepository,
    PositionSide, StateManager
)


class YunMinBot:
    """
    Main trading bot that orchestrates all components.
    
    Architecture:
    1. Fetch market data
    2. Generate trading signals (Strategy)
    3. Validate with Risk Manager
    4. Execute orders (if approved)
    5. Monitor positions
    """
    
    def __init__(self, config: YunMinConfig):
        """
        Initialize Yun Min trading bot.
        
        Args:
            config: Bot configuration
        """
        self.config = config
        
        # Initialize components
        logger.info("Initializing Yun Min Trading Bot...")
        
        # Exchange adapter
        if config.exchange.api_key:
            self.exchange = ExchangeAdapter(config.exchange)
        else:
            logger.warning("No exchange API credentials - running without exchange connection")
            self.exchange = None
        
        # LLM Analyzer - ВЫБОР ПО ПРОВАЙДЕРУ (OpenAI или Groq)
        self.llm_analyzer = None
        if config.llm.enabled:
            provider = config.llm.provider.lower()
            
            if provider == "openai":
                # 🚀 OPENAI: GPT-5, GPT-4O-MINI, GPT-4O
                # Priority: 1) config.llm.api_key, 2) OPENAI_API_KEY env, 3) YUNMIN_LLM_API_KEY env
                api_key = (
                    config.llm.api_key 
                    if config.llm.api_key and not config.llm.api_key.startswith("${") 
                    else os.getenv("OPENAI_API_KEY") or os.getenv("YUNMIN_LLM_API_KEY")
                )
                model = config.llm.model or "gpt-5"
                self.llm_analyzer = OpenAIAnalyzer(api_key=api_key, model=model)
                if self.llm_analyzer.enabled:
                    logger.info(f"🚀 OpenAI analyzer enabled: {model}")
                else:
                    logger.warning("⚠️ OpenAI analyzer failed to initialize")
                    self.llm_analyzer = None
            
            elif provider == "grok":
                # 🤖 GROQ: Llama 3.3 70B
                self.llm_analyzer = GrokAnalyzer()
                if self.llm_analyzer.enabled:
                    logger.info("🤖 Groq AI analyzer enabled")
                else:
                    logger.warning("⚠️ Groq analyzer failed to initialize")
                    self.llm_analyzer = None
            else:
                logger.warning(f"❌ Unknown LLM provider: {provider}")
        
        # Strategy - выбираем на основе LLM
        if self.llm_analyzer and self.llm_analyzer.enabled:
            # 🤖 AI-DRIVEN TRADING: LLM принимает решения!
            self.strategy = GrokAIStrategy(grok_analyzer=self.llm_analyzer)
            logger.info(f"🤖 Using AI STRATEGY with {config.llm.provider.upper()}")
        else:
            # Fallback: традиционная стратегия
            self.strategy = EMACrossoverStrategy(
                fast_period=config.strategy.fast_ema,
                slow_period=config.strategy.slow_ema,
                rsi_period=config.strategy.rsi_period,
                rsi_overbought=config.strategy.rsi_overbought,
                rsi_oversold=config.strategy.rsi_oversold
            )
            logger.info("Using EMA Crossover Strategy (traditional)")
        
        # Risk manager
        self.risk_manager = RiskManager(config.risk)
        
        # Order manager
        self.order_manager = OrderManager(
            exchange=self.exchange,
            mode=config.trading.mode
        )
        
        # P&L Tracker
        self.pnl_tracker = PnLTracker()
        logger.info("📊 P&L Tracker initialized")
        
        # 💾 Initialize Database (persistence layer)
        if hasattr(config, 'database') and config.database.db_url:
            db_url = config.database.db_url
        else:
            db_url = 'sqlite:///data/yunmin.db'
        
        init_db(db_url)
        self.db_session = get_session()
        self.pos_repo = PositionRepository(self.db_session)
        self.trade_repo = TradeRepository(self.db_session)
        self.portfolio_repo = PortfolioRepository(self.db_session)
        logger.info(f"💾 Database initialized: {db_url}")
        
        # � JSON StateManager для быстрого бэкапа (дополнительно к DB)
        self.state_manager = StateManager('data')
        logger.info("💾 StateManager initialized for JSON backup")
        
        # �🔄 Restore open positions from database (crash recovery)
        self._restore_positions()
        
        # State
        self.capital = config.trading.initial_capital
        self.current_position: Optional[PositionInfo] = None
        self.is_running = False
        
        logger.info(
            f"Bot initialized - Mode: {config.trading.mode}, "
            f"Symbol: {config.trading.symbol}, "
            f"Capital: ${self.capital:.2f}"
        )
        
    def fetch_market_data(self) -> pd.DataFrame:
        """Fetch and prepare market data for analysis."""
        if self.exchange is None:
            # Return dummy data for testing without exchange
            logger.warning("No exchange connection - using dummy data")
            return pd.DataFrame()
            
        try:
            # Fetch OHLCV data - УВЕЛИЧЕНО с 100 до 200 для лучшего анализа
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.config.trading.symbol,
                timeframe=self.config.trading.timeframe,
                limit=200  # Больше исторических данных для Grok AI
            )
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            return pd.DataFrame()
            
    def get_current_price(self) -> Optional[float]:
        """Get current market price."""
        if self.exchange is None:
            return None
            
        try:
            ticker = self.exchange.fetch_ticker(self.config.trading.symbol)
            return ticker.get('last') or ticker.get('close')
        except Exception as e:
            logger.error(f"Failed to fetch current price: {e}")
            return None
            
    def update_position(self):
        """Update current position information."""
        if self.exchange is None or self.config.trading.mode == 'dry_run':
            # For dry-run, track positions from paper trading
            paper_pos = self.order_manager.get_paper_positions()
            
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Убрали return!
            # Теперь позиции РЕАЛЬНО отслеживаются через PositionMonitor
            
            # Инициализировать PositionMonitor если есть открытые позиции
            if paper_pos and not hasattr(self, 'position_monitor'):
                from yunmin.core.position_monitor import PositionMonitor
                self.position_monitor = PositionMonitor(self, check_interval=5)
                self.position_monitor.start()
                logger.info("✅ PositionMonitor started for DRY RUN mode")
            
            # Обновить unrealized P&L для открытых позиций
            if self.pnl_tracker.open_positions:
                current_price = self.get_current_price()
                if current_price:
                    prices = {self.config.trading.symbol: current_price}
                    self.pnl_tracker.update_unrealized_pnl(prices)
                
            return
            
        try:
            positions = self.exchange.fetch_positions([self.config.trading.symbol])
            if positions:
                pos = positions[0]
                current_price = self.get_current_price()
                
                if pos.get('contracts', 0) > 0 and current_price:
                    self.current_position = PositionInfo(
                        symbol=self.config.trading.symbol,
                        size=pos['contracts'],
                        entry_price=pos['entryPrice'],
                        current_price=current_price,
                        leverage=pos.get('leverage', 1),
                        unrealized_pnl=pos.get('unrealizedPnl', 0)
                    )
                else:
                    self.current_position = None
            else:
                self.current_position = None
                
        except Exception as e:
            logger.error(f"Failed to update position: {e}")
            
    def process_signal(self, signal, current_price: Optional[float]):
        """Process trading signal and execute if validated."""
        
        # Get LLM analysis if enabled
        if self.llm_analyzer and self.llm_analyzer.enabled:
            market_data = {
                'price': current_price,
                'rsi': getattr(signal, 'rsi', None),
                'trend': getattr(signal, 'trend', 'unknown'),
                'signal_type': signal.type.value
            }
            
            # Use explain_signal if available (both OpenAI and Groq have it)
            if hasattr(self.llm_analyzer, 'explain_signal'):
                llm_insight = self.llm_analyzer.explain_signal(
                    signal.type.value, 
                    signal.reason, 
                    market_data
                )
                logger.info(f"🤖 AI: {llm_insight}")
        
        logger.info(f"Signal: {signal}")
        
        if signal.type == SignalType.HOLD:
            return
            
        # Check if we should close position
        if self.current_position:
            should_close, reason = self.risk_manager.check_position(self.current_position)
            if should_close:
                logger.warning(f"Closing position: {reason}")
                self._close_position(current_price)
                return
                
        # Process new signals
        if signal.type == SignalType.BUY and self.current_position is None:
            self._open_long_position(signal, current_price)
        elif signal.type == SignalType.SELL and self.current_position is None:
            self._open_short_position(signal, current_price)
        elif signal.type == SignalType.CLOSE and self.current_position:
            self._close_position(current_price)
            
    def _open_long_position(self, signal, current_price: Optional[float]):
        """
        Open a LONG position.
        
        LONG позиция: прибыль при росте цены, убыток при падении.
        """
        if current_price is None:
            logger.error("Cannot open LONG position without price")
            return
        
        logger.info(f"🔼 Opening LONG position for {self.config.trading.symbol} @ {current_price:.2f}")
            
        # Calculate position size
        position_value = self.capital * self.config.risk.max_position_size
        amount = position_value / current_price
        
        # Create order request
        order = OrderRequest(
            symbol=self.config.trading.symbol,
            side='buy',
            order_type='market',
            amount=amount,
            price=current_price,
            leverage=1.0  # Start with no leverage for safety
        )
        
        # Validate with risk manager
        context = {'capital': self.capital, 'current_price': current_price}
        approved, messages = self.risk_manager.validate_order(order, context)
        
        for msg in messages:
            logger.info(msg)
            
        if approved:
            # Execute order
            result = self.order_manager.execute_order(order, current_price)
            logger.info(f"✅ LONG position opened: {result}")
            
            # Рассчитать комиссию (0.1% от стоимости позиции)
            entry_fee = position_value * 0.001  # 0.1% комиссия
            
            # Добавить в P&L Tracker
            self.pnl_tracker.open_position(
                symbol=self.config.trading.symbol,
                side='LONG',
                entry_price=current_price,
                amount=amount,
                entry_fee=entry_fee
            )
            logger.info("📊 P&L tracking started for LONG position")
            
            # � JSON Backup: Save immediately after opening
            try:
                self.state_manager.save_positions(self.pnl_tracker.open_positions)
                logger.info("💾 LONG position saved to JSON backup")
            except Exception as e:
                logger.error(f"Failed to save position state: {e}")
            
            # �💾 Save position to database
            try:
                from yunmin.store import PositionSide
                db_position = self.pos_repo.create(
                    symbol=self.config.trading.symbol,
                    side=PositionSide.LONG,
                    entry_price=current_price,
                    amount=amount,
                    stop_loss=current_price * (1 - self.config.risk.stop_loss_pct),
                    take_profit=current_price * (1 + self.config.risk.take_profit_pct),
                    entry_fee=entry_fee,
                    strategy_name='EMA_Crossover'
                )
                logger.info(f"💾 Position saved to database (ID: {db_position.id})")
                
                # Record entry trade
                self.trade_repo.create(
                    symbol=self.config.trading.symbol,
                    side='buy',
                    price=current_price,
                    amount=amount,
                    fee=entry_fee,
                    position_id=db_position.id
                )
            except Exception as e:
                logger.error(f"Failed to save position to database: {e}")
            
            # Добавить в PositionMonitor для автоматического закрытия
            if self.config.trading.mode == 'dry_run':
                # Инициализировать PositionMonitor если нужно
                if not hasattr(self, 'position_monitor'):
                    from yunmin.core.position_monitor import PositionMonitor
                    self.position_monitor = PositionMonitor(self, check_interval=5)
                    self.position_monitor.start()
                    logger.info("✅ PositionMonitor started for LONG position")
                
                # Создать позицию для мониторинга
                from yunmin.core.position_monitor import Position
                from datetime import datetime
                
                # Для LONG:
                # Stop-Loss ниже entry (цена падает = убыток)
                # Take-Profit выше entry (цена растёт = прибыль)
                monitor_pos = Position(
                    symbol=self.config.trading.symbol,
                    side='LONG',
                    entry_price=current_price,
                    amount=amount,
                    stop_loss=current_price * (1 - self.config.risk.stop_loss_pct),  # Ниже entry
                    take_profit=current_price * (1 + self.config.risk.take_profit_pct),  # Выше entry
                    trailing_stop_pct=2.0,  # 2% trailing stop
                    highest_price=current_price,
                    lowest_price=current_price,
                    opened_at=datetime.now()
                )
                
                self.position_monitor.add_position(monitor_pos)
                logger.info(
                    f"📊 LONG position added to monitor: "
                    f"SL {monitor_pos.stop_loss:.2f} (-{self.config.risk.stop_loss_pct*100:.1f}%), "
                    f"TP {monitor_pos.take_profit:.2f} (+{self.config.risk.take_profit_pct*100:.1f}%)"
                )
        else:
            logger.warning("Order rejected by risk manager")
            
    def _open_short_position(self, signal, current_price: Optional[float]):
        """
        Open a SHORT position.
        
        SHORT позиция: прибыль при падении цены, убыток при росте.
        """
        if current_price is None:
            logger.error("Cannot open SHORT position without price")
            return
            
        logger.info(f"🔽 Opening SHORT position for {self.config.trading.symbol} @ {current_price:.2f}")
        
        # Calculate position size
        position_value = self.capital * self.config.risk.max_position_size
        amount = position_value / current_price
        
        # Create SHORT order request
        order = OrderRequest(
            symbol=self.config.trading.symbol,
            side='sell',  # SHORT = SELL
            order_type='market',
            amount=amount,
            price=current_price,
            leverage=1.0  # Start with no leverage for safety
        )
        
        # Validate with risk manager
        context = {'capital': self.capital, 'current_price': current_price}
        approved, messages = self.risk_manager.validate_order(order, context)
        
        for msg in messages:
            logger.info(msg)
            
        if approved:
            # Execute SHORT order
            result = self.order_manager.execute_order(order, current_price)
            logger.info(f"✅ SHORT position opened: {result}")
            
            # Рассчитать комиссию (0.1% от стоимости позиции)
            entry_fee = position_value * 0.001  # 0.1% комиссия
            
            # Добавить в P&L Tracker
            self.pnl_tracker.open_position(
                symbol=self.config.trading.symbol,
                side='SHORT',
                entry_price=current_price,
                amount=amount,
                entry_fee=entry_fee
            )
            logger.info("📊 P&L tracking started for SHORT position")
            
            # � JSON Backup: Save immediately after opening
            try:
                self.state_manager.save_positions(self.pnl_tracker.open_positions)
                logger.info("💾 SHORT position saved to JSON backup")
            except Exception as e:
                logger.error(f"Failed to save position state: {e}")
            
            # �💾 Save position to database
            try:
                from yunmin.store import PositionSide
                db_position = self.pos_repo.create(
                    symbol=self.config.trading.symbol,
                    side=PositionSide.SHORT,
                    entry_price=current_price,
                    amount=amount,
                    stop_loss=current_price * (1 + self.config.risk.stop_loss_pct),  # Выше для SHORT
                    take_profit=current_price * (1 - self.config.risk.take_profit_pct),  # Ниже для SHORT
                    entry_fee=entry_fee,
                    strategy_name='EMA_Crossover'
                )
                logger.info(f"💾 SHORT position saved to database (ID: {db_position.id})")
                
                # Record entry trade
                self.trade_repo.create(
                    symbol=self.config.trading.symbol,
                    side='sell',
                    price=current_price,
                    amount=amount,
                    fee=entry_fee,
                    position_id=db_position.id
                )
            except Exception as e:
                logger.error(f"Failed to save SHORT position to database: {e}")
            
            # Добавить в PositionMonitor для автоматического закрытия
            if self.config.trading.mode == 'dry_run':
                # Инициализировать PositionMonitor если нужно
                if not hasattr(self, 'position_monitor'):
                    from yunmin.core.position_monitor import PositionMonitor, Position
                    from datetime import datetime
                    self.position_monitor = PositionMonitor(self, check_interval=5)
                    self.position_monitor.start()
                    logger.info("✅ PositionMonitor started for SHORT position")
                
                # Создать позицию для мониторинга
                from yunmin.core.position_monitor import Position
                from datetime import datetime
                
                # Получить параметры риска для SHORT
                # Если есть отдельные параметры для SHORT, используем их
                if hasattr(self.config.risk, 'short'):
                    stop_loss_pct = self.config.risk.short.stop_loss_pct
                    take_profit_pct = self.config.risk.short.take_profit_pct
                    trailing_pct = getattr(self.config.risk.short, 'trailing_stop_pct', 2.0)
                else:
                    # Используем обычные параметры с запасом
                    stop_loss_pct = self.config.risk.stop_loss_pct * 1.2  # +20% запас для SHORT
                    take_profit_pct = self.config.risk.take_profit_pct
                    trailing_pct = 2.0
                
                # Для SHORT:
                # Stop-Loss выше entry (цена растёт = убыток)
                # Take-Profit ниже entry (цена падает = прибыль)
                monitor_pos = Position(
                    symbol=self.config.trading.symbol,
                    side='SHORT',
                    entry_price=current_price,
                    amount=amount,
                    stop_loss=current_price * (1 + stop_loss_pct / 100),  # Выше entry
                    take_profit=current_price * (1 - take_profit_pct / 100),  # Ниже entry
                    trailing_stop_pct=trailing_pct,
                    highest_price=current_price,
                    lowest_price=current_price,
                    opened_at=datetime.now()
                )
                
                self.position_monitor.add_position(monitor_pos)
                logger.info(
                    f"📊 SHORT position added to monitor: "
                    f"SL {monitor_pos.stop_loss:.2f} (+{stop_loss_pct:.1f}%), "
                    f"TP {monitor_pos.take_profit:.2f} (-{take_profit_pct:.1f}%)"
                )
        else:
            logger.warning("SHORT order rejected by risk manager")
        
    def _close_position(self, current_price: Optional[float]):
        """Close current position."""
        if self.current_position is None:
            return
            
        logger.info(f"Closing position for {self.config.trading.symbol}")
        
        # Create closing order
        order = OrderRequest(
            symbol=self.config.trading.symbol,
            side='sell',  # Close long
            order_type='market',
            amount=self.current_position.size,
            price=current_price
        )
        
        # Execute without risk checks (emergency close)
        result = self.order_manager.execute_order(order, current_price)
        logger.info(f"Position closed: {result}")
        
        self.current_position = None
        
    def run_once(self):
        """Run one iteration of the trading loop."""
        logger.info("=== Trading Loop Iteration ===")
        
        # Check circuit breaker
        if self.risk_manager.is_circuit_breaker_triggered():
            logger.error("Circuit breaker is triggered - trading halted")
            return
            
        # Fetch market data
        df = self.fetch_market_data()
        if df.empty:
            logger.warning("No market data available")
            return
            
        # Get current price
        current_price = self.get_current_price()
        logger.info(f"Current price: {current_price}")
        
        # Update position
        self.update_position()
        
        # Generate signal
        signal = self.strategy.analyze(df)
        
        # Process signal
        self.process_signal(signal, current_price)
        
        # Log risk summary
        context = {'capital': self.capital}
        risk_summary = self.risk_manager.get_risk_summary(context)
        logger.info(f"Risk summary: {risk_summary}")
        
        # Log P&L summary
        if self.pnl_tracker.total_trades > 0 or self.pnl_tracker.open_positions:
            summary = self.pnl_tracker.get_summary()
            logger.info(
                f"💰 P&L: Total ${summary['total_pnl']:+.2f} | "
                f"Realized ${summary['total_realized_pnl']:+.2f} | "
                f"Unrealized ${summary['total_unrealized_pnl']:+.2f} | "
                f"Trades: {summary['total_trades']} ({summary['win_rate']:.0f}% WR)"
            )
        
    def run(self, iterations: Optional[int] = None, interval: int = 60):
        """
        Run the trading bot.
        
        Args:
            iterations: Number of iterations (None for infinite)
            interval: Seconds between iterations
        """
        self.is_running = True
        iteration_count = 0
        
        logger.info(f"Starting Yun Min bot - interval: {interval}s")
        
        try:
            while self.is_running:
                self.run_once()
                
                iteration_count += 1
                if iterations and iteration_count >= iterations:
                    logger.info(f"Completed {iterations} iterations")
                    break
                    
                logger.info(f"Waiting {interval}s until next iteration...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise
        finally:
            self.stop()
            
    def stop(self):
        """Stop the trading bot."""
        self.is_running = False
        logger.info("Yun Min bot stopped")
        
        # 💾 Create final portfolio snapshot before shutdown
        try:
            summary = self.pnl_tracker.get_summary()
            self.portfolio_repo.create_snapshot(
                total_capital=self.capital + summary['total_pnl'],
                available_capital=self.capital,
                total_exposure=0.0,
                total_pnl=summary['total_pnl'],
                realized_pnl=summary['realized_pnl'],
                unrealized_pnl=summary['unrealized_pnl'],
                win_rate=self.pnl_tracker.get_win_rate(),
                active_symbols_count=len(self.pnl_tracker.open_positions)
            )
            logger.info("💾 Final portfolio snapshot saved")
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")
        
        # Stop position monitor if running
        if hasattr(self, 'position_monitor') and self.position_monitor:
            self.position_monitor.stop()
        
        # Close database connection
        if hasattr(self, 'db_session'):
            close_db()
            logger.info("💾 Database connection closed")
        
        # Close exchange connection
        if self.exchange:
            self.exchange.close()
    
    def get_statistics(self) -> dict:
        """
        Get current bot statistics.
        
        Returns:
            Dictionary with current trading statistics including P&L,
            trades, win rate, and open positions
        """
        summary = self.pnl_tracker.get_summary()
        
        return {
            'total_trades': summary['total_trades'],
            'winning_trades': summary['winning_trades'],
            'losing_trades': summary['losing_trades'],
            'win_rate': summary['win_rate'],
            'total_pnl': summary['total_pnl'],
            'realized_pnl': summary['total_realized_pnl'],
            'unrealized_pnl': summary['total_unrealized_pnl'],
            'total_fees': summary['total_fees'],
            'open_positions': summary['open_positions'],
            'avg_win': summary['avg_win'],
            'avg_loss': summary['avg_loss'],
            'profit_factor': summary['profit_factor'],
            'current_capital': self.capital + summary['total_pnl']
        }
    
    def _restore_positions(self):
        """
        🔄 Restore open positions from database (crash recovery).
        
        При перезапуске бота после краша, восстанавливаем все открытые позиции
        из базы данных.
        """
        try:
            open_positions = self.pos_repo.get_open_positions()
            
            if not open_positions:
                logger.info("No open positions to restore")
                return
            
            logger.info(f"🔄 Restoring {len(open_positions)} open position(s) from database...")
            
            for db_pos in open_positions:
                # Восстановить в P&L Tracker
                self.pnl_tracker.open_positions[db_pos.symbol] = {
                    'side': db_pos.side.value,
                    'entry_price': db_pos.entry_price,
                    'amount': db_pos.amount,
                    'entry_fee': db_pos.entry_fee or 0.0,
                    'opened_at': db_pos.opened_at
                }
                
                logger.info(
                    f"  ✅ {db_pos.side.value} {db_pos.symbol} @ "
                    f"{db_pos.entry_price:.2f} x{db_pos.amount:.6f}"
                )
                
                # Инициализировать PositionMonitor если в DRY RUN режиме
                if self.config.trading.mode == 'dry_run':
                    if not hasattr(self, 'position_monitor'):
                        from yunmin.core.position_monitor import PositionMonitor
                        self.position_monitor = PositionMonitor(self, check_interval=5)
                        self.position_monitor.start()
                        logger.info("✅ PositionMonitor started (restored positions)")
                    
                    # Добавить позицию в монитор
                    from yunmin.core.position_monitor import Position
                    
                    current_price = self.get_current_price() or db_pos.entry_price
                    
                    monitor_pos = Position(
                        symbol=db_pos.symbol,
                        side=db_pos.side.value,
                        entry_price=db_pos.entry_price,
                        amount=db_pos.amount,
                        stop_loss=db_pos.stop_loss,
                        take_profit=db_pos.take_profit,
                        trailing_stop_pct=2.0,
                        highest_price=max(current_price, db_pos.entry_price),
                        lowest_price=min(current_price, db_pos.entry_price),
                        opened_at=db_pos.opened_at
                    )
                    
                    self.position_monitor.positions[db_pos.symbol] = monitor_pos
            
            logger.info("🔄 Position restoration complete")
            
        except Exception as e:
            logger.error(f"Failed to restore positions: {e}")
            logger.warning("Starting with clean state...")
            
    def close_position(self, symbol: str, side: str, current_price: float):
        """
        Close position (called by PositionMonitor)
        
        Args:
            symbol: Symbol to close (e.g., 'BTC/USDT')
            side: Position side ('LONG' or 'SHORT')
            current_price: Current price for closing
        """
        logger.info(f"💰 Closing {side} position {symbol} at {current_price:.2f}")
        
        # Рассчитать комиссию за закрытие (0.1%)
        if symbol in self.pnl_tracker.open_positions:
            pos = self.pnl_tracker.open_positions[symbol]
            position_value = pos['amount'] * current_price
            exit_fee = position_value * 0.001  # 0.1% комиссия
        else:
            exit_fee = 0.0
        
        # Записать в P&L Tracker
        trade = self.pnl_tracker.close_position(
            symbol=symbol,
            exit_price=current_price,
            exit_fee=exit_fee
        )
        
        # � JSON Backup: Save trades immediately
        try:
            self.state_manager.save_trades(self.pnl_tracker.closed_positions)
            self.state_manager.save_positions(self.pnl_tracker.open_positions)
            stats = {
                'total_pnl': self.pnl_tracker.total_realized_pnl,
                'total_trades': self.pnl_tracker.total_trades,
                'winning_trades': self.pnl_tracker.winning_trades,
                'losing_trades': self.pnl_tracker.losing_trades,
                'win_rate': self.pnl_tracker.get_win_rate()
            }
            self.state_manager.save_statistics(stats)
            logger.info("💾 State saved to JSON backup")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
        
        # �💾 Close position in database
        try:
            # Find open position in database
            open_positions = self.pos_repo.get_open_positions(symbol=symbol)
            if open_positions:
                db_pos = open_positions[0]  # Get first open position
                
                # Close it
                closed_pos = self.pos_repo.close(
                    position_id=db_pos.id,
                    exit_price=current_price,
                    exit_fee=exit_fee
                )
                
                logger.info(f"💾 Position closed in database (P&L: ${closed_pos.realized_pnl:+.2f})")
                
                # Record exit trade
                close_side = 'sell' if side == 'LONG' else 'buy'
                self.trade_repo.create(
                    symbol=symbol,
                    side=close_side,
                    price=current_price,
                    amount=db_pos.amount,
                    fee=exit_fee,
                    position_id=db_pos.id
                )
        except Exception as e:
            logger.error(f"Failed to close position in database: {e}")
        
        if trade:
            logger.info(
                f"📊 P&L: {trade.pnl:+.2f} USDT ({trade.pnl_pct:+.2f}%) | "
                f"Win Rate: {self.pnl_tracker.get_win_rate():.1f}%"
            )
            
            # Вывести сводку
            summary = self.pnl_tracker.get_summary()
            logger.info(
                f"💰 Total P&L: ${summary['total_pnl']:+.2f} | "
                f"Trades: {summary['total_trades']} | "
                f"Wins: {summary['winning_trades']}/{summary['total_trades']}"
            )
        
        if self.config.trading.mode == 'dry_run':
            # Закрыть виртуальную позицию
            self.order_manager.close_paper_position(symbol, current_price)
            logger.info(f"✅ DRY RUN: Closed {side} {symbol} at {current_price:.2f}")
        else:
            # Закрыть реальную позицию на бирже
            try:
                # Определить направление закрытия
                close_side = 'sell' if side == 'LONG' else 'buy'
                
                # Получить размер позиции
                positions = self.exchange.fetch_positions([symbol])
                if positions and len(positions) > 0:
                    amount = positions[0]['contracts']
                    
                    # Создать ордер на закрытие
                    order = self.exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=close_side,
                        amount=amount
                    )
                    
                    logger.info(f"✅ LIVE: Closed {side} {symbol}, order: {order}")
                else:
                    logger.warning(f"⚠️ No open position found for {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to close position {symbol}: {e}", exc_info=True)
