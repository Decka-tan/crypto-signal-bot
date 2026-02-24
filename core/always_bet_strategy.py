"""
Always-Bet Strategy for Leaderboard Consistency

KEY INSIGHT: Must bet EVERY hour on ALL markets
- No skipping allowed
- Bet size varies based on signal strength
- Default bet when no signal

Leaderboard Metrics:
- Consistency: 100% participation (no skips)
- Active: Maximum volume (always betting)
- Profit: Optimize bet sizing based on edge
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class SignalQuality(Enum):
    """Signal quality levels"""
    STRONG = "strong"      # 80%+ conf, 5%+ edge
    GOOD = "good"          # 70-79% conf, 3-5% edge
    WEAK = "weak"          # 60-69% conf, 1-3% edge
    DEFAULT = "default"    # No signal, use trend


@dataclass
class AlwaysBetConfig:
    """
    Always-bet strategy config

    Goal: 100% market participation for leaderboard consistency
    """

    # Mandatory markets (every hour)
    mandatory_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']

    # Bet sizes (based on signal quality)
    bet_strong = 2.00      # Strong signal
    bet_good = 1.50        # Good signal
    bet_weak = 1.00        # Weak signal
    bet_default = 0.50     # Default/no signal

    # Thresholds
    conf_strong = 80       # Strong confidence
    conf_good = 70         # Good confidence
    conf_weak = 60         # Weak confidence (minimum)
    edge_strong = 0.05     # 5% edge
    edge_good = 0.03       # 3% edge
    edge_weak = 0.01       # 1% edge

    # Default bet strategy (when no signal)
    default_bet_mode = "trend"  # "trend", "random", "skip"

    # Targets
    bets_per_hour = 4      # 4 binary markets
    interval_bets = 4      # 4 interval markets (every 2 hours)


def classify_signal(signal: Dict, config: AlwaysBetConfig = None) -> SignalQuality:
    """
    Classify signal quality

    Args:
        signal: Signal analysis dict
        config: Strategy config (optional, uses default if None)

    Returns:
        SignalQuality enum
    """
    if config is None:
        config = AlwaysBetConfig()

    confidence = signal.get('confidence', 0)
    edge = signal.get('edge', 0)
    is_bettable = signal.get('is_bettable', False)

    # Check if signal exists
    if not is_bettable or confidence < config.conf_weak or edge < config.edge_weak:
        return SignalQuality.DEFAULT

    # Classify quality
    if confidence >= config.conf_strong and edge >= config.edge_strong:
        return SignalQuality.STRONG
    elif confidence >= config.conf_good and edge >= config.edge_good:
        return SignalQuality.GOOD
    elif confidence >= config.conf_weak and edge >= config.edge_weak:
        return SignalQuality.WEAK
    else:
        return SignalQuality.DEFAULT


def get_bet_amount(quality: SignalQuality, config: AlwaysBetConfig) -> float:
    """Get bet amount based on signal quality"""
    if quality == SignalQuality.STRONG:
        return config.bet_strong
    elif quality == SignalQuality.GOOD:
        return config.bet_good
    elif quality == SignalQuality.WEAK:
        return config.bet_weak
    else:  # DEFAULT
        return config.bet_default


def get_default_outcome(
    symbol: str,
    current_price: float,
    recent_trend: str,
    config: AlwaysBetConfig
) -> str:
    """
    Determine default outcome when no strong signal

    Strategies:
    - "trend": Follow recent price direction
    - "random": 50/50 (not recommended)
    - "skip": Don't bet (breaks consistency!)

    Args:
        symbol: Trading pair
        current_price: Current market price
        recent_trend: "up", "down", or "neutral"
        config: Strategy config

    Returns:
        "YES" or "NO"
    """
    if config.default_bet_mode == "trend":
        # Follow the trend
        if recent_trend == "up":
            return "YES"
        elif recent_trend == "down":
            return "NO"
        else:
            # Neutral: slight bias to YES (markets tend to go up)
            return "YES"

    elif config.default_bet_mode == "random":
        import random
        return random.choice(["YES", "NO"])

    else:  # skip (not recommended for leaderboard)
        return None


class AlwaysBetTracker:
    """
    Track always-bet performance

    Key metric: Consistency = % of hours with bets placed
    """

    def __init__(self, db_path: str = "always_bet_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hourly_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hour DATETIME UNIQUE,
                symbol TEXT,
                signal_quality TEXT,
                outcome TEXT,
                amount REAL,
                result TEXT,
                profit REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consistency_log (
                date TEXT PRIMARY KEY,
                total_hours INTEGER,
                hours_with_bets INTEGER,
                consistency_pct REAL,
                total_bets INTEGER,
                total_volume REAL,
                total_profit REAL
            )
        """)

        conn.commit()
        conn.close()

    def record_bet(
        self,
        hour: datetime,
        symbol: str,
        quality: SignalQuality,
        outcome: str,
        amount: float
    ):
        """Record a placed bet"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hourly_bets (hour, symbol, signal_quality, outcome, amount)
            VALUES (?, ?, ?, ?, ?)
        """, (hour, symbol, quality.value, outcome, amount))

        conn.commit()
        conn.close()

    def get_consistency_score(self, days: int = 7) -> Dict:
        """
        Calculate consistency score

        Consistency = % of hours where all mandatory bets were placed

        Returns:
            Dict with consistency metrics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=days)

        # Get all hours in range
        cursor.execute("""
            SELECT DISTINCT hour FROM hourly_bets
            WHERE hour > ?
            ORDER BY hour
        """, (cutoff,))

        hours = [row[0] for row in cursor.fetchall()]

        # Count bets per hour
        hours_with_full_bets = 0
        total_hours = len(hours)
        total_bets = 0
        total_volume = 0

        for hour in hours:
            cursor.execute("""
                SELECT COUNT(*), SUM(amount)
                FROM hourly_bets
                WHERE hour = ?
            """, (hour,))

            count, volume = cursor.fetchone()
            total_bets += count
            total_volume += volume or 0

            # Full participation = 4 bets (all mandatory symbols)
            if count >= 4:
                hours_with_full_bets += 1

        # Get profit
        cursor.execute("""
            SELECT SUM(profit) FROM hourly_bets
            WHERE hour > ? AND result IS NOT NULL
        """, (cutoff,))

        profit = cursor.fetchone()[0] or 0

        conn.close()

        consistency_pct = (hours_with_full_bets / total_hours * 100) if total_hours > 0 else 0

        return {
            'consistency': consistency_pct,
            'hours_tracked': total_hours,
            'hours_with_full_bets': hours_with_full_bets,
            'total_bets': total_bets,
            'total_volume': total_volume,
            'total_profit': profit,
            'bets_per_hour': total_bets / total_hours if total_hours > 0 else 0
        }


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("ALWAYS-BET STRATEGY TEST")
    print("=" * 60)

    config = AlwaysBetConfig()

    print("\n[1] Mandatory Markets:")
    for symbol in config.mandatory_symbols:
        print(f"  - {symbol}")

    print("\n[2] Signal Quality Classification:")

    test_signals = [
        {'confidence': 85, 'edge': 0.08, 'is_bettable': True},  # Strong
        {'confidence': 75, 'edge': 0.04, 'is_bettable': True},  # Good
        {'confidence': 65, 'edge': 0.02, 'is_bettable': True},  # Weak
        {'confidence': 55, 'edge': 0.01, 'is_bettable': False}, # Default
        {'confidence': 70, 'edge': 0.01, 'is_bettable': True},  # Weak
    ]

    for sig in test_signals:
        quality = classify_signal(sig, config)
        amount = get_bet_amount(quality, config)
        conf = sig['confidence']
        edg = sig['edge']
        print(f"  Conf={conf}%, Edge={edg*100:.1f}% -> {quality.value.upper():8} -> ${amount:.2f}")

    print("\n[3] Daily Volume Projection:")

    # 4 bets/hour × 24 hours = 96 bets/day
    # Average bet size varies
    avg_bet = (config.bet_strong + config.bet_good + config.bet_weak + config.bet_default) / 4
    bets_per_day = len(config.mandatory_symbols) * 24

    daily_volume = avg_bet * bets_per_day

    print(f"  Bets per day: {bets_per_day}")
    print(f"  Avg bet size: ${avg_bet:.2f}")
    print(f"  Daily volume: ${daily_volume:.2f}")
    print(f"  Monthly volume: ${daily_volume * 30:.2f}")

    print("\n[4] Consistency Target:")
    print(f"  100% participation = NO SKIPS")
    print(f"  Every hour = 4 binary bets")
    print(f"  Every 2 hours = +4 interval bets")
    print(f"  Total = 96-120 bets/day")

    print("\n[5] Profit Projection (at 65% win rate):")

    win_rate = 0.65
    avg_profit_per_win = avg_bet * 0.98  # Minus 2% fee
    avg_loss = -avg_bet

    wins = bets_per_day * win_rate
    losses = bets_per_day * (1 - win_rate)

    daily_profit = (wins * avg_profit_per_win) + (losses * avg_loss)

    print(f"  Wins: {wins:.1f} × +${avg_profit_per_win:.2f}")
    print(f"  Losses: {losses:.1f} × ${avg_loss:.2f}")
    print(f"  Daily profit: ${daily_profit:.2f}")
    print(f"  Monthly profit: ${daily_profit * 30:.2f}")
