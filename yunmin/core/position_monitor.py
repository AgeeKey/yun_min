"""
Position Monitor - мониторинг открытых позиций в отдельном потоке

Основная задача: проверять Stop-Loss и Take-Profit каждые 5 секунд
и автоматически закрывать позиции при достижении условий.

ИСПРАВЛЯЕТ КРИТИЧЕСКУЮ ПРОБЛЕМУ:
- yunmin/bot.py, строка 142: update_position() делает return для DRY RUN
- Теперь позиции РЕАЛЬНО отслеживаются и закрываются
"""

import threading
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Данные открытой позиции для мониторинга"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    amount: float
    stop_loss: float
    take_profit: float
    trailing_stop_pct: float
    highest_price: float  # Для trailing stop (LONG)
    lowest_price: float   # Для trailing stop (SHORT)
    opened_at: datetime


class PositionMonitor:
    """
    Мониторинг позиций в фоновом режиме
    
    Запускается в отдельном потоке и каждые {check_interval} секунд
    проверяет все открытые позиции на условия закрытия:
    - Stop-Loss
    - Take-Profit
    - Trailing Stop-Loss
    """
    
    def __init__(self, bot_instance, check_interval: int = 5):
        """
        Args:
            bot_instance: Экземпляр YunMinBot
            check_interval: Интервал проверки в секундах (по умолчанию 5)
        """
        self.bot = bot_instance
        self.positions: Dict[str, Position] = {}
        self.check_interval = check_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        logger.info(f"PositionMonitor initialized with {check_interval}s check interval")
        
    def start(self):
        """Запустить мониторинг в фоновом потоке"""
        if self.running:
            logger.warning("PositionMonitor already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("✅ PositionMonitor started")
        
    def stop(self):
        """Остановить мониторинг"""
        if not self.running:
            return
            
        logger.info("Stopping PositionMonitor...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=10)
            
        logger.info("✅ PositionMonitor stopped")
            
    def add_position(self, position: Position):
        """
        Добавить позицию для мониторинга
        
        Args:
            position: Объект Position с данными позиции
        """
        self.positions[position.symbol] = position
        logger.info(
            f"📊 Added {position.side} position {position.symbol} to monitor "
            f"(SL: {position.stop_loss:.2f}, TP: {position.take_profit:.2f})"
        )
        
    def remove_position(self, symbol: str):
        """
        Удалить позицию из мониторинга
        
        Args:
            symbol: Символ позиции (например, 'BTC/USDT')
        """
        if symbol in self.positions:
            pos = self.positions[symbol]
            del self.positions[symbol]
            logger.info(f"📊 Removed {pos.side} position {symbol} from monitor")
            
    def get_position_count(self) -> int:
        """Получить количество отслеживаемых позиций"""
        return len(self.positions)
            
    def _monitor_loop(self):
        """
        Основной цикл мониторинга (выполняется в отдельном потоке)
        
        Проверяет все позиции каждые {check_interval} секунд
        """
        logger.info(f"🔄 Monitor loop started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                if self.positions:
                    self._check_all_positions()
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in position monitor loop: {e}", exc_info=True)
                time.sleep(self.check_interval)  # Продолжаем работу даже после ошибки
                
        logger.info("🔄 Monitor loop finished")
                
    def _check_all_positions(self):
        """Проверить все открытые позиции"""
        for symbol, pos in list(self.positions.items()):
            try:
                # Получить текущую цену
                ticker = self.bot.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Проверить условия закрытия
                should_close, reason = self._should_close_position(pos, current_price)
                
                if should_close:
                    logger.info(f"🎯 Closing {pos.side} {symbol}: {reason}")
                    self._close_position(pos, current_price, reason)
                    
            except Exception as e:
                logger.error(f"❌ Error checking position {symbol}: {e}")
                
    def _should_close_position(self, pos: Position, current_price: float) -> tuple[bool, str]:
        """
        Проверить, нужно ли закрыть позицию
        
        Args:
            pos: Позиция для проверки
            current_price: Текущая цена
            
        Returns:
            (should_close, reason): Нужно ли закрыть и причина
        """
        
        if pos.side == 'LONG':
            # LONG позиция: прибыль при росте цены, убыток при падении
            
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
            
            # Обновить trailing stop ТОЛЬКО если:
            # 1. Цена выросла ЗНАЧИТЕЛЬНО (минимум 1% от предыдущего максимума)
            # 2. И текущая прибыль >= 3% (чтобы защитить от ложных срабатываний)
            price_increase_pct = ((current_price - pos.highest_price) / pos.highest_price) * 100
            
            if current_price > pos.highest_price and price_increase_pct >= 1.0 and pnl_pct >= 3.0:
                old_highest = pos.highest_price
                pos.highest_price = current_price
                
                # Пересчитать Stop-Loss на основе новой максимальной цены
                new_stop_loss = current_price * (1 - pos.trailing_stop_pct / 100)
                if new_stop_loss > pos.stop_loss:
                    old_sl = pos.stop_loss
                    pos.stop_loss = new_stop_loss
                    logger.info(
                        f"📈 LONG {pos.symbol}: Trailing SL activated "
                        f"(highest: {old_highest:.2f}→{current_price:.2f}, "
                        f"SL: {old_sl:.2f}→{new_stop_loss:.2f}, P&L: {pnl_pct:+.2f}%)"
                    )
                
            # Проверка Stop-Loss
            if current_price <= pos.stop_loss:
                return True, f"Stop-Loss triggered (price {current_price:.2f} <= SL {pos.stop_loss:.2f}, P&L: {pnl_pct:.2f}%)"
                
            # Проверка Take-Profit
            if current_price >= pos.take_profit:
                return True, f"Take-Profit triggered (price {current_price:.2f} >= TP {pos.take_profit:.2f}, P&L: {pnl_pct:.2f}%)"
                
        else:  # SHORT
            # SHORT позиция: прибыль при падении цены, убыток при росте
            
            pnl_pct = ((pos.entry_price - current_price) / pos.entry_price) * 100
            
            # Обновить trailing stop ТОЛЬКО если:
            # 1. Цена упала ЗНАЧИТЕЛЬНО (минимум 1% от предыдущего минимума)
            # 2. И текущая прибыль >= 3% (чтобы защитить от ложных срабатываний)
            price_decrease_pct = ((pos.lowest_price - current_price) / pos.lowest_price) * 100
            
            if current_price < pos.lowest_price and price_decrease_pct >= 1.0 and pnl_pct >= 3.0:
                old_lowest = pos.lowest_price
                pos.lowest_price = current_price
                
                # Пересчитать Stop-Loss на основе новой минимальной цены
                new_stop_loss = current_price * (1 + pos.trailing_stop_pct / 100)
                if new_stop_loss < pos.stop_loss:
                    old_sl = pos.stop_loss
                    pos.stop_loss = new_stop_loss
                    logger.info(
                        f"📉 SHORT {pos.symbol}: Trailing SL activated "
                        f"(lowest: {old_lowest:.2f}→{current_price:.2f}, "
                        f"SL: {old_sl:.2f}→{new_stop_loss:.2f}, P&L: {pnl_pct:+.2f}%)"
                    )
                
            # Проверка Stop-Loss (для SHORT срабатывает при росте цены)
            if current_price >= pos.stop_loss:
                return True, f"Stop-Loss triggered (price {current_price:.2f} >= SL {pos.stop_loss:.2f}, P&L: {pnl_pct:.2f}%)"
                
            # Проверка Take-Profit (для SHORT срабатывает при падении цены)
            if current_price <= pos.take_profit:
                return True, f"Take-Profit triggered (price {current_price:.2f} <= TP {pos.take_profit:.2f}, P&L: {pnl_pct:.2f}%)"
                
        return False, ""
        
    def _close_position(self, pos: Position, current_price: float, reason: str):
        """
        Закрыть позицию через бота
        
        Args:
            pos: Позиция для закрытия
            current_price: Текущая цена закрытия
            reason: Причина закрытия
        """
        logger.info(f"💰 Closing {pos.side} position {pos.symbol} at {current_price:.2f}: {reason}")
        
        try:
            # Вызвать метод закрытия позиции в боте
            self.bot.close_position(pos.symbol, pos.side, current_price)
            
            # Удалить из мониторинга
            self.remove_position(pos.symbol)
            
            logger.info(f"✅ Position {pos.symbol} closed successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to close position {pos.symbol}: {e}", exc_info=True)
