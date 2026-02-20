# 🚀 Cara Run Bot Setiap Hari

**Bot**: Crypto Signal Bot - ULTIMATE Mode
**Last Updated**: 2025-02-20

---

## 📋 Daftar Isi

1. [Persiapan Awal (One-Time Setup)](#1-persiapan-awal-one-time-setup)
2. [Run Bot Mode Harian](#2-run-bot-mode-harian)
3. [Run Bot Mode Test (Sekali Jalan)](#3-run-bot-mode-test-sekali-jalan)
4. [Troubleshooting Masalah Umum](#4-troubleshooting-masalah-umum)
5. [Tips & Best Practices](#5-tips--best-practices)

---

## 1. Persiapan Awal (One-Time Setup)

**Cukup lakuin sekali aja di awal!**

### Step 1: Buka Terminal/Command Prompt

```bash
# Masuk ke folder project
cd C:\Codingers\crypto-signal-bot
```

### Step 2: Install Dependencies (Belum Pernah?)

```bash
# Install semua yang dibutuhkan
pip install -r requirements.txt
```

**Apa yang di-install?**
- `requests` - untuk API calls
- `selenium` - untuk Chrome browser automation
- `webdriver-manager` - auto-download Chrome driver
- `pandas`, `numpy` - untuk data analysis
- `rich` - untuk tampilan terminal yang cantik
- `pyyaml` - untuk baca config file

**Output yang diharapkan:**
```
Successfully installed requests-2.31.0
Successfully installed selenium-4.15.0
Successfully installed webdriver-manager-4.0.0
Successfully installed pandas-2.0.0
... (dll)
```

### Step 3: Cek Config

**Pastikan file `config.yaml` sudah ter-set dengan benar:**

```bash
# Buka config.yaml di VS Code atau text editor
notepad config.yaml
# atau
code config.yaml
```

**Cek bagian penting:**
```yaml
# Symbols yang mau dimonitor
symbols:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT
  - CCUSDT

# Discord webhook (agar alerts masuk ke Discord)
alerts:
  discord:
    enabled: true
    webhook_url: "https://discord.com/api/webhooks/..."
    mention_everyone: true

# Unhedged API (untuk semi-automated betting)
unhedged:
  enabled: true
  api_key: "ak_..."
```

**Kalau config belum ada atau kosong, jalankan:**
```bash
python setup_discord.py
```

### Step 4: Test Connection (Optional tapi Disarankan)

```bash
# Test API connection (akan gagal kalau ada blocking - itu normal!)
python test_api.py
```

**Output:**
```
Testing Binance API...
[X] ERROR: Connection timeout  <- INI NORMAL KALAU KENA BLOCK
```

Kalau gagal, **jangan khawatir!** Bot punya Selenium fetcher untuk bypass blocking.

---

## 2. Run Bot Mode Harian

### Cara 1: Run Terus Menerus (Recommended)

**Bot akan jalan terus, monitoring 24/7 dan kirim alert ke Discord kalau ada signal.**

```bash
# Pastikan di folder project
cd C:\Codingers\crypto-signal-bot

# Run bot
python main_ultimate.py
```

**Apa yang akan terjadi:**

1. **Bot Start**
   ```
   ╔════════════════════════════════════════════════════════════╗
   ║       📊 Crypto Signal Bot - ULTIMATE Mode v2.0            ║
   ║    Multi-Exchange + ML + Sentiment + Correlation           ║
   ╚════════════════════════════════════════════════════════════╝

   Loading configuration from config.yaml...
   Initializing Chrome-based data fetcher...
   Fetching BTCUSDT via Chrome...
      [OK] Got 100 candles from Binance
   Fetching ETHUSDT via Chrome...
      [OK] Got 100 candles from Binance
   ...
   ```

2. **Monitoring Aktif**
   ```
   ╔═══════════════════════════════════════════════════════════════════════════╗
   ║                    📊 MARKET OVERVIEW - 5m Timeframe                      ║
   ╠═══════════════════════════════════════════════════════════════════════════╣
   ║ Symbol │ Price      │ Change │ RSI  │ MACD  │ Trend      │ Volume        ║
   ╠═══════════════════════════════════════════════════════════════════════════╣
   ║ BTC    │ $43,250   │ +1.2%  │ 45.3 │ Bull  │ NEUTRAL   │ 1.2K          ║
   ║ ETH    │ $1,965    │ +0.8%  │ 52.1 │ Bull  │ BULLISH   │ 856           ║
   ║ SOL    │ $82.45    │ +2.1%  │ 68.4 │ Bull  │ BULLISH   │ 2.3K          ║
   ║ CC     │ $0.85     │ -0.5%  │ 35.2 │ Bear  │ BEARISH   │ 124           ║
   ╚═══════════════════════════════════════════════════════════════════════════╝
   ```

3. **Kalau Ada Signal**
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

   🔗 Unhedged Link: https://unhedged.gg/markets/cmltgz8uw03dw0swj779dlin8
   ```

4. **Discord Alert Terkirim**
   - Cek Discord channel, bot akan kirim alert dengan @everyone
   - Tinggal klik link Unhedged untuk betting

5. **Update Setiap 60 Detik**
   ```
   [10:30:15] Updating market data...
   [10:31:15] Updating market data...
   [10:32:15] Updating market data...
   ```

### Stop Bot

**Tekan `Ctrl + C` di terminal**

```
^C
[!] Bot stopped by user
[INFO] Cleaning up...
```

### Cara 2: Run Background (Windows)

**Supaya bot tetep jalan walau terminal ditutup:**

```bash
# Buat batch file untuk run bot
notepad run_bot.bat
```

**Isi file `run_bot.bat`:**
```batch
@echo off
cd C:\Codingers\crypto-signal-bot
python main_ultimate.py
pause
```

**Cara pakai:**
- Double-click `run_bot.bat` → Bot jalan
- Tekan `Ctrl + C` → Bot stop

---

## 3. Run Bot Mode Test (Sekali Jalan)

**Cuma buat testing, jalan sekali terus keluar.**

### Test Sekali Saja

```bash
# Run once - bot akan analisa terus keluar
python main_ultimate.py --once
```

**Output:**
```
Running analysis ONCE...
Loading configuration...
Fetching data...
Analyzing signals...

No strong signals detected.
Analysis complete.
```

### Test dengan Symbols Tertentu

```bash
# Hanya monitor BTC dan ETH
python main_ultimate.py --symbols BTC ETH

# Atau pakai format USDT
python main_ultimate.py --symbols BTCUSDT ETHUSDT
```

### Test dengan Custom Config

```bash
# Pakai config file lain
python main_ultimate.py --config config_test.yaml
```

---

## 4. Troubleshooting Masalah Umum

### Problem 1: "ModuleNotFoundError: No module named 'selenium'"

**Solusi:**
```bash
pip install -r requirements.txt
```

Atau manual:
```bash
pip install selenium
pip install webdriver-manager
```

---

### Problem 2: "Chrome driver needs to be updated"

**Solusi (OTOMATIS):**
```bash
# Install webdriver-manager (sudah ada di requirements.txt)
pip install webdriver-manager
```

Bot akan auto-download Chrome driver yang cocok dengan versi Chrome kamu.

---

### Problem 3: "Connection timeout" / "API blocking"

**Solusi:**
Tenang! Bot sudah pakai **Selenium fetcher** yang bypass blocking.

Kalau masih gagal:
```bash
# Cek Chrome sudah terinstall
chrome --version

# Atau test Selenium fetcher langsung
python core/selenium_market_fetcher.py
```

---

### Problem 4: Discord webhook tidak jalan

**Cek:**
1. Webhook URL masih valid di Discord?
2. Bot sudah di-kick dari server?

**Test webhook:**
```bash
python test_discord.py
```

---

### Problem 5: Bot keluar error dan stop

**Cek error log:**
```bash
# Run dengan verbose output
python main_ultimate.py --verbose
```

**Lapor error dengan screenshot!**
- Screenshot error message
- Copy traceback
- Cek file `PROGRESS.md` dan `TODO.md`

---

## 5. Tips & Best Practices

### ✅ DO (Recommended)

1. **Commit sering ke git**
   ```bash
   git add .
   git commit -m "daily: update config"
   git push
   ```

2. **Cek Discord alerts berkala**
   - Pastikan bot aktif dan kirim alerts
   - Kalau lama gak ada alert, cek terminal bot

3. **Monitor resource usage**
   - Chrome driver consume RAM (sekitar 200-300MB)
   - Kalau RAM habis, matikan app lain

4. **Keep updated**
   - Pull latest changes dari GitHub
   - Update dependencies tiap bulan

### ❌ DON'T (Avoid)

1. **Jangan close terminal tanpa Ctrl+C**
   - Chrome driver mungkin gak ke-close bersih
   - Bisa sisa `chrome.exe` di background

2. **Jangan run multiple bot instances**
   - Bikin Chrome driver multiple
   - RAM habis

3. **Jangan edit config.yaml while bot running**
   - Bot gak reload config secara otomatis
   - Stop bot dulu, edit config, run lagi

---

## 📋 Quick Reference Command

```bash
# === DAILY USE ===

# Run bot (mode harian)
python main_ultimate.py

# Stop bot
Ctrl + C

# === TESTING ===

# Run once
python main_ultimate.py --once

# Test specific symbols
python main_ultimate.py --symbols BTC ETH

# Test Selenium fetcher
python core/selenium_market_fetcher.py

# === MAINTENANCE ===

# Update dependencies
pip install -r requirements.txt --upgrade

# Git commit
git add .
git commit -m "daily: update"
git push

# Cek log
cat logs/signals_$(date +%Y%m%d).log
```

---

## 🎯 Daily Workflow (Recommended)

### Setiap Hari:

1. **Buka terminal**
   ```bash
   cd C:\Codingers\crypto-signal-bot
   ```

2. **Pull latest updates** (kalau ada)
   ```bash
   git pull origin main
   ```

3. **Run bot**
   ```bash
   python main_ultimate.py
   ```

4. **Minimize terminal** (biarkan jalan di background)

5. **Cek Discord untuk alerts**

6. **Selesai hari ini** → Stop bot dengan `Ctrl + C`

---

## 🆘 Emergency Commands

### Kalau bot "stuck" atau gak respon:

```bash
# Force stop semua Python
taskkill /F /IM python.exe

# Kill Chrome driver (kalau sisa)
taskkill /F /IM chromedriver.exe

# Atau restart PC
```

### Kalau lupa command:

```bash
# Buka file ini
notepad HOW_TO_RUN.md

# Atau baca README
notepad README.md
```

---

## 📞 Butuh Bantuan?

1. **Baca dokumentasi:**
   - `README.md` - Overview project
   - `PROGRESS.md` - Status terbaru
   - `TODO.md` - Apa yang pending
   - `CLAUDE_NOTES.md` - Notes buat Claude AI

2. **Cek troubleshooting di atas**

3. **Kalau masih error:**
   - Screenshot error message
   - Copy full traceback
   - Pastikan `git status` clean (udah di-commit)

---

**Happy Trading! 🚀📈**

**Last Updated**: 2025-02-20
**Status**: Bot ready to run, Selenium fetcher integrated
