# Quick Start Guide

## Option 1: Demo Mode (Test Without Internet)

If you're having connection issues or just want to test the bot:

```bash
cd crypto-signal-bot

# Run once with demo data
python main.py --once --demo

# Run continuous with demo data
python main.py --demo
```

This generates realistic simulated data so you can see how the bot works.

---

## Option 2: Live Mode (Real Data)

### Prerequisites:
- Internet connection
- Access to Binance API (may be blocked in some regions)

### Run Live Bot:

```bash
cd crypto-signal-bot

# Install dependencies
pip install -r requirements.txt

# Run analysis once
python main.py --once

# Run continuous monitoring
python main.py

# Monitor specific coins
python main.py --symbols SOL ETH BTC AVAX
```

---

## Connection Issues?

If you see "No connection could be made" errors:

### Solution 1: Use Demo Mode
```bash
python main.py --demo
```

### Solution 2: Check Firewall/Network
- Ensure `api.binance.com` is accessible
- Try disabling VPN temporarily
- Check if your ISP blocks crypto APIs

### Solution 3: Use Different Network
- Try mobile hotspot
- Try different WiFi network

---

## What the Bot Shows

```
Signal Types:
- STRONG YES / YES    → Bet "YES" on prediction market
- STRONG NO / NO      → Bet "NO" on prediction market
- HOLD                → Wait, no clear signal

Confidence:
- 60-69%  → Small position
- 70-79%  → Standard position
- 80%+    → Strong signal, larger position
```

---

## Example Workflow

1. **Start the bot** (demo mode for testing):
   ```bash
   python main.py --demo
   ```

2. **Watch for alerts**:
   - The bot will show alerts when confidence > 60%
   - Example: "Bet YES on SOL above $105.50"

3. **Place your bet** on your prediction market:
   - Go to your prediction market platform
   - Find the 15-minute market for that coin
   - Bet "YES" or "NO" as recommended

4. **Track results**:
   - Check `logs/` folder for signal history
   - Adjust `min_confidence` in `config.yaml` based on results

---

## Configuration

Edit `config.yaml` to customize:

```yaml
# Add your favorite coins
symbols:
  - "SOLUSDT"
  - "ETHUSDT"
  - "BTCUSDT"
  - "AVAXUSDT"
  - "MATICUSDT"

# Adjust sensitivity
thresholds:
  min_confidence: 70  # Only alert high-confidence signals
  rsi_oversold: 30
  rsi_overbought: 70

# Update frequency
display:
  update_interval: 30  # Check every 30 seconds
```

---

## Tips for Success

1. **Start with Demo Mode**: Learn how the bot works first
2. **Track Your Results**: Check `logs/signals_YYYYMMDD.log`
3. **Adjust Confidence**: If too many false signals, increase `min_confidence`
4. **Focus on High Confidence**: Only trade signals with 70%+ confidence
5. **Use Small Positions**: Start small, increase as you verify the signals
6. **Multiple Confirmations**: Look for signals with 3+ reasons listed

---

## Need Help?

- Check `README.md` for detailed documentation
- Review `config.yaml` for all available options
- Check `logs/` folder for signal history
