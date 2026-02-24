#!/usr/bin/env python3
"""
Test Interval Signal Generator
Tests the LOW/MID/HIGH price range prediction
"""

import yaml
from core.market_monitor import MarketMonitor
from core.interval_signals import IntervalSignalGenerator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def main():
    console = Console()

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

    console.print("[bold cyan]Testing Interval Signal Generator[/bold cyan]")
    console.print("[dim]LOW/MID/HIGH Price Range Prediction[/dim]\n")

    # Initialize market monitor
    monitor = MarketMonitor(symbols, timeframe='5m', exchange='bybit')

    # Initialize interval signal generator
    interval_gen = IntervalSignalGenerator(config, monitor)

    results = {}

    for symbol in symbols:
        console.print(f"[cyan]Analyzing {symbol}...[/cyan]")

        # First, trigger selenium initialization by fetching klines
        # This initializes the Chrome driver
        _ = monitor.get_klines(symbol, limit=10)

        # Get current price
        current_price = monitor.get_current_price(symbol)

        if not current_price:
            console.print(f"  [red]X[/red] Could not fetch price\n")
            continue

        console.print(f"  Current Price: ${current_price:,.2f}")

        # Predict price in 2 hours
        prediction = interval_gen.predict_price_at_time(
            symbol,
            current_price,
            target_minutes_ahead=120
        )

        if prediction.get('confidence', 0) < 50:
            console.print(f"  [yellow]![/yellow] Low confidence prediction\n")
            continue

        # Calculate thresholds
        volatility = prediction.get('volatility', 2)
        range_percent = volatility * 1.5

        low_threshold = current_price * (1 - range_percent / 100)
        high_threshold = current_price * (1 + range_percent / 100)

        console.print(f"  Volatility: {volatility:.2f}%")
        console.print(f"  Range: ±{range_percent:.2f}%")
        console.print(f"  LOW Threshold: ${low_threshold:,.2f}")
        console.print(f"  HIGH Threshold: ${high_threshold:,.2f}")
        console.print(f"  Predicted Price: ${prediction['predicted_price']:,.2f}")
        console.print(f"  Confidence: {prediction['confidence']}%")

        # Classify interval
        interval_signal = interval_gen.classify_interval(
            prediction,
            low_threshold,
            high_threshold
        )

        signal = interval_signal['interval']
        confidence = interval_signal['confidence']

        # Color code
        if signal == 'LOW':
            color = 'red'
            symbol_icon = 'v'
        elif signal == 'MID':
            color = 'yellow'
            symbol_icon = '-'
        else:
            color = 'green'
            symbol_icon = '^'

        console.print(f"\n  [bold {color}]{symbol_icon} SIGNAL: {signal}[/bold {color}] (Confidence: {confidence}%)")
        console.print(f"  Backup: {interval_signal['secondary']}")

        for reason in interval_signal['reasoning'][:3]:
            console.print(f"    - {reason}")

        console.print("")

        results[symbol] = {
            'signal': signal,
            'confidence': confidence,
            'predicted': prediction['predicted_price'],
            'current': current_price,
            'color': color
        }

    # Summary table
    table = Table(title="\n[bold]Interval Market Summary[/bold]", show_header=True, header_style="bold magenta")
    table.add_column("Symbol", style="cyan")
    table.add_column("Signal", style="bold")
    table.add_column("Confidence")
    table.add_column("Current", justify="right")
    table.add_column("Predicted", justify="right")
    table.add_column("Change", justify="right")

    for symbol, data in results.items():
        change_pct = (data['predicted'] - data['current']) / data['current'] * 100
        change_str = f"{change_pct:+.2f}%"
        change_color = "green" if change_pct > 0 else "red"

        table.add_row(
            symbol,
            f"[{data['color']}]{data['signal']}[/{data['color']}]",
            f"{data['confidence']}%",
            f"${data['current']:,.2f}",
            f"${data['predicted']:,.2f}",
            f"[{change_color}]{change_str}[/{change_color}]"
        )

    console.print(table)

    # Cleanup
    monitor.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest stopped")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
