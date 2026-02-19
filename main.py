#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Signal Bot - Main CLI
Technical analysis bot for 15m prediction market signals

Usage:
    python main.py                    # Start monitoring with default config
    python main.py --symbols BTC ETH  # Monitor specific symbols
    python main.py --once             # Run analysis once and exit
    python main.py --config custom.yaml  # Use custom config file
"""

import sys
import io
import time
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich import box
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "colorama"])
    from rich.console import Console
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich import box

from core.market_monitor import MarketMonitor
from core.indicators import TechnicalIndicators
from core.signals import SignalGenerator
from core.alerts import AlertManager


class CryptoSignalBot:
    """Main bot class for crypto technical analysis"""

    def __init__(self, config_path: str = "config.yaml", demo_mode: bool = False):
        """
        Initialize the bot

        Args:
            config_path: Path to configuration file
            demo_mode: If True, use simulated data for testing
        """
        self.config = self._load_config(config_path)
        self.console = Console()

        # Initialize components
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
        timeframe = self.config.get('timeframe', '15m')

        self.market_monitor = MarketMonitor(symbols, timeframe, demo_mode=demo_mode)
        self.signal_generator = SignalGenerator(self.config)
        self.alert_manager = AlertManager(self.config)

        # Tracking
        self.running = False
        self.last_alerts = {}  # Track last alert time for each symbol

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ Config file not found: {config_path}")
            print("Using default configuration...")
            return self._default_config()
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            'timeframe': '15m',
            'thresholds': {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'min_confidence': 60,
                'volume_spike': 150
            },
            'alerts': {
                'console': True,
                'sound': '',
                'telegram': {'enabled': False}
            },
            'display': {
                'update_interval': 30
            },
            'indicators': {
                'rsi': {'period': 14, 'enabled': True},
                'macd': {'fast': 12, 'slow': 26, 'signal': 9, 'enabled': True},
                'ema': {'short': 9, 'long': 21, 'enabled': True},
                'bollinger_bands': {'period': 20, 'std': 2, 'enabled': True},
                'volume': {'period': 20, 'enabled': True}
            }
        }

    def analyze_symbol(self, symbol: str) -> Dict:
        """
        Analyze a single symbol and generate signal

        Args:
            symbol: Trading pair symbol

        Returns:
            Signal analysis dictionary or None if error
        """
        try:
            # Fetch latest data
            df = self.market_monitor.get_klines(symbol, limit=100)

            if df is None or len(df) < 30:
                return None

            # Calculate all indicators
            indicators = TechnicalIndicators.calculate_all(df, self.config.get('indicators', {}))
            indicators['current'] = df['close'].iloc[-1]

            # Generate signal
            signal_analysis = self.signal_generator.analyze_indicators(indicators, symbol)

            return signal_analysis

        except Exception as e:
            self.console.print(f"[red]Error analyzing {symbol}: {e}[/red]")
            return None

    def check_and_alert(self, signal_analysis: Dict):
        """
        Check if signal should trigger an alert and send it

        Args:
            signal_analysis: Signal analysis dictionary
        """
        if signal_analysis is None:
            return

        symbol = signal_analysis['symbol']

        # Check if we should alert
        if self.signal_generator.should_alert(signal_analysis):
            # Check cooldown (don't alert too frequently for same symbol)
            last_alert_time = self.last_alerts.get(symbol, 0)
            current_time = time.time()

            cooldown = self.config.get('display', {}).get('update_interval', 30) * 2  # 2x update interval

            if current_time - last_alert_time > cooldown:
                self.alert_manager.send_alert(signal_analysis)
                self.alert_manager.log_signal(signal_analysis)
                self.last_alerts[symbol] = current_time

    def create_summary_table(self, all_signals: Dict) -> Table:
        """
        Create a summary table of all signals

        Args:
            all_signals: Dictionary mapping symbols to their signal analysis

        Returns:
            Rich Table object
        """
        table = Table(title="📊 Crypto Signal Bot - Live Analysis", box=box.ROUNDED)

        table.add_column("Symbol", style="cyan bold", width=12)
        table.add_column("Signal", style="bold", width=15)
        table.add_column("Confidence", width=12)
        table.add_column("Price", style="yellow", width=12)
        table.add_column("RSI", width=8)
        table.add_column("MACD", width=10)
        table.add_column("Volume %", width=10)

        for symbol, analysis in all_signals.items():
            if analysis is None:
                table.add_row(symbol, "[dim]No data[/dim]", "-", "-", "-", "-", "-")
                continue

            # Determine signal color
            signal = analysis['signal']
            if 'STRONG YES' in signal:
                signal_style = "[bold green]STRONG YES[/bold green]"
            elif 'YES' in signal:
                signal_style = "[green]YES[/green]"
            elif 'STRONG NO' in signal:
                signal_style = "[bold red]STRONG NO[/bold red]"
            elif 'NO' in signal:
                signal_style = "[red]NO[/red]"
            else:
                signal_style = "[yellow]HOLD[/yellow]"

            # Get indicators
            indicators = analysis.get('indicators', {})
            price = indicators.get('current', 0)
            rsi = indicators.get('rsi', 0)
            macd = indicators.get('macd_trend', 'N/A').upper()
            vol_pct = indicators.get('volume_ratio', 0)

            table.add_row(
                symbol,
                signal_style,
                f"{analysis['confidence']}%",
                f"${price:,.4f}",
                f"{rsi:.1f}" if rsi else "-",
                macd,
                f"{vol_pct:.0f}%" if vol_pct else "-"
            )

        return table

    def run_once(self):
        """Run analysis once and display results"""
        self.console.print("\n[bold cyan]🚀 Crypto Signal Bot - Single Analysis[/bold cyan]\n")

        # Fetch all data
        self.console.print("📡 Fetching market data...")
        self.market_monitor.update_all_data(limit=100)

        # Analyze all symbols
        all_signals = {}
        for symbol in self.market_monitor.symbols:
            self.console.print(f"   Analyzing [cyan]{symbol}[/cyan]...")
            signal = self.analyze_symbol(symbol)
            all_signals[symbol] = signal

        # Display summary
        table = self.create_summary_table(all_signals)
        self.console.print(table)

        # Show detailed signals for alerts
        self.console.print("\n[bold]📨 Detailed Alerts:[/bold]\n")
        for symbol, analysis in all_signals.items():
            if analysis and self.signal_generator.should_alert(analysis):
                self.alert_manager.send_alert(analysis)

    def run_continuous(self):
        """Run continuous monitoring with live updates"""
        self.console.print("\n[bold green]🚀 Crypto Signal Bot - Live Monitoring[/bold green]")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        # Fetch initial data
        self.console.print("📡 Fetching initial market data...")
        self.market_monitor.update_all_data(limit=100)

        self.running = True
        update_interval = self.config.get('display', {}).get('update_interval', 30)

        try:
            while self.running:
                # Clear console for fresh display
                self.console.clear()

                # Header
                self.console.print(
                    f"[bold cyan]📊 Crypto Signal Bot[/bold cyan] | "
                    f"[dim]Updated: {datetime.now().strftime('%H:%M:%S')}[/dim] | "
                    f"[dim]Interval: {update_interval}s[/dim]\n"
                )

                # Analyze all symbols
                all_signals = {}
                for symbol in self.market_monitor.symbols:
                    signal = self.analyze_symbol(symbol)
                    all_signals[symbol] = signal

                    # Check for alerts
                    if signal:
                        self.check_and_alert(signal)

                # Display summary table
                table = self.create_summary_table(all_signals)
                self.console.print(table)

                # Display recent alerts
                if self.last_alerts:
                    self.console.print(f"\n[bold]🔔 Recent Alerts:[/bold]")
                    for symbol, alert_time in self.last_alerts.items():
                        time_ago = int(time.time() - alert_time)
                        self.console.print(f"   • {symbol}: {time_ago}s ago")

                # Wait for next update
                time.sleep(update_interval)

        except KeyboardInterrupt:
            self.console.print("\n\n[bold yellow]⏸️ Bot stopped by user[/bold yellow]")
            self.running = False

    def run(self, once: bool = False):
        """
        Run the bot

        Args:
            once: If True, run once and exit; otherwise run continuously
        """
        if once:
            self.run_once()
        else:
            self.run_continuous()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Crypto Signal Bot - Technical Analysis for Prediction Markets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Start continuous monitoring
  python main.py --once             # Run analysis once
  python main.py --symbols BTC ETH  # Monitor specific symbols
  python main.py --config custom.yaml  # Use custom config
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--symbols', '-s',
        nargs='+',
        help='Symbols to monitor (e.g., BTC ETH SOL)'
    )

    parser.add_argument(
        '--once', '-o',
        action='store_true',
        help='Run analysis once and exit'
    )

    parser.add_argument(
        '--demo', '-d',
        action='store_true',
        help='Use demo mode with simulated data (for testing)'
    )

    args = parser.parse_args()

    # Initialize bot
    bot = CryptoSignalBot(config_path=args.config, demo_mode=args.demo)

    # Override symbols if provided
    if args.symbols:
        # Convert to USDT format
        symbols = [f"{s}USDT" if not s.endswith('USDT') else s for s in args.symbols]
        bot.config['symbols'] = symbols
        bot.market_monitor.symbols = symbols

    # Run bot
    try:
        bot.run(once=args.once)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
