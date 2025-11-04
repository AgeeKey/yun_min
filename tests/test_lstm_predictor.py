"""
Tests for LSTM Price Predictor
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile

from yunmin.ml.lstm_predictor import LSTMPricePredictor, PricePrediction


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    n_samples = 200
    
    # Generate realistic price data
    base_price = 50000
    prices = [base_price]
    
    for i in range(n_samples - 1):
        change = np.random.randn() * 0.01  # 1% volatility
        prices.append(prices[-1] * (1 + change))
    
    prices = np.array(prices)
    
    # Generate OHLCV
    data = {
        'timestamp': [datetime.now() - timedelta(minutes=5*i) for i in range(n_samples, 0, -1)],
        'open': prices * (1 + np.random.randn(n_samples) * 0.002),
        'high': prices * (1 + np.abs(np.random.randn(n_samples)) * 0.005),
        'low': prices * (1 - np.abs(np.random.randn(n_samples)) * 0.005),
        'close': prices,
        'volume': np.random.rand(n_samples) * 1000 + 500
    }
    
    return pd.DataFrame(data)


def test_lstm_predictor_initialization():
    """Test LSTM predictor initialization."""
    predictor = LSTMPricePredictor(
        lookback_candles=50,
        lstm_units=[64, 32],
        dropout_rate=0.2
    )
    
    assert predictor.lookback_candles == 50
    assert predictor.lstm_units == [64, 32]
    assert predictor.dropout_rate == 0.2
    assert not predictor.is_trained


def test_feature_engineering(sample_ohlcv_data):
    """Test feature engineering."""
    predictor = LSTMPricePredictor()
    df_features = predictor._engineer_features(sample_ohlcv_data)
    
    # Check that features are created
    assert 'rsi' in df_features.columns
    assert 'macd' in df_features.columns
    assert 'bb_width' in df_features.columns
    assert 'atr_pct' in df_features.columns
    assert 'volume_ratio' in df_features.columns
    
    # Check for time-based features
    assert 'hour_sin' in df_features.columns
    assert 'hour_cos' in df_features.columns


def test_prepare_sequences(sample_ohlcv_data):
    """Test sequence preparation."""
    predictor = LSTMPricePredictor(lookback_candles=30)
    df_features = predictor._engineer_features(sample_ohlcv_data)
    
    X, y = predictor._prepare_sequences(df_features, target_horizons=[12, 24, 48])
    
    # Check shapes
    assert len(X.shape) == 3  # (samples, timesteps, features)
    assert X.shape[1] == 30  # lookback_candles
    assert len(y.shape) == 2  # (samples, outputs)
    assert y.shape[1] == 3  # 3 prediction horizons
    
    # Check that we have valid data
    assert X.shape[0] > 0
    assert not np.isnan(X).all()


def test_train_lstm_predictor(sample_ohlcv_data):
    """Test LSTM predictor training."""
    predictor = LSTMPricePredictor(
        lookback_candles=30,
        lstm_units=[32, 16],
        dropout_rate=0.2
    )
    
    # Train with small epochs for testing
    history = predictor.train(
        sample_ohlcv_data,
        epochs=5,
        batch_size=16,
        verbose=0
    )
    
    assert predictor.is_trained
    assert 'history' in history
    assert 'test_loss' in history
    assert 'test_mae' in history
    assert history['train_samples'] > 0
    assert history['val_samples'] > 0


def test_predict_without_training(sample_ohlcv_data):
    """Test that prediction without training raises error."""
    predictor = LSTMPricePredictor()
    
    with pytest.raises(ValueError, match="Model must be trained"):
        predictor.predict(sample_ohlcv_data)


def test_predict_with_training(sample_ohlcv_data):
    """Test prediction after training."""
    predictor = LSTMPricePredictor(
        lookback_candles=30,
        lstm_units=[32],
        dropout_rate=0.1
    )
    
    # Train
    predictor.train(sample_ohlcv_data, epochs=3, verbose=0)
    
    # Predict
    prediction = predictor.predict(sample_ohlcv_data)
    
    assert prediction is not None
    assert isinstance(prediction, PricePrediction)
    assert prediction.prediction_1h > 0
    assert prediction.prediction_2h > 0
    assert prediction.prediction_4h > 0
    assert 0 <= prediction.confidence <= 1.0


def test_predict_insufficient_data():
    """Test prediction with insufficient data."""
    predictor = LSTMPricePredictor(lookback_candles=50)
    
    # Create small dataset
    small_data = pd.DataFrame({
        'open': [1, 2, 3],
        'high': [1.1, 2.1, 3.1],
        'low': [0.9, 1.9, 2.9],
        'close': [1, 2, 3],
        'volume': [100, 200, 300]
    })
    
    # Train on larger dataset first
    np.random.seed(42)
    large_data = pd.DataFrame({
        'open': np.random.rand(200) * 100,
        'high': np.random.rand(200) * 100 + 1,
        'low': np.random.rand(200) * 100 - 1,
        'close': np.random.rand(200) * 100,
        'volume': np.random.rand(200) * 1000
    })
    
    predictor.train(large_data, epochs=2, verbose=0)
    
    # Predict on small data should return None
    prediction = predictor.predict(small_data)
    assert prediction is None


def test_save_and_load_model(sample_ohlcv_data):
    """Test model saving and loading."""
    predictor = LSTMPricePredictor(lookback_candles=30, lstm_units=[32])
    
    # Train
    predictor.train(sample_ohlcv_data, epochs=3, verbose=0)
    
    # Get prediction before saving
    pred_before = predictor.predict(sample_ohlcv_data)
    
    # Save
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_model')
        predictor.save_model(filepath)
        
        # Load into new predictor
        predictor2 = LSTMPricePredictor()
        predictor2.load_model(filepath)
        
        assert predictor2.is_trained
        assert predictor2.lookback_candles == predictor.lookback_candles
        
        # Get prediction after loading
        pred_after = predictor2.predict(sample_ohlcv_data)
        
        # Predictions should be very close
        assert abs(pred_before.prediction_1h - pred_after.prediction_1h) < 100


def test_price_prediction_to_dict():
    """Test PricePrediction to_dict method."""
    prediction = PricePrediction(
        prediction_1h=50100.0,
        prediction_2h=50200.0,
        prediction_4h=50300.0,
        confidence=0.75,
        timestamp=datetime.now()
    )
    
    result = prediction.to_dict()
    
    assert result['prediction_1h'] == 50100.0
    assert result['prediction_2h'] == 50200.0
    assert result['prediction_4h'] == 50300.0
    assert result['confidence'] == 0.75
    assert 'timestamp' in result


def test_normalization(sample_ohlcv_data):
    """Test data normalization."""
    predictor = LSTMPricePredictor(lookback_candles=30)
    df_features = predictor._engineer_features(sample_ohlcv_data)
    X, y = predictor._prepare_sequences(df_features)
    
    # Normalize
    X_scaled, y_scaled = predictor._normalize_data(X, y, fit=True)
    
    # Check that scalers are fitted
    assert predictor.scaler_x is not None
    assert predictor.scaler_y is not None
    
    # Check that data is normalized (mean ~0, std ~1)
    X_flat = X_scaled.reshape(-1, X_scaled.shape[-1])
    assert abs(np.mean(X_flat)) < 0.5  # Should be close to 0
    
    # Test inverse transform
    X_scaled2, y_scaled2 = predictor._normalize_data(X[:10], y[:10], fit=False)
    assert X_scaled2.shape == (10, X.shape[1], X.shape[2])


def test_model_architecture():
    """Test LSTM model architecture building."""
    predictor = LSTMPricePredictor(
        lookback_candles=50,
        lstm_units=[64, 32],
        dropout_rate=0.2
    )
    
    # Build model
    predictor._build_model(input_shape=(50, 20), output_dim=3)
    
    assert predictor.model is not None
    
    # Check input and output shapes
    assert predictor.model.input_shape == (None, 50, 20)
    assert predictor.model.output_shape == (None, 3)


def test_multiple_predictions(sample_ohlcv_data):
    """Test multiple predictions in sequence."""
    predictor = LSTMPricePredictor(lookback_candles=30, lstm_units=[32])
    predictor.train(sample_ohlcv_data, epochs=3, verbose=0)
    
    predictions = []
    for i in range(3):
        pred = predictor.predict(sample_ohlcv_data.iloc[:-i] if i > 0 else sample_ohlcv_data)
        if pred:
            predictions.append(pred)
    
    # Should get at least some predictions
    assert len(predictions) > 0
    
    # All predictions should have valid structure
    for pred in predictions:
        assert pred.prediction_1h > 0
        assert 0 <= pred.confidence <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
