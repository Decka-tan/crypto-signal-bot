# Discord Alert Setup Guide

Get instant trading signals directly to your Discord server!

---

## Step 1: Create Discord Webhook

### 1. Open Your Discord Server
1. Go to your Discord server
2. Click the **⚙️ Settings** icon next to your server name

### 2. Create Webhook
1. Go to **Integrations** → **Webhooks**
2. Click **New Webhook**
3. Choose the channel where you want alerts
4. Name it "Crypto Signal Bot"
5. Click **Copy Webhook URL**

Your URL will look like:
```
https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz
```

---

## Step 2: Configure the Bot

### Option 1: Edit config.yaml

Open `config.yaml` and add your webhook:

```yaml
alerts:
  console: true
  sound: ""

  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"
```

### Option 2: Quick Test

Create a test config file:

```bash
# Create test-config.yaml
cat > test-config.yaml << EOF
symbols:
  - "BTCUSDT"
  - "ETHUSDT"
timeframe: "15m"

thresholds:
  min_confidence: 60

alerts:
  console: true
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_HERE"

display:
  update_interval: 30

indicators:
  rsi: {period: 14, enabled: true}
  macd: {fast: 12, slow: 26, signal: 9, enabled: true}
  ema: {short: 9, long: 21, enabled: true}
  bollinger_bands: {period: 20, std: 2, enabled: true}
  volume: {period: 20, enabled: true}
EOF
```

---

## Step 3: Test It!

Run the bot in demo mode to test:

```bash
python main.py --once --demo --config test-config.yaml
```

You should see a beautiful alert in your Discord channel like this:

```
┌─────────────────────────────────────┐
│  🚨 Signal Alert: ETHUSDT          │
│                                     │
│  🔴 Signal: NO (73.8%)             │
│  💡 Action: Bet NO                 │
│  🎯 Target: BELOW $2,204.34        │
│                                     │
│  📊 Technical Reasons:             │
│  1. RSI neutral (45.3)             │
│  2. MACD bearish                   │
│  3. EMA bearish cross              │
│  4. Volume spike (178% of avg)     │
│                                     │
│  📈 Key Indicators:                │
│  • RSI: 45.3 (Neutral)             │
│  • MACD: BEARISH                   │
│  • EMA Cross: BEARISH              │
│  • Volume: 178% of avg             │
└─────────────────────────────────────┘
```

---

## Step 4: Run Continuous Monitoring

Once verified, run the bot continuously:

```bash
python main.py --demo  # Or remove --demo for live data
```

The bot will now send alerts to your Discord whenever it finds a trading opportunity!

---

## Discord Alert Features

✅ **Beautiful embeds** with color-coded signals
✅ **Coin thumbnails** automatically included
✅ **All indicators** displayed in readable format
✅ **Actionable advice** with target prices
✅ **Technical reasons** for each signal
✅ **Confidence scores** to help decision making

---

## Example Discord Alerts

### Bullish Signal (Green 🟢):
```
🚨 Signal Alert: SOLUSDT
🟢 Signal: STRONG YES (82.5%)
💡 Action: Bet YES
🎯 Target: ABOVE $105.50
```

### Bearish Signal (Red 🔴):
```
🚨 Signal Alert: ETHUSDT
🔴 Signal: NO (73.8%)
💡 Action: Bet NO
🎯 Target: BELOW $2,204.34
```

---

## Troubleshooting

### "Failed to send Discord alert"
- Check your webhook URL is correct
- Make sure the webhook wasn't deleted
- Verify you have internet connection

### No alerts appearing
- Check `min_confidence` in config (default: 60%)
- Try lowering it to 50 for more alerts
- Run with `--demo` to generate test data

### Webhook not working
- Regenerate the webhook in Discord
- Make a new webhook and update config

---

## Security Tips

✅ **DO:** Share webhook URL only with trusted sources
❌ **DON'T:** Post webhook URL publicly (anyone could spam your channel)
✅ **DO:** Use dedicated channel for alerts
❌ **DON'T:** Use webhook URLs from unknown sources

---

## Multiple Channels

Want alerts in multiple channels?

### Option 1: Multiple Webhooks
Edit `core/alerts.py` to support multiple webhooks:

```python
discord:
  enabled: true
  webhook_urls:
    - "https://discord.com/api/webhooks/.../high-priority"
    - "https://discord.com/api/webhooks/.../all-signals"
```

### Option 2: Discord Webhook Multi-Forwarder
Use a service like [Dishook](https://github.com/kyranet/Dishook) to forward to multiple channels

---

Need help? Join our Discord community!
