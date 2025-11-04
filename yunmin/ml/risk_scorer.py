"""
Risk Scoring Model - ML model for trade risk assessment.

This module implements a gradient boosting model (XGBoost/LightGBM)
that scores the risk of each trade based on position parameters and market conditions.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pickle

try:
    import xgboost as xgb
    import lightgbm as lgb
except ImportError:
    xgb = None
    lgb = None


@dataclass
class RiskScore:
    """Risk assessment for a trade."""
    score: float  # 0-100, higher = riskier
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'
    should_skip: bool  # True if risk is too high
    requires_higher_confidence: bool  # True if risk is elevated
    factors: Dict[str, float]  # Contributing risk factors
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'score': self.score,
            'risk_level': self.risk_level,
            'should_skip': self.should_skip,
            'requires_higher_confidence': self.requires_higher_confidence,
            'factors': self.factors,
            'timestamp': self.timestamp.isoformat()
        }


class RiskScorer:
    """
    ML-based risk scoring model for trading decisions.
    
    Uses gradient boosting (XGBoost or LightGBM) to predict trade risk
    based on position parameters and market conditions.
    """
    
    def __init__(
        self,
        model_type: str = 'xgboost',
        high_risk_threshold: float = 70.0,
        skip_threshold: float = 85.0
    ):
        """
        Initialize risk scorer.
        
        Args:
            model_type: 'xgboost' or 'lightgbm'
            high_risk_threshold: Score above which higher confidence is required
            skip_threshold: Score above which trade should be skipped
        """
        self.model_type = model_type
        self.high_risk_threshold = high_risk_threshold
        self.skip_threshold = skip_threshold
        
        self.model = None
        self.feature_names = None
        self.is_trained = False
        
        if model_type == 'xgboost' and xgb is None:
            raise ImportError("XGBoost not installed. Install with: pip install xgboost")
        if model_type == 'lightgbm' and lgb is None:
            raise ImportError("LightGBM not installed. Install with: pip install lightgbm")
    
    def _extract_features(
        self,
        position_size_pct: float,
        stop_loss_distance_pct: float,
        current_volatility: float,
        market_regime: str,
        time_since_last_trade_minutes: float,
        portfolio_drawdown_pct: float,
        current_price: float,
        atr: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        trend_strength: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Extract features for risk scoring.
        
        Args:
            position_size_pct: Position size as % of portfolio
            stop_loss_distance_pct: Stop loss distance as % from entry
            current_volatility: Current market volatility (ATR % or similar)
            market_regime: 'trending', 'ranging', or 'volatile'
            time_since_last_trade_minutes: Minutes since last trade
            portfolio_drawdown_pct: Current portfolio drawdown %
            current_price: Current asset price
            atr: Average True Range
            volume_ratio: Current volume vs average
            trend_strength: Strength of current trend (0-100)
            
        Returns:
            Dictionary of features
        """
        features = {
            'position_size_pct': position_size_pct,
            'stop_loss_distance_pct': stop_loss_distance_pct,
            'current_volatility': current_volatility,
            'time_since_last_trade_minutes': time_since_last_trade_minutes,
            'portfolio_drawdown_pct': portfolio_drawdown_pct,
            
            # Market regime encoding
            'regime_trending': 1.0 if market_regime == 'trending' else 0.0,
            'regime_ranging': 1.0 if market_regime == 'ranging' else 0.0,
            'regime_volatile': 1.0 if market_regime == 'volatile' else 0.0,
            
            # Derived features
            'risk_reward_ratio': stop_loss_distance_pct / max(position_size_pct, 0.01),
            'volatility_adjusted_position': position_size_pct * current_volatility,
            'drawdown_severity': max(0, portfolio_drawdown_pct) / 10.0,  # Normalize
            
            # Time-based risk
            'rapid_trading': 1.0 if time_since_last_trade_minutes < 30 else 0.0,
            'consecutive_trading': 1.0 if time_since_last_trade_minutes < 60 else 0.0,
        }
        
        # Optional features
        if atr is not None:
            features['atr'] = atr
            features['atr_pct'] = atr / current_price
        
        if volume_ratio is not None:
            features['volume_ratio'] = volume_ratio
            features['low_volume'] = 1.0 if volume_ratio < 0.5 else 0.0
            features['high_volume'] = 1.0 if volume_ratio > 1.5 else 0.0
        
        if trend_strength is not None:
            features['trend_strength'] = trend_strength
            features['weak_trend'] = 1.0 if trend_strength < 30 else 0.0
        
        return features
    
    def _create_training_labels(
        self,
        trade_outcomes: pd.DataFrame
    ) -> pd.Series:
        """
        Create training labels from trade outcomes.
        
        Args:
            trade_outcomes: DataFrame with 'pnl_pct' column
            
        Returns:
            Series with risk labels
        """
        labels = []
        
        for pnl_pct in trade_outcomes['pnl_pct']:
            if pnl_pct < -3.0:
                # High risk: significant loss
                labels.append(80)
            elif pnl_pct < -1.5:
                # Medium-high risk: moderate loss
                labels.append(60)
            elif pnl_pct < -0.5:
                # Medium risk: small loss
                labels.append(40)
            elif pnl_pct < 1.0:
                # Low-medium risk: small profit or breakeven
                labels.append(30)
            else:
                # Low risk: good profit
                labels.append(20)
        
        return pd.Series(labels)
    
    def train(
        self,
        historical_trades: pd.DataFrame,
        epochs: Optional[int] = None,
        verbose: bool = True
    ) -> Dict:
        """
        Train the risk scoring model.
        
        Args:
            historical_trades: DataFrame with trade data and outcomes
                Required columns: all feature columns + 'pnl_pct'
            epochs: Number of boosting rounds (None for auto)
            verbose: Whether to print training progress
            
        Returns:
            Training metrics
        """
        if 'pnl_pct' not in historical_trades.columns:
            raise ValueError("historical_trades must contain 'pnl_pct' column")
        
        # Extract features
        feature_data = []
        for _, row in historical_trades.iterrows():
            features = self._extract_features(
                position_size_pct=row.get('position_size_pct', 0),
                stop_loss_distance_pct=row.get('stop_loss_distance_pct', 0),
                current_volatility=row.get('current_volatility', 0),
                market_regime=row.get('market_regime', 'ranging'),
                time_since_last_trade_minutes=row.get('time_since_last_trade_minutes', 0),
                portfolio_drawdown_pct=row.get('portfolio_drawdown_pct', 0),
                current_price=row.get('current_price', 1),
                atr=row.get('atr'),
                volume_ratio=row.get('volume_ratio'),
                trend_strength=row.get('trend_strength')
            )
            feature_data.append(features)
        
        X = pd.DataFrame(feature_data)
        self.feature_names = list(X.columns)
        
        # Create labels
        y = self._create_training_labels(historical_trades)
        
        # Split data
        n_samples = len(X)
        n_train = int(n_samples * 0.8)
        
        X_train, X_val = X[:n_train], X[n_train:]
        y_train, y_val = y[:n_train], y[n_train:]
        
        # Train model
        if self.model_type == 'xgboost':
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 5,
                'learning_rate': 0.1,
                'n_estimators': epochs or 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            }
            
            self.model = xgb.XGBRegressor(**params)
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                verbose=verbose
            )
            
        else:  # lightgbm
            params = {
                'objective': 'regression',
                'max_depth': 5,
                'learning_rate': 0.1,
                'n_estimators': epochs or 100,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42,
                'verbose': -1 if not verbose else 1
            }
            
            self.model = lgb.LGBMRegressor(**params)
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric='rmse'
            )
        
        # Evaluate
        train_pred = self.model.predict(X_train)
        val_pred = self.model.predict(X_val)
        
        train_rmse = np.sqrt(np.mean((train_pred - y_train) ** 2))
        val_rmse = np.sqrt(np.mean((val_pred - y_val) ** 2))
        
        self.is_trained = True
        
        return {
            'train_rmse': float(train_rmse),
            'val_rmse': float(val_rmse),
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'feature_importance': self._get_feature_importance()
        }
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model."""
        if not self.is_trained:
            return {}
        
        if self.model_type == 'xgboost':
            importance = self.model.feature_importances_
        else:
            importance = self.model.feature_importances_
        
        return dict(zip(self.feature_names, importance.tolist()))
    
    def score_trade(
        self,
        position_size_pct: float,
        stop_loss_distance_pct: float,
        current_volatility: float,
        market_regime: str,
        time_since_last_trade_minutes: float = 0,
        portfolio_drawdown_pct: float = 0,
        current_price: float = 1.0,
        atr: Optional[float] = None,
        volume_ratio: Optional[float] = None,
        trend_strength: Optional[float] = None
    ) -> RiskScore:
        """
        Score the risk of a potential trade.
        
        Args:
            position_size_pct: Position size as % of portfolio
            stop_loss_distance_pct: Stop loss distance as % from entry
            current_volatility: Current market volatility
            market_regime: 'trending', 'ranging', or 'volatile'
            time_since_last_trade_minutes: Minutes since last trade
            portfolio_drawdown_pct: Current portfolio drawdown %
            current_price: Current asset price
            atr: Average True Range
            volume_ratio: Current volume vs average
            trend_strength: Strength of current trend
            
        Returns:
            RiskScore object
        """
        # Extract features
        features = self._extract_features(
            position_size_pct=position_size_pct,
            stop_loss_distance_pct=stop_loss_distance_pct,
            current_volatility=current_volatility,
            market_regime=market_regime,
            time_since_last_trade_minutes=time_since_last_trade_minutes,
            portfolio_drawdown_pct=portfolio_drawdown_pct,
            current_price=current_price,
            atr=atr,
            volume_ratio=volume_ratio,
            trend_strength=trend_strength
        )
        
        if self.is_trained and self.model is not None:
            # Use trained model
            # Ensure all feature_names exist in features, using 0 for missing optional features
            feature_dict = {fname: features.get(fname, 0.0) for fname in self.feature_names}
            X = pd.DataFrame([feature_dict])
            score = float(self.model.predict(X)[0])
        else:
            # Use heuristic scoring
            score = self._heuristic_score(features)
        
        # Ensure score is in 0-100 range
        score = float(np.clip(score, 0, 100))
        
        # Determine risk level
        if score < 30:
            risk_level = 'LOW'
        elif score < 50:
            risk_level = 'MEDIUM'
        elif score < 70:
            risk_level = 'HIGH'
        else:
            risk_level = 'VERY_HIGH'
        
        # Determine actions (convert to Python bool)
        should_skip = bool(score > self.skip_threshold)
        requires_higher_confidence = bool(score > self.high_risk_threshold)
        
        return RiskScore(
            score=score,
            risk_level=risk_level,
            should_skip=should_skip,
            requires_higher_confidence=requires_higher_confidence,
            factors=features,
            timestamp=datetime.now()
        )
    
    def _heuristic_score(self, features: Dict[str, float]) -> float:
        """
        Calculate risk score using heuristics when model is not trained.
        
        Args:
            features: Dictionary of features
            
        Returns:
            Risk score 0-100
        """
        score = 20.0  # Base score
        
        # Position size contribution
        pos_size = features['position_size_pct']
        if pos_size > 30:
            score += 25
        elif pos_size > 20:
            score += 15
        elif pos_size > 10:
            score += 5
        
        # Volatility contribution
        volatility = features['current_volatility']
        if volatility > 0.05:  # >5% volatility
            score += 20
        elif volatility > 0.03:
            score += 10
        
        # Stop loss contribution
        stop_loss = features['stop_loss_distance_pct']
        if stop_loss > 5:
            score += 15
        elif stop_loss > 3:
            score += 8
        
        # Drawdown contribution
        drawdown_severity = features['drawdown_severity']
        score += drawdown_severity * 2  # Up to 20 points
        
        # Rapid trading penalty
        if features['rapid_trading'] > 0:
            score += 10
        
        # Market regime
        if features['regime_volatile'] > 0:
            score += 15
        elif features['regime_ranging'] > 0:
            score += 5
        
        # Volume considerations
        if 'low_volume' in features and features['low_volume'] > 0:
            score += 8
        
        # Weak trend penalty
        if 'weak_trend' in features and features['weak_trend'] > 0:
            score += 7
        
        return score
    
    def evaluate_historical_performance(
        self,
        historical_trades: pd.DataFrame
    ) -> Dict:
        """
        Evaluate how well the risk scorer would have performed historically.
        
        Args:
            historical_trades: DataFrame with trades and outcomes
            
        Returns:
            Performance metrics
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before evaluation")
        
        scores = []
        outcomes = []
        
        for _, row in historical_trades.iterrows():
            risk_score = self.score_trade(
                position_size_pct=row.get('position_size_pct', 0),
                stop_loss_distance_pct=row.get('stop_loss_distance_pct', 0),
                current_volatility=row.get('current_volatility', 0),
                market_regime=row.get('market_regime', 'ranging'),
                time_since_last_trade_minutes=row.get('time_since_last_trade_minutes', 0),
                portfolio_drawdown_pct=row.get('portfolio_drawdown_pct', 0),
                current_price=row.get('current_price', 1),
                atr=row.get('atr'),
                volume_ratio=row.get('volume_ratio'),
                trend_strength=row.get('trend_strength')
            )
            
            scores.append(risk_score.score)
            outcomes.append(row['pnl_pct'])
        
        scores = np.array(scores)
        outcomes = np.array(outcomes)
        
        # Calculate metrics
        high_risk_mask = scores > self.high_risk_threshold
        low_risk_mask = scores <= self.high_risk_threshold
        
        high_risk_avg_pnl = np.mean(outcomes[high_risk_mask]) if high_risk_mask.any() else 0
        low_risk_avg_pnl = np.mean(outcomes[low_risk_mask]) if low_risk_mask.any() else 0
        
        # Correlation between risk score and negative outcomes
        losses_mask = outcomes < 0
        avg_score_for_losses = np.mean(scores[losses_mask]) if losses_mask.any() else 0
        avg_score_for_wins = np.mean(scores[~losses_mask]) if (~losses_mask).any() else 0
        
        return {
            'high_risk_avg_pnl': float(high_risk_avg_pnl),
            'low_risk_avg_pnl': float(low_risk_avg_pnl),
            'avg_score_for_losses': float(avg_score_for_losses),
            'avg_score_for_wins': float(avg_score_for_wins),
            'correlation': float(np.corrcoef(scores, outcomes)[0, 1]) if len(scores) > 1 else 0
        }
    
    def save_model(self, filepath: str):
        """
        Save model to disk.
        
        Args:
            filepath: Path to save the model
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        data = {
            'model': self.model,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'high_risk_threshold': self.high_risk_threshold,
            'skip_threshold': self.skip_threshold,
            'is_trained': self.is_trained
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
    
    def load_model(self, filepath: str):
        """
        Load model from disk.
        
        Args:
            filepath: Path to load the model from
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.model = data['model']
        self.model_type = data['model_type']
        self.feature_names = data['feature_names']
        self.high_risk_threshold = data['high_risk_threshold']
        self.skip_threshold = data['skip_threshold']
        self.is_trained = data['is_trained']
