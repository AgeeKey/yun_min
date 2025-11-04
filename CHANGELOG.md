# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2025-11-04

### Added
- Initial YunMin trading bot framework
- Multi-exchange support (Binance via CCXT)
- EMA Crossover trading strategy
- Advanced risk management system with 6 policies:
  - Max position size (10% of capital)
  - Max leverage (3x)
  - Daily drawdown protection (5%)
  - Stop loss enforcement
  - Margin check
  - Circuit breaker (100 orders/day limit)
- Comprehensive backtesting engine
- Integration with Grok AI for strategy optimization
- Async WebSocket support
- Configuration management with Pydantic V2
- Test coverage for core modules

### Phase 1: Foundation ✅
- Project structure initialized
- Core modules: config, risk, strategy, execution
- Basic testing infrastructure
- Documentation (README, QUICKSTART, ARCHITECTURE)

### Phase 2: Development & Testing 🔄
#### Week 1 Complete ✅
- **V1 (2025-10-28)**: Initial dry run (0 trades)
  - Issue: RSI calculation bug caused no signal generation
  
- **V2 (2025-10-29)**: First successful test
  - Fix: RSI implementation corrected
  - Results: 2 trades executed
  
- **V3 (2025-11-03)**: Major discovery test
  - Duration: 2h 51min (2880 candles)
  - Total trades: 124 positions
  - **SHORT Performance**: 100% Win Rate (62/62 positions profitable)
  - **LONG Performance**: 38.7% Win Rate (24/62 profitable, 38 losses)
  - Key Finding: Asymmetric performance suggests directional bias issue
  
- **V4 (Planned)**: Grok AI Optimization
  - Implement asymmetric SL/TP ratios (SHORT: 1.5%, LONG: 3%)
  - Add trend filter to reduce choppy market exposure
  - Optimize RSI thresholds based on V3 data

### Technical Improvements
- **Python 3.13 Compatibility**: Fixed datetime.utcnow() deprecations (12 files)
- **Pydantic V2 Migration**: Updated all config classes to use ConfigDict
- **Async Testing**: Added pytest-asyncio support with proper configuration
- **Code Quality**: 100% passing tests (16/16)

### Bug Fixes
- Fixed RSI calculation causing signal generation failures
- Fixed Pydantic class-based config deprecation warnings
- Fixed Python 3.13 datetime.utcnow() deprecation (replaced with datetime.now(UTC))
- Fixed backtester API changes (generate_dummy_data → generate_sample_data)
- Fixed async test framework configuration

### Dependencies
- Core: ccxt, pandas, numpy, ta-lib, pandas-ta
- ML: scikit-learn, xgboost, lightgbm, torch, stable-baselines3
- LLM: openai, anthropic
- Database: sqlalchemy, redis, psycopg2-binary, faiss-cpu
- API: fastapi, uvicorn, pydantic
- Monitoring: prometheus-client, mlflow
- Dev: pytest, pytest-asyncio, pytest-cov, black, flake8, mypy

### Known Issues
- LONG position performance needs improvement (38.7% WR)
- Risk manager rejecting some valid orders due to precision rounding

### Next Steps (Phase 2, Week 2)
1. Implement V4 strategy improvements
2. Conduct 48h testnet validation
3. Live safety runbook preparation
4. Incident response planning

---

## Development Timeline

**Phase 1** (Complete): Framework setup, core modules  
**Phase 2** (In Progress): Development, testing, optimization  
**Phase 3** (Planned): Testnet deployment, monitoring  
**Phase 4** (Future): Live deployment, scaling  

---

*Generated with assistance from Grok AI by x.AI*
