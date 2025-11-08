"""
Tests for Reasoning Module - Chain of Thought, Ensemble, Confidence
"""

import pytest
from yunmin.reasoning.chain_of_thought import ChainOfThoughtReasoning
from yunmin.reasoning.ensemble import EnsembleDecisionMaker
from yunmin.reasoning.confidence import ConfidenceCalibrator


class TestChainOfThoughtReasoning:
    """Test Chain of Thought Reasoning."""
    
    def test_initialization(self):
        """Test reasoning initialization."""
        reasoning = ChainOfThoughtReasoning()
        assert reasoning is not None
    
    def test_reason(self):
        """Test complete reasoning chain."""
        reasoning = ChainOfThoughtReasoning()
        
        market_context = {
            'price': 50000.0,
            'indicators': {
                'rsi': 45,
                'ema_fast': 50100,
                'ema_slow': 49900,
                'macd': 50,
                'volume_ratio': 1.2
            },
            'trend': 'bullish',
            'volatility': 0.02
        }
        
        analyst_output = {
            'decision': 'BUY',
            'confidence': 0.75,
            'reasoning_chain': {
                'regime': 'trending_up'
            }
        }
        
        risk_assessment = {
            'risk_score': 75,
            'approved': True
        }
        
        result = reasoning.reason(market_context, analyst_output, risk_assessment)
        
        assert 'steps' in result
        assert len(result['steps']) > 0
        assert 'final_decision' in result
        assert result['final_decision'] in ['BUY', 'SELL', 'HOLD']
        assert 'confidence' in result
    
    def test_observation_step(self):
        """Test observation step."""
        reasoning = ChainOfThoughtReasoning()
        
        context = {
            'price': 50000.0,
            'trend': 'bullish',
            'indicators': {
                'rsi': 45,
                'volume_ratio': 1.2
            },
            'volatility': 0.02
        }
        
        observation = reasoning._step_observe(context)
        
        assert observation['step'] == 1
        assert observation['name'] == 'Observation'
        assert 'observations' in observation
        assert len(observation['observations']) > 0
    
    def test_format_reasoning_chain(self):
        """Test formatting reasoning chain."""
        reasoning = ChainOfThoughtReasoning()
        
        chain = {
            'steps': [
                {'step': 1, 'name': 'Test', 'summary': 'Test summary'}
            ],
            'final_decision': 'BUY',
            'confidence': 0.75
        }
        
        formatted = reasoning.format_reasoning_chain(chain)
        
        assert isinstance(formatted, str)
        assert 'BUY' in formatted
        assert '75' in formatted or '0.75' in formatted


class TestEnsembleDecisionMaker:
    """Test Ensemble Decision Maker."""
    
    def test_initialization(self):
        """Test ensemble initialization."""
        ensemble = EnsembleDecisionMaker(method='voting')
        assert ensemble.method == 'voting'
    
    def test_voting_ensemble(self):
        """Test voting ensemble method."""
        ensemble = EnsembleDecisionMaker(method='voting')
        
        decisions = [
            {'decision': 'BUY', 'confidence': 0.7, 'agent': 'agent1'},
            {'decision': 'BUY', 'confidence': 0.8, 'agent': 'agent2'},
            {'decision': 'HOLD', 'confidence': 0.6, 'agent': 'agent3'}
        ]
        
        result = ensemble.decide(decisions)
        
        assert result['decision'] == 'BUY'  # Majority
        assert 'confidence' in result
        assert result['method'] == 'voting'
        assert result['agents_count'] == 3
    
    def test_weighted_ensemble(self):
        """Test weighted ensemble method."""
        ensemble = EnsembleDecisionMaker(method='weighted')
        
        # Set weights
        ensemble.update_agent_weight('agent1', 0.9)  # Strong performer
        ensemble.update_agent_weight('agent2', 0.5)  # Weak performer
        
        decisions = [
            {'decision': 'BUY', 'confidence': 0.7, 'agent': 'agent1'},
            {'decision': 'SELL', 'confidence': 0.8, 'agent': 'agent2'}
        ]
        
        result = ensemble.decide(decisions)
        
        assert result['decision'] in ['BUY', 'SELL']
        assert result['method'] == 'weighted'
    
    def test_confidence_ensemble(self):
        """Test confidence-based ensemble."""
        ensemble = EnsembleDecisionMaker(method='confidence')
        
        decisions = [
            {'decision': 'BUY', 'confidence': 0.9},
            {'decision': 'SELL', 'confidence': 0.6},
            {'decision': 'BUY', 'confidence': 0.7}
        ]
        
        result = ensemble.decide(decisions)
        
        assert result['decision'] == 'BUY'  # Highest combined confidence
        assert result['method'] == 'confidence'
    
    def test_empty_decisions(self):
        """Test with no decisions."""
        ensemble = EnsembleDecisionMaker()
        
        result = ensemble.decide([])
        
        assert result['decision'] == 'HOLD'
        assert result['agents_count'] == 0
    
    def test_consensus_level(self):
        """Test consensus level calculation."""
        ensemble = EnsembleDecisionMaker()
        
        # Perfect consensus
        decisions = [
            {'decision': 'BUY'},
            {'decision': 'BUY'},
            {'decision': 'BUY'}
        ]
        
        consensus = ensemble.get_consensus_level(decisions)
        assert consensus == 1.0
        
        # Split decision
        decisions = [
            {'decision': 'BUY'},
            {'decision': 'SELL'}
        ]
        
        consensus = ensemble.get_consensus_level(decisions)
        assert consensus == 0.5


class TestConfidenceCalibrator:
    """Test Confidence Calibrator."""
    
    def test_initialization(self):
        """Test calibrator initialization."""
        calibrator = ConfidenceCalibrator()
        assert calibrator.calibrated is False
    
    def test_simple_calibration(self):
        """Test simple calibration without data."""
        calibrator = ConfidenceCalibrator()
        
        # High confidence should be reduced
        calibrated_high = calibrator.calibrate(0.95)
        assert calibrated_high < 0.95
        
        # Low confidence should be boosted
        calibrated_low = calibrator.calibrate(0.2)
        assert calibrated_low >= 0.2
        
        # Medium confidence should stay similar
        calibrated_mid = calibrator.calibrate(0.5)
        assert 0.4 <= calibrated_mid <= 0.6
    
    def test_add_observation(self):
        """Test adding calibration observations."""
        calibrator = ConfidenceCalibrator()
        
        # Add some observations
        calibrator.add_observation(0.7, True)  # Predicted 70%, was correct
        calibrator.add_observation(0.8, True)
        calibrator.add_observation(0.6, False)
        
        assert len(calibrator.calibration_data) == 3
    
    def test_calibration_with_data(self):
        """Test calibration after collecting data."""
        calibrator = ConfidenceCalibrator()
        
        # Add enough observations to trigger calibration
        for i in range(25):
            # Simulate overconfident predictions
            predicted = 0.8
            actual = i < 15  # Only 60% actually correct
            calibrator.add_observation(predicted, actual)
        
        assert calibrator.calibrated is True
        
        # Calibration should adjust the overconfidence
        calibrated = calibrator.calibrate(0.8)
        assert calibrated <= 0.8  # Should be adjusted down
    
    def test_get_statistics(self):
        """Test getting calibration statistics."""
        calibrator = ConfidenceCalibrator()
        
        # Empty stats
        stats = calibrator.get_statistics()
        assert stats['num_observations'] == 0
        
        # Add observations
        for i in range(10):
            calibrator.add_observation(0.7, i < 7)
        
        stats = calibrator.get_statistics()
        assert stats['num_observations'] == 10
        assert stats['mean_confidence'] > 0
        assert 0 <= stats['mean_accuracy'] <= 1
    
    def test_get_calibration_curve(self):
        """Test getting calibration curve data."""
        calibrator = ConfidenceCalibrator()
        
        # Add enough varied data
        for conf in [0.3, 0.5, 0.7, 0.9] * 5:
            outcome = conf > 0.5  # Simple rule
            calibrator.add_observation(conf, outcome)
        
        curve = calibrator.get_calibration_curve()
        
        assert 'predicted' in curve
        assert 'actual' in curve
        assert len(curve['predicted']) > 0
