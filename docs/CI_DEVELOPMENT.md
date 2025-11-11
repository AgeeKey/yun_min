# CI/CD and Development Guide

## Continuous Integration

This project uses GitHub Actions for continuous integration. The CI pipeline runs automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### CI Workflow

The CI pipeline consists of multiple jobs:

#### 1. **Tests** (`test`)
- Runs on Python 3.9, 3.10, 3.11, and 3.12
- Executes full test suite with pytest
- Generates coverage reports
- Uploads coverage to Codecov (Python 3.11 only)

#### 2. **Linting** (`lint`)
- **Black**: Code formatting check
- **Flake8**: Style guide enforcement
- **isort**: Import sorting validation
- **mypy**: Static type checking
- **Bandit**: Security vulnerability scanning

#### 3. **Integration Tests** (`integration`)
- Runs after unit tests and linting pass
- Executes integration test suite
- Tests end-to-end workflows

#### 4. **Build Check** (`build-check`)
- Builds distribution packages
- Validates package metadata
- Tests package installation

### Badge Status

Add these badges to your README.md:

```markdown
![CI Status](https://github.com/AgeeKey/yun_min/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![Code Coverage](https://codecov.io/gh/AgeeKey/yun_min/branch/main/graph/badge.svg)
```

## Local Development

### Setup Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/AgeeKey/yun_min.git
   cd yun_min
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Running Tests Locally

**Run all tests:**
```bash
pytest tests/
```

**Run with coverage:**
```bash
pytest tests/ --cov=yunmin --cov-report=html
```

**Run specific test file:**
```bash
pytest tests/test_backtester_execution.py -v
```

**Run specific test:**
```bash
pytest tests/test_backtester_execution.py::test_leverage_handling -v
```

### Code Quality Checks

**Format code with Black:**
```bash
black yunmin/ tests/ tools/ --line-length 100
```

**Sort imports:**
```bash
isort yunmin/ tests/ tools/ --profile black --line-length 100
```

**Run linting:**
```bash
flake8 yunmin/ tests/ tools/ --max-line-length=100 --extend-ignore=E203,W503
```

**Type checking:**
```bash
mypy yunmin/ --ignore-missing-imports
```

**Security scan:**
```bash
bandit -r yunmin/ --severity-level medium
```

**Run all pre-commit hooks:**
```bash
pre-commit run --all-files
```

### Writing Tests

Follow these guidelines when writing tests:

1. **Test file naming:** `test_<module>.py`
2. **Test function naming:** `test_<feature>_<scenario>()`
3. **Use fixtures for common setup**
4. **Keep tests focused and independent**
5. **Add docstrings to test functions**

Example:
```python
def test_backtester_initialization():
    """Test that backtester initializes with correct parameters."""
    strategy = SimpleStrategy()
    backtester = Backtester(strategy, initial_capital=10000.0)
    
    assert backtester.initial_capital == 10000.0
    assert backtester.capital == 10000.0
```

### Commit Message Convention

Follow conventional commits:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build/tooling changes

**Example:**
```
feat(backtester): add leverage support

- Added leverage parameter to Backtester
- Updated position sizing calculations
- Added tests for leverage handling

Issue: #38
```

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit
3. Run tests and linting locally
4. Push to GitHub
5. Create pull request
6. Wait for CI to pass
7. Request review
8. Address feedback
9. Merge when approved

### Troubleshooting

**Import errors:**
```bash
pip install -e .
```

**TA-Lib installation issues:**
```bash
# Linux
sudo apt-get install libta-lib0-dev

# Mac
brew install ta-lib

# Windows
# Download from: https://github.com/mrjbq7/ta-lib
```

**Pre-commit hook failures:**
```bash
pre-commit run --all-files
# Fix issues, then commit again
```

## Continuous Deployment

Deployment is manual for now. To deploy:

1. Update version in `setup.py`
2. Create release tag: `git tag v1.0.0`
3. Push tag: `git push origin v1.0.0`
4. GitHub Actions can be extended for automatic PyPI deployment

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [pre-commit Framework](https://pre-commit.com/)
