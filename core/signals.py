"""
Signal Generation Module
Analyzes indicators and generates trading signals for prediction markets
"""

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class SignalType(Enum):
    """Types of trading signals"""
    STRONG_BUY = "STRONG YES"  # High confidence "Yes" bet
    BUY = "YES"                 # Moderate confidence "Yes" bet
    HOLD = "HOLD"               # No clear signal
    SELL = "NO"                 # Moderate confidence "No" bet
    STRONG_SELL = "STRONG NO"   # High confidence "No" bet


class SignalGenerator:
    """Generate trading signals based on technical analysis"""

    def __init__(self, config: Dict):
        """
        Initialize signal generator

        Args:
            config: Configuration dictionary with thresholds
        """
        self.config = config
        self.thresholds = config.get('thresholds', {})

    def analyze_indicators(self, indicators: Dict, symbol: str) -> Dict:
        """
        Analyze all indicators and generate a comprehensive signal

        Args:
            indicators: Dictionary with all calculated indicators
            symbol: Trading pair symbol

        Returns:
            Dictionary with signal analysis including recommendation
        """
        signals = []
        confidence_scores = []
        reasons = []

        # RSI Analysis
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < self.thresholds.get('rsi_oversold', 30):
                signals.append(SignalType.BUY)
                confidence_scores.append(70)
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > self.thresholds.get('rsi_overbought', 70):
                signals.append(SignalType.SELL)
                confidence_scores.append(70)
                reasons.append(f"RSI overbought ({rsi:.1f})")
            else:
                signals.append(SignalType.HOLD)
                confidence_scores.append(50)
                reasons.append(f"RSI neutral ({rsi:.1f})")

        # MACD Analysis
        if 'macd_trend' in indicators:
            macd_trend = indicators['macd_trend']
            macd_hist = indicators.get('macd_histogram', 0)

            if macd_trend == 'bullish' and macd_hist > 0:
                signals.append(SignalType.BUY)
                confidence_scores.append(60)
                reasons.append(f"MACD bullish (hist: {macd_hist:.4f})")
            elif macd_trend == 'bearish' and macd_hist < 0:
                signals.append(SignalType.SELL)
                confidence_scores.append(60)
                reasons.append(f"MACD bearish (hist: {macd_hist:.4f})")

        # EMA Crossover Analysis
        if 'ema_cross' in indicators:
            ema_cross = indicators['ema_cross']
            ema_short = indicators.get('ema_short', 0)
            ema_long = indicators.get('ema_long', 0)

            if ema_cross == 'bullish':
                signals.append(SignalType.BUY)
                confidence_scores.append(65)
                reasons.append(f"EMA bullish cross (short: {ema_short:.2f} > long: {ema_long:.2f})")
            else:
                signals.append(SignalType.SELL)
                confidence_scores.append(65)
                reasons.append(f"EMA bearish cross (short: {ema_short:.2f} < long: {ema_long:.2f})")

        # Bollinger Bands Analysis
        if 'bb_percent' in indicators:
            bb_percent = indicators['bb_percent']
            current_price = indicators.get('current', 0)
            bb_upper = indicators.get('bb_upper', 0)
            bb_lower = indicators.get('bb_lower', 0)

            if bb_percent < 10:  # Near lower band
                signals.append(SignalType.BUY)
                confidence_scores.append(60)
                reasons.append(f"Price near lower BB ({bb_percent:.1f}%)")
            elif bb_percent > 90:  # Near upper band
                signals.append(SignalType.SELL)
                confidence_scores.append(60)
                reasons.append(f"Price near upper BB ({bb_percent:.1f}%)")

        # Volume Analysis
        if 'volume_ratio' in indicators:
            vol_ratio = indicators['volume_ratio']
            threshold = self.thresholds.get('volume_spike', 150)

            if vol_ratio > threshold:
                # Volume spike - confirms the signal
                for i in range(len(confidence_scores)):
                    confidence_scores[i] = min(confidence_scores[i] + 15, 95)
                reasons.append(f"Volume spike ({vol_ratio:.0f}% of avg)")

        # Support/Resistance Analysis
        if 'distance_to_support' in indicators and 'distance_to_resistance' in indicators:
            dist_support = indicators['distance_to_support']
            dist_resistance = indicators['distance_to_resistance']

            if dist_support < 1:  # Very close to support
                signals.append(SignalType.BUY)
                confidence_scores.append(75)
                reasons.append(f"Near support ({dist_support:.2f}% away)")

            if dist_resistance < 1:  # Very close to resistance
                signals.append(SignalType.SELL)
                confidence_scores.append(75)
                reasons.append(f"Near resistance ({dist_resistance:.2f}% away)")

        # Calculate final signal
        if not signals:
            final_signal = SignalType.HOLD
            final_confidence = 50
        else:
            # Weight signals by confidence
            signal_weights = {
                SignalType.STRONG_BUY: 100,
                SignalType.BUY: 75,
                SignalType.HOLD: 50,
                SignalType.SELL: 25,
                SignalType.STRONG_SELL: 0
            }

            # Calculate weighted average
            total_weight = sum(signal_weights[s] * c for s, c in zip(signals, confidence_scores))
            total_confidence = sum(confidence_scores)

            if total_confidence > 0:
                avg_weight = total_weight / total_confidence
            else:
                avg_weight = 50

            # Determine final signal
            if avg_weight >= 80:
                final_signal = SignalType.STRONG_BUY
            elif avg_weight >= 60:
                final_signal = SignalType.BUY
            elif avg_weight >= 40:
                final_signal = SignalType.HOLD
            elif avg_weight >= 20:
                final_signal = SignalType.SELL
            else:
                final_signal = SignalType.STRONG_SELL

            # Average confidence
            final_confidence = sum(confidence_scores) / len(confidence_scores)

        # Prediction market specific advice
        prediction_advice = self._generate_prediction_advice(
            indicators, final_signal, final_confidence
        )

        return {
            'symbol': symbol,
            'signal': final_signal.value,
            'signal_type': final_signal,
            'confidence': round(final_confidence, 1),
            'reasons': reasons,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'indicators': indicators,
            'prediction_advice': prediction_advice
        }

    def _generate_prediction_advice(
        self, indicators: Dict, signal: SignalType, confidence: float
    ) -> Dict:
        """
        Generate specific advice for prediction market betting

        Args:
            indicators: All calculated indicators
            signal: Generated signal type
            confidence: Signal confidence score

        Returns:
            Dictionary with prediction market advice
        """
        advice = {
            'recommendation': signal.value,
            'confidence': confidence,
            'action': '',
            'target_price': None,
            'timeframe': '15m',
            'risk_level': '',
            'position_size': ''
        }

        # Determine action based on signal
        if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
            current = indicators.get('current', indicators.get('close', 0))
            resistance = indicators.get('resistance', current * 1.01)

            advice['action'] = 'Bet YES'
            advice['target_price'] = round(resistance, 4)
            advice['target_direction'] = 'ABOVE'
            advice['risk_level'] = 'Medium' if confidence < 70 else 'Low'
            advice['position_size'] = 'Standard' if confidence >= 70 else 'Small'

        elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
            current = indicators.get('current', indicators.get('close', 0))
            support = indicators.get('support', current * 0.99)

            advice['action'] = 'Bet NO'
            advice['target_price'] = round(support, 4)
            advice['target_direction'] = 'BELOW'
            advice['risk_level'] = 'Medium' if confidence < 70 else 'Low'
            advice['position_size'] = 'Standard' if confidence >= 70 else 'Small'

        else:
            advice['action'] = 'WAIT'
            advice['risk_level'] = 'None'
            advice['position_size'] = 'None'

        return advice

    def should_alert(self, signal_analysis: Dict) -> bool:
        """
        Determine if a signal is strong enough to trigger an alert

        Args:
            signal_analysis: Signal analysis dictionary

        Returns:
            True if alert should be triggered
        """
        confidence = signal_analysis['confidence']
        min_confidence = self.thresholds.get('min_confidence', 60)

        # Alert if confidence is above threshold and signal is not HOLD
        signal_type = signal_analysis['signal_type']

        return signal_type != SignalType.HOLD and confidence >= min_confidence

    def format_signal_message(self, signal_analysis: Dict) -> str:
        """
        Format signal analysis into a readable message

        Args:
            signal_analysis: Signal analysis dictionary

        Returns:
            Formatted message string
        """
        symbol = signal_analysis['symbol']
        signal = signal_analysis['signal']
        confidence = signal_analysis['confidence']
        reasons = signal_analysis['reasons']
        indicators = signal_analysis['indicators']
        advice = signal_analysis['prediction_advice']

        lines = [
            f"\n{'='*60}",
            f"🚨 SIGNAL ALERT: {symbol}",
            f"{'='*60}",
            f"\n📊 RECOMMENDATION: {signal} (Confidence: {confidence}%)",
            f"\n💡 ACTION: {advice['action']}",
        ]

        if advice['target_price']:
            lines.append(f"   Target: {advice['target_direction']} ${advice['target_price']}")
            lines.append(f"   Timeframe: {advice['timeframe']}")
            lines.append(f"   Risk Level: {advice['risk_level']}")
            lines.append(f"   Position Size: {advice['position_size']}")

        lines.append(f"\n📈 TECHNICAL REASONS:")
        for i, reason in enumerate(reasons, 1):
            lines.append(f"   {i}. {reason}")

        lines.append(f"\n📋 KEY INDICATORS:")

        if 'rsi' in indicators:
            lines.append(f"   • RSI: {indicators['rsi']:.1f}")

        if 'macd_trend' in indicators:
            lines.append(f"   • MACD: {indicators['macd_trend'].upper()}")

        if 'ema_cross' in indicators:
            lines.append(f"   • EMA Cross: {indicators['ema_cross'].upper()}")

        if 'bb_percent' in indicators:
            lines.append(f"   • BB Position: {indicators['bb_percent']:.1f}%")

        if 'volume_ratio' in indicators:
            lines.append(f"   • Volume: {indicators['volume_ratio']:.0f}% of avg")

        if 'distance_to_support' in indicators and 'distance_to_resistance' in indicators:
            lines.append(f"   • Distance from Support: {indicators['distance_to_support']:.2f}%")
            lines.append(f"   • Distance to Resistance: {indicators['distance_to_resistance']:.2f}%")

        lines.append(f"\n⏰ Time: {signal_analysis['timestamp']}")
        lines.append(f"{'='*60}\n")

        return "\n".join(lines)
