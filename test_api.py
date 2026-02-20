"""
Test API Connections - Debugging Script
"""
import requests

def test_binance():
    """Test Binance API"""
    print("=" * 50)
    print("Testing Binance API...")
    print("=" * 50)

    # Test 1: Ping
    print("\n[1] Testing Ping Endpoint:")
    try:
        response = requests.get("https://api.binance.com/api/v3/ping", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   X ERROR: {type(e).__name__}: {e}")

    # Test 2: Get BTC Price
    print("\n[2] Testing BTCUSDT Price:")
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ERROR: {type(e).__name__}: {e}")

    # Test 3: Get Klines (Candlesticks)
    print("\n[3] Testing Klines (Candlestick Data):")
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "5m",
            "limit": 5
        }
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   OK Got {len(data)} candles")
            print(f"   Latest candle: {data[-1]}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   X ERROR: {type(e).__name__}: {e}")


def test_bybit():
    """Test Bybit API"""
    print("\n" + "=" * 50)
    print("? Testing Bybit API...")
    print("=" * 50)

    # Test 1: Get BTC Price
    print("\n[1] Testing BTCUSDT Price:")
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   RetCode: {data.get('retCode')}")
            print(f"   Price: {data['result']['list'][0]['lastPrice']}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   X ERROR: {type(e).__name__}: {e}")

    # Test 2: Get Klines
    print("\n2️⃣ Testing Klines (Candlestick Data):")
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": "BTCUSDT",
            "interval": "5",
            "limit": 5
        }
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   RetCode: {data.get('retCode')}")
            if data.get('retCode') == 0:
                klines = data['result']['list']
                print(f"   OK Got {len(klines)} candles")
                print(f"   Latest candle: {klines[0]}")
            else:
                print(f"   Error: {data.get('retMsg')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   X ERROR: {type(e).__name__}: {e}")

    # Test 3: Get CCUSDT (Canton)
    print("\n3️⃣ Testing CCUSDT (Canton):")
    try:
        response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=CCUSDT", timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   RetCode: {data.get('retCode')}")
            if data.get('retCode') == 0:
                print(f"   OK Price: {data['result']['list'][0]['lastPrice']}")
            else:
                print(f"   Error: {data.get('retMsg')}")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   X ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("API CONNECTION TEST")
    print("=" * 50 + "\n")

    test_binance()
    test_bybit()

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)
