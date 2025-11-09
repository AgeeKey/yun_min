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
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Run tests
pytest tests/
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Format code with black: `black yunmin/`
- Check with flake8: `flake8 yunmin/`

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
