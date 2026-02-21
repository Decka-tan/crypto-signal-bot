"""
Integration layer for Proper Signal Generator
Add this to main_ultimate.py to replace analyze_symbol()
"""

from typing import Dict, Optional
from datetime import datetime
import re

from core.proper_signals import ProperSignalGenerator, MarketOdds


def analyze_symbol_proper(self, symbol: str) -> Dict:
    """
    PROPER signal analysis with EV, Edge, and Real Probability

    Replaces UltimateSignalGenerator with ProperSignalGenerator
    """
    # Get price data
    df = self.market_monitor.get_klines(symbol, limit=100)
    if df is None or len(df) < 30:
        return {
            'error': 'Not enough data',
            'symbol': symbol,
            'reason': 'Need at least 30 candles'
        }

    current_price = float(df['close'].iloc[-1])

    # Get market odds from Unhedged
    market_odds = None
    try:
        odds = self.get_market_odds(symbol, 'binary')
        if odds:
            market_odds = MarketOdds(
                yes_price=odds.yes_pct / 100,
                no_price=odds.no_pct / 100,
                yes_volume=odds.yes_volume,
                no_volume=odds.no_volume
            )
    except:
        pass

    # Get active market for strike price
    active_market = self.find_matching_market(symbol, market_type='binary')
    strike_price = None
    market_question = ""
    market_id = None
    market_link = None

    if active_market:
        market_question = active_market.question
        market_id = active_market.market_id
        market_link = active_market.url

        # Extract strike price from question
        # Pattern: "above $67,000" or "below $65,000"
        above_match = re.search(r'above\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)
        below_match = re.search(r'below\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)

        if above_match:
            strike_price = float(above_match.group(1).replace(',', ''))
        elif below_match:
            strike_price = float(below_match.group(1).replace(',', ''))

    # Generate PROPER signal
    if not hasattr(self, 'proper_signal_generator'):
        self.proper_signal_generator = ProperSignalGenerator(self.config)

    signal_analysis = self.proper_signal_generator.generate_signal(
        symbol=symbol,
        df=df,
        current_price=current_price,
        market_odds=market_odds,
        strike_price=strike_price
    )

    # Convert to dict format (compatible with existing code)
    result = {
        'symbol': symbol,
        'signal': signal_analysis.signal,
        'signal_type': signal_analysis.signal,  # For compatibility
        'confidence': signal_analysis.confidence,
        'p_yes': signal_analysis.p_yes,
        'ev': signal_analysis.ev,
        'edge': signal_analysis.edge,
        'is_bettable': signal_analysis.is_bettable,
        'current_price': signal_analysis.current_price,
        'predicted_price': signal_analysis.predicted_price,
        'distance_to_strike': signal_analysis.distance_to_strike,
        'volatility_5m': signal_analysis.volatility_5m,
        'reasons': signal_analysis.reasons,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'market_id': market_id,
        'market_link': market_link,
        'market_question': market_question
    }

    # Add market odds info
    if market_odds:
        result['market_odds'] = {
            'yes_pct': market_odds.yes_price * 100,
            'no_pct': market_odds.no_price * 100,
            'yes_volume': market_odds.yes_volume,
            'no_volume': market_odds.no_volume
        }
        result['implied_prob'] = market_odds.implied_prob_yes * 100
        result['crowd_sentiment'] = 'STRONG_BULLISH' if market_odds.yes_price > 0.7 else \
                                       'BULLISH' if market_odds.yes_price > 0.6 else \
                                       'NEUTRAL' if market_odds.yes_price > 0.4 else \
                                       'BEARISH' if market_odds.yes_price > 0.3 else 'STRONG_BEARISH'

    # Add edge status to reasons
    if signal_analysis.edge > 0:
        result['reasons'].insert(0, f"✅ POSITIVE EDGE: +{signal_analysis.edge*100:.1f}%")
    else:
        result['reasons'].insert(0, f"❌ NEGATIVE EDGE: {signal_analysis.edge*100:.1f}%")

    # Add distance to strike status
    if signal_analysis.distance_to_strike is not None:
        dist = signal_analysis.distance_to_strike
        if abs(dist) < 1:
            result['reasons'].append(f"⚠️  TOO CLOSE TO STRIKE: {dist:.2f}%")
        elif abs(dist) > 5:
            result['reasons'].append(f"✅ GOOD DISTANCE: {dist:.2f}% from strike")

    # Add volatility status
    if signal_analysis.volatility_5m is not None:
        vol = signal_analysis.volatility_5m * 100
        result['reasons'].append(f"📊 5m Volatility: {vol:.2f}%")

    return result


def check_and_alert_proper(self, signal_analysis: Dict):
    """
    PROPER alert checking with EV and is_bettable

    Only alert if:
    1. is_bettable = True (EV > 0 AND passes safety checks)
    2. Market is still active
    3. Within optimal time window
    """
    if not signal_analysis or signal_analysis.get('error'):
        return

    symbol = signal_analysis['symbol']

    # CHECK: Is this bettable?
    if not signal_analysis.get('is_bettable', False):
        edge = signal_analysis.get('edge', 0) * 100
        ev = signal_analysis.get('ev', 0)

        if edge < 0:
            self.console.print(f"   [dim][SKIP] {symbol}: Negative edge ({edge:.1f}%)[/dim]")
        else:
            self.console.print(f"   [dim][SKIP] {symbol}: Failed safety checks (dist/vol)[/dim]")
        return

    # CHECK: Market still active?
    market_id = signal_analysis.get('market_id')
    if market_id:
        active_market = self.find_matching_market(symbol)
        if not active_market or not active_market.is_still_active():
            self.console.print(f"   [dim][SKIP] {symbol}: Market resolved[/dim]")
            return

        # CHECK: Optimal time window
        minutes_left = active_market.get_time_until_resolved_minutes()
        if minutes_left is not None:
            min_time = self.config.get('min_time_binary', 5)
            max_time = self.config.get('max_time_binary', 40)

            if minutes_left < min_time:
                self.console.print(f"   [dim][SKIP] {symbol}: {minutes_left} min left (market closing)[/dim]")
                return
            elif minutes_left > max_time:
                self.console.print(f"   [dim][SKIP] {symbol}: {minutes_left} min left (too early)[/dim]")
                return

    # ALL CHECKS PASSED - SEND ALERT!
    edge = signal_analysis.get('edge', 0) * 100
    ev = signal_analysis.get('ev', 0)
    p_yes = signal_analysis.get('p_yes', 0) * 100

    self.console.print(
        f"   [green][ALERT] {symbol}: {signal_analysis['signal']} "
        f"(P(YES): {p_yes:.1f}%, EV: {ev:.3f}, Edge: +{edge:.1f}%)[/green]"
    )

    # Log to result tracker
    try:
        from core.result_tracker import BetResult

        bet = BetResult(
            timestamp=signal_analysis['timestamp'],
            symbol=symbol,
            market_type='binary',
            market_id=signal_analysis.get('market_id', 'unknown'),
            market_question=signal_analysis.get('market_question', '')[:200],
            signal=signal_analysis['signal'],
            confidence=signal_analysis['confidence'],
            predicted_price=signal_analysis.get('predicted_price'),
            target_price=None,  # Will extract from strike price
            current_price=signal_analysis['current_price'],
            time_until_resolved=minutes_left if minutes_left else 0,
            outcome=signal_analysis['signal'],
            actual_result=None,
            is_win=None,
            amount_bet=0,
            amount_won=None,
            edge=signal_analysis['edge']
        )

        self.result_tracker.log_bet(bet, raw_analysis=signal_analysis)
    except Exception as e:
        pass  # Don't break alerts for logging errors

    # Send alert
    self.alert_manager.send_alert(signal_analysis)
    self.last_alerts[symbol] = time.time()


# HOW TO USE:
# 1. Add to main_ultimate.py:
#    from core.signal_integration import analyze_symbol_proper, check_and_alert_proper
#
# 2. In run_continuous(), replace:
#    signal = self.analyze_symbol(symbol)
#    self.check_and_alert(signal)
#
#    With:
#    signal = analyze_symbol_proper(self, symbol)
#    check_and_alert_proper(self, signal)
