# Memory System Architecture

## Overview

YunMin's memory system enables the trading agent to learn from past experiences using RAG (Retrieval-Augmented Generation) with vector embeddings.

## Components

### Vector Store (`memory/vector_store.py`)

- **Technology**: FAISS (Facebook AI Similarity Search)
- **Purpose**: Fast similarity search for trade history retrieval
- **Features**:
  - Efficient storage of trade embeddings
  - Semantic search capabilities
  - Incremental updates

### Trade History (`memory/trade_history.py`)

- **Purpose**: Store and retrieve historical trade data
- **Features**:
  - Trade outcome tracking
  - Market condition snapshots
  - Performance metrics
  - Embedding generation for each trade

### Pattern Library (`memory/pattern_library.py`)

- **Purpose**: Identify and store recurring market patterns
- **Features**:
  - Pattern detection algorithms
  - Success rate tracking
  - Context-aware pattern matching

## How It Works

1. **Trade Execution**: Every trade is recorded with full context
   - Market conditions (price, volume, indicators)
   - Decision reasoning
   - Outcome (profit/loss)

2. **Embedding Generation**: Trade data is converted to vector embeddings
   - Uses LLM to create semantic representations
   - Captures both numerical and contextual data

3. **Retrieval**: When making new decisions, the agent:
   - Creates embedding of current market state
   - Queries similar past situations
   - Learns from historical outcomes

4. **Learning**: Agent continuously improves by:
   - Identifying successful patterns
   - Avoiding repeated mistakes
   - Adjusting confidence based on past performance

## Configuration

```yaml
memory:
  enabled: true
  vector_store:
    backend: faiss  # or chromadb
    dimension: 1536  # OpenAI embedding dimension
    index_path: ./data/vectors/
  
  history:
    max_trades: 10000
    retention_days: 365
    
  retrieval:
    k_neighbors: 5  # Number of similar trades to retrieve
    similarity_threshold: 0.75
```

## API Usage

```python
from yunmin.memory.vector_store import VectorStore
from yunmin.memory.trade_history import TradeHistory

# Initialize memory system
memory = TradeHistory(vector_store=VectorStore())

# Record a trade
await memory.record_trade(
    symbol="BTC/USDT",
    side="LONG",
    entry_price=50000,
    exit_price=51000,
    market_conditions={
        "rsi": 45,
        "trend": "bullish",
        "volatility": "low"
    },
    reasoning="RSI oversold + bullish trend confirmation",
    outcome="profit",
    pnl=1000
)

# Retrieve similar situations
similar_trades = await memory.find_similar(
    current_market={
        "rsi": 44,
        "trend": "bullish",
        "volatility": "low"
    },
    k=5
)

# Analyze past performance in similar conditions
success_rate = memory.get_success_rate(similar_trades)
```

## Benefits

- **Adaptive Strategy**: Agent learns what works in different market conditions
- **Risk Management**: Better position sizing based on historical performance
- **Confidence Calibration**: Adjust confidence scores using past accuracy
- **Pattern Recognition**: Identify high-probability setups
- **Continuous Improvement**: Performance improves over time

## Future Enhancements

- [ ] Multi-modal memory (technical + sentiment + news)
- [ ] Hierarchical memory structure (short/medium/long-term)
- [ ] Memory pruning strategies for efficiency
- [ ] Cross-asset pattern transfer learning
- [ ] Federated learning across multiple instances
