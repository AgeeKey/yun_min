"""
Example: Using ML modules together for trading decisions

This example demonstrates how to use the LSTM Price Predictor,
Pattern Recognizer, and Risk Scorer together in a trading workflow.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from yunmin.ml import (
    LSTMPricePredictor,
    PatternRecognizer,
    RiskScorer
)


def generate_sample_data(n_candles=300):
    """Generate sample OHLCV data for demonstration."""
    np.random.seed(42)
    
    # Simulate realistic price movement
    base_price = 50000
    prices = [base_price]
    
    for i in range(n_candles - 1):
        # Random walk with slight upward bias
        change = np.random.randn() * 0.01 + 0.0001
        prices.append(prices[-1] * (1 + change))
    
    prices = np.array(prices)
    
    data = {
        'timestamp': [datetime.now() - timedelta(minutes=5*i) for i in range(n_candles, 0, -1)],
        'open': prices * (1 + np.random.randn(n_candles) * 0.002),
        'high': prices * (1 + np.abs(np.random.randn(n_candles)) * 0.005),
        'low': prices * (1 - np.abs(np.random.randn(n_candles)) * 0.005),
        'close': prices,
        'volume': np.random.rand(n_candles) * 1000 + 500
    }
    
    return pd.DataFrame(data)


def main():
    print("=" * 80)
    print("ML-Enhanced Trading Decision Example")
    print("=" * 80)
    
    # Generate sample data
    print("\n1. Generating sample OHLCV data...")
    df = generate_sample_data(n_candles=300)
    print(f"   Generated {len(df)} candles")
    print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    # Initialize LSTM Price Predictor
    print("\n2. Training LSTM Price Predictor...")
    lstm_predictor = LSTMPricePredictor(
        lookback_candles=50,
        lstm_units=[32, 16],
        dropout_rate=0.2
    )
    
    # Train on historical data
    train_result = lstm_predictor.train(
        df,
        epochs=10,
        batch_size=16,
        verbose=0
    )
    print(f"   Training complete!")
    print(f"   Test RMSE: {train_result['test_mae']:.4f}")
    print(f"   Train samples: {train_result['train_samples']}")
    
    # Make price prediction
    print("\n3. Generating price predictions...")
    prediction = lstm_predictor.predict(df)
    if prediction:
        current_price = df['close'].iloc[-1]
        print(f"   Current price: ${current_price:.2f}")
        print(f"   Predicted 1h:  ${prediction.prediction_1h:.2f} ({((prediction.prediction_1h/current_price-1)*100):+.2f}%)")
        print(f"   Predicted 2h:  ${prediction.prediction_2h:.2f} ({((prediction.prediction_2h/current_price-1)*100):+.2f}%)")
        print(f"   Predicted 4h:  ${prediction.prediction_4h:.2f} ({((prediction.prediction_4h/current_price-1)*100):+.2f}%)")
        print(f"   Confidence:    {prediction.confidence:.2%}")
    
    # Initialize Pattern Recognizer
    print("\n4. Detecting chart patterns...")
    pattern_recognizer = PatternRecognizer(
        lookback_window=100,
        min_pattern_length=10
    )
    
    # Detect patterns
    patterns = pattern_recognizer.detect_patterns(df)
    print(f"   Detected {len(patterns)} pattern(s)")
    
    for i, pattern in enumerate(patterns[:3], 1):  # Show top 3
        print(f"   {i}. {pattern.pattern_type.value}")
        print(f"      Sentiment: {pattern.sentiment.value}")
        print(f"      Reliability: {pattern.reliability_score:.2%}")
    
    # Generate pattern-based signal
    signal = pattern_recognizer.generate_signal(df, current_trend='uptrend')
    if signal:
        print(f"\n   Signal: {signal.action}")
        print(f"   Confidence: {signal.confidence:.2%}")
        print(f"   Reason: {signal.reason}")
    
    # Initialize Risk Scorer
    print("\n5. Assessing trade risk...")
    risk_scorer = RiskScorer(
        model_type='xgboost',
        high_risk_threshold=70.0,
        skip_threshold=85.0
    )
    
    # Calculate current volatility (ATR-based)
    price_changes = df['close'].pct_change().abs()
    current_volatility = price_changes.rolling(14).mean().iloc[-1]
    
    # Score a potential trade
    risk_score = risk_scorer.score_trade(
        position_size_pct=20.0,
        stop_loss_distance_pct=2.5,
        current_volatility=current_volatility,
        market_regime='trending',
        time_since_last_trade_minutes=60,
        portfolio_drawdown_pct=2.0,
        current_price=df['close'].iloc[-1],
        trend_strength=65
    )
    
    print(f"   Risk Score: {risk_score.score:.1f}/100")
    print(f"   Risk Level: {risk_score.risk_level}")
    print(f"   Should Skip: {risk_score.should_skip}")
    print(f"   Requires Higher Confidence: {risk_score.requires_higher_confidence}")
    
    # Make integrated decision
    print("\n6. Integrated Trading Decision")
    print("   " + "=" * 70)
    
    # Combine all signals
    price_signal = "BULLISH" if prediction and prediction.prediction_4h > current_price else "BEARISH"
    pattern_action = signal.action if signal else "HOLD"
    
    print(f"   Price Prediction Signal: {price_signal}")
    print(f"   Pattern Recognition Signal: {pattern_action}")
    print(f"   Risk Assessment: {risk_score.risk_level}")
    
    # Decision logic
    if risk_score.should_skip:
        decision = "❌ SKIP TRADE - Risk too high"
    elif pattern_action == "BUY" and price_signal == "BULLISH":
        if risk_score.requires_higher_confidence:
            decision = "⚠️  CONDITIONAL BUY - Require >80% AI confidence due to elevated risk"
        else:
            decision = "✅ STRONG BUY - All signals align, acceptable risk"
    elif pattern_action == "SELL" and price_signal == "BEARISH":
        if risk_score.requires_higher_confidence:
            decision = "⚠️  CONDITIONAL SELL - Require >80% AI confidence due to elevated risk"
        else:
            decision = "✅ STRONG SELL - All signals align, acceptable risk"
    else:
        decision = "⏸️  HOLD - Mixed signals"
    
    print(f"\n   Final Decision: {decision}")
    
    print("\n" + "=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
