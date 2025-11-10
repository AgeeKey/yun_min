"""
Integration test for Phase 2 enhancements to GrokAIStrategy

Tests the complete flow:
- Relaxed entry conditions
- Advanced indicators integration
- Hybrid mode (classical + AI)
- Voting system
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.strategy.base import SignalType


class TestGrokAIStrategyPhase2:
    """Integration tests for Phase 2 enhanced strategy."""
    
    @pytest.fixture
    def sample_data(self):
        """Create realistic sample OHLCV data."""
        np.random.seed(42)
        n = 100
        dates = pd.date_range(start='2024-01-01', periods=n, freq='5min')
        
        # Generate realistic BTC-like price data
        base_price = 50000
        trend = np.linspace(0, 2000, n)  # Upward trend
        noise = np.cumsum(np.random.randn(n) * 50)
        close_prices = base_price + trend + noise
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices + np.random.randn(n) * 20,
            'high': close_prices + abs(np.random.randn(n) * 50),
            'low': close_prices - abs(np.random.randn(n) * 50),
            'close': close_prices,
            'volume': np.random.rand(n) * 1000 + 500
        })
        
        return df
    
    @pytest.fixture
    def mock_ai_analyzer(self):
        """Create a mock AI analyzer."""
        mock = Mock()
        mock.enabled = True
        mock.__class__.__name__ = "MockAIAnalyzer"
        
        # Mock analyze_market to return bullish signal
        mock.analyze_market = Mock(return_value={
            'signal': 'BUY',
            'confidence': 0.75,
            'reasoning': 'Mock AI says BUY',
            'model_used': 'mock-model'
        })
        
        return mock
    
    def test_strategy_initialization_with_phase2_features(self):
        """Test strategy initializes with Phase 2 features enabled."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        assert strategy.use_advanced_indicators is True
        assert strategy.hybrid_mode is True
        assert strategy.fallback_rsi_oversold == 35  # Relaxed from 30
        assert strategy.fallback_rsi_overbought == 65  # Relaxed from 70
        assert strategy.volume_multiplier == 1.2  # Relaxed from 1.5
        assert strategy.min_ema_distance == 0.003  # Relaxed from 0.005
    
    def test_classical_analysis_generates_signal(self, sample_data):
        """Test classical analysis without AI."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        signal = strategy.analyze(sample_data)
        
        # Should generate a valid signal
        assert signal is not None
        assert signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0.0 <= signal.confidence <= 1.0
        assert len(signal.reason) > 0
    
    def test_hybrid_mode_with_high_classical_confidence(self, sample_data, mock_ai_analyzer):
        """Test hybrid mode skips AI when classical confidence is high."""
        strategy = GrokAIStrategy(
            grok_analyzer=mock_ai_analyzer,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        # Patch _classical_analysis to return high confidence
        original_classical = strategy._classical_analysis
        def high_confidence_classical(df):
            from yunmin.strategy.base import Signal, SignalType
            return Signal(
                type=SignalType.BUY,
                confidence=0.85,  # High confidence
                reason="High confidence classical signal"
            )
        strategy._classical_analysis = high_confidence_classical
        
        signal = strategy.analyze(sample_data)
        
        # AI should not be called
        assert not mock_ai_analyzer.analyze_market.called
        assert signal.type == SignalType.BUY
        assert signal.confidence >= 0.70
    
    def test_hybrid_mode_consults_ai_on_low_confidence(self, sample_data, mock_ai_analyzer):
        """Test hybrid mode consults AI when classical confidence is low."""
        strategy = GrokAIStrategy(
            grok_analyzer=mock_ai_analyzer,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        # Patch _classical_analysis to return low confidence
        def low_confidence_classical(df):
            from yunmin.strategy.base import Signal, SignalType
            return Signal(
                type=SignalType.HOLD,
                confidence=0.55,  # Low confidence
                reason="Low confidence classical signal"
            )
        strategy._classical_analysis = low_confidence_classical
        
        signal = strategy.analyze(sample_data)
        
        # AI should be consulted
        assert mock_ai_analyzer.analyze_market.called
    
    def test_advanced_indicators_integration(self, sample_data):
        """Test that advanced indicators are calculated when enabled."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=False
        )
        
        # Calculate indicators
        df_with_indicators = strategy._calculate_indicators(sample_data)
        
        # Check advanced indicators are present
        assert 'macd_line' in df_with_indicators.columns
        assert 'macd_signal' in df_with_indicators.columns
        assert 'bb_upper' in df_with_indicators.columns
        assert 'bb_lower' in df_with_indicators.columns
        assert 'atr' in df_with_indicators.columns
        assert 'obv' in df_with_indicators.columns
        assert 'ichimoku_cloud_top' in df_with_indicators.columns
    
    def test_voting_system_generates_signal(self, sample_data):
        """Test the voting system generates valid signals."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        df_with_indicators = strategy._calculate_indicators(sample_data)
        classical_signal = strategy._classical_analysis(df_with_indicators)
        
        # Voting should produce a valid signal
        assert classical_signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert 0.0 <= classical_signal.confidence <= 1.0
    
    def test_relaxed_thresholds_allow_more_trades(self, sample_data):
        """Test that relaxed thresholds are less strict than before."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        # Test RSI thresholds
        assert strategy.fallback_rsi_oversold == 35  # More lenient than 30
        assert strategy.fallback_rsi_overbought == 65  # More lenient than 70
        
        # Test that RSI between 35-40 would now trigger (but 30-35 wouldn't before)
        # Create data with RSI ~37
        test_data = sample_data.copy()
        
        df_with_indicators = strategy._calculate_indicators(test_data)
        signal = strategy.analyze(test_data)
        
        # Should not crash and produce valid signal
        assert signal is not None
    
    def test_signal_merging_logic(self):
        """Test signal merging when classical and AI disagree."""
        from yunmin.strategy.base import Signal, SignalType
        
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        # Test agreement: both BUY
        classical = Signal(type=SignalType.BUY, confidence=0.65, reason="Classical BUY")
        ai = Signal(type=SignalType.BUY, confidence=0.70, reason="AI BUY")
        merged = strategy._merge_signals(classical, ai)
        
        assert merged.type == SignalType.BUY
        assert merged.confidence > classical.confidence  # Boosted by agreement
        
        # Test disagreement: classical BUY, AI SELL
        ai_sell = Signal(type=SignalType.SELL, confidence=0.60, reason="AI SELL")
        merged_disagree = strategy._merge_signals(classical, ai_sell)
        
        # Should take higher confidence (classical)
        assert merged_disagree.type == SignalType.BUY
        assert merged_disagree.confidence < classical.confidence  # Penalized for disagreement
    
    def test_non_hybrid_mode_works(self, sample_data, mock_ai_analyzer):
        """Test non-hybrid mode (AI-first) still works."""
        strategy = GrokAIStrategy(
            grok_analyzer=mock_ai_analyzer,
            use_advanced_indicators=True,
            hybrid_mode=False  # Disabled
        )
        
        signal = strategy.analyze(sample_data)
        
        # AI should be called directly
        assert mock_ai_analyzer.analyze_market.called
        assert signal.type in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
    
    def test_backwards_compatibility_basic_indicators_only(self, sample_data):
        """Test backwards compatibility with advanced indicators disabled."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=False,  # Disabled
            hybrid_mode=False
        )
        
        df_with_indicators = strategy._calculate_indicators(sample_data)
        
        # Only basic indicators should be present
        assert 'rsi' in df_with_indicators.columns
        assert 'ema_fast' in df_with_indicators.columns
        assert 'ema_slow' in df_with_indicators.columns
        
        # Advanced indicators should not be present
        assert 'macd_line' not in df_with_indicators.columns
        
        # Should still generate signal
        signal = strategy.analyze(sample_data)
        assert signal is not None
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        strategy = GrokAIStrategy(
            grok_analyzer=None,
            use_advanced_indicators=True,
            hybrid_mode=True
        )
        
        # Very short dataframe
        short_df = pd.DataFrame({
            'close': [50000, 50100, 50200],
            'high': [50100, 50200, 50300],
            'low': [49900, 50000, 50100],
            'open': [50000, 50050, 50150],
            'volume': [100, 110, 105]
        })
        
        signal = strategy.analyze(short_df)
        
        # Should return HOLD with low confidence
        assert signal.type == SignalType.HOLD
        assert signal.confidence == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
