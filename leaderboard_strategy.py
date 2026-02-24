"""
Leaderboard-Optimized Auto-Bet Strategy

Goal: Climb Unhedged leaderboard
Metrics: Consistency, Active (Pool Share), Profit

Strategy:
- High volume (30-50 bets/day)
- Small position sizes (1-3% of bankroll)
- High win rate (65%+ target)
- Always bet on positive EV (edge ≥ 1%)
"""

from dataclasses import dataclass
from typing import Dict, Optional
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class LeaderboardConfig:
    """Config optimized for leaderboard ranking"""

    # Position sizing (percentage of bankroll)
    min_bet_pct = 0.01      # 1% = ~$0.33 with $33 bankroll
    base_bet_pct = 0.03     # 3% = ~$1
    max_bet_pct = 0.06      # 6% = ~$2

    # Confidence multipliers
    confidence_90_mult = 2.0      # 90%+ = 2x base bet
    confidence_75_mult = 1.5      # 75-89% = 1.5x
    confidence_60_mult = 1.0      # 60-74% = 1x

    # Filters (LOWER THRESHOLD for MORE bets)
    min_confidence = 60       # Was 70%
    min_edge = 0.01           # 1% (was 2-3%)
    min_distance = 1.0        # 1% from strike (was 2%)

    # Risk limits
    max_bets_per_hour = 15    # Rate limiting
    max_loss_per_day = 5.0    # Stop if loss > $5/day
    max_loss_streak = 5       # Stop if 5 losses in a row

    # Targets
    target_bets_per_day = 40
    target_win_rate = 0.65
    target_daily_volume = 40.0


class LeaderboardTracker:
    """Track leaderboard metrics"""

    def __init__(self, db_path: str = "leaderboard_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                market_id TEXT,
                symbol TEXT,
                signal TEXT,
                outcome TEXT,
                amount REAL,
                result TEXT,
                profit REAL,
                confidence REAL,
                edge REAL,
                win_rate_at_time REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                bets_placed INTEGER,
                bets_won INTEGER,
                bets_lost INTEGER,
                total_volume REAL,
                total_profit REAL,
                win_rate REAL,
                pool_share REAL
            )
        """)

        conn.commit()
        conn.close()

    def record_bet(self, market_id: str, symbol: str, signal: str,
                   amount: float, confidence: float, edge: float):
        """Record a placed bet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bets (market_id, symbol, signal, amount, confidence, edge)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (market_id, symbol, signal, amount, confidence, edge))

        conn.commit()
        conn.close()

    def get_current_win_rate(self, days: int = 7) -> float:
        """Calculate win rate over last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=days)

        cursor.execute("""
            SELECT COUNT(*) FROM bets
            WHERE timestamp > ? AND result IN ('WIN', 'LOSS')
        """, (cutoff,))

        total = cursor.fetchone()[0]

        if total == 0:
            return 0.0

        cursor.execute("""
            SELECT COUNT(*) FROM bets
            WHERE timestamp > ? AND result = 'WIN'
        """, (cutoff,))

        wins = cursor.fetchone()[0]
        conn.close()

        return wins / total

    def get_daily_stats(self, date: str = None) -> Dict:
        """Get stats for a specific date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as bets,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(amount) as volume,
                SUM(profit) as profit
            FROM bets
            WHERE DATE(timestamp) = ?
        """, (date,))

        row = cursor.fetchone()
        conn.close()

        if row[0] == 0:
            return {
                'bets': 0,
                'wins': 0,
                'losses': 0,
                'volume': 0,
                'profit': 0,
                'win_rate': 0
            }

        return {
            'bets': row[0],
            'wins': row[1],
            'losses': row[2],
            'volume': row[3],
            'profit': row[4],
            'win_rate': row[1] / row[0] if row[0] > 0 else 0
        }

    def get_leaderboard_prediction(self) -> Dict:
        """
        Predict current leaderboard standing

        Scores based on:
        - Consistency: Win rate × streak bonus
        - Active: Total volume (last 7 days)
        - Profit: Net profit (last 7 days)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        seven_days_ago = datetime.now() - timedelta(days=7)

        # Volume (7 days)
        cursor.execute("""
            SELECT SUM(amount) FROM bets
            WHERE timestamp > ?
        """, (seven_days_ago,))
        volume = cursor.fetchone()[0] or 0

        # Profit (7 days)
        cursor.execute("""
            SELECT SUM(profit) FROM bets
            WHERE timestamp > ?
        """, (seven_days_ago,))
        profit = cursor.fetchone()[0] or 0

        # Win rate
        win_rate = self.get_current_win_rate(7)

        # Streak
        cursor.execute("""
            SELECT result FROM bets
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (seven_days_ago,))

        results = [row[0] for row in cursor.fetchall()]
        streak = 0
        for r in results[:10]:  # Check last 10 bets
            if r == 'WIN':
                streak += 1
            else:
                break

        conn.close()

        # Calculate scores
        consistency_score = (win_rate * 100) + (streak * 5)
        active_score = volume  # Direct volume = score
        profit_score = max(0, profit * 10)  # Scale profit

        return {
            'consistency': consistency_score,
            'active': active_score,
            'profit': profit_score,
            'total': consistency_score + active_score + profit_score,
            'metrics': {
                'win_rate_7d': win_rate,
                'streak': streak,
                'volume_7d': volume,
                'profit_7d': profit
            }
        }


def calculate_bet_amount(
    bankroll: float,
    confidence: float,
    edge: float,
    config: LeaderboardConfig
) -> float:
    """
    Calculate optimal bet amount for leaderboard strategy

    Goals:
    - Maximize volume (more bets)
    - Maintain consistency (small sizes)
    - Grow profit (positive EV)
    """
    base_amount = bankroll * config.base_bet_pct

    # Confidence multiplier
    if confidence >= 90:
        multiplier = config.confidence_90_mult
    elif confidence >= 75:
        multiplier = config.confidence_75_mult
    else:
        multiplier = config.confidence_60_mult

    # Edge bonus (small bonus for higher edge)
    edge_bonus = 1.0 + (edge * 5)  # 10% edge = 1.5x bonus

    amount = base_amount * multiplier * edge_bonus

    # Cap at max
    max_amount = bankroll * config.max_bet_pct
    return min(amount, max_amount)


def should_bet_leaderboard(
    signal_analysis: Dict,
    current_bankroll: float,
    tracker: LeaderboardTracker,
    config: LeaderboardConfig
) -> tuple[bool, str]:
    """
    Decide if should bet (leaderboard-optimized)

    Returns:
        (should_bet, reason)
    """
    # Check basic filters
    confidence = signal_analysis.get('confidence', 0)
    edge = signal_analysis.get('edge', 0)
    distance = signal_analysis.get('distance_to_strike', 0)

    if confidence < config.min_confidence:
        return False, f"Confidence too low: {confidence}%"

    if edge < config.min_edge:
        return False, f"Edge too low: {edge*100:.1f}%"

    if abs(distance) < config.min_distance:
        return False, f"Too close to strike: {distance:.1f}%"

    # Check daily limits
    today = datetime.now().strftime('%Y-%m-%d')
    stats = tracker.get_daily_stats(today)

    if stats['profit'] <= -config.max_loss_per_day:
        return False, f"Daily loss limit reached: ${stats['profit']:.2f}"

    # Check loss streak
    # TODO: Query last 5 bets to check streak

    return True, "Pass"


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("Leaderboard Strategy Test")
    print("=" * 60)

    config = LeaderboardConfig()
    tracker = LeaderboardTracker()

    bankroll = 33.0

    # Test different signals
    test_signals = [
        {'confidence': 95, 'edge': 0.08, 'symbol': 'BTCUSDT'},
        {'confidence': 85, 'edge': 0.05, 'symbol': 'ETHUSDT'},
        {'confidence': 70, 'edge': 0.02, 'symbol': 'SOLUSDT'},
        {'confidence': 55, 'edge': 0.01, 'symbol': 'CCUSDT'},  # Should skip
    ]

    print("\n[1] Position Sizing:")
    for sig in test_signals:
        should, reason = should_bet_leaderboard(sig, bankroll, tracker, config)

        if should:
            amount = calculate_bet_amount(bankroll, sig['confidence'], sig['edge'], config)
            print(f"  {sig['symbol']}: ${amount:.2f} ({sig['confidence']}% conf, {sig['edge']*100:.1f}% edge)")
        else:
            print(f"  {sig['symbol']}: SKIP - {reason}")

    print("\n[2] Leaderboard Prediction:")
    prediction = tracker.get_leaderboard_prediction()
    print(f"  Consistency: {prediction['consistency']:.0f}")
    print(f"  Active: {prediction['active']:.0f}")
    print(f"  Profit: {prediction['profit']:.0f}")
    print(f"  TOTAL SCORE: {prediction['total']:.0f}")
