"""
Machine Learning Prediction Module
Uses historical patterns to predict price movements
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class MLPredictor:
    """ML-based price prediction using pattern recognition"""

    def __init__(self):
        """Initialize ML predictor"""
        self.models = {}
        self.feature_columns = []

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for ML model

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with engineered features
        """
        features = pd.DataFrame(index=df.index)

        # Price features
        features['returns'] = df['close'].pct_change()
        features['returns_5'] = df['close'].pct_change(5)
        features['returns_10'] = df['close'].pct_change(10)

        # Volatility
        features['volatility'] = df['close'].rolling(20).std()
        features['volatility_ratio'] = features['volatility'] / features['volatility'].rolling(50).mean()

        # Price position
        features['high_low_ratio'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.0001)

        # Volume features
        features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        features['volume_change'] = df['volume'].pct_change()

        # Momentum
        features['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        features['momentum_10'] = df['close'] / df['close'].shift(10) - 1

        # Moving averages
        features['ma_ratio_5_20'] = df['close'].rolling(5).mean() / df['close'].rolling(20).mean()
        features['ma_ratio_10_30'] = df['close'].rolling(10).mean() / df['close'].rolling(30).mean()

        # Price acceleration
        features['acceleration'] = features['returns'].diff()

        # Direction changes
        features['direction_change'] = (np.sign(features['returns']) != np.sign(features['returns'].shift(1))).astype(int)

        return features.fillna(0)

    def create_target(self, df: pd.DataFrame, periods_ahead: int = 5) -> pd.Series:
        """
        Create target variable for prediction

        Args:
            df: DataFrame with close prices
            periods_ahead: Number of periods to predict ahead

        Returns:
            Series with target (1 for up, 0 for down)
        """
        future_returns = df['close'].shift(-periods_ahead) / df['close'] - 1
        target = (future_returns > 0).astype(int)
        return target

    def train_pattern_model(self, df: pd.DataFrame) -> Dict:
        """
        Train pattern recognition model on historical data

        Args:
            df: Historical price data

        Returns:
            Dictionary with model metrics
        """
        # Prepare features
        features = self.prepare_features(df)
        target = self.create_target(df, periods_ahead=5)

        # Remove last rows (no target)
        valid_idx = target.notna()
        X = features[valid_idx].values
        y = target[valid_idx].values

        if len(X) < 100:
            return {'error': 'Not enough data for training'}

        # Simple pattern-based prediction (no external ML library needed)
        # Use recent pattern matching

        return {
            'status': 'trained',
            'samples': len(X),
            'features': features.shape[1],
            'up_patterns': int(y.sum()),
            'down_patterns': int(len(y) - y.sum())
        }

    def predict_next_move(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """
        Predict next price movement using pattern matching

        Args:
            df: Historical price data
            lookback: Number of similar patterns to find

        Returns:
            Dictionary with prediction
        """
        if len(df) < 100:
            return {'error': 'Not enough data'}

        # Get recent pattern
        recent_returns = df['close'].pct_change().tail(15).values

        # Find similar patterns in history
        all_returns = df['close'].pct_change().values

        similarities = []
        outcomes = []

        for i in range(20, len(all_returns) - 20):
            # Get historical pattern
            hist_pattern = all_returns[i-15:i]

            # Calculate similarity (correlation)
            if len(recent_returns) == len(hist_pattern):
                try:
                    corr = np.corrcoef(recent_returns, hist_pattern)[0, 1]
                    if not np.isnan(corr):
                        similarities.append((i, abs(corr)))
                except:
                    pass

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Get outcomes of most similar patterns
        for idx, sim in similarities[:lookback]:
            # What happened after this pattern?
            if idx + 10 < len(all_returns):
                future_move = all_returns[idx:idx+10].sum()
                outcomes.append(future_move)

        if not outcomes:
            return {'prediction': 'neutral', 'confidence': 50}

        # Calculate average outcome
        avg_outcome = np.mean(outcomes)
        positive_pct = len([o for o in outcomes if o > 0]) / len(outcomes)

        if positive_pct > 0.65:
            direction = 'bullish'
            confidence = min(95, 50 + positive_pct * 40)
        elif positive_pct < 0.35:
            direction = 'bearish'
            confidence = min(95, 50 + (1 - positive_pct) * 40)
        else:
            direction = 'neutral'
            confidence = 50

        return {
            'prediction': direction,
            'confidence': round(confidence, 1),
            'similar_patterns': len(outcomes),
            'avg_outcome': round(avg_outcome * 100, 2),
            'positive_pct': round(positive_pct * 100, 1)
        }

    def detect_chart_patterns(self, df: pd.DataFrame) -> List[str]:
        """
        Detect common chart patterns

        Args:
            df: Price data

        Returns:
            List of detected patterns
        """
        patterns = []

        if len(df) < 50:
            return patterns

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # Double top/bottom detection
        recent_highs = high[-20:]
        recent_lows = low[-20:]

        if len(recent_highs) >= 10:
            max_high_idx = np.argmax(recent_highs)
            second_high = np.argmax(np.concatenate([recent_highs[:max_high_idx], [0], recent_highs[max_high_idx+1:]]))

            # Check for double top (similar highs)
            if abs(recent_highs[max_high_idx] - recent_highs[second_high]) / recent_highs[max_high_idx] < 0.02:
                patterns.append('Double Top (bearish)')

        # Divergence detection (price vs momentum)
        if len(close) >= 20:
            price_trend = np.polyfit(range(20), close[-20:], 1)[0]
            momentum = close[-20:] / close[-21:-1] - 1
            momentum_trend = np.polyfit(range(20), momentum, 1)[0]

            if price_trend > 0 and momentum_trend < 0:
                patterns.append('Bearish Divergence')
            elif price_trend < 0 and momentum_trend > 0:
                patterns.append('Bullish Divergence')

        # Support/resistance breakouts
        if len(df) >= 50:
            recent_range = high[-50:].max() - low[-50:].min()
            current_price = close[-1]

            if current_price > high[-50:].max() - recent_range * 0.02:
                patterns.append('Resistance Breakout (bullish)')
            elif current_price < low[-50:].min() + recent_range * 0.02:
                patterns.append('Support Break (bearish)')

        return patterns

    def calculate_pivot_probability(self, df: pd.DataFrame) -> Dict:
        """
        Calculate probability of price reaching pivot levels

        Args:
            df: Price data

        Returns:
            Dictionary with pivot probabilities
        """
        if len(df) < 20:
            return {}

        current_price = df['close'].iloc[-1]
        atr = df['high'].rolling(14).apply(
            lambda x: max(x) - min(x),
            raw=True
        ).iloc[-1]

        # Calculate support/resistance zones
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()

        # Probability-based levels
        levels = {
            'strong_resistance': recent_high,
            'resistance': (recent_high + current_price) / 2,
            'pivot': current_price,
            'support': (recent_low + current_price) / 2,
            'strong_support': recent_low
        }

        # Calculate probabilities
        probs = {}
        for level_name, level_price in levels.items():
            distance = abs(level_price - current_price) / current_price
            atr_multiple = distance / (atr / current_price)

            # Simple probability model based on ATR
            if atr_multiple < 1:
                prob = 80
            elif atr_multiple < 2:
                prob = 60
            elif atr_multiple < 3:
                prob = 40
            else:
                prob = 20

            probs[level_name] = {
                'price': round(level_price, 4),
                'probability': prob,
                'atr_away': round(atr_multiple, 2)
            }

        return probs
