"""
Tests for Risk Scoring Model
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
import os
import tempfile

from yunmin.ml.risk_scorer import RiskScorer, RiskScore


@pytest.fixture
def sample_trade_data():
    """Generate sample trade data for testing."""
    np.random.seed(42)
    n_trades = 100
    
    data = {
        'position_size_pct': np.random.uniform(5, 30, n_trades),
        'stop_loss_distance_pct': np.random.uniform(1, 5, n_trades),
        'current_volatility': np.random.uniform(0.01, 0.08, n_trades),
        'market_regime': np.random.choice(['trending', 'ranging', 'volatile'], n_trades),
        'time_since_last_trade_minutes': np.random.uniform(0, 240, n_trades),
        'portfolio_drawdown_pct': np.random.uniform(0, 15, n_trades),
        'current_price': np.random.uniform(45000, 55000, n_trades),
        'atr': np.random.uniform(500, 2000, n_trades),
        'volume_ratio': np.random.uniform(0.3, 2.0, n_trades),
        'trend_strength': np.random.uniform(0, 100, n_trades),
        'pnl_pct': np.random.randn(n_trades) * 2  # Random P&L
    }
    
    return pd.DataFrame(data)


def test_risk_scorer_initialization_xgboost():
    """Test risk scorer initialization with XGBoost."""
    scorer = RiskScorer(
        model_type='xgboost',
        high_risk_threshold=70.0,
        skip_threshold=85.0
    )
    
    assert scorer.model_type == 'xgboost'
    assert scorer.high_risk_threshold == 70.0
    assert scorer.skip_threshold == 85.0
    assert not scorer.is_trained


def test_risk_scorer_initialization_lightgbm():
    """Test risk scorer initialization with LightGBM."""
    scorer = RiskScorer(
        model_type='lightgbm',
        high_risk_threshold=75.0,
        skip_threshold=90.0
    )
    
    assert scorer.model_type == 'lightgbm'
    assert scorer.high_risk_threshold == 75.0
    assert scorer.skip_threshold == 90.0


def test_extract_features():
    """Test feature extraction."""
    scorer = RiskScorer()
    
    features = scorer._extract_features(
        position_size_pct=20.0,
        stop_loss_distance_pct=2.5,
        current_volatility=0.04,
        market_regime='trending',
        time_since_last_trade_minutes=60,
        portfolio_drawdown_pct=5.0,
        current_price=50000,
        atr=1000,
        volume_ratio=1.2,
        trend_strength=75
    )
    
    # Check basic features
    assert features['position_size_pct'] == 20.0
    assert features['stop_loss_distance_pct'] == 2.5
    assert features['current_volatility'] == 0.04
    
    # Check regime encoding
    assert features['regime_trending'] == 1.0
    assert features['regime_ranging'] == 0.0
    assert features['regime_volatile'] == 0.0
    
    # Check derived features
    assert 'risk_reward_ratio' in features
    assert 'volatility_adjusted_position' in features
    assert 'drawdown_severity' in features
    
    # Check optional features
    assert features['atr'] == 1000
    assert features['volume_ratio'] == 1.2
    assert features['trend_strength'] == 75


def test_extract_features_minimal():
    """Test feature extraction with minimal parameters."""
    scorer = RiskScorer()
    
    features = scorer._extract_features(
        position_size_pct=15.0,
        stop_loss_distance_pct=3.0,
        current_volatility=0.03,
        market_regime='ranging',
        time_since_last_trade_minutes=120,
        portfolio_drawdown_pct=2.0,
        current_price=50000
    )
    
    # Should work without optional parameters
    assert 'position_size_pct' in features
    assert 'regime_ranging' in features
    assert features['regime_ranging'] == 1.0


def test_create_training_labels():
    """Test creation of training labels."""
    scorer = RiskScorer()
    
    trade_outcomes = pd.DataFrame({
        'pnl_pct': [-5.0, -2.0, -0.8, 0.5, 2.0]
    })
    
    labels = scorer._create_training_labels(trade_outcomes)
    
    assert len(labels) == 5
    assert all(0 <= label <= 100 for label in labels)
    
    # Larger losses should have higher risk scores
    assert labels.iloc[0] > labels.iloc[1]  # -5% worse than -2%
    assert labels.iloc[1] > labels.iloc[4]  # -2% worse than +2%


def test_train_xgboost(sample_trade_data):
    """Test training with XGBoost."""
    scorer = RiskScorer(model_type='xgboost')
    
    result = scorer.train(
        sample_trade_data,
        epochs=10,
        verbose=False
    )
    
    assert scorer.is_trained
    assert 'train_rmse' in result
    assert 'val_rmse' in result
    assert 'train_samples' in result
    assert 'val_samples' in result
    assert 'feature_importance' in result
    
    # Check feature importance
    assert len(result['feature_importance']) > 0


def test_train_lightgbm(sample_trade_data):
    """Test training with LightGBM."""
    scorer = RiskScorer(model_type='lightgbm')
    
    result = scorer.train(
        sample_trade_data,
        epochs=10,
        verbose=False
    )
    
    assert scorer.is_trained
    assert 'train_rmse' in result
    assert 'val_rmse' in result


def test_score_trade_without_training():
    """Test scoring without training (should use heuristics)."""
    scorer = RiskScorer()
    
    risk_score = scorer.score_trade(
        position_size_pct=25.0,
        stop_loss_distance_pct=4.0,
        current_volatility=0.06,
        market_regime='volatile',
        time_since_last_trade_minutes=15,
        portfolio_drawdown_pct=8.0
    )
    
    assert isinstance(risk_score, RiskScore)
    assert 0 <= risk_score.score <= 100
    assert risk_score.risk_level in ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH']
    assert isinstance(risk_score.should_skip, bool)
    assert isinstance(risk_score.requires_higher_confidence, bool)


def test_score_trade_with_training(sample_trade_data):
    """Test scoring after training."""
    scorer = RiskScorer(model_type='xgboost')
    scorer.train(sample_trade_data, epochs=5, verbose=False)
    
    risk_score = scorer.score_trade(
        position_size_pct=20.0,
        stop_loss_distance_pct=3.0,
        current_volatility=0.04,
        market_regime='trending',
        time_since_last_trade_minutes=60,
        portfolio_drawdown_pct=3.0,
        current_price=50000,
        atr=1000,
        volume_ratio=1.1,
        trend_strength=70
    )
    
    assert isinstance(risk_score, RiskScore)
    assert 0 <= risk_score.score <= 100


def test_risk_score_levels():
    """Test risk score level assignment."""
    scorer = RiskScorer()
    
    # Low risk scenario
    risk_low = scorer.score_trade(
        position_size_pct=5.0,
        stop_loss_distance_pct=1.5,
        current_volatility=0.02,
        market_regime='trending',
        time_since_last_trade_minutes=120,
        portfolio_drawdown_pct=0.0
    )
    
    # High risk scenario
    risk_high = scorer.score_trade(
        position_size_pct=35.0,
        stop_loss_distance_pct=6.0,
        current_volatility=0.08,
        market_regime='volatile',
        time_since_last_trade_minutes=5,
        portfolio_drawdown_pct=12.0
    )
    
    # High risk should have higher score
    assert risk_high.score > risk_low.score


def test_heuristic_scoring():
    """Test heuristic-based scoring."""
    scorer = RiskScorer()
    
    features = {
        'position_size_pct': 25.0,
        'current_volatility': 0.05,
        'stop_loss_distance_pct': 4.0,
        'drawdown_severity': 0.8,
        'rapid_trading': 1.0,
        'regime_volatile': 1.0,
        'regime_ranging': 0.0,
        'regime_trending': 0.0,
        'low_volume': 0.0,
        'weak_trend': 0.0
    }
    
    score = scorer._heuristic_score(features)
    
    assert isinstance(score, float)
    assert score > 0  # Should be elevated due to high risk factors


def test_risk_thresholds():
    """Test risk threshold logic."""
    scorer = RiskScorer(
        high_risk_threshold=60.0,
        skip_threshold=80.0
    )
    
    # Create a high-risk trade
    risk_score = scorer.score_trade(
        position_size_pct=30.0,
        stop_loss_distance_pct=5.0,
        current_volatility=0.07,
        market_regime='volatile',
        time_since_last_trade_minutes=10,
        portfolio_drawdown_pct=10.0
    )
    
    # Check threshold logic
    if risk_score.score > 80:
        assert risk_score.should_skip
        assert risk_score.requires_higher_confidence
    elif risk_score.score > 60:
        assert not risk_score.should_skip
        assert risk_score.requires_higher_confidence
    else:
        assert not risk_score.should_skip
        assert not risk_score.requires_higher_confidence


def test_evaluate_historical_performance(sample_trade_data):
    """Test evaluation of historical performance."""
    scorer = RiskScorer(model_type='xgboost')
    scorer.train(sample_trade_data[:80], epochs=5, verbose=False)
    
    # Evaluate on the remaining data
    performance = scorer.evaluate_historical_performance(sample_trade_data[80:])
    
    assert 'high_risk_avg_pnl' in performance
    assert 'low_risk_avg_pnl' in performance
    assert 'avg_score_for_losses' in performance
    assert 'avg_score_for_wins' in performance
    assert 'correlation' in performance


def test_save_and_load_model_xgboost(sample_trade_data):
    """Test saving and loading XGBoost model."""
    scorer = RiskScorer(model_type='xgboost')
    scorer.train(sample_trade_data, epochs=5, verbose=False)
    
    # Score before saving
    score_before = scorer.score_trade(
        position_size_pct=20.0,
        stop_loss_distance_pct=3.0,
        current_volatility=0.04,
        market_regime='trending',
        time_since_last_trade_minutes=60,
        portfolio_drawdown_pct=3.0,
        current_price=50000
    )
    
    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_scorer.pkl')
        scorer.save_model(filepath)
        
        scorer2 = RiskScorer(model_type='xgboost')
        scorer2.load_model(filepath)
        
        assert scorer2.is_trained
        assert scorer2.model_type == 'xgboost'
        
        # Score after loading
        score_after = scorer2.score_trade(
            position_size_pct=20.0,
            stop_loss_distance_pct=3.0,
            current_volatility=0.04,
            market_regime='trending',
            time_since_last_trade_minutes=60,
            portfolio_drawdown_pct=3.0,
            current_price=50000
        )
        
        # Scores should be very close
        assert abs(score_before.score - score_after.score) < 1.0


def test_save_and_load_model_lightgbm(sample_trade_data):
    """Test saving and loading LightGBM model."""
    scorer = RiskScorer(model_type='lightgbm')
    scorer.train(sample_trade_data, epochs=5, verbose=False)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test_scorer_lgb.pkl')
        scorer.save_model(filepath)
        
        scorer2 = RiskScorer(model_type='lightgbm')
        scorer2.load_model(filepath)
        
        assert scorer2.is_trained
        assert scorer2.model_type == 'lightgbm'


def test_risk_score_to_dict():
    """Test RiskScore to_dict method."""
    risk_score = RiskScore(
        score=65.0,
        risk_level='HIGH',
        should_skip=False,
        requires_higher_confidence=True,
        factors={'position_size_pct': 20.0, 'volatility': 0.04},
        timestamp=datetime.now()
    )
    
    result = risk_score.to_dict()
    
    assert result['score'] == 65.0
    assert result['risk_level'] == 'HIGH'
    assert result['should_skip'] is False
    assert result['requires_higher_confidence'] is True
    assert 'factors' in result
    assert 'timestamp' in result


def test_multiple_regime_types():
    """Test scoring with different market regimes."""
    scorer = RiskScorer()
    
    regimes = ['trending', 'ranging', 'volatile']
    scores = []
    
    for regime in regimes:
        risk_score = scorer.score_trade(
            position_size_pct=20.0,
            stop_loss_distance_pct=3.0,
            current_volatility=0.04,
            market_regime=regime,
            time_since_last_trade_minutes=60,
            portfolio_drawdown_pct=3.0
        )
        scores.append(risk_score.score)
    
    # Volatile regime should generally have higher risk
    volatile_idx = regimes.index('volatile')
    assert scores[volatile_idx] > min(scores)


def test_feature_importance(sample_trade_data):
    """Test feature importance extraction."""
    scorer = RiskScorer(model_type='xgboost')
    result = scorer.train(sample_trade_data, epochs=5, verbose=False)
    
    importance = result['feature_importance']
    
    assert len(importance) > 0
    assert all(isinstance(v, float) for v in importance.values())
    
    # Check that known important features are present
    assert 'position_size_pct' in importance
    assert 'current_volatility' in importance


def test_training_without_pnl_column():
    """Test that training fails without pnl_pct column."""
    scorer = RiskScorer()
    
    bad_data = pd.DataFrame({
        'position_size_pct': [10, 20, 30],
        'stop_loss_distance_pct': [2, 3, 4]
    })
    
    with pytest.raises(ValueError, match="must contain 'pnl_pct'"):
        scorer.train(bad_data)


def test_save_untrained_model():
    """Test that saving untrained model raises error."""
    scorer = RiskScorer()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = os.path.join(tmpdir, 'test.pkl')
        with pytest.raises(ValueError, match="Cannot save untrained model"):
            scorer.save_model(filepath)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
