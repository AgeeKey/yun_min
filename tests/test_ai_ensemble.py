"""
Tests for Multi-Model AI Ensemble Strategy
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from yunmin.strategy.ai_ensemble import (
    AIEnsembleStrategy, 
    ModelProvider, 
    ModelPrediction,
    SignalType
)


class TestAIEnsembleStrategy:
    """Test suite for AI Ensemble strategy."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
        
        base_price = 50000
        prices = base_price + np.cumsum(np.random.randn(100) * 100)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + np.random.rand(100) * 50,
            'low': prices - np.random.rand(100) * 50,
            'close': prices,
            'volume': np.random.rand(100) * 1000
        })
        
        return data
    
    @pytest.fixture
    def mock_strategy(self):
        """Create ensemble strategy with mocked API keys."""
        return AIEnsembleStrategy(
            groq_api_key="test_groq_key",
            openrouter_api_key="test_openrouter_key",
            openai_api_key="test_openai_key"
        )
    
    def test_initialization_all_models(self):
        """Test strategy initialization with all models enabled."""
        strategy = AIEnsembleStrategy(
            groq_api_key="test_groq",
            openrouter_api_key="test_openrouter",
            openai_api_key="test_openai"
        )
        
        assert strategy.name == "AI_Ensemble"
        assert len(strategy.enabled_models) == 3
        assert ModelProvider.GROQ in strategy.enabled_models
        assert ModelProvider.OPENROUTER in strategy.enabled_models
        assert ModelProvider.OPENAI in strategy.enabled_models
    
    def test_initialization_partial_models(self):
        """Test initialization with only some models enabled."""
        strategy = AIEnsembleStrategy(
            groq_api_key="test_groq",
            openrouter_api_key=None,
            openai_api_key="test_openai",
            enable_openrouter=False
        )
        
        assert len(strategy.enabled_models) == 2
        assert ModelProvider.GROQ in strategy.enabled_models
        assert ModelProvider.OPENAI in strategy.enabled_models
        assert ModelProvider.OPENROUTER not in strategy.enabled_models
    
    def test_insufficient_data(self, mock_strategy):
        """Test strategy with insufficient data."""
        data = pd.DataFrame({
            'close': [50000, 50100],
            'high': [50050, 50150],
            'low': [49950, 50050],
            'volume': [100, 110]
        })
        
        signal = mock_strategy.analyze(data)
        
        assert signal.type == SignalType.HOLD
        assert signal.confidence == 0.0
        assert "Insufficient data" in signal.reason
    
    def test_prepare_market_context(self, mock_strategy, sample_data):
        """Test market context preparation."""
        context = mock_strategy._prepare_market_context(sample_data)
        
        assert 'price' in context
        assert 'prev_price' in context
        assert 'price_change_pct' in context
        assert 'sma_20' in context
        assert 'sma_50' in context
        assert 'volatility' in context
        assert 'trend' in context
        assert context['trend'] in ['bullish', 'bearish']
    
    def test_create_trading_prompt(self, mock_strategy):
        """Test trading prompt creation."""
        market_data = {
            'price': 50000.0,
            'price_change_pct': 1.5,
            'high_24h': 51000.0,
            'low_24h': 49000.0,
            'sma_20': 49800.0,
            'sma_50': 49500.0,
            'volatility': 2.3,
            'trend': 'bullish'
        }
        
        prompt = mock_strategy._create_trading_prompt(market_data)
        
        assert "50000" in prompt
        assert "1.5" in prompt
        assert "SIGNAL:" in prompt
        assert "CONFIDENCE:" in prompt
        assert "REASONING:" in prompt
    
    def test_parse_llm_response_buy(self, mock_strategy):
        """Test parsing BUY signal from LLM response."""
        response = """SIGNAL: BUY
CONFIDENCE: 85
REASONING: Strong bullish momentum with price above key moving averages."""
        
        signal_type, confidence, reasoning = mock_strategy._parse_llm_response(response)
        
        assert signal_type == SignalType.BUY
        assert confidence == 0.85
        assert "bullish momentum" in reasoning.lower()
    
    def test_parse_llm_response_sell(self, mock_strategy):
        """Test parsing SELL signal from LLM response."""
        response = """SIGNAL: SELL
CONFIDENCE: 75
REASONING: Bearish trend with declining volume."""
        
        signal_type, confidence, reasoning = mock_strategy._parse_llm_response(response)
        
        assert signal_type == SignalType.SELL
        assert confidence == 0.75
        assert "bearish" in reasoning.lower()
    
    def test_parse_llm_response_hold(self, mock_strategy):
        """Test parsing HOLD signal from LLM response."""
        response = """SIGNAL: HOLD
CONFIDENCE: 60
REASONING: Mixed signals, waiting for clearer direction."""
        
        signal_type, confidence, reasoning = mock_strategy._parse_llm_response(response)
        
        assert signal_type == SignalType.HOLD
        assert confidence == 0.60
    
    def test_meta_analysis_strong_consensus(self, mock_strategy):
        """Test meta-analysis with strong consensus."""
        predictions = [
            ModelPrediction(
                provider=ModelProvider.GROQ,
                signal_type=SignalType.BUY,
                confidence=0.8,
                reasoning="Bullish trend",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENROUTER,
                signal_type=SignalType.BUY,
                confidence=0.85,
                reasoning="Strong momentum",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENAI,
                signal_type=SignalType.BUY,
                confidence=0.75,
                reasoning="Positive indicators",
                success=True
            )
        ]
        
        market_data = {'price': 50000, 'trend': 'bullish'}
        signal = mock_strategy._meta_analysis(predictions, market_data)
        
        assert signal.type == SignalType.BUY
        assert signal.confidence > 0.7  # High consensus should have high confidence
        assert "100% agreement" in signal.reason or "consensus" in signal.reason.lower()
    
    def test_meta_analysis_split_vote(self, mock_strategy):
        """Test meta-analysis with split vote (disagreement)."""
        predictions = [
            ModelPrediction(
                provider=ModelProvider.GROQ,
                signal_type=SignalType.BUY,
                confidence=0.7,
                reasoning="Bullish",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENROUTER,
                signal_type=SignalType.SELL,
                confidence=0.6,
                reasoning="Bearish",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENAI,
                signal_type=SignalType.HOLD,
                confidence=0.5,
                reasoning="Neutral",
                success=True
            )
        ]
        
        market_data = {'price': 50000, 'trend': 'neutral'}
        signal = mock_strategy._meta_analysis(predictions, market_data)
        
        # With split vote, confidence should be reduced
        assert signal.confidence < 0.7
        # Disagreement should be logged
        assert len(mock_strategy.disagreements) > 0
    
    def test_meta_analysis_majority_not_unanimous(self, mock_strategy):
        """Test meta-analysis with majority but not unanimous."""
        predictions = [
            ModelPrediction(
                provider=ModelProvider.GROQ,
                signal_type=SignalType.BUY,
                confidence=0.8,
                reasoning="Bullish",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENROUTER,
                signal_type=SignalType.BUY,
                confidence=0.75,
                reasoning="Bullish",
                success=True
            ),
            ModelPrediction(
                provider=ModelProvider.OPENAI,
                signal_type=SignalType.HOLD,
                confidence=0.6,
                reasoning="Wait",
                success=True
            )
        ]
        
        market_data = {'price': 50000}
        signal = mock_strategy._meta_analysis(predictions, market_data)
        
        # 2 out of 3 agree on BUY (66% agreement)
        assert signal.type == SignalType.BUY
        # Check if disagreement is logged depending on threshold
        # Default threshold is 0.6, so 0.66 should pass
    
    def test_fallback_signal_bullish(self, mock_strategy):
        """Test fallback signal in bullish market."""
        market_data = {
            'price': 50000.0,
            'sma_20': 49000.0,
            'trend': 'bullish'
        }
        
        predictions = [
            ModelPrediction(
                provider=ModelProvider.GROQ,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="",
                success=False,
                error="API error"
            )
        ]
        
        signal = mock_strategy._fallback_signal(market_data, predictions)
        
        assert signal.type == SignalType.BUY
        assert signal.confidence == 0.3  # Lower confidence for fallback
        assert "Fallback mode" in signal.reason
    
    def test_fallback_signal_bearish(self, mock_strategy):
        """Test fallback signal in bearish market."""
        market_data = {
            'price': 48000.0,
            'sma_20': 49000.0,
            'trend': 'bearish'
        }
        
        predictions = [
            ModelPrediction(
                provider=ModelProvider.GROQ,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reasoning="",
                success=False,
                error="Timeout"
            )
        ]
        
        signal = mock_strategy._fallback_signal(market_data, predictions)
        
        assert signal.type == SignalType.SELL
        assert signal.confidence == 0.3
        assert "Fallback mode" in signal.reason
    
    def test_fallback_signal_neutral(self, mock_strategy):
        """Test fallback signal in neutral market."""
        market_data = {
            'price': 49500.0,
            'sma_20': 49400.0,
            'trend': 'neutral'
        }
        
        predictions = []
        
        signal = mock_strategy._fallback_signal(market_data, predictions)
        
        assert signal.type == SignalType.HOLD
        assert "Fallback mode" in signal.reason
    
    def test_get_disagreement_log(self, mock_strategy):
        """Test disagreement logging."""
        # Simulate a disagreement
        predictions = [
            ModelPrediction(ModelProvider.GROQ, SignalType.BUY, 0.7, "Bull", True),
            ModelPrediction(ModelProvider.OPENROUTER, SignalType.SELL, 0.6, "Bear", True),
        ]
        
        market_data = {'price': 50000}
        mock_strategy._meta_analysis(predictions, market_data)
        
        log = mock_strategy.get_disagreement_log()
        assert len(log) > 0
        assert 'votes' in log[0]
        assert 'predictions' in log[0]
    
    def test_get_params(self, mock_strategy):
        """Test getting strategy parameters."""
        params = mock_strategy.get_params()
        
        assert 'consensus_threshold' in params
        assert 'min_models' in params
        assert 'enabled_models' in params
        assert 'model_count' in params
        assert params['model_count'] == 3
    
    @patch('requests.post')
    def test_call_groq_success(self, mock_post, mock_strategy):
        """Test successful Groq API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SIGNAL: BUY\nCONFIDENCE: 80\nREASONING: Good"}}]
        }
        mock_post.return_value = mock_response
        
        result = mock_strategy._call_groq("test prompt", 30)
        
        assert "SIGNAL: BUY" in result
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_call_openrouter_success(self, mock_post, mock_strategy):
        """Test successful OpenRouter API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SIGNAL: SELL\nCONFIDENCE: 70\nREASONING: Bearish"}}]
        }
        mock_post.return_value = mock_response
        
        result = mock_strategy._call_openrouter("test prompt", 30)
        
        assert "SIGNAL: SELL" in result
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_call_openai_success(self, mock_post, mock_strategy):
        """Test successful OpenAI API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SIGNAL: HOLD\nCONFIDENCE: 60\nREASONING: Wait"}}]
        }
        mock_post.return_value = mock_response
        
        result = mock_strategy._call_openai("test prompt", 30)
        
        assert "SIGNAL: HOLD" in result
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_analyze_with_mocked_llms(self, mock_post, sample_data):
        """Test full analyze flow with mocked LLM responses."""
        # Mock all LLM responses to return BUY signals
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "SIGNAL: BUY\nCONFIDENCE: 85\nREASONING: Strong bullish trend"}}]
        }
        mock_post.return_value = mock_response
        
        strategy = AIEnsembleStrategy(
            groq_api_key="test_groq",
            openrouter_api_key="test_openrouter",
            openai_api_key="test_openai"
        )
        
        signal = strategy.analyze(sample_data)
        
        assert signal.type == SignalType.BUY
        assert signal.confidence > 0.0
        assert "consensus" in signal.reason.lower()
    
    @patch('requests.post')
    def test_analyze_with_api_failure(self, mock_post, sample_data):
        """Test analyze when APIs fail."""
        # Simulate API failure
        mock_post.side_effect = Exception("API Error")
        
        strategy = AIEnsembleStrategy(
            groq_api_key="test_groq",
            openrouter_api_key="test_openrouter",
            openai_api_key="test_openai"
        )
        
        signal = strategy.analyze(sample_data)
        
        # Should fall back to technical analysis
        assert signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert "Fallback mode" in signal.reason
    
    def test_confidence_range(self, mock_strategy):
        """Test that confidence values are always in valid range [0, 1]."""
        # Test various confidence inputs
        test_cases = [
            ("CONFIDENCE: 150", 1.0),  # Should cap at 1.0
            ("CONFIDENCE: -10", 0.0),  # Should floor at 0.0
            ("CONFIDENCE: 50", 0.5),   # Normal case
            ("CONFIDENCE: 0", 0.0),    # Min valid
            ("CONFIDENCE: 100", 1.0),  # Max valid
        ]
        
        for input_str, expected in test_cases:
            response = f"SIGNAL: BUY\n{input_str}\nREASONING: Test"
            _, confidence, _ = mock_strategy._parse_llm_response(response)
            assert 0.0 <= confidence <= 1.0
            assert confidence == expected
    
    def test_empty_predictions_list(self, mock_strategy):
        """Test meta-analysis with empty predictions list."""
        signal = mock_strategy._meta_analysis([], {})
        
        assert signal.type == SignalType.HOLD
        assert signal.confidence == 0.0
        assert "No valid predictions" in signal.reason
