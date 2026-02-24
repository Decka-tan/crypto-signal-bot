"""
Test Chainlink Price Feeds
Unhedged uses Chainlink for resolution, so this might be more accurate!

Sources to test:
1. Chainlink Data Feeds (direct)
2. CoinGecko (free API)
3. CoinMarketCap (free API)
4. Binance API (no Chrome needed)
"""

import requests
import time
from datetime import datetime

print("=" * 60)
print("CHAINLINK PRICE DATA TEST")
print("=" * 60)

# ============================================================================
# TEST 1: Binance API (Direct, no Chrome)
# ============================================================================
print("\n[1] Binance API (Direct HTTP Request)")
print("-" * 60)

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']

for symbol in symbols:
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        data = response.json()

        price = float(data.get('price', 0))
        print(f"  {symbol}: ${price:.6f}")
    except Exception as e:
        print(f"  {symbol}: FAILED - {str(e)[:40]}")

# ============================================================================
# TEST 2: Binance Klines (Historical data - no Chrome!)
# ============================================================================
print("\n[2] Binance Klines API (Candlestick data)")
print("-" * 60)

for symbol in symbols:
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': '5m',
            'limit': 10
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            latest = data[-1]
            open_price = float(latest[1])
            high = float(latest[2])
            low = float(latest[3])
            close = float(latest[4])
            volume = float(latest[5])

            print(f"  {symbol}: O=${open_price:.2f} H=${high:.2f} L=${low:.2f} C=${close:.2f}")
        else:
            print(f"  {symbol}: No data")
    except Exception as e:
        print(f"  {symbol}: FAILED - {str(e)[:40]}")

# ============================================================================
# TEST 3: Chainlink Data Feeds (via Binance Chain tokens)
# ============================================================================
print("\n[3] Chainlink Price Feeds (ETH Mainnet)")
print("-" * 60)
print("  Note: Chainlink feeds are on-chain, need RPC node")
print("  Alternative: Use coingecko API")

# ============================================================================
# TEST 4: CoinGecko API (Free, no rate limit issues)
# ============================================================================
print("\n[4] CoinGecko API (Free, reliable)")
print("-" * 60)

coingecko_ids = {
    'BTCUSDT': 'bitcoin',
    'ETHUSDT': 'ethereum',
    'SOLUSDT': 'solana',
    'CCUSDT': 'canton-network'  # Try to find Canton
}

for symbol, coin_id in coingecko_ids.items():
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if coin_id in data:
            price = data[coin_id]['usd']
            change_24h = data[coin_id].get('usd_24h_change', 0)
            print(f"  {symbol}: ${price:.6f} (24h: {change_24h:+.2f}%)")
        else:
            print(f"  {symbol}: Not found on CoinGecko")
    except Exception as e:
        print(f"  {symbol}: FAILED - {str(e)[:40]}")

# ============================================================================
# TEST 5: CryptoCompare API (Alternative)
# ============================================================================
print("\n[5] CryptoCompare API")
print("-" * 60)

for symbol in symbols:
    try:
        # Remove USDT suffix
        base = symbol.replace('USDT', '').lower()

        url = f"https://min-api.cryptocompare.com/data/pricehistogram"
        params = {
            'fsym': base,
            'tsym': 'USD',
            'limit': 10
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if 'Data' in data and data['Data']:
            latest = data['Data'][-1]
            price = latest['close']
            print(f"  {symbol}: ${price:.6f}")
        else:
            print(f"  {symbol}: No data")
    except Exception as e:
        print(f"  {symbol}: FAILED - {str(e)[:40]}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("\nRecommendations:")
print("1. Binance API: FASTEST, no Chrome needed!")
print("2. CoinGecko: Good fallback, free tier")
print("3. Chainlink: Direct on-chain (need Web3.py)")
print("\nWinner: Binance API (simple, fast, reliable)")
print("=" * 60)
