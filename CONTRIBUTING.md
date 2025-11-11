# Contributing to Yun Min

Thank you for your interest in contributing to Yun Min! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and constructive
- Focus on what is best for the community
- Show empathy towards other contributors

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)

### Suggesting Features

1. Open an issue describing the feature
2. Explain why it would be useful
3. Provide examples of how it would work

### Pull Requests

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass: `pytest tests/`
6. Update documentation as needed
7. Commit with clear messages
8. Push to your fork
9. Create a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/yun_min.git
cd yun_min

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (recommended)
pre-commit install

# Install package in editable mode
pip install -e .

# Run tests
pytest tests/
```

## Code Quality Tools

We use several tools to maintain code quality:

### Formatting
- **Black**: Code formatter with line length 100
  ```bash
  black yunmin/ tests/
  ```

- **isort**: Import statement sorter
  ```bash
  isort yunmin/ tests/
  ```

### Linting
- **flake8**: Style guide enforcement
  ```bash
  flake8 yunmin/ tests/
  ```

- **ruff**: Fast Python linter
  ```bash
  ruff check yunmin/ tests/
  ```

### Type Checking
- **mypy**: Static type checker
  ```bash
  mypy yunmin/
  ```

### Security
- **bandit**: Security issue scanner
  ```bash
  bandit -r yunmin/ -c pyproject.toml
  ```

### Pre-commit Hooks
Pre-commit hooks automatically run checks before each commit:
```bash
# Install hooks (one-time setup)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

The hooks include:
- black (formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)
- prettier (YAML formatting)
- trailing whitespace removal
- end-of-file fixer
- YAML validation
- large file check
- merge conflict check
- private key detection
- bandit (security)

### Running All Checks
```bash
# Format code
black yunmin/ tests/
isort yunmin/ tests/

# Run linters
flake8 yunmin/ tests/
ruff check yunmin/ tests/

# Type check
mypy yunmin/

# Security scan
bandit -r yunmin/ -c pyproject.toml

# Run tests
pytest tests/
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Line length: 100 characters (configured in pyproject.toml)
- All code should pass pre-commit hooks before committing
- Use type hints where appropriate

## Testing

- Write tests for new functionality
- Maintain test coverage above 80%
- Run tests before submitting PR: `pytest tests/`
- Test coverage: `pytest --cov=yunmin tests/`

## Documentation

- Update README.md for user-facing changes
- Add docstrings following Google style
- Update examples if adding new features

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb: "Add", "Fix", "Update", "Remove"
- Keep first line under 50 characters
- Add details in body if needed

Example:
```
Add risk management circuit breaker

- Implement emergency stop mechanism
- Add tests for circuit breaker
- Update documentation
```

## Areas for Contribution

We especially welcome contributions in:

- [ ] Backtesting engine implementation
- [ ] ML model integration (XGBoost, LSTM, etc.)
- [ ] LLM integration for trade analysis
- [ ] Web dashboard UI
- [ ] Telegram/Discord notifications
- [ ] Additional trading strategies
- [ ] Performance optimizations
- [ ] Documentation improvements
- [ ] Test coverage improvements

## Questions?

Feel free to:
- Open an issue for questions
- Start a discussion in GitHub Discussions
- Contact maintainers

Thank you for contributing!
