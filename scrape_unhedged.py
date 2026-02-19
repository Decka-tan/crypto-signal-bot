#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unhedged Market Scraper using Selenium
Scrapes market IDs from unhedged.gg with JavaScript rendering
"""

import sys
import io
import time
import re
import json
from datetime import datetime

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def scrape_unhedged_markets():
    """Scrape Unhedged markets using Selenium"""

    print("🔍 Unhedged Market Scraper (Selenium)")
    print("=" * 60)

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    driver = None

    try:
        print("📡 Starting Chrome driver...\n")

        # Create driver
        driver = webdriver.Chrome(options=chrome_options)

        # Navigate to Unhedged
        url = "https://unhedged.gg/markets?category=crypto&sort=newest"
        print(f"📡 Opening {url}...")

        driver.get(url)

        # Wait for page to load
        print("⏳ Waiting for page to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Wait extra time for JavaScript to load market data
        print("⏳ Waiting for market data to load (5 seconds)...")
        time.sleep(5)

        # Get page HTML after JavaScript execution
        html = driver.page_source

        print(f"✓ Page loaded: {len(html)} characters\n")

        # Save HTML
        with open('unhedged_rendered.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("💾 Saved to unhedged_rendered.html\n")

        # Extract market data
        print("🔍 Extracting market data...\n")

        # Method 1: Look for market data in window object
        market_data = driver.execute_script("""
            // Try to find market data in window object
            let results = [];

            // Check common window properties
            for (let key in window) {
                if (key.includes('__') || key.includes('data') || key.includes('DATA')) {
                    try {
                        let val = window[key];
                        if (typeof val === 'object' && val !== null) {
                            let str = JSON.stringify(val);
                            if (str.includes('market') || str.includes('BTC') || str.includes('ETH')) {
                                results.push({
                                    property: key,
                                    data: str.substring(0, 1000)
                                });
                            }
                        }
                    } catch(e) {}
                }
            }

            return results;
        """)

        if market_data:
            print(f"✓ Found {len(market_data)} potential data objects in window:")
            for item in market_data[:5]:
                print(f"  - window.{item['property']}")
                print(f"    Preview: {item['data'][:200]}...")
                print()

        # Method 2: Look for market cards/elements in DOM
        print("🔍 Searching for market elements in DOM...\n")

        # Look for elements with market-related content
        market_elements = driver.execute_script("""
            let results = [];

            // Look for elements containing market data
            let allElements = document.querySelectorAll('*');

            for (let elem of allElements) {
                let text = elem.textContent || '';

                // Check if element contains market-related text
                if (text.includes('above') || text.includes('price at') || text.includes('BTC') || text.includes('ETH')) {
                    // Check for data attributes
                    let attrs = {};
                    for (let attr of elem.attributes) {
                        if (attr.name.includes('data-') || attr.name.includes('id')) {
                            attrs[attr.name] = attr.value;
                        }
                    }

                    if (Object.keys(attrs).length > 0) {
                        results.push({
                            tag: elem.tagName,
                            text: text.substring(0, 100),
                            attrs: attrs
                        });

                        if (results.length >= 10) break;
                    }
                }
            }

            return results;
        """)

        if market_elements:
            print(f"✓ Found {len(market_elements)} market-related elements:")
            for elem in market_elements[:5]:
                print(f"  - <{elem['tag']}> {elem['text'][:50]}...")
                for attr, val in elem['attrs'].items():
                    print(f"      {attr}: {val}")
                print()

        # Method 3: Interception of network calls
        print("🔍 Monitoring network calls...\n")

        logs = driver.get_log('performance')

        api_calls = []
        for log in logs:
            try:
                message = json.loads(log['message'])
                method = message['message']['method']

                if method == 'Network.requestWillBeSent':
                    request = message['message']['params']['request']
                    url = request.get('url', '')

                    if 'api' in url.lower() or 'market' in url.lower():
                        api_calls.append({
                            'method': request.get('method'),
                            'url': url
                        })
            except:
                pass

        if api_calls:
            print(f"✓ Found {len(api_calls)} API calls:")
            for call in set(c['url'] for c in api_calls[:10]):
                print(f"  - {call}")
            print()

        # Method 4: Extract market IDs from URLs
        print("🔍 Extracting market IDs from page content...\n")

        market_ids = set()

        # Look for UUID patterns
        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        uuids = re.findall(uuid_pattern, html)
        market_ids.update(uuids)

        # Look for MongoDB ObjectId patterns
        mongo_pattern = r'[a-f0-9]{24}'
        mongo_ids = re.findall(mongo_pattern, html)
        market_ids.update(mongo_ids[:20])  # Limit

        if market_ids:
            print(f"✓ Found {len(market_ids)} potential IDs:")
            for mid in sorted(list(market_ids))[:15]:
                print(f"  - {mid}")
            if len(market_ids) > 15:
                print(f"  ... and {len(market_ids) - 15} more")
            print()

        # Method 5: Look for links to individual markets
        print("🔍 Finding market links...\n")

        market_links = driver.execute_script("""
            let links = [];

            // Find all links
            let allLinks = document.querySelectorAll('a[href*="market"]');

            for (let link of allLinks) {
                links.push({
                    href: link.href,
                    text: link.textContent.substring(0, 50)
                });

                if (links.length >= 20) break;
            }

            return links;
        """)

        if market_links:
            print(f"✓ Found {len(market_links)} market links:")
            for link in market_links[:10]:
                print(f"  - {link['href']}")
                print(f"    {link['text']}")
            print()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if driver:
            driver.quit()
            print("\n✓ Driver closed")


def main():
    success = scrape_unhedged_markets()

    if success:
        print("\n" + "=" * 60)
        print("✓ Scraping complete!")
        print("=" * 60)
        print("\n💡 Check unhedged_rendered.html for full HTML")
        print("💡 Look for market IDs in the output above")
    else:
        print("\n❌ Scraping failed")


if __name__ == "__main__":
    main()
