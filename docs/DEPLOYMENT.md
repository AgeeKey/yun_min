# YunMin Production Deployment Guide

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Health Checks](#health-checks)
- [Rollback Procedure](#rollback-procedure)
- [Monitoring Setup](#monitoring-setup)

---

## Prerequisites

### System Requirements
- **Python**: 3.11 or 3.13
- **RAM**: Minimum 4GB, recommended 8GB+
- **Disk**: 20GB+ for logs, database, and backups
- **Network**: Stable connection with <100ms latency to exchange

### Required Accounts
- **Binance**: API keys with trading permissions (testnet for staging)
- **Telegram**: Bot token (optional, for alerts)
- **Email**: SMTP credentials (optional, for alerts)

### Dependencies
```bash
pip install -r requirements.txt
```

---

## Environment Setup

### 1. Create Production Environment

```bash
# Create virtual environment
python -m venv venv-prod

# Activate (Linux/Mac)
source venv-prod/bin/activate

# Activate (Windows)
venv-prod\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Environment Variables

Create `.env` file in project root:

```bash
# Exchange Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=false  # Set to true for testnet

# Alert Configuration
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
ALERT_EMAIL=alerts@yourcompany.com

# Webhook (optional)
WEBHOOK_URL=https://your-webhook-endpoint.com/alerts

# Database
DB_PATH=./data/yunmin_prod.db

# Logging
LOG_LEVEL=INFO
LOG_PATH=./logs/yunmin.log
```

---

## Configuration

### 1. Trading Configuration (`config/production.yaml`)

```yaml
# Trading Engine
trading:
  mode: "live"  # "dry_run" | "live"
  symbol: "BTC/USDT"
  timeframe: "5m"
  initial_capital: 10000
  max_position_size: 5000  # 50% of capital
  
# Risk Management
risk:
  max_position_pct: 0.50  # 50%
  max_daily_loss: 500     # $500
  max_open_positions: 3
  stop_loss_pct: 0.02     # 2%
  take_profit_pct: 0.05   # 5%
  
# Strategy Parameters
strategy:
  name: "MomentumStrategy"
  params:
    rsi_period: 14
    rsi_oversold: 30
    rsi_overbought: 70
    volume_threshold: 1.5
    
# Alerts
alerts:
  enabled: true
  channels:
    - telegram
    - email
    - log
  rate_limit_seconds: 60
  levels:
    - ERROR
    - CRITICAL
    
# Error Recovery
recovery:
  max_retries: 3
  initial_backoff_seconds: 1
  max_backoff_seconds: 60
  exponential_base: 2
  
# Persistence
persistence:
  enabled: true
  db_path: "./data/yunmin_prod.db"
  checkpoint_interval_seconds: 300  # 5 min
```

### 2. Validate Configuration

```bash
# Test configuration loading
python -c "from yunmin.core.config import load_config; print(load_config('config/production.yaml'))"
```

---

## Deployment Steps

### Step 1: Pre-Deployment Checks

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Check code quality
pylint yunmin/

# 3. Verify environment variables
python -c "import os; assert os.getenv('BINANCE_API_KEY'), 'API key missing'"

# 4. Test exchange connectivity
python examples/test_exchange_connection.py
```

### Step 2: Database Setup

```bash
# Initialize production database
python -c "from yunmin.store.sqlite_store import SQLiteStore; store = SQLiteStore('./data/yunmin_prod.db'); store.initialize()"

# Verify database
sqlite3 data/yunmin_prod.db ".tables"
# Expected: positions, trades, portfolio_snapshots, bot_state, alerts
```

### Step 3: Dry Run Testing (Recommended)

```bash
# Run in dry-run mode for 24 hours before going live
python yunmin/bot.py --config config/production.yaml --dry-run

# Monitor logs
tail -f logs/yunmin.log
```

### Step 4: Go Live

```bash
# Start production bot
python yunmin/bot.py --config config/production.yaml --live

# Or use CLI
yunmin run --config config/production.yaml --live
```

### Step 5: Process Management (Production)

Use `systemd` for automatic restart and management:

**Create `/etc/systemd/system/yunmin.service`:**

```ini
[Unit]
Description=YunMin Trading Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/yunmin
Environment="PATH=/path/to/venv-prod/bin"
ExecStart=/path/to/venv-prod/bin/python yunmin/bot.py --config config/production.yaml --live
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**

```bash
sudo systemctl enable yunmin
sudo systemctl start yunmin
sudo systemctl status yunmin
```

---

## Health Checks

### 1. Application Health

```bash
# Check if bot is running
ps aux | grep yunmin

# Check logs for errors
tail -n 100 logs/yunmin.log | grep ERROR

# Check database connectivity
sqlite3 data/yunmin_prod.db "SELECT COUNT(*) FROM trades;"
```

### 2. Exchange Connectivity

```python
from yunmin.connectors.binance_connector import BinanceConnector

connector = BinanceConnector(testnet=False)
balance = connector.get_balance()
print(f"USDT Balance: {balance['USDT']}")
```

### 3. Alert System Test

```python
from yunmin.core.alert_manager import AlertManager, AlertConfig

config = AlertConfig(telegram_enabled=True)
manager = AlertManager(config)
await manager.send_info("Health check test")
```

---

## Rollback Procedure

### Immediate Stop

```bash
# Stop the bot
sudo systemctl stop yunmin

# Or kill process
pkill -f "yunmin/bot.py"
```

### Close All Positions (Emergency)

```python
from yunmin.connectors.binance_connector import BinanceConnector

connector = BinanceConnector(testnet=False)
positions = connector.get_open_positions()

for pos in positions:
    connector.close_position(pos['symbol'], pos['size'])
```

### Restore from Backup

```bash
# Restore database
cp data/backups/yunmin_prod_YYYYMMDD.db data/yunmin_prod.db

# Restart bot
sudo systemctl start yunmin
```

---

## Monitoring Setup

### 1. Log Monitoring

```bash
# Real-time log monitoring
tail -f logs/yunmin.log

# Search for errors
grep -i error logs/yunmin.log

# Daily log rotation (cron)
0 0 * * * /path/to/rotate_logs.sh
```

**`rotate_logs.sh`:**
```bash
#!/bin/bash
cd /path/to/yunmin
mv logs/yunmin.log logs/yunmin_$(date +%Y%m%d).log
touch logs/yunmin.log
find logs/ -name "yunmin_*.log" -mtime +30 -delete
```

### 2. Performance Metrics

```python
# Daily performance report
from yunmin.reports.report_generator import ReportGenerator

generator = ReportGenerator(db_path="./data/yunmin_prod.db")
report = generator.generate_daily_report()
print(report)
```

### 3. Alert Configuration

Ensure alerts are configured for:
- ✅ Position opened/closed
- ✅ Risk limits exceeded
- ✅ Connection lost
- ✅ Critical errors
- ✅ Daily P&L summary

---

## Security Best Practices

### 1. API Key Security
- ✅ Never commit API keys to git
- ✅ Use environment variables or encrypted vault
- ✅ Restrict IP whitelist on Binance
- ✅ Use read-only keys for monitoring

### 2. Server Hardening
- ✅ SSH key-only authentication
- ✅ Firewall rules (allow only necessary ports)
- ✅ Regular security updates
- ✅ Encrypted database backups

### 3. Access Control
- ✅ Separate user for bot process
- ✅ Limit file permissions (chmod 600 .env)
- ✅ Audit logs for unauthorized access

---

## Troubleshooting

### Bot Won't Start
```bash
# Check config syntax
python -c "import yaml; yaml.safe_load(open('config/production.yaml'))"

# Check dependencies
pip check

# Check logs
cat logs/yunmin.log
```

### No Trades Executing
- Check dry-run mode is disabled
- Verify exchange connectivity
- Check risk limits (may be blocking trades)
- Review strategy signals in logs

### High Memory Usage
```bash
# Monitor memory
top -p $(pgrep -f yunmin)

# Reduce data retention in config
# Set shorter checkpoint intervals
```

### Connection Errors
- Check network connectivity
- Verify API keys are valid
- Check Binance service status
- Review rate limits

---

## Post-Deployment Checklist

- [ ] Bot is running (`systemctl status yunmin`)
- [ ] Logs are being written
- [ ] Database is updating
- [ ] Alerts are delivering (test with send_info)
- [ ] Exchange connectivity confirmed
- [ ] Risk limits configured correctly
- [ ] Monitoring dashboard accessible
- [ ] Backup cron job scheduled
- [ ] Team notified of deployment
- [ ] Runbook reviewed

---

## Support Contacts

- **On-Call Engineer**: your-name@company.com
- **Exchange Support**: Binance support portal
- **Emergency Shutdown**: Run `emergency_stop.sh`

---

**Last Updated**: 2024-12-20  
**Version**: 1.0  
**Maintained by**: YunMin DevOps Team
