"""
PREDICTION MARKET SIGNAL GENERATOR
Binary markets: Will price be ABOVE/BELOW strike at time X?

LOGIC:
1. Compare current price vs strike price
2. Calculate distance percentage
3. Check volatility: Can price move enough in remaining time?
4. Determine signal (YES/NO) based on current position
5. Calculate confidence based on distance + volatility + time
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime


@dataclass
class PredictionSignal:
    """Prediction market signal"""
    symbol: str
    current_price: float
    strike_price: float
    signal: str  # "YES" or "NO"
    confidence: float  # 0-100%
    edge: float  # Expected edge vs market
    distance_pct: float  # How far from strike (%)
    distance_dollars: float  # How far from strike ($)
    volatility_5m: float  # Recent volatility (5-min std dev)
    time_until_close: int  # Minutes until market close
    is_bettable: bool
    reasons: List[str]


class PredictionMarketGenerator:
    """Generate signals for binary prediction markets"""

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # Thresholds
        self.min_confidence = self.config.get('min_confidence', 60)
        self.min_edge = self.config.get('min_edge', 0.01)  # 1%
        self.volatility_window = 20  # Use last 20 candles for volatility

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: float,
        strike_price: float,
        time_until_close: int,
        market_odds: Optional = None
    ) -> PredictionSignal:
        """
        Generate prediction market signal

        Args:
            symbol: Trading pair
            df: Price data (candlesticks)
            current_price: Current market price
            strike_price: Target price from market question
            time_until_close: Minutes until market close
            market_odds: Current odds from Unhedged (optional)
        """
        # 1. Calculate distance to strike
        distance_dollars = current_price - strike_price
        distance_pct = (distance_dollars / strike_price) * 100

        # 2. Calculate volatility (5-min std dev of returns)
        volatility_5m = self._calculate_volatility(df)

        # 3. Determine signal based on current position
        if current_price > strike_price:
            signal = "YES"  # Currently above, betting it stays above
            side = "above"
        else:
            signal = "NO"   # Currently below, betting it stays below
            side = "below"

        # 4. Calculate probability: Can price move enough to cross strike?
        # Probability based on statistical likelihood of crossing
        probability = self._calculate_crossing_probability(
            distance_pct,
            volatility_5m,
            time_until_close,
            side
        )

        confidence = probability * 100

        # 5. Calculate edge vs market
        edge = self._calculate_edge(probability, market_odds)

        # 6. Determine if bettable
        is_bettable = self._is_bettable(
            confidence,
            edge,
            distance_pct,
            volatility_5m
        )

        # 7. Generate reasons
        reasons = self._generate_reasons(
            distance_pct,
            volatility_5m,
            time_until_close,
            probability,
            signal
        )

        return PredictionSignal(
            symbol=symbol,
            current_price=current_price,
            strike_price=strike_price,
            signal=signal,
            confidence=confidence,
            edge=edge,
            distance_pct=distance_pct,
            distance_dollars=distance_dollars,
            volatility_5m=volatility_5m,
            time_until_close=time_until_close,
            is_bettable=is_bettable,
            reasons=reasons
        )

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate 5-min volatility (std dev of returns)"""
        if df is None or len(df) < 10:
            return 0.02  # Default 2%

        # Calculate returns
        returns = df['close'].pct_change().dropna()

        # Use recent volatility (last 20 candles)
        recent_returns = returns.tail(min(self.volatility_window, len(returns)))

        # Annualized vol = std * sqrt(288 * 5) (288 5-min periods per day)
        # But we want 5-min vol, so just use std directly
        vol = float(recent_returns.std())

        return vol if not np.isnan(vol) else 0.02

    def _calculate_crossing_probability(
        self,
        distance_pct: float,
        volatility_5m: float,
        time_until_close: int,
        side: str
    ) -> float:
        """
        Calculate probability that price will stay on current side

        Uses simplified statistical model:
        - Probability decreases as distance approaches 0
        - Probability decreases as volatility increases
        - Probability increases as time decreases

        Formula: P = 0.5 + (distance_strength / sqrt(time)) * vol_adjustment
        """
        if volatility_5m == 0:
            volatility_5m = 0.01  # Avoid division by zero

        # How strong is the current position? (in standard deviations)
        distance_strength = abs(distance_pct) / 100  # Convert to decimal

        # Expected move in remaining time (random walk)
        # Expected std deviation = vol * sqrt(time_periods)
        # 5-min vol, so time_periods = time_until_close / 5
        time_periods = max(1, time_until_close / 5)
        expected_std = volatility_5m * np.sqrt(time_periods)

        # How many standard deviations away from strike?
        z_score = distance_strength / expected_std if expected_std > 0 else 0

        # Convert z-score to probability using sigmoid
        # P(stay) = sigmoid(z_score * confidence_factor)
        confidence_factor = 2.0  # Higher = more confident
        probability = 1 / (1 + np.exp(-z_score * confidence_factor))

        # Clip to reasonable range
        probability = max(0.05, min(0.95, probability))

        return probability

    def _calculate_edge(self, probability: float, market_odds) -> float:
        """Calculate edge vs market implied probability"""
        if market_odds is None:
            # No market odds, assume 50/50
            implied_prob = 0.5
        else:
            implied_prob = market_odds.implied_prob_yes

        # If we predict YES
        edge = probability - implied_prob

        return edge

    def _is_bettable(
        self,
        confidence: float,
        edge: float,
        distance_pct: float,
        volatility_5m: float
    ) -> bool:
        """
        Determine if signal is bettable

        LEADERBOARD MODE: Bet ALL markets with positive edge!
        Consistency metric requires 100% participation.
        """
        # Must have positive edge (that's it!)
        if edge <= 0:
            return False

        # Leaderboard: Bet everything with edge, no confidence threshold!
        # This ensures 100% market participation for consistency metric

        return True

    def _generate_reasons(
        self,
        distance_pct: float,
        volatility_5m: float,
        time_until_close: int,
        probability: float,
        signal: str
    ) -> List[str]:
        """Generate explanation for signal"""
        reasons = []

        # Distance reason
        if distance_pct > 0:
            reasons.append(f"Currently {distance_pct:+.2f}% ABOVE strike")
        else:
            reasons.append(f"Currently {distance_pct:+.2f}% BELOW strike")

        # Volatility reason
        if volatility_5m < 0.01:
            reasons.append(f"Low volatility ({volatility_5m*100:.2f}%) - stable")
        elif volatility_5m > 0.03:
            reasons.append(f"High volatility ({volatility_5m*100:.2f}%) - risky")
        else:
            reasons.append(f"Moderate volatility ({volatility_5m*100:.2f}%)")

        # Time reason
        if time_until_close < 3:
            reasons.append(f"Only {time_until_close} min left - low time risk")
        elif time_until_close < 10:
            reasons.append(f"{time_until_close} min left - time decay")

        # Probability reason
        if probability > 0.8:
            reasons.append(f"High confidence ({probability*100:.0f}%)")
        elif probability < 0.6:
            reasons.append(f"Low confidence ({probability*100:.0f}%)")

        return reasons


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("PREDICTION MARKET SIGNAL TEST")
    print("=" * 60)

    # Simulate CC market
    generator = PredictionMarketGenerator()

    # Create sample data
    dates = pd.date_range(start='12:00', periods=100, freq='5min')
    np.random.seed(42)

    # Generate price data with volatility
    base_price = 0.165
    returns = np.random.normal(0, 0.01, 100)  # 1% volatility
    prices = [base_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    df = pd.DataFrame({
        'timestamp': dates,
        'close': prices
    })
    df.set_index('timestamp', inplace=True)

    # Test scenarios
    scenarios = [
        {
            'name': 'CC ABOVE, moderate distance',
            'current': 0.170,
            'strike': 0.164,
            'time': 2
        },
        {
            'name': 'CC BELOW, very close',
            'current': 0.1645,
            'strike': 0.164,
            'time': 5
        },
        {
            'name': 'BTC BELOW, far distance',
            'current': 62736,
            'strike': 65000,
            'time': 3
        }
    ]

    for scenario in scenarios:
        print(f"\n[Scenario] {scenario['name']}")
        print("-" * 60)

        signal = generator.generate_signal(
            symbol='CCUSDT' if 'CC' in scenario['name'] else 'BTCUSDT',
            df=df,
            current_price=scenario['current'],
            strike_price=scenario['strike'],
            time_until_close=scenario['time'],
            market_odds=None
        )

        print(f"Current: ${signal.current_price:.6f}")
        print(f"Strike:  ${signal.strike_price:.6f}")
        print(f"Distance: {signal.distance_pct:+.2f}% (${signal.distance_dollars:+.6f})")
        print(f"Signal: {signal.signal}")
        print(f"Confidence: {signal.confidence:.1f}%")
        print(f"Edge: {signal.edge*100:+.2f}%")
        print(f"Volatility: {signal.volatility_5m*100:.2f}%")
        print(f"Bettable: {signal.is_bettable}")
        print(f"Reasons:")
        for reason in signal.reasons:
            print(f"  - {reason}")

    print("\n" + "=" * 60)
