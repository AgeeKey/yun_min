"""
Yun Min Trading Bot - Main Entry Point

Coordinates all components: data ingestion, strategy, risk management, and execution.
"""

import time
from typing import Optional
import pandas as pd
from loguru import logger

from yunmin.core.config import YunMinConfig, load_config
from yunmin.data_ingest.exchange_adapter import ExchangeAdapter
from yunmin.strategy.ema_crossover import EMACrossoverStrategy
from yunmin.strategy.base import SignalType
from yunmin.risk.manager import RiskManager
from yunmin.risk.policies import OrderRequest, PositionInfo
from yunmin.execution.order_manager import OrderManager


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
            
        # Strategy
        self.strategy = EMACrossoverStrategy(
            fast_period=config.strategy.fast_ema,
            slow_period=config.strategy.slow_ema,
            rsi_period=config.strategy.rsi_period,
            rsi_overbought=config.strategy.rsi_overbought,
            rsi_oversold=config.strategy.rsi_oversold
        )
        
        # Risk manager
        self.risk_manager = RiskManager(config.risk)
        
        # Order manager
        self.order_manager = OrderManager(
            exchange=self.exchange,
            mode=config.trading.mode
        )
        
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
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.config.trading.symbol,
                timeframe=self.config.trading.timeframe,
                limit=100
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
            # Simplified position tracking for now
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
        """Open a long position."""
        if current_price is None:
            logger.error("Cannot open position without price")
            return
            
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
            logger.info(f"Long position opened: {result}")
        else:
            logger.warning("Order rejected by risk manager")
            
    def _open_short_position(self, signal, current_price: Optional[float]):
        """Open a short position."""
        # Similar to long but with 'sell' side
        logger.info("Short positions not yet implemented in this version")
        
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
        
        # Close exchange connection
        if self.exchange:
            self.exchange.close()
