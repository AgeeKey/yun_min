# YunMin Development Guide

This guide will help you set up a complete development environment for YunMin trading bot.

## Quick Start (5 minutes)

### Prerequisites

- Docker & Docker Compose installed
- Git
- 4GB+ RAM available

### Start Development Environment

```bash
# Clone the repository
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min

# Start all services
docker-compose -f docker-compose.dev.yml up
```

That's it! The development environment includes:
- ✅ Python service with hot-reload
- ✅ PostgreSQL database (production-like)
- ✅ Redis for caching
- ✅ Prometheus for metrics
- ✅ Grafana for visualization

## Services Overview

### YunMin Bot (yunmin-dev)
- **Port**: N/A (internal)
- **Purpose**: Main trading bot with hot-reload
- **Auto-restarts**: When any `.py` file changes
- **Logs**: `docker-compose logs -f yunmin-dev`

### PostgreSQL (postgres)
- **Port**: 5432
- **Database**: yunmin_dev
- **User**: yunmin
- **Password**: yunmin_dev_pass
- **Connection**: `postgresql://yunmin:yunmin_dev_pass@localhost:5432/yunmin_dev`

### Redis (redis)
- **Port**: 6379
- **Purpose**: Caching and message queue
- **Connection**: `redis://localhost:6379/0`

### Prometheus (prometheus)
- **Port**: 9090
- **URL**: http://localhost:9090
- **Purpose**: Metrics collection and monitoring

### Grafana (grafana)
- **Port**: 3000
- **URL**: http://localhost:3000
- **Username**: admin
- **Password**: admin
- **Purpose**: Metrics visualization and dashboards

## Development Workflow

### 1. Code Changes

All code in `yunmin/`, `tests/`, and `config/` is mounted as volumes.
Changes are automatically detected and the bot restarts.

```bash
# Edit code in your favorite IDE
vim yunmin/strategy/my_strategy.py

# Watch logs for restart
docker-compose -f docker-compose.dev.yml logs -f yunmin-dev
```

### 2. Running Tests

#### Manual Test Run
```bash
# Run all tests
docker-compose -f docker-compose.dev.yml exec yunmin-dev pytest

# Run specific test file
docker-compose -f docker-compose.dev.yml exec yunmin-dev pytest tests/test_strategy.py

# Run with coverage
docker-compose -f docker-compose.dev.yml exec yunmin-dev pytest --cov=yunmin
```

#### Auto-Testing on File Changes
```bash
# Start test runner service
docker-compose -f docker-compose.dev.yml --profile testing up test-runner

# Watch logs
docker-compose -f docker-compose.dev.yml logs -f test-runner
```

### 3. Database Operations

#### Connect to PostgreSQL
```bash
docker-compose -f docker-compose.dev.yml exec postgres psql -U yunmin -d yunmin_dev
```

#### View Tables
```sql
\dt yunmin.*
```

#### Query Trades
```sql
SELECT * FROM yunmin.trades ORDER BY timestamp DESC LIMIT 10;
```

#### Reset Database
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d postgres
```

### 4. Redis Operations

#### Connect to Redis
```bash
docker-compose -f docker-compose.dev.yml exec redis redis-cli
```

#### View Keys
```redis
KEYS *
```

#### Monitor Commands
```redis
MONITOR
```

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality.

### Setup
```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install
```

### What Gets Checked
- ✅ **Black**: Code formatting (line length 100)
- ✅ **isort**: Import sorting
- ✅ **flake8**: Code linting
- ✅ **mypy**: Type checking
- ✅ **YAML**: Formatting
- ✅ **Security**: Bandit security checks
- ✅ **Common issues**: Trailing whitespace, merge conflicts, etc.

### Manual Run
```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## Monitoring & Metrics

### Grafana Dashboards

1. Open http://localhost:3000
2. Login with admin/admin
3. Import dashboards from `dev-config/grafana/dashboards/`

### Prometheus Metrics

1. Open http://localhost:9090
2. Query bot metrics:
   - `yunmin_trades_total`
   - `yunmin_pnl_total`
   - `yunmin_positions_open`

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose -f docker-compose.dev.yml ps

# View logs
docker-compose -f docker-compose.dev.yml logs

# Restart specific service
docker-compose -f docker-compose.dev.yml restart yunmin-dev
```

### Port Already in Use

```bash
# Find process using port
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :3000  # Grafana

# Kill process or change port in docker-compose.dev.yml
```

### Database Connection Issues

```bash
# Check PostgreSQL health
docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U yunmin

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml restart postgres
```

### Hot-Reload Not Working

```bash
# Check volume mounts
docker-compose -f docker-compose.dev.yml config

# Restart with fresh build
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build
```

## Clean Up

### Stop Services
```bash
docker-compose -f docker-compose.dev.yml down
```

### Remove Volumes (Data)
```bash
docker-compose -f docker-compose.dev.yml down -v
```

### Complete Cleanup
```bash
docker-compose -f docker-compose.dev.yml down -v --remove-orphans
docker system prune -a
```

## Best Practices

### 1. Always Use Virtual Environment (if not using Docker)
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. Write Tests First
- Follow TDD (Test-Driven Development)
- Minimum 80% code coverage
- Use pytest fixtures for common setup

### 3. Code Style
- Run `black` before committing
- Use type hints everywhere
- Write docstrings (Google style)
- Keep functions small and focused

### 4. Commit Messages
- Use conventional commits
- Format: `type(scope): description`
- Examples:
  - `feat(strategy): add LSTM predictor`
  - `fix(risk): correct position sizing calculation`
  - `docs(readme): update installation guide`

### 5. Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: New features
- `fix/*`: Bug fixes

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Run pre-commit hooks (`pre-commit run --all-files`)
5. Commit changes (`git commit -m 'feat: add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open Pull Request

## IDE Setup

### VS Code
Recommended extensions:
- Python
- Pylance
- Docker
- YAML
- GitLens

### PyCharm
- Enable "Black" as code formatter
- Configure pytest as test runner
- Set line length to 100

## Additional Resources

- [Architecture Documentation](../architecture/overview.md)
- [API Reference](../API_DOCUMENTATION.md)
- [AI Strategies Guide](../strategies/ai-strategies.md)
- [Custom Strategy Guide](../strategies/custom-strategy.md)

## Getting Help

- 📧 Email: support@yunmin.dev
- 💬 Discord: https://discord.gg/yunmin
- 🐛 Issues: https://github.com/AgeeKey/yun_min/issues
- 📖 Docs: https://docs.yunmin.dev

---

**Happy Coding! 🚀**
