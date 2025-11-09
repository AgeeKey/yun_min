# Autonomous AI Trading Agent Architecture

## 🎯 Overview

YunMin has been transformed from a simple bot with LLM advisor into a **true autonomous AI trading agent** with:

- **Memory**: Vector database (RAG) for learning from past trades
- **Multi-modal context**: 500+ candles, orderbook, correlations
- **Chain-of-thought reasoning**: Transparent step-by-step decisions
- **Multi-agent system**: Specialized agents for different tasks
- **Portfolio management**: Multi-asset allocation (3-5 coins)
- **Learning**: Continuous improvement from experience

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Autonomous AI Trading Agent                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐│
│  │  Memory   │  │ Context   │  │ Reasoning │  │ Learning ││
│  │  System   │  │ Builders  │  │  Engine   │  │  System  ││
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘│
│        │              │              │              │       │
│        └──────────────┴──────────────┴──────────────┘       │
│                          │                                   │
│                          ▼                                   │
│        ┌─────────────────────────────────────┐              │
│        │         AI Agents Layer             │              │
│        ├─────────────────────────────────────┤              │
│        │  Market    Risk      Portfolio      │              │
│        │  Analyst │ Assessor │ Manager       │              │
│        │  Agent   │ Agent    │ Agent         │              │
│        │          │          │               │              │
│        │         Execution Agent             │              │
│        └─────────────────────────────────────┘              │
│                          │                                   │
│                          ▼                                   │
│        ┌─────────────────────────────────────┐              │
│        │      Integration Layer              │              │
│        ├─────────────────────────────────────┤              │
│        │  Binance  │  Risk    │  Database   │              │
│        │  Connector│  Manager │  Models     │              │
│        └─────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Directory Structure

```
yunmin/
├── agents/                    # 🆕 AI Agents
│   ├── market_analyst.py     # Market analysis with chain-of-thought
│   ├── risk_assessor.py      # Risk evaluation & position sizing
│   ├── portfolio_manager.py  # Multi-asset portfolio management
│   └── execution_agent.py    # Smart order execution (TWAP/VWAP)
│
├── memory/                    # 🆕 Memory System (RAG)
│   ├── vector_store.py       # Vector database (FAISS)
│   ├── trade_history.py      # Trade history with embeddings
│   └── pattern_library.py    # Recurring patterns database
│
├── context/                   # 🆕 Context Builders
│   ├── market_data.py        # Multi-timeframe candles, indicators
│   ├── orderbook.py          # Order book depth analysis
│   └── correlations.py       # Cross-asset correlations
│
├── reasoning/                 # 🆕 Reasoning Engine
│   ├── chain_of_thought.py   # Step-by-step reasoning
│   ├── ensemble.py           # Multi-agent consensus
│   └── confidence.py         # Confidence calibration
│
├── learning/                  # 🆕 Learning System
│   ├── backtest_analyzer.py  # Extract insights from history
│   └── strategy_optimizer.py # Parameter optimization
│
└── [existing modules]         # ✅ Preserved
    ├── connectors/            # Exchange connectivity
    ├── risk/                  # Risk management
    ├── store/                 # Database models
    └── core/                  # Configuration
```

## 🚀 Quick Start

### Installation

```bash
# Install YunMin with new dependencies
pip install -e .

# Optional: Install FAISS for faster vector search
pip install faiss-cpu
```

### Basic Usage

```python
import asyncio
from examples.ai_agent_demo import AutonomousAITradingAgent

# Create agent
agent = AutonomousAITradingAgent()

# Run single trading cycle
await agent.trading_loop('BTC/USDT')

# Run continuous trading
await agent.run_continuous(['BTC/USDT', 'ETH/USDT'], interval=300)
```

### Running the Demo

```bash
python examples/ai_agent_demo.py
```

## 🧠 Key Components

### 1. Memory System (RAG)

**Vector Store**: Similarity search for finding similar past situations
```python
from yunmin.memory.vector_store import VectorStore

store = VectorStore(embedding_dim=384)
store.add(embedding, metadata={'trade': 'details'})
results = store.search(query_embedding, k=5)
```

**Trade History**: Remember and recall past trades
```python
from yunmin.memory.trade_history import TradeHistory

history = TradeHistory()
history.remember_trade(context, decision, outcome)
similar = history.recall_similar(current_context, top_k=5)
```

**Pattern Library**: Store recurring market patterns
```python
from yunmin.memory.pattern_library import PatternLibrary, PatternType

library = PatternLibrary()
library.add_pattern(PatternType.BREAKOUT, context, outcome)
stats = library.get_pattern_statistics(PatternType.BREAKOUT)
```

### 2. AI Agents

**Market Analyst**: Analyzes market with chain-of-thought reasoning
```python
from yunmin.agents.market_analyst import MarketAnalystAgent

analyst = MarketAnalystAgent()
result = await analyst.analyze(market_context, risk_tolerance=0.7)
# Returns: {decision, confidence, reasoning_chain}
```

**Risk Assessor**: Evaluates trade risk and calculates position size
```python
from yunmin.agents.risk_assessor import RiskAssessorAgent

assessor = RiskAssessorAgent(max_position_size=0.1)
result = assessor.evaluate(proposed_trade, market_context, portfolio)
# Returns: {risk_score, recommended_position_size, approved}
```

**Portfolio Manager**: Manages multi-asset portfolio
```python
from yunmin.agents.portfolio_manager import PortfolioManagerAgent

manager = PortfolioManagerAgent(max_assets=5)
allocation = manager.allocate(trade_proposal, market_context, portfolio)
# Returns: {approved, size, amount, priority}
```

**Execution Agent**: Smart order execution
```python
from yunmin.agents.execution_agent import ExecutionAgent

executor = ExecutionAgent(default_strategy='adaptive')
result = await executor.execute(allocation, market_context)
# Supports: immediate, TWAP, VWAP, iceberg, adaptive
```

### 3. Context Builders

**Market Data Provider**: Multi-timeframe candles and indicators
```python
from yunmin.context.market_data import MarketDataProvider

provider = MarketDataProvider()
context = await provider.fetch_market_context('BTC/USDT')
# Includes: 500+ candles, RSI, MACD, EMA, Bollinger, support/resistance
```

**Order Book Analyzer**: Liquidity and depth analysis
```python
from yunmin.context.orderbook import OrderBookAnalyzer

analyzer = OrderBookAnalyzer()
analysis = await analyzer.analyze('BTC/USDT', depth=50)
# Returns: {bid_depth, ask_depth, imbalance, liquidity_score, price_walls}
```

### 4. Reasoning Engine

**Chain of Thought**: Transparent step-by-step reasoning
```python
from yunmin.reasoning.chain_of_thought import ChainOfThoughtReasoning

reasoning = ChainOfThoughtReasoning()
result = reasoning.reason(market_context, analyst_output, risk_assessment, memory)
# Steps: Observe → Analyze → Recall → Hypothesize → Evaluate → Decide
```

**Ensemble**: Multi-agent consensus
```python
from yunmin.reasoning.ensemble import EnsembleDecisionMaker

ensemble = EnsembleDecisionMaker(method='confidence')
final_decision = ensemble.decide([decision1, decision2, decision3])
# Methods: voting, weighted, confidence-based
```

### 5. Learning System

**Backtest Analyzer**: Extract insights from trading history
```python
from yunmin.learning.backtest_analyzer import BacktestAnalyzer

analyzer = BacktestAnalyzer()
performance = analyzer.analyze_performance()
patterns = analyzer.find_winning_patterns()
mistakes = analyzer.find_common_mistakes()
```

## 📊 Trading Loop Flow

```python
# 1. Build Context
context = await market_data.fetch_market_context('BTC/USDT')
orderbook = await orderbook_analyzer.analyze('BTC/USDT')

# 2. Market Analysis (with memory)
analysis = await market_analyst.analyze(context)

# 3. Chain-of-Thought Reasoning
reasoning_result = reasoning.reason(context, analysis, risk_result, memory)

# 4. Risk Assessment
risk_result = risk_assessor.evaluate(analysis, context, portfolio)

# 5. Portfolio Allocation (if approved)
if risk_result['approved']:
    allocation = portfolio_manager.allocate(analysis, context, portfolio)
    
    # 6. Execution (if allocated)
    if allocation['approved']:
        execution = await execution_agent.execute(allocation, context)
        
        # 7. Remember Trade
        trade_id = trade_history.remember_trade(context, analysis, None)
```

## 🧪 Testing

Run comprehensive tests:

```bash
# All tests
pytest tests/

# Specific modules
pytest tests/memory/
pytest tests/agents/
pytest tests/reasoning/
pytest tests/integration/

# With coverage
pytest tests/ --cov=yunmin --cov-report=html
```

## 💰 Cost Estimation

Using GPT-4o-mini (2.5M tokens/day FREE tier):

```
Market Analyst:  ~500 tokens/analysis × 1440/day = 720k tokens
Risk Assessor:   ~200 tokens × 100 trades/day  = 20k tokens
Portfolio Mgr:   ~300 tokens × 10 decisions/day = 3k tokens
─────────────────────────────────────────────────────────────
TOTAL:           ~750k tokens/day (30% of free tier)
```

**Embeddings** (for memory): ~$0.065 per 1000 trades (practically free)

**Infrastructure**: All free (FAISS local, PostgreSQL local, Binance testnet)

## 📈 Expected Results

### After 1 Month:
- ✅ 1000+ trades in memory
- ✅ Identified profitable patterns
- ✅ 60%+ win rate (realistic goal)
- ✅ Multi-asset portfolio (3-5 coins)
- ✅ 20-30 trades/day (not 1440!)

### After 3 Months:
- ✅ Reinforcement learning integration
- ✅ Adaptation to market regime changes
- ✅ Ready for real money (small amounts)

## 🔧 Configuration

Key settings in `config/default.yaml`:

```yaml
ai_agents:
  market_analyst:
    model: "gpt-4o-mini"
    risk_tolerance: 0.7
  
  risk_assessor:
    max_position_size: 0.1
    max_leverage: 3.0
  
  portfolio_manager:
    max_assets: 5
    max_total_exposure: 0.5
  
  memory:
    embedding_model: "simple"  # or "openai"
    storage_path: "data/vector_store"
```

## 🤝 Integration with Existing Code

The new architecture **preserves all existing components**:

- ✅ Binance connector still used for market data
- ✅ Risk manager still enforces limits
- ✅ Config system still loads settings
- ✅ Database models still store trades
- ✅ CLI interface still works

Old strategies can coexist with new AI agents:

```python
# Old strategy still works
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
strategy = GrokAIStrategy()

# New AI agent can be used alongside
from yunmin.agents.market_analyst import MarketAnalystAgent
analyst = MarketAnalystAgent()
```

## 📚 Examples

See `examples/` directory:

- **ai_agent_demo.py**: Complete autonomous agent demo
- **advanced_ai_framework_example.py**: Existing ML integration
- **ml_integration_demo.py**: Machine learning examples

## 🐛 Troubleshooting

### FAISS not available
```python
# Vector store falls back to simple storage automatically
store = VectorStore(use_faiss=False)
```

### OpenAI API key not set
```python
# Agents fall back to rule-based logic
analyst = MarketAnalystAgent()  # Works without API key
```

### Memory persistence
```python
# Save memory periodically
trade_history.save()
pattern_library.save()
```

## 🔒 Security Notes

- Never commit API keys to git
- Use testnet for development
- Start with small position sizes
- Monitor agent decisions closely
- Set strict risk limits

## 📖 Further Reading

- [Architecture Overview](overview.md) - Overall system design
- [Memory System](memory-system.md) - Learn about the memory system
- [AI Strategies](../strategies/ai-strategies.md) - Strategy documentation

## 🙋 Support

For questions or issues:
- Open an issue on GitHub
- Check existing documentation
- Review test files for usage examples

---

**Built with ❤️ by the YunMin team**
