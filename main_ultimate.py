#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Signal Bot - ULTIMATE Mode
Institutional-grade analysis combining:
- Multi-timeframe technical analysis
- Machine learning predictions
- Sentiment analysis
- Correlation analysis
- Funding rates
"""

import sys
import io
import time
import argparse
import yaml
import traceback
import os
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding (DISABLED - causing stdout issues)
# if sys.platform == "win32":
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from core.market_monitor import MarketMonitor
from core.ultimate_signals import UltimateSignalGenerator, SignalType
from core.alerts import AlertManager
from core.unhedged_client import UnhedgedClient, BetPreparer
from core.unhedged_scraper import UnhedgedScraper
from core.interval_signals import IntervalSignalGenerator, IntervalType
from core.unhedged_scraper import UnhedgedMarket
from core.unhedged_market_status import UnhedgedMarketStatus
from core.unhedged_odds_scraper import UnhedgedOddsScraper, UnhedgedOdds
from core.unhedged_active_markets import UnhedgedActiveMarketsScraper, UnhedgedActiveMarket
from core.result_tracker import ResultTracker, BetResult
from core.proper_signals import ProperSignalGenerator, MarketOdds
from core.unhedged_history import UnhedgedHistoryFetcher, calculate_calibration_from_tracker


def scrape_market_ids_to_config():
    """Standalone function to scrape market IDs and update config.yaml"""
    import yaml
    from bs4 import BeautifulSoup
    import re
    import time
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    console = Console()

    try:
        console.print("  [dim]Starting Chrome driver...[/dim]")

        # Setup Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')

        driver = webdriver.Chrome(options=chrome_options)

        try:
            # Navigate to Unhedged
            url = "https://unhedged.gg/markets?category=crypto&sort=newest"
            driver.get(url)

            # Wait for page load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Wait for market data
            time.sleep(5)

            # Get HTML
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Extract market IDs
            market_cards = soup.find_all('a', href=re.compile(r'/markets/'))

            # Map to our symbols
            symbol_map = {}
            for card in market_cards:
                href = card.get('href', '')
                market_id = href.replace('/markets/', '') if href else ''

                title_elem = card.find('h3')
                title = title_elem.get_text(strip=True) if title_elem else ''

                # Determine symbol
                title_lower = title.lower()
                if 'canton' in title_lower or ' cc ' in title.lower():
                    symbol = 'CCUSDT'
                elif 'btc' in title_lower or 'bitcoin' in title_lower:
                    symbol = 'BTCUSDT'
                elif 'eth' in title_lower or 'ethereum' in title_lower:
                    symbol = 'ETHUSDT'
                elif 'sol' in title_lower or 'solana' in title_lower:
                    symbol = 'SOLUSDT'
                else:
                    continue

                # Only store binary markets (with "above" in title)
                if 'above' in title_lower and market_id:
                    symbol_map[symbol] = market_id

            driver.quit()

            if symbol_map:
                console.print(f"  [green]✓[/green] Found {len(symbol_map)} market IDs:\n")

                for symbol, mid in symbol_map.items():
                    console.print(f"    [cyan]{symbol}:[/cyan] {mid[:30]}...")

                # Update config.yaml
                try:
                    with open('config.yaml', 'r') as f:
                        config = yaml.safe_load(f)

                    config.setdefault('unhedged', {})['manual_markets'] = symbol_map

                    with open('config.yaml', 'w') as f:
                        yaml.dump(config, f, default_flow_style=False)

                    console.print("\n  [green]✓[/green] config.yaml updated!")

                except Exception as e:
                    console.print(f"\n  [red]✗[/red] Failed to update config.yaml: {e}")
            else:
                console.print("  [yellow]⚠[/yellow] No markets found")

        except Exception as e:
            if driver:
                driver.quit()
            raise

    except Exception as e:
        console.print(f"  [red]✗ Scraping failed: {e}[/red]")
        console.print("  [dim]Make sure Chrome and ChromeDriver are installed[/dim]")


class CryptoSignalBotUltimate:
    """Ultimate version with all analysis methods"""

    def __init__(self, config_path: str = "config.yaml", demo_mode: bool = False):
        """Initialize ultimate bot"""
        self.config = self._load_config(config_path)
        self.console = Console()

        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
        timeframe = self.config.get('timeframe', '15m')

        exchange = self.config.get('exchange', 'auto')
        self.market_monitor = MarketMonitor(symbols, timeframe, demo_mode=demo_mode, exchange=exchange)
        self.signal_generator = UltimateSignalGenerator(self.config, self.market_monitor)
        self.alert_manager = AlertManager(self.config)

        # Interval signal generator for LOW/MID/HIGH markets
        interval_config = self.config.get('interval_markets', {})
        if interval_config.get('enabled', False):
            self.interval_generator = IntervalSignalGenerator(self.config, self.market_monitor)
        else:
            self.interval_generator = None

        # Unhedged market status calculator (time-based)
        self.unhedged_status = UnhedgedMarketStatus()

        # Unhedged active markets scraper (get CURRENTLY ACTIVE markets from Unhedged)
        self.active_markets_scraper = UnhedgedActiveMarketsScraper()
        self.active_markets_cache = {}
        self.active_markets_cache_time = 0

        # Unhedged odds scraper for crowd sentiment
        self.odds_scraper = UnhedgedOddsScraper()
        self.odds_cache = {}  # Cache odds to avoid re-scraping
        self.odds_cache_time = {}  # Track when odds were cached

        # Result tracker for backtesting
        self.result_tracker = ResultTracker()

        # PROPER signal generator (with EV, edge, real probability)
        self.proper_signal_generator = ProperSignalGenerator(self.config)

        # Unhedged scraper for real-time market status (may not work due to JS rendering)
        self.unhedged_scraper = UnhedgedScraper(use_selenium=True)

        # Unhedged client (optional)
        self.unhedged_client = None
        self.bet_preparer = None
        self.unhedged_scraper = None

        unhedged_config = self.config.get('unhedged', {})
        if unhedged_config.get('enabled', False):
            api_key = unhedged_config.get('api_key', '')
            if api_key:
                try:
                    self.unhedged_client = UnhedgedClient(api_key)
                    self.bet_preparer = BetPreparer(self.unhedged_client, self.config)
                except Exception as e:
                    pass  # Silent fail, will show error in run()

        self.running = False
        self.last_alerts = {}

    def _load_config(self, config_path: str):
        """Load configuration from YAML and environment variables"""
        # Load .env file
        from dotenv import load_dotenv
        env_path = Path('.env')
        if env_path.exists():
            load_dotenv(env_path)

        # Load YAML config
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except:
            config = self._default_config()

        # Override with environment variables (if set)
        if os.getenv('UNHEDGED_API_KEY'):
            config.setdefault('unhedged', {})['api_key'] = os.getenv('UNHEDGED_API_KEY')

        if os.getenv('DISCORD_WEBHOOK_URL'):
            config.setdefault('alerts', {})['discord'] = config.get('alerts', {}).get('discord', {})
            config['alerts']['discord']['webhook_url'] = os.getenv('DISCORD_WEBHOOK_URL')

        return config

    def _default_config(self):
        """Default configuration"""
        return {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            'timeframe': '15m',
            'thresholds': {'min_confidence': 75},
            'alerts': {'console': True, 'discord': {'enabled': False}},
            'display': {'update_interval': 60}
        }

    def analyze_symbol(self, symbol: str):
        """Analyze symbol with ultimate method"""
        return self.signal_generator.generate_ultimate_signal(symbol)

    def analyze_symbol_proper(self, symbol: str) -> Dict:
        """
        PROPER signal analysis with EV, Edge, and Real Probability

        Replaces UltimateSignalGenerator with ProperSignalGenerator
        """
        # Get price data
        df = self.market_monitor.get_klines(symbol, limit=100)
        if df is None or len(df) < 30:
            return {
                'error': 'Not enough data',
                'symbol': symbol,
                'reason': 'Need at least 30 candles'
            }

        current_price = float(df['close'].iloc[-1])

        # Get market odds from Unhedged
        market_odds = None
        try:
            odds = self.get_market_odds(symbol, 'binary')
            if odds:
                market_odds = MarketOdds(
                    yes_price=odds.yes_pct / 100,
                    no_price=odds.no_pct / 100,
                    yes_volume=odds.yes_volume,
                    no_volume=odds.no_volume
                )
        except:
            pass

        # Get active market for strike price
        active_market = self.find_matching_market(symbol, market_type='binary')
        strike_price = None
        market_question = ""
        market_id = None
        market_link = None

        if active_market:
            market_question = active_market.question
            market_id = active_market.market_id
            market_link = active_market.url

            # Extract strike price from question
            import re
            above_match = re.search(r'above\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)
            below_match = re.search(r'below\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)

            if above_match:
                strike_price = float(above_match.group(1).replace(',', ''))
            elif below_match:
                strike_price = float(below_match.group(1).replace(',', ''))

        # Generate PROPER signal
        signal_analysis = self.proper_signal_generator.generate_signal(
            symbol=symbol,
            df=df,
            current_price=current_price,
            market_odds=market_odds,
            strike_price=strike_price
        )

        # Convert to dict format (compatible with existing code)
        result = {
            'symbol': symbol,
            'signal': signal_analysis.signal,
            'signal_type': signal_analysis.signal,
            'confidence': signal_analysis.confidence,
            'p_yes': signal_analysis.p_yes,
            'ev': signal_analysis.ev,
            'edge': signal_analysis.edge,
            'is_bettable': signal_analysis.is_bettable,
            'current_price': signal_analysis.current_price,
            'predicted_price': signal_analysis.predicted_price,
            'distance_to_strike': signal_analysis.distance_to_strike,
            'distance_dollars': signal_analysis.distance_dollars,
            'buffer_remaining': signal_analysis.buffer_remaining,
            'volatility_5m': signal_analysis.volatility_5m,
            'reasons': signal_analysis.reasons,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market_id': market_id,
            'market_link': market_link,
            'market_question': market_question
        }

        # Add market odds info
        if market_odds:
            result['market_odds'] = {
                'yes_pct': market_odds.yes_price * 100,
                'no_pct': market_odds.no_price * 100,
                'yes_volume': market_odds.yes_volume,
                'no_volume': market_odds.no_volume
            }
            result['implied_prob'] = market_odds.implied_prob_yes * 100
            result['crowd_sentiment'] = 'STRONG_BULLISH' if market_odds.yes_price > 0.7 else \
                                           'BULLISH' if market_odds.yes_price > 0.6 else \
                                           'NEUTRAL' if market_odds.yes_price > 0.4 else \
                                           'BEARISH' if market_odds.yes_price > 0.3 else 'STRONG_BEARISH'

        # Add edge status to reasons
        if signal_analysis.edge > 0:
            result['reasons'].insert(0, f"Edge: +{signal_analysis.edge*100:.1f}%")
        else:
            result['reasons'].insert(0, f"Edge: {signal_analysis.edge*100:.1f}%")

        # Add distance to strike status
        if signal_analysis.distance_to_strike is not None:
            dist = signal_analysis.distance_to_strike
            if abs(dist) < 1:
                result['reasons'].append(f"Too close to strike: {dist:.2f}%")
            elif abs(dist) > 5:
                result['reasons'].append(f"Good distance: {dist:.2f}%")

        # Add volatility status
        if signal_analysis.volatility_5m is not None:
            vol = signal_analysis.volatility_5m * 100
            result['reasons'].append(f"5m Volatility: {vol:.2f}%")

        return result

    def check_and_alert(self, signal_analysis):
        """
        Check and send alert
        Implements flexible high-confidence strategy with time-based market status check + crowd odds
        """
        if not signal_analysis or signal_analysis.get('error'):
            return

        symbol = signal_analysis['symbol']
        confidence = signal_analysis['confidence']
        min_conf = self.config.get('thresholds', {}).get('min_confidence', 80)

        from core.ultimate_signals import SignalType

        # Check if signal meets minimum confidence
        if signal_analysis['signal_type'] == SignalType.HOLD or confidence < min_conf:
            return

        # CHECK: Time-based market status (binary markets)
        # MUST be during active window (XX:05 - XX:50)
        current_min = time.localtime().tm_min

        # Skip if market is CLOSED (XX:50-XX:00)
        if current_min >= 50:
            self.console.print(f"   [dim][SKIP] {symbol}: Market CLOSED (betting ends at XX:50)[/dim]")
            return

        # Skip if market just RESOLVED (XX:00-XX:05)
        if current_min < 5:
            self.console.print(f"   [dim][SKIP] {symbol}: Market RESOLVED, new market opening[/dim]")
            return

        # Market is ACTIVE (XX:05 - XX:50)
        status_msg = f"{50 - current_min} min left" if current_min >= 30 else "ACTIVE"

        # CHECK: Find the BEST matching market for this symbol
        # This handles multiple markets per symbol (e.g., BTC at 9AM, 11AM, 1PM)
        active_market = self.find_matching_market(symbol)

        if active_market:
            # CRITICAL: Check if this SPECIFIC market is still active
            if not active_market.is_still_active():
                self.console.print(f"   [dim][SKIP] {symbol}: Market '{active_market.question[:40]}...' already resolved[/dim]")
                return

            # Market is still active - add link and info
            signal_analysis['market_link'] = active_market.url
            signal_analysis['market_id'] = active_market.market_id

            # Add time until resolved to status
            minutes_left = active_market.get_time_until_resolved_minutes()
            if minutes_left is not None:
                status_msg = f"{minutes_left} min left"
                signal_analysis['time_until_resolved'] = f"{minutes_left} min"

                # CHECK: Optimal time window for binary markets
                # Binary: 1-hour duration, optimal is CLOSE to resolution (trend clearer)
                # Too early: > 40 min left (trend not yet established)
                # Too close: < 5 min left (market closing)
                min_time_binary = self.config.get('min_time_binary', 5)
                max_time_binary = self.config.get('max_time_binary', 40)

                if minutes_left < min_time_binary:
                    self.console.print(f"   [dim][SKIP] {symbol}: Only {minutes_left} min left (market closing)[/dim]")
                    return
                elif minutes_left > max_time_binary:
                    self.console.print(f"   [dim][SKIP] {symbol}: {minutes_left} min left (too early, trend not yet established)[/dim]")
                    return
                # Optimal: 5-40 min left (close to resolution, trend clearer!)
        else:
            # No time data available - skip to be safe
            self.console.print(f"   [dim][SKIP] {symbol}: No time data available[/dim]")
            return

        # CHECK: Get crowd odds from Unhedged
        try:
            odds = self.get_market_odds(symbol, 'binary')
            if odds:
                # Adjust confidence based on crowd sentiment
                adjusted_confidence, additional_reasons = self.adjust_confidence_with_odds(signal_analysis, odds)

                # Update confidence
                signal_analysis['original_confidence'] = signal_analysis['confidence']
                signal_analysis['confidence'] = adjusted_confidence
                signal_analysis['crowd_odds'] = {
                    'yes_pct': odds.yes_pct,
                    'no_pct': odds.no_pct
                }
                signal_analysis['sentiment_strength'] = odds.get_sentiment_strength()

                # Add crowd reasons to existing reasons
                if 'reasons' in signal_analysis:
                    signal_analysis['reasons'].extend(additional_reasons)
                else:
                    signal_analysis['reasons'] = additional_reasons

                # Update confidence variable
                confidence = adjusted_confidence

                # Re-check min confidence with adjusted score
                if confidence < min_conf:
                    self.console.print(f"   [dim][SKIP] {symbol}: Adjusted confidence {adjusted_confidence:.1f}% below threshold[/dim]")
                    return

        except Exception as e:
            pass  # If odds scraping fails, continue with original confidence

        # Add market info to signal analysis
        signal_analysis['market_status'] = status_msg

        # CHECK: Cooldown (prevent spam alerts for same symbol)
        last_time = self.last_alerts.get(symbol, 0)
        cooldown = 120  # 2 minutes cooldown

        if time.time() - last_time < cooldown:
            return

        # ALL CHECKS PASSED - SEND ALERT!
        self.console.print(f"   [green][ALERT] {symbol}: {signal_analysis['signal']} (Confidence: {confidence}%) - {status_msg}[/green]")

        # Log to result tracker for backtesting
        try:
            from datetime import datetime
            import re

            # Parse target price from question (for binary markets)
            target_price = None
            market_question = active_market.question if active_market else ""
            above_match = re.search(r'above\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)
            below_match = re.search(r'below\s+\$?([\d,]+\.?\d*)', market_question, re.IGNORECASE)

            if above_match:
                target_price = float(above_match.group(1).replace(',', ''))
            elif below_match:
                target_price = float(below_match.group(1).replace(',', ''))

            # Get time left
            minutes_left = active_market.get_time_until_resolved_minutes() if active_market else None

            # Calculate edge (our confidence - implied odds)
            edge = confidence - 50  # Simplified, should use actual odds

            # Create bet result
            bet = BetResult(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                symbol=symbol,
                market_type='binary',
                market_id=active_market.market_id if active_market else 'unknown',
                market_question=market_question[:200] if market_question else '',
                signal=signal_analysis['signal'],
                confidence=confidence,
                predicted_price=signal_analysis.get('predicted_price'),
                target_price=target_price,
                current_price=signal_analysis.get('current_price', 0),
                time_until_resolved=minutes_left if minutes_left else 0,
                outcome=signal_analysis['signal'],
                actual_result=None,  # Will update when market resolves
                is_win=None,
                amount_bet=0,  # No actual bet, just signal
                amount_won=None,
                edge=edge
            )

            self.result_tracker.log_bet(bet, raw_analysis=signal_analysis)
        except Exception as e:
            # Don't let logging errors break alerts
            pass

        self.alert_manager.send_alert(signal_analysis)
        self.last_alerts[symbol] = time.time()

    def check_and_alert_proper(self, signal_analysis: Dict):
        """
        PROPER alert checking with EV and is_bettable

        Only alert if:
        1. is_bettable = True (EV > 0 AND passed safety checks)
        2. Market is still active
        """
        if not signal_analysis or signal_analysis.get('error'):
            return

        symbol = signal_analysis['symbol']

        # CHECK: Is this bettable?
        if not signal_analysis.get('is_bettable', False):
            edge = signal_analysis.get('edge', 0) * 100
            ev = signal_analysis.get('ev', 0)

            if edge < 0:
                self.console.print(f"   [dim][SKIP] {symbol}: Negative edge ({edge:.1f}%)[/dim]")
            else:
                dist = signal_analysis.get('distance_to_strike')
                vol = signal_analysis.get('volatility_5m', 0) * 100
                self.console.print(f"   [dim][SKIP] {symbol}: Failed safety (dist: {dist:.1f}%, vol: {vol:.1f}%)[/dim]")
            return

        # CHECK: Market still active?
        market_id = signal_analysis.get('market_id')
        if market_id:
            active_market = self.find_matching_market(symbol)
            if not active_market or not active_market.is_still_active():
                self.console.print(f"   [dim][SKIP] {symbol}: Market resolved[/dim]")
                return

        # ALL CHECKS PASSED - SEND ALERT!
        edge = signal_analysis.get('edge', 0) * 100
        ev = signal_analysis.get('ev', 0)
        p_yes = signal_analysis.get('p_yes', 0) * 100
        implied_prob = signal_analysis.get('implied_prob', 50)

        self.console.print(
            f"   [green][ALERT] {symbol}: {signal_analysis['signal']} "
            f"(P: {p_yes:.1f}%, Imp: {implied_prob:.1f}%, EV: {ev:.3f}, Edge: +{edge:.1f}%)[/green]"
        )

        # Log to result tracker
        try:
            active_market = self.find_matching_market(symbol)
            minutes_left = active_market.get_time_until_resolved_minutes() if active_market else 15

            # Track prediction time and expected resolve time
            from datetime import datetime, timedelta
            now = datetime.now()
            prediction_time = now.strftime('%Y-%m-%d %H:%M:%S')

            # Calculate expected resolve time (XX:00 next hour)
            if minutes_left:
                expected_resolve = now + timedelta(minutes=minutes_left)
                expected_resolve_time = expected_resolve.strftime('%Y-%m-%d %H:%M:%S')
            else:
                expected_resolve_time = None

            bet = BetResult(
                timestamp=signal_analysis['timestamp'],
                symbol=symbol,
                market_type='binary',
                market_id=signal_analysis.get('market_id', 'unknown'),
                market_question=signal_analysis.get('market_question', '')[:200],
                signal=signal_analysis['signal'],
                confidence=signal_analysis['confidence'],
                predicted_price=signal_analysis.get('predicted_price'),
                target_price=None,
                current_price=signal_analysis['current_price'],
                time_until_resolved=minutes_left,
                outcome=signal_analysis['signal'],
                actual_result=None,
                is_win=None,
                amount_bet=0,
                amount_won=None,
                edge=signal_analysis['edge'],
                prediction_time=prediction_time,
                expected_resolve_time=expected_resolve_time
            )

            self.result_tracker.log_bet(bet, raw_analysis=signal_analysis)
        except Exception as e:
            pass  # Don't break alerts for logging errors

        # Send alert
        self.alert_manager.send_alert(signal_analysis)
        self.last_alerts[symbol] = time.time()

    def refresh_active_markets(self) -> List[UnhedgedActiveMarket]:
        """
        Scrape Unhedged for CURRENTLY ACTIVE markets
        Caches ALL markets with composite keys to handle multiple markets per symbol

        Returns:
            List of active markets
        """
        try:
            console = Console()

            # Check if we need to refresh (cache expires every 10 minutes)
            current_time = time.time()
            if current_time - self.active_markets_cache_time < 600:  # 10 minutes
                return list(self.active_markets_cache.values())

            console.print("   [dim][INFO] Refreshing active markets from Unhedged...[/dim]")

            # Scrape active markets
            active_markets = self.active_markets_scraper.scrape_active_markets()

            # Filter for our symbols
            our_symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT'])
            our_markets = [m for m in active_markets if m.symbol in our_symbols and m.symbol != 'UNKNOWN']

            # Cache ALL markets with composite key: {symbol}_{market_id}
            # This allows us to have MULTIPLE markets per symbol
            self.active_markets_cache = {}
            for market in our_markets:
                # Use composite key to handle multiple markets per symbol
                key = f"{market.symbol}_{market.market_id}"
                self.active_markets_cache[key] = market

            self.active_markets_cache_time = current_time

            console.print(f"   [dim][INFO] Found {len(our_markets)} active markets for our symbols[/dim]")

            return our_markets

        except Exception as e:
            console = Console()
            console.print(f"   [yellow][WARN] Failed to refresh active markets: {str(e)[:50]}[/yellow]")
            return []

    def find_matching_market(self, symbol: str, market_type: str = 'any') -> Optional[UnhedgedActiveMarket]:
        """
        Find the BEST matching active market for a symbol
        Prioritizes markets that are still active and closest to resolve time

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            market_type: Filter by market type ('binary', 'interval', or 'any')

        Returns:
            Best matching UnhedgedActiveMarket or None
        """
        # Find all markets for this symbol
        matching_markets = []
        for key, market in self.active_markets_cache.items():
            if key.startswith(f"{symbol}_"):
                # Filter by market type if specified
                if market_type != 'any' and market.market_type != market_type:
                    continue
                matching_markets.append(market)

        if not matching_markets:
            return None

        # Prefer markets that are STILL ACTIVE
        for market in matching_markets:
            minutes_left = market.get_time_until_resolved_minutes()
            if minutes_left is not None and minutes_left > 0:
                # Found an active market!
                return market

        # NO ACTIVE MARKET FOUND - return None, don't return resolved markets!
        return None

    def send_active_markets_alert(self, markets: List[UnhedgedActiveMarket]):
        """
        Send Discord alert with all active market links

        Clean format like alert messages
        """
        if not markets:
            return

        try:
            import requests
            discord_config = self.config.get('alerts', {}).get('discord', {})
            webhook_url = discord_config.get('webhook_url')

            if not webhook_url:
                return

            username = discord_config.get('username', 'Unhedged Bot')
            avatar_url = discord_config.get('avatar_url', '')

            # Build clean message
            lines = []
            lines.append("@everyone 🔔 **ACTIVE MARKETS ON UNHEDGED**\n")

            # Group by symbol
            by_symbol = {}
            for market in markets:
                if market.symbol not in by_symbol:
                    by_symbol[market.symbol] = []
                by_symbol[market.symbol].append(market)

            # List each symbol with its markets
            for symbol in sorted(by_symbol.keys()):
                markets_list = by_symbol[symbol]
                lines.append(f"**{symbol}** ({len(markets_list)} market(s))\n")

                for market in markets_list:
                    # Get time left
                    minutes_left = market.get_time_until_resolved_minutes()
                    time_left = f"{minutes_left}m left" if minutes_left else "Active"

                    # Clean question format
                    question = market.question
                    if " above " in question.lower():
                        # Binary: "Bitcoin above $67,898.71 at 5:00 PM?"
                        question_clean = question.replace("?", "").strip()
                    elif " price at " in question.lower():
                        # Interval: "Bitcoin price at 5:00 PM?"
                        # Extract range
                        if market.low_threshold and market.high_threshold:
                            # Format resolve time
                            resolve_str = market.resolve_time.split('T')[1][:5] if 'T' in str(market.resolve_time) else str(market.resolve_time)
                            low_str = f"{market.low_threshold:.6f}" if market.low_threshold else "N/A"
                            high_str = f"{market.high_threshold:.6f}" if market.high_threshold else "N/A"
                            question_clean = f"Price at {resolve_str}: ${low_str} - ${high_str}"
                        else:
                            question_clean = question.replace("?", "").strip()
                    else:
                        question_clean = question[:60]

                    lines.append(f"  • {question_clean}")
                    lines.append(f"    {time_left} | [View Market]({market.url})")
                    lines.append("")

            # Add footer
            from datetime import datetime
            lines.append(f"_Updated: {datetime.now().strftime('%H:%M:%S')}_")

            message = "\n".join(lines)

            # Send via webhook
            data = {
                "content": message,
                "username": username
            }

            if avatar_url:
                data['avatar_url'] = avatar_url

            response = requests.post(webhook_url, json=data, timeout=10)
            response.raise_for_status()

            console = Console()
            console.print(f"   [green]✓[/green] Sent active markets alert to Discord")

        except Exception as e:
            console = Console()
            console.print(f"   [yellow][WARN] Failed to send active markets alert: {str(e)[:50]}[/yellow]")

    def get_market_odds(self, symbol: str, market_type: str) -> Optional[UnhedgedOdds]:
        """
        Get odds for a symbol (with caching)

        Args:
            symbol: Trading pair symbol
            market_type: 'binary' or 'interval'

        Returns:
            UnhedgedOdds object or None
        """
        # Get market ID from config
        manual_markets = self.config.get('unhedged', {}).get('manual_markets', {})
        market_id = manual_markets.get(symbol)

        if not market_id:
            return None

        # Check cache (5 minute cache)
        cache_key = f"{symbol}_{market_type}"
        current_time = time.time()

        if cache_key in self.odds_cache:
            cache_time = self.odds_cache_time.get(cache_key, 0)
            if current_time - cache_time < 300:  # 5 minutes
                return self.odds_cache[cache_key]

        # Scrape fresh odds
        try:
            odds = self.odds_scraper.scrape_market_odds(market_id, market_type)
            if odds:
                self.odds_cache[cache_key] = odds
                self.odds_cache_time[cache_key] = current_time
                return odds
        except Exception as e:
            pass

        return None

    def adjust_confidence_with_odds(self, signal_analysis: Dict, odds: UnhedgedOdds) -> tuple[float, List[str]]:
        """
        Adjust confidence based on crowd odds

        Args:
            signal_analysis: Signal analysis
            odds: UnhedgedOdds object

        Returns:
            Tuple of (adjusted_confidence, additional_reasons)
        """
        base_confidence = signal_analysis['confidence']
        signal = signal_analysis['signal']

        additional_reasons = []
        adjusted_confidence = base_confidence

        # Check crowd alignment
        if odds.is_crowd_aligned(signal):
            # Crowd agrees! Slight confidence boost
            adjusted_confidence = min(95, base_confidence + 3)
            additional_reasons.append(f"📊 Crowd agrees ({odds.get_outcome_pct(signal):.0f}% {signal})")

            # Check sentiment strength
            strength = odds.get_sentiment_strength()
            if strength in ['VERY_STRONG', 'STRONG']:
                adjusted_confidence = min(95, base_confidence + 5)
                additional_reasons.append(f"🔥 Strong {strength.lower()} crowd sentiment")

        elif odds.is_contrarian_opportunity(signal):
            # Crowd against signal - could be contrarian play
            additional_reasons.append(f"🔄 CONTRARIAN: Crowd {odds.get_winning_outcome()} ({odds.get_outcome_pct(odds.get_winning_outcome()):.0f}%), bot {signal}")

            # Don't adjust confidence - keep original for contrarian plays
            # User can decide if they want to take the contrarian bet
        else:
            # Neutral - slight crowd bias but not strong
            crowd_outcome = odds.get_winning_outcome()
            crowd_pct = odds.get_outcome_pct(crowd_outcome)
            additional_reasons.append(f"📊 Crowd leans {crowd_outcome} ({crowd_pct:.0f}%)")

        return adjusted_confidence, additional_reasons

    def analyze_interval_market(self, symbol: str) -> Dict:
        """
        Analyze symbol for interval/price range market (LOW/MID/HIGH)

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with interval signal analysis
        """
        if not self.interval_generator:
            return None

        # Get current price
        current_price = self.market_monitor.get_current_price(symbol)
        if not current_price:
            return {'error': 'Could not fetch current price', 'symbol': symbol}

        # Predict price at target time (usually 2 hours for interval markets)
        interval_config = self.config.get('interval_markets', {})
        target_minutes = interval_config.get('target_minutes', 120)  # Default 2 hours

        prediction = self.interval_generator.predict_price_at_time(
            symbol,
            current_price,
            target_minutes
        )

        if prediction.get('confidence', 0) < 50:
            return {'error': 'Low confidence prediction', 'symbol': symbol}

        # Get volatility for result (always needed)
        volatility = prediction.get('volatility', 2)

        # Get price ranges from scraped Unhedged interval market (if available)
        active_market = self.find_matching_market(symbol, market_type='interval')

        if active_market:
            # Use scraped ranges from Unhedged
            low_threshold = active_market.low_threshold or active_market.mid_threshold_low
            high_threshold = active_market.high_threshold or active_market.mid_threshold_high

            if not (low_threshold and high_threshold):
                # Fallback to calculated thresholds
                range_percent = volatility * 1.5
                low_threshold = current_price * (1 - range_percent / 100)
                high_threshold = current_price * (1 + range_percent / 100)
        else:
            # No interval market found, calculate thresholds
            range_percent = volatility * 1.5
            low_threshold = current_price * (1 - range_percent / 100)
            high_threshold = current_price * (1 + range_percent / 100)

        # Classify into LOW/MID/HIGH
        interval_signal = self.interval_generator.classify_interval(
            prediction,
            low_threshold,
            high_threshold
        )

        # Combine with metadata
        result = {
            'symbol': symbol,
            'signal': interval_signal['interval'],
            'signal_type': interval_signal['interval_type'],
            'confidence': interval_signal['confidence'],
            'current_price': current_price,
            'predicted_price': interval_signal['predicted_price'],
            'interval_description': interval_signal['interval_description'],
            'low_threshold': low_threshold,
            'high_threshold': high_threshold,
            'secondary': interval_signal['secondary'],
            'reasons': interval_signal['reasoning'],
            'timestamp': prediction['timestamp'],
            'is_interval': True,
            'target_minutes': target_minutes,
            'volatility': volatility
        }

        return result

    def check_and_alert_interval(self, interval_analysis: Dict):
        """
        Check and send alert for interval signal

        Args:
            interval_analysis: Interval signal analysis dictionary
        """
        if not interval_analysis or interval_analysis.get('error'):
            return

        symbol = interval_analysis['symbol']
        confidence = interval_analysis['confidence']
        min_conf = self.config.get('interval_markets', {}).get('min_confidence', 70)

        # Check if signal meets minimum confidence
        if confidence < min_conf:
            return

        # CHECK: Interval market active window
        # Interval markets: 2-hour duration, close at XX+1:50, resolve at XX+2:00
        # At XX:50-XX:00, the interval market is CLOSED
        current_min = time.localtime().tm_min
        current_hour = time.localtime().tm_hour

        # Interval markets closed at XX:50-XX:00 (of the second hour)
        # For example: 11:00 market closes at 12:50, resolves at 13:00
        # So at 12:50-13:00, market is CLOSED/RESOLVED
        if current_min >= 50:
            self.console.print(f"   [dim][SKIP] {symbol}: Interval market CLOSED (betting ends at XX:50)[/dim]")
            return

        # Skip if market just resolved (XX:00-XX:05)
        if current_min < 5:
            self.console.print(f"   [dim][SKIP] {symbol}: Interval market RESOLVED[/dim]")
            return

        # Market is ACTIVE
        status_msg = f"{50 - current_min} min left" if current_min >= 30 else "ACTIVE"

        # CHECK: Find the BEST matching INTERVAL market for this symbol
        active_market = self.find_matching_market(symbol, market_type='interval')

        if active_market:
            # CRITICAL: Check if this SPECIFIC market is still active
            if not active_market.is_still_active():
                self.console.print(f"   [dim][SKIP] {symbol}: Interval market already resolved[/dim]")
                return

            # Market is still active - add link and info
            interval_analysis['market_link'] = active_market.url
            interval_analysis['market_id'] = active_market.market_id

            # Add time until resolved
            minutes_left = active_market.get_time_until_resolved_minutes()
            if minutes_left is not None:
                status_msg = f"{minutes_left} min left"
                interval_analysis['time_until_resolved'] = f"{minutes_left} min"

                # CHECK: Optimal time window for interval markets
                # Interval: 2-hour duration, optimal is CLOSE to resolution (trend clearer)
                # Too early: > 80 min left (trend not yet established)
                # Too close: < 15 min left (market closing)
                min_time_interval = self.config.get('min_time_interval', 15)
                max_time_interval = self.config.get('max_time_interval', 80)

                if minutes_left < min_time_interval:
                    self.console.print(f"   [dim][SKIP] {symbol}: Only {minutes_left} min left (market closing)[/dim]")
                    return
                elif minutes_left > max_time_interval:
                    self.console.print(f"   [dim][SKIP] {symbol}: {minutes_left} min left (too early, trend not yet established)[/dim]")
                    return
                # Optimal: 15-80 min left (closer to resolution = more certain!)
        else:
            # No time data available - skip to be safe
            self.console.print(f"   [dim][SKIP] {symbol}: No time data available[/dim]")
            return

        # CHECK: Get crowd odds from Unhedged (interval markets)
        try:
            odds = self.get_market_odds(symbol, 'interval')
            if odds:
                # Adjust confidence based on crowd sentiment
                adjusted_confidence, additional_reasons = self.adjust_confidence_with_odds(interval_analysis, odds)

                # Update confidence
                interval_analysis['original_confidence'] = interval_analysis['confidence']
                interval_analysis['confidence'] = adjusted_confidence
                interval_analysis['crowd_odds'] = {
                    'low_pct': odds.low_pct,
                    'mid_pct': odds.mid_pct,
                    'high_pct': odds.high_pct
                }
                interval_analysis['sentiment_strength'] = odds.get_sentiment_strength()

                # Add crowd reasons
                if 'reasons' in interval_analysis:
                    interval_analysis['reasons'].extend(additional_reasons)
                else:
                    interval_analysis['reasons'] = additional_reasons

                confidence = adjusted_confidence

                # Re-check min confidence
                if confidence < min_conf:
                    self.console.print(f"   [dim][SKIP] {symbol}: Adjusted confidence {adjusted_confidence:.1f}% below threshold[/dim]")
                    return

        except Exception as e:
            pass  # If odds scraping fails, continue with original confidence

        # Add market info to interval analysis
        interval_analysis['market_status'] = status_msg

        # Check cooldown (interval signals use separate cooldown key)
        cooldown_key = f"{symbol}_interval"
        last_time = self.last_alerts.get(cooldown_key, 0)
        cooldown = 120  # 2 minutes cooldown

        if time.time() - last_time < cooldown:
            return

        # Send alert
        signal = interval_analysis['signal']
        self.console.print(f"   [cyan][INTERVAL] {symbol}: {signal} (Confidence: {confidence}%) - {status_msg}[/cyan]")
        self.alert_manager.send_alert(interval_analysis)
        self.last_alerts[cooldown_key] = time.time()

    def create_summary_table(self, all_signals):
        """Create ultimate summary table"""
        table = Table(
            title="[bold magenta]ULTIMATE Crypto Signal Bot[/bold magenta] 🚀\n[dim]All-Mode Analysis: Technical + ML + Sentiment + Correlation + Funding[/dim]",
            box=box.DOUBLE_EDGE
        )

        table.add_column("Symbol", style="cyan bold", width=10)
        table.add_column("Signal", style="bold", width=15)
        table.add_column("Confidence", width=10)
        table.add_column("Tech", width=8)
        table.add_column("ML", width=8)
        table.add_column("Sentiment", width=10)
        table.add_column("Funding", width=10)

        for symbol, analysis in all_signals.items():
            if not analysis or analysis.get('error'):
                table.add_row(symbol, "[dim]No data[/dim]", "-", "-", "-", "-", "-")
                continue

            signal = analysis['signal']
            signal_type = analysis.get('signal_type')

            # Check if it's a HOLD signal (both string and enum)
            is_hold = (signal == SignalType.HOLD.value or
                      signal_type == SignalType.HOLD or
                      'HOLD' in signal.upper())

            if 'ULTIMATE YES' in signal:
                signal_style = "[bold bright_magenta]ULTIMATE YES[/bold bright_magenta]"
            elif 'STRONG YES' in signal:
                signal_style = "[bold green]STRONG YES[/bold green]"
            elif 'YES' in signal:
                signal_style = "[green]YES[/green]"
            elif 'ULTIMATE NO' in signal:
                signal_style = "[bold bright_red]ULTIMATE NO[/bold bright_red]"
            elif 'STRONG NO' in signal:
                signal_style = "[bold red]STRONG NO[/bold red]"
            elif 'NO' in signal:
                signal_style = "[red]NO[/red]"
            else:
                # HOLD or no signal = show as dash (not a betting signal)
                signal_style = "[dim]NO SIGNAL[/dim]"

            # For NO SIGNAL (HOLD), show dash instead of confidence
            if is_hold:
                conf_str = "-"
            else:
                conf = analysis['confidence']
                conf_str = f"{conf}%"

            # Module scores
            combined = analysis.get('combined_scores', {})
            signals = combined.get('module_signals', {})

            tech_score = "✓" if signals.get('technical', 0.5) > 0.6 else ("×" if signals.get('technical', 0.5) < 0.4 else "≈")
            ml_score = "✓" if signals.get('ml', 0.5) > 0.6 else ("×" if signals.get('ml', 0.5) < 0.4 else "≈")
            sent_score = "✓" if signals.get('sentiment', 0.5) > 0.6 else ("×" if signals.get('sentiment', 0.5) < 0.4 else "≈")
            fund_score = "✓" if signals.get('funding', 0.5) > 0.6 else ("×" if signals.get('funding', 0.5) < 0.4 else "≈")

            table.add_row(
                symbol,
                signal_style,
                conf_str,
                tech_score,
                ml_score,
                sent_score,
                fund_score
            )

        return table

    def display_detailed_analysis(self, analysis):
        """Display detailed ultimate analysis"""
        if not analysis or analysis.get('error'):
            return

        symbol = analysis['symbol']
        signal = analysis['signal']
        confidence = analysis['confidence']

        # Build detailed panel
        lines = []
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")
        lines.append(f"[bold white]ULTIMATE ANALYSIS: {symbol}[/bold white]")
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")
        lines.append("")
        lines.append(f"[bold {self._get_signal_color(signal)}]SIGNAL: {signal}[/bold {self._get_signal_color(signal)}]")
        lines.append(f"[bold white]CONFIDENCE: {confidence}%[/bold white]")
        lines.append("")

        # Module breakdown
        analyses = analysis.get('analyses', {})

        lines.append("[bold yellow]📊 Module Breakdown:[/bold yellow]")

        # Technical
        tech = analyses.get('technical', {})
        if tech and 'error' not in tech:
            lines.append(f"  🔬 Technical: {tech.get('signal', 'N/A')} ({tech.get('confidence', 0)}%)")
            lines.append(f"     Trend: {tech.get('trend_strength', 'N/A')}")

        # ML
        ml = analyses.get('ml', {})
        if ml and 'error' not in ml:
            lines.append(f"  🤖 ML: {ml.get('prediction', 'N/A')} ({ml.get('ml_confidence', 0)}%)")
            patterns = ml.get('patterns_detected', [])
            if patterns:
                lines.append(f"     Patterns: {', '.join(patterns)}")

        # Sentiment
        sent = analyses.get('sentiment', {})
        if sent and 'error' not in sent:
            lines.append(f"  😊 Sentiment: {sent.get('signal', 'N/A')} (FG: {sent.get('fear_greed', 'N/A')})")

        # Correlation
        corr = analyses.get('correlation', {})
        if corr and 'error' not in corr:
            btc_inf = corr.get('btc_influence', {})
            lines.append(f"  🔗 BTC: {btc_inf.get('trading_implication', 'N/A')}")

        # Funding
        fund = analyses.get('funding', {})
        if fund and 'error' not in fund:
            funding_rate = fund.get('funding_rate')
            if funding_rate is not None:
                lines.append(f"  💰 Funding: {fund.get('funding_sentiment', 'N/A')} ({funding_rate:.4f})")
            else:
                lines.append(f"  💰 Funding: {fund.get('funding_sentiment', 'N/A')}")

        lines.append("")

        # Reasons
        reasons = analysis.get('reasons', [])[:5]
        if reasons:
            lines.append("[bold yellow]📋 Key Reasons:[/bold yellow]")
            for reason in reasons:
                lines.append(f"  • {reason}")

        lines.append("")

        # Actionable advice
        advice = analysis.get('actionable_advice', {})
        if advice:
            lines.append("[bold green]💡 Trading Advice:[/bold green]")
            lines.append(f"  Action: {advice.get('action', 'N/A')}")
            lines.append(f"  Position Size: {advice.get('position_size', 'N/A')}")
            if advice.get('risk_warning'):
                lines.append(f"  [bold red]⚠️  Risk: {'; '.join(advice['risk_warning'])}[/bold red]")

        lines.append("")
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")

        panel_text = "\n".join(lines)
        panel = Panel(panel_text, border_style="magenta")
        self.console.print(panel)

    def _get_signal_color(self, signal):
        """Get color for signal"""
        if 'YES' in signal:
            return "green"
        elif 'NO' in signal:
            return "red"
        else:
            return "yellow"

    def auto_scrape_market_ids(self):
        """Automatically scrape Unhedged market IDs and update config"""
        import yaml

        self.console.print("[dim]🔍 Auto-scraping Unhedged market IDs...[/dim]")

        try:
            from bs4 import BeautifulSoup
            import re
            import time
            import subprocess
            import sys

            # Run scrape in subprocess to avoid stdout conflicts
            result = subprocess.run(
                [sys.executable, '-c', '''
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
import time

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--log-level=3")
driver = webdriver.Chrome(options=options)

driver.get("https://unhedged.gg/markets?category=crypto&sort=newest")
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(5)

html = driver.page_source
soup = BeautifulSoup(html, "html.parser")
cards = soup.find_all("a", href=re.compile(r"/markets/"))

symbol_map = {}
for card in cards:
    href = card.get("href", "")
    mid = href.replace("/markets/", "") if href else ""
    title_elem = card.find("h3")
    title = title_elem.get_text(strip=True) if title_elem else ""
    title_lower = title.lower()

    if "canton" in title_lower or " cc " in title.lower():
        sym = "CCUSDT"
    elif "btc" in title_lower or "bitcoin" in title_lower:
        sym = "BTCUSDT"
    elif "eth" in title_lower or "ethereum" in title_lower:
        sym = "ETHUSDT"
    elif "sol" in title_lower or "solana" in title_lower:
        sym = "SOLUSDT"
    else:
        continue

    if "above" in title_lower and mid:
        symbol_map[sym] = mid

driver.quit()

# Output as JSON
import json
print(json.dumps(symbol_map))
'''],
                capture_output=True,
                text=True,
                timeout=60,
                cwd='C:/Codingers/crypto-signal-bot'
            )

            if result.returncode == 0:
                import json
                symbol_map = json.loads(result.stdout.strip().split('\n')[-1])

                if symbol_map:
                    self.console.print(f"  [green]✓[/green] Found {len(symbol_map)} market IDs")

                    # Update config
                    self.config.setdefault('unhedged', {})['manual_markets'] = symbol_map

                    # Update bet preparer
                    if self.bet_preparer:
                        self.bet_preparer.manual_markets = symbol_map

                    # Update config file
                    try:
                        with open('config.yaml', 'r') as f:
                            config = yaml.safe_load(f)
                        config.setdefault('unhedged', {})['manual_markets'] = symbol_map
                        with open('config.yaml', 'w') as f:
                            yaml.dump(config, f, default_flow_style=False)
                    except:
                        pass

                    # Show found markets
                    for symbol, mid in symbol_map.items():
                        self.console.print(f"    [cyan]{symbol}:[/cyan] {mid[:25]}...")
                else:
                    self.console.print("  [yellow]⚠ No markets found[/yellow]")
            else:
                self.console.print("  [yellow]⚠ Scrape failed, using cached IDs[/yellow]")

        except Exception as e:
            self.console.print(f"  [yellow]⚠ Auto-scrape failed: {str(e)[:50]}[/yellow]")
            self.console.print("  [dim]Using cached market IDs from config...[/dim]")

    def prepare_bets_from_signals(self, all_signals: Dict) -> List[Dict]:
        """Prepare bets from all signals - ONLY FOR ACTIVE MARKETS"""
        if not self.bet_preparer:
            return []

        prepared_bets = []
        for symbol, analysis in all_signals.items():
            if analysis and not analysis.get('error'):
                # CRITICAL: Check if market is still active before preparing bet
                # Find active market for this symbol
                active_market = self.find_matching_market(symbol)

                if not active_market or not active_market.is_still_active():
                    # Market not found or already resolved - SKIP
                    self.console.print(f"   [dim][SKIP BET] {symbol}: No active market found[/dim]")
                    continue

                # Prepare bet only if market is active
                prepared_bet = self.bet_preparer.prepare_bet_from_signal(analysis)
                if prepared_bet:
                    # Update market link to active market
                    prepared_bet['market_link'] = active_market.url
                    prepared_bets.append(prepared_bet)

        return prepared_bets

    def display_prepared_bets(self, prepared_bets: List[Dict]):
        """Display prepared bets in console"""
        if not prepared_bets:
            self.console.print("[dim]No bets prepared (confidence < 75% or no matching markets)[/dim]")

            # Debug: Show what's happening
            if self.unhedged_client:
                self.console.print("\n[dim]🔍 Debug: Checking Unhedged API...[/dim]")
                markets = self.unhedged_client.get_markets()
                if 'error' in markets:
                    self.console.print(f"[yellow]⚠️ Unhedged API Error: {markets['error']}[/yellow]")
                    self.console.print("\n[bold cyan]💡 To enable semi-automated betting:[/bold cyan]")
                    self.console.print("1. Go to https://unhedged.gg and open a market for your symbol")
                    self.console.print("2. Copy the market ID from the URL (e.g., /market/btc-price-3pm)")
                    self.console.print("3. Add it to config.yaml under unhedged.manual_markets:")
                    help_text = """   unhedged:
     manual_markets:
       \"BTCUSDT\": \"btc-price-3pm\"
       \"ETHUSDT\": \"eth-price-3pm\""""
                    self.console.print(help_text)
                else:
                    active_crypto = self.unhedged_client.get_active_crypto_markets()
                    self.console.print(f"[dim]✓ Found {len(active_crypto)} active crypto markets[/dim]")
                    if active_crypto:
                        self.console.print("[dim]Sample markets:[/dim]")
                        for m in active_crypto[:3]:
                            self.console.print(f"[dim]  - {m.get('name', 'N/A')}[/dim]")
            return

        self.console.print("\n[bold bright_yellow]🎯 BETTING OPPORTUNITIES[/bold bright_yellow]\n")

        for i, bet in enumerate(prepared_bets, 1):
            self.console.print(f"[bold cyan]#{i}. {bet.get('symbol', 'N/A')}[/bold cyan]")
            self.console.print(f"   Signal: [bold {self._get_signal_color(bet.get('signal', ''))}]{bet.get('signal', 'N/A')}[/bold {self._get_signal_color(bet.get('signal', ''))}]")
            self.console.print(f"   Confidence: [bold]{bet.get('confidence', 0)}%[/bold]")
            self.console.print(f"   Outcome: [bold]{bet.get('outcome', 'N/A')}[/bold]")
            self.console.print(f"   Amount: [bold green]${bet.get('amount', 0)}[/bold green]")
            self.console.print(f"\n   [bold cyan]🔗 Open Market:[/bold cyan]")
            self.console.print(f"   {bet.get('market_link', 'N/A')}")
            self.console.print("")

    def send_prepared_bets_to_discord(self, prepared_bets: List[Dict]):
        """Send prepared bets to Discord"""
        if not prepared_bets or not self.alert_manager:
            return

        discord_config = self.config.get('alerts', {}).get('discord', {})
        if not discord_config.get('enabled', False):
            return

        webhook_url = discord_config.get('webhook_url', '')
        if not webhook_url:
            return

        username = discord_config.get('username', 'Unhedged Bot')
        avatar_url = discord_config.get('avatar_url', '')

        for bet in prepared_bets:
            # Format bet message for Discord with link
            message = f"""🎯 **Betting Opportunity** - {bet.get('symbol', 'N/A')}

**Signal:** {bet.get('signal', 'N/A')}
**Confidence:** {bet.get('confidence', 0)}%
**Outcome:** {bet.get('outcome', 'N/A')}
**Amount:** ${bet.get('amount', 0)}

**🔗 Open Market:** {bet.get('market_link', 'N/A')}

*Click the link above to place your bet!*"""

            # Send via webhook
            try:
                import requests
                data = {"content": message, "username": username}

                if avatar_url:
                    data["avatar_url"] = avatar_url

                response = requests.post(webhook_url, json=data, timeout=5)
                response.raise_for_status()

                print(f"✓ Discord alert sent for {bet.get('symbol', 'N/A')}")
            except Exception as e:
                print(f"⚠️ Failed to send Discord alert: {e}")

    def run_once(self):
        """Run analysis once"""
        self.console.print("\n[bold bright_magenta]ULTIMATE Mode - Full Analysis[/bold bright_magenta] 🚀\n")

        # Auto-scrape market IDs if Unhedged enabled
        if self.unhedged_client:
            self.auto_scrape_market_ids()
            self.console.print("")

        # Test connections first
        self.console.print("[bold]🔍 Testing API Connections...[/bold]")

        # Test Bybit/Binance
        self.console.print("  [dim]Testing Bybit/Binance API...[/dim]", end="\r")
        try:
            test_df = self.market_monitor.get_klines('BTCUSDT', limit=1)
            if test_df is not None and len(test_df) > 0:
                self.console.print("  [green]✓[/green] [dim]Bybit/Binance API - OK[/dim]")
            else:
                self.console.print("  [yellow]⚠[/yellow] [dim]Bybit/Binance API - No data (using demo)[/dim]")
        except Exception as e:
            self.console.print(f"  [red]✗[/red] [dim]Bybit/Binance API - ERROR: {str(e)[:50]}[/dim]")

        # Test Unhedged
        if self.unhedged_client:
            self.console.print("  [dim]Testing Unhedged API...[/dim]", end="\r")
            try:
                unhedged_test = self.unhedged_client.get_markets()
                if 'error' in unhedged_test:
                    self.console.print(f"  [yellow]⚠[/yellow] [dim]Unhedged API - {unhedged_test['error'][:50]}[/dim]")
                else:
                    self.console.print("  [green]✓[/green] [dim]Unhedged API - OK[/dim]")
            except Exception as e:
                self.console.print(f"  [red]✗[/red] [dim]Unhedged API - ERROR: {str(e)[:50]}[/dim]")

        self.console.print("")
        self.console.print("📡 Fetching data and running all analysis modules...")

        all_signals = {}
        errors = {}

        for symbol in self.market_monitor.symbols:
            self.console.print(f"   [cyan]{symbol}[/cyan]...", end="\r")
            try:
                signal = self.analyze_symbol(symbol)
                if signal and signal.get('error'):
                    errors[symbol] = f"Analysis error: {signal.get('error', 'Unknown')}"
                all_signals[symbol] = signal
            except Exception as e:
                errors[symbol] = str(e)
                all_signals[symbol] = None

        self.console.print("")  # New line after progress

        # Show errors if any
        if errors:
            self.console.print("\n[bold red]⚠️  Errors encountered:[/bold red]")
            for symbol, error in errors.items():
                self.console.print(f"  [yellow]{symbol}:[/yellow] {error}")
            self.console.print("")

        # Show summary table
        table = self.create_summary_table(all_signals)
        self.console.print(table)

        # Show detailed for high confidence
        self.console.print("\n[bold]📨 Detailed Analysis (Confidence ≥ 75%):[/bold]\n")

        for symbol, analysis in all_signals.items():
            if analysis and analysis.get('confidence', 0) >= 75:
                self.display_detailed_analysis(analysis)
                self.check_and_alert(analysis)

        # Prepare bets (DISABLED: Use signal alerts instead)
        # if self.bet_preparer:
        #     prepared_bets = self.prepare_bets_from_signals(all_signals)
        #     self.display_prepared_bets(prepared_bets)
        #     self.send_prepared_bets_to_discord(prepared_bets)

    def run_continuous(self):
        """Run continuous monitoring with multi-timeframe analysis"""
        # Check multi-timeframe settings
        mtf_config = self.config.get('multi_timeframe', {})
        mtf_enabled = mtf_config.get('enabled', True)
        timeframes = mtf_config.get('timeframes', ['5m', '15m', '1h'])

        # Check smart timing
        smart_timing = self.config.get('smart_timing', {})
        avoid_resolved = smart_timing.get('avoid_during_resolve', True)
        resolved_window = smart_timing.get('resolved_window', {'start': 50, 'end': 5})

        # Check interval markets
        interval_config = self.config.get('interval_markets', {})
        interval_enabled = interval_config.get('enabled', False)
        interval_hours = interval_config.get('hours', [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23])  # All odd hours

        self.console.print("\n[bold bright_magenta]ULTIMATE Mode - Multi-Timeframe Analysis[/bold bright_magenta] 🚀")
        if mtf_enabled:
            self.console.print(f"[dim]Timeframes: {', '.join(timeframes)}[/dim]")
        if interval_enabled:
            hours_str = ', '.join([f'{h:02d}:00' for h in interval_hours])
            self.console.print(f"[dim]Interval Markets: Enabled (every 2h at odd hours)[/dim]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        if avoid_resolved:
            self.console.print(f"[yellow]⚠️  Smart Timing: Alerts skipped during market resolved window (XX:{resolved_window['start']:02d} - XX:0{resolved_window['end']})[/yellow]\n")

        self.running = True
        interval = self.config.get('display', {}).get('update_interval', 60)

        # INITIAL: Scrape active markets when bot starts
        self.console.print("\n[bold cyan]🔍 Scanning Unhedged for active markets...[/bold cyan]")
        active_markets = self.refresh_active_markets()

        if active_markets:
            self.send_active_markets_alert(active_markets)
        else:
            self.console.print("   [yellow]No active markets found or scraping failed[/yellow]")

        self.console.print("")

        try:
            while self.running:
                self.console.clear()

                # Current time and window status
                current_time = time.strftime('%H:%M:%S')
                current_min = time.localtime().tm_min
                in_resolved_window = current_min >= resolved_window['start'] or current_min < resolved_window['end']
                window_status = "[red]MARKET RESOLVED ❌[/red]" if in_resolved_window else "[green]BETTING OPEN ✅[/green]"

                self.console.print(
                    f"[bold bright_magenta]ULTIMATE[/bold bright_magenta] 🚀 | "
                    f"[dim]{current_time}[/dim] | "
                    f"{window_status} | "
                    f"[dim]Update: {interval}s[/dim]\n"
                )

                all_signals = {}

                # SKIP ANALYSIS during market resolved window (XX:50-XX:00)
                # Data is not accurate during this time
                if in_resolved_window:
                    self.console.print("[dim]⏸️  Market resolved window - Analysis paused[/dim]\n")

                    # Wait until next minute
                    secs_to_next = 60 - time.localtime().tm_sec
                    self.console.print(f"[dim]⏰ Resuming at XX:00 ({secs_to_next}s)[/dim]")

                    time.sleep(min(interval, secs_to_next))
                    continue  # Skip to next iteration

                # KING'S RULE: Alert at XX:45 (5 min before close = SAFE!)
                # Close XX:50, Resolve XX:00 = 10 min exposure
                # As long as we check 10-min volatility, XX:45 is SAFE!
                #
                # TIMING:
                # - Binary: 9:00 market → Close 9:50 → Alert at 9:45
                # - Interval: 9:00 market → Close 10:50 → Alert at 10:45
                if current_min == 45:
                    self.console.print("\n[bold yellow]⏰ OPTIMAL TIMING: XX:45 (5 min to close)[/bold yellow]\n")

                    # Binary markets (every hour)
                    for symbol in self.market_monitor.symbols:
                        signal = self.analyze_symbol_proper(symbol)  # Use PROPER signal generator
                        all_signals[symbol] = signal

                        # Only alert if bettable (EV > 0, passed buffer checks)
                        if signal.get('is_bettable', False):
                            self.check_and_alert_proper(signal)
                        else:
                            # Show why skipped
                            edge = signal.get('edge', 0) * 100
                            dist = signal.get('distance_to_strike', 0)
                            dist_dollars = signal.get('distance_dollars', 0)
                            buffer = signal.get('buffer_remaining', 0)
                            vol = signal.get('volatility_5m', 0) * 100
                            self.console.print(f"   [dim][SKIP BINARY] {symbol}: Edge={edge:.1f}%, Dist={dist:.1f}% (${dist_dollars:.2f}), Vol={vol:.1f}%[/dim]")
                            if buffer is not None:
                                if buffer <= 0:
                                    self.console.print(f"   [dim]        [NO-BET ZONE: Buffer ${buffer:.2f} < $100][/dim]")
                                else:
                                    self.console.print(f"   [dim]        Buffer: ${buffer:.2f}[/dim]")

                    # Interval markets (every 2 hours, at XX:45 of the CLOSING hour)
                    # Example: 9:00 market closes at 10:50, so alert at 10:45
                    if interval_enabled and self.interval_generator:
                        current_hour = time.localtime().tm_hour

                        # Interval markets close at XX:50 of odd+1 hours
                        # 9:00 market → 10:50 close → Alert at 10:45
                        # So we alert at even hours: 10, 12, 14, 16, 18, 20, 22, 0
                        closing_hours = [h for h in range(24) if h % 2 == 0]  # Even hours

                        if current_hour in closing_hours:
                            self.console.print("[cyan]📊 Checking interval markets...[/cyan]")

                            for symbol in self.market_monitor.symbols:
                                interval_signal = self.analyze_interval_market(symbol)
                                if interval_signal and not interval_signal.get('error'):
                                    # Check time constraints
                                    active_market = self.find_matching_market(symbol, market_type='interval')

                                    if active_market and active_market.is_still_active():
                                        minutes_left = active_market.get_time_until_resolved_minutes()

                                        # Only alert if 10-20 min left (optimal window)
                                        if 10 <= minutes_left <= 20:
                                            self.check_and_alert_interval(interval_signal)
                                        else:
                                            self.console.print(f"   [dim][SKIP INTERVAL] {symbol}: {minutes_left} min left (not optimal)[/dim]")
                                elif interval_signal.get('error'):
                                    self.console.print(f"   [dim][SKIP INTERVAL] {symbol}: {interval_signal.get('error', 'Unknown error')}[/dim]")
                else:
                    # Still run analysis for display, but don't alert
                    for symbol in self.market_monitor.symbols:
                        signal = self.analyze_symbol(symbol)
                        all_signals[symbol] = signal

                # Refresh active markets every hour at XX:05
                if current_min == 5:
                    self.console.print("\n[bold cyan]🔄 Hourly refresh: Scanning Unhedged for active markets...[/bold cyan]")
                    active_markets = self.refresh_active_markets()
                    if active_markets:
                        self.send_active_markets_alert(active_markets)

                    # Check resolved markets and update benchmark
                    self.console.print("\n[bold cyan]📊 Checking resolved markets...[/bold cyan]")
                    self.check_resolved_markets()

                    self.console.print("")

                table = self.create_summary_table(all_signals)
                self.console.print(table)

                # Prepare bets (DISABLED: Betting opportunity alerts disabled - use signal alerts instead)
                # if self.bet_preparer:
                #     prepared_bets = self.prepare_bets_from_signals(all_signals)
                #     if prepared_bets:
                #         self.console.print("\n[bold bright_yellow]🎯 Prepared Bets Available[/bold bright_yellow]")
                #         self.send_prepared_bets_to_discord(prepared_bets)

                # Show next check time (Option A: continuous monitoring)
                current_min = time.localtime().tm_min
                current_sec = time.localtime().tm_sec
                secs_to_next = 60 - current_sec
                self.console.print(f"\n[dim]⏰ Next check: {secs_to_next}s (continuous monitoring)[/dim]")

                time.sleep(interval)

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⏸️  Bot stopped[/yellow]")
            self.running = False

    def check_resolved_markets(self):
        """
        Check resolved markets and update results in tracker

        This should be run at XX:05 after markets resolve
        """
        self.console.print("\n[cyan]🔍 Checking resolved markets...[/cyan]")

        # Get pending bets
        pending = self.result_tracker.get_pending_bets()

        if not pending:
            self.console.print("  [dim]No pending bets[/dim]")
            return

        self.console.print(f"  Found {len(pending)} pending bets")

        # For each pending bet, check if market is resolved
        updated = 0
        for bet in pending:
            try:
                symbol = bet['symbol']
                market_id = bet['market_id']
                signal = bet['signal']
                target_price = bet['target_price']
                predicted_price = bet.get('predicted_price')

                # Get current price to see outcome
                current_price = self.market_monitor.get_current_price(symbol)

                if not current_price:
                    continue

                # Determine outcome based on binary market
                if target_price:
                    # Binary market: above/below target
                    actual_result = 'YES' if current_price > target_price else 'NO'
                    is_win = (actual_result == signal)
                else:
                    self.console.print(f"  [dim]Skip {symbol}: No target price[/dim]")
                    continue

                # Update database
                import sqlite3
                conn = sqlite3.connect(self.result_tracker.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE bets
                    SET actual_result = ?, is_win = ?
                    WHERE id = ?
                """, (actual_result, is_win, bet['id']))
                conn.commit()
                conn.close()

                updated += 1

                # Show result
                result_str = "[green]WIN[/green]" if is_win else "[red]LOSS[/red]"
                self.console.print(f"  {symbol}: {signal} → {actual_result} ({result_str})")

            except Exception as e:
                self.console.print(f"  [dim]Error updating {bet.get('symbol', 'unknown')}: {str(e)[:30]}[/dim]")
                continue

        self.console.print(f"\n  [green]✓ Updated {updated} resolved bets[/green]")

        # Show benchmark summary
        self.console.print("\n[cyan]📊 Benchmark Summary:[/cyan]")
        latest = self.result_tracker.get_latest_benchmark()

        if latest.get('prediction_time'):
            self.console.print(f"  Predictions at: {latest['prediction_time']}")
            self.console.print(f"  Resolved: {latest['resolved']}/{latest['resolved'] + latest['pending']}")
            self.console.print(f"  Win Rate: {latest['win_rate']:.1f}%")

            # Show each prediction
            for pred in latest['predictions']:
                status = pred['status']
                if status == 'resolved':
                    status_str = "[green]✓[/green]" if pred['is_win'] else "[red]✗[/red]"
                else:
                    status_str = "[yellow]⏳[/yellow]"

                self.console.print(f"    {status_str} {pred['symbol']}: {pred['signal']}")

    def show_benchmark(self, hours: int = 24):
        """Show benchmark summary"""
        self.console.print(f"\n[bold cyan]📊 BENCHMARK - Last {hours} hours[/bold cyan]\n")
        self.result_tracker.print_benchmark(hours=hours)

    def fetch_bet_history(self, days_back: int = 30):
        """
        Fetch bet history from Unhedged API and update tracker

        This syncs actual Unhedged results with our predictions for learning
        """
        unhedged_config = self.config.get('unhedged', {})
        api_key = unhedged_config.get('api_key', '')

        if not api_key:
            self.console.print("[red]No Unhedged API key found in config.yaml[/red]")
            return False

        self.console.print(f"\n[cyan]🔄 Fetching bet history from Unhedged API (last {days_back} days)...[/cyan]\n")

        try:
            fetcher = UnhedgedHistoryFetcher(api_key)
            fetcher.update_tracker_from_history(self.result_tracker, api_key)
            self.console.print("\n[green]✓ Bet history fetched and tracker updated![/green]")
            return True
        except Exception as e:
            self.console.print(f"\n[red]✗ Failed to fetch bet history: {str(e)}[/red]")
            return False

    def calibrate_model(self, days: int = 30):
        """
        Calculate calibration metrics from historical bets

        Shows how well our predictions match actual outcomes
        """
        self.console.print(f"\n[cyan]📊 Calculating calibration metrics (last {days} days)...[/cyan]\n")

        try:
            calibration = calculate_calibration_from_tracker(self.result_tracker, days)

            if not calibration:
                self.console.print("[yellow]⚠ No resolved bets found for calibration[/yellow]")
                self.console.print("[dim]Run with --history first to fetch bet history from Unhedged API[/dim]")
                return None

            # Print calibration report
            calibration.print_calibration_report()

            # Get calibration parameters
            params = calibration.get_calibration_params()

            # Save to file for use in signal generation
            import json
            with open('calibration_params.json', 'w') as f:
                json.dump(params, f, indent=2)

            self.console.print(f"\n[green]✓ Calibration parameters saved to calibration_params.json[/green]")

            return params

        except Exception as e:
            self.console.print(f"\n[red]✗ Calibration failed: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
            return None

    def show_stats(self, days: int = 7):
        """Show performance statistics from result tracker"""
        self.console.print(f"\n[cyan]📈 Performance Statistics (Last {days} days)[/cyan]\n")

        try:
            stats = self.result_tracker.get_stats(days=days)

            if not stats or stats.get('total_bets', 0) == 0:
                self.console.print("[yellow]⚠ No bets found in tracker[/yellow]")
                self.console.print("[dim]Run the bot to start tracking predictions, or use --history to fetch past results[/dim]")
                return

            # Overall stats
            self.console.print("[bold]Overall Performance:[/bold]")
            self.console.print(f"  Total Bets: {stats['total_bets']}")
            self.console.print(f"  Wins: {stats['wins']}")
            self.console.print(f"  Losses: {stats['losses']}")
            self.console.print(f"  Win Rate: [cyan]{stats['win_rate']*100:.1f}%[/cyan]")
            self.console.print(f"  Profit/Loss: [green]${stats['profit_loss']:.2f}[/green]" if stats['profit_loss'] >= 0 else f"  Profit/Loss: [red]${stats['profit_loss']:.2f}[/red]")
            self.console.print(f"  ROI: [cyan]{stats['roi']*100:.1f}%[/cyan]")
            self.console.print(f"  Avg Edge: {stats['avg_edge']*100:.1f}%\n")

            # By symbol breakdown
            by_symbol = stats.get('by_symbol', {})
            if by_symbol:
                self.console.print("[bold]Performance by Symbol:[/bold]")

                table = Table()
                table.add_column("Symbol", style="cyan")
                table.add_column("Bets", justify="right")
                table.add_column("Win Rate", justify="right")
                table.add_column("P&L", justify="right")
                table.add_column("ROI", justify="right")

                for symbol, symbol_stats in by_symbol.items():
                    pnl = symbol_stats['profit_loss']
                    pnl_style = "green" if pnl >= 0 else "red"

                    table.add_row(
                        symbol,
                        str(symbol_stats['total_bets']),
                        f"{symbol_stats['win_rate']*100:.1f}%",
                        f"[{pnl_style}]${pnl:.2f}[/{pnl_style}]",
                        f"{symbol_stats['roi']*100:.1f}%"
                    )

                self.console.print(table)

        except Exception as e:
            self.console.print(f"\n[red]✗ Failed to get stats: {str(e)}[/red]")
            import traceback
            traceback.print_exc()

    def run(self, once=False):
        """Run the bot"""
        if once:
            self.run_once()
        else:
            self.run_continuous()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Crypto Signal Bot - ULTIMATE Mode")

    parser.add_argument('--config', '-c', default='config.yaml')
    parser.add_argument('--symbols', '-s', nargs='+')
    parser.add_argument('--once', '-o', action='store_true')
    parser.add_argument('--demo', '-d', action='store_true')
    parser.add_argument('--scrape', action='store_true', help='Scrape Unhedged market IDs and update config')
    parser.add_argument('--history', action='store_true', help='Fetch bet history from Unhedged API and update tracker')
    parser.add_argument('--calibrate', action='store_true', help='Calculate calibration metrics and show recommendations')
    parser.add_argument('--stats', action='store_true', help='Show performance statistics from result tracker')
    parser.add_argument('--benchmark', action='store_true', help='Show benchmark summary (predictions vs results)')
    parser.add_argument('--check-resolved', action='store_true', help='Check resolved markets and update results')
    parser.add_argument('--calibration-days', type=int, default=30, help='Days to look back for calibration (default: 30)')
    parser.add_argument('--benchmark-hours', type=int, default=24, help='Hours to show for benchmark (default: 24)')

    args = parser.parse_args()

    # Handle --scrape flag separately (before bot init to avoid stdout issues)
    if args.scrape:
        from rich.console import Console
        console = Console()
        console.print("[bold yellow]🔍 Scraping Unhedged Market IDs...[/bold yellow]\n")
        scrape_market_ids_to_config()
        console.print("\n[green]✓ Done! You can now run the bot normally.[/green]")
        return

    # Initialize bot (needed for history, calibrate, stats commands)
    bot = CryptoSignalBotUltimate(config_path=args.config, demo_mode=args.demo)

    # Handle --history flag
    if args.history:
        success = bot.fetch_bet_history(days_back=args.calibration_days)
        if success:
            # After fetching history, automatically calibrate
            bot.console.print("\n[cyan]📊 Auto-calibrating model with new history...[/cyan]\n")
            bot.calibrate_model(days=args.calibration_days)
        return

    # Handle --calibrate flag
    if args.calibrate:
        bot.calibrate_model(days=args.calibration_days)
        return

    # Handle --stats flag
    if args.stats:
        bot.show_stats(days=args.calibration_days)
        return

    # Handle --benchmark flag
    if args.benchmark:
        bot.show_benchmark(hours=args.benchmark_hours)
        return

    # Handle --check-resolved flag
    if args.check_resolved:
        bot.check_resolved_markets()
        return

    if args.symbols:
        symbols = [f"{s}USDT" if not s.endswith('USDT') else s for s in args.symbols]
        bot.config['symbols'] = symbols
        bot.market_monitor.symbols = symbols

    try:
        bot.run(once=args.once)
    except KeyboardInterrupt:
        print("\n\n[!] Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n--- Full Traceback ---")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup Selenium driver
        print("\n[INFO] Cleaning up...")
        bot.market_monitor.cleanup()


if __name__ == "__main__":
    main()
