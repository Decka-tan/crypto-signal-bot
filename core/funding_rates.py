"""
Funding Rates Module
Monitor funding rates and open interest for market sentiment
"""

import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class FundingRatesMonitor:
    """Monitor funding rates and derivatives market data"""

    def __init__(self):
        """Initialize funding rates monitor"""
        self.cache = {}
        self.last_update = {}

    def get_funding_rates(self) -> Dict:
        """
        Get funding rates from major exchanges

        Returns:
            Dictionary with funding rate data
        """
        # Note: In production, use APIs from:
        # - Binance Futures: https://fapi.binance.com/fapi/v1/premiumIndex
        # - Bybit: https://api.bybit.com/v5/market/funding/history
        # - OKX: https://www.okx.com/api/v5/public/funding-rate

        # For this demo, we'll simulate funding rates
        # Real implementation would fetch from exchange APIs

        coins = ['BTC', 'ETH', 'SOL', 'BNB', 'ADA']

        funding_data = {}

        for coin in coins:
            # Simulate realistic funding rates
            np.random.seed(hash(coin + datetime.now().strftime('%Y%m%d%H')) % 10000)

            base_rate = np.random.normal(0.01, 0.05)  # Mean 0.01%, std 0.05%

            funding_data[f"{coin}USDT"] = {
                'funding_rate': round(base_rate, 4),
                'annualized_rate': round(base_rate * 365 * 3, 2),  # 3x funding per day
                'timestamp': datetime.now().isoformat()
            }

        return funding_data

    def get_open_interest(self, symbol: str) -> Dict:
        """
        Get open interest for a symbol

        Args:
            symbol: Trading pair

        Returns:
            Open interest data
        """
        # Simulated data - in production use exchange APIs
        np.random.seed(hash(symbol) % 10000)

        base_oi = np.random.uniform(100, 1000)

        # Calculate change over 24h
        oi_change_24h = np.random.uniform(-10, 15)

        return {
            'open_interest': round(base_oi, 2),
            'change_24h_pct': round(oi_change_24h, 2),
            'trend': 'increasing' if oi_change_24h > 5 else 'decreasing' if oi_change_24h < -5 else 'stable'
        }

    def analyze_funding_sentiment(self, symbol: str) -> Dict:
        """
        Analyze market sentiment from funding rates

        Args:
            symbol: Trading pair

        Returns:
            Sentiment analysis from funding
        """
        funding_rates = self.get_funding_rates()

        if symbol not in funding_rates:
            return {'error': f'No funding data for {symbol}'}

        rate = funding_rates[symbol]['funding_rate']
        annualized = funding_rates[symbol]['annualized_rate']

        # Interpret funding rate
        if rate > 0.05:
            sentiment = "Very Bullish"
            interpretation = "Longs paying shorts - extreme bullishness"
            contrarian_signal = "BEARISH"  # Too crowded
        elif rate > 0.02:
            sentiment = "Bullish"
            interpretation = "Longs paying shorts - moderate bullishness"
            contrarian_signal = "NEUTRAL"
        elif rate > -0.02:
            sentiment = "Neutral"
            interpretation = "Balanced funding"
            contrarian_signal = "NEUTRAL"
        elif rate > -0.05:
            sentiment = "Bearish"
            interpretation = "Shorts paying longs - bearish pressure"
            contrarian_signal = "BULLISH"  # Oversold
        else:
            sentiment = "Very Bearish"
            interpretation = "Extreme bearishness - shorts crowded"
            contrarian_signal = "BULLISH"

        # Get open interest
        oi_data = self.get_open_interest(symbol)

        # Combine signals
        oi_trend = oi_data.get('trend', 'stable')

        # Combined interpretation
        if rate > 0.05 and oi_trend == 'increasing':
            combined = "DANGER: Crowded longs, potential liquidation cascade"
            signal = "NO"  # Short
        elif rate < -0.05 and oi_trend == 'increasing':
            combined = "SQUEEZE ALERT: Crowded shorts, potential squeeze"
            signal = "YES"  # Long
        elif rate > 0 and oi_trend == 'decreasing':
            combined = "Bullish but OI dropping - trend weakening"
            signal = "HOLD"
        elif rate < 0 and oi_trend == 'decreasing':
            combined = "Bearish but OI dropping - selling pressure easing"
            signal = "HOLD"
        else:
            combined = f"{sentiment}, OI {oi_trend}"
            signal = "YES" if 'Bullish' in sentiment else "NO" if 'Bearish' in sentiment else "HOLD"

        return {
            'symbol': symbol,
            'funding_rate': rate,
            'annualized_pct': annualized,
            'sentiment': sentiment,
            'interpretation': interpretation,
            'contrarian_signal': contrarian_signal,
            'open_interest': oi_data,
            'combined_analysis': combined,
            'signal': signal,
            'confidence': round(abs(rate) * 1000, 1)  # Higher rate = higher confidence
        }

    def detect_funding_rate_extremes(self, symbols: List[str]) -> Dict:
        """
        Detect symbols with extreme funding rates

        Args:
            symbols: List of symbols to check

        Returns:
            Symbols with extreme funding rates
        """
        funding_rates = self.get_funding_rates()

        extremes = {
            'extreme_bullish': [],  # Very high positive funding
            'extreme_bearish': [],  # Very negative funding
            'normal': []
        }

        for symbol in symbols:
            if symbol in funding_rates:
                rate = funding_rates[symbol]['funding_rate']

                if rate > 0.05:
                    extremes['extreme_bullish'].append({
                        'symbol': symbol,
                        'rate': rate,
                        'signal': 'NO (contrarian)'
                    })
                elif rate < -0.05:
                    extremes['extreme_bearish'].append({
                        'symbol': symbol,
                        'rate': rate,
                        'signal': 'YES (contrarian)'
                    })
                else:
                    extremes['normal'].append(symbol)

        return extremes

    def get_long_short_ratio(self, symbol: str) -> Dict:
        """
        Get long/short ratio (simulated)

        Args:
            symbol: Trading pair

        Returns:
            Long/short ratio data
        """
        # Simulated data
        np.random.seed(hash(symbol + datetime.now().strftime('%Y%m%d')) % 10000)

        ratio = np.random.uniform(0.8, 1.5)

        if ratio > 1.2:
            sentiment = "Bullish crowd"
            contrarian = "bearish"
        elif ratio < 0.8:
            sentiment = "Bearish crowd"
            contrarian = "bullish"
        else:
            sentiment = "Balanced"
            contrarian = "neutral"

        return {
            'symbol': symbol,
            'long_short_ratio': round(ratio, 2),
            'sentiment': sentiment,
            'contrarian_view': contrarian
        }

    def get_liquidation_data(self, symbol: str) -> Dict:
        """
        Get liquidation data (simulated)

        Args:
            symbol: Trading pair

        Returns:
            Liquidation data
        """
        # Simulated data - in production use exchange APIs
        np.random.seed(hash(symbol) % 10000)

        long_liquidations = np.random.uniform(0, 10)
        short_liquidations = np.random.uniform(0, 10)

        total_liq = long_liquidations + short_liquidations

        if total_liq > 15:
            level = "High liquidation activity"
        elif total_liq > 5:
            level = "Moderate liquidation activity"
        else:
            level = "Low liquidation activity"

        if long_liquidations > short_liquidations * 2:
            implication = "Longs being liquidated - potential reversal down"
        elif short_liquidations > long_liquidations * 2:
            implication = "Shorts being liquidated - potential squeeze up"
        else:
            implication = "Balanced liquidations"

        return {
            'symbol': symbol,
            'long_liquidations_m': round(long_liquidations, 2),
            'short_liquidations_m': round(short_liquidations, 2),
            'total_liquidations_m': round(total_liq, 2),
            'level': level,
            'implication': implication
        }

    def get_derivatives_summary(self, symbol: str) -> Dict:
        """
        Get comprehensive derivatives market summary

        Args:
            symbol: Trading pair

        Returns:
            Complete derivatives analysis
        """
        funding = self.analyze_funding_sentiment(symbol)
        oi = self.get_open_interest(symbol)
        ls_ratio = self.get_long_short_ratio(symbol)
        liquidations = self.get_liquidation_data(symbol)

        # Overall signal
        signals = []
        weights = []

        # Funding rate signal (40% weight)
        signals.append(funding.get('signal', 'HOLD'))
        weights.append(0.4)

        # Long/short ratio (30% weight)
        if ls_ratio['contrarian_view'] == 'bullish':
            signals.append('YES')
        elif ls_ratio['contrarian_view'] == 'bearish':
            signals.append('NO')
        else:
            signals.append('HOLD')
        weights.append(0.3)

        # Liquidation implication (30% weight)
        liq_implication = liquidations.get('implication', '')
        if 'squeeze up' in liq_implication:
            signals.append('YES')
        elif 'reversal down' in liq_implication:
            signals.append('NO')
        else:
            signals.append('HOLD')
        weights.append(0.3)

        # Calculate weighted signal
        yes_weight = sum(w for s, w in zip(signals, weights) if s == 'YES')
        no_weight = sum(w for s, w in zip(signals, weights) if s == 'NO')

        if yes_weight > 0.6:
            overall_signal = 'YES'
        elif no_weight > 0.6:
            overall_signal = 'NO'
        else:
            overall_signal = 'HOLD'

        return {
            'symbol': symbol,
            'overall_signal': overall_signal,
            'funding_rate': funding.get('funding_rate'),
            'funding_sentiment': funding.get('sentiment'),
            'open_interest_trend': oi.get('trend'),
            'long_short_ratio': ls_ratio.get('long_short_ratio'),
            'liquidation_level': liquidations.get('level'),
            'market_state': self._determine_market_state(funding, oi, ls_ratio),
            'trading_implications': self._get_trading_implications(funding, oi, liquidations)
        }

    def _determine_market_state(self, funding: Dict, oi: Dict, ls_ratio: Dict) -> str:
        """Determine overall market state"""
        rate = funding.get('funding_rate', 0)
        oi_trend = oi.get('trend', 'stable')
        ratio = ls_ratio.get('long_short_ratio', 1)

        if rate > 0.05 and oi_trend == 'increasing' and ratio > 1.3:
            return "EUPHORIC - Danger zone"
        elif rate > 0.02 and oi_trend == 'increasing':
            return "GREED - Bullish but cautious"
        elif rate < -0.02 and oi_trend == 'increasing' and ratio < 0.7:
            return "PANIC - Capitulation"
        elif rate < -0.02:
            return "FEAR - Bearish"
        else:
            return "NEUTRAL"

    def _get_trading_implications(self, funding: Dict, oi: Dict, liquidations: Dict) -> List[str]:
        """Get trading implications"""
        implications = []

        rate = funding.get('funding_rate', 0)
        oi_change = oi.get('change_24h_pct', 0)
        liq_level = liquidations.get('level', '')

        if rate > 0.05:
            implications.append("⚠️ Extreme funding - consider short or wait")

        if oi_change > 10 and rate > 0:
            implications.append("📈 OI surging with longs - watch for reversal")

        if oi_change < -10:
            implications.append("📉 OI dropping - trend may be ending")

        if 'High' in liq_level:
            implications.append("💥 High liquidations - volatility elevated")

        if not implications:
            implications.append("✅ Normal market conditions")

        return implications
