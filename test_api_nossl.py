"""
Test API with SSL verification disabled
"""
import requests
import urllib3

# Disable SSL warnings (for testing only!)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_binance_no_ssl():
    """Test Binance API without SSL verification"""
    print("=" * 50)
    print("Testing Binance API (SSL Verification DISABLED)")
    print("=" * 50)

    # Test 1: Ping
    print("\n[1] Testing Ping Endpoint:")
    try:
        response = requests.get("https://api.binance.com/api/v3/ping", timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        if response.status_code == 200:
            print("   [OK] SUCCESS!")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test 2: Get BTC Price
    print("\n[2] Testing BTCUSDT Price:")
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] BTC Price: ${data['price']}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test 3: Get Klines
    print("\n[3] Testing Klines:")
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "5m", "limit": 5}
        response = requests.get(url, params=params, timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Got {len(data)} candles")
            print(f"   Latest close price: ${data[-1][4]}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")


def test_bybit_no_ssl():
    """Test Bybit API without SSL verification"""
    print("\n" + "=" * 50)
    print("Testing Bybit API (SSL Verification DISABLED)")
    print("=" * 50)

    # Test 1: Get BTC Price
    print("\n[1] Testing BTCUSDT Price:")
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                print(f"   [OK] BTC Price: ${data['result']['list'][0]['lastPrice']}")
            else:
                print(f"   Error: {data.get('retMsg')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test 2: Get CCUSDT
    print("\n[2] Testing CCUSDT (Canton):")
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=CCUSDT", timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                print(f"   [OK] CC Price: ${data['result']['list'][0]['lastPrice']}")
            else:
                print(f"   Error: {data.get('retMsg')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("API TEST - SSL VERIFICATION DISABLED")
    print("WARNING: This is for TESTING only!")
    print("=" * 50 + "\n")

    test_binance_no_ssl()
    test_bybit_no_ssl()

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
