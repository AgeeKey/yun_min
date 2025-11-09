# YunMin Operations Runbook

## Daily Operations Checklist

### Morning Routine (Before Market Open)

- [ ] Check bot status: `systemctl status yunmin`
- [ ] Review overnight logs: `tail -n 200 logs/yunmin.log | grep -i error`
- [ ] Check open positions: `sqlite3 data/yunmin_prod.db "SELECT * FROM positions WHERE status='OPEN';"`
- [ ] Verify account balance matches expected
- [ ] Check alert delivery (Telegram, email)
- [ ] Review daily P&L report

### Mid-Day Check

- [ ] Monitor active trades
- [ ] Check CPU/memory usage: `top -p $(pgrep -f yunmin)`
- [ ] Review risk exposure
- [ ] Verify no stuck orders

### End-of-Day Routine

- [ ] Generate daily report
- [ ] Backup database
- [ ] Review performance metrics
- [ ] Check for any anomalies
- [ ] Update trading journal

---

## Common Commands

### Bot Management

```bash
# Start bot
sudo systemctl start yunmin

# Stop bot
sudo systemctl stop yunmin

# Restart bot
sudo systemctl restart yunmin

# Check status
sudo systemctl status yunmin

# View logs (real-time)
tail -f logs/yunmin.log

# View last 100 lines
tail -n 100 logs/yunmin.log
```

### Database Queries

```bash
# Open database
sqlite3 data/yunmin_prod.db

# Check all tables
.tables

# View recent trades
SELECT * FROM trades ORDER BY timestamp DESC LIMIT 10;

# Check open positions
SELECT * FROM positions WHERE status='OPEN';

# Calculate total P&L
SELECT SUM(pnl) as total_pnl FROM trades WHERE DATE(timestamp) = DATE('now');

# Exit
.quit
```

### Performance Monitoring

```bash
# Generate daily report
python -c "from yunmin.reports.report_generator import ReportGenerator; r = ReportGenerator('./data/yunmin_prod.db'); print(r.generate_daily_report())"

# Check win rate
python -c "from yunmin.reports.report_generator import ReportGenerator; r = ReportGenerator('./data/yunmin_prod.db'); print(f'Win rate: {r.calculate_win_rate():.1f}%')"

# View equity curve
python examples/plot_equity_curve.py
```

---

## Alert Management

### Test Alert Delivery

```python
import asyncio
from yunmin.core.alert_manager import AlertManager, AlertConfig

config = AlertConfig(
    telegram_enabled=True,
    email_enabled=True,
    log_enabled=True
)

manager = AlertManager(config)
await manager.send_info("Test alert - system operational")
```

### Configure Alert Levels

Edit `config/production.yaml`:

```yaml
alerts:
  enabled: true
  channels:
    - telegram  # Primary
    - email     # Backup
    - log       # Always enabled
  rate_limit_seconds: 60  # Prevent spam
  levels:
    - INFO      # General updates
    - WARNING   # Risk warnings
    - ERROR     # Trade errors
    - CRITICAL  # System failures
```

### Common Alerts

| Alert Type | Level | Meaning | Action Required |
|------------|-------|---------|-----------------|
| Position Opened | INFO | New trade entered | Monitor |
| Position Closed | INFO | Trade exited | Review P&L |
| Risk Limit Hit | WARNING | Max position/loss reached | Review risk settings |
| Connection Lost | ERROR | Exchange disconnected | Check network |
| Critical Error | CRITICAL | System failure | Immediate investigation |

---

## Risk Management

### Check Current Exposure

```python
from yunmin.risk.manager import RiskManager
from yunmin.store.sqlite_store import SQLiteStore

store = SQLiteStore('./data/yunmin_prod.db')
risk_mgr = RiskManager(
    max_position_pct=0.50,
    max_daily_loss=500
)

exposure = risk_mgr.calculate_exposure(store.get_open_positions())
print(f"Current exposure: ${exposure:.2f}")
```

### Update Risk Limits

```bash
# Edit config
nano config/production.yaml

# Update risk section
risk:
  max_position_pct: 0.40  # Reduce from 50% to 40%
  max_daily_loss: 300     # Reduce from $500 to $300

# Restart bot to apply
sudo systemctl restart yunmin
```

### Emergency Stop

```bash
# Immediate stop (all positions remain open)
sudo systemctl stop yunmin

# Close all positions (manual)
python scripts/close_all_positions.py

# Or use exchange web interface
# Login to Binance > Close all positions manually
```

---

## Troubleshooting Guide

### Bot Not Starting

**Symptoms**: `systemctl status yunmin` shows "failed" or "inactive"

**Diagnosis**:
```bash
# Check logs
journalctl -u yunmin -n 50

# Check config syntax
python -c "import yaml; yaml.safe_load(open('config/production.yaml'))"

# Check dependencies
pip check
```

**Solutions**:
1. Fix config syntax errors
2. Install missing dependencies: `pip install -r requirements.txt`
3. Check API keys in `.env`
4. Verify database exists: `ls -lh data/yunmin_prod.db`

---

### No Trades Executing

**Symptoms**: Bot running but no trades for extended period

**Diagnosis**:
```bash
# Check strategy signals
grep "Signal:" logs/yunmin.log | tail -n 20

# Check risk blocks
grep "Risk check failed" logs/yunmin.log | tail -n 20

# Check dry-run mode
grep "dry_run" config/production.yaml
```

**Solutions**:
1. Verify `mode: "live"` in config (not "dry_run")
2. Check risk limits not too restrictive
3. Review market conditions (strategy may be avoiding trades)
4. Check balance sufficient for trades

---

### Exchange Connection Errors

**Symptoms**: "Connection lost" alerts, timeout errors in logs

**Diagnosis**:
```bash
# Test network
ping api.binance.com

# Test exchange connectivity
python -c "from yunmin.connectors.binance_connector import BinanceConnector; c = BinanceConnector(); print(c.get_server_time())"

# Check rate limits
grep "429" logs/yunmin.log  # HTTP 429 = rate limit
```

**Solutions**:
1. Check internet connection
2. Verify API keys valid (not expired/revoked)
3. Check Binance service status: https://www.binance.com/en/support/announcement
4. Reduce request frequency if hitting rate limits
5. Restart bot: `sudo systemctl restart yunmin`

---

### High CPU/Memory Usage

**Symptoms**: Slow performance, system lag

**Diagnosis**:
```bash
# Monitor resources
top -p $(pgrep -f yunmin)

# Check memory
ps aux | grep yunmin

# Check disk space
df -h
```

**Solutions**:
1. Reduce data retention period in config
2. Clear old logs: `find logs/ -mtime +30 -delete`
3. Vacuum database: `sqlite3 data/yunmin_prod.db "VACUUM;"`
4. Restart bot to free memory

---

### Database Errors

**Symptoms**: "Database locked", "unable to open database file"

**Diagnosis**:
```bash
# Check file permissions
ls -lh data/yunmin_prod.db

# Check disk space
df -h /path/to/yunmin/data

# Test database integrity
sqlite3 data/yunmin_prod.db "PRAGMA integrity_check;"
```

**Solutions**:
1. Fix permissions: `chmod 644 data/yunmin_prod.db`
2. Free disk space
3. Restore from backup if corrupted:
   ```bash
   mv data/yunmin_prod.db data/yunmin_prod_corrupt.db
   cp data/backups/yunmin_prod_latest.db data/yunmin_prod.db
   ```

---

## Backup & Recovery

### Manual Backup

```bash
# Backup database
cp data/yunmin_prod.db data/backups/yunmin_prod_$(date +%Y%m%d_%H%M%S).db

# Backup config
cp config/production.yaml config/backups/production_$(date +%Y%m%d).yaml

# Backup logs
tar -czf logs/archive_$(date +%Y%m%d).tar.gz logs/yunmin_*.log
```

### Automated Backup (Cron)

Add to crontab (`crontab -e`):

```bash
# Daily database backup at 2 AM
0 2 * * * /path/to/yunmin/scripts/backup_database.sh

# Weekly cleanup of old backups (keep 30 days)
0 3 * * 0 find /path/to/yunmin/data/backups -mtime +30 -delete
```

**`scripts/backup_database.sh`:**
```bash
#!/bin/bash
BACKUP_DIR="/path/to/yunmin/data/backups"
DB_PATH="/path/to/yunmin/data/yunmin_prod.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cp "$DB_PATH" "$BACKUP_DIR/yunmin_prod_$TIMESTAMP.db"
echo "Backup created: yunmin_prod_$TIMESTAMP.db"
```

### Restore from Backup

```bash
# Stop bot
sudo systemctl stop yunmin

# Restore database
cp data/backups/yunmin_prod_20241220_020000.db data/yunmin_prod.db

# Restart bot
sudo systemctl start yunmin

# Verify
sqlite3 data/yunmin_prod.db "SELECT COUNT(*) FROM trades;"
```

---

## Performance Optimization

### Database Optimization

```bash
# Vacuum database (reclaim space)
sqlite3 data/yunmin_prod.db "VACUUM;"

# Analyze query plans
sqlite3 data/yunmin_prod.db "ANALYZE;"

# Check database size
du -h data/yunmin_prod.db
```

### Log Rotation

```bash
# Rotate logs manually
mv logs/yunmin.log logs/yunmin_$(date +%Y%m%d).log
touch logs/yunmin.log

# Compress old logs
gzip logs/yunmin_20241219.log

# Delete logs older than 90 days
find logs/ -name "yunmin_*.log.gz" -mtime +90 -delete
```

---

## Security Checklist

### Weekly Security Audit

- [ ] Review API key activity on Binance
- [ ] Check for unauthorized login attempts: `grep "Failed password" /var/log/auth.log`
- [ ] Verify firewall rules: `sudo ufw status`
- [ ] Update dependencies: `pip list --outdated`
- [ ] Rotate API keys (if compromised)
- [ ] Review alert history for suspicious activity

### API Key Rotation

```bash
# 1. Generate new API keys on Binance
# 2. Update .env file
nano .env
# BINANCE_API_KEY=new_key
# BINANCE_API_SECRET=new_secret

# 3. Restart bot
sudo systemctl restart yunmin

# 4. Delete old keys from Binance
```

---

## Monitoring Dashboard

### Key Metrics to Track

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Win Rate | >50% | <40% |
| Daily P&L | Positive | Loss >$500 |
| Max Drawdown | <10% | >20% |
| Sharpe Ratio | >1.0 | <0.5 |
| Uptime | 99%+ | <95% |
| Avg Trade Duration | Varies | >24h (stuck?) |

### Daily Report Example

```
=== YunMin Daily Report ===
Date: 2024-12-20

Trades: 12
Winning: 7 (58.3%)
Losing: 5 (41.7%)

Total P&L: +$234.56
Fees: -$12.34
Net P&L: +$222.22

Best Trade: +$67.89
Worst Trade: -$23.45

Open Positions: 1
Current Exposure: $4,500 (45%)

Alerts Sent: 15
  - INFO: 12
  - WARNING: 2
  - ERROR: 1
  - CRITICAL: 0
```

---

## Contacts & Escalation

### Support Tiers

**Tier 1 (Self-Service)**:
- Check runbook
- Review logs
- Restart bot

**Tier 2 (Engineering)**:
- Email: devops@yourcompany.com
- Slack: #yunmin-trading-alerts
- Response: <2 hours

**Tier 3 (Emergency)**:
- On-call engineer: +1-555-123-4567
- Emergency shutdown: Run `scripts/emergency_stop.sh`
- Escalation: CTO/VP Engineering

### Incident Response

1. **Detect**: Alert received or anomaly identified
2. **Assess**: Check logs, metrics, system status
3. **Contain**: Stop bot if necessary, close risky positions
4. **Resolve**: Fix root cause, restore service
5. **Document**: Log incident, update runbook
6. **Review**: Post-mortem analysis, prevent recurrence

---

## Appendix: Useful Scripts

### Close All Positions (`scripts/close_all_positions.py`)

```python
from yunmin.connectors.binance_connector import BinanceConnector

connector = BinanceConnector(testnet=False)
positions = connector.get_open_positions()

for pos in positions:
    print(f"Closing {pos['symbol']} size {pos['size']}")
    connector.close_position(pos['symbol'], pos['size'])
    
print(f"Closed {len(positions)} positions")
```

### Emergency Stop (`scripts/emergency_stop.sh`)

```bash
#!/bin/bash
echo "=== EMERGENCY STOP ==="
sudo systemctl stop yunmin
echo "Bot stopped. Positions remain open."
echo "To close positions, run: python scripts/close_all_positions.py"
```

---

**Document Version**: 1.0  
**Last Updated**: 2024-12-20  
**Next Review**: 2025-01-20
