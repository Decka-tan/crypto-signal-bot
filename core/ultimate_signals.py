"""
ULTIMATE Signal Generator
Combines ALL analysis methods for institutional-grade signals
- Multi-timeframe technical analysis
- Machine learning predictions
- Sentiment analysis
- Correlation analysis
- Funding rates
- Backtesting optimization
"""

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import pandas as pd
import numpy as np

from core.pro_signals import ProSignalGenerator
from core.ml_predictor import MLPredictor
from core.sentiment import SentimentAnalyzer
from core.correlation import CorrelationAnalyzer
from core.funding_rates import FundingRatesMonitor


class SignalType(Enum):
    """Types of trading signals"""
    ULTIMATE_BUY = "ULTIMATE YES"
    STRONG_BUY = "STRONG YES"
    BUY = "YES"
    HOLD = "HOLD"
    SELL = "NO"
    STRONG_SELL = "STRONG NO"
    ULTIMATE_SELL = "ULTIMATE NO"


class UltimateSignalGenerator:
    """Ultimate signal generator combining all analysis methods"""

    def __init__(self, config: Dict, market_monitor):
        """Initialize ultimate signal generator"""
        self.config = config
        self.market_monitor = market_monitor

        # Initialize all modules
        self.pro_generator = ProSignalGenerator(config, market_monitor)
        self.ml_predictor = MLPredictor()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.funding_monitor = FundingRatesMonitor()

    def generate_ultimate_signal(self, symbol: str) -> Dict:
        """
        Generate ultimate signal combining all analysis methods

        Args:
            symbol: Trading pair symbol

        Returns:
            Ultimate signal analysis
        """
        # 1. Get price data
        df = self.market_monitor.get_klines(symbol, limit=200)
        if df is None or len(df) < 100:
            return self._no_signal(symbol, "Insufficient data")

        # 2. Run all analysis modules
        analyses = {}

        # A. Multi-timeframe technical analysis
        analyses['technical'] = self._analyze_technical(symbol)

        # B. ML prediction
        analyses['ml'] = self._analyze_ml(df)

        # C. Sentiment analysis
        analyses['sentiment'] = self._analyze_sentiment(symbol, df)

        # D. Correlation analysis (if BTC/ETH available)
        analyses['correlation'] = self._analyze_correlation(symbol, df)

        # E. Funding rates
        analyses['funding'] = self._analyze_funding(symbol)

        # 3. Combine all signals
        combined = self._combine_signals(analyses)

        # 4. Calculate ultimate confidence
        ultimate_confidence = self._calculate_ultimate_confidence(combined, analyses)

        # 5. Determine final signal
        final_signal = self._determine_final_signal(combined, ultimate_confidence)

        # 6. Generate comprehensive report
        return {
            'symbol': symbol,
            'signal': final_signal.value,
            'signal_type': final_signal,
            'confidence': ultimate_confidence,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyses': analyses,
            'combined_scores': combined,
            'reasons': self._generate_ultimate_reasons(analyses, final_signal),
            'actionable_advice': self._generate_actionable_advice(final_signal, analyses),
            'risk_assessment': self._assess_risk(analyses)
        }

    def _analyze_technical(self, symbol: str) -> Dict:
        """Multi-timeframe technical analysis"""
        try:
            return self.pro_generator.analyze_multi_timeframe(symbol)
        except:
            return {'error': 'Technical analysis failed'}

    def _analyze_ml(self, df: pd.DataFrame) -> Dict:
        """ML-based predictions"""
        try:
            ml_signal = self.ml_predictor.predict_next_move(df, lookback=20)
            patterns = self.ml_predictor.detect_chart_patterns(df)

            return {
                'prediction': ml_signal.get('prediction', 'neutral'),
                'ml_confidence': ml_signal.get('confidence', 50),
                'similar_patterns': ml_signal.get('similar_patterns', 0),
                'patterns_detected': patterns,
                'pivot_probability': self.ml_predictor.calculate_pivot_probability(df)
            }
        except:
            return {'error': 'ML analysis failed'}

    def _analyze_sentiment(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Sentiment analysis"""
        try:
            return self.sentiment_analyzer.get_combined_sentiment(symbol, df)
        except:
            return {'error': 'Sentiment analysis failed'}

    def _analyze_correlation(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Correlation analysis"""
        try:
            # Try to get BTC data
            btc_df = self.market_monitor.get_klines('BTCUSDT', limit=200)

            if btc_df is not None:
                btc_influence = self.correlation_analyzer.get_btc_influence(symbol, btc_df, df)
                return {
                    'btc_influence': btc_influence,
                    'btc_signal': btc_influence.get('btc_signal', 'HOLD')
                }
            else:
                return {'error': 'BTC data unavailable'}
        except:
            return {'error': 'Correlation analysis failed'}

    def _analyze_funding(self, symbol: str) -> Dict:
        """Funding rates analysis"""
        try:
            return self.funding_monitor.get_derivatives_summary(symbol)
        except:
            return {'error': 'Funding analysis failed'}

    def _combine_signals(self, analyses: Dict) -> Dict:
        """Combine signals from all modules with weights"""
        signals = {}
        weights = {
            'technical': 0.35,
            'ml': 0.20,
            'sentiment': 0.20,
            'correlation': 0.15,
            'funding': 0.10
        }

        # Technical signal
        tech = analyses.get('technical', {})
        if 'signal_type' in tech:
            signals['technical'] = self._signal_to_score(tech['signal_type'])

        # ML signal
        ml = analyses.get('ml', {})
        ml_pred = ml.get('prediction', 'neutral')
        if ml_pred == 'bullish':
            signals['ml'] = 0.75
        elif ml_pred == 'bearish':
            signals['ml'] = 0.25
        else:
            signals['ml'] = 0.50

        # Sentiment signal
        sent = analyses.get('sentiment', {})
        sent_sig = sent.get('signal', 'HOLD')
        if sent_sig == 'YES':
            signals['sentiment'] = 0.70
        elif sent_sig == 'NO':
            signals['sentiment'] = 0.30
        else:
            signals['sentiment'] = 0.50

        # Correlation signal
        corr = analyses.get('correlation', {})
        signals['correlation'] = self._signal_to_score_str(corr.get('btc_signal', 'HOLD'))

        # Funding signal
        fund = analyses.get('funding', {})
        fund_sig = fund.get('overall_signal', 'HOLD')
        signals['funding'] = self._signal_to_score_str(fund_sig)

        # Calculate weighted score
        weighted_score = 0
        total_weight = 0

        for module, score in signals.items():
            if isinstance(score, (int, float)):
                weight = weights.get(module, 0.2)
                weighted_score += score * weight
                total_weight += weight

        final_score = weighted_score / total_weight if total_weight > 0 else 0.5

        return {
            'module_signals': signals,
            'weights': weights,
            'weighted_score': final_score,
            'signal_agreement': self._calculate_agreement(signals)
        }

    def _signal_to_score(self, signal_type) -> float:
        """Convert signal type to score"""
        if hasattr(signal_type, 'value'):
            signal_str = signal_type.value
        else:
            signal_str = str(signal_type)

        if 'ULTIMATE YES' in signal_str or 'STRONG YES' in signal_str:
            return 1.0
        elif 'YES' in signal_str:
            return 0.70
        elif 'HOLD' in signal_str:
            return 0.50
        elif 'NO' in signal_str:
            return 0.30
        elif 'ULTIMATE NO' in signal_str or 'STRONG NO' in signal_str:
            return 0.0
        else:
            return 0.50

    def _signal_to_score_str(self, signal_str: str) -> float:
        """Convert signal string to score"""
        if 'YES' in signal_str:
            return 0.70
        elif 'NO' in signal_str:
            return 0.30
        else:
            return 0.50

    def _calculate_agreement(self, signals: Dict) -> float:
        """Calculate how much modules agree"""
        scores = [s for s in signals.values() if isinstance(s, (int, float))]
        if not scores:
            return 0.5

        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)

        # Lower variance = higher agreement
        agreement = max(0, 1 - variance * 2)
        return agreement

    def _calculate_ultimate_confidence(self, combined: Dict, analyses: Dict) -> float:
        """Calculate ultimate confidence score"""
        base_confidence = 65

        # Agreement bonus
        agreement = combined.get('signal_agreement', 0.5)
        agreement_bonus = agreement * 25

        # Technical confidence
        tech = analyses.get('technical', {})
        tech_conf = tech.get('confidence', 0)
        tech_bonus = (tech_conf - 50) * 0.3

        # ML confidence
        ml = analyses.get('ml', {})
        ml_conf = ml.get('ml_confidence', 50)
        ml_bonus = (ml_conf - 50) * 0.2

        # Sentiment confidence
        sent = analyses.get('sentiment', {})
        sent_conf = sent.get('confidence', 0)
        sent_bonus = (sent_conf - 50) * 0.15

        # Calculate total
        total = base_confidence + agreement_bonus + tech_bonus + ml_bonus + sent_bonus

        return round(max(0, min(100, total)), 1)

    def _determine_final_signal(self, combined: Dict, confidence: float) -> SignalType:
        """Determine final signal type"""
        score = combined.get('weighted_score', 0.5)
        agreement = combined.get('signal_agreement', 0.5)

        # Ultimate signals require high agreement
        if agreement > 0.8:
            if score >= 0.85:
                return SignalType.ULTIMATE_BUY
            elif score <= 0.15:
                return SignalType.ULTIMATE_SELL

        # Strong signals
        if score >= 0.70:
            return SignalType.STRONG_BUY
        elif score <= 0.30:
            return SignalType.STRONG_SELL

        # Regular signals
        if score >= 0.55:
            return SignalType.BUY
        elif score <= 0.45:
            return SignalType.SELL

        return SignalType.HOLD

    def _generate_ultimate_reasons(self, analyses: Dict, final_signal: SignalType) -> List[str]:
        """Generate comprehensive reasons list"""
        reasons = []

        # Technical reasons
        tech = analyses.get('technical', {})
        tech_reasons = tech.get('reasons', [])
        for reason in tech_reasons[:3]:
            reasons.append(f"🔬 Technical: {reason}")

        # ML reasons
        ml = analyses.get('ml', {})
        ml_pred = ml.get('prediction', '')
        if ml_pred:
            ml_conf = ml.get('ml_confidence', 0)
            patterns = ml.get('patterns_detected', [])
            reasons.append(f"🤖 ML: {ml_pred} ({ml_conf}% conf)")
            if patterns:
                reasons.append(f"📊 Patterns: {', '.join(patterns[:2])}")

        # Sentiment reasons
        sent = analyses.get('sentiment', {})
        fg = sent.get('fear_greed', '')
        if fg:
            reasons.append(f"😊 Sentiment: {fg}")

        # Correlation reasons
        corr = analyses.get('correlation', {})
        btc_inf = corr.get('btc_influence', {})
        if btc_inf:
            influence = btc_inf.get('influence_level', '')
            reasons.append(f"🔗 BTC Influence: {influence}")

        # Funding reasons
        fund = analyses.get('funding', {})
        fund_sent = fund.get('funding_sentiment', '')
        if fund_sent:
            reasons.append(f"💰 Funding: {fund_sent}")

        return reasons

    def _generate_actionable_advice(self, signal: SignalType, analyses: Dict) -> Dict:
        """Generate actionable trading advice"""
        advice = {
            'action': '',
            'position_size': '',
            'entry_strategy': '',
            'exit_strategy': '',
            'risk_warning': []
        }

        if signal in [SignalType.ULTIMATE_BUY, SignalType.STRONG_BUY]:
            advice['action'] = 'BET YES - Strong bullish signal'
            advice['position_size'] = 'Standard to Large (3-5%)'
            advice['entry_strategy'] = 'Enter on 15m candle close'
            advice['exit_strategy'] = 'Take profit at resistance, stop loss below support'

            # Check for danger signals
            fund = analyses.get('funding', {})
            if fund.get('funding_rate', 0) > 0.05:
                advice['risk_warning'].append('High funding rate - potential long squeeze')

        elif signal in [SignalType.ULTIMATE_SELL, SignalType.STRONG_SELL]:
            advice['action'] = 'BET NO - Strong bearish signal'
            advice['position_size'] = 'Standard to Large (3-5%)'
            advice['entry_strategy'] = 'Enter on 15m candle close'
            advice['exit_strategy'] = 'Take profit at support, stop loss above resistance'

        elif signal == SignalType.BUY:
            advice['action'] = 'BET YES - Moderate bullish signal'
            advice['position_size'] = 'Small (1-2%)'
            advice['entry_strategy'] = 'Wait for pullback before entering'

        elif signal == SignalType.SELL:
            advice['action'] = 'BET NO - Moderate bearish signal'
            advice['position_size'] = 'Small (1-2%)'
            advice['entry_strategy'] = 'Wait for bounce before entering'

        else:
            advice['action'] = 'WAIT - No clear signal'
            advice['position_size'] = 'None'
            advice['entry_strategy'] = 'Wait for confirmation'

        return advice

    def _assess_risk(self, analyses: Dict) -> Dict:
        """Assess overall risk level"""
        risk_factors = []
        risk_level = "Medium"

        # Check funding rate risk
        fund = analyses.get('funding', {})
        # Handle error case
        if 'error' in fund or 'funding_rate' not in fund:
            funding_rate = 0
        else:
            funding_rate = fund.get('funding_rate', 0)

        if funding_rate is not None and abs(funding_rate) > 0.05:
            risk_factors.append("Extreme funding rate")
            risk_level = "High"

        # Check for low agreement
        tech = analyses.get('technical', {})
        agreement = tech.get('agreement', 0)
        if agreement < 50:
            risk_factors.append("Low timeframe agreement")
            risk_level = "Medium-High"

        # Check volatility
        ml = analyses.get('ml', {})
        pivot_probs = ml.get('pivot_probability', {})
        if pivot_probs:
            atr_multiple = pivot_probs.get('strong_support', {}).get('atr_away', 0)
            if atr_multiple > 3:
                risk_factors.append("High volatility - wide stops needed")

        return {
            'level': risk_level,
            'factors': risk_factors,
            'recommendation': self._get_risk_recommendation(risk_level, risk_factors)
        }

    def _get_risk_recommendation(self, level: str, factors: List[str]) -> str:
        """Get risk management recommendation"""
        if level == "High":
            return "REDUCE position size by 50% or wait for better setup"
        elif level == "Medium-High":
            return "Use smaller position size (1-2%) and tight stops"
        elif level == "Medium":
            return "Normal position size (2-3%) with standard stops"
        else:
            return "Consider increasing position size slightly"

    def _no_signal(self, symbol: str, reason: str) -> Dict:
        """Return no-signal result"""
        return {
            'symbol': symbol,
            'signal': SignalType.HOLD.value,
            'signal_type': SignalType.HOLD,
            'confidence': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analyses': {},
            'combined_scores': {},
            'reasons': [reason],
            'error': reason
        }
