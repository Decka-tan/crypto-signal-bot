"""
Unhedged Odds Scraper
Scrapes real-time odds dari Unhedged markets
Binary: YES% vs NO%
Interval: LOW% vs MID% vs HIGH%
"""

import re
import json
from typing import Dict, Optional, List
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class UnhedgedOdds:
    """Represents odds for an Unhedged market"""

    def __init__(self, market_id: str, market_type: str, odds_data: Dict):
        self.market_id = market_id
        self.market_type = market_type  # 'binary' or 'interval'
        self.raw_data = odds_data

        # Parse odds based on market type
        if market_type == 'binary':
            self.yes_pct = odds_data.get('yes_pct', 0)
            self.no_pct = odds_data.get('no_pct', 0)
            self.yes_volume = odds_data.get('yes_volume', 0)
            self.no_volume = odds_data.get('no_volume', 0)
            self.total_volume = self.yes_volume + self.no_volume
        else:  # interval
            self.low_pct = odds_data.get('low_pct', 0)
            self.mid_pct = odds_data.get('mid_pct', 0)
            self.high_pct = odds_data.get('high_pct', 0)
            self.low_volume = odds_data.get('low_volume', 0)
            self.mid_volume = odds_data.get('mid_volume', 0)
            self.high_volume = odds_data.get('high_volume', 0)
            self.total_volume = self.low_volume + self.mid_volume + self.high_volume

    def get_winning_outcome(self) -> str:
        """Get outcome with highest percentage"""
        if self.market_type == 'binary':
            return 'YES' if self.yes_pct > self.no_pct else 'NO'
        else:  # interval
            pcts = {'LOW': self.low_pct, 'MID': self.mid_pct, 'HIGH': self.high_pct}
            return max(pcts, key=pcts.get)

    def get_outcome_pct(self, outcome: str) -> float:
        """Get percentage for specific outcome"""
        if self.market_type == 'binary':
            return self.yes_pct if outcome == 'YES' else self.no_pct
        else:  # interval
            if outcome == 'LOW':
                return self.low_pct
            elif outcome == 'MID':
                return self.mid_pct
            elif outcome == 'HIGH':
                return self.high_pct
        return 0

    def is_crowd_aligned(self, signal: str) -> bool:
        """
        Check if crowd (majority) aligns with signal

        Args:
            signal: 'YES', 'NO', 'LOW', 'MID', 'HIGH'

        Returns:
            True if crowd majority aligns with signal (>50%)
        """
        if self.market_type == 'binary':
            if signal == 'YES':
                return self.yes_pct > 50
            else:  # NO
                return self.no_pct > 50
        else:  # interval
            if signal == 'LOW':
                return self.low_pct == max(self.low_pct, self.mid_pct, self.high_pct)
            elif signal == 'MID':
                return self.mid_pct == max(self.low_pct, self.mid_pct, self.high_pct)
            elif signal == 'HIGH':
                return self.high_pct == max(self.low_pct, self.mid_pct, self.high_pct)
        return False

    def is_contrarian_opportunity(self, signal: str, threshold: float = 30) -> bool:
        """
        Check if this is a contrarian opportunity (crowd against signal)

        Args:
            signal: 'YES', 'NO', 'LOW', 'MID', 'HIGH'
            threshold: Max crowd percentage for signal to be contrarian

        Returns:
            True if crowd against signal (< threshold% agree with signal)
        """
        signal_pct = self.get_outcome_pct(signal)
        return signal_pct < threshold

    def get_sentiment_strength(self) -> str:
        """
        Get sentiment strength (how confident is the crowd)

        Returns:
            'VERY_STRONG', 'STRONG', 'MODERATE', 'WEAK', 'DIVIDED'
        """
        if self.market_type == 'binary':
            max_pct = max(self.yes_pct, self.no_pct)
        else:  # interval
            max_pct = max(self.low_pct, self.mid_pct, self.high_pct)

        if max_pct >= 80:
            return 'VERY_STRONG'
        elif max_pct >= 65:
            return 'STRONG'
        elif max_pct >= 55:
            return 'MODERATE'
        elif max_pct >= 45:
            return 'WEAK'
        else:
            return 'DIVIDED'

    def __repr__(self) -> str:
        if self.market_type == 'binary':
            return f"BinaryOdds(YES: {self.yes_pct}%, NO: {self.no_pct}%, Vol: ${self.total_volume})"
        else:
            return f"IntervalOdds(LOW: {self.low_pct}%, MID: {self.mid_pct}%, HIGH: {self.high_pct}%, Vol: ${self.total_volume})"


class UnhedgedOddsScraper:
    """Scrape odds from Unhedged markets"""

    def __init__(self):
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome driver"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed")

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--log-level=3')

        self.driver = webdriver.Chrome(options=options)

    def scrape_market_odds(self, market_id: str, market_type: str) -> Optional[UnhedgedOdds]:
        """
        Scrape odds for a specific market

        Args:
            market_id: Unhedged market ID
            market_type: 'binary' or 'interval'

        Returns:
            UnhedgedOdds object or None
        """
        try:
            if self.driver is None:
                self._init_driver()

            # Navigate to market page
            url = f"https://unhedged.gg/markets/{market_id}"
            self.driver.get(url)

            # Wait for page load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait extra for JavaScript (Unhedged uses React)
            import time
            time.sleep(5)

            # Get page source
            html = self.driver.page_source

            # Debug: Check if we got any data
            if len(html) < 1000:
                print(f"   [WARN] Page source too short: {len(html)} chars")
                return None

            # Check for common Unhedged patterns
            if 'unhedged' not in html.lower():
                print(f"   [WARN] Page doesn't look like Unhedged")
                return None

            # Parse odds based on market type
            if market_type == 'binary':
                odds_data = self._parse_binary_odds(html)
            else:  # interval
                odds_data = self._parse_interval_odds(html)

            if odds_data:
                return UnhedgedOdds(market_id, market_type, odds_data)

            return None

        except Exception as e:
            print(f"   Error scraping odds: {str(e)[:50]}")
            return None

    def _parse_binary_odds(self, html: str) -> Optional[Dict]:
        """Parse binary market odds from HTML"""
        try:
            # Method 1: Look for percentage patterns in HTML
            # Pattern: "75%", "25%", etc.

            # Find all percentages
            pct_matches = re.findall(r'(\d+)%', html)

            if len(pct_matches) >= 2:
                yes_pct = float(pct_matches[0])
                no_pct = float(pct_matches[1])

                # Validate (should add to ~100%)
                if abs(yes_pct + no_pct - 100) < 5:
                    # Try to find volumes
                    volume_matches = re.findall(r'\$?(\d+\.?\d*)\s*(?:USD)?', html)

                    yes_volume = 0
                    no_volume = 0

                    if len(volume_matches) >= 2:
                        try:
                            yes_volume = float(volume_matches[0])
                            no_volume = float(volume_matches[1])
                        except:
                            pass

                    return {
                        'yes_pct': yes_pct,
                        'no_pct': no_pct,
                        'yes_volume': yes_volume,
                        'no_volume': no_volume
                    }

            # Method 2: Look for JSON data in script tags
            script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

            for script in script_tags:
                if 'odds' in script.lower() or 'yes' in script.lower():
                    # Try to find JSON
                    try:
                        # Look for percentage patterns
                        yes_match = re.search(r'yes["\s:]+(\d+)', script, re.IGNORECASE)
                        no_match = re.search(r'no["\s:]+(\d+)', script, re.IGNORECASE)

                        if yes_match and no_match:
                            yes_pct = float(yes_match.group(1))
                            no_pct = float(no_match.group(1))

                            if yes_pct + no_pct == 100 or yes_pct + no_pct == 1000:
                                # Normalize if needed
                                if yes_pct + no_pct == 1000:
                                    yes_pct /= 10
                                    no_pct /= 10

                                return {
                                    'yes_pct': yes_pct,
                                    'no_pct': no_pct,
                                    'yes_volume': 0,
                                    'no_volume': 0
                                }
                    except:
                        continue

            return None

        except Exception as e:
            print(f"   Error parsing binary odds: {str(e)[:50]}")
            return None

    def _parse_interval_odds(self, html: str) -> Optional[Dict]:
        """Parse interval market odds from HTML"""
        try:
            # Method 1: Look for 3 percentages
            pct_matches = re.findall(r'(\d+)%', html)

            if len(pct_matches) >= 3:
                low_pct = float(pct_matches[0])
                mid_pct = float(pct_matches[1])
                high_pct = float(pct_matches[2])

                # Validate
                if abs(low_pct + mid_pct + high_pct - 100) < 5:
                    return {
                        'low_pct': low_pct,
                        'mid_pct': mid_pct,
                        'high_pct': high_pct,
                        'low_volume': 0,
                        'mid_volume': 0,
                        'high_volume': 0
                    }

            # Method 2: Look for JSON/Script data
            script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

            for script in script_tags:
                if 'low' in script.lower() or 'high' in script.lower():
                    try:
                        low_match = re.search(r'low["\s:]+(\d+)', script, re.IGNORECASE)
                        mid_match = re.search(r'mid["\s:]+(\d+)', script, re.IGNORECASE)
                        high_match = re.search(r'high["\s:]+(\d+)', script, re.IGNORECASE)

                        if low_match and mid_match and high_match:
                            low_pct = float(low_match.group(1))
                            mid_pct = float(mid_match.group(1))
                            high_pct = float(high_match.group(1))

                            total = low_pct + mid_pct + high_pct

                            if total == 100 or total == 1000:
                                if total == 1000:
                                    low_pct /= 10
                                    mid_pct /= 10
                                    high_pct /= 10

                                return {
                                    'low_pct': low_pct,
                                    'mid_pct': mid_pct,
                                    'high_pct': high_pct,
                                    'low_volume': 0,
                                    'mid_volume': 0,
                                    'high_volume': 0
                                }
                    except:
                        continue

            return None

        except Exception as e:
            print(f"   Error parsing interval odds: {str(e)[:50]}")
            return None

    def scrape_multiple_markets(self, market_ids: List[tuple]) -> Dict[str, UnhedgedOdds]:
        """
        Scrape odds for multiple markets

        Args:
            market_ids: List of (market_id, market_type) tuples

        Returns:
            Dict mapping market_id to UnhedgedOdds
        """
        results = {}

        for market_id, market_type in market_ids:
            odds = self.scrape_market_odds(market_id, market_type)
            if odds:
                results[market_id] = odds

        return results

    def close(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_odds_scraper():
    """Test the odds scraper"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print("[bold cyan]Testing Unhedged Odds Scraper[/bold cyan]\n")

    # Sample market IDs from config
    test_markets = [
        ('cmltgz89a03dk0swj3febsk7m', 'binary'),  # BTC
        ('cmltgz8gt03do0swju58b72ab', 'binary'),  # ETH
    ]

    with UnhedgedOddsScraper() as scraper:
        for market_id, market_type in test_markets:
            console.print(f"[cyan]Scraping {market_id} ({market_type})...[/cyan]")

            odds = scraper.scrape_market_odds(market_id, market_type)

            if odds:
                console.print(f"  [green]OK[/green] {odds}")

                # Show sentiment
                console.print(f"  Winning: {odds.get_winning_outcome()}")
                console.print(f"  Strength: {odds.get_sentiment_strength()}")
            else:
                console.print(f"  [red]X[/red] Failed to scrape")

            console.print("")


if __name__ == "__main__":
    test_odds_scraper()
