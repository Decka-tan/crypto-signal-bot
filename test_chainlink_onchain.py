"""
Test Chainlink On-Chain Price Feeds
Get prices directly from Chainlink smart contracts on Ethereum
"""

from web3 import Web3
import requests
import json

print("=" * 60)
print("CHAINLINK ON-CHAIN PRICE FEEDS TEST")
print("=" * 60)

# ============================================================================
# Chainlink Price Feed Addresses (Ethereum Mainnet)
# ============================================================================

# Registry: https://docs.chain.link/data-feeds/price-feeds/addresses
CHAINLINK_FEEDS = {
    'BTC/USD': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c',  # Bitcoin
    'ETH/USD': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',  # Ethereum
    'SOL/USD': '0xD1a20244C4146eCcBc1Cee5f4b2680895eb9B24b',  # Solana
    # CC/USD - Need to find this one!
}

print("\n[1] Checking Chainlink Registry for CC/USD feed...")
print("-" * 60)

# Check Chainlink Data Feeds registry
registry_url = "https://feeds.chain.link/feedAddresses"

try:
    response = requests.get(registry_url, timeout=10)
    print("  Fetched Chainlink feed addresses")

    # Parse JSON
    feeds = response.json()

    # Search for CC or Canton
    found_feeds = []
    for network, data in feeds.items():
        if isinstance(data, dict):
            for feed_name, address in data.items():
                if 'CC' in feed_name.upper() or 'CANTON' in feed_name.upper():
                    found_feeds.append({
                        'network': network,
                        'feed': feed_name,
                        'address': address
                    })

    if found_feeds:
        print("\n  Found CC feeds!")
        for feed in found_feeds:
            print(f"    Network: {feed['network']}")
            print(f"    Feed: {feed['feed']}")
            print(f"    Address: {feed['address']}")
            CHAINLINK_FEEDS['CC/USD'] = feed['address']
    else:
        print("  CC/USD feed not found in registry")
        print("  Might be a custom feed for Unhedged")

except Exception as e:
    print(f"  Failed to fetch registry: {str(e)[:50]}")

# ============================================================================
# Test with RPC Node (try public endpoints)
# ============================================================================

print("\n[2] Testing RPC Connections...")
print("-" * 60)

# Public RPC endpoints
RPC_ENDPOINTS = [
    'https://eth.llamarpc.com',
    'https://rpc.ankr.com/eth',
    'https://1rpc.io/eth',
]

w3 = None
for rpc in RPC_ENDPOINTS:
    try:
        test_w3 = Web3(Web3.HTTPProvider(rpc))
        if test_w3.is_connected():
            block = test_w3.eth.block_number
            print(f"  [OK] {rpc}")
            print(f"    Block: {block}")
            w3 = test_w3
            break
    except Exception as e:
        print(f"  [FAIL] {rpc} - {str(e)[:30]}")

if not w3:
    print("\n  ERROR: Could not connect to any RPC node")
    print("  Need Infura/Alchemy API key for reliable access")
    exit(1)

# ============================================================================
# Get prices from Chainlink feeds
# ============================================================================

print("\n[3] Fetching Prices from Chainlink...")
print("-" * 60)

# Chainlink Price Feed ABI (minimal)
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

for feed_name, feed_address in CHAINLINK_FEEDS.items():
    if not feed_address:
        continue

    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(feed_address), abi=PRICE_FEED_ABI)

        # Get decimals
        decimals = contract.functions.decimals().call()

        # Get latest price
        latest_data = contract.functions.latestRoundData().call()
        round_id, price, started_at, updated_at, answered_in = latest_data

        # Convert to decimal
        price_usd = price / (10 ** decimals)

        # Convert timestamps
        updated_time = updated_at
        from datetime import datetime
        updated_datetime = datetime.fromtimestamp(updated_time)

        print(f"\n  {feed_name}:")
        print(f"    Price: ${price_usd:.6f}")
        print(f"    Updated: {updated_datetime}")
        print(f"    Round ID: {round_id}")

    except Exception as e:
        print(f"\n  {feed_name}: FAILED - {str(e)[:50]}")

# ============================================================================
# Alternative: Chainlink API (if exists)
# ============================================================================

print("\n" + "=" * 60)
print("CONCLUSION")
print("=" * 60)
print("""
If CC/USD feed found:
  - Use Web3.py to fetch directly from contract
  - No Chrome needed!
  - Same data source as Unhedged resolution

If CC/USD feed NOT found:
  - Unhedged might use custom Chainlink feed
  - Or aggregated price from multiple sources
  - Current Bybit setup is still the best option
""")
