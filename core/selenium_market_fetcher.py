"""
Selenium-based Market Data Fetcher
Uses Chrome browser to fetch data - bypasses Python blocking!
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd
from typing import List, Dict, Optional
import json
import time


class SeleniumMarketFetcher:
    """Fetch market data using Chrome browser"""

    def __init__(self, symbols: List[str], timeframe: str = "5m", headless: bool = True):
        """
        Initialize Selenium fetcher

        Args:
            symbols: List of trading pairs
            timeframe: Candlestick interval
            headless: Run Chrome in headless mode (no GUI)
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome driver"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument('--headless=new')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--disable-logging')
        chrome_options.add_argument('--disable-extensions')

        # Disable SSL verification (like Chrome does)
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-running-insecure-content')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)

    def get_binance_klines(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch candlesticks from Binance using Chrome"""
        try:
            if self.driver is None:
                self._init_driver()

            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={self.timeframe}&limit={limit}"
            self.driver.get(url)

            # Get page source and parse JSON
            page_source = self.driver.find_element(By.TAG_NAME, "pre").text
            data = json.loads(page_source)

            if not data or len(data) == 0:
                return None

            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"   Binance error: {str(e)[:50]}")
            return None

    def get_bybit_klines(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch candlesticks from Bybit using Chrome"""
        try:
            if self.driver is None:
                self._init_driver()

            # Bybit interval mapping
            interval_map = {
                '1m': '1', '5m': '5', '15m': '15', '1h': '60',
                '4h': '240', '1d': 'D'
            }
            interval = interval_map.get(self.timeframe, '5')

            url = f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}&interval={interval}&limit={limit}"
            self.driver.get(url)

            # Get page source and parse JSON
            page_source = self.driver.find_element(By.TAG_NAME, "pre").text
            data = json.loads(page_source)

            if data.get('retCode') != 0:
                return None

            klines = data['result']['list']

            if not klines or len(klines) == 0:
                return None

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            print(f"   Bybit error: {str(e)[:50]}")
            return None

    def get_binance_price(self, symbol: str) -> Optional[float]:
        """Get current price from Binance using Chrome"""
        try:
            if self.driver is None:
                self._init_driver()

            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            self.driver.get(url)

            page_source = self.driver.find_element(By.TAG_NAME, "pre").text
            data = json.loads(page_source)

            return float(data.get('price', 0))

        except Exception as e:
            return None

    def get_bybit_price(self, symbol: str) -> Optional[float]:
        """Get current price from Bybit using Chrome"""
        try:
            if self.driver is None:
                self._init_driver()

            url = f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
            self.driver.get(url)

            page_source = self.driver.find_element(By.TAG_NAME, "pre").text
            data = json.loads(page_source)

            if data.get('retCode') == 0:
                return float(data['result']['list'][0]['lastPrice'])

            return None

        except Exception as e:
            return None

    def get_klines(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch candlesticks - tries Binance then Bybit"""
        print(f"   Fetching {symbol} via Chrome...")

        # Try Binance first
        df = self.get_binance_klines(symbol, limit)
        if df is not None and len(df) > 0:
            print(f"   [OK] Got {len(df)} candles from Binance")
            return df

        # Try Bybit
        df = self.get_bybit_klines(symbol, limit)
        if df is not None and len(df) > 0:
            print(f"   [OK] Got {len(df)} candles from Bybit")
            return df

        print(f"   [X] Failed to fetch {symbol}")
        return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price - tries Binance then Bybit"""
        # Try Binance first
        price = self.get_binance_price(symbol)
        if price is not None:
            return price

        # Try Bybit
        price = self.get_bybit_price(symbol)
        if price is not None:
            return price

        return None

    def update_all_data(self, limit: int = 100) -> Dict[str, pd.DataFrame]:
        """Fetch latest data for all symbols"""
        data = {}

        for symbol in self.symbols:
            df = self.get_klines(symbol, limit)
            if df is not None:
                data[symbol] = df

        return data

    def close(self):
        """Close Chrome driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Test the fetcher
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "CCUSDT"]

    print("=" * 50)
    print("Testing Selenium Market Fetcher")
    print("=" * 50)

    with SeleniumMarketFetcher(symbols, timeframe="5m", headless=False) as fetcher:
        print("\nFetching data via Chrome...\n")

        for symbol in symbols:
            print(f"\n{symbol}:")
            df = fetcher.get_klines(symbol, limit=5)
            if df is not None:
                print(f"  Latest candle: {df.iloc[-1].to_dict()}")
            else:
                print(f"  Failed to fetch")

            price = fetcher.get_current_price(symbol)
            if price:
                print(f"  Current price: ${price}")

    print("\n" + "=" * 50)
    print("Test complete!")
    print("=" * 50)
