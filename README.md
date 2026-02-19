# 📊 Crypto Signal Bot

**AI-Powered Technical Analysis Bot for 15-Minute Prediction Markets**

This bot monitors crypto markets in real-time, performs technical analysis using multiple indicators (RSI, MACD, EMA, Bollinger Bands, Volume), and alerts you when to bet "YES" or "NO" on prediction markets with 15-minute timeframes.

---

## 🎯 Features

- **Real-Time Monitoring**: Tracks crypto prices on 15-minute timeframe
- **Multiple Indicators**: RSI, MACD, EMA Crossovers, Bollinger Bands, Volume Analysis
- **Smart Signals**: Generates "YES"/"NO" recommendations with confidence scores
- **Alert System**: Console alerts, sound notifications, optional Telegram alerts
- **Prediction Market Optimized**: Specifically designed for 15m prediction market betting
- **Configurable**: Customize symbols, thresholds, and indicators via `config.yaml`

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

**Note**: If you have issues with `ta-lib`, install it via conda:
```bash
conda install -c conda-forge ta-lib
```

### 2. Configure the Bot

Edit `config.yaml` to customize:

```yaml
symbols:
  - "SOLUSDT"   # Add your favorite coins
  - "ETHUSDT"
  - "BTCUSDT"

timeframe: "15m"

thresholds:
  rsi_oversold: 30
  rsi_overbought: 70
  min_confidence: 60  # Only alert above this confidence
```

### 3. Run the Bot

```bash
# Run continuous monitoring (recommended)
python main.py

# Run analysis once
python main.py --once

# Monitor specific symbols
python main.py --symbols SOL ETH AVAX

# Use custom config
python main.py --config my_config.yaml
```

---

## 📖 How It Works

### Signal Generation

The bot analyzes multiple technical indicators and combines them to generate signals:

| Indicator | Bullish Signal (Bet YES) | Bearish Signal (Bet NO) |
|-----------|-------------------------|------------------------|
| **RSI** | Below 30 (oversold) | Above 70 (overbought) |
| **MACD** | Histogram positive | Histogram negative |
| **EMA** | Short EMA above Long EMA | Short EMA below Long EMA |
| **Bollinger Bands** | Price near lower band | Price near upper band |
| **Volume** | Spike confirms direction | Spike confirms direction |

### Confidence Scoring

- **60-69%**: Moderate confidence - small position
- **70-79%**: Good confidence - standard position
- **80%+**: High confidence - strong signal

### Alert Example

```
🚨 SIGNAL ALERT: SOLUSDT

📊 RECOMMENDATION: STRONG YES (Confidence: 82.5%)

💡 ACTION: Bet YES
   Target: ABOVE $82.695
   Timeframe: 15m
   Risk Level: Low

📈 Technical Reasons:
   1. RSI oversold (28.3)
   2. EMA bullish cross (short: 82.45 > long: 82.12)
   3. Volume spike (165% of avg)
```

---

## ⚙️ Configuration Options

### Indicators

Enable/disable and customize indicators in `config.yaml`:

```yaml
indicators:
  rsi:
    period: 14
    enabled: true

  macd:
    fast: 12
    slow: 26
    signal: 9
    enabled: true

  ema:
    short: 9
    long: 21
    enabled: true

  bollinger_bands:
    period: 20
    std: 2
    enabled: true

  volume:
    period: 20
    enabled: true
```

### Alerts

```yaml
alerts:
  console: true              # Show alerts in terminal
  sound: "C:\\Windows\\Media\\notify.wav"  # Sound file

  telegram:                  # Optional Telegram alerts
    enabled: false
    bot_token: "your_bot_token"
    chat_id: "your_chat_id"
```

### Display Settings

```yaml
display:
  history_length: 50         # Number of candles to analyze
  update_interval: 30        # Update every 30 seconds
```

---

## 📱 Telegram Alerts (Optional)

### 1. Create a Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot` and follow the instructions
3. Save your bot token

### 2. Get Your Chat ID

1. Search for @userinfobot in Telegram
2. Send `/start` to get your chat ID

### 3. Configure the Bot

Edit `config.yaml`:

```yaml
alerts:
  telegram:
    enabled: true
    bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    chat_id: "123456789"
```

---

## 🎯 Trading Strategy Tips

### When to Bet YES (Bullish)

- RSI drops below 30 (oversold) + starts turning up
- MACD histogram crosses above zero
- Short EMA crosses above long EMA
- Price bounces off lower Bollinger Band
- Volume spike on upward move

### When to Bet NO (Bearish)

- RSI rises above 70 (overbought) + starts turning down
- MACD histogram crosses below zero
- Short EMA crosses below long EMA
- Price rejects at upper Bollinger Band
- Volume spike on downward move

### Risk Management

- Start with small positions (1-2% of capital)
- Increase size as confidence improves
- Don't trade every signal - wait for high confidence (70%+)
- Use stop losses on the prediction platform
- Track your results in the `logs/` folder

---

## 📁 Project Structure

```
crypto-signal-bot/
├── main.py                 # Main CLI entry point
├── config.yaml             # Configuration file
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── core/
│   ├── __init__.py
│   ├── market_monitor.py  # Fetches price data
│   ├── indicators.py      # Technical indicators
│   ├── signals.py         # Signal generation
│   └── alerts.py          # Alert system
└── logs/                  # Signal history (auto-created)
    └── signals_YYYYMMDD.log
```

---

## 🛠️ Troubleshooting

### ta-lib Installation Error

If you get an error installing `ta-lib`:

**Windows:**
```bash
# Download wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.28‑cp311‑cp311‑win_amd64.whl
```

**macOS/Linux:**
```bash
conda install -c conda-forge ta-lib
```

### No Data Error

- Check your internet connection
- Verify symbol format (e.g., "BTCUSDT", not "BTC")
- Binance API may be rate-limited - increase `update_interval`

### Import Errors

Make sure you're running from the project directory:
```bash
cd crypto-signal-bot
python main.py
```

---

## 📊 Example Output

```
📊 Crypto Signal Bot - Live Analysis
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Symbol     ┃ Signal        ┃ Confidence ┃ Price       ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ SOLUSDT    │ STRONG YES    │ 82.5%      │ $82.456     │
│ ETHUSDT    │ YES           │ 68.3%      │ $1,965.32   │
│ BTCUSDT    │ HOLD          │ 51.2%      │ $43,250.00  │
└────────────┴───────────────┴────────────┴─────────────┘
```

---

## 📝 License

MIT License - Feel free to modify and use for your prediction market trading!

---

## ⚠️ Disclaimer

This bot is for educational purposes only. Cryptocurrency trading and prediction markets involve substantial risk of loss. Always do your own research and never trade more than you can afford to lose. Past performance does not guarantee future results.

---

**Happy Trading! 🚀📈**
