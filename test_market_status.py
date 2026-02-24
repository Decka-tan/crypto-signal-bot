#!/usr/bin/env python3
"""
Test Market Status Calculation
"""

from datetime import datetime, timedelta
from core.unhedged_market_status import UnhedgedMarketStatus
from rich.console import Console
from rich.table import Table

console = Console()

console.print("[bold cyan]Testing Market Status Calculation[/bold cyan]\n")

# Test different times
test_times = [
    (9, 0, "9:00 AM - Market opens"),
    (9, 30, "9:30 AM - Active"),
    (9, 45, "9:45 AM - Near close"),
    (9, 50, "9:50 AM - Market CLOSED"),
    (9, 55, "9:55 AM - Resolved window"),
    (10, 0, "10:00 AM - Resolved"),
    (10, 5, "10:05 AM - Next market open"),
    (10, 30, "10:30 AM - Active"),
    (11, 0, "11:00 AM - Interval market opens"),
    (11, 30, "11:30 AM - Interval active"),
    (12, 40, "12:40 PM - Interval near close"),
    (12, 50, "12:50 PM - Interval CLOSED"),
    (13, 0, "1:00 PM - Interval resolved"),
]

table = Table(show_header=True, header_style="bold magenta")
table.add_column("Time", style="cyan")
table.add_column("Binary Status", style="green")
table.add_column("Interval Status", style="yellow")

for hour, minute, desc in test_times:
    test_time = datetime(2025, 2, 20, hour, minute)

    # Binary status
    binary_status = UnhedgedMarketStatus.get_market_status_from_time(test_time, 'binary')
    binary_display = f"{binary_status['display']} ({binary_status['status']})"

    # Interval status
    interval_status = UnhedgedMarketStatus.get_market_status_from_time(test_time, 'interval')
    interval_display = f"{interval_status['display']} ({interval_status['status']})"

    table.add_row(
        f"{hour:02d}:{minute:02d}",
        binary_display,
        interval_display
    )

console.print(table)
console.print("\n[dim]Binary markets: Hourly (close XX:50, resolve XX:00)[/dim]")
console.print("[dim]Interval markets: Every 2 hours at odd hours (close XX+1:50, resolve XX+2:00)[/dim]")
