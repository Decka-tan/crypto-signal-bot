"""
Bankroll-Aware Always-Bet Strategy

Rules:
- Bet as many markets as possible with available balance
- Prioritize by signal quality (strongest first)
- Stop when balance < min_bet (5 CC)
- Track remaining balance in real-time
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum
import sqlite3
from datetime import datetime


class SignalQuality(Enum):
    STRONG = "strong"
    GOOD = "good"
    WEAK = "weak"
    DEFAULT = "default"


@dataclass
class BankrollAwareConfig:
    """Bankroll-aware betting config"""

    # Mandatory markets
    mandatory_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']

    # Bet sizes (in CC)
    min_bet = 5          # Minimum bet (platform requirement)
    bet_strong = 15
    bet_good = 10
    bet_weak = 7
    bet_default = 5

    # Signal thresholds
    conf_strong = 80
    conf_good = 70
    conf_weak = 60
    edge_strong = 0.05
    edge_good = 0.03
    edge_weak = 0.01

    # Timing
    binary_window_start = 45    # XX:45
    binary_window_end = 48      # XX:48
    interval_window_start = 105 # XX:105
    interval_window_end = 108   # XX:108


class BankrollManager:
    """Manage available balance and bet allocation"""

    def __init__(self, initial_balance_cc: float):
        self.initial_balance = initial_balance_cc
        self.current_balance = initial_balance_cc
        self.total_bet = 0
        self.bets_placed = []

    def can_bet(self, amount: float) -> bool:
        """Check if have enough balance"""
        return self.current_balance >= amount

    def place_bet(self, amount: float, market_id: str, symbol: str) -> bool:
        """Record a bet and deduct from balance"""
        if not self.can_bet(amount):
            return False

        self.current_balance -= amount
        self.total_bet += amount
        self.bets_placed.append({
            'time': datetime.now(),
            'market_id': market_id,
            'symbol': symbol,
            'amount': amount,
            'remaining_balance': self.current_balance
        })
        return True

    def get_remaining_bets_at_min(self, min_amount: float = 5) -> int:
        """How many more min bets can we place?"""
        return int(self.current_balance / min_amount)

    def is_bust(self) -> bool:
        """Check if busted (can't place min bet)"""
        return self.current_balance < 5


def classify_signal(signal: Dict, config: BankrollAwareConfig) -> SignalQuality:
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


def get_bet_amount_cc(quality: SignalQuality, config: BankrollAwareConfig) -> int:
    """Get bet amount based on signal quality"""
    if quality == SignalQuality.STRONG:
        return config.bet_strong
    elif quality == SignalQuality.GOOD:
        return config.bet_good
    elif quality == SignalQuality.WEAK:
        return config.bet_weak
    else:
        return config.bet_default


def prioritize_signals(
    all_signals: Dict[str, Dict],
    config: BankrollAwareConfig
) -> List[Tuple[str, Dict, SignalQuality, int]]:
    """
    Prioritize signals by quality

    Returns:
        List of (symbol, signal, quality, bet_amount) sorted by priority
    """
    prioritized = []

    for symbol, signal in all_signals.items():
        quality = classify_signal(signal, config)
        bet_amount = get_bet_amount_cc(quality, config)

        prioritized.append((symbol, signal, quality, bet_amount))

    # Sort by quality (strongest first) and then by bet amount
    quality_order = {
        SignalQuality.STRONG: 0,
        SignalQuality.GOOD: 1,
        SignalQuality.WEAK: 2,
        SignalQuality.DEFAULT: 3
    }

    prioritized.sort(key=lambda x: (quality_order[x[2]], -x[3]))

    return prioritized


def execute_bets_with_bankroll(
    all_signals: Dict[str, Dict],
    bankroll_manager: BankrollManager,
    config: BankrollAwareConfig
) -> List[Dict]:
    """
    Execute bets prioritized by quality, stop when bankroll runs out

    Returns:
        List of placed bets
    """
    prioritized = prioritize_signals(all_signals, config)
    placed_bets = []

    print(f"\n[cyan]Bankroll: {bankroll_manager.current_balance:.1f} CC[/cyan]")
    print(f"[cyan]Can place: {bankroll_manager.get_remaining_bets_at_min()} more min bets[/cyan]\n")

    for symbol, signal, quality, bet_amount in prioritized:
        # Check if we have enough balance
        if not bankroll_manager.can_bet(bet_amount):
            print(f"  [yellow][SKIP] {symbol}: Insufficient balance ({bankroll_manager.current_balance:.1f} CC left)[/yellow]")
            continue

        # Place the bet
        if bankroll_manager.place_bet(bet_amount, "market_id", symbol):
            placed_bets.append({
                'symbol': symbol,
                'amount': bet_amount,
                'quality': quality.value,
                'signal': signal.get('signal', 'N/A'),
                'confidence': signal.get('confidence', 0),
                'edge': signal.get('edge', 0)
            })

            print(f"  [green][BET] {symbol}: {bet_amount} CC ({quality.value}) - {bankroll_manager.current_balance:.1f} CC remaining[/green]")

        # Check if bust
        if bankroll_manager.is_bust():
            print(f"\n  [red]BANKROLL BUST! Cannot place more bets.[/red]")
            break

    return placed_bets


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("BANKROLL-AWARE STRATEGY TEST")
    print("=" * 60)

    config = BankrollAwareConfig()
    bankroll = BankrollManager(initial_balance_cc=33)

    print(f"\nInitial Balance: {bankroll.initial_balance} CC")
    print(f"Min bet: {config.min_bet} CC")
    print(f"Max bets at min: {bankroll.get_remaining_bets_at_min()}")

    # Simulate 8 markets with varying signal qualities
    test_signals = {
        'BTCUSDT': {'confidence': 85, 'edge': 0.08, 'is_bettable': True, 'signal': 'YES'},
        'ETHUSDT': {'confidence': 75, 'edge': 0.04, 'is_bettable': True, 'signal': 'YES'},
        'SOLUSDT': {'confidence': 65, 'edge': 0.02, 'is_bettable': True, 'signal': 'NO'},
        'CCUSDT': {'confidence': 55, 'edge': 0.01, 'is_bettable': False, 'signal': 'YES'},
        'BNBUSDT': {'confidence': 90, 'edge': 0.10, 'is_bettable': True, 'signal': 'YES'},
        'XRPUSDT': {'confidence': 70, 'edge': 0.03, 'is_bettable': True, 'signal': 'NO'},
        'ADAUSDT': {'confidence': 60, 'edge': 0.015, 'is_bettable': True, 'signal': 'YES'},
        'DOGEUSDT': {'confidence': 80, 'edge': 0.06, 'is_bettable': True, 'signal': 'NO'},
    }

    print("\n[1] Signal Analysis (8 markets):")
    for symbol, signal in test_signals.items():
        quality = classify_signal(signal, config)
        amount = get_bet_amount_cc(quality, config)
        conf = signal['confidence']
        edg = signal['edge']
        print(f"  {symbol}: {conf}% conf, {edg*100:.1f}% edge -> {quality.value.upper():8} -> {amount} CC")

    print("\n[2] Prioritized Betting (33 CC bankroll):")
    print("=" * 60)

    placed = execute_bets_with_bankroll(test_signals, bankroll, config)

    print("\n" + "=" * 60)
    print("[3] Results:")
    print(f"  Bets placed: {len(placed)}")
    print(f"  Total wagered: {bankroll.total_bet} CC")
    print(f"  Remaining: {bankroll.current_balance:.1f} CC")
    print(f"  Bust: {'YES' if bankroll.is_bust() else 'NO'}")

    print("\n[4] Placed Bets Detail:")
    for bet in placed:
        print(f"  {bet['symbol']}: {bet['amount']} CC ({bet['quality']})")

    print("\n[5] Skipped Markets:")
    skipped_count = len(test_signals) - len(placed)
    if skipped_count > 0:
        print(f"  {skipped_count} markets skipped due to insufficient balance")
    else:
        print(f"  All markets covered!")

    print("\n" + "=" * 60)
