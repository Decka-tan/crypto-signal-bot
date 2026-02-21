"""
Unhedged Market Scraper
Scrapes https://unhedged.gg/markets?category=crypto&sort=newest
Extracts market data including IDs, prices, and timing
"""

import sys
import io
import time
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class UnhedgedMarketType:
    """Unhedged market types"""
    BINARY = "binary"  # YES/NO above price
    RANGE = "range"    # Price ranges


class UnhedgedMarket:
    """Represents an Unhedged prediction market"""

    def __init__(self, data: Dict):
        self.raw_data = data
        self.market_id = data.get('id', '')
        self.question = data.get('question', '')
        self.name = data.get('name', '')
        self.category = data.get('category', 'crypto')
        self.market_type = self._detect_market_type()
        self.symbol = self._extract_symbol()
        self.target_price = self._extract_target_price()
        self.target_time = self._extract_target_time()
        self.update_time = data.get('created_at', '') or data.get('startTime', '')
        self.close_time = data.get('closeTime', '')
        self.resolve_time = data.get('resolveTime', '')
        self.outcomes = data.get('outcomes', [])
        self.odds = data.get('odds', {})

    def _detect_market_type(self) -> str:
        """Detect if market is binary (YES/NO) or range"""
        question_lower = self.question.lower()

        if 'above' in question_lower or 'below' in question_lower:
            return UnhedgedMarketType.BINARY
        elif len(self.outcomes) == 3:
            return UnhedgedMarketType.RANGE
        else:
            return UnhedgedMarketType.BINARY  # Default

    def _extract_symbol(self) -> str:
        """Extract crypto symbol from question"""
        question = self.question.upper()

        # Common crypto symbols
        symbols = ['BTC', 'ETH', 'SOL', 'CC', 'CANTON', 'BNB', 'ADA', 'DOGE', 'MATIC']

        for symbol in symbols:
            if symbol in question:
                if symbol == 'CANTON':
                    return 'CCUSDT'
                return f"{symbol}USDT"

        # Try to extract from question pattern
        # Pattern: "XXX Coin above..." or "XXX price at..."
        match = re.search(r'([A-Z]{2,10})\s+(?:COIN|PRICE)', question)
        if match:
            symbol = match.group(1)
            if symbol == 'CANTON':
                return 'CCUSDT'
            return f"{symbol}USDT"

        return 'UNKNOWN'

    def _extract_target_price(self) -> Optional[float]:
        """Extract target price from question"""
        # Pattern: $XXXXX or XXXXX USD
        patterns = [
            r'\$(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*USD',
            r'above\s+(\d+\.?\d*)',
            r'below\s+(\d+\.?\d*)',
        ]

        question = self.question.lower()
        for pattern in patterns:
            match = re.search(pattern, question)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass

        return None

    def _extract_target_time(self) -> Optional[str]:
        """Extract target time from question"""
        # Pattern: "at X:00 PM" or "at X:00 AM"
        match = re.search(r'at\s+(\d{1,2}):(\d{2})\s*(AM|PM)', self.question, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = match.group(3).upper()

            # Convert to 24-hour format
            if ampm == 'PM' and hour != 12:
                hour += 12
            elif ampm == 'AM' and hour == 12:
                hour = 0

            return f"{hour:02d}:{minute:02d}"

        return None

    def get_market_duration_minutes(self) -> int:
        """Get market duration in minutes"""
        if self.market_type == UnhedgedMarketType.BINARY:
            return 60  # 1 hour
        else:
            return 120  # 2 hours

    def get_close_minute(self) -> int:
        """Get the minute when betting closes (relative to market start)"""
        if self.market_type == UnhedgedMarketType.BINARY:
            return 50  # XX:50 for hourly markets
        else:
            return 110  # XX:110 for 2-hourly markets

    def is_market_active(self) -> bool:
        """
        Check if market is still ACTIVE (not resolved)

        Returns:
            True if market is active, False if resolved/ended
        """
        if not self.resolve_time:
            return True  # Assume active if no resolve time

        try:
            # Parse resolve time
            # Format could be: "2025-02-20T10:00:00Z" or similar
            resolve_dt = None

            # Try ISO format
            if 'T' in self.resolve_time:
                from datetime import datetime
                resolve_dt = datetime.fromisoformat(self.resolve_time.replace('Z', '+00:00'))
            else:
                # Try other formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%H:%M']:
                    try:
                        from datetime import datetime
                        resolve_dt = datetime.strptime(self.resolve_time, fmt)
                        break
                    except:
                        continue

            if resolve_dt:
                from datetime import datetime
                now = datetime.now(resolve_dt.tzinfo)
                return now < resolve_dt

        except Exception as e:
            pass

        return True  # Assume active if can't determine

    def get_time_until_resolved(self) -> Optional[int]:
        """
        Get minutes until market resolves

        Returns:
            Minutes until resolve, or None if can't determine
        """
        if not self.resolve_time:
            return None

        try:
            from datetime import datetime

            # Parse resolve time
            if 'T' in self.resolve_time:
                resolve_dt = datetime.fromisoformat(self.resolve_time.replace('Z', '+00:00'))
            else:
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        resolve_dt = datetime.strptime(self.resolve_time, fmt)
                        break
                    except:
                        continue
                else:
                    return None

            now = datetime.now(resolve_dt.tzinfo)
            delta = resolve_dt - now

            minutes_left = int(delta.total_seconds() / 60)
            return max(0, minutes_left)

        except Exception as e:
            return None

    def get_status_display(self) -> str:
        """
        Get market status display string

        Returns:
            Status string like "15 min left", "ENDED", "RESOLVED"
        """
        if not self.is_market_active():
            return "ENDED"

        minutes_left = self.get_time_until_resolved()
        if minutes_left is not None:
            if minutes_left <= 0:
                return "ENDED"
            elif minutes_left <= 60:
                return f"{minutes_left} min left"
            else:
                hours = minutes_left // 60
                mins = minutes_left % 60
                return f"{hours}h {mins}m left"

        return "ACTIVE"

    def should_alert_now(self, current_minute: int) -> bool:
        """
        Check if we should send alert now

        Args:
            current_minute: Current minute in the hour (0-59)

        Returns:
            True if should alert
        """
        close_minute = self.get_close_minute()

        # Alert 10-15 minutes before close
        if self.market_type == UnhedgedMarketType.BINARY:
            # Hourly: alert at XX:40-XX:45
            return 40 <= current_minute <= 45
        else:
            # 2-hourly: alert at XX:100-XX:105 (which is XX:40-XX:45 of second hour)
            return 40 <= current_minute <= 45

    def __repr__(self) -> str:
        return f"UnhedgedMarket({self.symbol}, {self.market_type}, {self.question})"


class UnhedgedScraper:
    """Scrape Unhedged markets"""

    def __init__(self, use_selenium: bool = True):
        """
        Initialize scraper

        Args:
            use_selenium: Use Selenium for JavaScript rendering
        """
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None
        self.markets = []

    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Run: pip install selenium")

        options = Options()
        options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=options)

    def scrape_markets_selenium(self) -> List[UnhedgedMarket]:
        """Scrape markets using Selenium (handles JavaScript)"""
        if not self.use_selenium:
            print("[yellow]Selenium not available, use requests method[/yellow]")
            return self.scrape_markets_requests()

        try:
            self._init_selenium()

            url = "https://unhedged.gg/markets?category=crypto&sort=newest"
            print(f"[dim]Loading {url}...[/dim]")

            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait extra time for JavaScript to load markets
            time.sleep(5)

            # Get page HTML after JavaScript execution
            html = self.driver.page_source

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Look for market data in script tags or JSON
            markets_data = self._extract_markets_from_html(soup)

            return markets_data

        except Exception as e:
            print(f"[red]Error scraping with Selenium: {e}[/red]")
            return []
        finally:
            if self.driver:
                self.driver.quit()

    def scrape_markets_requests(self) -> List[UnhedgedMarket]:
        """Scrape markets using requests (may not get JS-rendered content)"""
        if not REQUESTS_AVAILABLE:
            print("[red]Neither Selenium nor requests available[/red]")
            return []

        try:
            url = "https://unhedged.gg/markets?category=crypto&sort=newest"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            markets_data = self._extract_markets_from_html(soup)

            return markets_data

        except Exception as e:
            print(f"[red]Error scraping with requests: {e}[/red]")
            return []

    def _extract_markets_from_html(self, soup) -> List[UnhedgedMarket]:
        """Extract market data from HTML"""
        markets = []

        # Method 1: Look for JSON in script tags
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = script.string

            if not script_content:
                continue

            # Look for market data patterns
            if 'market' in script_content.lower() or 'btc' in script_content.lower():
                # Try to extract JSON
                json_matches = re.findall(r'\{[^{}]*(?:"(?:question|id|symbol)"[^{}]*)+\}', script_content)

                for match in json_matches:
                    try:
                        data = json.loads(match)
                        if 'question' in data or 'id' in data:
                            markets.append(UnhedgedMarket(data))
                    except:
                        pass

        # Method 2: Look for market elements in DOM
        # This depends on Unhedged's HTML structure
        market_elements = soup.find_all(['div', 'a'], class_=re.compile(r'market|card', re.I))

        for elem in market_elements:
            text = elem.get_text()

            # Look for market patterns
            if 'above' in text.lower() or 'price at' in text.lower():
                # Try to extract data from attributes
                data = {}
                for attr in ['data-id', 'data-market-id', 'id']:
                    if elem.get(attr):
                        data['id'] = elem.get(attr)
                        break

                data['question'] = text.strip()[:200]  # Limit length

                if data.get('id'):
                    markets.append(UnhedgedMarket(data))

        return markets

    def scrape_and_filter(self, symbols: List[str] = None) -> List[UnhedgedMarket]:
        """
        Scrape and filter markets by symbols

        Args:
            symbols: List of symbols to filter (e.g., ['BTCUSDT', 'ETHUSDT'])
                     If None, returns all markets

        Returns:
            Filtered list of markets
        """
        if self.use_selenium:
            markets = self.scrape_markets_selenium()
        else:
            markets = self.scrape_markets_requests()

        if symbols:
            # Filter by our symbols
            filtered = []
            for market in markets:
                if market.symbol in symbols or market.symbol != 'UNKNOWN':
                    filtered.append(market)
            return filtered

        return markets

    def get_market_id_map(self, symbols: List[str]) -> Dict[str, str]:
        """
        Get mapping of symbol -> market_id

        Args:
            symbols: List of our symbols (e.g., ['BTCUSDT', 'ETHUSDT'])

        Returns:
            Dict mapping symbol to market_id
        """
        markets = self.scrape_and_filter(symbols)

        market_map = {}
        for market in markets:
            if market.symbol != 'UNKNOWN':
                market_map[market.symbol] = market.market_id

        return market_map

    def get_active_markets_for_symbols(self, symbols: List[str]) -> Dict[str, UnhedgedMarket]:
        """
        Get active markets for specific symbols

        Args:
            symbols: List of our symbols (e.g., ['BTCUSDT', 'ETHUSDT'])

        Returns:
            Dict mapping symbol to UnhedgedMarket (only ACTIVE markets)
        """
        markets = self.scrape_and_filter(symbols)

        active_markets = {}
        for market in markets:
            # Only include active markets
            if market.symbol != 'UNKNOWN' and market.is_market_active():
                active_markets[market.symbol] = market

        return active_markets

    def should_alert_symbol(self, symbol: str) -> tuple[bool, UnhedgedMarket, str]:
        """
        Check if we should send alert for this symbol

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')

        Returns:
            Tuple of (should_alert: bool, market: UnhedgedMarket, reason: str)
            - should_alert: True if should send alert
            - market: The market object (or None)
            - reason: Status message (e.g., "15 min left", "ENDED", "No market found")
        """
        markets = self.scrape_and_filter([symbol])

        if not markets:
            return False, None, "No market found"

        # Find matching market
        for market in markets:
            if market.symbol == symbol:
                # Check if market is active
                if not market.is_market_active():
                    return False, market, "ENDED"

                # Check if within betting window
                minutes_left = market.get_time_until_resolved()
                if minutes_left is not None and minutes_left > 0:
                    # Market is active, OK to alert
                    status = market.get_status_display()
                    return True, market, status
                else:
                    return False, market, "ENDED"

        return False, None, "No matching market"


def main():
    """Test scraper"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()

    console.print("[bold cyan]Unhedged Market Scraper[/bold cyan]")
    console.print("[dim]Testing scraper functionality...[/dim]\n")

    # Try both methods
    for use_selenium in [True, False]:
        console.print(f"[bold]Testing with Selenium={use_selenium}[/bold]")

        try:
            scraper = UnhedgedScraper(use_selenium=use_selenium)
            markets = scraper.scrape_and_filter(['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT'])

            console.print(f"[green]✓ Found {len(markets)} markets[/green]\n")

            if markets:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Symbol", style="cyan")
                table.add_column("Type")
                table.add_column("Market ID")
                table.add_column("Question")

                for market in markets[:5]:
                    table.add_row(
                        market.symbol,
                        market.market_type,
                        market.market_id[:20] + "..." if len(market.market_id) > 20 else market.market_id,
                        market.question[:50] + "..." if len(market.question) > 50 else market.question
                    )

                console.print(table)

        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]\n")


if __name__ == "__main__":
    main()
