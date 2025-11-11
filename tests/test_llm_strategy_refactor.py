"""
Test suite for LLMAIStrategy refactoring.

Validates:
1. New LLMAIStrategy class works correctly
2. Backward compatibility with GrokAIStrategy
3. OpenAI analyzer integration
4. Groq analyzer integration (legacy)
5. Parameter naming (llm_analyzer vs grok_analyzer)
"""

import pytest
from unittest.mock import Mock
from yunmin.strategy.grok_ai_strategy import LLMAIStrategy, GrokAIStrategy


class TestLLMAIStrategyRefactor:
    """Test suite for strategy refactoring."""
    
    def test_imports_successful(self):
        """Test that all required imports work."""
        # Should not raise any exceptions
        from yunmin.strategy.grok_ai_strategy import LLMAIStrategy, GrokAIStrategy
        from yunmin.llm.openai_analyzer import OpenAIAnalyzer
        from yunmin.llm.grok_analyzer import GrokAnalyzer
        
        assert LLMAIStrategy is not None
        assert GrokAIStrategy is not None
        assert OpenAIAnalyzer is not None
        assert GrokAnalyzer is not None
    
    def test_grok_ai_strategy_is_alias(self):
        """Test that GrokAIStrategy is a subclass of LLMAIStrategy."""
        assert issubclass(GrokAIStrategy, LLMAIStrategy)
    
    def test_llm_strategy_with_new_parameter_name(self):
        """Test LLMAIStrategy with new parameter name."""
        mock_analyzer = Mock()
        mock_analyzer.enabled = True
        mock_analyzer.__class__.__name__ = "MockAnalyzer"
        
        strategy = LLMAIStrategy(llm_analyzer=mock_analyzer)
        
        assert strategy.llm is mock_analyzer
        assert strategy.grok is mock_analyzer  # Backward compat alias
    
    def test_llm_strategy_with_old_parameter_name(self):
        """Test LLMAIStrategy with old parameter name (backward compat)."""
        mock_analyzer = Mock()
        mock_analyzer.enabled = True
        mock_analyzer.__class__.__name__ = "MockAnalyzer"
        
        strategy = LLMAIStrategy(grok_analyzer=mock_analyzer)
        
        assert strategy.llm is mock_analyzer
        assert strategy.grok is mock_analyzer
    
    def test_grok_strategy_backward_compatibility(self):
        """Test GrokAIStrategy backward compatibility."""
        mock_analyzer = Mock()
        mock_analyzer.enabled = True
        mock_analyzer.__class__.__name__ = "MockAnalyzer"
        
        # Old API should still work
        strategy = GrokAIStrategy(grok_analyzer=mock_analyzer)
        
        assert strategy.llm is mock_analyzer
        assert strategy.grok is mock_analyzer
    
    def test_strategy_without_analyzer(self):
        """Test strategy initialization without analyzer."""
        strategy = LLMAIStrategy(llm_analyzer=None)
        
        assert strategy.llm is None
        assert strategy.grok is None
    
    def test_strategy_with_disabled_analyzer(self):
        """Test strategy with disabled analyzer."""
        mock_analyzer = Mock()
        mock_analyzer.enabled = False
        mock_analyzer.__class__.__name__ = "DisabledAnalyzer"
        
        strategy = LLMAIStrategy(llm_analyzer=mock_analyzer)
        
        # Strategy should initialize but not use AI
        assert strategy.llm is mock_analyzer
        assert not strategy.llm.enabled
    
    def test_openai_analyzer_integration(self):
        """Test OpenAI analyzer integration."""
        from yunmin.llm.openai_analyzer import OpenAIAnalyzer
        
        # Without API key
        analyzer = OpenAIAnalyzer()
        assert analyzer.enabled is False
        
        strategy = LLMAIStrategy(llm_analyzer=analyzer)
        assert strategy.llm is analyzer
        assert not strategy.llm.enabled
    
    def test_groq_analyzer_integration(self):
        """Test Groq analyzer integration (legacy)."""
        from yunmin.llm.grok_analyzer import GrokAnalyzer
        
        # Without API key
        analyzer = GrokAnalyzer()
        assert analyzer.enabled is False
        
        strategy = LLMAIStrategy(llm_analyzer=analyzer)
        assert strategy.llm is analyzer
        assert not strategy.llm.enabled
    
    def test_strategy_initialization_modes(self):
        """Test strategy initialization with different modes."""
        # Test hybrid mode
        strategy1 = LLMAIStrategy(
            llm_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        assert strategy1.hybrid_mode is True
        assert strategy1.use_advanced_indicators is True
        
        # Test AI-only mode
        strategy2 = LLMAIStrategy(
            llm_analyzer=None,
            use_advanced_indicators=False,
            hybrid_mode=False
        )
        assert strategy2.hybrid_mode is False
        assert strategy2.use_advanced_indicators is False
    
    def test_phase2_relaxed_parameters(self):
        """Test Phase 2 relaxed parameters are correctly set."""
        strategy = LLMAIStrategy(llm_analyzer=None)
        
        # Phase 2.1: Relaxed thresholds
        assert strategy.fallback_rsi_oversold == 35  # Was 30
        assert strategy.fallback_rsi_overbought == 65  # Was 70
        assert strategy.volume_multiplier == 1.2  # Was 1.5
        assert strategy.min_ema_distance == 0.003  # Was 0.005


class TestBackwardCompatibilityWarnings:
    """Test deprecation warnings."""
    
    def test_deprecation_warning_with_grok_parameter(self, caplog):
        """Test that using grok_analyzer shows deprecation warning."""
        import logging
        caplog.set_level(logging.WARNING)
        
        mock_analyzer = Mock()
        mock_analyzer.enabled = False
        
        # Use deprecated parameter
        strategy = GrokAIStrategy(grok_analyzer=mock_analyzer)
        
        # Check that strategy still works
        assert strategy.llm is mock_analyzer


class TestAnalyzerCompatibility:
    """Test analyzer interface compatibility."""
    
    def test_analyzer_interface_requirements(self):
        """Test that analyzer must have required interface."""
        # Mock analyzer with required interface
        mock_analyzer = Mock()
        mock_analyzer.enabled = True
        mock_analyzer.analyze_market = Mock(return_value={
            'signal': 'HOLD',
            'confidence': 0.5,
            'reasoning': 'Test',
            'model_used': 'test-model'
        })
        
        strategy = LLMAIStrategy(llm_analyzer=mock_analyzer)
        
        # Strategy should be able to call analyze_market
        assert hasattr(strategy.llm, 'analyze_market')
        assert hasattr(strategy.llm, 'enabled')
        
        result = strategy.llm.analyze_market({})
        assert 'signal' in result
        assert 'confidence' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
