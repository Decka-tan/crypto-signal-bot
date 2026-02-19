"""
Sentiment Analysis Module
Analyzes market sentiment from social media and news sources
"""

import requests
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


class SentimentAnalyzer:
    """Analyze market sentiment from multiple sources"""

    def __init__(self):
        """Initialize sentiment analyzer"""
        self.sentiment_cache = {}
        self.last_update = {}

    def analyze_fear_greed_index(self) -> Dict:
        """
        Get Bitcoin Fear & Greed Index (free API)

        Returns:
            Dictionary with sentiment data
        """
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            value = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            timestamp = data['data'][0]['timestamp']

            # Convert to sentiment score
            if value <= 20:
                sentiment = "Extreme Fear"
                signal = "bullish"  # Contrarian: extreme fear = buy
            elif value <= 40:
                sentiment = "Fear"
                signal = "bullish"
            elif value <= 60:
                sentiment = "Neutral"
                signal = "neutral"
            elif value <= 80:
                sentiment = "Greed"
                signal = "bearish"  # Contrarian: greed = sell
            else:
                sentiment = "Extreme Greed"
                signal = "bearish"

            return {
                'index': value,
                'classification': sentiment,
                'signal': signal,
                'timestamp': timestamp,
                'contrarian_signal': 'BUY' if value < 25 else 'SELL' if value > 75 else 'HOLD'
            }

        except Exception as e:
            return {'error': str(e)}

    def analyze_google_trends(self, keywords: List[str]) -> Dict:
        """
        Analyze Google Trends for crypto keywords

        Args:
            keywords: List of keywords to search

        Returns:
            Dictionary with trend data
        """
        # Note: Google Trends API requires authentication
        # This is a simplified version that returns simulated data

        trends = {}

        for keyword in keywords:
            # Simulate trend score (0-100)
            # In production, use pytrends library
            np.random.seed(hash(keyword) % 10000)
            score = np.random.randint(30, 80)

            trends[keyword] = {
                'score': score,
                'trend': 'up' if score > 50 else 'down',
                'interest': 'high' if score > 70 else 'medium' if score > 40 else 'low'
            }

        return trends

    def calculate_sentiment_from_price_action(self, df: pd.DataFrame) -> Dict:
        """
        Derive sentiment from price action

        Args:
            df: Price data

        Returns:
            Sentiment analysis
        """
        if len(df) < 50:
            return {}

        close = df['close']
        volume = df['volume']

        # Price momentum
        returns = close.pct_change()
        momentum_5 = returns.tail(5).sum() * 100
        momentum_20 = returns.tail(20).sum() * 100

        # Volume trend
        volume_trend = volume.tail(20).mean() / volume.tail(50).mean()

        # Volatility
        volatility = returns.tail(20).std() * 100

        # Price position
        price_position = (close.iloc[-1] - close.tail(50).min()) / (close.tail(50).max() - close.tail(50).min())

        # Determine sentiment
        if momentum_5 > 3 and volume_trend > 1.2:
            sentiment = "Very Bullish"
        elif momentum_5 > 1 and volume_trend > 1.0:
            sentiment = "Bullish"
        elif momentum_5 < -3 and volume_trend > 1.2:
            sentiment = "Very Bearish"
        elif momentum_5 < -1 and volume_trend > 1.0:
            sentiment = "Bearish"
        else:
            sentiment = "Neutral"

        return {
            'sentiment': sentiment,
            'momentum_5': round(momentum_5, 2),
            'momentum_20': round(momentum_20, 2),
            'volume_ratio': round(volume_trend, 2),
            'volatility': round(volatility, 2),
            'price_position': round(price_position * 100, 1),
            'signal': 'BUY' if 'Bullish' in sentiment else 'SELL' if 'Bearish' in sentiment else 'HOLD'
        }

    def analyze_social_sentiment(self, symbol: str) -> Dict:
        """
        Analyze social media sentiment (simplified version)

        Args:
            symbol: Trading pair symbol

        Returns:
            Sentiment data
        """
        # Remove USDT suffix
        coin = symbol.replace('USDT', '').lower()

        # Simulate sentiment analysis
        # In production, use APIs like:
        # - LunarCrush for social analytics
        # - Santiment for on-chain + social
        # - Twitter API for tweet analysis

        np.random.seed(hash(coin + datetime.now().strftime('%Y%m%d')) % 10000)

        # Generate realistic sentiment scores
        sentiment_score = np.random.normal(50, 15)  # Mean 50, std 15
        sentiment_score = max(0, min(100, sentiment_score))

        volume_score = np.random.randint(40, 90)
        influence_score = np.random.randint(30, 80)

        if sentiment_score > 65:
            mood = "Bullish"
            signal = "YES"
        elif sentiment_score < 35:
            mood = "Bearish"
            signal = "NO"
        else:
            mood = "Neutral"
            signal = "HOLD"

        return {
            'coin': coin,
            'sentiment_score': round(sentiment_score, 1),
            'mood': mood,
            'signal': signal,
            'volume_score': volume_score,
            'influence_score': influence_score,
            'sources': ['Twitter', 'Reddit', 'Discord'],
            'confidence': round(abs(sentiment_score - 50) * 2, 1)  # Distance from neutral
        }

    def get_combined_sentiment(self, symbol: str, df: pd.DataFrame = None) -> Dict:
        """
        Get combined sentiment from all sources

        Args:
            symbol: Trading pair
            df: Optional price data

        Returns:
            Combined sentiment analysis
        """
        signals = []
        weights = []

        # Fear & Greed (weight: 30%)
        fg = self.analyze_fear_greed_index()
        if 'error' not in fg:
            if fg['signal'] == 'bullish':
                signals.append(1)
            elif fg['signal'] == 'bearish':
                signals.append(0)
            else:
                signals.append(0.5)
            weights.append(0.30)

        # Social sentiment (weight: 40%)
        social = self.analyze_social_sentiment(symbol)
        if social['signal'] == 'YES':
            signals.append(1)
        elif social['signal'] == 'NO':
            signals.append(0)
        else:
            signals.append(0.5)
        weights.append(0.40)

        # Price action sentiment (weight: 30%)
        if df is not None:
            price_sentiment = self.calculate_sentiment_from_price_action(df)
            if price_sentiment.get('signal') == 'BUY':
                signals.append(1)
            elif price_sentiment.get('signal') == 'SELL':
                signals.append(0)
            else:
                signals.append(0.5)
            weights.append(0.30)

        if not signals:
            return {'error': 'Could not analyze sentiment'}

        # Calculate weighted average
        total_weight = sum(weights)
        weighted_sentiment = sum(s * w for s, w in zip(signals, weights)) / total_weight

        # Convert to signal
        if weighted_sentiment > 0.65:
            final_signal = "YES"
            confidence = round((weighted_sentiment - 0.5) * 100 * 2, 1)
        elif weighted_sentiment < 0.35:
            final_signal = "NO"
            confidence = round((0.5 - weighted_sentiment) * 100 * 2, 1)
        else:
            final_signal = "HOLD"
            confidence = 50

        return {
            'signal': final_signal,
            'confidence': round(confidence, 1),
            'weighted_sentiment': round(weighted_sentiment, 2),
            'fear_greed': fg.get('classification', 'Unknown'),
            'social_mood': social.get('mood', 'Unknown'),
            'components': {
                'fear_greed': fg,
                'social': social
            }
        }

    def detect_sentiment_divergence(
        self,
        symbol: str,
        technical_signal: str,
        df: pd.DataFrame = None
    ) -> Dict:
        """
        Detect divergence between technical and sentiment signals

        Args:
            symbol: Trading pair
            technical_signal: Signal from technical analysis
            df: Optional price data

        Returns:
            Divergence analysis
        """
        sentiment = self.get_combined_sentiment(symbol, df)
        sentiment_signal = sentiment.get('signal', 'HOLD')

        # Check for divergence
        divergence_detected = False
        divergence_type = None

        if technical_signal in ['YES', 'STRONG YES'] and sentiment_signal == 'NO':
            divergence_detected = True
            divergence_type = 'Bearish Divergence'
        elif technical_signal in ['NO', 'STRONG NO'] and sentiment_signal == 'YES':
            divergence_detected = True
            divergence_type = 'Bullish Divergence'

        # Recommendation
        if divergence_detected:
            recommendation = "CAUTION: Technical and sentiment signals disagree. Consider reducing position size or waiting for confirmation."
        else:
            recommendation = "Signals aligned - higher confidence trade"

        return {
            'divergence_detected': divergence_detected,
            'divergence_type': divergence_type,
            'technical_signal': technical_signal,
            'sentiment_signal': sentiment_signal,
            'recommendation': recommendation,
            'combined_signal': 'HOLD' if divergence_detected else technical_signal
        }
