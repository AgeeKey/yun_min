# Creating a Custom Strategy

Learn how to create your own trading strategy for YunMin.

## Overview

YunMin supports custom strategies through a simple interface. You can create:

- Rule-based strategies (technical indicators)
- ML-based strategies (predictive models)
- Hybrid strategies (combining multiple approaches)

## Basic Strategy Template

```python
from typing import Dict, Optional
from yunmin.strategy.base import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    """
    My custom trading strategy.
    
    This strategy combines RSI and MACD indicators to generate signals.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize strategy.
        
        Args:
            config: Strategy configuration dictionary
        """
        super().__init__(config)
        self.rsi_period = config.get("rsi_period", 14)
        self.rsi_overbought = config.get("rsi_overbought", 70)
        self.rsi_oversold = config.get("rsi_oversold", 30)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal.
        
        Args:
            market_data: Current market data with OHLCV and indicators
            
        Returns:
            "BUY", "SELL", or None
        """
        # Get indicators
        rsi = market_data["indicators"]["rsi"]
        macd = market_data["indicators"]["macd"]
        macd_signal = market_data["indicators"]["macd_signal"]
        
        # Generate signal
        if rsi < self.rsi_oversold and macd > macd_signal:
            return "BUY"
        elif rsi > self.rsi_overbought and macd < macd_signal:
            return "SELL"
        
        return None
    
    def calculate_position_size(self, signal: str, market_data: Dict) -> float:
        """
        Calculate position size for the signal.
        
        Args:
            signal: Trading signal ("BUY" or "SELL")
            market_data: Current market data
            
        Returns:
            Position size as fraction of capital (0.0 to 1.0)
        """
        # Simple fixed sizing - 5% of capital
        return 0.05
```

## Register Your Strategy

Add to `yunmin/strategy/__init__.py`:

```python
from yunmin.strategy.my_custom_strategy import MyCustomStrategy

STRATEGIES = {
    "my_custom": MyCustomStrategy,
    # ... other strategies
}
```

## Configuration

Add strategy config to your YAML:

```yaml
strategy:
  name: my_custom
  rsi_period: 14
  rsi_overbought: 70
  rsi_oversold: 30
```

## Advanced: Using Machine Learning

```python
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from yunmin.strategy.base import BaseStrategy

class MLStrategy(BaseStrategy):
    """ML-based strategy using Random Forest."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        self.model = RandomForestClassifier()
        self.is_trained = False
    
    def train(self, historical_data: np.ndarray, labels: np.ndarray):
        """Train the model on historical data."""
        self.model.fit(historical_data, labels)
        self.is_trained = True
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """Generate signal using ML model."""
        if not self.is_trained:
            return None
        
        # Prepare features
        features = self._extract_features(market_data)
        
        # Predict
        prediction = self.model.predict([features])[0]
        
        if prediction == 1:
            return "BUY"
        elif prediction == -1:
            return "SELL"
        
        return None
    
    def _extract_features(self, market_data: Dict) -> np.ndarray:
        """Extract features from market data."""
        return np.array([
            market_data["indicators"]["rsi"],
            market_data["indicators"]["macd"],
            market_data["indicators"]["bb_width"],
            # Add more features
        ])
```

## Testing Your Strategy

```python
# tests/test_my_strategy.py
import pytest
from yunmin.strategy.my_custom_strategy import MyCustomStrategy

def test_strategy_buy_signal():
    """Test buy signal generation."""
    config = {"rsi_period": 14, "rsi_oversold": 30}
    strategy = MyCustomStrategy(config)
    
    market_data = {
        "indicators": {
            "rsi": 25,  # Oversold
            "macd": 0.5,
            "macd_signal": 0.3
        }
    }
    
    signal = strategy.generate_signal(market_data)
    assert signal == "BUY"
```

## Best Practices

1. **Start Simple**: Begin with basic indicators before adding complexity
2. **Backtest Thoroughly**: Test on historical data before live trading
3. **Risk Management**: Always implement proper stop-loss and position sizing
4. **Documentation**: Document your strategy's logic and parameters
5. **Version Control**: Track changes to your strategy over time

## Example: Integrating a New Indicator

```python
def add_custom_indicator(self, df):
    """
    Add a custom indicator to the dataframe.
    
    Example: Custom momentum indicator
    """
    df["custom_momentum"] = (
        df["close"].pct_change(10) * 100
    )
    return df
```

## Next Steps

- Review [AI Strategies](ai-strategies.md) for advanced examples
- Check [Architecture Overview](../architecture/overview.md) for system details
- Explore [Backtesting](backtesting.md) to test your strategy

---

**Happy Strategy Building! 📊**
