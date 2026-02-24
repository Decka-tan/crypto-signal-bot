"""
Chainlink Price Fetcher
Get prices directly from Chainlink on-chain feeds (same as Unhedged resolution!)
"""

from web3 import Web3
from typing import Optional, Dict
import time

# Chainlink Price Feed Addresses (Ethereum Mainnet)
CHAINLINK_FEEDS = {
    'BTC/USD': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c',  # Bitcoin / USD
    'ETH/USD': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',  # Ethereum / USD
    # SOL/USD and CC/USD not available in standard Chainlink feeds
}

# Price Feed ABI (minimal for getting latest price)
PRICE_FEED_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class ChainlinkFetcher:
    """Fetch prices from Chainlink on-chain price feeds"""

    def __init__(self, rpc_url: str = None):
        """
        Initialize Chainlink fetcher

        Args:
            rpc_url: Ethereum RPC URL (uses public endpoints if None)
        """
        if rpc_url is None:
            # Use public RPC endpoints
            self.rpc_urls = [
                'https://eth.llamarpc.com',
                'https://rpc.ankr.com/eth',
            ]
        else:
            self.rpc_urls = [rpc_url]

        self.w3 = None
        self.contracts = {}
        self._connect()

    def _connect(self):
        """Connect to Ethereum RPC"""
        for rpc in self.rpc_urls:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc))
                if w3.is_connected():
                    self.w3 = w3
                    print(f"[Chainlink] Connected to Ethereum via {rpc[:30]}...")
                    break
            except Exception as e:
                continue

        if not self.w3:
            print("[Chainlink] ERROR: Could not connect to RPC")

        # Initialize contracts
        for feed_name, address in CHAINLINK_FEEDS.items():
            try:
                contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(address),
                    abi=PRICE_FEED_ABI
                )
                self.contracts[feed_name] = contract
            except Exception as e:
                print(f"[Chainlink] Failed to init {feed_name}: {str(e)[:30]}")

    def get_price(self, feed_name: str) -> Optional[float]:
        """
        Get latest price from Chainlink feed

        Args:
            feed_name: Feed name (e.g., 'BTC/USD', 'ETH/USD')

        Returns:
            Price in USD or None if failed
        """
        if feed_name not in self.contracts:
            return None

        try:
            contract = self.contracts[feed_name]

            # Get decimals
            decimals = contract.functions.decimals().call()

            # Get latest round data
            data = contract.functions.latestRoundData().call()

            # data = (round_id, price, started_at, updated_at, answered_in_round)
            price = data[1] / (10 ** decimals)
            updated_at = data[3]

            return price

        except Exception as e:
            print(f"[Chainlink] Error fetching {feed_name}: {str(e)[:40]}")
            return None

    def get_btc_price(self) -> Optional[float]:
        """Get BTC price from Chainlink"""
        return self.get_price('BTC/USD')

    def get_eth_price(self) -> Optional[float]:
        """Get ETH price from Chainlink"""
        return self.get_price('ETH/USD')

    def is_available(self, symbol: str) -> bool:
        """Check if Chainlink feed is available for symbol"""
        feed_map = {
            'BTCUSDT': 'BTC/USD',
            'ETHUSDT': 'ETH/USD',
        }
        feed = feed_map.get(symbol)
        return feed in self.contracts

    def fetch_symbol(self, symbol: str) -> Optional[float]:
        """Fetch price for trading symbol"""
        feed_map = {
            'BTCUSDT': 'BTC/USD',
            'ETHUSDT': 'ETH/USD',
        }
        feed = feed_map.get(symbol)
        if feed:
            return self.get_price(feed)
        return None


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("CHAINLINK PRICE FETCHER TEST")
    print("=" * 60)

    fetcher = ChainlinkFetcher()

    print("\nFetching prices...\n")

    btc = fetcher.get_btc_price()
    eth = fetcher.get_eth_price()

    if btc:
        print(f"  BTC/USD: ${btc:.2f} [Chainlink]")
    else:
        print(f"  BTC/USD: FAILED")

    if eth:
        print(f"  ETH/USD: ${eth:.2f} [Chainlink]")
    else:
        print(f"  ETH/USD: FAILED")

    print("\n" + "=" * 60)
    print("Available symbols:", list(fetcher.contracts.keys()))
    print("=" * 60)
