"""
Unhedged API Client - Semi-Automated Betting
Fetches markets, prepares bet commands for manual execution
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime


class UnhedgedClient:
    """Unhedged API client for prediction market betting"""

    def __init__(self, api_key: str):
        """
        Initialize Unhedged client

        Args:
            api_key: Unhedged API key (Bearer token)
        """
        self.api_key = api_key
        self.base_url = "https://unhedged.gg/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_markets(self) -> Dict:
        """
        Get all available prediction markets

        Returns:
            Market data with prices
        """
        # Try different endpoints
        endpoints = [
            f"{self.base_url}/markets",
            f"{self.base_url}/market",
            f"{self.base_url}/bets",  # Some APIs use /bets for listing
            "https://unhedged.gg/api/v1/markets",
            "https://unhedged.gg/api/markets",
        ]

        for url in endpoints:
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    return response.json()
            except:
                continue

        return {'error': 'Could not fetch markets - API endpoint not found or requires different auth'}

    def get_markets_manual(self) -> Dict:
        """
        Manual market list - user needs to configure market IDs manually

        Returns:
            Dict of symbol -> market_id mappings from config
        """
        # This will be populated from config
        return {}

    def get_market_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Find market for specific trading pair

        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "ETHUSDT")

        Returns:
            Market data or None
        """
        markets = self.get_markets()

        if 'error' in markets:
            return None

        # Try to find matching market
        # Unhedged markets might have different naming
        symbol_variants = [
            symbol,
            symbol.replace('USDT', ''),
            symbol.replace('USDT', '/USDT'),
            symbol.replace('USDT', '-USDT'),
        ]

        for market in markets.get('data', []):
            market_name = market.get('name', '').upper()
            market_id = market.get('id', '').upper()

            for variant in symbol_variants:
                if variant in market_name or variant in market_id:
                    return market

        return None

    def get_market_odds(self, market_id: str) -> Optional[Dict]:
        """
        Get current odds for a specific market

        Args:
            market_id: Market ID

        Returns:
            Odds data
        """
        try:
            url = f"{self.base_url}/markets/{market_id}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return None

    def prepare_bet_command(
        self,
        market_id: str,
        outcome: str,  # "YES" or "NO"
        amount: float,
        confidence: float
    ) -> Dict:
        """
        Prepare bet command for manual execution

        Args:
            market_id: Unhedged market ID
            outcome: "YES" or "NO"
            amount: Bet amount in USD
            confidence: Signal confidence %

        Returns:
            Prepared bet command info
        """
        # Generate direct market link
        market_link = f"https://unhedged.gg/markets/{market_id}"

        # Determine outcome index (usually 0 for YES, 1 for NO)
        outcome_index = 0 if outcome.upper() == "YES" else 1

        # Prepare curl command (fallback)
        curl_command = f"""curl -X POST {self.base_url}/bets \\
  -H "Authorization: Bearer {self.api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{{"marketId":"{market_id}","outcomeIndex":{outcome_index},"amount":{amount}}}'"""

        return {
            'market_id': market_id,
            'outcome': outcome.upper(),
            'outcome_index': outcome_index,
            'amount': amount,
            'confidence': confidence,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market_link': market_link,
            'curl_command': curl_command
        }

    def get_account_balance(self) -> Optional[Dict]:
        """
        Get account balance

        Returns:
            Balance info
        """
        try:
            url = f"{self.base_url}/account"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except:
            return {'error': 'Failed to fetch balance'}

    def place_bet(
        self,
        market_id: str,
        outcome_index: int,
        amount: float
    ) -> Dict:
        """
        Place a bet (USE WITH CAUTION!)

        Args:
            market_id: Market ID
            outcome_index: 0 for YES, 1 for NO
            amount: Bet amount

        Returns:
            Bet result
        """
        try:
            url = f"{self.base_url}/bets"
            payload = {
                "marketId": market_id,
                "outcomeIndex": outcome_index,
                "amount": amount
            }

            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {'error': str(e)}

    def match_symbol_to_market(self, symbol: str, available_markets: List[Dict]) -> Optional[Dict]:
        """
        Match our crypto symbol to Unhedged market

        Args:
            symbol: Our symbol (e.g., "BTCUSDT")
            available_markets: List of Unhedged markets

        Returns:
            Matched market or None
        """
        # Extract base symbol (BTC, ETH, SOL, CC)
        base_symbol = symbol.replace('USDT', '').replace('USDC', '')

        # Search patterns
        search_patterns = [
            base_symbol,
            f"{base_symbol}USDT",
            f"{base_symbol}/USDT",
            f"{base_symbol}-USDT",
            base_symbol.lower(),
        ]

        for market in available_markets:
            market_name = market.get('name', '')
            market_question = market.get('question', '')
            market_id = market.get('id', '')

            # Check all fields
            for pattern in search_patterns:
                if pattern.upper() in market_name.upper():
                    return market
                if pattern.upper() in market_question.upper():
                    return market
                if pattern.upper() in market_id.upper():
                    return market

        return None

    def get_active_crypto_markets(self) -> List[Dict]:
        """
        Get only active crypto price prediction markets

        Returns:
            List of active crypto markets
        """
        markets = self.get_markets()

        if 'error' in markets:
            return []

        crypto_keywords = ['BTC', 'ETH', 'SOL', 'CRYPTO', 'PRICE', 'USDT', 'USDC']

        active_markets = []
        for market in markets.get('data', []):
            # Filter for active markets
            if market.get('status', '').upper() != 'ACTIVE':
                continue

            # Filter for crypto-related markets
            market_name = market.get('name', '').upper()
            market_question = market.get('question', '').upper()

            is_crypto = any(keyword in market_name or keyword in market_question
                           for keyword in crypto_keywords)

            if is_crypto:
                active_markets.append(market)

        return active_markets


class BetPreparer:
    """Prepares bets based on signals"""

    def __init__(self, unhedged_client: UnhedgedClient, config: Dict):
        """
        Initialize bet preparer

        Args:
            unhedged_client: Unhedged API client
            config: Bot configuration
        """
        self.client = unhedged_client
        self.config = config

        # Bet sizing config
        self.bettings = config.get('betting', {})
        self.base_bet_amount = self.bettings.get('base_amount', 10)
        self.max_bet_amount = self.bettings.get('max_amount', 100)
        self.min_confidence_for_bet = self.bettings.get('min_confidence', 75)

        # Manual market ID mappings from config
        self.manual_markets = config.get('unhedged', {}).get('manual_markets') or {}

    def prepare_bet_from_signal(self, signal_analysis: Dict) -> Optional[Dict]:
        """
        Prepare bet command from signal analysis
        CORRECTLY converts trading signal to prediction market outcome

        Args:
            signal_analysis: Signal analysis from ultimate_signals

        Returns:
            Prepared bet info or None
        """
        # Check confidence threshold
        confidence = signal_analysis.get('confidence', 0)
        if confidence < self.min_confidence_for_bet:
            return None

        # Check signal type
        signal = signal_analysis.get('signal', '')
        if 'HOLD' in signal or confidence < 75:
            return None

        # Get symbol
        symbol = signal_analysis.get('symbol', '')

        # Check if we have market info from scraping (preferred!)
        market_link = signal_analysis.get('market_link', '')
        market_id = signal_analysis.get('market_id', '')
        market_question = signal_analysis.get('market_question', '')

        # If we have scraped market info, use it
        if market_id and market_link:
            # Determine outcome based on MARKET QUESTION + PREDICTED PRICE
            outcome = self._determine_outcome_from_market(
                market_question,
                signal_analysis,
                signal
            )

            # Use scraped market info
            market_name = market_question[:50] if market_question else f"{symbol} market"
        else:
            # Fallback to manual mapping (old method)
            market_id = self.manual_markets.get(symbol)

            if not market_id:
                # Try API (less reliable)
                active_markets = self.client.get_active_crypto_markets()
                matched_market = self.client.match_symbol_to_market(symbol, active_markets)
                if matched_market:
                    market_id = matched_market.get('id', '')
                    market_question = matched_market.get('question', '')
                    market_name = matched_market.get('name', '')
                else:
                    return None
            else:
                market_name = f"{symbol} (manual config)"

            # Determine outcome from market question
            if market_question:
                outcome = self._determine_outcome_from_market(
                    market_question,
                    signal_analysis,
                    signal
                )
            else:
                # No question available, use signal as fallback
                outcome = "YES" if "YES" in signal else "NO"

        # Calculate bet size based on confidence
        bet_amount = self._calculate_bet_amount(confidence, signal)

        # Prepare command
        prepared_bet = self.client.prepare_bet_command(
            market_id=market_id,
            outcome=outcome,
            amount=bet_amount,
            confidence=confidence
        )

        # Add market info
        prepared_bet['symbol'] = symbol
        prepared_bet['signal'] = signal
        prepared_bet['market_name'] = market_name
        prepared_bet['market_id'] = market_id
        prepared_bet['market_question'] = f"Bet {outcome} on {symbol}"
        prepared_bet['market_link'] = market_link
        prepared_bet['current_odds'] = {}

        return prepared_bet

    def _determine_outcome_from_market(self, market_question: str, signal_analysis: Dict, signal: str) -> str:
        """
        Determine the correct outcome (YES/NO) based on:
        1. Market question (what's being asked?)
        2. Predicted price (where will price be?)

        Args:
            market_question: e.g., "SOL above $83.014 at 12:00 PM?"
            signal_analysis: Contains predicted_price
            signal: Trading signal (fallback)

        Returns:
            "YES" or "NO"
        """
        import re

        # Parse the market question to get target price and direction
        # Pattern: "above $X", "below $X"
        above_match = re.search(r'above\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)
        below_match = re.search(r'below\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)

        # Get predicted price
        predicted_price = signal_analysis.get('predicted_price')
        current_price = signal_analysis.get('current_price')

        if predicted_price and current_price:
            # We have predicted price - use it to determine outcome
            if above_match:
                target_price = float(above_match.group(1).replace(',', ''))
                # Market: "Price above $X?"
                # YES if predicted > target, NO if predicted <= target
                if predicted_price > target_price:
                    return "YES"
                else:
                    return "NO"
            elif below_match:
                target_price = float(below_match.group(1).replace(',', ''))
                # Market: "Price below $X?"
                # YES if predicted < target, NO if predicted >= target
                if predicted_price < target_price:
                    return "YES"
                else:
                    return "NO"

        # Fallback: Use trading signal
        return "YES" if "YES" in signal else "NO"

    def _calculate_bet_amount(self, confidence: float, signal: str) -> float:
        """
        Calculate bet size based on confidence and signal strength

        Args:
            confidence: Signal confidence %
            signal: Signal type

        Returns:
            Bet amount in USD
        """
        # Base amount
        amount = self.base_bet_amount

        # Confidence multiplier
        if confidence >= 90:
            multiplier = 3.0
        elif confidence >= 85:
            multiplier = 2.0
        elif confidence >= 80:
            multiplier = 1.5
        else:
            multiplier = 1.0

        # Signal strength multiplier
        if 'ULTIMATE' in signal:
            multiplier *= 1.5
        elif 'STRONG' in signal:
            multiplier *= 1.2

        amount = amount * multiplier

        # Cap at max
        return round(min(amount, self.max_bet_amount), 2)

    def format_bet_for_display(self, prepared_bet: Dict) -> str:
        """
        Format prepared bet for console/Discord display

        Args:
            prepared_bet: Prepared bet info

        Returns:
            Formatted string
        """
        lines = []
        lines.append("🎯 **PREPARED BET** 🎯")
        lines.append("")
        lines.append(f"**Symbol:** {prepared_bet.get('symbol', 'N/A')}")
        lines.append(f"**Market:** {prepared_bet.get('market_name', 'N/A')}")
        lines.append(f"**Signal:** {prepared_bet.get('signal', 'N/A')}")
        lines.append(f"**Confidence:** {prepared_bet.get('confidence', 0)}%")
        lines.append(f"**Outcome:** {prepared_bet.get('outcome', 'N/A')}")
        lines.append(f"**Amount:** ${prepared_bet.get('amount', 0)}")
        lines.append("")
        lines.append("**To execute this bet, run:**")
        lines.append("```bash")
        lines.append(prepared_bet.get('curl_command', ''))
        lines.append("```")
        lines.append("")
        lines.append("*⚠️ Check market details before executing!*")

        return "\n".join(lines)
