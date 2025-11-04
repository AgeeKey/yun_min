"""
LSTM Price Predictor - Neural network for price prediction on 1-4 hour horizons.

This module implements a TensorFlow/Keras LSTM model that predicts BTC prices
for the next 1h, 2h, and 4h based on historical OHLCV data and technical indicators.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
import pickle
import os
from datetime import datetime

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
except ImportError:
    tf = None
    keras = None
    layers = None


@dataclass
class PricePrediction:
    """Price prediction result with confidence."""
    prediction_1h: float
    prediction_2h: float
    prediction_4h: float
    confidence: float  # 0.0 to 1.0
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'prediction_1h': self.prediction_1h,
            'prediction_2h': self.prediction_2h,
            'prediction_4h': self.prediction_4h,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


class LSTMPricePredictor:
    """
    LSTM-based price predictor for cryptocurrency prices.
    
    Uses 50 candles of OHLCV data + technical indicators to predict
    future prices at 1h, 2h, and 4h horizons.
    """
    
    def __init__(
        self,
        lookback_candles: int = 50,
        lstm_units: List[int] = [64, 32],
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001
    ):
        """
        Initialize LSTM predictor.
        
        Args:
            lookback_candles: Number of historical candles to use
            lstm_units: List of LSTM layer units
            dropout_rate: Dropout rate for regularization
            learning_rate: Learning rate for optimizer
        """
        if tf is None:
            raise ImportError("TensorFlow is required for LSTM predictor. Install with: pip install tensorflow")
        
        self.lookback_candles = lookback_candles
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model: Optional[keras.Model] = None
        self.scaler_x = None
        self.scaler_y = None
        self.feature_columns = None
        self.is_trained = False
        
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from OHLCV data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with engineered features
        """
        data = df.copy()
        
        # Normalized price changes
        data['price_change_pct'] = data['close'].pct_change()
        data['high_low_pct'] = (data['high'] - data['low']) / data['close']
        data['open_close_pct'] = (data['close'] - data['open']) / data['open']
        
        # RSI (Relative Strength Index)
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = data['close'].ewm(span=12, adjust=False).mean()
        exp2 = data['close'].ewm(span=26, adjust=False).mean()
        data['macd'] = exp1 - exp2
        data['macd_signal'] = data['macd'].ewm(span=9, adjust=False).mean()
        data['macd_diff'] = data['macd'] - data['macd_signal']
        
        # Bollinger Bands
        bb_period = 20
        data['bb_middle'] = data['close'].rolling(window=bb_period).mean()
        bb_std = data['close'].rolling(window=bb_period).std()
        data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
        data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
        data['bb_width'] = (data['bb_upper'] - data['bb_lower']) / data['bb_middle']
        data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
        
        # ATR (Average True Range)
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        data['atr'] = true_range.rolling(14).mean()
        data['atr_pct'] = data['atr'] / data['close']
        
        # Volume indicators
        data['volume_sma'] = data['volume'].rolling(window=20).mean()
        data['volume_ratio'] = data['volume'] / data['volume_sma']
        data['volume_change_pct'] = data['volume'].pct_change()
        
        # Time-based features (if timestamp available)
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data['hour'] = data['timestamp'].dt.hour
            data['day_of_week'] = data['timestamp'].dt.dayofweek
            # Cyclical encoding
            data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
            data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
            data['day_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
            data['day_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)
        
        # Moving averages
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['sma_50'] = data['close'].rolling(window=50).mean()
        data['sma_20_pct'] = (data['close'] - data['sma_20']) / data['sma_20']
        data['sma_50_pct'] = (data['close'] - data['sma_50']) / data['sma_50']
        
        return data
    
    def _prepare_sequences(
        self,
        df: pd.DataFrame,
        target_horizons: List[int] = [12, 24, 48]  # 1h, 2h, 4h in 5-min candles
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare sequences for LSTM training.
        
        Args:
            df: DataFrame with features
            target_horizons: Future candles to predict (for 5-min data)
            
        Returns:
            Tuple of (X, y) arrays
        """
        # Select feature columns
        feature_cols = [
            'open', 'high', 'low', 'close', 'volume',
            'price_change_pct', 'high_low_pct', 'open_close_pct',
            'rsi', 'macd', 'macd_signal', 'macd_diff',
            'bb_width', 'bb_position', 'atr_pct',
            'volume_ratio', 'volume_change_pct',
            'sma_20_pct', 'sma_50_pct'
        ]
        
        # Add time features if available
        if 'hour_sin' in df.columns:
            feature_cols.extend(['hour_sin', 'hour_cos', 'day_sin', 'day_cos'])
        
        # Filter columns that exist
        feature_cols = [col for col in feature_cols if col in df.columns]
        self.feature_columns = feature_cols
        
        # Ensure we have 'close' for targets (but not duplicated)
        cols_for_clean = feature_cols.copy()
        if 'close' not in cols_for_clean:
            cols_for_clean.append('close')
        
        # Drop NaN values
        df_clean = df[cols_for_clean].dropna()
        
        X_list = []
        y_list = []
        
        max_horizon = max(target_horizons)
        
        for i in range(len(df_clean) - self.lookback_candles - max_horizon):
            # Input sequence
            X_seq = df_clean[feature_cols].iloc[i:i + self.lookback_candles].values
            X_list.append(X_seq)
            
            # Target prices at different horizons
            # Use .values[0] if Series, otherwise use scalar
            current_price_val = df_clean['close'].iloc[i + self.lookback_candles - 1]
            current_price = float(current_price_val.values[0] if hasattr(current_price_val, 'values') else current_price_val)
            
            y_targets = []
            for horizon in target_horizons:
                future_price_val = df_clean['close'].iloc[i + self.lookback_candles + horizon - 1]
                future_price = float(future_price_val.values[0] if hasattr(future_price_val, 'values') else future_price_val)
                # Predict percentage change instead of absolute price
                y_targets.append((future_price - current_price) / current_price)
            
            y_list.append(y_targets)
        
        return np.array(X_list), np.array(y_list)
    
    def _normalize_data(self, X: np.ndarray, y: np.ndarray, fit: bool = True):
        """
        Normalize input and output data.
        
        Args:
            X: Input sequences
            y: Target values
            fit: Whether to fit the scalers
            
        Returns:
            Normalized X and y
        """
        from sklearn.preprocessing import StandardScaler
        
        # Reshape X for scaling
        n_samples, n_timesteps, n_features = X.shape
        X_reshaped = X.reshape(-1, n_features)
        
        if fit:
            self.scaler_x = StandardScaler()
            X_scaled = self.scaler_x.fit_transform(X_reshaped)
            
            self.scaler_y = StandardScaler()
            y_scaled = self.scaler_y.fit_transform(y)
        else:
            X_scaled = self.scaler_x.transform(X_reshaped)
            y_scaled = self.scaler_y.transform(y)
        
        # Reshape back
        X_scaled = X_scaled.reshape(n_samples, n_timesteps, n_features)
        
        return X_scaled, y_scaled
    
    def _build_model(self, input_shape: Tuple[int, int], output_dim: int):
        """
        Build LSTM model architecture.
        
        Args:
            input_shape: (timesteps, features)
            output_dim: Number of outputs (3 for 1h, 2h, 4h)
        """
        model = keras.Sequential()
        
        # First LSTM layer
        model.add(layers.LSTM(
            self.lstm_units[0],
            return_sequences=True if len(self.lstm_units) > 1 else False,
            input_shape=input_shape
        ))
        model.add(layers.Dropout(self.dropout_rate))
        
        # Additional LSTM layers
        for i in range(1, len(self.lstm_units)):
            return_seq = i < len(self.lstm_units) - 1
            model.add(layers.LSTM(self.lstm_units[i], return_sequences=return_seq))
            model.add(layers.Dropout(self.dropout_rate))
        
        # Dense layers
        model.add(layers.Dense(32, activation='relu'))
        model.add(layers.Dropout(self.dropout_rate))
        model.add(layers.Dense(16, activation='relu'))
        model.add(layers.Dense(output_dim))
        
        # Compile
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        self.model = model
    
    def train(
        self,
        df: pd.DataFrame,
        epochs: int = 100,
        batch_size: int = 32,
        validation_split: float = 0.15,
        verbose: int = 1
    ) -> Dict:
        """
        Train the LSTM model.
        
        Args:
            df: DataFrame with OHLCV data
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Validation data split ratio
            verbose: Verbosity level
            
        Returns:
            Training history
        """
        # Feature engineering
        df_features = self._engineer_features(df)
        
        # Prepare sequences
        X, y = self._prepare_sequences(df_features)
        
        if len(X) == 0:
            raise ValueError("Not enough data to create sequences")
        
        # Split into train/validation/test (70/15/15)
        n_samples = len(X)
        n_train = int(n_samples * 0.70)
        n_val = int(n_samples * 0.15)
        
        X_train = X[:n_train]
        y_train = y[:n_train]
        X_val = X[n_train:n_train + n_val]
        y_val = y[n_train:n_train + n_val]
        X_test = X[n_train + n_val:]
        y_test = y[n_train + n_val:]
        
        # Normalize
        X_train_scaled, y_train_scaled = self._normalize_data(X_train, y_train, fit=True)
        X_val_scaled, y_val_scaled = self._normalize_data(X_val, y_val, fit=False)
        X_test_scaled, y_test_scaled = self._normalize_data(X_test, y_test, fit=False)
        
        # Build model
        input_shape = (X_train_scaled.shape[1], X_train_scaled.shape[2])
        output_dim = y_train_scaled.shape[1]
        self._build_model(input_shape, output_dim)
        
        # Callbacks
        early_stop = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        reduce_lr = ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6
        )
        
        # Train
        history = self.model.fit(
            X_train_scaled, y_train_scaled,
            validation_data=(X_val_scaled, y_val_scaled),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop, reduce_lr],
            verbose=verbose
        )
        
        # Evaluate on test set
        test_loss, test_mae = self.model.evaluate(X_test_scaled, y_test_scaled, verbose=0)
        
        self.is_trained = True
        
        return {
            'history': history.history,
            'test_loss': float(test_loss),
            'test_mae': float(test_mae),
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'test_samples': len(X_test)
        }
    
    def predict(self, df: pd.DataFrame) -> Optional[PricePrediction]:
        """
        Predict future prices.
        
        Args:
            df: DataFrame with recent OHLCV data (at least lookback_candles rows)
            
        Returns:
            PricePrediction object or None if prediction fails
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model must be trained before prediction")
        
        # Feature engineering
        df_features = self._engineer_features(df)
        
        # Get last sequence
        if len(df_features) < self.lookback_candles:
            return None
        
        # Extract features
        last_sequence = df_features[self.feature_columns].iloc[-self.lookback_candles:].values
        
        # Check for NaN
        if np.isnan(last_sequence).any():
            return None
        
        # Reshape for model
        X_pred = last_sequence.reshape(1, self.lookback_candles, len(self.feature_columns))
        
        # Normalize
        X_pred_flat = X_pred.reshape(-1, len(self.feature_columns))
        X_pred_scaled = self.scaler_x.transform(X_pred_flat)
        X_pred_scaled = X_pred_scaled.reshape(1, self.lookback_candles, len(self.feature_columns))
        
        # Predict
        y_pred_scaled = self.model.predict(X_pred_scaled, verbose=0)
        y_pred = self.scaler_y.inverse_transform(y_pred_scaled)[0]
        
        # Convert percentage changes back to prices
        current_price = df['close'].iloc[-1]
        pred_1h = current_price * (1 + y_pred[0])
        pred_2h = current_price * (1 + y_pred[1])
        pred_4h = current_price * (1 + y_pred[2])
        
        # Calculate confidence based on prediction variance
        # Lower variance = higher confidence
        pred_variance = np.var(y_pred)
        confidence = 1.0 / (1.0 + pred_variance * 100)  # Scaled confidence
        confidence = np.clip(confidence, 0.0, 1.0)
        
        return PricePrediction(
            prediction_1h=float(pred_1h),
            prediction_2h=float(pred_2h),
            prediction_4h=float(pred_4h),
            confidence=float(confidence),
            timestamp=datetime.now()
        )
    
    def save_model(self, filepath: str):
        """
        Save model to disk.
        
        Args:
            filepath: Path to save the model
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        # Save Keras model (use .keras format instead of .h5)
        model_path = filepath + '_model.keras'
        self.model.save(model_path)
        
        # Save scalers and metadata
        metadata = {
            'scaler_x': self.scaler_x,
            'scaler_y': self.scaler_y,
            'feature_columns': self.feature_columns,
            'lookback_candles': self.lookback_candles,
            'lstm_units': self.lstm_units,
            'dropout_rate': self.dropout_rate,
            'learning_rate': self.learning_rate,
            'is_trained': self.is_trained
        }
        
        metadata_path = filepath + '_metadata.pkl'
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
    
    def load_model(self, filepath: str):
        """
        Load model from disk.
        
        Args:
            filepath: Path to load the model from
        """
        # Load Keras model (try .keras first, fallback to .h5 for compatibility)
        model_path_keras = filepath + '_model.keras'
        model_path_h5 = filepath + '_model.h5'
        
        if os.path.exists(model_path_keras):
            self.model = keras.models.load_model(model_path_keras)
        elif os.path.exists(model_path_h5):
            self.model = keras.models.load_model(model_path_h5)
        else:
            raise FileNotFoundError(f"Model file not found at {filepath}")
        
        # Load metadata
        metadata_path = filepath + '_metadata.pkl'
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        self.scaler_x = metadata['scaler_x']
        self.scaler_y = metadata['scaler_y']
        self.feature_columns = metadata['feature_columns']
        self.lookback_candles = metadata['lookback_candles']
        self.lstm_units = metadata['lstm_units']
        self.dropout_rate = metadata['dropout_rate']
        self.learning_rate = metadata['learning_rate']
        self.is_trained = metadata['is_trained']
