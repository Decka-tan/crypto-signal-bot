"""
Test Unhedged API Connection
Verifies if API key works and endpoints are accessible
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)

API_KEY = os.getenv('UNHEDGED_API_KEY')
BASE_URL = "https://api.unhedged.gg/api/v1"

if not API_KEY:
    print("[ERROR] UNHEDGED_API_KEY not found in .env")
    exit(1)

print("=" * 50)
print("Testing Unhedged API Connection")
print("=" * 50)
print(f"Base URL: {BASE_URL}")
print(f"API Key: {API_KEY[:15]}...{API_KEY[-5:]}")
print()

# Setup session
session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
})

# Test 1: Balance
print("[TEST 1] Checking balance...")
try:
    response = session.get(f"{BASE_URL}/balance", timeout=10)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Response: {data}")
    else:
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"  Exception: {str(e)[:100]}")

print()

# Test 2: Markets
print("[TEST 2] Fetching active markets...")
try:
    params = {
        'status': 'ACTIVE',
        'limit': 5,
        'orderBy': 'endTime',
        'orderDirection': 'asc'
    }
    response = session.get(f"{BASE_URL}/markets", params=params, timeout=10)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list):
            print(f"  Found {len(data)} markets")
            if data:
                print(f"  First market keys: {list(data[0].keys())}")
        else:
            print(f"  Response: {data}")
    else:
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"  Exception: {str(e)[:100]}")

print()

# Test 3: My Positions
print("[TEST 3] Checking my positions...")
try:
    response = session.get(f"{BASE_URL}/my-positions", timeout=10)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  Response: {data}")
    else:
        print(f"  Error: {response.text[:200]}")
except Exception as e:
    print(f"  Exception: {str(e)[:100]}")

print()
print("=" * 50)
print("Test complete!")
print("=" * 50)
