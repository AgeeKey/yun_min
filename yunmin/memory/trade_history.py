"""
Trade History - Memory of Past Trades with Embeddings

Stores trade history with rich context and enables similarity search
for finding similar past situations using RAG.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
from loguru import logger

from yunmin.memory.vector_store import VectorStore


class TradeHistory:
    """
    Trade history with embeddings for similarity search.
    
    Stores each trade with:
    - Market context (price, indicators, orderbook)
    - Decision reasoning
    - Outcome (PnL, success/failure)
    - Embedding for similarity search
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_model: str = "simple"
    ):
        """
        Initialize trade history.
        
        Args:
            vector_store: VectorStore instance for similarity search
            embedding_model: Model to use for embeddings ("simple", "openai")
        """
        self.vector_store = vector_store or VectorStore(embedding_dim=384)
        self.embedding_model = embedding_model
        
        logger.info(f"📚 Trade history initialized with {self.embedding_model} embeddings")
    
    def remember_trade(
        self,
        trade_context: Dict[str, Any],
        decision: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Remember a trade with full context.
        
        Args:
            trade_context: Market conditions (price, indicators, etc.)
            decision: Trading decision (action, reasoning, confidence)
            outcome: Trade result (PnL, success/failure) - can be added later
            
        Returns:
            Trade ID (index in vector store)
        """
        # Create embedding from trade context
        embedding = self._create_embedding(trade_context)
        
        # Combine all information
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'context': trade_context,
            'decision': decision,
            'outcome': outcome,
        }
        
        # Store in vector database
        trade_id = self.vector_store.add(embedding, metadata)
        
        logger.debug(f"💾 Remembered trade {trade_id}")
        return trade_id
    
    def recall_similar(
        self,
        current_context: Dict[str, Any],
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past situations.
        
        Args:
            current_context: Current market conditions
            top_k: Number of similar situations to retrieve
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of similar past trades with metadata
        """
        # Create embedding for current context
        query_embedding = self._create_embedding(current_context)
        
        # Search for similar vectors
        results = self.vector_store.search(query_embedding, k=top_k)
        
        # Filter by similarity threshold
        filtered_results = [
            r for r in results
            if r['similarity'] >= min_similarity
        ]
        
        # Format results
        similar_trades = []
        for r in filtered_results:
            meta = r['metadata']
            similar_trades.append({
                'situation': meta.get('context', {}),
                'decision': meta.get('decision', {}),
                'outcome': meta.get('outcome', {}),
                'similarity': r['similarity'],
                'timestamp': meta.get('timestamp', '')
            })
        
        logger.debug(f"🔍 Found {len(similar_trades)} similar trades (threshold={min_similarity})")
        return similar_trades
    
    def update_outcome(
        self,
        trade_id: int,
        outcome: Dict[str, Any]
    ) -> None:
        """
        Update the outcome of a trade after it closes.
        
        Args:
            trade_id: ID of the trade to update
            outcome: Trade outcome (PnL, success/failure, lessons)
        """
        if trade_id < len(self.vector_store):
            self.vector_store.metadata[trade_id]['outcome'] = outcome
            logger.debug(f"✏️  Updated outcome for trade {trade_id}")
        else:
            logger.warning(f"Trade {trade_id} not found")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored trades.
        
        Returns:
            Dictionary with trade statistics
        """
        total_trades = len(self.vector_store)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'trades_with_outcome': 0,
                'avg_pnl': 0.0,
                'win_rate': 0.0
            }
        
        trades_with_outcome = 0
        total_pnl = 0.0
        wins = 0
        
        for meta in self.vector_store.metadata:
            outcome = meta.get('outcome')
            if outcome:
                trades_with_outcome += 1
                pnl = outcome.get('pnl', 0.0)
                total_pnl += pnl
                if pnl > 0:
                    wins += 1
        
        return {
            'total_trades': total_trades,
            'trades_with_outcome': trades_with_outcome,
            'avg_pnl': total_pnl / trades_with_outcome if trades_with_outcome > 0 else 0.0,
            'win_rate': wins / trades_with_outcome if trades_with_outcome > 0 else 0.0
        }
    
    def _create_embedding(self, context: Dict[str, Any]) -> np.ndarray:
        """
        Create embedding vector from trade context.
        
        Args:
            context: Market context dictionary
            
        Returns:
            Embedding vector as numpy array
        """
        if self.embedding_model == "simple":
            return self._simple_embedding(context)
        elif self.embedding_model == "openai":
            return self._openai_embedding(context)
        else:
            raise ValueError(f"Unknown embedding model: {self.embedding_model}")
    
    def _simple_embedding(self, context: Dict[str, Any]) -> np.ndarray:
        """
        Create simple embedding from numerical features.
        
        Uses key market indicators as features.
        """
        # Extract numerical features
        features = []
        
        # Price features
        price = context.get('price', 0.0)
        features.append(price / 100000.0)  # Normalize BTC price
        
        # Technical indicators
        indicators = context.get('indicators', {})
        features.append(indicators.get('rsi', 50.0) / 100.0)
        features.append(indicators.get('ema_fast', price) / price if price > 0 else 1.0)
        features.append(indicators.get('ema_slow', price) / price if price > 0 else 1.0)
        features.append(indicators.get('macd', 0.0) / 1000.0)
        features.append(indicators.get('volume_ratio', 1.0))
        
        # Trend features
        features.append(1.0 if context.get('trend') == 'bullish' else -1.0 if context.get('trend') == 'bearish' else 0.0)
        features.append(context.get('volatility', 0.02))
        
        # Pad to embedding dimension (384)
        features = features + [0.0] * (384 - len(features))
        features = features[:384]
        
        return np.array(features, dtype=np.float32)
    
    def _openai_embedding(self, context: Dict[str, Any]) -> np.ndarray:
        """
        Create embedding using OpenAI embeddings API.
        
        This is more expensive but produces better semantic embeddings.
        """
        try:
            import openai
            import os
            
            # Create text description of context
            text = self._context_to_text(context)
            
            # Get embedding from OpenAI
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Resize if needed (text-embedding-3-small is 1536 dim)
            if len(embedding) != 384:
                # Simple resize by averaging chunks
                chunk_size = len(embedding) // 384
                resized = []
                for i in range(384):
                    start = i * chunk_size
                    end = start + chunk_size
                    resized.append(embedding[start:end].mean())
                embedding = np.array(resized, dtype=np.float32)
            
            return embedding
            
        except Exception as e:
            logger.warning(f"Failed to create OpenAI embedding: {e}, falling back to simple")
            return self._simple_embedding(context)
    
    def _context_to_text(self, context: Dict[str, Any]) -> str:
        """Convert context dictionary to text description."""
        parts = []
        
        price = context.get('price', 0)
        parts.append(f"Price: {price}")
        
        indicators = context.get('indicators', {})
        if indicators:
            parts.append(f"RSI: {indicators.get('rsi', 50):.1f}")
            parts.append(f"MACD: {indicators.get('macd', 0):.2f}")
        
        trend = context.get('trend', 'neutral')
        parts.append(f"Trend: {trend}")
        
        volatility = context.get('volatility', 0)
        parts.append(f"Volatility: {volatility:.3f}")
        
        return ", ".join(parts)
    
    def save(self) -> None:
        """Save trade history to disk."""
        self.vector_store.save()
        logger.info("💾 Trade history saved")
    
    def __len__(self) -> int:
        """Return number of trades in history."""
        return len(self.vector_store)
