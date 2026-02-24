"""
Quick guide to find Unhedged API endpoints

Steps:
1. Open unhedged.gg in Chrome/Firefox
2. Press F12 (Developer Tools)
3. Go to Network tab
4. Filter by "Fetch" or "XHR"
5. Do these actions:
   - Load market list
   - Click on a market
   - (Optional) Try placing a bet (then cancel)

6. Look for requests to unhedged domain
7. Copy the FULL URL and update in unhedged_auto_better.py

Example URLs to look for:
- https://unhedged.gg/api/markets
- https://api.unhedged.gg/v1/markets
- https://unhedged.gg/api/balance
- https://unhedged.gg/api/bets

Things to note:
- Look at the "Headers" tab
- Find "Authorization: Bearer XXX" header
- Check the request method (GET/POST)
- Check the request body (for POST requests)
"""

print(__doc__)
