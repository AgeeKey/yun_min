"""Strategy module initialization."""

from yunmin.strategy.base import BaseStrategy, Signal
from yunmin.strategy.ema_crossover import EMACrossoverStrategy

__all__ = ["BaseStrategy", "Signal", "EMACrossoverStrategy"]
