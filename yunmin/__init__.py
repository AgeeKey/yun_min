"""
Yun Min AI Trading Agent

A modular cryptocurrency trading system with ML/AI capabilities.
"""

__version__ = "0.1.0"
__author__ = "Yun Min Team"

# Try to import core config, but don't fail if dependencies missing
try:
    from yunmin.core.config import load_config
    __all__ = ["__version__", "__author__", "load_config"]
except ImportError:
    # Allow module imports even if full dependencies not installed
    __all__ = ["__version__", "__author__"]
