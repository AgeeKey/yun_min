"""
Tests for Memory Module - Vector Store, Trade History, Pattern Library
"""

import pytest
import numpy as np
from yunmin.memory.vector_store import VectorStore
from yunmin.memory.trade_history import TradeHistory
from yunmin.memory.pattern_library import PatternLibrary, PatternType


class TestVectorStore:
    """Test VectorStore functionality."""
    
    def test_initialization(self):
        """Test vector store initialization."""
        store = VectorStore(embedding_dim=384, use_faiss=False)
        
        assert store.embedding_dim == 384
        assert len(store) == 0
    
    def test_add_vector(self):
        """Test adding vectors to store."""
        store = VectorStore(embedding_dim=10, use_faiss=False)
        
        # Add a vector
        embedding = np.random.rand(10).astype('float32')
        metadata = {'test': 'data', 'value': 42}
        
        idx = store.add(embedding, metadata)
        
        assert idx == 0
        assert len(store) == 1
    
    def test_search(self):
        """Test similarity search."""
        store = VectorStore(embedding_dim=10, use_faiss=False)
        
        # Add some vectors
        for i in range(5):
            embedding = np.random.rand(10).astype('float32')
            metadata = {'index': i, 'value': i * 10}
            store.add(embedding, metadata)
        
        # Search for similar
        query = np.random.rand(10).astype('float32')
        results = store.search(query, k=3)
        
        assert len(results) == 3
        assert all('metadata' in r for r in results)
        assert all('distance' in r for r in results)
        assert all('similarity' in r for r in results)
    
    def test_empty_search(self):
        """Test search on empty store."""
        store = VectorStore(embedding_dim=10, use_faiss=False)
        
        query = np.random.rand(10).astype('float32')
        results = store.search(query, k=3)
        
        assert len(results) == 0


class TestTradeHistory:
    """Test TradeHistory functionality."""
    
    def test_initialization(self):
        """Test trade history initialization."""
        history = TradeHistory(embedding_model='simple')
        
        assert history.embedding_model == 'simple'
        assert len(history) == 0
    
    def test_remember_trade(self):
        """Test remembering a trade."""
        history = TradeHistory(embedding_model='simple')
        
        trade_context = {
            'price': 50000.0,
            'indicators': {'rsi': 45, 'ema_fast': 49000, 'ema_slow': 48000},
            'trend': 'bullish',
            'volatility': 0.02
        }
        
        decision = {
            'action': 'BUY',
            'confidence': 0.75,
            'reasoning': 'Test trade'
        }
        
        outcome = {
            'pnl': 100.0,
            'success': True
        }
        
        trade_id = history.remember_trade(trade_context, decision, outcome)
        
        assert trade_id == 0
        assert len(history) == 1
    
    def test_recall_similar(self):
        """Test recalling similar trades."""
        history = TradeHistory(embedding_model='simple')
        
        # Add some trades
        for i in range(3):
            context = {
                'price': 50000.0 + i * 100,
                'indicators': {'rsi': 45 + i, 'ema_fast': 49000, 'ema_slow': 48000},
                'trend': 'bullish',
                'volatility': 0.02
            }
            decision = {'action': 'BUY', 'confidence': 0.7}
            outcome = {'pnl': 50.0 + i * 10}
            
            history.remember_trade(context, decision, outcome)
        
        # Recall similar
        current_context = {
            'price': 50100.0,
            'indicators': {'rsi': 46, 'ema_fast': 49000, 'ema_slow': 48000},
            'trend': 'bullish',
            'volatility': 0.02
        }
        
        similar = history.recall_similar(current_context, top_k=2)
        
        assert len(similar) <= 2
    
    def test_statistics(self):
        """Test getting statistics."""
        history = TradeHistory(embedding_model='simple')
        
        # Add trades with outcomes
        for i in range(5):
            context = {'price': 50000.0}
            decision = {'action': 'BUY'}
            outcome = {'pnl': 100.0 if i % 2 == 0 else -50.0}
            
            history.remember_trade(context, decision, outcome)
        
        stats = history.get_statistics()
        
        assert stats['total_trades'] == 5
        assert stats['trades_with_outcome'] == 5
        assert stats['win_rate'] > 0


class TestPatternLibrary:
    """Test PatternLibrary functionality."""
    
    def test_initialization(self):
        """Test pattern library initialization."""
        library = PatternLibrary()
        
        assert len(library) == 0
    
    def test_add_pattern(self):
        """Test adding a pattern."""
        library = PatternLibrary()
        
        context = {
            'indicators': {'rsi': 30},
            'trend': 'bullish'
        }
        
        outcome = {
            'pnl': 100.0
        }
        
        pattern_id = library.add_pattern(
            PatternType.BREAKOUT,
            context,
            outcome
        )
        
        assert pattern_id is not None
        assert len(library) == 1
    
    def test_pattern_statistics(self):
        """Test getting pattern statistics."""
        library = PatternLibrary()
        
        # Add multiple breakout patterns
        for i in range(5):
            context = {'indicators': {'rsi': 30 + i}}
            outcome = {'pnl': 50.0 if i < 3 else -20.0}
            
            library.add_pattern(PatternType.BREAKOUT, context, outcome)
        
        stats = library.get_pattern_statistics(PatternType.BREAKOUT)
        
        assert stats['count'] > 0
        assert stats['total_occurrences'] == 5
        assert 0 <= stats['win_rate'] <= 1
    
    def test_find_matching_patterns(self):
        """Test finding matching patterns."""
        library = PatternLibrary()
        
        # Add some patterns
        for i in range(3):
            context = {
                'indicators': {'rsi': 45 + i * 5},
                'trend': 'bullish'
            }
            outcome = {'pnl': 100.0}
            
            library.add_pattern(PatternType.TREND_CONTINUATION, context, outcome)
        
        # Find matches
        current_context = {
            'indicators': {'rsi': 47},
            'trend': 'bullish'
        }
        
        matches = library.find_matching_patterns(current_context, top_k=2)
        
        # Should find at least some matches
        assert isinstance(matches, list)
