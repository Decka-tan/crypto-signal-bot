"""
Pro Signal Generator - Multi-timeframe analysis with advanced indicators
Designed for higher accuracy prediction market signals
"""

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import pandas as pd

from core.indicators import TechnicalIndicators
from core.advanced_indicators import AdvancedIndicators


class SignalType(Enum):
    """Types of trading signals"""
    STRONG_BUY = "STRONG YES"
    BUY = "YES"
    HOLD = "HOLD"
    SELL = "NO"
    STRONG_SELL = "STRONG NO"


class ProSignalGenerator:
    """Professional-grade signal generator with multi-timeframe analysis"""

    def __init__(self, config: Dict, market_monitor):
        """
        Initialize pro signal generator

        Args:
            config: Configuration dictionary
            market_monitor: MarketMonitor instance for fetching multi-timeframe data
        """
        self.config = config
        self.market_monitor = market_monitor
        self.thresholds = config.get('thresholds', {})

        # Timeframes to analyze (from fastest to slowest)
        self.timeframes = ['5m', '15m', '1h']  # 5m for confirmation, 15m main, 1h for trend

    def analyze_multi_timeframe(self, symbol: str) -> Dict:
        """
        Analyze symbol across multiple timeframes for higher accuracy

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with multi-timeframe signal analysis
        """
        timeframe_signals = {}
        weighted_score = 0
        total_weight = 0

        # Weights: 15m is most important for prediction markets
        weights = {
            '5m': 0.25,
            '15m': 0.50,
            '1h': 0.25
        }

        for tf in self.timeframes:
            try:
                # Fetch data for this timeframe
                df = self.market_monitor.get_klines(symbol, limit=100, timeframe=tf)
                if df is None or len(df) < 30:
                    continue

                # Calculate all indicators
                basic_indicators = TechnicalIndicators.calculate_all(
                    df,
                    self.config.get('indicators', {})
                )

                # Add advanced indicators
                adv_indicators = self._calculate_advanced(df)

                # Combine indicators
                all_indicators = {**basic_indicators, **adv_indicators}
                all_indicators['current'] = df['close'].iloc[-1]

                # Generate signal for this timeframe
                tf_signal = self._analyze_timeframe(all_indicators, tf)

                timeframe_signals[tf] = tf_signal

                # Add to weighted score
                signal_weight = self._signal_to_weight(tf_signal['signal_type'])
                weighted_score += signal_weight * weights[tf]
                total_weight += weights[tf]

            except Exception as e:
                continue

        # Calculate final signal
        if total_weight == 0:
            return self._no_signal(symbol, "No data available")

        avg_score = weighted_score / total_weight

        # Determine final signal type
        if avg_score >= 0.75:
            final_signal = SignalType.STRONG_BUY
        elif avg_score >= 0.55:
            final_signal = SignalType.BUY
        elif avg_score >= 0.45:
            final_signal = SignalType.HOLD
        elif avg_score >= 0.25:
            final_signal = SignalType.SELL
        else:
            final_signal = SignalType.STRONG_SELL

        # Calculate confidence based on:
        # 1. Signal agreement across timeframes
        # 2. Trend strength (ADX)
        # 3. Volume confirmation

        agreement = self._calculate_timeframe_agreement(timeframe_signals)
        trend_strength = self._get_trend_strength(timeframe_signals)
        volume_confirms = self._volume_confirms(timeframe_signals)

        confidence = self._calculate_pro_confidence(
            final_signal,
            agreement,
            trend_strength,
            volume_confirms
        )

        # Generate comprehensive analysis
        return {
            'symbol': symbol,
            'signal': final_signal.value,
            'signal_type': final_signal,
            'confidence': round(confidence, 1),
            'timeframe_signals': timeframe_signals,
            'agreement': round(agreement * 100, 1),
            'trend_strength': trend_strength,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reasons': self._generate_pro_reasons(timeframe_signals, final_signal)
        }

    def _calculate_advanced(self, df: pd.DataFrame) -> Dict:
        """Calculate advanced indicators"""
        indicators = {}

        try:
            # ADX for trend strength
            adx_data = AdvancedIndicators.adx(df)
            indicators['adx'] = adx_data['adx'].iloc[-1]
            indicators['di_plus'] = adx_data['di_plus'].iloc[-1]
            indicators['di_minus'] = adx_data['di_minus'].iloc[-1]

            # Stochastic
            stoch = AdvancedIndicators.stochastic(df)
            indicators['stoch_k'] = stoch['k'].iloc[-1]
            indicators['stoch_d'] = stoch['d'].iloc[-1]

            # Williams %R
            indicators['williams_r'] = AdvancedIndicators.williams_r(df).iloc[-1]

            # CCI
            indicators['cci'] = AdvancedIndicators.cci(df).iloc[-1]

            # Money Flow Index
            indicators['mfi'] = AdvancedIndicators.money_flow_index(df).iloc[-1]

            # VWAP
            indicators['vwap'] = AdvancedIndicators.vwap(df).iloc[-1]

            # Pivot points
            pivots = AdvancedIndicators.pivot_points(df)
            indicators.update(pivots)

        except Exception as e:
            pass

        return indicators

    def _analyze_timeframe(self, indicators: Dict, timeframe: str) -> Dict:
        """Analyze indicators for a single timeframe"""
        signals = []
        scores = []

        # RSI
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:
                signals.append(SignalType.BUY)
                scores.append(0.75)
            elif rsi > 70:
                signals.append(SignalType.SELL)
                scores.append(0.25)
            else:
                scores.append(0.5)

        # MACD
        if 'macd_trend' in indicators:
            if indicators['macd_trend'] == 'bullish':
                signals.append(SignalType.BUY)
                scores.append(0.70)
            else:
                signals.append(SignalType.SELL)
                scores.append(0.30)

        # EMA Cross
        if 'ema_cross' in indicators:
            if indicators['ema_cross'] == 'bullish':
                signals.append(SignalType.BUY)
                scores.append(0.65)
            else:
                signals.append(SignalType.SELL)
                scores.append(0.35)

        # Stochastic
        if 'stoch_k' in indicators and 'stoch_d' in indicators:
            k = indicators['stoch_k']
            d = indicators['stoch_d']

            if k < 20 and d < 20:
                signals.append(SignalType.BUY)
                scores.append(0.70)
            elif k > 80 and d > 80:
                signals.append(SignalType.SELL)
                scores.append(0.30)
            elif k > d:
                signals.append(SignalType.BUY)
                scores.append(0.55)
            else:
                signals.append(SignalType.SELL)
                scores.append(0.45)

        # ADX Trend Strength (CRITICAL)
        if 'adx' in indicators:
            adx = indicators['adx']
            if adx < 20:
                # No trend - reduce confidence
                for i in range(len(scores)):
                    scores[i] = scores[i] * 0.5 + 0.25  # Pull toward neutral
            elif adx > 25:
                # Strong trend - increase confidence
                trend = indicators['di_plus'] > indicators['di_minus']
                if trend:
                    signals.append(SignalType.BUY)
                    scores.append(0.70)
                else:
                    signals.append(SignalType.SELL)
                    scores.append(0.30)

        # Money Flow Index
        if 'mfi' in indicators:
            mfi = indicators['mfi']
            if mfi < 20:
                signals.append(SignalType.BUY)
                scores.append(0.65)
            elif mfi > 80:
                signals.append(SignalType.SELL)
                scores.append(0.35)

        # Price vs VWAP
        if 'vwap' in indicators and 'current' in indicators:
            if indicators['current'] > indicators['vwap']:
                signals.append(SignalType.BUY)
                scores.append(0.55)
            else:
                signals.append(SignalType.SELL)
                scores.append(0.45)

        # Calculate average score
        if scores:
            avg_score = sum(scores) / len(scores)

            if avg_score >= 0.70:
                signal_type = SignalType.STRONG_BUY
            elif avg_score >= 0.55:
                signal_type = SignalType.BUY
            elif avg_score >= 0.45:
                signal_type = SignalType.HOLD
            elif avg_score >= 0.30:
                signal_type = SignalType.SELL
            else:
                signal_type = SignalType.STRONG_SELL
        else:
            signal_type = SignalType.HOLD
            avg_score = 0.5

        return {
            'timeframe': timeframe,
            'signal_type': signal_type,
            'score': avg_score,
            'indicators': indicators
        }

    def _signal_to_weight(self, signal_type: SignalType) -> float:
        """Convert signal type to numeric weight"""
        weights = {
            SignalType.STRONG_BUY: 1.0,
            SignalType.BUY: 0.65,
            SignalType.HOLD: 0.5,
            SignalType.SELL: 0.35,
            SignalType.STRONG_SELL: 0.0
        }
        return weights.get(signal_type, 0.5)

    def _calculate_timeframe_agreement(self, timeframe_signals: Dict) -> float:
        """Calculate how much signals agree across timeframes"""
        if len(timeframe_signals) < 2:
            return 0.5

        scores = [tf['score'] for tf in timeframe_signals.values()]
        avg = sum(scores) / len(scores)

        # Lower variance = higher agreement
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)

        # Convert variance to agreement (0-1)
        agreement = max(0, 1 - (variance * 4))

        return agreement

    def _get_trend_strength(self, timeframe_signals: Dict) -> str:
        """Get overall trend strength from all timeframes"""
        adx_values = []

        for tf_data in timeframe_signals.values():
            if 'adx' in tf_data['indicators']:
                adx_values.append(tf_data['indicators']['adx'])

        if not adx_values:
            return "Unknown"

        avg_adx = sum(adx_values) / len(adx_values)

        if avg_adx < 20:
            return "Weak (No Trend)"
        elif avg_adx < 25:
            return "Moderate"
        elif avg_adx < 40:
            return "Strong"
        else:
            return "Very Strong"

    def _volume_confirms(self, timeframe_signals: Dict) -> bool:
        """Check if volume confirms the signal"""
        for tf_data in timeframe_signals.values():
            vol_ratio = tf_data['indicators'].get('volume_ratio', 100)
            if vol_ratio > 150:  # Volume spike
                return True
        return False

    def _calculate_pro_confidence(
        self,
        signal: SignalType,
        agreement: float,
        trend_strength: str,
        volume_confirms: bool
    ) -> float:
        """Calculate confidence score for pro signal"""
        base_confidence = 60

        # Agreement bonus (up to +20%)
        agreement_bonus = agreement * 20

        # Trend strength bonus
        strength_bonus = {
            "Very Strong": 15,
            "Strong": 10,
            "Moderate": 5,
            "Weak (No Trend)": -10,
            "Unknown": 0
        }.get(trend_strength, 0)

        # Volume confirmation bonus
        volume_bonus = 10 if volume_confirms else 0

        # Calculate final confidence
        confidence = base_confidence + agreement_bonus + strength_bonus + volume_bonus

        # Clamp to 0-100
        confidence = max(0, min(100, confidence))

        return confidence

    def _generate_pro_reasons(
        self,
        timeframe_signals: Dict,
        final_signal: SignalType
    ) -> List[str]:
        """Generate professional-grade reasons for the signal"""
        reasons = []

        # Collect reasons from all timeframes
        for tf, data in timeframe_signals.items():
            indicators = data['indicators']

            # RSI
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if rsi < 35:
                    reasons.append(f"{tf}: RSI oversold ({rsi:.1f})")
                elif rsi > 65:
                    reasons.append(f"{tf}: RSI overbought ({rsi:.1f})")

            # MACD
            if 'macd_trend' in indicators:
                reasons.append(f"{tf}: MACD {indicators['macd_trend']}")

            # ADX trend
            if 'adx' in indicators:
                adx = indicators['adx']
                if adx > 25:
                    direction = "bullish" if indicators.get('di_plus', 0) > indicators.get('di_minus', 0) else "bearish"
                    reasons.append(f"{tf}: Strong {direction} trend (ADX: {adx:.1f})")
                elif adx < 20:
                    reasons.append(f"{tf}: Weak/no trend (ADX: {adx:.1f})")

            # Stochastic
            if 'stoch_k' in indicators:
                k = indicators['stoch_k']
                if k < 25:
                    reasons.append(f"{tf}: Stochastic oversold")
                elif k > 75:
                    reasons.append(f"{tf}: Stochastic overbought")

            # Volume
            if 'volume_ratio' in indicators:
                vol = indicators['volume_ratio']
                if vol > 150:
                    reasons.append(f"{tf}: Volume spike ({vol:.0f}% of avg)")

            # Multi-timeframe agreement
            if len(timeframe_signals) >= 2:
                agreement = self._calculate_timeframe_agreement(timeframe_signals) * 100
                if agreement > 70:
                    reasons.append(f"Multi-timeframe agreement ({agreement:.0f}%)")

        return list(set(reasons))  # Remove duplicates

    def _no_signal(self, symbol: str, reason: str) -> Dict:
        """Return no-signal result"""
        return {
            'symbol': symbol,
            'signal': SignalType.HOLD.value,
            'signal_type': SignalType.HOLD,
            'confidence': 0,
            'timeframe_signals': {},
            'agreement': 0,
            'trend_strength': 'Unknown',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'reasons': [reason]
        }
