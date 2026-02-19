"""
Advanced Technical Indicators Module
Adds professional-grade indicators for improved signal accuracy
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


class AdvancedIndicators:
    """Advanced technical indicators for professional trading"""

    @staticmethod
    def atr(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range - Measures volatility

        Args:
            data: DataFrame with high, low, close columns
            period: ATR period (default 14)

        Returns:
            Series with ATR values
        """
        high = data['high']
        low = data['low']
        close = data['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def adx(data: pd.DataFrame, period: int = 14) -> Dict[str, pd.Series]:
        """
        Average Directional Index - Measures trend strength

        Args:
            data: DataFrame with high, low, close columns
            period: ADX period (default 14)

        Returns:
            Dictionary with 'adx', 'di_plus', 'di_minus' series
        """
        high = data['high']
        low = data['low']
        close = data['close']

        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate directional movements
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # Calculate smoothed values
        atr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di_smooth = pd.Series(plus_dm, index=tr.index).ewm(alpha=1/period, adjust=False).mean()
        minus_di_smooth = pd.Series(minus_dm, index=tr.index).ewm(alpha=1/period, adjust=False).mean()

        # Calculate DX
        plus_di = 100 * (plus_di_smooth / atr_smooth)
        minus_di = 100 * (minus_di_smooth / atr_smooth)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

        # Calculate ADX
        adx = dx.ewm(alpha=1/period, adjust=False).mean()

        return {
            'adx': adx,
            'di_plus': plus_di,
            'di_minus': minus_di
        }

    @staticmethod
    def stochastic(data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """
        Stochastic Oscillator - Measures momentum

        Args:
            data: DataFrame with high, low, close columns
            k_period: %K period (default 14)
            d_period: %D period (default 3)

        Returns:
            Dictionary with 'k' and 'd' series
        """
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()

        k = 100 * (data['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()

        return {
            'k': k,
            'd': d
        }

    @staticmethod
    def williams_r(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Williams %R - Momentum indicator

        Args:
            data: DataFrame with high, low, close columns
            period: Lookback period (default 14)

        Returns:
            Series with Williams %R values (-100 to 0)
        """
        high_max = data['high'].rolling(window=period).max()
        low_min = data['low'].rolling(window=period).min()

        wr = -100 * (high_max - data['close']) / (high_max - low_min)

        return wr

    @staticmethod
    def cci(data: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Commodity Channel Index - Identifies cyclical trends

        Args:
            data: DataFrame with high, low, close columns
            period: CCI period (default 20)

        Returns:
            Series with CCI values
        """
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        sma = typical_price.rolling(window=period).mean()
        mean_deviation = typical_price.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean()
        )

        cci = (typical_price - sma) / (0.015 * mean_deviation)

        return cci

    @staticmethod
    def money_flow_index(data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Money Flow Index - Measures buying/selling pressure

        Args:
            data: DataFrame with high, low, close, volume columns
            period: MFI period (default 14)

        Returns:
            Series with MFI values (0-100)
        """
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        money_flow = typical_price * data['volume']

        # Determine positive/negative money flow
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        # Calculate money ratio
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        money_ratio = positive_mf / negative_mf

        # Calculate MFI
        mfi = 100 - (100 / (1 + money_ratio))

        return mfi

    @staticmethod
    def vwap(data: pd.DataFrame) -> pd.Series:
        """
        Volume Weighted Average Price

        Args:
            data: DataFrame with high, low, close, volume columns

        Returns:
            Series with VWAP values
        """
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        vwap = (typical_price * data['volume']).cumsum() / data['volume'].cumsum()

        return vwap

    @staticmethod
    def pivot_points(data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate pivot points and support/resistance levels

        Args:
            data: DataFrame with high, low, close columns (uses latest candle)

        Returns:
            Dictionary with pivot, support, and resistance levels
        """
        high = data['high'].iloc[-1]
        low = data['low'].iloc[-1]
        close = data['close'].iloc[-1]

        pivot = (high + low + close) / 3

        resistance1 = 2 * pivot - low
        resistance2 = pivot + (high - low)
        resistance3 = high + 2 * (pivot - low)

        support1 = 2 * pivot - high
        support2 = pivot - (high - low)
        support3 = low - 2 * (high - pivot)

        return {
            'pivot': pivot,
            'r1': resistance1,
            'r2': resistance2,
            'r3': resistance3,
            's1': support1,
            's2': support2,
            's3': support3
        }

    @staticmethod
    def fibonacci_retracements(high: float, low: float) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels

        Args:
            high: Recent high price
            low: Recent low price

        Returns:
            Dictionary with Fibonacci levels
        """
        diff = high - low

        return {
            '0%': high,
            '23.6%': high - (diff * 0.236),
            '38.2%': high - (diff * 0.382),
            '50%': high - (diff * 0.5),
            '61.8%': high - (diff * 0.618),
            '78.6%': high - (diff * 0.786),
            '100%': low
        }

    @staticmethod
    def get_trend_quality(adx: float, di_plus: float, di_minus: float) -> Dict:
        """
        Analyze trend quality based on ADX

        Args:
            adx: ADX value
            di_plus: +DI value
            di_minus: -DI value

        Returns:
            Dictionary with trend analysis
        """
        if adx < 20:
            trend = "absent"
            quality = "weak"
        elif adx < 25:
            trend = "weak"
            quality = "developing"
        elif adx < 40:
            trend = di_plus > di_minus and "bullish" or "bearish"
            quality = "strong"
        else:
            trend = di_plus > di_minus and "bullish" or "bearish"
            quality = "very strong"

        return {
            'trend': trend,
            'quality': quality,
            'strength': adx,
            'direction': di_plus > di_minus and 'up' or 'down'
        }
