# Yun Min (云敏) - Grok AI Trading Bot

<div align="center">

**Полностью автономный торговый бот на основе Grok AI**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Grok AI](https://img.shields.io/badge/Powered%20by-Grok%20AI-00ADD8.svg)](https://x.ai)

📊 **[V3 Test Results](docs/reports/v3-final-report.md)** | 📚 **[Architecture](ARCHITECTURE.md)** | 🚀 **[Quick Start](QUICKSTART.md)**

</div>

## 🎯 Overview

**Yun Min** - это полностью автономный торговый бот для криптовалютных фьючерсов, который использует **Grok AI** для принятия торговых решений в режиме реального времени. Система комбинирует технический анализ (RSI, EMA) с анализом рыночных трендов через Grok AI.

### ✨ Текущий статус (ноябрь 2025)

- ✅ **V3 тест завершён** (2ч 51мин работы)
- ✅ **124 позиции открыто**, 37 закрыто, 87 ожидают TP/SL
- ⚠️ **Обнаружена асимметрия**: SHORT 100% WR, LONG 38.7% WR
- 🔄 **V4 в разработке** (улучшенные параметры от Grok)

### 🔥 Key Features

### 🔥 Key Features

- 🤖 **Grok AI Decision Making**: Каждое решение принимается через Grok AI API
- 📊 **Technical Analysis**: RSI, EMA, волатильность, объём
- 🛡️ **Risk Management**: SL/TP на каждую позицию, максимум 10% капитала
- 🔄 **24/7 Autonomous Trading**: Полностью автономная работа
- 📈 **Real-time Monitoring**: База данных SQLite для отслеживания
- 🎯 **Futures Trading**: LONG/SHORT позиции на криптофьючерсах

## 🏗️ Architecture

```
yunmin/
├── data_ingest/     # Exchange connectivity, data fetching
├── features/        # Technical indicators, feature engineering
├── strategy/        # Trading strategies (rule-based + ML)
├── risk/            # Risk management policies and circuit breakers
├── execution/       # Order management (dry-run/paper/live)
├── backtester/      # Historical testing framework
├── ml/              # Machine learning models
├── llm/             # LLM integration for analysis
├── ui/              # Web dashboard and notifications
└── core/            # Configuration and utilities
```

## 🚀 Quick Start

### 1️⃣ Установка

```bash
# Clone repository
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2️⃣ Конфигурация

```bash
# Создайте .env файл с вашим Grok API ключом
echo GROK_API_KEY=your_key_here > .env
echo BINANCE_API_KEY=your_binance_key >> .env
echo BINANCE_SECRET=your_binance_secret >> .env
```

### 3️⃣ Запуск 24-часового теста

```powershell
# Запустить через PowerShell скрипт
.\Start-24h-DryRun.ps1

# Или напрямую через Python
python run_24h_dry_run.py
```

### 4️⃣ Мониторинг

```python
# Анализ базы данных
python -c "
import sqlite3
conn = sqlite3.connect('yunmin.db')
print(conn.execute('SELECT COUNT(*) FROM positions').fetchone())
conn.close()
"
```

## ⚙️ Configuration

### Ключевые параметры (V3 → V4)

**Текущие параметры V3:**
```yaml
LONG:  SL -2%, TP +3%
SHORT: SL -2%, TP +3%
Confidence: 50%
```

**Рекомендации Grok для V4:**
```yaml
LONG:  SL -3%, TP +4%  # Расширены из-за низкого WR
SHORT: SL -2%, TP +3%  # Без изменений (100% WR)
Confidence: 65%         # Повышен порог
```

### Environment Variables (.env)

```bash
# Grok AI
GROK_API_KEY=xai-xxxxxxxxx

# Binance
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# Trading
TRADING_SYMBOL=BTC/USDT
TIMEFRAME=5m
MAX_POSITIONS=10
```

## 📊 V3 Test Results

**Длительность:** 2h 51min (07:23 - 10:14, 4 ноября 2025)

**Статистика:**
- Всего позиций: 124 (77 LONG, 47 SHORT)
- Закрыто: 37 (48.6% WR)
- Открыто: 87 (ожидают SL/TP)
- Реализованный P&L: -$31.49

**Критическая находка:**
- **SHORT**: 6/6 wins (100%), +$27.83
- **LONG**: 12/31 wins (38.7%), -$59.32

**Вывод:** Стратегия работает, но требует асимметричных параметров

## 📚 Usage Examples

### Запуск 24-часового теста

```python
# run_24h_dry_run.py
from yunmin.strategy.grok_ai_strategy import GrokAIStrategy
from yunmin.connectors.binance_connector import BinanceConnector

# Инициализация
connector = BinanceConnector()
strategy = GrokAIStrategy()

# Запуск бесконечного цикла
while True:
    # 1. Получить данные
    market_data = connector.get_market_data('BTCUSDT', '5m')
    
    # 2. Спросить Grok AI
    decision = strategy.analyze(market_data)
    
    # 3. Выполнить решение
    if decision.action in ['LONG', 'SHORT']:
        connector.open_position(decision)
    
    time.sleep(300)  # 5 минут
```

### Анализ результатов

```python
import sqlite3
import pandas as pd

# Подключение к БД
conn = sqlite3.connect('yunmin.db')

# Статистика по сторонам
df = pd.read_sql("""
    SELECT side, 
           COUNT(*) as total,
           SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) as closed,
           AVG(realized_pnl) as avg_pnl
    FROM positions
    GROUP BY side
""", conn)

print(df)
```

### Grok AI интеграция

```python
from openai import OpenAI
import os

# Подключение к Grok
client = OpenAI(
    api_key=os.environ.get("GROK_API_KEY"),
    base_url="https://api.x.ai/v1"
)

# Запрос решения
response = client.chat.completions.create(
    model="grok-2-1212",
    messages=[{
        "role": "user",
        "content": f"Analyze: RSI={rsi}, Price={price}, Trend={trend}"
    }]
)

decision = response.choices[0].message.content
```

## 🎯 Roadmap

### ✅ Completed (V1-V3)
- [x] Grok AI integration
- [x] RSI + EMA indicators
- [x] Database persistence (SQLite)
- [x] Position tracking (OPEN/CLOSED)
- [x] SL/TP automatic management
- [x] 24h autonomous testing

### 🔄 In Progress (V4)
- [ ] Asymmetric SL/TP parameters
- [ ] Higher confidence threshold (65%)
- [ ] Trend detection filter
- [ ] MACD/Bollinger Bands for LONG

### 🚀 Future
- [ ] Real trading on Binance
- [ ] Multi-pair support
- [ ] Telegram notifications
- [ ] Web dashboard

## 📄 License

MIT License - see [LICENSE](LICENSE)

## 🤝 Contributing

Вклад приветствуется! Пожалуйста:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📞 Contact

- Issues: [GitHub Issues](https://github.com/AgeeKey/yun_min/issues)
- Author: AgeeKey

---

**⚠️ DISCLAIMER**: Это экспериментальный проект. Торговля криптовалютой несёт высокий риск. Используйте только средства, которые можете потерять.


### Metrics

Key metrics tracked:
- PnL (Profit and Loss)
- Win rate
- Maximum drawdown
- Sharpe ratio
- Order fill rates
- Latency

## 🛣️ Roadmap

- [x] Core architecture and configuration
- [x] Exchange adapter (CCXT)
- [x] Risk management system
- [x] EMA crossover strategy
- [x] Order execution (dry-run/paper/live)
- [x] Binance connector
- [x] Order tracking system
- [x] Backtesting engine
- [x] Production deployment guides
- [ ] ML model integration
- [ ] LLM assistant integration
- [ ] Web dashboard UI
- [ ] Telegram notifications
- [ ] Database persistence
- [ ] Multi-strategy support
- [ ] Portfolio management

## 📚 Documentation

### Main Documentation
- 📖 [README.md](README.md) - Quick start and overview
- 📊 [Project Overview](docs/project-overview.md) - Comprehensive project overview
- 🏗️ [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- 🚀 [QUICKSTART.md](QUICKSTART.md) - 5-minute setup guide
- 🔗 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Integration patterns
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

### Production Documentation (docs/)
- 🚨 [Alert Rules](docs/advanced/alert-rules.md) - Alert configuration
- 🔒 [Live Safety Runbook](docs/advanced/runbook-live-safety.md) - Live trading safety
- 🚀 [Deployment Guide](docs/deployment/deployment-guide.md) - Deployment guide
- 🆘 [Incident Response](docs/deployment/incident-response.md) - Incident response
- 📊 [Monitoring Dashboard](docs/deployment/monitoring-dashboard.md) - Monitoring setup
- 📈 [Scaling Roadmap](docs/deployment/scaling.md) - Scaling roadmap
- 📜 [Attribution](docs/reports/attribution.md) - License attribution

## ⚠️ Disclaimer

**WARNING: Trading cryptocurrencies involves substantial risk of loss and is not suitable for every investor. This software is for educational purposes only.**

- Past performance does not guarantee future results
- Always test strategies thoroughly in dry-run and paper trading modes
- Never invest more than you can afford to lose
- This software comes with NO WARRANTY
- The developers are not responsible for any financial losses

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📧 Contact

- GitHub: [@AgeeKey](https://github.com/AgeeKey)
- Issues: [GitHub Issues](https://github.com/AgeeKey/yun_min/issues)

---

<div align="center">

**Built with ❤️ for the crypto trading community**

⭐ Star us on GitHub if you find this useful!

</div>