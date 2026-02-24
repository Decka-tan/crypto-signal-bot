#!/usr/bin/env python3
"""
Test Unhedged Scraper - Real-time Market Status
"""

import sys
sys.path.insert(0, '.')

from core.unhedged_scraper import UnhedgedScraper
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

console.print("[bold cyan]Testing Unhedged Scraper - Market Status[/bold cyan]\n")

scraper = UnhedgedScraper(use_selenium=True)

symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'CCUSDT']

try:
    console.print("[dim]Scraping Unhedged markets...[/dim]\n")

    for symbol in symbols:
        console.print(f"[cyan]{symbol}:[/cyan]")

        should_alert, market, status_msg = scraper.should_alert_symbol(symbol)

        if market:
            console.print(f"  Market ID: {market.market_id[:30]}...")
            console.print(f"  Question: {market.question[:60]}...")
            console.print(f"  Type: {market.market_type}")
            console.print(f"  Resolve Time: {market.resolve_time}")
            console.print(f"  Close Time: {market.close_time}")
            console.print(f"  Is Active: {market.is_market_active()}")

            minutes_left = market.get_time_until_resolved()
            if minutes_left is not None:
                console.print(f"  Time Until Resolved: {minutes_left} minutes")

            console.print(f"  Status Display: {market.get_status_display()}")
            console.print(f"  Should Alert: {should_alert}")
            console.print(f"  Reason: {status_msg}")
        else:
            console.print(f"  [yellow]No market found[/yellow]")
            console.print(f"  Reason: {status_msg}")

        console.print("")

except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    import traceback
    traceback.print_exc()

console.print("\n[bold]Test complete![/bold]")
