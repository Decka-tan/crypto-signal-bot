#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract market IDs from rendered Unhedged HTML
"""

import sys
import io
import re

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from bs4 import BeautifulSoup


def extract_market_data():
    """Extract market IDs and symbols from rendered HTML"""

    with open('unhedged_rendered.html', 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')

    # Find all market cards
    market_cards = soup.find_all('a', href=re.compile(r'/markets/'))

    print(f"Found {len(market_cards)} market cards\n")

    markets = []

    for card in market_cards:
        # Extract market ID from href
        href = card.get('href', '')
        market_id = href.replace('/markets/', '') if href else ''

        # Find the title/h3
        title_elem = card.find('h3')
        title = title_elem.get_text(strip=True) if title_elem else 'Unknown'

        # Find symbol tags (like "cc", "sol", etc.)
        symbol_tags = card.find_all('span', class_=re.compile(r'uppercase'))
        symbols = [s.get_text(strip=True).lower() for s in symbol_tags]

        markets.append({
            'id': market_id,
            'title': title,
            'symbols': symbols,
            'our_symbol': determine_symbol(title, symbols)
        })

    # Print results
    print("=" * 60)
    print("MARKETS FOUND")
    print("=" * 60 + "\n")

    for market in markets:
        print(f"Market ID: {market['id']}")
        print(f"Title: {market['title']}")
        print(f"Tags: {', '.join(market['symbols'])}")
        print(f"Our Symbol: {market['our_symbol']}")
        print()

    # Generate config
    print("=" * 60)
    print("CONFIG.YAML FORMAT")
    print("=" * 60 + "\n")

    print("unhedged:")
    print("  api_key: \"ak_rHWj55mvAzifWvuVnRZDkGcasjFwHwsshgZNpKXXVCIOHIYk\"")
    print("  enabled: true")
    print("  manual_markets:")

    for market in markets:
        if market['our_symbol'] and market['our_symbol'] != 'UNKNOWN':
            print(f"    \"{market['our_symbol']}\": \"{market['id']}\"  # {market['title']}")

    return markets


def determine_symbol(title, tags):
    """Determine our symbol format from title/tags"""

    title_lower = title.lower()

    # Check for CC/Canton
    if 'canton' in title_lower or 'cc' in tags:
        return 'CCUSDT'

    # Check for BTC
    if 'btc' in title_lower or 'bitcoin' in title_lower:
        return 'BTCUSDT'

    # Check for ETH
    if 'eth' in title_lower or 'ethereum' in title_lower:
        return 'ETHUSDT'

    # Check for SOL
    if 'sol' in title_lower or 'solana' in title_lower:
        return 'SOLUSDT'

    # Check tags
    for tag in tags:
        if tag == 'cc':
            return 'CCUSDT'
        elif tag == 'btc':
            return 'BTCUSDT'
        elif tag == 'eth':
            return 'ETHUSDT'
        elif tag == 'sol':
            return 'SOLUSDT'

    return 'UNKNOWN'


if __name__ == "__main__":
    extract_market_data()
