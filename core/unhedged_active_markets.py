"""
Unhedged Active Markets Scraper
Scrapes CURRENTLY ACTIVE markets from Unhedged
Gets market IDs, links, and status
"""

import re
import json
from typing import Dict, List, Optional
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class UnhedgedActiveMarket:
    """Represents an active Unhedged market"""

    def __init__(self, data: Dict):
        self.market_id = data.get('id', '')
        self.question = data.get('question', '')
        self.name = data.get('name', '')
        self.slug = data.get('slug', '')
        self.status = data.get('status', 'ACTIVE')
        self.close_time = data.get('closeTime', '')
        self.resolve_time = data.get('resolveTime', '')
        self.category = data.get('category', 'crypto')
        self.outcomes = data.get('outcomes', [])
        self.symbol = self._extract_symbol()
        self.market_type = self._detect_market_type()
        self.url = f"https://unhedged.gg/markets/{self.slug}" if self.slug else ''

        # For interval markets: extract price ranges
        self.low_threshold = None
        self.mid_threshold_low = None
        self.mid_threshold_high = None
        self.high_threshold = None

        if self.market_type == 'interval':
            self._extract_price_ranges()

    def _extract_symbol(self) -> str:
        """Extract crypto symbol from question"""
        question_upper = self.question.upper()

        symbols = {
            'BITCOIN': 'BTCUSDT',
            'BTC': 'BTCUSDT',
            'ETHEREUM': 'ETHUSDT',
            'ETH': 'ETHUSDT',
            'SOLANA': 'SOLUSDT',
            'SOL': 'SOLUSDT',
            'CANTON': 'CCUSDT',
            'CC': 'CCUSDT',
        }

        for key, value in symbols.items():
            if key in question_upper:
                return value

        return 'UNKNOWN'

    def extract_target_time_from_question(self) -> Optional[datetime]:
        """
        Extract target resolve time from question

        Returns:
            datetime object of when market resolves, or None
        """
        from datetime import datetime, timedelta

        question = self.question.upper()

        # Parse "X min left" or "Xh left" from question
        time_left_match = re.search(r'(\d+)\s*m\s*left', question, re.IGNORECASE)
        if time_left_match:
            try:
                time_left_min = int(time_left_match.group(1))
                now = datetime.now()
                resolve_dt = now + timedelta(minutes=time_left_min)
                return resolve_dt
            except:
                pass

        # Parse "at XX:XX" or "at X:XX AM/PM"
        time_patterns = [
            r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM)',
            r'at\s+(\d{1,2}):(\d{2})',
        ]

        for pattern in time_patterns:
            match = re.search(pattern, self.question, re.IGNORECASE)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    ampm = match.group(3) if len(match.groups()) > 2 else None

                    # Convert to 24-hour
                    if ampm:
                        if ampm.upper() == 'PM' and hour != 12:
                            hour += 12
                        elif ampm.upper() == 'AM' and hour == 12:
                            hour = 0

                    now = datetime.now()
                    target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # If target is in the past, it's tomorrow
                    if target_dt < now:
                        target_dt += timedelta(days=1)

                    return target_dt

                except:
                    pass

        return None

    def get_time_until_resolved_minutes(self) -> Optional[int]:
        """
        Get minutes until market resolves

        Returns:
            Minutes remaining, or None
        """
        resolve_time = self.extract_target_time_from_question()

        if resolve_time:
            from datetime import datetime
            now = datetime.now()
            delta = resolve_time - now
            minutes_left = int(delta.total_seconds() / 60)
            return max(0, minutes_left)

        return None

    def is_still_active(self) -> bool:
        """
        Check if market is still active (not resolved)

        Returns:
            True if market is still active, False if resolved
        """
        minutes_left = self.get_time_until_resolved_minutes()

        if minutes_left is not None:
            return minutes_left > 0

        # Fallback to status field
        return self.status.upper() == 'ACTIVE'

    def extract_target_time(self) -> Optional[datetime]:
        """
        Extract target resolve time from question

        Returns:
            datetime object of when market resolves, or None
        """
        import time
        from datetime import datetime, timedelta

        question = self.question.upper()

        # Pattern: "at 12:00", "at 1:00 PM", "at 10:00 AM"
        # Try different formats
        patterns = [
            r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM)',  # "at 9:00 AM"
            r'at\s+(\d{1,2}):(\d{2})',  # "at 9:00"
            r'at\s+(\d{1,2})\s*:\s*(\d{2})',  # "at 9 : 00"
        ]

        for pattern in patterns:
            match = re.search(pattern, self.question, re.IGNORECASE)
            if match:
                try:
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    ampm = match.group(3) if len(match.groups()) > 2 else None

                    # Convert to 24-hour format
                    if ampm:
                        if ampm.upper() == 'PM' and hour != 12:
                            hour += 12
                        elif ampm.upper() == 'AM' and hour == 12:
                            hour = 0

                    # Get today's date with the target time
                    now = datetime.now()
                    target_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

                    # If target time is in the past, it's for tomorrow
                    if target_dt < now:
                        target_dt += timedelta(days=1)

                    # Parse "X min left" or "Xh left" from question
                    time_left_match = re.search(r'(\d+)\s*m\s*left', self.question, re.IGNORECASE)
                    if time_left_match:
                        time_left_min = int(time_left_match.group(1))
                        resolve_dt = now + timedelta(minutes=time_left_min)
                        return resolve_dt

                    return target_dt

                except Exception as e:
                    pass

        return None

    def get_time_remaining_minutes(self) -> Optional[int]:
        """
        Get minutes until market resolves

        Returns:
            Minutes remaining, or None
        """
        resolve_time = self.extract_target_time()

        if resolve_time:
            from datetime import datetime
            now = datetime.now()
            delta = resolve_time - now
            minutes_left = int(delta.total_seconds() / 60)
            return max(0, minutes_left)

        return None

    def _detect_market_type(self) -> str:
        """Detect if binary or interval market"""
        # Method 1: Check outcomes (if available from API)
        if len(self.outcomes) == 3:
            return 'interval'

        import re
        question = self.question

        # Method 2: Check for BINARY market patterns FIRST (before checking ranges)
        # Binary: "above $X", "below $X", "higher than $X", "lower than $X"
        binary_patterns = [
            r'above\s+\$[\d,]+\.?\d*',  # "above $67,000"
            r'below\s+\$[\d,]+\.?\d*',  # "below $67,000"
            r'higher than\s+\$[\d,]+\.?\d*',  # "higher than $67,000"
            r'lower than\s+\$[\d,]+\.?\d*',  # "lower than $67,000"
        ]

        for pattern in binary_patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return 'binary'

        # Method 3: Check for INTERVAL market patterns
        # Interval: "price at HH:MM" WITHOUT a target price/above/below
        if re.search(r'price at\s+\d{1,2}:\d{2}', question, re.IGNORECASE):
            # If has "price at X:XX" and no above/below keyword, it's interval
            return 'interval'

        # Method 4: Check for price range pattern (from outcomes text)
        # Interval markets show ranges like "$X - $Y" in scraped text
        range_pattern = r'\$[\d,]+\.?\d*\s*-\s*\$[\d,]+\.?\d*'
        if re.search(range_pattern, question):
            return 'interval'

        # Default to binary
        return 'binary'

    def _extract_price_ranges(self):
        """
        Extract price ranges from interval market question
        Example: "< $67,005.37 ... $67,005.37 - $67,678.79 ... > $67,678.79"
        """
        import re

        question = self.question

        # Pattern 1: Look for price ranges like "$67,005.37 - $67,678.79"
        range_pattern = r'\$?([\d,]+\.?\d*)\s*-\s*\$?([\d,]+\.?\d*)'
        range_match = re.search(range_pattern, question)

        if range_match:
            try:
                low_price = float(range_match.group(1).replace(',', ''))
                high_price = float(range_match.group(2).replace(',', ''))

                self.mid_threshold_low = low_price
                self.mid_threshold_high = high_price

                # Now find the LOW and HIGH thresholds
                # LOW is typically "< $X" where X is the same as mid_threshold_low
                # HIGH is typically "> $Y" where Y is the same as mid_threshold_high

                less_than_pattern = r'<\s*\$?([\d,]+\.?\d*)'
                less_match = re.search(less_than_pattern, question)
                if less_match:
                    self.low_threshold = float(less_match.group(1).replace(',', ''))

                greater_than_pattern = r'>\s*\$?([\d,]+\.?\d*)'
                greater_match = re.search(greater_than_pattern, question)
                if greater_match:
                    self.high_threshold = float(greater_match.group(1).replace(',', ''))

                return
            except (ValueError, IndexError):
                pass

        # Fallback: Look for individual price mentions
        all_prices = re.findall(r'\$?([\d,]+\.?\d*)', question)
        if len(all_prices) >= 2:
            try:
                prices = [float(p.replace(',', '')) for p in all_prices if float(p.replace(',', '')) > 100]
                prices = sorted(set(prices))

                if len(prices) >= 2:
                    # Assume first two are the range boundaries
                    self.mid_threshold_low = prices[0]
                    self.mid_threshold_high = prices[1] if len(prices) > 1 else prices[0]
                    self.low_threshold = prices[0]
                    self.high_threshold = prices[-1]
            except (ValueError, IndexError):
                pass

    def is_active(self) -> bool:
        """Check if market is currently ACTIVE"""
        if self.status.upper() != 'ACTIVE':
            return False
        return True

    def get_markdown_link(self) -> str:
        """Get markdown-formatted link"""
        if self.url:
            return f"[{self.symbol}]({self.url})"
        return f"[{self.symbol}](No link)"

    def __repr__(self) -> str:
        return f"UnhedgedActiveMarket({self.symbol}, {self.market_type}, status={self.status})"


class UnhedgedActiveMarketsScraper:
    """Scrape currently ACTIVE markets from Unhedged"""

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

    def scrape_active_markets(self, category: str = 'crypto') -> List[UnhedgedActiveMarket]:
        """
        Scrape all ACTIVE markets from Unhedged

        Args:
            category: Market category (default: 'crypto')

        Returns:
            List of active markets
        """
        try:
            if self.driver is None:
                self._init_driver()

            # Navigate to markets page
            url = f"https://unhedged.gg/markets?category={category}&sort=newest"
            print(f"   [dim]Loading {url}...[/dim]")
            self.driver.get(url)

            # Wait for page load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait longer for JavaScript to load markets (React app)
            import time
            time.sleep(8)

            # Try to find market data in different ways
            markets = []

            # Method 1: Look for market cards/links in DOM (after JS execution)
            try:
                # Find all links that might be markets
                market_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/markets/']")
                print(f"   [dim]Found {len(market_elements)} market links in DOM[/dim]")

                for elem in market_elements[:50]:  # Limit to first 50
                    try:
                        href = elem.get_attribute('href')
                        if href and '/markets/' in href:
                            # Extract market ID from href
                            # Handle both relative (/markets/id) and absolute (https://unhedged.gg/markets/id) URLs
                            if '/markets/' in href:
                                # Split by '/markets/' and get the part after it
                                parts = href.split('/markets/')
                                if len(parts) > 1:
                                    market_id = parts[1].split('?')[0]  # Remove query params
                                else:
                                    continue
                            else:
                                continue

                            # Try to get text content
                            text = elem.text.strip()
                            if not text:
                                # Try to get from aria-label or other attributes
                                text = elem.get_attribute('aria-label') or ''
                                text = elem.get_attribute('title') or ''

                            if text and len(text) > 10:  # Valid market name
                                market_data = {
                                    'id': market_id,
                                    'slug': market_id,
                                    'question': text[:200],
                                    'name': text[:100],
                                    'status': 'ACTIVE',  # Assume active if on page
                                    'category': 'crypto',
                                    'outcomes': []
                                }
                                markets.append(UnhedgedActiveMarket(market_data))
                    except:
                        continue

                print(f"   [dim]Extracted {len(markets)} markets from DOM links[/dim]")

            except Exception as e:
                print(f"   [WARN] Failed to extract from DOM: {str(e)[:50]}")

            # Method 2: Check page source (fallback)
            if len(markets) == 0:
                html = self.driver.page_source

                # Look for market data in script tags
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                # Find all market links
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    if '/markets/' in href:
                        # Extract market ID from href (handle both relative and absolute URLs)
                        parts = href.split('/markets/')
                        if len(parts) > 1:
                            market_id = parts[1].split('?')[0]  # Remove query params
                        else:
                            continue

                        # Get question from link text or nearby
                        text = link.get_text(strip=True)
                        if not text:
                            # Try to find from parent or siblings
                            parent = link.find_parent()
                            if parent:
                                text = parent.get_text(strip=True)

                        if text and len(text) > 10 and len(text) < 300:
                            market_data = {
                                'id': market_id,
                                'slug': market_id,
                                'question': text[:200],
                                'name': text[:100],
                                'status': 'ACTIVE',
                                'category': 'crypto',
                                'outcomes': []
                            }
                            markets.append(UnhedgedActiveMarket(market_data))

                print(f"   [dim]Extracted {len(markets)} markets from BeautifulSoup[/dim]")

            print(f"   [green]Total markets found: {len(markets)}[/green]")

            return markets

        except Exception as e:
            print(f"   [ERROR] Failed to scrape active markets: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_active_markets_from_html(self, html: str) -> List[UnhedgedActiveMarket]:
        """Extract active markets from HTML"""
        markets = []

        # Method 1: Look for JSON data in script tags (React state)
        script_tags = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)

        for script in script_tags:
            if '__NEXT_DATA__' in script or 'market' in script.lower():
                # Try to extract JSON
                try:
                    # Look for market data patterns
                    json_matches = re.findall(r'\{[^{}]*(?:"question"|"id"|"name"|"slug")[^{}]*\}', script)

                    for match in json_matches:
                        try:
                            data = json.loads(match)
                            if 'question' in data or 'id' in data:
                                markets.append(UnhedgedActiveMarket(data))
                        except:
                            continue
                except:
                    pass

        # Method 2: Look for market cards/links in HTML
        # Pattern: <a href="/markets/some-slug">
        market_links = re.findall(r'<a[^>]*href="/markets/([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)

        for slug, title in market_links:
            # Check if we already have this market
            if not any(m.slug == slug for m in markets):
                market_data = {
                    'id': slug,
                    'slug': slug,
                    'question': title.strip() if title else slug,
                    'name': title.strip() if title else slug,
                    'status': 'ACTIVE',  # Assume active if on page
                    'category': 'crypto',
                    'outcomes': []
                }
                markets.append(UnhedgedActiveMarket(market_data))

        return markets

    def get_active_markets_for_symbols(self, symbols: List[str]) -> List[UnhedgedActiveMarket]:
        """
        Get active markets filtered by our symbols

        Args:
            symbols: List of symbols we track (BTCUSDT, ETHUSDT, etc.)

        Returns:
            List of active markets for our symbols
        """
        all_active = self.scrape_active_markets()

        # Filter by our symbols
        filtered = []
        for market in all_active:
            if market.symbol in symbols and market.symbol != 'UNKNOWN':
                filtered.append(market)

        return filtered

    def get_active_markets_summary(self) -> Dict:
        """
        Get summary of all active markets

        Returns:
            Dict with market info for Discord alert
        """
        markets = self.scrape_active_markets()

        # Group by symbol
        by_symbol = {}
        for market in markets:
            if market.symbol == 'UNKNOWN':
                continue

            if market.symbol not in by_symbol:
                by_symbol[market.symbol] = []

            by_symbol[market.symbol].append(market)

        return {
            'total_markets': len(markets),
            'by_symbol': by_symbol,
            'markets': markets
        }

    def close(self):
        """Close driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def test_active_markets_scraper():
    """Test the active markets scraper"""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print("[bold cyan]Testing Unhedged Active Markets Scraper[/bold cyan]\n")

    with UnhedgedActiveMarketsScraper() as scraper:
        console.print("[dim]Scraping active markets...[/dim]\n")

        summary = scraper.get_active_markets_summary()

        console.print(f"[green]Found {summary['total_markets']} active markets[/green]\n")

        # Table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Symbol", style="cyan")
        table.add_column("Type")
        table.add_column("Question")
        table.add_column("Status")
        table.add_column("Link")

        for market in summary['markets'][:10]:
            question_short = market.question[:50] + "..." if len(market.question) > 50 else market.question

            table.add_row(
                market.symbol,
                market.market_type,
                question_short,
                market.status,
                market.url[:40] + "..." if market.url and len(market.url) > 40 else market.url
            )

        console.print(table)

        # Show by symbol
        console.print("\n[bold]Grouped by Symbol:[/bold]")
        for symbol, markets_list in summary['by_symbol'].items():
            console.print(f"  {symbol}: {len(markets_list)} market(s)")


if __name__ == "__main__":
    test_active_markets_scraper()
