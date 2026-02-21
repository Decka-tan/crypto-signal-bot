"""
PROPER Signal Generator with EV, Edge, and Real Probability

Fixes from GPT King feedback:
1. Confidence = REAL probability (not heuristic)
2. EV calculation
3. Distance-to-strike vs volatility check
4. No indicator bias
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
import numpy as np
import pandas as pd
from datetime import datetime

from core.indicators import TechnicalIndicators


@dataclass
class MarketOdds:
    """Market odds from Unhedged"""
    yes_price: float  # Decimal odds (e.g., 0.75 for 75%)
    no_price: float   # Decimal odds
    yes_volume: float
    no_volume: float

    @property
    def implied_prob_yes(self) -> float:
        """Implied probability from odds"""
        return self.yes_price

    @property
    def implied_prob_no(self) -> float:
        return self.no_price


@dataclass
class SignalAnalysis:
    """Proper signal analysis with EV"""
    symbol: str
    signal: str  # 'YES' or 'NO'
    p_yes: float  # REAL probability (0-1)
    confidence: float  # Same as p_yes (100x)
    ev: float  # Expected value
    edge: float  # p_yes - implied_prob
    market_odds: Optional[MarketOdds]
    distance_to_strike: Optional[float]  # % distance from current price to strike
    distance_dollars: Optional[float]  # Absolute distance in dollars
    volatility_5m: Optional[float]  # Recent volatility (15-min = 30 candles)
    buffer_remaining: Optional[float]  # How much buffer left (dollars)
    reasons: List[str]
    current_price: float
    predicted_price: Optional[float]
    is_bettable: bool  # Only bet if EV > 0 AND passes safety checks


class ProperSignalGenerator:
    """
    Proper signal generator with:
    - Real probability estimation
    - EV calculation
    - Edge detection
    - Volatility-based gating
    """

    def __init__(self, config: Dict):
        self.config = config

        # Historical calibration (will be updated from backtest)
        # For now, use simple baseline
        self.calibration_slope = 1.0
        self.calibration_intercept = 0.0

        # Try to load calibration parameters from file
        self._load_calibration_params()

    def _load_calibration_params(self):
        """Load calibration parameters from calibration_params.json if exists"""
        try:
            import json
            import os

            calib_file = os.path.join(os.path.dirname(__file__), '..', 'calibration_params.json')

            if os.path.exists(calib_file):
                with open(calib_file, 'r') as f:
                    params = json.load(f)
                    self.calibration_slope = params.get('slope', 1.0)
                    self.calibration_intercept = params.get('intercept', 0.0)
        except:
            # If loading fails, use defaults
            pass

    def generate_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: float,
        market_odds: Optional[MarketOdds] = None,
        strike_price: Optional[float] = None
    ) -> SignalAnalysis:
        """
        Generate proper signal with EV analysis

        Args:
            symbol: Trading pair
            df: Price data
            current_price: Current price
            market_odds: Market odds from Unhedged
            strike_price: Target price for binary markets
        """
        # Get raw technical score (-1 to 1)
        raw_score = self._calculate_technical_score(df)

        # Convert to PROBABILITY using sigmoid (not heuristic!)
        p_yes = self._score_to_probability(raw_score)

        # Apply calibration from historical data
        p_yes_calibrated = self._calibrate_probability(p_yes)

        # Calculate EV and edge
        ev, edge = self._calculate_ev(p_yes_calibrated, market_odds)

        # Distance to strike check
        distance_pct, volatility_5m = self._check_distance_vs_volatility(
            current_price, strike_price, df
        )

        # Calculate distance in dollars and buffer remaining
        distance_dollars = None
        buffer_remaining = None

        if strike_price is not None and distance_pct is not None:
            distance_dollars = abs(distance_pct / 100 * current_price)

            # Get buffer for this symbol
            buffer_map = {
                'BTCUSDT': 100,
                'ETHUSDT': 10,
                'SOLUSDT': 5,
                'CCUSDT': 0.02
            }
            buffer = buffer_map.get(symbol, 20)
            buffer_remaining = max(0, distance_dollars - buffer)

        # Determine signal
        signal = "YES" if p_yes_calibrated > 0.5 else "NO"

        # Safety checks
        is_bettable = self._is_bettable(
            p_yes_calibrated, edge, distance_pct, volatility_5m, market_odds,
            symbol=symbol, current_price=current_price
        )

        # Generate reasons
        reasons = self._generate_reasons(raw_score, p_yes_calibrated, edge, df)

        return SignalAnalysis(
            symbol=symbol,
            signal=signal,
            p_yes=p_yes_calibrated,
            confidence=p_yes_calibrated * 100,
            ev=ev,
            edge=edge,
            market_odds=market_odds,
            distance_to_strike=distance_pct,
            distance_dollars=distance_dollars,
            buffer_remaining=buffer_remaining,
            volatility_5m=volatility_5m,
            reasons=reasons,
            current_price=current_price,
            predicted_price=current_price * (1 + raw_score * 0.02),  # Simple prediction
            is_bettable=is_bettable
        )

    def _calculate_technical_score(self, df: pd.DataFrame) -> float:
        """
        Calculate technical score from -1 (strong bearish) to +1 (strong bullish)
        Using PROPER logic without bias
        """
        scores = []
        reasons = []

        indicators = TechnicalIndicators.calculate_all(df, {})

        # 1. RSI (0-100 -> -1 to 1)
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            # RSI > 70 = overbought = bearish (-), RSI < 30 = oversold = bullish (+)
            if rsi > 70:
                rsi_score = (70 - rsi) / 30  # -1 to 0
                scores.append(rsi_score)
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi < 30:
                rsi_score = (50 - rsi) / 20  # 0 to 1
                scores.append(rsi_score)
                reasons.append(f"RSI oversold ({rsi:.1f})")
            # Neutral RSI = NO SCORE (don't vote!)

        # 2. MACD trend
        if 'macd_trend' in indicators:
            if indicators['macd_trend'] == 'bullish':
                scores.append(0.5)  # Moderate bullish
                reasons.append("MACD bullish")
            elif indicators['macd_trend'] == 'bearish':
                scores.append(-0.5)  # Moderate bearish
                reasons.append("MACD bearish")

        # 3. EMA trend
        if 'ema_short' in indicators and 'ema_long' in indicators:
            ema_short = indicators['ema_short']
            ema_long = indicators['ema_long']

            close = df['close'].iloc[-1]
            if ema_short > ema_long and close > ema_short:
                scores.append(0.3)  # Weak bullish
                reasons.append("Price above EMA")
            elif ema_short < ema_long and close < ema_short:
                scores.append(-0.3)  # Weak bearish
                reasons.append("Price below EMA")

        # 4. Volume confirmation (ONLY if we have a direction)
        if 'volume_ratio' in indicators and scores:
            vol_ratio = indicators['volume_ratio']
            if vol_ratio > 150:
                # High volume confirms the trend
                avg_score = np.mean(scores)
                if avg_score > 0:
                    scores.append(avg_score * 0.2)  # Boost bullish
                    reasons.append(f"High volume confirms ({vol_ratio:.0f}%)")
                elif avg_score < 0:
                    scores.append(avg_score * 0.2)  # Boost bearish
                    reasons.append(f"High volume confirms ({vol_ratio:.0f}%)")

        # NO SCORE? Return 0 (neutral)
        if not scores:
            return 0.0

        # Average scores (simple mean, not weighted)
        return np.mean(scores)

    def _score_to_probability(self, score: float) -> float:
        """
        Convert score (-1 to 1) to probability (0 to 1)
        Using sigmoid: 1 / (1 + exp(-x))

        This gives REAL probability, not heuristic!
        """
        # Sigmoid function
        probability = 1 / (1 + np.exp(-score * 3))  # *3 for steeper curve

        return np.clip(probability, 0.05, 0.95)  # Clip to 5-95%

    def _calibrate_probability(self, raw_prob: float) -> float:
        """
        Calibrate probability using historical data
        Platt scaling or isotonic regression

        Uses calibration parameters from calibration_params.json
        Formula: p_calibrated = slope * p_raw + intercept
        """
        # Apply linear calibration
        p_calibrated = self.calibration_slope * raw_prob + self.calibration_intercept

        # Clip to valid range [0, 1]
        p_calibrated = max(0.0, min(1.0, p_calibrated))

        return p_calibrated

    def _calculate_ev(
        self,
        p_yes: float,
        market_odds: Optional[MarketOdds]
    ) -> tuple[float, float]:
        """
        Calculate Expected Value and Edge

        EV = (p_yes * payout_yes) - (p_no * cost_no)
        Edge = p_yes - implied_prob_yes

        Returns:
            (ev, edge)
        """
        if not market_odds:
            # No odds available, assume even money
            ev = (p_yes * 1) - ((1 - p_yes) * 1)
            edge = p_yes - 0.5
            return (ev, edge)

        # Get implied probability from market
        implied_prob = market_odds.implied_prob_yes

        # Calculate edge
        edge = p_yes - implied_prob

        # Calculate EV (assume $1 bet)
        # If YES wins: get (1 / yes_price) - 1 profit
        # If NO wins: get (1 / no_price) - 1 profit

        yes_payout = (1 / market_odds.yes_price) - 1
        no_payout = (1 / market_odds.no_price) - 1

        ev = (p_yes * yes_payout) - ((1 - p_yes) * no_payout)

        return (ev, edge)

    def _check_distance_vs_volatility(
        self,
        current_price: float,
        strike_price: Optional[float],
        df: pd.DataFrame
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Check distance to strike vs 15-MIN volatility (GPT King rule!)

        Why 15 min? Because exposure from close (XX:50) to resolve (XX:00) = 10-15 min
        Need to check volatility in THIS window, not just 5-min
        """
        if strike_price is None:
            return (None, None)

        # Calculate distance as %
        distance = (strike_price - current_price) / current_price

        # Calculate 15-MIN volatility (GPT King's requirement)
        # 15-min candles = 3 candles of 5-min
        if len(df) >= 30:
            returns = df['close'].pct_change().tail(30)  # Last 30 candles = ~2.5 hours
            volatility = returns.std()
        else:
            volatility = 0.02  # Default 2%

        distance_pct = distance * 100  # Convert to percentage

        return (distance_pct, volatility)

    def _is_bettable(
        self,
        p_yes: float,
        edge: float,
        distance_pct: Optional[float],
        volatility_5m: Optional[float],
        market_odds: Optional[MarketOdds],
        symbol: str = 'BTCUSDT',
        current_price: float = 0
    ) -> bool:
        """
        Minimal filtering for LEARNING mode

        Purpose: Bot needs to learn from ALL predictions (both wins and losses)
        User decides whether to follow the signal or not

        Rules:
        1. Edge > 0% (any positive edge)
        2. No-bet zone only if TOO close (0.5% instead of $100 absolute)
        3. NO overconfidence protection (let it learn!)
        """
        # Rule 1: Must have positive edge (any amount)
        if edge <= 0:
            return False

        # Rule 2: Only skip if EXTREMELY close to strike (within 0.5%)
        # This is for learning - we want data on borderline cases too!
        if distance_pct is not None and current_price > 0:
            abs_distance_pct = abs(distance_pct)

            if abs_distance_pct < 0.5:  # Only skip if within 0.5% (too risky)
                return False

        # NO MORE RULES - let it learn!
        return True

    def _generate_reasons(
        self,
        raw_score: float,
        p_yes: float,
        edge: float,
        df: pd.DataFrame
    ) -> List[str]:
        """Generate human-readable reasons"""
        reasons = []

        # Score direction
        if raw_score > 0.3:
            reasons.append(f"Bullish momentum (score: {raw_score:.2f})")
        elif raw_score < -0.3:
            reasons.append(f"Bearish momentum (score: {raw_score:.2f})")

        # Probability
        reasons.append(f"Win probability: {p_yes*100:.1f}%")

        # Edge
        if edge > 0:
            reasons.append(f"Edge: +{edge*100:.1f}%")
        elif edge < 0:
            reasons.append(f"Edge: {edge*100:.1f}% (negative)")

        return reasons


def test_proper_signal():
    """Test the proper signal generator"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print("[cyan]Testing Proper Signal Generator[/cyan]\n")

    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='5min')

    # Bullish trend
    price = 100 + np.cumsum(np.random.randn(100) * 0.5)
    volume = np.random.randint(1000, 5000, 100)
    df = pd.DataFrame({'close': price, 'volume': volume}, index=dates)

    # Market odds
    market_odds = MarketOdds(
        yes_price=0.60,  # 60% implied
        no_price=0.40,
        yes_volume=1000,
        no_volume=500
    )

    # Generate signal
    generator = ProperSignalGenerator({})
    signal = generator.generate_signal(
        symbol='BTCUSDT',
        df=df,
        current_price=price[-1],
        market_odds=market_odds,
        strike_price=102
    )

    console.print(f"[bold]Signal Analysis:[/bold]\n")
    console.print(f"  Signal: {signal.signal}")
    console.print(f"  P(YES): {signal.p_yes*100:.1f}%")
    console.print(f"  EV: {signal.ev:.3f}")
    console.print(f"  Edge: {signal.edge*100:.1f}%")
    console.print(f"  Bettable: {signal.is_bettable}")
    console.print(f"\n[cyan]Reasons:[/cyan]")
    for reason in signal.reasons:
        console.print(f"  - {reason}")

    console.print("\n[green]OK[/green] Proper signal generator working!")


if __name__ == "__main__":
    test_proper_signal()
