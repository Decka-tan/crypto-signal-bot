"""
Find correct endpoint for bets/positions
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

session = requests.Session()
session.headers.update({
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
})

# Common endpoints to try for bets/positions
endpoints_to_try = [
    '/my-positions',
    '/positions',
    '/bets',
    '/my-bets',
    '/orders',
    '/pending',
]

print("Trying different endpoints for bets/positions:")
print("=" * 50)

for endpoint in endpoints_to_try:
    try:
        response = session.get(f"{BASE_URL}{endpoint}", timeout=10)
        status = "[OK]" if response.status_code == 200 else f"[{response.status_code}]"
        print(f"{status} {endpoint}")
        if response.status_code == 200:
            print(f"     Response keys: {list(response.json().keys()) if isinstance(response.json(), dict) else 'array'}")
    except Exception as e:
        print(f"[ERR] {endpoint} - {str(e)[:30]}")

print()
print("Done!")
