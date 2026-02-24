"""
Unhedged API Client - Fetches markets directly from API
Replaces the Selenium scraper!

Benefits:
- No Chrome driver needed
- Faster
- More reliable
- Returns complete market data
"""

import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)


class UnhedgedAPIMarket:
    """Market data from API"""

    def __init__(self, data: Dict):
        self.data = data
        self.id = data.get('id')
        self.question = data.get('question')
        self.description = data.get('description')
        self.category = data.get('category')
        self.status = data.get('status')
        self.end_time = data.get('endTime')
        self.resolution_time = data.get('scheduledResolutionTime')
        self.minimum_bet = float(data.get('minimumBet', 0))
        self.maximum_bet = data.get('maximumBet')
        self.total_pool = float(data.get('totalPool', 0))
        self.outcomes = data.get('outcomes', [])
        self.tags = data.get('tags', [])
        self.bet_count = data.get('betCount', 0)
        self.outcome_stats = data.get('outcomeStats', [])

        # Determine market type
        self.market_type = self._determine_market_type()

        # Extract symbol from question/tags
        self.symbol = self._extract_symbol()

        # Build market URL
        self.url = f"https://unhedged.gg/markets/{self.id}"

    def _determine_market_type(self) -> str:
        """Determine if binary or interval market"""
        if not self.outcomes:
            return 'unknown'

        # Binary markets have YES/NO
        outcome_labels = [o.get('label', '').upper() for o in self.outcomes]
        if 'YES' in outcome_labels and 'NO' in outcome_labels:
            return 'binary'

        # Interval markets have price ranges
        # Look for $ signs in outcomes
        has_prices = any('$' in o.get('label', '') for o in self.outcomes)
        if has_prices:
            return 'interval'

        return 'unknown'

    def _extract_symbol(self) -> str:
        """Extract trading symbol from question/tags"""
        # Check tags first
        for tag in self.tags:
            tag_upper = tag.upper()
            if tag_upper in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'MATIC', 'DOT', 'AVAX']:
                return f"{tag_upper}USDT"

        # Check question for common coins
        question_upper = self.question.upper()

        coin_map = {
            'BITCOIN': 'BTCUSDT',
            'ETHEREUM': 'ETHUSDT',
            'SOLANA': 'SOLUSDT',
            'CANTON': 'CCUSDT',
            'BINANCE': 'BNBUSDT',
            'RIPPLE': 'XRPUSDT',
            'CARDANO': 'ADAUSDT',
            'DOGECOIN': 'DOGEUSDT',
            'POLYGON': 'MATICUSDT',
            'POLKADOT': 'DOTUSDT',
            'AVALANCHE': 'AVAXUSDT',
        }

        for coin, symbol in coin_map.items():
            if coin in question_upper:
                return symbol

        return 'UNKNOWN'

    def is_still_active(self) -> bool:
        """Check if market is still accepting bets"""
        if self.status != 'ACTIVE':
            return False

        # Check end time
        if self.end_time:
            try:
                end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
                if datetime.now(end_dt.tzinfo) > end_dt:
                    return False
            except:
                pass

        return True

    def get_time_until_resolved_minutes(self) -> Optional[int]:
        """Get minutes until market resolves"""
        if not self.resolution_time:
            return None

        try:
            resolve_dt = datetime.fromisoformat(self.resolution_time.replace('Z', '+00:00'))
            now = datetime.now(resolve_dt.tzinfo)
            delta = resolve_dt - now
            return int(delta.total_seconds() / 60)
        except:
            return None

    def __repr__(self):
        return f"UnhedgedAPIMarket(id={self.id}, symbol={self.symbol}, question={self.question[:40]}...)"


class UnhedgedAPIClient:
    """
    Direct API client for Unhedged
    No scraping needed!
    """

    def __init__(self):
        self.api_key = os.getenv('UNHEDGED_API_KEY')
        if not self.api_key:
            raise ValueError("UNHEDGED_API_KEY not found in environment")

        self.base_url = "https://api.unhedged.gg/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

    def get_markets(
        self,
        status: str = "ACTIVE",
        limit: int = 100,
        category: Optional[str] = None
    ) -> List[UnhedgedAPIMarket]:
        """
        Get list of markets

        Args:
            status: Filter by status (ACTIVE, ENDED, RESOLVED)
            limit: Max number of markets to fetch
            category: Filter by category (e.g., 'crypto')

        Returns:
            List of UnhedgedAPIMarket objects
        """
        params = {
            'status': status,
            'limit': limit,
            'orderBy': 'endTime',
            'orderDirection': 'asc'
        }

        if category:
            params['category'] = category

        try:
            response = self.session.get(f"{self.base_url}/markets", params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            markets_data = data.get('markets', [])

            return [UnhedgedAPIMarket(m) for m in markets_data]

        except Exception as e:
            print(f"   [ERROR] Failed to fetch markets: {str(e)[:50]}")
            return []

    def get_market_by_id(self, market_id: str) -> Optional[UnhedgedAPIMarket]:
        """
        Get specific market by ID

        Args:
            market_id: Market ID

        Returns:
            UnhedgedAPIMarket object or None
        """
        try:
            response = self.session.get(f"{self.base_url}/markets/{market_id}", timeout=10)
            response.raise_for_status()

            data = response.json()
            return UnhedgedAPIMarket(data)

        except Exception as e:
            print(f"   [ERROR] Failed to fetch market {market_id}: {str(e)[:50]}")
            return None

    def find_crypto_markets(
        self,
        symbols: List[str] = None
    ) -> Dict[str, List[UnhedgedAPIMarket]]:
        """
        Find all active crypto markets, optionally filtered by symbols

        Args:
            symbols: List of symbols to filter (e.g., ['BTCUSDT', 'ETHUSDT'])
                    If None, returns all crypto markets

        Returns:
            Dict mapping symbol to list of markets
        """
        markets = self.get_markets(status="ACTIVE", limit=200, category="crypto")

        # Filter by symbol if provided
        if symbols:
            filtered = {}
            for market in markets:
                if market.symbol in symbols:
                    if market.symbol not in filtered:
                        filtered[market.symbol] = []
                    filtered[market.symbol].append(market)
            return filtered

        # Group by symbol
        grouped = {}
        for market in markets:
            if market.symbol not in grouped:
                grouped[market.symbol] = []
            grouped[market.symbol].append(market)

        return grouped

    def get_balance(self) -> Optional[Dict]:
        """Get account balance"""
        try:
            response = self.session.get(f"{self.base_url}/balance", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   [ERROR] Failed to fetch balance: {str(e)[:50]}")
            return None


# Test the client
if __name__ == "__main__":
    print("Testing Unhedged API Client")
    print("=" * 60)

    client = UnhedgedAPIClient()

    # Test balance
    print("\n[1] Checking balance...")
    balance = client.get_balance()
    if balance:
        bal_data = balance.get('balance', {})
        print(f"  Available: ${bal_data.get('available', '0')}")
        print(f"  Total: ${bal_data.get('total', '0')}")

    # Test markets
    print("\n[2] Fetching crypto markets...")
    markets = client.get_markets(status="ACTIVE", limit=50, category="crypto")
    print(f"  Found {len(markets)} active crypto markets")

    # Show sample
    if markets:
        print("\n[3] Sample markets:")
        for m in markets[:5]:
            print(f"  {m.symbol}: {m.question[:50]}...")
            print(f"    Type: {m.market_type}, Status: {m.status}")
            print(f"    Min bet: ${m.minimum_bet}, Pool: ${m.total_pool}")

    # Group by symbol
    print("\n[4] Grouping by symbol...")
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']
    grouped = client.find_crypto_markets(symbols)

    for symbol in symbols:
        if symbol in grouped:
            print(f"  {symbol}: {len(grouped[symbol])} market(s)")
