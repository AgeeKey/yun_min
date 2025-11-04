"""
Multi-Currency Trading Bot

Manages multiple trading bots for different symbols simultaneously.
"""

import time
import threading
from typing import List, Dict, Any
from loguru import logger

from yunmin.bot import YunMinBot
from yunmin.core.config import YunMinConfig


class MultiCurrencyBot:
    """
    Orchestrates multiple trading bots for different symbols.
    
    Each symbol runs in its own thread with independent strategy.
    """
    
    def __init__(self, base_config: YunMinConfig, symbols: List[str]):
        """
        Initialize multi-currency bot.
        
        Args:
            base_config: Base configuration
            symbols: List of trading symbols (e.g., ['BTC/USDT', 'ETH/USDT'])
        """
        self.base_config = base_config
        self.symbols = symbols
        self.bots: Dict[str, YunMinBot] = {}
        self.threads: Dict[str, threading.Thread] = {}
        self.is_running = False
        
        logger.info(f"🌐 Multi-Currency Bot initialized with {len(symbols)} symbols")
        
    def start(self, interval: int = 60):
        """
        Start all trading bots.
        
        Args:
            interval: Check interval in seconds
        """
        self.is_running = True
        
        for i, symbol in enumerate(self.symbols):
            # Create config for this symbol
            config = self._create_symbol_config(symbol)
            
            # Create bot
            bot = YunMinBot(config)
            self.bots[symbol] = bot
            
            # Create thread
            thread = threading.Thread(
                target=self._run_bot,
                args=(bot, symbol, interval),
                name=f"Bot-{symbol.replace('/', '-')}",
                daemon=True
            )
            self.threads[symbol] = thread
            
            # Start thread
            thread.start()
            logger.info(f"🚀 Started bot for {symbol}")
            
            # Add delay between starting bots to avoid rate limiting
            if i < len(self.symbols) - 1:
                time.sleep(3)  # 3 second delay between each bot
                logger.debug("Waiting 3s before starting next bot...")
            
        logger.info(f"✅ All {len(self.symbols)} bots started!")
        
        # Keep main thread alive
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⚠️  Shutdown signal received")
            self.stop()
            
    def stop(self):
        """Stop all trading bots."""
        logger.info("🛑 Stopping all bots...")
        self.is_running = False
        
        for symbol, bot in self.bots.items():
            bot.stop()
            logger.info(f"Stopped bot for {symbol}")
            
        # Wait for threads to finish
        for thread in self.threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
                
        logger.info("✅ All bots stopped")
        
    def _create_symbol_config(self, symbol: str) -> YunMinConfig:
        """
        Create configuration for specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Symbol-specific configuration
        """
        # Clone base config
        import copy
        config = copy.deepcopy(self.base_config)
        
        # Update symbol
        config.trading.symbol = symbol
        
        # Adjust capital per symbol (split evenly)
        config.trading.initial_capital = self.base_config.trading.initial_capital / len(self.symbols)
        
        logger.debug(f"Config for {symbol}: capital=${config.trading.initial_capital:.2f}")
        
        return config
        
    def _run_bot(self, bot: YunMinBot, symbol: str, interval: int):
        """
        Run bot in thread with auto-recovery.
        
        Args:
            bot: Bot instance
            symbol: Trading symbol
            interval: Check interval
        """
        logger.info(f"[{symbol}] Bot thread started")
        retry_count = 0
        max_retries = 10
        
        while self.is_running and retry_count < max_retries:
            try:
                bot.run(interval=interval)
                break  # Normal exit
            except KeyboardInterrupt:
                logger.info(f"[{symbol}] Received stop signal")
                break
            except Exception as e:
                retry_count += 1
                logger.error(f"[{symbol}] Bot error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    wait_time = min(30 * retry_count, 300)  # Max 5 minutes
                    logger.info(f"[{symbol}] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"[{symbol}] Max retries reached, stopping bot")
        
        logger.info(f"[{symbol}] Bot thread stopped")
            
    def get_status(self) -> Dict[str, Any]:
        """
        Get status of all bots.
        
        Returns:
            Status dictionary
        """
        status = {
            'running': self.is_running,
            'symbols': self.symbols,
            'bots': {}
        }
        
        for symbol, bot in self.bots.items():
            status['bots'][symbol] = {
                'capital': bot.capital,
                'position': bot.current_position is not None
            }
            
        return status
