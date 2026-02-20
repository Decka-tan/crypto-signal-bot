# 🤖 Claude Code Session Notes

**FOR CLAUDE AI**: Read this file FIRST at the start of every new session!

---

## 🚨 IMPORTANT: READ THIS FIRST!

**Claude Code has NO memory between sessions!** Each new session = fresh start with zero knowledge of previous conversations.

**Always read these files in order:**
1. `CLAUDE_NOTES.md` (this file) - Quick context
2. `PROGRESS.md` - What was done
3. `TODO.md` - What needs to be done
4. Check `git status` - Uncommitted changes

---

## 📋 Project Overview

**Project Name**: Crypto Signal Bot for Unhedged Prediction Markets
**Language**: Python 3.x
**Purpose**: Monitor crypto markets, generate trading signals, send Discord alerts, semi-automated betting on Unhedged

**Tech Stack**:
- Selenium (Chrome WebDriver) - for API bypass
- Requests (fallback)
- Pandas - data processing
- TA-Lib - technical indicators
- Discord webhooks - alerts
- Unhedged API - betting integration

---

## 🎯 Main Problem Being Solved

### Issue: API Blocking
**Python requests library is being blocked** (likely by firewall, ISP, or antivirus)
- Cannot fetch market data from Binance/Bybit APIs
- Connection timeouts, SSL errors, connection refused

### Solution: Selenium-Based Fetcher
**Use Chrome browser via Selenium to bypass Python-level blocking**
- Chrome makes the HTTP requests instead of Python
- Appears as regular browser traffic to firewall/ISP
- Bypasses the blocking

**Status**: Solution implemented, NOT YET TESTED

---

## 📁 Key Files to Know

### Recently Modified (NOT COMMITTED YET!)
```
core/selenium_market_fetcher.py  - NEW! Chrome-based API fetcher
core/market_monitor.py           - Modified to integrate Selenium
main_ultimate.py                 - Added cleanup handler
core/alerts.py                   - Changed @everyone logic
test_api.py                      - NEW! API testing script
test_api_nossl.py                - NEW! API test without SSL
```

### Important Config
```
config.yaml                      - Bot configuration
```

### Documentation (READ THESE!)
```
PROGRESS.md                      - What was done, current status
TODO.md                          - What needs to be done next
CLAUDE_NOTES.md                  - This file - session context
```

---

## ✅ What Was Built Last Session

### 1. Selenium Market Fetcher
**File**: `core/selenium_market_fetcher.py`

**Purpose**: Fetch market data using Chrome browser instead of Python requests

**Key Features**:
- Uses Chrome WebDriver via Selenium
- Headless mode (no GUI)
- Ignores SSL errors
- Supports Binance & Bybit APIs
- Falls back to demo data on failure
- Context manager for proper cleanup

**Usage**:
```python
from core.selenium_market_fetcher import SeleniumMarketFetcher

fetcher = SeleniumMarketFetcher(symbols=["BTCUSDT"], timeframe="5m")
df = fetcher.get_klines("BTCUSDT", limit=100)
price = fetcher.get_current_price("BTCUSDT")
fetcher.close()
```

---

### 2. Integration with Market Monitor
**File**: `core/market_monitor.py`

**Changes**:
- Added import: `from core.selenium_market_fetcher import SeleniumMarketFetcher`
- Added flag: `self.use_selenium = True`
- Added lazy initialization of Selenium fetcher
- Modified `get_klines()` to try Selenium first, fallback to requests
- Modified `get_current_price()` to use Selenium
- Added `cleanup()` method to close Chrome driver

**Behavior**:
1. First call: Initialize Chrome driver
2. Try fetching with Selenium
3. If fails, fallback to requests method
4. If all fail, use demo data

---

### 3. Cleanup Handler
**File**: `main_ultimate.py`

**Changes**:
```python
try:
    bot.run(once=args.once)
except KeyboardInterrupt:
    print("\n\n[!] Bot stopped by user")
except Exception as e:
    # error handling
finally:
    # Cleanup Selenium driver
    print("\n[INFO] Cleaning up...")
    bot.market_monitor.cleanup()
```

**Purpose**: Ensure Chrome driver closes properly on exit

---

### 4. Discord Alert Changes
**File**: `core/alerts.py`

**Changes**:
- Changed @everyone logic from "only high confidence" to "ALL alerts"
- High confidence (≥75%): "@everyone 🚨 HIGH CONFIDENCE SIGNAL!"
- Normal confidence: "@everyone 📊 New Trading Signal!"

**Reason**: User wants to be mentioned on all trading signals

---

## 🧪 Testing Status

### NOT TESTED YET ⏳
- [ ] Selenium fetcher standalone test
- [ ] Full bot run with Selenium
- [ ] Discord alerts with new @everyone logic
- [ ] Chrome driver cleanup on exit
- [ ] End-to-end signal generation

### Test Scripts Available
```bash
# Test Selenium fetcher
python core/selenium_market_fetcher.py

# Test API connections (will fail - demonstrates blocking)
python test_api.py

# Test API without SSL (will also fail)
python test_api_nossl.py

# Run full bot
python main_ultimate.py
```

---

## 🎯 Next Session Goals (IN ORDER!)

### 1. TEST SELENIUM FETCHER (CRITICAL!)
```bash
# First, ensure Chrome driver is installed:
pip install webdriver-manager

# Then test:
python core/selenium_market_fetcher.py
```

**What to look for**:
- Chrome launches in headless mode
- Successfully fetches data for BTCUSDT, ETHUSDT, SOLUSDT
- No connection errors
- Clean shutdown

### 2. FULL BOT TEST
```bash
python main_ultimate.py
```

**What to look for**:
- Bot initializes without errors
- "Initializing Chrome-based data fetcher..." message appears
- Data is fetched for all symbols
- Discord alerts work
- Ctrl+C triggers cleanup

### 3. COMMIT CHANGES!
```bash
git add .
git commit -m "feat: add Selenium fetcher to bypass API blocking"
git push
```

---

## 💬 Talking Points for User

### When Starting New Session:
1. "Welcome back! I've read the notes from our last session."
2. "Last time we built a Selenium fetcher to bypass API blocking."
3. "The changes haven't been tested yet. Should we test it now?"
4. "After that, we should commit the changes to git."

### If User Asks "What Were We Doing?":
- "We were fixing an API blocking issue where Python requests couldn't reach Binance/Bybit."
- "We built a Selenium-based solution using Chrome browser to bypass the blocking."
- "It's implemented but not tested yet. That's our next step."

### If User Asks "What Do I Do?":
- "First, let's test if the Selenium fetcher works."
- "If it works, we'll run the full bot."
- "Then we'll commit everything to git so we don't lose progress."

---

## 🚨 Common Pitfalls to Avoid

### DON'T:
- ❌ Start from scratch or rebuild what's already done
- ❌ Add new features before testing existing work
- ❌ Forget to check git status for uncommitted changes
- ❌ Assume the blocking is fixed - test first!
- ❌ Close VS Code without committing

### DO:
- ✅ Read PROGRESS.md and TODO.md first
- ✅ Test the Selenium solution
- ✅ Commit changes frequently
- ✅ Update TODO.md as tasks are completed
- ✅ Ask user before starting major work

---

## 📊 Current Bot Configuration

### Active Symbols
```
BTCUSDT - Bitcoin
ETHUSDT - Ethereum
SOLUSDT - Solana
CCUSDT  - Canton (Unhedged-specific)
```

### Key Settings
- Exchange: Bybit (with fallback to Binance)
- Timeframe: 5 minutes
- Min Confidence: 75%
- Discord: Enabled with @everyone on all alerts
- Unhedged: Semi-automated betting enabled

### Unhedged Market IDs
```
BTCUSDT: cmltgz89a03dk0swj3febsk7m
ETHUSDT: cmltgz8gt03do0swju58b72ab
SOLUSDT: cmltgz8uw03dw0swj779dlin8
CCUSDT:  cmltgz8o003ds0swjitsvl7rh
```

---

## 🔧 Quick Reference Commands

### Testing
```bash
# Test Selenium fetcher
python core/selenium_market_fetcher.py

# Test API (will fail - expected)
python test_api.py

# Run full bot
python main_ultimate.py

# Run once and exit
python main_ultimate.py --once
```

### Git
```bash
# Check status
git status

# Commit all changes
git add .
git commit -m "feat: add selenium fetcher"

# Push to remote
git push
```

### Chrome Driver
```bash
# Install auto-manager
pip install webdriver-manager

# Manual install (Windows)
choco install chromedriver
```

---

## 📈 Git Status

**Current Branch**: main
**Last Commit**: 4285385 - "Change bet execution from curl command to clickable market link"

**Uncommitted Changes**:
```
Modified:
  - config.yaml
  - core/alerts.py
  - core/market_monitor.py
  - main_ultimate.py

New (Untracked):
  - core/selenium_market_fetcher.py
  - test_api.py
  - test_api_nossl.py
  - PROGRESS.md
  - TODO.md
  - CLAUDE_NOTES.md
```

**Action Needed**: COMMIT BEFORE CLOSING!

---

## 🎓 Context for User's Frustration

The user expressed frustration because:
1. They lost work when closing VS Code (Claude Code doesn't remember sessions)
2. They had to re-explain context multiple times
3. Progress was lost between sessions

**Solution**:
- These documentation files (PROGRESS.md, TODO.md, CLAUDE_NOTES.md) were created
- Commit frequently to git
- Always update docs before closing session
- Read docs first at start of new session

---

## ✅ Session Checklist

When starting a new session, Claude should:

- [ ] Read CLAUDE_NOTES.md (this file)
- [ ] Read PROGRESS.md for detailed status
- [ ] Read TODO.md for next tasks
- [ ] Check git status
- [ ] Ask user: "Shall we continue with testing the Selenium fetcher?"
- [ ] DO NOT start new features without user request

When ending a session, Claude should:

- [ ] Update PROGRESS.md with what was done
- [ ] Update TODO.md with what's pending
- [ ] Remind user to commit changes
- [ ] Update CLAUDE_NOTES.md if anything major changed

---

**Last Updated**: 2025-02-20
**Session Count**: 2
**User Preference**: Wants documentation and git commits to avoid losing work
**Next Action**: Test Selenium fetcher, then commit changes
