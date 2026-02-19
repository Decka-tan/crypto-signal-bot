# Discord Setup - Quick Guide

## Step 1: Create Discord Webhook (2 minutes)

### In Discord:
1. Open your Discord server
2. Click **⚙️ Settings** (next to server name)
3. Go to **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Name it: `Crypto Signal Bot`
6. Choose channel: `#trading-signals` (or any channel)
7. Click **Copy Webhook URL**

Your URL looks like:
```
https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz
```

---

## Step 2: Add to config.yaml

Open `config.yaml` and find this section:

```yaml
alerts:
  console: true
  sound: "C:\\Windows\\Media\\notify.wav"

  discord:
    enabled: false
    webhook_url: ""
```

**Change it to:**

```yaml
alerts:
  console: true
  sound: "C:\\Windows\\Media\\notify.wav"

  discord:
    enabled: true
    webhook_url: "PASTE_YOUR_WEBHOOK_URL_HERE"
```

**Example:**
```yaml
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz"
```

---

## Step 3: Test It!

### Option A: Quick Test Script
```bash
cd crypto-signal-bot

# Test with your webhook URL
python test_discord.py
```

### Option B: Run Bot (Will auto-send alerts)
```bash
# Run once (will send any high-confidence signals)
python main_ultimate.py --once --demo

# Or continuous (sends alerts every 30s)
python main_ultimate.py --demo
```

---

## What You'll See in Discord

When a signal triggers, you'll get:

```
┌─────────────────────────────────────────┐
│ 🚨 Signal Alert: ETHUSDT               │
│                                         │
│ 🔴 Signal: NO (73.8%)                 │
│                                         │
│ 💡 Action: Bet NO                      │
│ 🎯 Target: BELOW $2,204.34             │
│ ⏱️  Timeframe: 15m                     │
│ ⚠️  Risk: Low                          │
│                                         │
│ 📊 Technical Reasons:                  │
│ • RSI neutral (45.3)                    │
│ • MACD bearish                          │
│ • Volume spike (178% of avg)           │
│                                         │
│ 📈 Key Indicators:                     │
│ • RSI: 45.3 (Neutral)                   │
│ • MACD: BEARISH                         │
│ • Volume: 178% of avg                   │
└─────────────────────────────────────────┘
```

---

## Troubleshooting

### "No alerts appearing"
- ✅ Check `webhook_url` is correct in config.yaml
- ✅ Check `enabled: true` is set
- ✅ Make sure `min_confidence` is not too high (try 60)
- ✅ Run with `--demo` to generate test data

### "Invalid webhook"
- 🔄 Webhook was deleted - create a new one
- 🔄 URL was copied wrong - copy again carefully

### "Too many alerts"
- 📈 Increase `min_confidence` in config.yaml (try 75 or 80)

---

## Multiple Channels?

Want alerts in multiple channels?

### Option 1: Multiple Webhooks
1. Create 2+ webhooks in different channels
2. Edit `core/alerts.py` to support multiple webhooks

### Option 2: Discord Forwarder
Use a service that forwards one webhook to multiple channels

---

## Security Tips

✅ **DO:**
- Keep webhook URL private
- Use dedicated channel for alerts
- Regenerate webhook if compromised

❌ **DON'T:**
- Share webhook URL publicly
- Post in GitHub/Discord publicly
- Use webhooks from unknown sources

---

## Ready?

1. Create webhook in Discord
2. Edit `config.yaml` with webhook URL
3. Run: `python main_ultimate.py --demo`
4. Check Discord for alerts!

Need help? The bot will show errors if webhook doesn't work.
