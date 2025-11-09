# AI-Powered Strategies

## Overview

YunMin V4 uses autonomous AI agents powered by Large Language Models (LLMs) to make trading decisions. Unlike traditional rule-based strategies, AI strategies can:

- Analyze complex market conditions
- Learn from past trades via memory system (RAG)
- Provide transparent reasoning for each decision
- Adapt to changing market conditions
- Coordinate multiple specialized agents

## Available AI Strategies

### AI V4 - Multi-Agent Ensemble (Recommended)

The latest and most advanced AI strategy using a multi-agent architecture.

**Features:**
- **Market Analyst Agent**: Analyzes trends, patterns, and indicators
- **Risk Assessor Agent**: Evaluates position sizing and risk metrics
- **Portfolio Manager Agent**: Manages multi-asset allocation
- **Execution Agent**: Handles smart order execution (TWAP/VWAP)
- **Memory System**: Learns from past trades using RAG
- **Chain-of-Thought**: Provides step-by-step reasoning

**Configuration:**
```yaml
strategy:
  type: ai_agent
  ai_agent:
    model: grok-2-1212
    min_confidence: 0.65
    use_memory: true
    lookback_candles: 500
    agents:
      - market_analyst
      - risk_assessor
      - portfolio_manager
      - execution_agent
```

**Usage:**
```python
from yunmin.strategy.ai_agent_strategy import AIAgentStrategy

strategy = AIAgentStrategy(
    model="grok-2-1212",
    min_confidence=0.65,
    use_memory=True
)

# Get trading decision
decision = await strategy.analyze(market_data)
```

### AI V3 - Grok/GPT Single Agent

A simpler single-agent approach using Grok or GPT models.

**Features:**
- Single LLM decision maker
- RSI, EMA, and volume analysis
- Basic risk management
- Fast execution

**Configuration:**
```yaml
strategy:
  type: ai_v3
  ai_v3:
    model: grok-2-1212  # or gpt-4, claude-3-opus
    min_confidence: 0.50
    indicators:
      - rsi
      - ema
      - volume
```

## How AI Strategies Work

### 1. Data Collection

The strategy gathers:
- **Price data**: 500+ candles across multiple timeframes
- **Technical indicators**: RSI, EMA, MACD, Bollinger Bands
- **Order book**: Bid/ask depth, market pressure
- **Market context**: Volatility, volume, correlations
- **Historical trades**: Similar past situations from memory

### 2. Context Building

All data is structured into a comprehensive context:

```python
{
    "current_price": 50000,
    "timeframe": "5m",
    "indicators": {
        "rsi_14": 45,
        "ema_20": 49800,
        "ema_50": 49500,
        "macd": {"value": 120, "signal": 100},
        "bbands": {"upper": 51000, "middle": 50000, "lower": 49000}
    },
    "market_conditions": {
        "trend": "bullish",
        "volatility": "medium",
        "volume_profile": "increasing"
    },
    "orderbook": {
        "bid_depth": 1500000,
        "ask_depth": 1200000,
        "imbalance": 0.25
    },
    "similar_trades": [
        {"date": "2024-10-15", "outcome": "profit", "pnl": 500},
        {"date": "2024-10-10", "outcome": "profit", "pnl": 300}
    ]
}
```

### 3. AI Analysis

The AI agent(s) analyze the context using chain-of-thought reasoning:

```
Step 1: Market Analysis
- BTC is in an uptrend (EMA 20 > EMA 50)
- RSI at 45 suggests not overbought
- Volume increasing, confirming trend

Step 2: Risk Assessment
- Current volatility is medium
- Stop loss would be at $49,000 (-2%)
- Take profit at $51,500 (+3%)
- Risk/reward ratio: 1:1.5

Step 3: Memory Consultation
- Found 5 similar situations in history
- 4 out of 5 resulted in profit
- Average profit: $400

Step 4: Decision
- RECOMMENDATION: LONG
- CONFIDENCE: 75%
- POSITION SIZE: 10% of capital
- REASONING: Strong uptrend + bullish indicators + positive historical precedent
```

### 4. Decision Execution

Based on the AI's decision and confidence level:
- If confidence >= threshold → Execute trade
- If confidence < threshold → Wait for better setup
- Log reasoning for future learning

### 5. Learning Loop

After trade closure:
- Record outcome in memory system
- Update success patterns
- Adjust confidence calibration
- Improve future decisions

## AI Model Options

### Grok (x.AI)

**Pros:**
- Fast response time
- Good at market analysis
- Cost-effective
- Real-time data integration

**Cons:**
- Requires Grok API key
- Limited availability

**Configuration:**
```python
GROK_API_KEY=xai-xxxxxxxxxx
model: grok-2-1212
```

### GPT-4 (OpenAI)

**Pros:**
- Excellent reasoning
- Large context window
- Proven track record

**Cons:**
- Higher cost
- Rate limits
- Slower response

**Configuration:**
```python
OPENAI_API_KEY=sk-xxxxxxxxxx
model: gpt-4-turbo
```

### Claude 3 (Anthropic)

**Pros:**
- Best reasoning capabilities
- Large context window (200k tokens)
- Good at following instructions

**Cons:**
- Most expensive
- API availability

**Configuration:**
```python
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxx
model: claude-3-opus-20240229
```

## Performance Optimization

### Reduce API Calls

```yaml
strategy:
  ai_agent:
    # Only call AI when conditions change significantly
    min_change_threshold: 0.005  # 0.5%
    
    # Cache decisions for N candles
    cache_duration: 3
    
    # Use local filtering before AI
    pre_filters:
      - volume_threshold
      - volatility_range
```

### Batch Processing

Process multiple pairs in one API call:

```python
decisions = await strategy.analyze_batch([
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT"
])
```

## Testing AI Strategies

### Backtesting

```bash
python run_v4_backtest.py \
    --strategy ai_agent \
    --start-date 2024-01-01 \
    --end-date 2024-12-31 \
    --symbol BTC/USDT
```

### Paper Trading

```bash
python run_testnet.py \
    --strategy ai_agent \
    --mode paper \
    --duration 24h
```

### Live Testing

```bash
# Start with small capital
python run_testnet.py \
    --strategy ai_agent \
    --mode live \
    --capital 100
```

## Best Practices

1. **Start with paper trading** - Test thoroughly before going live
2. **Monitor API costs** - AI calls can be expensive at high frequency
3. **Set confidence thresholds** - Higher threshold = fewer but better trades
4. **Use memory system** - Enable learning from past trades
5. **Review reasoning logs** - Understand why AI makes decisions
6. **Combine with rules** - Add safety filters (max drawdown, daily loss limit)
7. **Regular evaluation** - Review and adjust parameters weekly

## Troubleshooting

### Low Confidence Scores

- **Increase lookback period**: More data for analysis
- **Improve context quality**: Add more indicators
- **Tune confidence threshold**: Lower threshold for more trades

### High API Costs

- **Reduce call frequency**: Analyze every N candles
- **Use caching**: Cache recent decisions
- **Add pre-filters**: Only call AI for promising setups

### Inconsistent Results

- **Enable memory system**: Learn from experience
- **Use ensemble**: Multiple agents provide consensus
- **Add reasoning validation**: Check if reasoning is sound

## Next Steps

- [Creating Custom Strategies](custom-strategy.md) - Build your own AI strategy
- [Backtesting](backtesting.md) - Test AI strategies historically
