"""
Correlation Analysis Module
Analyzes inter-asset correlations for trading signals
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class CorrelationAnalyzer:
    """Analyze correlations between assets for trading insights"""

    def __init__(self):
        """Initialize correlation analyzer"""
        self.correlation_cache = {}
        self.cache_time = {}

    def calculate_correlation(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        period: int = 50
    ) -> Dict:
        """
        Calculate correlation between two assets

        Args:
            df1: Price data for asset 1
            df2: Price data for asset 2
            period: Lookback period

        Returns:
            Correlation data
        """
        if len(df1) < period or len(df2) < period:
            return {'error': 'Not enough data'}

        # Get returns
        returns1 = df1['close'].tail(period).pct_change().dropna()
        returns2 = df2['close'].tail(period).pct_change().dropna()

        if len(returns1) != len(returns2):
            # Align indices
            returns1 = returns1.tail(len(returns2))

        # Calculate correlation
        correlation = returns1.corr(returns2)

        # Determine strength
        if abs(correlation) >= 0.8:
            strength = "Very Strong"
        elif abs(correlation) >= 0.6:
            strength = "Strong"
        elif abs(correlation) >= 0.4:
            strength = "Moderate"
        elif abs(correlation) >= 0.2:
            strength = "Weak"
        else:
            strength = "Very Weak"

        return {
            'correlation': round(correlation, 3),
            'strength': strength,
            'direction': 'positive' if correlation > 0 else 'negative',
            'period': period
        }

    def analyze_leading_lagging(
        self,
        leader_df: pd.DataFrame,
        follower_df: pd.DataFrame,
        max_lag: int = 10
    ) -> Dict:
        """
        Determine if one asset leads another

        Args:
            leader_df: Potential leading asset data
            follower_df: Potential following asset data
            max_lag: Maximum periods to check for lag

        Returns:
            Leading/lagging analysis
        """
        if len(leader_df) < 100 or len(follower_df) < 100:
            return {'error': 'Not enough data'}

        leader_returns = leader_df['close'].pct_change().tail(100).dropna()
        follower_returns = follower_df['close'].pct_change().tail(100).dropna()

        best_correlation = 0
        best_lag = 0

        # Test different lags
        for lag in range(0, max_lag + 1):
            if lag >= len(leader_returns) or lag >= len(follower_returns):
                break

            # Shift leader returns by lag
            shifted_leader = leader_returns.shift(-lag).dropna()
            aligned_follower = follower_returns.iloc[:len(shifted_leader)]

            if len(shifted_leader) != len(aligned_follower):
                aligned_follower = aligned_follower.tail(len(shifted_leader))

            if len(shifted_leader) > 0:
                corr = shifted_leader.corr(aligned_follower)

                if abs(corr) > abs(best_correlation):
                    best_correlation = corr
                    best_lag = lag

        return {
            'best_correlation': round(best_correlation, 3),
            'best_lag': best_lag,
            'interpretation': f"Leader leads by {best_lag} periods" if best_lag > 0 else "No clear lead-lag"
        }

    def get_btc_influence(self, symbol: str, btc_df: pd.DataFrame, coin_df: pd.DataFrame) -> Dict:
        """
        Analyze BTC influence on altcoin

        Args:
            symbol: Altcoin symbol
            btc_df: BTC price data
            coin_df: Altcoin price data

        Returns:
            BTC influence analysis
        """
        # Calculate correlation
        corr_data = self.calculate_correlation(btc_df, coin_df, period=50)

        if 'error' in corr_data:
            return {'error': corr_data['error'], 'symbol': symbol}

        # Check if BTC leads
        lead_lag = self.analyze_leading_lagging(btc_df, coin_df, max_lag=5)

        # Determine influence level
        correlation = corr_data.get('correlation')
        if correlation is None:
            return {'error': 'Could not calculate correlation', 'symbol': symbol}

        influence_score = abs(correlation) * 100

        if influence_score > 80:
            influence = "Very High"
        elif influence_score > 60:
            influence = "High"
        elif influence_score > 40:
            influence = "Moderate"
        else:
            influence = "Low"

        # Trading implication
        btc_trend = "UP" if btc_df['close'].iloc[-1] > btc_df['close'].iloc[-5] else "DOWN"

        if correlation > 0.6:
            implication = f"{symbol} tends to follow BTC direction"
            btc_signal = "YES" if btc_trend == "UP" else "NO"
        elif correlation < -0.6:
            implication = f"{symbol} tends to move opposite to BTC"
            btc_signal = "NO" if btc_trend == "UP" else "YES"
        else:
            implication = f"{symbol} has weak correlation with BTC"
            btc_signal = "HOLD"

        return {
            'symbol': symbol,
            'btc_correlation': corr_data['correlation'],
            'influence_level': influence,
            'influence_score': round(influence_score, 1),
            'btc_leads_by': lead_lag.get('best_lag', 0),
            'btc_trend': btc_trend,
            'trading_implication': implication,
            'btc_signal': btc_signal,
            'confidence': round(influence_score, 1)
        }

    def get_eth_influence(self, symbol: str, eth_df: pd.DataFrame, coin_df: pd.DataFrame) -> Dict:
        """
        Analyze ETH influence on altcoin

        Args:
            symbol: Altcoin symbol
            eth_df: ETH price data
            coin_df: Altcoin price data

        Returns:
            ETH influence analysis
        """
        # Similar to BTC analysis
        corr_data = self.calculate_correlation(eth_df, coin_df, period=50)

        if 'error' in corr_data:
            return corr_data

        influence_score = abs(corr_data['correlation']) * 100

        eth_trend = "UP" if eth_df['close'].iloc[-1] > eth_df['close'].iloc[-5] else "DOWN"

        if corr_data['correlation'] > 0.6:
            eth_signal = "YES" if eth_trend == "UP" else "NO"
        elif corr_data['correlation'] < -0.6:
            eth_signal = "NO" if eth_trend == "UP" else "YES"
        else:
            eth_signal = "HOLD"

        return {
            'symbol': symbol,
            'eth_correlation': corr_data['correlation'],
            'influence_score': round(influence_score, 1),
            'eth_trend': eth_trend,
            'eth_signal': eth_signal
        }

    def analyze_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        Analyze overall market regime (risk-on vs risk-off)

        Args:
            market_data: Dictionary of symbol -> DataFrame

        Returns:
            Market regime analysis
        """
        if 'BTCUSDT' not in market_data:
            return {'error': 'BTC data required for regime analysis'}

        btc_df = market_data['BTCUSDT']

        # BTC trend strength
        btc_returns = btc_df['close'].tail(20).pct_change()
        btc_momentum = btc_returns.sum() * 100

        # BTC volatility
        btc_volatility = btc_returns.std() * 100

        # Determine regime
        if btc_momentum > 5 and btc_volatility < 5:
            regime = "Strong Risk-On"
            regime_signal = "Bullish"
        elif btc_momentum > 2:
            regime = "Moderate Risk-On"
            regime_signal = "Mildly Bullish"
        elif btc_momentum < -5 and btc_volatility < 5:
            regime = "Strong Risk-Off"
            regime_signal = "Bearish"
        elif btc_momentum < -2:
            regime = "Moderate Risk-Off"
            regime_signal = "Mildly Bearish"
        else:
            regime = "Neutral/Choppy"
            regime_signal = "Neutral"

        # Alts performance vs BTC
        alt_performance = {}
        for symbol, df in market_data.items():
            if symbol != 'BTCUSDT':
                alt_returns = df['close'].tail(20).pct_change().sum()
                alt_performance[symbol] = alt_returns - btc_returns.sum()

        # Find best/worst performers
        if alt_performance:
            best_alt = max(alt_performance, key=alt_performance.get)
            worst_alt = min(alt_performance, key=alt_performance.get)
        else:
            best_alt = None
            worst_alt = None

        return {
            'regime': regime,
            'signal': regime_signal,
            'btc_momentum': round(btc_momentum, 2),
            'btc_volatility': round(btc_volatility, 2),
            'alt_vs_btc': alt_performance,
            'best_performer': best_alt,
            'worst_performer': worst_alt,
            'trading_strategy': self._get_regime_strategy(regime)
        }

    def _get_regime_strategy(self, regime: str) -> str:
        """Get trading strategy for market regime"""
        strategies = {
            "Strong Risk-On": "Long alts, especially high beta",
            "Moderate Risk-On": "Selective longs, focus on leaders",
            "Strong Risk-Off": "Reduce exposure, short weak alts",
            "Moderate Risk-Off": "Conservative longs or wait",
            "Neutral/Choppy": "Range trading, small positions"
        }
        return strategies.get(regime, "Wait for clarity")

    def calculate_portfolio_beta(
        self,
        portfolio: Dict[str, float],
        btc_df: pd.DataFrame,
        market_data: Dict[str, pd.DataFrame]
    ) -> Dict:
        """
        Calculate portfolio beta vs BTC

        Args:
            portfolio: Dictionary of symbol -> weight
            btc_df: BTC price data
            market_data: All market data

        Returns:
            Portfolio beta and implications
        """
        if not portfolio:
            return {'error': 'Empty portfolio'}

        weighted_beta = 0

        for symbol, weight in portfolio.items():
            if symbol in market_data and symbol != 'BTCUSDT':
                coin_df = market_data[symbol]
                corr = self.calculate_correlation(btc_df, coin_df, period=50)

                if 'error' not in corr:
                    # Simplified beta calculation using correlation
                    beta = corr['correlation']
                    weighted_beta += beta * weight

        # Interpret beta
        if weighted_beta > 1.2:
            interpretation = "High beta - amplified BTC moves"
        elif weighted_beta > 0.8:
            interpretation = "Moderate beta - follows BTC"
        elif weighted_beta > 0.3:
            interpretation = "Low beta - less correlated"
        elif weighted_beta > -0.3:
            interpretation = "Very low correlation to BTC"
        else:
            interpretation = "Negative correlation - moves opposite BTC"

        return {
            'portfolio_beta': round(weighted_beta, 2),
            'interpretation': interpretation,
            'btc_move_impact': f"If BTC moves 1%, portfolio moves ~{weighted_beta:.1f}%"
        }
