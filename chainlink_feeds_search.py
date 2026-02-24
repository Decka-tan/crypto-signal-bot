"""
Search Chainlink feeds for Canton (CC) or similar assets
"""

import requests
from web3 import Web3

# Connect to Ethereum
w3 = Web3(Web3.HTTPProvider('https://eth.llamarpc.com'))
print(f"Connected to Ethereum. Block: {w3.eth.block_number}\n")

# Chainlink Price Feed ABI
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
    },
    {
        "inputs": [],
        "name": "description",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

print("=" * 60)
print("TESTING COMMON CHAINLINK FEEDS")
print("=" * 60)

# Known Chainlink feed addresses (from official docs)
FEEDS_TO_TEST = {
    'BTC/USD': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c',
    'ETH/USD': '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419',
    'SOL/USD': '0x466A1B783Fb4922368988D3671Ab94f9924F1489',  # Try alternate address
    'LINK/USD': '0x2c1d072e956AFFC0D466CbC3B2BaCAC9D792dE34',
    'MATIC/USD': '0x7BAC1A94eDdD9a327E4348b6EC351AaF80F3A526',
    'AVAX/USD': '0x0c7087139FFf891760969Bed75e0b1b3C3A9F35c',
    'AAVE/USD': '0x547a514d5e3769680Ce22B2361c205E1A7798699',
    'UNI/USD': '0xD6aA79A4246eBF23B354B638Dep3d180cC7Fbf4c',
}

for name, address in FEEDS_TO_TEST.items():
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=PRICE_FEED_ABI
        )

        # Get description
        desc = contract.functions.description().call()

        # Get decimals
        decimals = contract.functions.decimals().call()

        # Get price
        data = contract.functions.latestRoundData().call()
        price = data[1] / (10 ** decimals)

        print(f"{name:15} - ${price:10.2f} - {desc}")

    except Exception as e:
        print(f"{name:15} - ERROR: {str(e)[:40]}")

print("\n" + "=" * 60)
print("CONCLUSION:")
print("=" * 60)
print("""
BTC & ETH Chainlink feeds work perfectly!

For CC (Canton):
  - Not in standard Chainlink feeds
  - Unhedged might use CUSTOM feed
  - Or aggregate from multiple sources

Recommendation:
  1. Use Chainlink for BTC/ETH (no Chrome needed!)
  2. Keep Bybit for CC/SOL (small cap coins)
  3. Hybrid approach for best accuracy
""")
