"""
Interval Signal Generator - For 3-option markets (LOW/MID/HIGH)
Analyzes price ranges to predict where price will be at target time
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from core.indicators import TechnicalIndicators


class IntervalType(Enum):
    """Types of interval signals"""
    LOW = "LOW"      # Price will be below range
    MID = "MID"      # Price will be within range
    HIGH = "HIGH"    # Price will be above range


class IntervalSignalGenerator:
    """Generate signals for interval/price range markets"""

    def __init__(self, config: Dict, market_monitor):
        """
        Initialize interval signal generator

        Args:
            config: Configuration dictionary
            market_monitor: MarketMonitor instance for fetching data
        """
        self.config = config
        self.market_monitor = market_monitor

    def predict_price_at_time(
        self,
        symbol: str,
        current_price: float,
        target_minutes_ahead: int = 60
    ) -> Dict:
        """
        Predict where price will be at target time

        Args:
            symbol: Trading pair symbol
            current_price: Current price
            target_minutes_ahead: Minutes until market closes

        Returns:
            Dictionary with prediction data
        """
        # Fetch multi-timeframe data
        timeframes = ['5m', '15m', '1h']
        predictions = []

        for tf in timeframes:
            try:
                df = self.market_monitor.get_klines(symbol, limit=100, timeframe=tf)
                if df is None or len(df) < 30:
                    continue

                # Calculate indicators
                indicators = TechnicalIndicators.calculate_all(
                    df,
                    self.config.get('indicators', {})
                )

                # Predict price movement for this timeframe
                tf_prediction = self._predict_timeframe(
                    df,
                    indicators,
                    current_price,
                    tf,
                    target_minutes_ahead
                )

                predictions.append(tf_prediction)

            except Exception as e:
                continue

        if not predictions:
            return self._no_prediction(symbol)

        # Combine predictions from all timeframes
        final_prediction = self._combine_predictions(predictions, current_price)

        return final_prediction

    def _predict_timeframe(
        self,
        df: pd.DataFrame,
        indicators: Dict,
        current_price: float,
        timeframe: str,
        target_minutes: int
    ) -> Dict:
        """Predict price movement for a single timeframe"""

        # Get price statistics
        closes = df['close']
        current_volatility = closes.pct_change().std() * 100

        # Calculate predicted price change
        predicted_change_pct = 0
        confidence_boost = 0
        reasons = []

        # 1. Trend Analysis (EMA)
        if 'ema_short' in indicators and 'ema_long' in indicators:
            ema_short = indicators['ema_short']
            ema_long = indicators['ema_long']
            current_trend = (current_price - ema_long) / ema_long * 100

            if ema_short > ema_long:
                # Bullish trend
                predicted_change_pct += abs(current_trend) * 0.3
                reasons.append(f"{timeframe}: EMA bullish (short above long)")
                confidence_boost += 5
            else:
                # Bearish trend
                predicted_change_pct -= abs(current_trend) * 0.3
                reasons.append(f"{timeframe}: EMA bearish (short below long)")
                confidence_boost += 5

        # 2. Momentum (RSI)
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            if rsi < 30:
                # Oversold - likely to bounce up
                predicted_change_pct += (30 - rsi) * 0.1
                reasons.append(f"{timeframe}: RSI oversold ({rsi:.1f})")
                confidence_boost += 3
            elif rsi > 70:
                # Overbought - likely to pull back
                predicted_change_pct -= (rsi - 70) * 0.1
                reasons.append(f"{timeframe}: RSI overbought ({rsi:.1f})")
                confidence_boost += 3
            elif rsi > 50:
                # Bullish momentum
                predicted_change_pct += (rsi - 50) * 0.02
            else:
                # Bearish momentum
                predicted_change_pct -= (50 - rsi) * 0.02

        # 3. MACD Trend
        if 'macd_trend' in indicators:
            if indicators['macd_trend'] == 'bullish':
                predicted_change_pct += 0.5
                reasons.append(f"{timeframe}: MACD bullish")
                confidence_boost += 3
            else:
                predicted_change_pct -= 0.5
                reasons.append(f"{timeframe}: MACD bearish")
                confidence_boost += 3

        # 4. Bollinger Bands Position
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            bb_width = indicators['bb_upper'] - indicators['bb_lower']
            bb_position = (current_price - indicators['bb_lower']) / bb_width

            if bb_position < 0.2:
                # Near lower band - likely to bounce
                predicted_change_pct += 0.8
                reasons.append(f"{timeframe}: Price near BB lower")
            elif bb_position > 0.8:
                # Near upper band - likely to pull back
                predicted_change_pct -= 0.8
                reasons.append(f"{timeframe}: Price near BB upper")

        # 5. Volume Confirmation
        if 'volume_ratio' in indicators:
            vol_ratio = indicators['volume_ratio']
            if vol_ratio > 150 and predicted_change_pct > 0:
                # High volume supporting upward move
                confidence_boost += 5
                reasons.append(f"{timeframe}: High volume supports move ({vol_ratio:.0f}%)")
            elif vol_ratio > 150 and predicted_change_pct < 0:
                confidence_boost += 5
                reasons.append(f"{timeframe}: High volume supports drop ({vol_ratio:.0f}%)")

        # 6. Recent Price Action (last few candles)
        recent_change = (closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5] * 100
        predicted_change_pct += recent_change * 0.2

        # Calculate target price
        target_price = current_price * (1 + predicted_change_pct / 100)

        # Adjust for volatility (more volatile = wider range possible)
        volatility_adjustment = current_volatility * 0.5
        confidence_boost = max(0, confidence_boost - (current_volatility * 0.5))

        # Calculate timeframe-specific weight
        timeframe_weights = {'5m': 0.3, '15m': 0.4, '1h': 0.3}
        weight = timeframe_weights.get(timeframe, 0.33)

        return {
            'timeframe': timeframe,
            'target_price': target_price,
            'predicted_change_pct': predicted_change_pct,
            'volatility': current_volatility,
            'volatility_adjustment': volatility_adjustment,
            'confidence_boost': confidence_boost,
            'weight': weight,
            'reasons': reasons
        }

    def _combine_predictions(
        self,
        predictions: List[Dict],
        current_price: float
    ) -> Dict:
        """Combine predictions from all timeframes"""

        # Calculate weighted average
        total_weight = sum(p['weight'] for p in predictions)
        weighted_target_price = sum(p['target_price'] * p['weight'] for p in predictions) / total_weight
        weighted_change_pct = sum(p['predicted_change_pct'] * p['weight'] for p in predictions) / total_weight

        # Calculate average volatility
        avg_volatility = sum(p['volatility'] for p in predictions) / len(predictions)

        # Calculate confidence based on:
        # 1. Agreement between timeframes
        # 2. Trend strength
        # 3. Volume confirmation

        # Agreement: lower variance in predictions = higher confidence
        pred_prices = [p['target_price'] for p in predictions]
        pred_variance = np.var(pred_prices)
        agreement_score = max(0, 1 - (pred_variance / (current_price ** 2) * 1000))

        # Average confidence boost from all timeframes
        avg_confidence_boost = sum(p['confidence_boost'] for p in predictions) / len(predictions)

        # Calculate base confidence
        base_confidence = 50
        confidence = base_confidence + (agreement_score * 20) + avg_confidence_boost

        # Clamp confidence
        confidence = max(30, min(95, confidence))

        # Collect all reasons
        all_reasons = []
        for p in predictions:
            all_reasons.extend(p['reasons'])

        # Calculate price range (for uncertainty)
        price_range_low = min(p['target_price'] for p in predictions)
        price_range_high = max(p['target_price'] for p in predictions)

        return {
            'current_price': current_price,
            'predicted_price': weighted_target_price,
            'predicted_change_pct': weighted_change_pct,
            'price_range_low': price_range_low,
            'price_range_high': price_range_high,
            'volatility': avg_volatility,
            'confidence': round(confidence, 1),
            'timeframe_predictions': predictions,
            'agreement_score': round(agreement_score * 100, 1),
            'reasons': list(set(all_reasons)),  # Remove duplicates
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def classify_interval(
        self,
        prediction: Dict,
        low_threshold: float,
        high_threshold: float
    ) -> Dict:
        """
        Classify prediction into LOW/MID/HIGH interval

        Args:
            prediction: Prediction dictionary from predict_price_at_time
            low_threshold: LOW/MID boundary price
            high_threshold: MID/HIGH boundary price

        Returns:
            Dictionary with interval classification
        """
        predicted_price = prediction['predicted_price']
        current_price = prediction['current_price']
        confidence = prediction['confidence']

        # Determine primary interval
        if predicted_price < low_threshold:
            interval = IntervalType.LOW
            interval_desc = f"< ${low_threshold:,.2f}"

            # Calculate confidence for this interval
            distance_to_threshold = (low_threshold - predicted_price) / current_price * 100
            interval_confidence = min(95, confidence + distance_to_threshold * 2)

        elif predicted_price > high_threshold:
            interval = IntervalType.HIGH
            interval_desc = f"> ${high_threshold:,.2f}"

            # Calculate confidence for this interval
            distance_to_threshold = (predicted_price - high_threshold) / current_price * 100
            interval_confidence = min(95, confidence + distance_to_threshold * 2)

        else:
            interval = IntervalType.MID
            interval_desc = f"${low_threshold:,.2f} - ${high_threshold:,.2f}"

            # For MID, confidence depends on how centered in the range
            mid_point = (low_threshold + high_threshold) / 2
            distance_from_mid = abs(predicted_price - mid_point) / (high_threshold - low_threshold)
            interval_confidence = max(40, confidence * (1 - distance_from_mid))

        # Secondary recommendation (in case primary is wrong)
        if interval != IntervalType.MID:
            # If LOW or HIGH, suggest MID as backup
            secondary = IntervalType.MID
        elif predicted_price < (low_threshold + high_threshold) / 2:
            secondary = IntervalType.LOW
        else:
            secondary = IntervalType.HIGH

        return {
            'interval': interval.value,
            'interval_type': interval,
            'interval_description': interval_desc,
            'confidence': round(interval_confidence, 1),
            'secondary': secondary.value,
            'predicted_price': predicted_price,
            'low_threshold': low_threshold,
            'high_threshold': high_threshold,
            'reasoning': self._generate_interval_reasoning(
                prediction, interval, low_threshold, high_threshold
            )
        }

    def _generate_interval_reasoning(
        self,
        prediction: Dict,
        interval: IntervalType,
        low_threshold: float,
        high_threshold: float
    ) -> List[str]:
        """Generate reasoning for interval classification"""

        reasons = prediction.get('reasons', [])

        # Add interval-specific reasoning
        predicted_price = prediction['predicted_price']
        current_price = prediction['current_price']

        if interval == IntervalType.LOW:
            reasons.append(f"Predicted price ${predicted_price:,.2f} is below LOW threshold")
            if predicted_price < current_price:
                reasons.append(f"Bearish move expected ({prediction['predicted_change_pct']:.2f}%)")
        elif interval == IntervalType.HIGH:
            reasons.append(f"Predicted price ${predicted_price:,.2f} exceeds HIGH threshold")
            if predicted_price > current_price:
                reasons.append(f"Bullish move expected ({prediction['predicted_change_pct']:.2f}%)")
        else:
            reasons.append(f"Predicted price ${predicted_price:,.2f} falls within range")
            reasons.append(f"Price likely to consolidate between ${low_threshold:,.2f} - ${high_threshold:,.2f}")

        # Add volatility note
        if prediction['volatility'] > 2:
            reasons.append(f"High volatility detected ({prediction['volatility']:.2f}%)")

        return list(set(reasons))

    def _no_prediction(self, symbol: str) -> Dict:
        """Return no-prediction result"""
        return {
            'current_price': 0,
            'predicted_price': 0,
            'predicted_change_pct': 0,
            'price_range_low': 0,
            'price_range_high': 0,
            'volatility': 0,
            'confidence': 0,
            'timeframe_predictions': [],
            'agreement_score': 0,
            'reasons': ['No data available for prediction'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
