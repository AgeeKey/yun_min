# Binance Testnet Setup Instructions

## 🔑 Getting Testnet API Keys

### Step 1: Visit Binance Testnet
Navigate to: **https://testnet.binance.vision/**

### Step 2: Register/Login
- Click "Register" if new user
- Or "Login" if you have an account
- Use any email (no verification needed for testnet)

### Step 3: Generate API Keys
1. After login, click on your email in top-right
2. Select "API Management"
3. Click "Create API"
4. Give it a name (e.g., "YunMin_V3_Test")
5. Complete 2FA if enabled
6. **IMPORTANT:** Copy both:
   - API Key
   - Secret Key
   (Secret key is shown only once!)

### Step 4: Enable Spot Trading
1. Go to "API Management"
2. Find your newly created API key
3. Click "Edit Restrictions"
4. Enable "Enable Spot & Margin Trading"
5. Save changes

### Step 5: Get Testnet Funds
1. Go to your account page
2. Find "Testnet Faucet" or similar option
3. Request testnet USDT (usually instant)
4. You'll get fake USDT for testing (~1000-10000 USDT)

---

## 📝 Creating .env.testnet File

### Option 1: Copy from Example
```bash
cp .env.testnet.example .env.testnet
```

Then edit `.env.testnet` and replace placeholders with your actual keys.

### Option 2: Create Manually
Create file `.env.testnet` in project root:

```bash
# Binance Testnet Credentials
BINANCE_TESTNET_API_KEY=your_actual_api_key_here
BINANCE_TESTNET_API_SECRET=your_actual_secret_key_here

# Risk Management
MAX_POSITION_SIZE_PCT=10.0
MAX_LEVERAGE=1.0
MAX_DAILY_DRAWDOWN_PCT=5.0

# Trading Settings
SYMBOL=BTCUSDT
INITIAL_CAPITAL=10000
COMMISSION_RATE=0.001

# Monitoring
LOG_LEVEL=INFO
```

**⚠️ SECURITY WARNING:**
- NEVER commit `.env.testnet` to git
- File is already in `.gitignore`
- Keep API secrets confidential even for testnet

---

## ✅ Verify Setup

Run the readiness check:

```bash
python check_testnet_ready.py
```

Expected output:
```
✅ BINANCE_TESTNET_API_KEY: abcd****wxyz
✅ BINANCE_TESTNET_API_SECRET: 1234****7890
✅ Ping successful
✅ Server time sync OK
✅ Sufficient testnet funds: $10000.00
🎉 ALL CHECKS PASSED - V3 READY FOR TESTNET DEPLOYMENT!
```

---

## 🚀 Launch Testnet Bot

### Dry Run (Recommended First)
```bash
python run_testnet.py --dry-run --duration 0.1
```
This runs for 6 minutes without placing real orders. Good for testing.

### Full 48-Hour Run
```bash
python run_testnet.py --duration 48
```

### Indefinite Run (Manual Stop)
```bash
python run_testnet.py
```
Press Ctrl+C to stop gracefully.

---

## 📊 Monitoring During Run

Bot logs will show:
- ⏱ Runtime
- 📊 Trade count (Wins/Losses)
- 📈 Win Rate
- 💰 P&L and Return %
- 💵 Current Capital
- 📉 Max Drawdown
- 🔁 Consecutive Losses

Emergency shutdown triggers:
- 🚨 Drawdown > 10%
- 🚨 5+ consecutive losses

---

## 🔍 After Run

Trade log saved to: `testnet_trades_YYYYMMDD_HHMMSS.json`

Contains:
- Session start/end times
- Initial/final capital
- All trades with timestamps, prices, P&L
- Final statistics

---

## ❓ Troubleshooting

### "API key not found" Error
- Double-check API key is correct
- Make sure key is for TESTNET (not mainnet)
- Verify key has "Spot Trading" enabled

### "Signature verification failed"
- Check API secret is correct
- Ensure system time is synced
- Try regenerating API keys

### "Insufficient balance"
- Request more testnet funds from faucet
- Lower `INITIAL_CAPITAL` in .env.testnet

### "Connection timeout"
- Check internet connection
- Binance testnet may be down (rare)
- Try again in a few minutes

---

## 📚 Next Steps

After successful 48h testnet run:
1. Review `testnet_trades_*.json` log
2. Calculate actual Win Rate, P&L, Drawdown
3. Compare with V3 backtest results
4. Decide: Deploy to mainnet OR optimize strategy
5. If optimizing, V4 improvements can be tested on testnet data

---

**Good luck! 🚀**
