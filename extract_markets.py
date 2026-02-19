#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unhedged Market ID Extractor
Extracts market IDs from Unhedged.gg using browser automation
"""

import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import re
from typing import Dict, Optional

def try_common_api_endpoints(base_url: str = "https://unhedged.gg") -> Dict:
    """Try common API endpoints to find markets"""

    endpoints = [
        "/api/markets",
        "/api/v1/markets",
        "/api/market",
        "/api/v1/market",
        "/api/markets/list",
        "/api/v1/markets/list",
        "/markets/api",
        "/v1/markets",
        "/_app/immutable/data/markets.svelte",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    found = {}

    for endpoint in endpoints:
        url = base_url + endpoint
        try:
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                try:
                    data = response.json()
                    found[url] = data
                    print(f"✅ Found: {url}")
                    print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                except:
                    # Not JSON, might be HTML
                    content = response.text
                    if 'market' in content.lower():
                        print(f"⚠️  Possible HTML response: {url}")
                        found[url] = 'html'
        except Exception as e:
            pass

    return found

def search_js_bundles(base_url: str = "https://unhedged.gg") -> Dict:
    """
    Fetch main page and search for API endpoints in JavaScript bundles
    """
    try:
        response = requests.get(base_url, timeout=10)
        content = response.text

        # Look for API endpoints in the HTML/JS
        api_patterns = [
            r'/api/v?1?/?\w+',
            r'"api":\s*"[^"]+"',
            r'baseURL:\s*"[^"]+"',
            r'endpoint:\s*"[^"]+"',
        ]

        found_apis = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, content)
            found_apis.update(matches)

        return {
            'apis': list(found_apis),
            'js_bundles': re.findall(r'/_app/immutable/[^"]+\.js', content)
        }
    except Exception as e:
        return {'error': str(e)}

def inspect_market_page(market_slug: str = "btc") -> Dict:
    """
    Try to inspect a specific market page
    """
    url = f"https://unhedged.gg/market/{market_slug}"
    try:
        response = requests.get(url, timeout=10)
        content = response.text

        # Look for market data in scripts
        script_data = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)

        markets_found = []
        for script in script_data:
            if 'market' in script.lower() or 'btc' in script.lower():
                # Try to extract JSON data
                json_matches = re.findall(r'\{[^{}]*"[^"]*(?:market|id|symbol)[^"]*"[^{}]*\}', script)
                markets_found.extend(json_matches[:3])  # Limit to avoid spam

        return {
            'url': url,
            'status': response.status_code,
            'markets_found': markets_found[:5]  # Limit output
        }
    except Exception as e:
        return {'error': str(e)}

def main():
    """Main extraction function"""
    print("🔍 Unhedged Market ID Extractor")
    print("=" * 60)
    print()

    # Step 1: Try API endpoints
    print("📡 Step 1: Trying common API endpoints...")
    api_results = try_common_api_endpoints()

    if api_results:
        print(f"\n✅ Found {len(api_results)} potential endpoints!")
        for url, data in api_results.items():
            print(f"\n  {url}:")
            if isinstance(data, dict) and 'error' not in data:
                # Try to extract market IDs
                json_str = json.dumps(data)
                if 'BTC' in json_str or 'ETH' in json_str:
                    print(f"    ⚠️  Contains crypto references!")
                    # Print preview
                    print(f"    Preview: {json_str[:200]}...")
    else:
        print("❌ No API endpoints found")

    # Step 2: Search JS bundles
    print("\n📦 Step 2: Searching JavaScript bundles...")
    js_results = search_js_bundles()

    if js_results.get('apis'):
        print(f"✅ Found {len(js_results['apis'])} API references:")
        for api in js_results['apis'][:10]:
            print(f"  - {api}")

    if js_results.get('js_bundles'):
        print(f"\n✅ Found {len(js_results['js_bundles'])} JS bundles")
        print("   (These contain the actual API calls)")

    # Step 3: Inspect market pages
    print("\n🎯 Step 3: Inspecting market pages...")
    market_slugs = ['btc', 'eth', 'btc-price', 'btcusdt']

    for slug in market_slugs:
        result = inspect_market_page(slug)
        if result.get('status') == 200:
            print(f"✅ Found: /market/{slug}")
            if result.get('markets_found'):
                print(f"   Market data detected in page scripts")
        elif 'error' not in result:
            print(f"⚠️  Tried: /market/{slug} (status: {result.get('status', 'unknown')})")

    # Instructions
    print("\n" + "=" * 60)
    print("📝 MANUAL METHOD (RECOMMENDED)")
    print("=" * 60)
    print("""
Since Unhedged is a SPA (Single Page App), the best way is:

1. Open https://unhedged.gg in your browser
2. Open DevTools (F12) → Network tab
3. Filter by "Fetch/XHR"
4. Navigate to a market (e.g., BTC price)
5. Look for API calls in the Network tab
6. Click on the API call and check the Response
7. Copy the market ID from the response

Then add to config.yaml:

    unhedged:
      api_key: "your_key"
      manual_markets:
        "BTCUSDT": "market_id_from_network_tab"
        "ETHUSDT": "market_id_from_network_tab"

Or run get_market_ids.js in browser console for automatic extraction!
    """)

if __name__ == "__main__":
    main()
