"""
BOSS DECISION: Trend Following + Breakout Strategy

ПРОБЛЕМА:
- Oct 28 - Nov 3: BTC $67k → $73k (+9% trending move)
- EMA Crossover: Ловит тренд, но много ложных сигналов (-21.54%)
- RSI Mean Reversion: Отлично на choppy, но период был трендовый (-9.86%)

РЕШЕНИЕ: TREND BREAKOUT STRATEGY
- MACD для подтверждения тренда
- Bollinger Bands для breakout сигналов
- Входим на пробой BB + MACD подтверждение
- Выходим по trailing stop (следуем за трендом)

ЛОГИКА:
BUY:
- Price пробивает BB upper (breakout вверх)
- MACD > Signal (восходящий тренд)
- MACD Histogram > 0 (momentum растет)
- Volume > avg * 1.2 (подтверждение объемом)

SELL:
- Price пробивает BB lower (breakout вниз)
- MACD < Signal (нисходящий тренд)
- MACD Histogram < 0 (momentum падает)
- Volume > avg * 1.2

EXIT:
- Trailing Stop: 1.5% от peak
- Take Profit: 3% (risk:reward 1:2)
- MACD разворот (пересечение линий)

ПАРАМЕТРЫ:
- BB: 20 период, 2σ (стандарт)
- MACD: 12, 26, 9 (стандарт)
- Volume MA: 20 период
- Trailing Stop: 1.5%
- Take Profit: 3%
- Position Size: 90% capital (агрессивно на тренде)

Автор: Boss Agent (Autonomous Decision)
Дата: 2024-11-04
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TrendBreakoutMACD:
    """
    Trend Following + Breakout Strategy
    
    Стратегия для трендовых рынков:
    - MACD для определения тренда
    - Bollinger Bands для точек входа
    - Volume для подтверждения
    - Trailing Stop для максимизации прибыли на тренде
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        volume_period: int = 20,
        volume_multiplier: float = 1.2,
        trailing_stop_pct: float = 0.015,  # 1.5%
        take_profit_pct: float = 0.03,     # 3%
        position_size_pct: float = 0.9     # 90% capital
    ):
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.volume_period = volume_period
        self.volume_multiplier = volume_multiplier
        self.trailing_stop_pct = trailing_stop_pct
        self.take_profit_pct = take_profit_pct
        self.position_size_pct = position_size_pct
        
        self.position = None
        self.entry_price = None
        self.peak_price = None  # Для trailing stop
        self.stop_loss = None
        self.take_profit = None
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Рассчитываем все индикаторы"""
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
        bb_std_dev = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std_dev * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std_dev * self.bb_std)
        
        # MACD
        ema_fast = df['close'].ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.macd_slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(window=self.volume_period).mean()
        
        return df
        
    def check_breakout_long(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """Проверяем условия для LONG входа (breakout вверх)"""
        # 1. Price пробивает BB upper (сейчас выше, раньше был ниже или около)
        breakout = (
            row['close'] > row['bb_upper'] and
            prev_row['close'] <= prev_row['bb_upper']
        )
        
        # 2. MACD подтверждает восходящий тренд
        macd_bullish = (
            row['macd'] > row['macd_signal'] and
            row['macd_histogram'] > 0
        )
        
        # 3. Volume выше среднего (подтверждение)
        volume_confirm = (
            row['volume'] > row['volume_ma'] * self.volume_multiplier
        )
        
        return breakout and macd_bullish and volume_confirm
        
    def check_breakout_short(self, row: pd.Series, prev_row: pd.Series) -> bool:
        """Проверяем условия для SHORT входа (breakout вниз)"""
        # 1. Price пробивает BB lower
        breakout = (
            row['close'] < row['bb_lower'] and
            prev_row['close'] >= prev_row['bb_lower']
        )
        
        # 2. MACD подтверждает нисходящий тренд
        macd_bearish = (
            row['macd'] < row['macd_signal'] and
            row['macd_histogram'] < 0
        )
        
        # 3. Volume подтверждение
        volume_confirm = (
            row['volume'] > row['volume_ma'] * self.volume_multiplier
        )
        
        return breakout and macd_bearish and volume_confirm
        
    def check_exit_signal(self, row: pd.Series, current_price: float) -> tuple[bool, str]:
        """Проверяем условия выхода из позиции"""
        if self.position is None:
            return False, ""
            
        # 1. Take Profit
        if self.position == 'LONG':
            if current_price >= self.take_profit:
                return True, "TAKE_PROFIT"
                
            # Update peak для trailing stop
            if current_price > self.peak_price:
                self.peak_price = current_price
                # Обновляем trailing stop
                self.stop_loss = self.peak_price * (1 - self.trailing_stop_pct)
                
            # 2. Trailing Stop
            if current_price <= self.stop_loss:
                return True, "TRAILING_STOP"
                
            # 3. MACD разворот (MACD пересекает signal вниз)
            if row['macd'] < row['macd_signal'] and row['macd_histogram'] < 0:
                return True, "MACD_REVERSAL"
                
        elif self.position == 'SHORT':
            if current_price <= self.take_profit:
                return True, "TAKE_PROFIT"
                
            # Update peak для trailing stop (для SHORT - это минимум)
            if current_price < self.peak_price:
                self.peak_price = current_price
                self.stop_loss = self.peak_price * (1 + self.trailing_stop_pct)
                
            # Trailing Stop для SHORT
            if current_price >= self.stop_loss:
                return True, "TRAILING_STOP"
                
            # MACD разворот вверх
            if row['macd'] > row['macd_signal'] and row['macd_histogram'] > 0:
                return True, "MACD_REVERSAL"
                
        return False, ""
        
    def generate_signals(self, df: pd.DataFrame) -> List[Dict]:
        """Генерируем торговые сигналы"""
        df = self.calculate_indicators(df)
        signals = []
        
        # Нужна предыдущая свеча для определения breakout
        for i in range(max(self.bb_period, self.macd_slow) + 1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i - 1]
            current_price = row['close']
            
            # Проверяем выход из позиции (если есть)
            if self.position is not None:
                should_exit, exit_reason = self.check_exit_signal(row, current_price)
                
                if should_exit:
                    signal = {
                        'timestamp': row['timestamp'],
                        'action': 'EXIT',
                        'position_type': self.position,
                        'price': current_price,
                        'reason': exit_reason,
                        'macd': row['macd'],
                        'macd_signal': row['macd_signal'],
                        'bb_upper': row['bb_upper'],
                        'bb_lower': row['bb_lower'],
                    }
                    signals.append(signal)
                    
                    # Reset позиция
                    self.position = None
                    self.entry_price = None
                    self.peak_price = None
                    self.stop_loss = None
                    self.take_profit = None
                    continue
                    
            # Проверяем вход в позицию (если свободны)
            if self.position is None:
                # LONG breakout
                if self.check_breakout_long(row, prev_row):
                    self.position = 'LONG'
                    self.entry_price = current_price
                    self.peak_price = current_price
                    self.stop_loss = current_price * (1 - self.trailing_stop_pct)
                    self.take_profit = current_price * (1 + self.take_profit_pct)
                    
                    signal = {
                        'timestamp': row['timestamp'],
                        'action': 'BUY',
                        'position_type': 'LONG',
                        'price': current_price,
                        'stop_loss': self.stop_loss,
                        'take_profit': self.take_profit,
                        'reason': 'BB_BREAKOUT_UP_MACD_BULLISH',
                        'macd': row['macd'],
                        'macd_signal': row['macd_signal'],
                        'bb_upper': row['bb_upper'],
                        'volume_ratio': row['volume'] / row['volume_ma'],
                    }
                    signals.append(signal)
                    
                # SHORT breakout
                elif self.check_breakout_short(row, prev_row):
                    self.position = 'SHORT'
                    self.entry_price = current_price
                    self.peak_price = current_price
                    self.stop_loss = current_price * (1 + self.trailing_stop_pct)
                    self.take_profit = current_price * (1 - self.take_profit_pct)
                    
                    signal = {
                        'timestamp': row['timestamp'],
                        'action': 'SELL',
                        'position_type': 'SHORT',
                        'price': current_price,
                        'stop_loss': self.stop_loss,
                        'take_profit': self.take_profit,
                        'reason': 'BB_BREAKOUT_DOWN_MACD_BEARISH',
                        'macd': row['macd'],
                        'macd_signal': row['macd_signal'],
                        'bb_lower': row['bb_lower'],
                        'volume_ratio': row['volume'] / row['volume_ma'],
                    }
                    signals.append(signal)
                    
        return signals
        
    def get_position_size(self, capital: float, price: float) -> float:
        """Рассчитываем размер позиции"""
        position_value = capital * self.position_size_pct
        quantity = position_value / price
        return quantity
        
    def get_name(self) -> str:
        """Название стратегии"""
        return "Trend Breakout MACD"
        
    def get_description(self) -> str:
        """Описание стратегии"""
        return (
            f"Trend Following + Breakout Strategy:\n"
            f"- BB({self.bb_period}, {self.bb_std}σ) для breakout сигналов\n"
            f"- MACD({self.macd_fast}, {self.macd_slow}, {self.macd_signal}) для тренда\n"
            f"- Volume > {self.volume_multiplier}x MA для подтверждения\n"
            f"- Trailing Stop: {self.trailing_stop_pct*100:.1f}%\n"
            f"- Take Profit: {self.take_profit_pct*100:.1f}%\n"
            f"- Position Size: {self.position_size_pct*100:.0f}% capital"
        )
