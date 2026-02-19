"""
Market Monitor Module - Fetches real-time crypto price data
Supports multiple APIs for redundancy
"""

import requests
import pandas as pd
from typing import List, Dict, Optional
import random


class MarketMonitor:
    """Monitor crypto markets using multiple APIs for redundancy"""

    def __init__(self, symbols: List[str], timeframe: str = "15m", demo_mode: bool = False):
        """
        Initialize market monitor

        Args:
            symbols: List of trading pairs (e.g., ["BTCUSDT", "ETHUSDT"])
            timeframe: Candlestick interval (1m, 5m, 15m, 1h, 4h, 1d)
            demo_mode: If True, use simulated data for testing
        """
        self.symbols = symbols
        self.timeframe = timeframe
        self.demo_mode = demo_mode
        self.data_cache = {}

        # Try different APIs
        self.apis = [
            {
                'name': 'Binance',
                'klines_url': 'https://api.binance.com/api/v3/klines',
                'price_url': 'https://api.binance.com/api/v3/ticker/price'
            },
            {
                'name': 'Binance Backup',
                'klines_url': 'https://api1.binance.com/api/v3/klines',
                'price_url': 'https://api1.binance.com/api/v3/ticker/price'
            },
            {
                'name': 'Binance US',
                'klines_url': 'https://api.binance.us/api/v3/klines',
                'price_url': 'https://api.binance.us/api/v3/ticker/price'
            }
        ]
        self.current_api_index = 0

    def _try_api(self, url: str, params: dict, timeout: int = 10) -> Optional[requests.Response]:
        """Try to make API request with fallback to alternative APIs"""
        for i in range(len(self.apis)):
            api_index = (self.current_api_index + i) % len(self.apis)
            api_name = self.apis[api_index]['name']

            try:
                # Replace domain in URL with current API
                base_url = self.apis[api_index]['klines_url'].split('/api/')[0]
                modified_url = url.replace('https://api.binance.com', base_url)
                modified_url = modified_url.replace('https://api1.binance.com', base_url)

                response = requests.get(modified_url, params=params, timeout=timeout)
                if response.status_code == 200:
                    # Update current API on success
                    self.current_api_index = api_index
                    return response

            except Exception as e:
                continue

        return None

    def get_klines(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Fetch candlestick data"""
        if self.demo_mode:
            return self._generate_demo_data(symbol, limit)

        try:
            params = {
                "symbol": symbol,
                "interval": self.timeframe,
                "limit": limit
            }

            response = self._try_api(
                self.apis[0]['klines_url'],
                params,
                timeout=10
            )

            if response is None:
                print(f"⚠️ All APIs failed for {symbol}")
                return None

            data = response.json()

            # Parse into DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert to proper types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None

    def _generate_demo_data(self, symbol: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Generate realistic demo data for testing"""
        import numpy as np
        from datetime import datetime, timedelta

        # Base price for different symbols
        base_prices = {
            'BTCUSDT': 43000,
            'ETHUSDT': 2300,
            'SOLUSDT': 100,
            'BNBUSDT': 320,
            'ADAUSDT': 0.55
        }

        base_price = base_prices.get(symbol, 100)

        # Generate timestamps
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=15 * limit)
        timestamps = pd.date_range(start=start_time, end=end_time, periods=limit)

        # Generate price data with random walk
        np.random.seed(hash(symbol) % 10000)  # Consistent data for same symbol

        returns = np.random.normal(0, 0.005, limit)  # 0.5% volatility
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))

        prices = np.array(prices)

        # Generate OHLC from close prices
        noise = np.random.normal(0, 0.001, limit)  # Small noise for high/low

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
        """Get current price for a symbol"""
        if self.demo_mode:
            df = self.get_klines(symbol, limit=1)
            if df is not None and len(df) > 0:
                return float(df['close'].iloc[-1])
            return None

        try:
            for api in self.apis:
                try:
                    response = requests.get(
                        api['price_url'],
                        params={"symbol": symbol},
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return float(data['price'])
                except:
                    continue
            return None
        except:
            return None

    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """Get 24hr ticker statistics"""
        return None  # Not critical for main functionality

    def update_all_data(self, limit: int = 100) -> Dict[str, pd.DataFrame]:
        """Fetch latest data for all monitored symbols"""
        data = {}

        for symbol in self.symbols:
            df = self.get_klines(symbol, limit)
            if df is not None:
                data[symbol] = df
                self.data_cache[symbol] = df

        return data

    def get_price_summary(self, symbol: str) -> Optional[Dict]:
        """Get a summary of current price data"""
        df = self.data_cache.get(symbol)
        if df is None or len(df) == 0:
            df = self.get_klines(symbol, limit=50)
            if df is None:
                return None

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        return {
            'symbol': symbol,
            'current_price': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'volume': latest['volume'],
            'change': latest['close'] - prev['close'],
            'change_percent': ((latest['close'] - prev['close']) / prev['close']) * 100,
            'time': latest.name.strftime('%H:%M:%S')
        }
