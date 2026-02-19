#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test scraping Unhedged with proper decompression
"""

import sys
import io
import re
import json
import gzip
from datetime import datetime

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
from bs4 import BeautifulSoup


def scrape_unhedged():
    """Scrape Unhedged with proper handling"""

    url = "https://unhedged.gg/markets?category=crypto&sort=newest"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    print(f"Fetching {url}...\n")

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        print(f"✓ Status: {response.status_code}")
        print(f"✓ Encoding: {response.encoding}")
        print(f"✓ Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
        print(f"✓ Content length: {len(response.content)} bytes\n")

        # Decompress if needed
        if response.headers.get('Content-Encoding') == 'gzip':
            content = gzip.decompress(response.content).decode('utf-8')
            print("✓ Decompressed gzip content\n")
        else:
            content = response.text
            print("✓ Using plain text\n")

        # Save for inspection
        with open('unhedged_page.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("💾 Saved to unhedged_page.html\n")

        # Look for data in script tags
        soup = BeautifulSoup(content, 'html.parser')

        print("🔍 Searching for data in script tags...\n")

        script_tags = soup.find_all('script')
        print(f"Found {len(script_tags)} script tags\n")

        # Look for specific data patterns
        data_patterns = [
            (r'window\.__INITIAL_STATE__\s*=\s*({.+?});', 'Initial State'),
            (r'window\.__DATA__\s*=\s*({.+?});', 'Window Data'),
            (r'__NUXT__\s*=\s*({.+?});', 'Nuxt Data'),
            (r'data-sveltekit-data="([^"]+)"', 'SvelteKit Data'),
            (r'"markets":\s*\[([^\]]+)\]', 'Markets Array'),
            (r'"market":\s*{([^}]+)}', 'Single Market'),
        ]

        for pattern, name in data_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                print(f"✓ Found {name}: {len(matches)} match(es)")
                for match in matches[:2]:
                    preview = str(match)[:200]
                    print(f"  Preview: {preview}...")
                print()

        # Look for API endpoints
        print("\n🔍 Searching for API endpoints...\n")

        api_patterns = [
            r'"https://[^"]*api[^"]*"',
            r'"/api/v?1?/[^"]*"',
            r'baseURL:\s*"([^"]+)"',
            r'apiUrl:\s*"([^"]+)"',
        ]

        apis = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, content)
            apis.update(matches)

        if apis:
            print(f"✓ Found {len(apis)} API endpoints:")
            for api in sorted(apis):
                print(f"  - {api}")
            print()

        # Look for market IDs
        print("\n🔍 Searching for market IDs...\n")

        id_patterns = [
            r'"id":\s*"([a-f0-9\-]{24,})"',  # MongoDB-style IDs
            r'"_id":\s*"([a-f0-9\-]{24,})"',
            r'"marketId":\s*"([a-f0-9\-]+)"',
            r'/market/([a-f0-9\-]{36})"',  # UUIDs
            r'data-market-id="([a-f0-9\-]+)"',
        ]

        market_ids = set()
        for pattern in id_patterns:
            matches = re.findall(pattern, content)
            market_ids.update(matches)

        if market_ids:
            print(f"✓ Found {len(market_ids)} market IDs:")
            for mid in sorted(list(market_ids))[:10]:
                print(f"  - {mid}")
            if len(market_ids) > 10:
                print(f"  ... and {len(market_ids) - 10} more")
        else:
            print("⚠️  No market IDs found in HTML")
            print("   Market data is probably loaded via JavaScript after page load")

        # Look for market-related text
        print("\n🔍 Searching for market keywords...\n")

        crypto_keywords = ['BTC', 'ETH', 'SOL', 'Canton', 'bitcoin', 'ethereum', 'solana']

        for keyword in crypto_keywords:
            if keyword.lower() in content.lower():
                # Find context around keyword
                idx = content.lower().find(keyword.lower())
                context = content[max(0, idx-50):min(len(content), idx+100)]
                print(f"✓ Found '{keyword}':")
                print(f"  ...{context}...")
                print()

        return content

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    scrape_unhedged()
