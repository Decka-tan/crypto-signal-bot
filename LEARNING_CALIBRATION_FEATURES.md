# Learning & Calibration System - User Guide

## Overview

The bot now includes a **learning and calibration system** that:
1. Tracks all predictions and outcomes in a SQLite database
2. Calculates calibration metrics to see how accurate predictions are
3. Adjusts model confidence based on historical performance
4. Fetches bet history from Unhedged API (when available)

---

## New Commands

### 1. `--stats` - Show Performance Statistics

```bash
python main_ultimate.py --stats
```

**What it does:**
- Shows win rate, profit/loss, ROI
- Breaks down performance by symbol (BTC, ETH, SOL, CC)
- Shows average edge (our advantage over market odds)

**Example output:**
```
📈 Performance Statistics (Last 30 days)

Overall Performance:
  Total Bets: 25
  Wins: 18
  Losses: 7
  Win Rate: 72.0%
  Profit/Loss: $127.50
  ROI: 12.8%
  Avg Edge: 3.2%

Performance by Symbol:
  Symbol    Bets  Win Rate   P&L     ROI
  BTCUSDT     10    80.0%   $85.00  17.0%
  ETHUSDT      8    75.0%   $32.50  13.0%
  SOLUSDT      7    57.1%  -$10.00  -5.7%
```

---

### 2. `--calibrate` - Calculate Calibration Metrics

```bash
python main_ultimate.py --calibrate
```

**What it does:**
- Analyzes how well predicted probabilities match actual outcomes
- Generates calibration curve by confidence bucket (0-20%, 20-40%, etc.)
- Calculates calibration parameters (slope, intercept) to adjust future predictions
- Shows recommendations for model improvement

**Example output:**
```
📊 CALIBRATION REPORT

Overall Accuracy: 72.0%
Brier Score: 0.1850 (lower is better)
Expected Profit per Bet: 3.2%

Accuracy by Confidence Bucket:
┌──────────┬───────┬───────────┬─────────────┬─────────┐
│ Bucket   │ Count │ Pred Prob │ Actual Freq │ Diff    │
├──────────┼───────┼───────────┼─────────────┼─────────┤
│ 0-20%    │     5 │     12.0% │       10.0% │  -2.0%  │
│ 20-40%   │     3 │     35.0% │       40.0% │  +5.0%  │
│ 40-60%   │     4 │     52.0% │       45.0% │  -7.0%  │
│ 60-80%   │     6 │     72.0% │       75.0% │  +3.0%  │
│ 80-100%  │     7 │     88.0% │       92.0% │  +4.0%  │
└──────────┴───────┴───────────┴─────────────┴─────────┘

Calibration Parameters:
  Slope (m): 1.05
  Intercept (b): -0.02
  Formula: p_calibrated = 1.05 * p_raw + -0.02

💡 RECOMMENDATIONS:
  ✅ Good accuracy (>75%) - Model is working well!
```

**What happens:**
- Calibration parameters are saved to `calibration_params.json`
- Future predictions automatically use these calibrated probabilities
- Example: If model predicts 75% YES, calibrated prediction = `1.05 * 0.75 - 0.02 = 76.75%`

---

### 3. `--history` - Fetch Bet History from Unhedged

```bash
python main_ultimate.py --history
```

**What it does:**
- Fetches your past bets from Unhedged API
- Updates the result tracker with actual outcomes
- Automatically runs calibration after fetching

**Note:** This requires the Unhedged API to have a bets/orders endpoint. If the endpoint is not available, you can still track bets by running the bot normally.

---

### 4. Combined Options

```bash
# Specify days to look back (default: 30)
python main_ultimate.py --stats --calibration-days 7

# Fetch history and calibrate in one command
python main_ultimate.py --history --calibration-days 14
```

---

## How It Works

### 1. Tracking (Automatic)

When the bot runs, it automatically:
- Logs every prediction to `bets.db` SQLite database
- Records: symbol, signal, confidence, edge, timestamp, market ID
- When market resolves, updates with actual result and win/loss

### 2. Calibration

**Calibration Curve:**
- Groups predictions by confidence bucket (0-20%, 20-40%, etc.)
- Compares predicted probability vs actual win rate
- If we predict 80% and win 75% of the time → we're overconfident
- Calibration adjusts future predictions to be more accurate

**Calibration Formula:**
```
p_calibrated = slope * p_raw + intercept
```

Example:
- Model predicts: 70% YES
- Calibration: slope=1.1, intercept=-0.05
- Calibrated: `1.1 * 0.70 - 0.05 = 72%` (more confident)

### 3. Improvements

The calibration system helps:
- **Reduce overconfidence**: If 90% predictions only win 75% of the time, calibration adjusts down
- **Increase underconfidence**: If 60% predictions win 70% of the time, calibration adjusts up
- **Better EV calculations**: Edge = `p_calibrated - implied_prob` uses calibrated probability

---

## Files

### `bets.db`
SQLite database with tables:
- `bets` - All predictions and outcomes
- `market_snapshots` - Market state at prediction time
- `performance_stats` - Aggregated statistics

### `calibration_params.json`
Calibration parameters from last calibration:
```json
{
  "slope": 1.05,
  "intercept": -0.02,
  "calibration_type": "linear"
}
```

### `core/result_tracker.py`
ResultTracker class that:
- Logs predictions to database
- Calculates statistics
- Generates performance reports

### `core/unhedged_history.py`
UnhedgedHistoryFetcher class that:
- Fetches bet history from API
- Calculates calibration metrics
- Generates calibration reports

---

## Workflow

### Initial Setup (No historical data)
1. Run bot: `python main_ultimate.py`
2. Bot tracks predictions to `bets.db`
3. Wait for markets to resolve (auto-updates when you run `--history`)

### After 1 Week of Tracking
1. Run: `python main_ultimate.py --stats`
2. Check win rate and performance
3. Run: `python main_ultimate.py --calibrate`
4. Calibration parameters saved and used automatically

### Continuous Improvement
1. Run `--stats` weekly to check performance
2. Run `--calibrate` weekly to update model
3. Bot automatically uses latest calibration parameters

---

## Example: Using Calibration to Improve Win Rate

### Before Calibration:
```
Prediction: 80% YES (confidence: 80%)
Edge: 80% - 75% = +5%
Result: Bet (is_bettable=true)
```

### After Calibration (slope=0.9, intercept=-0.05):
```
Raw Prediction: 80%
Calibrated: 0.9 * 0.80 - 0.05 = 67%
Edge: 67% - 75% = -8%
Result: NO BET (is_bettable=false, negative edge)
```

**Result:** Calibration prevented a bad bet by correcting overconfidence!

---

## GPT King Alignment

This calibration system addresses GPT King's feedback:

1. ✅ **Confidence = REAL probability** - Now calibrated from actual results
2. ✅ **EV calculation** - Uses calibrated probability
3. ✅ **Edge detection** - `p_calibrated - implied_prob` is accurate
4. ✅ **No indicator bias** - Model learns from actual outcomes
5. ✅ **Continuous improvement** - Bot gets smarter over time

---

## Troubleshooting

### "No bets found in tracker"
- Run the bot normally to start tracking predictions
- Or use `--history` to fetch past bets from Unhedged

### "No resolved bets found for calibration"
- Need at least 10-20 resolved bets for calibration
- Wait for markets to resolve (1 hour for binary markets)

### "Calibration shows overconfidence"
- This is normal! The system will adjust future predictions
- Run `--calibrate` weekly to keep model accurate

### API endpoint not found for history
- Unhedged API may not have public bet history endpoint
- Bot still tracks predictions automatically when running
- Manual result tracking can be added if needed

---

## Next Steps

1. **Run the bot** for 1 week to gather data
2. **Check stats**: `python main_ultimate.py --stats`
3. **Calibrate**: `python main_ultimate.py --calibrate`
4. **Repeat weekly** for continuous improvement

---

**The goal: 100% win rate through continuous learning!** 🚀
