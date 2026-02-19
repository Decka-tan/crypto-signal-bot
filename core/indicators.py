"""
Technical Indicators Module
Implements various technical analysis indicators for signal generation
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


class TechnicalIndicators:
    """Calculate technical indicators for market analysis"""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index

        Args:
            data: Price series (usually close prices)
            period: RSI period (default 14)

        Returns:
            Series with RSI values (0-100)
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """
        Moving Average Convergence Divergence (MACD)

        Args:
            data: Price series (usually close prices)
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' series
        """
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)

        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """
        Bollinger Bands

        Args:
            data: Price series (usually close prices)
            period: Period for middle band (default 20)
            std_dev: Standard deviation for bands (default 2)

        Returns:
            Dictionary with 'upper', 'middle', and 'lower' bands
        """
        middle = TechnicalIndicators.sma(data, period)
        std = data.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Volume Simple Moving Average"""
        return volume.rolling(window=period).mean()

    @staticmethod
    def support_resistance(data: pd.Series, window: int = 20) -> Dict[str, float]:
        """
        Find dynamic support and resistance levels

        Args:
            data: Price series (usually close prices)
            window: Lookback period (default 20)

        Returns:
            Dictionary with 'support' and 'resistance' levels
        """
        recent = data.tail(window)

        # Find local minima (support) and maxima (resistance)
        support = recent.min()
        resistance = recent.max()

        # Current price
        current = data.iloc[-1]

        # Calculate support/resistance zones
        distance = resistance - support
        support_zone = support + (distance * 0.1)
        resistance_zone = resistance - (distance * 0.1)

        return {
            'support': support,
            'resistance': resistance,
            'support_zone': support_zone,
            'resistance_zone': resistance_zone,
            'current': current
        }

    @staticmethod
    def calculate_all(df: pd.DataFrame, config: Dict) -> Dict:
        """
        Calculate all enabled indicators for a DataFrame

        Args:
            df: DataFrame with OHLCV data
            config: Configuration dictionary with indicator settings

        Returns:
            Dictionary with all calculated indicators
        """
        indicators = {}

        # RSI
        if config.get('rsi', {}).get('enabled', True):
            rsi_period = config.get('rsi', {}).get('period', 14)
            indicators['rsi'] = TechnicalIndicators.rsi(df['close'], rsi_period).iloc[-1]

        # MACD
        if config.get('macd', {}).get('enabled', True):
            fast = config.get('macd', {}).get('fast', 12)
            slow = config.get('macd', {}).get('slow', 26)
            signal = config.get('macd', {}).get('signal', 9)

            macd_data = TechnicalIndicators.macd(df['close'], fast, slow, signal)
            indicators['macd'] = macd_data['macd'].iloc[-1]
            indicators['macd_signal'] = macd_data['signal'].iloc[-1]
            indicators['macd_histogram'] = macd_data['histogram'].iloc[-1]
            indicators['macd_trend'] = 'bullish' if macd_data['histogram'].iloc[-1] > 0 else 'bearish'

        # EMA
        if config.get('ema', {}).get('enabled', True):
            short = config.get('ema', {}).get('short', 9)
            long = config.get('ema', {}).get('long', 21)

            ema_short = TechnicalIndicators.ema(df['close'], short).iloc[-1]
            ema_long = TechnicalIndicators.ema(df['close'], long).iloc[-1]

            indicators['ema_short'] = ema_short
            indicators['ema_long'] = ema_long
            indicators['ema_cross'] = 'bullish' if ema_short > ema_long else 'bearish'

        # Bollinger Bands
        if config.get('bollinger_bands', {}).get('enabled', True):
            period = config.get('bollinger_bands', {}).get('period', 20)
            std = config.get('bollinger_bands', {}).get('std', 2)

            bb = TechnicalIndicators.bollinger_bands(df['close'], period, std)

            indicators['bb_upper'] = bb['upper'].iloc[-1]
            indicators['bb_middle'] = bb['middle'].iloc[-1]
            indicators['bb_lower'] = bb['lower'].iloc[-1]

            # Calculate %B (position within bands)
            current_price = df['close'].iloc[-1]
            bb_range = bb['upper'].iloc[-1] - bb['lower'].iloc[-1]
            if bb_range > 0:
                indicators['bb_percent'] = ((current_price - bb['lower'].iloc[-1]) / bb_range) * 100
            else:
                indicators['bb_percent'] = 50

        # Volume
        if config.get('volume', {}).get('enabled', True):
            period = config.get('volume', {}).get('period', 20)

            avg_volume = TechnicalIndicators.volume_sma(df['volume'], period).iloc[-1]
            current_volume = df['volume'].iloc[-1]

            indicators['volume'] = current_volume
            indicators['avg_volume'] = avg_volume
            indicators['volume_ratio'] = (current_volume / avg_volume) * 100 if avg_volume > 0 else 100

        # Support/Resistance
        sr = TechnicalIndicators.support_resistance(df['close'])
        indicators['support'] = sr['support']
        indicators['resistance'] = sr['resistance']
        indicators['distance_to_support'] = ((sr['current'] - sr['support']) / sr['current']) * 100
        indicators['distance_to_resistance'] = ((sr['resistance'] - sr['current']) / sr['current']) * 100

        return indicators
