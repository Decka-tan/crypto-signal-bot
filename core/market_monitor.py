"""
Multi-Exchange Market Monitor Module
Supports: Binance, Bybit, OKX, KuCoin
Uses Selenium/Chrome for data fetching (bypasses Python blocking)
"""

import requests
import pandas as pd
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime, timedelta

# Import Selenium fetcher
from core.selenium_market_fetcher import SeleniumMarketFetcher


class MarketMonitor:
    """Monitor crypto markets across multiple exchanges"""

    def __init__(self, symbols: List[str], timeframe: str = "15m", demo_mode: bool = False, exchange: str = "auto"):
        """
        Initialize market monitor

        Args:
            symbols: List of trading pairs (e.g., ["BTCUSDT", "CCUSDT"])
            timeframe: Candlestick interval
            demo_mode: Use simulated data
            exchange: "auto", "binance", "bybit", "okx", "kucoin"
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.demo_mode = demo_mode
        self.exchange = exchange
        self.data_cache = {}
        self.selenium_fetcher = None

        # Use Selenium fetcher by default (bypasses Python blocking)
        self.use_selenium = True

    def get_klines(self, symbol: str, limit: int = 100, timeframe: str = None) -> Optional[pd.DataFrame]:
        """
        Fetch candlestick data - uses Selenium by default (bypasses Python blocking)

        Args:
            symbol: Trading pair symbol
            limit: Number of candles to fetch
            timeframe: Candlestick interval (optional, uses default if not specified)
        """
        # Use provided timeframe or fall back to default
        tf = timeframe if timeframe else self.timeframe

        if self.demo_mode:
            return self._generate_demo_data(symbol, limit)

        # Use Selenium fetcher (Chrome browser)
        if self.use_selenium:
            try:
                if self.selenium_fetcher is None:
                    print("   [INFO] Initializing Chrome-based data fetcher...")
                    self.selenium_fetcher = SeleniumMarketFetcher(
                        symbols=self.symbols,
                        timeframe=self.timeframe,  # Default timeframe
                        headless=True  # Run in background
                    )

                df = self.selenium_fetcher.get_klines(symbol, limit, timeframe=tf)
                if df is not None and len(df) > 0:
                    return df
            except Exception as e:
                print(f"   [WARN] Selenium fetch failed: {str(e)[:50]}")
                print(f"   [INFO] Falling back to requests method...")

        # Fallback to requests method
        exchanges_to_try = []
        errors = []

        if self.exchange == "auto":
            exchanges_to_try = ["binance", "bybit"]  # Skip OKX/KuCoin for now
        else:
            exchanges_to_try = [self.exchange]

        for exchange in exchanges_to_try:
            try:
                if exchange == "binance":
                    df = self._get_binance_klines(symbol, limit, tf)
                elif exchange == "bybit":
                    df = self._get_bybit_klines(symbol, limit, tf)
                elif exchange == "okx":
                    df = self._get_okx_klines(symbol, limit, tf)
                elif exchange == "kucoin":
                    df = self._get_kucoin_klines(symbol, limit, tf)

                if df is not None and len(df) > 0:
                    return df

            except Exception as e:
                error_msg = f"{exchange.upper()}: {str(e)[:50]}"
                errors.append(error_msg)
                continue

        # Show which exchanges failed
        if errors:
            print(f"   [WARN] [{symbol}] All methods failed, using demo data")

        return self._generate_demo_data(symbol, limit)

    def _get_binance_klines(self, symbol: str, limit: int, timeframe: str = None) -> Optional[pd.DataFrame]:
        """Fetch from Binance"""
        try:
            tf = timeframe if timeframe else self.timeframe
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": tf,
                "limit": limit
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

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

        except:
            return None

    def _get_bybit_klines(self, symbol: str, limit: int, timeframe: str = None) -> Optional[pd.DataFrame]:
        """Fetch from Bybit - supports CCUSDT!"""
        try:
            tf = timeframe if timeframe else self.timeframe
            url = "https://api.bybit.com/v5/market/kline"

            # Bybit uses different interval names
            interval_map = {
                '1m': '1', '5m': '5', '15m': '15', '1h': '60',
                '4h': '240', '1d': 'D'
            }
            interval = interval_map.get(tf, '15')

            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 200)  # Bybit max is 200
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('retCode') != 0:
                return None

            klines = data['result']['list']

            # Bybit format: [startTime, open, high, low, close, volume, turnover]
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

        except:
            return None

    def _get_okx_klines(self, symbol: str, limit: int, timeframe: str = None) -> Optional[pd.DataFrame]:
        """Fetch from OKX"""
        try:
            tf = timeframe if timeframe else self.timeframe
            # OKX uses dash format (BTC-USDT)
            okx_symbol = symbol.replace('USDT', '-USDT')

            url = "https://www.okx.com/api/v5/market/candles"

            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '1h': '1H',
                '4h': '4H', '1d': '1D'
            }
            interval = interval_map.get(tf, '15m')

            params = {
                "instId": okx_symbol,
                "bar": interval,
                "limit": str(min(limit, 100))
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '0':
                return None

            klines = data['data']

            # OKX format: [timestamp, open, high, low, close, volume, ...]
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'volCcy', 'volCcyQuote', 'confirm'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]

        except:
            return None

    def _get_kucoin_klines(self, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch from KuCoin"""
        try:
            # KuCoin uses dash format (BTC-USDT)
            kc_symbol = symbol.replace('USDT', '-USDT')

            url = "https://api.kucoin.com/api/v1/klines"

            params = {
                "symbol": kc_symbol,
                "type": self.timeframe,
                "limit": str(limit)
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '200000':
                return None

            klines = data['data']

            if not klines or len(klines) == 0:
                return None

            # KuCoin format: [timestamp, open, high, low, close, volume]
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume'
            ])

            # Handle timestamps safely
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]

        except:
            return None

    def _generate_demo_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Generate realistic demo data"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=15 * limit)
        timestamps = pd.date_range(start=start_time, end=end_time, periods=limit)

        # Base prices for different symbols
        base_prices = {
            'BTCUSDT': 43000,
            'ETHUSDT': 2300,
            'SOLUSDT': 100,
            'BNBUSDT': 320,
            'ADAUSDT': 0.55,
            'CCUSDT': 0.165  # Canton!
        }

        base_price = base_prices.get(symbol, 100)

        # Generate price data
        np.random.seed(hash(symbol) % 10000)
        returns = np.random.normal(0, 0.005, limit)
        prices = [base_price]

        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        prices = np.array(prices)
        noise = np.random.normal(0, 0.001, limit)

        data = {
            'open': prices * (1 + np.abs(noise) * 0.3),
            'high': prices * (1 + np.abs(noise)),
            'low': prices * (1 - np.abs(noise)),
            'close': prices,
            'volume': np.random.lognormal(10, 0.5, limit)
        }

        df = pd.DataFrame(data, index=timestamps)
        return df

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price - uses Selenium by default"""
        if self.demo_mode:
            df = self.get_klines(symbol, limit=1)
            if df is not None and len(df) > 0:
                return float(df['close'].iloc[-1])
            return None

        # Use Selenium fetcher first
        if self.use_selenium and self.selenium_fetcher is not None:
            try:
                price = self.selenium_fetcher.get_current_price(symbol)
                if price is not None:
                    return price
            except:
                pass

        # Fallback to requests
        for exchange in ["bybit" if self.exchange == "auto" else self.exchange, "binance"]:
            try:
                if exchange == "bybit":
                    url = "https://api.bybit.com/v5/market/tickers"
                    params = {"category": "spot", "symbol": symbol}
                    response = requests.get(url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('retCode') == 0:
                            return float(data['result']['list'][0]['lastPrice'])
                elif exchange == "binance":
                    url = "https://api.binance.com/api/v3/ticker/price"
                    params = {"symbol": symbol}
                    response = requests.get(url, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        return float(data['price'])
            except:
                continue

        return None

    def update_all_data(self, limit: int = 100) -> Dict[str, pd.DataFrame]:
        """Fetch latest data for all symbols"""
        data = {}
        for symbol in self.symbols:
            df = self.get_klines(symbol, limit)
            if df is not None:
                data[symbol] = df
                self.data_cache[symbol] = df
        return data

    def get_price_summary(self, symbol: str) -> Optional[Dict]:
        """Get price summary"""
        df = self.data_cache.get(symbol)
        if df is None or len(df) == 0:
            df = self.get_klines(symbol, limit=50)
            if df is None or len(df) == 0:
                return None

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # Safely calculate change
        if prev is not None and 'close' in prev and not pd.isna(prev['close']):
            change = latest['close'] - prev['close']
            change_percent = (change / prev['close']) * 100
        else:
            change = 0
            change_percent = 0

        return {
            'symbol': symbol,
            'current_price': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            'change': change,
            'change_percent': change_percent,
            'time': latest.name.strftime('%H:%M:%S')
        }

    def cleanup(self):
        """Clean up resources (close Selenium driver)"""
        if self.selenium_fetcher is not None:
            self.selenium_fetcher.close()
            self.selenium_fetcher = None
