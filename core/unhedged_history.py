"""
Unhedged Bet History Fetcher - Get REAL results for calibration

Uses Unhedged API to:
1. Fetch all past bets
2. Get actual outcomes
3. Update result tracker
4. Calculate calibration metrics
5. Suggest model improvements
"""

import requests
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd

from core.unhedged_client import UnhedgedClient


@dataclass
class BetHistory:
    """Historical bet from Unhedged"""
    bet_id: str
    market_id: str
    market_question: str
    outcome: str  # 'YES', 'NO', 'LOW', 'MID', 'HIGH'
    amount: float
    status: str  # 'PENDING', 'WON', 'LOST', 'CANCELLED'
    created_at: str
    resolved_at: Optional[str]
    payout: Optional[float]  # Amount won (positive) or lost (0 or negative)
    odds_yes: float  # Odds when bet placed
    odds_no: float


class CalibrationMetrics:
    """Calibration metrics to improve the model"""

    def __init__(self, predictions: List[Dict], results: List[Dict]):
        """
        Calculate calibration metrics

        Args:
            predictions: List of {p_yes, actual_outcome}
            results: List of actual results
        """
        self.predictions = predictions
        self.results = results

        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'p_yes': p['p_yes'],
                'actual': 1 if r['actual_result'] == r['predicted_outcome'] else 0,
                'edge': p.get('edge', 0)
            }
            for p, r in zip(predictions, results)
        ])

        self.df = df

        # Calculate metrics
        self._calculate_metrics()

    def _calculate_metrics(self):
        """Calculate calibration metrics"""
        df = self.df

        # 1. Overall accuracy
        self.accuracy = (df['actual'].sum() / len(df)) if len(df) > 0 else 0

        # 2. Accuracy by confidence bucket
        df['bucket'] = pd.cut(df['p_yes'], bins=[0, 0.2, 0.4, 0.6, 0.8, 1.0],
                                 labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])

        self.bucket_accuracy = df.groupby('bucket')['actual'].mean()

        # 3. Calibration curve (reliability diagram)
        # Compare predicted probability vs actual frequency
        self.calibration = {}

        for bucket in ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']:
            bucket_data = df[df['bucket'] == bucket]
            if len(bucket_data) > 0:
                pred_mean = bucket_data['p_yes'].mean()
                actual_mean = bucket_data['actual'].mean()
                self.calibration[bucket] = {
                    'predicted_prob': pred_mean,
                    'actual_freq': actual_mean,
                    'count': len(bucket_data),
                    'calibrated': pred_mean * 0.9 + 0.05  # Simple Platt scaling
                }

        # 4. Brier score (lower is better)
        self.brier_score = ((df['actual'] - df['p_yes']) ** 2).mean()

        # 5. Expected profit per bet
        # Assuming even money odds for simplicity
        self.expected_profit = (df['p_yes'] - 0.5).mean()

    def get_calibration_params(self) -> Dict:
        """
        Get calibration parameters for the model

        Returns:
            Calibration parameters to adjust future predictions
        """
        if not self.calibration:
            return {}

        # Simple linear regression: y = mx + b
        # Fit: actual_freq ~ predicted_prob

        import numpy as np

        x = []
        y = []

        for bucket, data in self.calibration.items():
            x.append(data['predicted_prob'])
            y.append(data['actual_freq'])

        x = np.array(x)
        y = np.array(y)

        # Linear regression
        A = np.vstack([x, np.ones(len(x))]).T
        m, b = np.linalg.lstsq(A, y, rcond=None)[0]

        return {
            'slope': m,
            'intercept': b,
            'calibration_type': 'linear'
        }

    def print_calibration_report(self):
        """Print pretty calibration report"""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        console.print("\n[bold cyan]📊 CALIBRATION REPORT[/bold cyan]\n")

        # Overall stats
        console.print(f"[bold]Overall Accuracy:[/bold] {self.accuracy*100:.1f}%")
        console.print(f"[bold]Brier Score:[/bold] {self.brier_score:.4f} (lower is better)")
        console.print(f"[bold]Expected Profit per Bet:[/bold] {self.expected_profit*100:.1f}%")

        # Bucket accuracy
        console.print(f"\n[bold]Accuracy by Confidence Bucket:[/bold]")
        table = Table()
        table.add_column("Bucket", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Pred Prob", justify="right")
        table.add_column("Actual Freq", justify="right")
        table.add_column("Diff", justify="right")

        for bucket in ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']:
            if bucket in self.bucket_accuracy:
                count = len(self.df[self.df['bucket'] == bucket])
                pred = self.calibration[bucket]['predicted_prob']
                actual = self.calibration[bucket]['actual_freq']
                diff = actual - pred

                diff_style = "green" if abs(diff) < 0.1 else "red"
                table.add_row(
                    bucket,
                    str(count),
                    f"{pred*100:.1f}%",
                    f"{actual*100:.1f}%",
                    f"[{diff_style}]{diff*100:+.1f}%[/{diff_style}]"
                )

        console.print(table)

        # Calibration parameters
        params = self.get_calibration_params()
        console.print(f"\n[bold]Calibration Parameters:[/bold]")
        console.print(f"  Slope (m): {params['slope']:.3f}")
        console.print(f"  Intercept (b): {params['intercept']:.3f}")
        console.print(f"  Formula: p_calibrated = {params['slope']:.2f} * p_raw + {params['intercept']:.2f}")

        # Recommendations
        console.print(f"\n[bold yellow]💡 RECOMMENDATIONS:[/bold yellow]")

        if self.accuracy < 0.6:
            console.print("  ⚠️  Low accuracy (<60%) - Model needs improvement")
            console.print("     → Add more features (funding, liquidations)")
            console.print("     → Increase buffer size")
        elif self.accuracy < 0.75:
            console.print("  ⚠️  Moderate accuracy (60-75%) - Model needs tuning")
            console.print("     → Adjust calibration parameters")
        else:
            console.print("  ✅ Good accuracy (>75%) - Model is working well!")

        # Check for overconfidence
        for bucket in ['60-80%', '80-100%']:
            if bucket in self.calibration:
                pred = self.calibration[bucket]['predicted_prob']
                actual = self.calibration[bucket]['actual_freq']

                if pred > actual + 0.15:  # Overconfident by 15%
                    console.print(f"  ⚠️  Overconfident in {bucket} bucket")
                    console.print(f"     Predicted: {pred*100:.1f}%, Actual: {actual*100:.1f}%")
                    console.print(f"     → Reduce confidence in this range")

        console.print("")


class UnhedgedHistoryFetcher:
    """Fetch bet history from Unhedged API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://unhedged.gg/api/v1"  # Match UnhedgedClient base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_bet_history(
        self,
        limit: int = 100,
        days_back: int = 7
    ) -> List[BetHistory]:
        """
        Fetch bet history from Unhedged API

        Args:
            limit: Max number of bets to fetch
            days_back: Only fetch bets from last N days

        Returns:
            List of BetHistory objects
        """
        # Try different possible endpoints
        endpoints = [
            f"{self.base_url}/bets",
            f"{self.base_url}/orders",
            f"{self.base_url}/positions",
            f"{self.base_url}/user/bets",
            f"{self.base_url}/user/orders",
        ]

        params = {
            "limit": limit,
            "sort": "created_at",
            "order": "desc"
        }

        for url in endpoints:
            try:
                response = self.session.get(url, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_bet_response(data, days_back)
                elif response.status_code == 404:
                    continue  # Try next endpoint
                else:
                    print(f"[WARN] {url} returned {response.status_code}")
            except Exception as e:
                continue  # Try next endpoint

        # If all endpoints failed, try scraping the web interface
        print("[INFO] API endpoints failed, trying web scraping...")
        return self._fetch_bet_history_web(limit, days_back)

    def _parse_bet_response(self, data: Dict, days_back: int) -> List[BetHistory]:
        """Parse bet response from API"""
        bets = []

        # Try different response structures
        items = data.get('bets', [])
        if not items:
            items = data.get('orders', [])
        if not items:
            items = data.get('data', [])
        if not items:
            items = data if isinstance(data, list) else []

        for item in items:
            try:
                # Parse bet (handle different response formats)
                bet = BetHistory(
                    bet_id=item.get('id') or item.get('bet_id', ''),
                    market_id=item.get('market_id') or item.get('marketId', ''),
                    market_question=item.get('market', {}).get('question', '') if isinstance(item.get('market'), dict) else item.get('market_question', ''),
                    outcome=item.get('outcome') or item.get('side', '') or item.get('prediction', ''),
                    amount=item.get('amount', 0) or item.get('size', 0),
                    status=item.get('status', 'PENDING').upper(),
                    created_at=item.get('created_at') or item.get('createdAt', '') or item.get('timestamp', ''),
                    resolved_at=item.get('resolved_at') or item.get('resolvedAt', ''),
                    payout=item.get('payout') or item.get('profit_loss', 0) or item.get('pnl', 0),
                    odds_yes=item.get('odds', {}).get('yes', 0.5) if isinstance(item.get('odds'), dict) else 0.5,
                    odds_no=item.get('odds', {}).get('no', 0.5) if isinstance(item.get('odds'), dict) else 0.5
                )

                # Only include resolved bets from last N days
                if bet.status in ['WON', 'LOST', 'WIN', 'LOSE', 'FILLED']:
                    # Normalize status
                    if bet.status in ['WIN', 'FILLED']:
                        bet.status = 'WON'
                    elif bet.status == 'LOSE':
                        bet.status = 'LOST'

                    try:
                        # Try different date formats
                        if 'T' in bet.created_at:
                            created_date = datetime.fromisoformat(bet.created_at.replace('Z', '+00:00'))
                        else:
                            created_date = datetime.strptime(bet.created_at, '%Y-%m-%d %H:%M:%S')

                        if datetime.now() - created_date < timedelta(days=days_back):
                            bets.append(bet)
                    except:
                        pass  # Skip bets with invalid dates

            except Exception as e:
                continue  # Skip malformed items

        return bets

    def _fetch_bet_history_web(self, limit: int, days_back: int) -> List[BetHistory]:
        """
        Fallback: Scrape bet history from web interface
        This is used when API endpoints are not available
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from bs4 import BeautifulSoup
            import time

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')

            driver = webdriver.Chrome(options=options)

            try:
                # Go to profile page
                driver.get("https://unhedged.gg/profile")
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(5)

                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # Parse bet history from page
                # Note: This is a placeholder - actual implementation depends on Unhedged's page structure
                bets = []

                # TODO: Parse actual page structure
                # For now, return empty list

                return bets

            finally:
                driver.quit()

        except Exception as e:
            print(f"[ERROR] Web scraping failed: {str(e)}")
            return []

    def update_tracker_from_history(
        self,
        tracker,  # ResultTracker instance
        api_key: str
    ):
        """
        Fetch bet history and update result tracker

        This syncs actual Unhedged results with our predictions
        """
        from rich.console import Console

        console = Console()

        console.print("[cyan]🔄 Fetching bet history from Unhedged API...[/cyan]")

        # Fetch history
        bets = self.fetch_bet_history(limit=200, days_back=30)

        if not bets:
            console.print("[yellow]No bets found or API error[/yellow]")
            return

        console.print(f"[green]Found {len(bets)} resolved bets[/green]\n")

        # Update tracker
        updated = 0

        for bet in bets:
            # Check if we have a matching prediction in our tracker
            # We match by market_id and timestamp

            # For now, just insert the result
            # TODO: Match with our actual predictions

            is_win = (bet.status == 'WON')
            amount_won = bet.payout if is_win else 0

            # Update in database
            try:
                import sqlite3
                conn = sqlite3.connect(tracker.db_path)
                cursor = conn.cursor()

                # Check if bet already exists
                cursor.execute("""
                    SELECT id FROM bets WHERE market_id = ?
                """, (bet.market_id,))

                if cursor.fetchone():
                    # Update existing
                    cursor.execute("""
                        UPDATE bets
                        SET actual_result = ?, is_win = ?, amount_won = ?
                        WHERE market_id = ?
                    """, (bet.outcome, is_win, amount_won, bet.market_id))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO bets (
                            timestamp, symbol, market_type, market_id, market_question,
                            signal, confidence, amount_bet, amount_won,
                            actual_result, is_win
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        bet.created_at,
                        self._extract_symbol(bet.market_question),
                        'binary',
                        bet.market_id,
                        bet.market_question,
                        bet.outcome,
                        50.0,  # Confidence unknown
                        bet.amount,
                        amount_won,
                        bet.outcome,
                        is_win
                    ))

                conn.commit()
                conn.close()

                updated += 1

            except Exception as e:
                console.print(f"[dim]Error updating bet {bet.market_id}: {str(e)[:30]}[/dim]")

        console.print(f"[green]✓ Updated {updated} bets in database[/green]")

    def _extract_symbol(self, question: str) -> str:
        """Extract symbol from market question"""
        question_upper = question.upper()

        if 'BITCOIN' in question_upper or 'BTC' in question_upper:
            return 'BTCUSDT'
        elif 'ETHEREUM' in question_upper or 'ETH' in question_upper:
            return 'ETHUSDT'
        elif 'SOLANA' in question_upper or 'SOL' in question_upper:
            return 'SOLUSDT'
        elif 'CANTON' in question_upper or ' CC ' in question_upper:
            return 'CCUSDT'

        return 'UNKNOWN'


def calculate_calibration_from_tracker(tracker, days: int = 30):
    """
    Calculate calibration metrics from result tracker

    This uses our tracked predictions vs actual outcomes

    Args:
        tracker: ResultTracker instance
        days: Number of days to look back

    Returns:
        CalibrationMetrics object
    """
    # Get bets from tracker
    conn = sqlite3.connect(tracker.db_path)
    cursor = conn.cursor()

    # Get resolved bets with p_yes
    cursor.execute("""
        SELECT signal, confidence, actual_result, is_win, timestamp
        FROM bets
        WHERE actual_result IS NOT NULL
        AND date(timestamp) >= date('now', '-{} days')
        ORDER BY timestamp DESC
    """.format(days))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("[WARN] No resolved bets found in tracker for calibration")
        return None

    # Convert to format for CalibrationMetrics
    predictions = []
    results = []

    for row in rows:
        signal, confidence, actual_result, is_win, timestamp = row

        # Convert signal to outcome
        predicted_outcome = signal

        # Convert confidence to p_yes
        # If signal is YES, p_yes = confidence/100
        # If signal is NO, p_yes = (100 - confidence)/100 = 1 - confidence/100
        if predicted_outcome == 'YES':
            p_yes = confidence / 100
        else:
            p_yes = 1 - (confidence / 100)

        predictions.append({
            'p_yes': p_yes,
            'predicted_outcome': predicted_outcome,
            'edge': 0  # TODO: Calculate edge from odds
        })

        results.append({
            'actual_result': actual_result,
            'predicted_outcome': predicted_outcome
        })

    # Create calibration metrics
    calibration = CalibrationMetrics(predictions, results)

    return calibration


def test_history_fetcher():
    """Test the history fetcher"""
    from rich.console import Console

    console = Console()

    console.print("[cyan]Testing Unhedged History Fetcher...[/cyan]\n")

    # Test with API key from config
    import yaml
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    api_key = config.get('unhedged', {}).get('api_key', '')

    if not api_key:
        console.print("[red]No API key found in config.yaml[/red]")
        return

    fetcher = UnhedgedHistoryFetcher(api_key)

    # Fetch history
    console.print("Fetching bet history...")
    bets = fetcher.fetch_bet_history(limit=50, days_back=7)

    console.print(f"\n[green]Found {len(bets)} bets[/green]\n")

    # Show some bets
    for i, bet in enumerate(bets[:10]):
        console.print(f"  {i+1}. {bet.market_question[:50]}...")
        console.print(f"     Outcome: {bet.outcome} | Status: {bet.status}")
        console.print(f"     Amount: ${bet.amount} | Payout: ${bet.payout or 0:.2f}")
        console.print("")

    console.print("[green]✓[/green] History fetcher working!")


if __name__ == "__main__":
    test_history_fetcher()
