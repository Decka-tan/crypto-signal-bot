"""
Unhedged Auto-Bet Module
Handles automated betting with proper risk controls

Risk Management:
- Max bet per market
- Max bet per hour
- Max loss per day
- DRY_RUN mode for testing
- Position sizing based on edge
"""

import os
import time
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import sqlite3
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

@dataclass
class BetConfig:
    """Risk management configuration"""
    max_bet_per_market: float = 10.0  # Max USDT per single bet
    max_bet_per_hour: float = 50.0  # Max total bets per hour
    max_loss_per_day: float = 100.0  # Max loss per day before stop
    min_bet_amount: float = 1.0  # Minimum bet size
    default_bet_amount: float = 5.0  # Default bet when edge is low
    high_confidence_bet: float = 10.0  # Bet when confidence > 80%
    min_edge_to_bet: float = 0.02  # Minimum 2% edge to bet
    min_liquidity: float = 1000.0  # Min liquidity in market

@dataclass
class BetResult:
    """Result of a bet placement"""
    success: bool
    bet_id: Optional[str] = None
    error: Optional[str] = None
    amount: float = 0
    outcome: str = ""
    market_id: str = ""


class UnhedgedAutoBetter:
    """
    Automated betting system for Unhedged

    Features:
    - Bearer token authentication
    - Risk controls (max bet, max loss, etc)
    - DRY_RUN mode for testing
    - Position sizing based on edge/confidence
    - Local database for tracking
    """

    def __init__(self, config: BetConfig, dry_run: bool = True):
        """
        Initialize auto-better

        Args:
            config: Risk management configuration
            dry_run: If True, simulates bets without placing them
        """
        self.config = config
        self.dry_run = dry_run

        # Load API key from environment
        self.api_key = os.getenv('UNHEDGED_API_KEY')
        if not self.api_key:
            raise ValueError("UNHEDGED_API_KEY not found in environment")

        # Found from DevTools: https://api.unhedged.gg/api/v1
        self.base_url = "https://api.unhedged.gg/api/v1"

        # Setup session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })

        # Tracking
        self.bets_today = []
        self.total_bet_today = 0.0
        self.total_loss_today = 0.0

        # Database for tracking
        self.db_path = "auto_bets.db"
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for bet tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                market_id TEXT,
                symbol TEXT,
                signal TEXT,
                outcome TEXT,
                amount REAL,
                bet_id TEXT,
                dry_run INTEGER,
                status TEXT,
                error TEXT,
                confidence REAL,
                edge REAL
            )
        """)

        conn.commit()
        conn.close()

    def _log_bet(self, market_id: str, symbol: str, signal: str, outcome: str,
                 amount: float, bet_id: Optional[str], confidence: float, edge: float):
        """Log bet to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO auto_bets
            (market_id, symbol, signal, outcome, amount, bet_id, dry_run, status, confidence, edge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            market_id, symbol, signal, outcome, amount,
            bet_id, 1 if self.dry_run else 0,
            'success' if bet_id else 'dry_run',
            confidence, edge
        ))

        conn.commit()
        conn.close()

    def check_balance(self) -> Optional[Dict]:
        """
        Check account balance

        Returns:
            Balance dict or None if failed
        """
        endpoint = f"{self.base_url}/balance"

        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   [WARN] Failed to fetch balance: {str(e)[:50]}")
            return None

    def get_markets(self, status: str = "ACTIVE", limit: int = 50) -> Optional[List[Dict]]:
        """
        Get list of active markets

        Args:
            status: Market status filter (ACTIVE, CLOSED, etc)
            limit: Number of markets to fetch

        Returns:
            List of markets or None if failed
        """
        endpoint = f"{self.base_url}/markets"

        try:
            params = {
                'status': status,
                'limit': limit,
                'orderBy': 'endTime',
                'orderDirection': 'asc'
            }
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   [WARN] Failed to fetch markets: {str(e)[:50]}")
            return None

    def get_market_odds(self, market_id: str) -> Optional[Dict]:
        """
        Get odds for a specific market

        Args:
            market_id: Market ID

        Returns:
            Odds dict or None if failed
        """
        endpoint = f"{self.base_url}/markets/{market_id}/odds"

        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   [WARN] Failed to fetch odds: {str(e)[:50]}")
            return None

    def place_bet(self, market_id: str, outcome: str, amount: float,
                  signal: str, symbol: str, confidence: float, edge: float) -> BetResult:
        """
        Place a bet with risk controls

        Args:
            market_id: Market ID to bet on
            outcome: "YES" or "NO"
            amount: Amount to bet in USDT
            signal: Signal type (for logging)
            symbol: Symbol (for logging)
            confidence: Confidence percentage
            edge: Edge percentage

        Returns:
            BetResult with success status
        """
        # Check risk limits
        limit_check = self._check_risk_limits(amount)
        if not limit_check['allowed']:
            return BetResult(
                success=False,
                error=limit_check['reason']
            )

        # Check amount constraints
        if amount < self.config.min_bet_amount:
            return BetResult(
                success=False,
                error=f"Amount ${amount:.2f} below minimum ${self.config.min_bet_amount}"
            )

        if amount > self.config.max_bet_per_market:
            amount = self.config.max_bet_per_market

        # DRY RUN - Simulate bet
        if self.dry_run:
            print(f"   [DRY RUN] Would bet: ${amount:.2f} on {symbol} {outcome}")
            self._log_bet(market_id, symbol, signal, outcome, amount, None, confidence, edge)
            return BetResult(
                success=True,
                bet_id=f"dry_{int(time.time())}",
                amount=amount,
                outcome=outcome,
                market_id=market_id
            )

        # REAL BET - Place actual bet
        # Format from DevTools: POST /bets?marketId=<market_id>
        endpoint = f"{self.base_url}/bets?marketId={market_id}"

        payload = {
            'outcome': outcome,
            'amount': str(amount)  # API might expect string
        }

        try:
            response = self.session.post(endpoint, json=payload, timeout=15)
            response.raise_for_status()

            result = response.json()
            bet_id = result.get('bet_id') or result.get('id')

            print(f"   [SUCCESS] Bet placed: ${amount:.2f} on {symbol} {outcome}")
            print(f"              Bet ID: {bet_id}")

            # Track
            self.bets_today.append({
                'time': datetime.now(),
                'amount': amount,
                'market_id': market_id,
                'bet_id': bet_id
            })
            self.total_bet_today += amount

            # Log to database
            self._log_bet(market_id, symbol, signal, outcome, amount, bet_id, confidence, edge)

            return BetResult(
                success=True,
                bet_id=bet_id,
                amount=amount,
                outcome=outcome,
                market_id=market_id
            )

        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            if e.response.status_code == 401:
                error_msg = "Unauthorized: Check API key"
            elif e.response.status_code == 403:
                error_msg = "Forbidden: Insufficient permissions"
            elif e.response.status_code == 429:
                error_msg = "Rate limit exceeded"
            elif e.response.status_code == 400:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('message', error_msg)
                except:
                    pass

            print(f"   [ERROR] Bet failed: {error_msg}")
            return BetResult(
                success=False,
                error=error_msg
            )

        except Exception as e:
            print(f"   [ERROR] Bet failed: {str(e)[:50]}")
            return BetResult(
                success=False,
                error=str(e)[:50]
            )

    def _check_risk_limits(self, amount: float) -> Dict:
        """
        Check if bet is within risk limits

        Returns:
            Dict with 'allowed' (bool) and 'reason' (str)
        """
        # Check max per market
        if amount > self.config.max_bet_per_market:
            return {
                'allowed': False,
                'reason': f'Amount ${amount:.2f} exceeds max ${self.config.max_bet_per_market}'
            }

        # Check hourly limit (reset each hour)
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        recent_bets = [b for b in self.bets_today if b['time'] > one_hour_ago]
        hourly_total = sum(b['amount'] for b in recent_bets)

        if hourly_total + amount > self.config.max_bet_per_hour:
            return {
                'allowed': False,
                'reason': f'Hourly limit ${hourly_total:.2f} + ${amount:.2f} exceeds ${self.config.max_bet_per_hour}'
            }

        # Check daily loss limit
        if self.total_loss_today >= self.config.max_loss_per_day:
            return {
                'allowed': False,
                'reason': f'Daily loss limit reached: ${self.total_loss_today:.2f}'
            }

        return {'allowed': True}

    def calculate_position_size(self, signal_analysis: Dict) -> float:
        """
        Calculate bet amount based on signal strength

        Uses Kelly Criterion simplified:
        - Higher edge = larger bet
        - Higher confidence = larger bet
        - Capped at max_bet_per_market

        Args:
            signal_analysis: Signal analysis dict

        Returns:
            Bet amount in USDT
        """
        edge = signal_analysis.get('edge', 0)
        confidence = signal_analysis.get('confidence', 0)

        # Base amount
        if confidence >= 80:
            base = self.config.high_confidence_bet
        elif confidence >= 60:
            base = self.config.default_bet_amount
        else:
            base = self.config.min_bet_amount

        # Scale by edge (0.02 to 0.10 = 1x to 2x multiplier)
        edge_multiplier = 1.0 + max(0, min((edge - 0.02) * 10, 1.0))

        amount = base * edge_multiplier

        # Cap at max
        return min(amount, self.config.max_bet_per_market)

    def should_bet(self, signal_analysis: Dict) -> bool:
        """
        Determine if we should bet based on signal

        Args:
            signal_analysis: Signal analysis dict

        Returns:
            True if we should place a bet
        """
        # Must be bettable
        if not signal_analysis.get('is_bettable', False):
            return False

        # Check edge
        edge = signal_analysis.get('edge', 0)
        if edge < self.config.min_edge_to_bet:
            return False

        # Check confidence
        confidence = signal_analysis.get('confidence', 0)
        if confidence < 60:
            return False

        return True


def test_auto_better():
    """Test the auto-better in DRY_RUN mode"""
    print("=== Testing Unhedged Auto-Better (DRY_RUN mode) ===\n")

    config = BetConfig(
        max_bet_per_market=10.0,
        max_bet_per_hour=50.0,
        max_loss_per_day=100.0,
        min_edge_to_bet=0.02
    )

    better = UnhedgedAutoBetter(config, dry_run=True)

    # Simulate a signal
    signal = {
        'symbol': 'BTCUSDT',
        'signal': 'YES',
        'confidence': 85,
        'edge': 0.05,
        'is_bettable': True,
        'market_id': 'test_market_123'
    }

    # Check if should bet
    if better.should_bet(signal):
        amount = better.calculate_position_size(signal)
        print(f"Signal accepted! Position size: ${amount:.2f}\n")

        # Place bet (will be DRY_RUN)
        result = better.place_bet(
            market_id=signal['market_id'],
            outcome=signal['signal'],
            amount=amount,
            signal=signal['signal'],
            symbol=signal['symbol'],
            confidence=signal['confidence'],
            edge=signal['edge']
        )

        if result.success:
            print(f"[OK] Bet simulated successfully")
            print(f"  Bet ID: {result.bet_id}")
            print(f"  Amount: ${result.amount}")
        else:
            print(f"[ERROR] Bet failed: {result.error}")
    else:
        print("Signal rejected by risk rules")


if __name__ == "__main__":
    test_auto_better()
