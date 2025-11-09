# Installation Guide

## System Requirements

- **Python**: 3.11 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 1GB for application and data
- **OS**: Windows, Linux, or macOS
- **Git**: For cloning the repository

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/AgeeKey/yun_min.git
cd yun_min
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install YunMin in development mode
pip install -e .
```

### 4. Optional: Install TA-Lib

TA-Lib provides additional technical indicators. Installation varies by platform:

**Windows:**
Download the wheel from [unofficial binaries](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib) and install:
```bash
pip install TA_Lib‑0.4.XX‑cpXX‑cpXXm‑win_amd64.whl
```

**Linux:**
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install TA-Lib
```

**macOS:**
```bash
brew install ta-lib
pip install TA-Lib
```

### 5. Verify Installation

```bash
# Check if yunmin is installed
python -c "import yunmin; print(yunmin.__version__)"

# Run basic tests
pytest tests/unit/ -v
```

## Post-Installation

After successful installation:

1. **Configure API Keys**: See [Configuration Guide](configuration.md)
2. **Quick Start**: Follow the [Quickstart Guide](quickstart.md)
3. **Test Connection**: Run `python check_testnet_ready.py`

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError: No module named 'yunmin'`**
- Solution: Make sure you ran `pip install -e .` from the project root

**Issue: TA-Lib installation fails**
- Solution: You can use pandas-ta as an alternative (already in requirements.txt)

**Issue: CCXT connection errors**
- Solution: Check your internet connection and firewall settings

**Issue: Import errors for ML libraries**
- Solution: Try installing packages individually:
  ```bash
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install tensorflow
  ```

### Getting Help

- Open an issue on [GitHub](https://github.com/AgeeKey/yun_min/issues)

## Next Steps

- [Configuration Guide](configuration.md) - Set up your trading environment
- [Quickstart](quickstart.md) - Run your first backtest
