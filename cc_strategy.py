"""
Final Strategy - CC Denomination

Currency: CC (Canton Coin)
Min bet: 5 CC
Bankroll: ~200 CC (based on $33 @ $0.16/CC)
"""

from dataclasses import dataclass
from typing import Dict
from enum import Enum


class SignalQuality(Enum):
    """Signal quality levels"""
    STRONG = "strong"
    GOOD = "good"
    WEAK = "weak"
    DEFAULT = "default"


@dataclass
class AlwaysBetConfigCC:
    """
    Always-bet strategy config (CC denomination)

    Goal: 100% market participation for leaderboard consistency
    """

    # Mandatory markets (every hour)
    mandatory_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']

    # Bet sizes (in CC)
    bet_strong = 15      # Strong signal
    bet_good = 10        # Good signal
    bet_weak = 7         # Weak signal
    bet_default = 5      # Default/no signal (minimum!)

    # Thresholds
    conf_strong = 80
    conf_good = 70
    conf_weak = 60
    edge_strong = 0.05
    edge_good = 0.03
    edge_weak = 0.01

    # Targets
    bets_per_hour_binary = 4
    bets_per_hour_interval = 2  # Average over 24 hours


def classify_signal(signal: Dict, config: AlwaysBetConfigCC) -> SignalQuality:
    """Classify signal quality"""
    confidence = signal.get('confidence', 0)
    edge = signal.get('edge', 0)
    is_bettable = signal.get('is_bettable', False)

    if not is_bettable or confidence < config.conf_weak or edge < config.edge_weak:
        return SignalQuality.DEFAULT

    if confidence >= config.conf_strong and edge >= config.edge_strong:
        return SignalQuality.STRONG
    elif confidence >= config.conf_good and edge >= config.edge_good:
        return SignalQuality.GOOD
    elif confidence >= config.conf_weak and edge >= config.edge_weak:
        return SignalQuality.WEAK
    else:
        return SignalQuality.DEFAULT


def get_bet_amount_cc(quality: SignalQuality, config: AlwaysBetConfigCC) -> int:
    """Get bet amount in CC"""
    if quality == SignalQuality.STRONG:
        return config.bet_strong
    elif quality == SignalQuality.GOOD:
        return config.bet_good
    elif quality == SignalQuality.WEAK:
        return config.bet_weak
    else:  # DEFAULT
        return config.bet_default


# Test and projections
if __name__ == "__main__":
    print("=" * 60)
    print("FINAL STRATEGY - CC DENOMINATION")
    print("=" * 60)

    config = AlwaysBetConfigCC()

    print("\n[1] Mandatory Markets:")
    for symbol in config.mandatory_symbols:
        print(f"  - {symbol}")

    print("\n[2] Bet Sizing (in CC):")
    print(f"  Strong signal (80%+ conf, 5%+ edge):  {config.bet_strong} CC")
    print(f"  Good signal (70-79% conf, 3-5% edge):  {config.bet_good} CC")
    print(f"  Weak signal (60-69% conf, 1-3% edge):  {config.bet_weak} CC")
    print(f"  Default/No signal:                     {config.bet_default} CC (minimum!)")

    print("\n[3] Timing:")
    print("  Binary (hourly):")
    print("    - Window: XX:45-48")
    print("    - Close: XX:50")
    print("    - Markets: 4 (BTC, ETH, SOL, CC)")
    print()
    print("  Interval (every 2 hours):")
    print("    - Window: XX:105-108")
    print("    - Close: XX:110")
    print("    - Markets: 4")

    print("\n[4] Daily Volume Projection:")

    # Binary: 4 bets/hour x 24 hours = 96 bets
    # Interval: 4 bets/2hours x 12 = 24 bets
    # Total: 120 bets/day

    binary_bets_per_day = config.bets_per_hour_binary * 24
    interval_bets_per_day = 24  # 4 bets every 2 hours
    total_bets_per_day = binary_bets_per_day + interval_bets_per_day

    # Average bet size (assuming mix of signals)
    avg_bet_cc = (config.bet_strong + config.bet_good + config.bet_weak + config.bet_default) / 4

    daily_volume_cc = total_bets_per_day * avg_bet_cc
    monthly_volume_cc = daily_volume_cc * 30

    print(f"  Binary bets:   {binary_bets_per_day}/day")
    print(f"  Interval bets: {interval_bets_per_day}/day")
    print(f"  Total bets:    {total_bets_per_day}/day")
    print(f"  Avg bet size:  {avg_bet_cc:.1f} CC")
    print(f"  Daily volume:  {daily_volume_cc:.0f} CC")
    print(f"  Monthly volume: {monthly_volume_cc:.0f} CC")

    print("\n[5] Profit Projection (at 70% win rate):")

    win_rate = 0.70
    avg_profit_per_win_cc = avg_bet_cc * 0.98  # Minus 2% fee
    avg_loss_cc = -avg_bet_cc

    wins = total_bets_per_day * win_rate
    losses = total_bets_per_day * (1 - win_rate)

    daily_profit_cc = (wins * avg_profit_per_win_cc) + (losses * avg_loss_cc)
    monthly_profit_cc = daily_profit_cc * 30

    print(f"  Wins:  {wins:.1f} x +{avg_profit_per_win_cc:.1f} CC")
    print(f"  Losses: {losses:.1f} x {avg_loss_cc:.1f} CC")
    print(f"  Daily profit:  {daily_profit_cc:.1f} CC")
    print(f"  Monthly profit: {monthly_profit_cc:.1f} CC")

    print("\n[6] Leaderboard Prediction:")
    print(f"  Consistency: 100% (no skips!)")
    print(f"  Pool Share: TOP 10% ({monthly_volume_cc:.0f} CC/month)")
    print(f"  Profit: TOP 5% ({monthly_profit_cc:.0f} CC/month)")
    print(f"  Overall: TOP 3 MVP!")

    print("\n[7] Bankroll Management:")
    print(f"  Starting: ~200 CC")
    print(f"  Daily profit: ~{daily_profit_cc:.0f} CC")
    print(f"  ROI/day: {daily_profit_cc / 200 * 100:.1f}%")
    print(f"  Compound growth: YES")

    print("\n" + "=" * 60)
