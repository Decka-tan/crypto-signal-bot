#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Signal Bot - PRO Mode
Multi-timeframe analysis with advanced indicators for higher accuracy

Usage:
    python main_pro.py --demo              # Run with demo data
    python main_pro.py --symbols BTC ETH   # Monitor specific symbols
"""

import sys
import io
import time
import argparse
import yaml
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from core.market_monitor import MarketMonitor
from core.pro_signals import ProSignalGenerator
from core.alerts import AlertManager


class CryptoSignalBotPro:
    """Pro version with multi-timeframe analysis"""

    def __init__(self, config_path: str = "config.yaml", demo_mode: bool = False):
        """Initialize pro bot"""
        self.config = self._load_config(config_path)
        self.console = Console()

        # Initialize market monitor
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
        timeframe = self.config.get('timeframe', '15m')

        self.market_monitor = MarketMonitor(symbols, timeframe, demo_mode=demo_mode)
        self.signal_generator = ProSignalGenerator(self.config, self.market_monitor)
        self.alert_manager = AlertManager(self.config)

        self.running = False
        self.last_alerts = {}

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ Config not found: {config_path}")
            return self._default_config()
        except Exception as e:
            print(f"⚠️ Error loading config: {e}")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            'timeframe': '15m',
            'thresholds': {
                'min_confidence': 70  # Higher threshold for pro mode
            },
            'alerts': {
                'console': True,
                'discord': {'enabled': False}
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
        """Analyze symbol with multi-timeframe analysis"""
        try:
            return self.signal_generator.analyze_multi_timeframe(symbol)
        except Exception as e:
            self.console.print(f"[red]Error analyzing {symbol}: {e}[/red]")
            return None

    def check_and_alert(self, signal_analysis: Dict):
        """Check if signal should trigger alert"""
        if signal_analysis is None:
            return

        symbol = signal_analysis['symbol']
        confidence = signal_analysis['confidence']
        min_confidence = self.config.get('thresholds', {}).get('min_confidence', 70)

        # Check if signal meets threshold
        signal_type = signal_analysis['signal_type']

        from core.pro_signals import SignalType

        if signal_type != SignalType.HOLD and confidence >= min_confidence:
            # Check cooldown
            last_alert_time = self.last_alerts.get(symbol, 0)
            current_time = time.time()
            cooldown = self.config.get('display', {}).get('update_interval', 30) * 2

            if current_time - last_alert_time > cooldown:
                self.alert_manager.send_alert(signal_analysis)
                self.last_alerts[symbol] = current_time

    def create_summary_table(self, all_signals: Dict) -> Table:
        """Create summary table"""
        table = Table(
            title="[bold cyan]📊 Crypto Signal Bot PRO - Multi-Timeframe Analysis[/bold cyan]",
            box=box.ROUNDED
        )

        table.add_column("Symbol", style="cyan bold", width=12)
        table.add_column("Signal", style="bold", width=15)
        table.add_column("Confidence", width=12)
        table.add_column("TF Agreement", width=14)
        table.add_column("Trend", width=12)
        table.add_column("Price", style="yellow", width=12)

        for symbol, analysis in all_signals.items():
            if analysis is None:
                table.add_row(symbol, "[dim]No data[/dim]", "-", "-", "-", "-")
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

            # Get data
            confidence = analysis['confidence']
            agreement = analysis['agreement']
            trend = analysis['trend_strength']

            # Get price from any timeframe
            price = "-"
            if analysis['timeframe_signals']:
                for tf_data in analysis['timeframe_signals'].values():
                    if 'current' in tf_data.get('indicators', {}):
                        price = f"${tf_data['indicators']['current']:,.4f}"
                        break

            table.add_row(
                symbol,
                signal_style,
                f"{confidence}%",
                f"{agreement}%",
                trend,
                price
            )

        return table

    def run_continuous(self):
        """Run continuous monitoring"""
        self.console.print("\n[bold green]🚀 Crypto Signal Bot PRO - Live Monitoring[/bold green]")
        self.console.print("[dim]Multi-timeframe analysis | Press Ctrl+C to stop[/dim]\n")

        self.running = True
        update_interval = self.config.get('display', {}).get('update_interval', 30)

        try:
            while self.running:
                self.console.clear()

                # Header
                self.console.print(
                    f"[bold cyan]📊 PRO Mode[/bold cyan] | "
                    f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] | "
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

                # Display table
                table = self.create_summary_table(all_signals)
                self.console.print(table)

                # Display recent alerts
                if self.last_alerts:
                    self.console.print(f"\n[bold]🔔 Recent Alerts:[/bold]")
                    for symbol, alert_time in self.last_alerts.items():
                        time_ago = int(time.time() - alert_time)
                        self.console.print(f"   • {symbol}: {time_ago}s ago")

                time.sleep(update_interval)

        except KeyboardInterrupt:
            self.console.print("\n\n[bold yellow]⏸️ Bot stopped[/bold yellow]")
            self.running = False

    def run_once(self):
        """Run analysis once"""
        self.console.print("\n[bold cyan]🚀 PRO Mode - Single Analysis[/bold cyan]\n")

        self.console.print("📡 Fetching market data...")

        # Analyze all symbols
        all_signals = {}
        for symbol in self.market_monitor.symbols:
            self.console.print(f"   Analyzing [cyan]{symbol}[/cyan] (multi-timeframe)...")
            signal = self.analyze_symbol(symbol)
            all_signals[symbol] = signal

        # Display summary
        table = self.create_summary_table(all_signals)
        self.console.print(table)

        # Show detailed alerts
        self.console.print("\n[bold]📨 Detailed Analysis:[/bold]\n")
        for symbol, analysis in all_signals.items():
            if analysis and analysis['confidence'] >= 70:
                self._display_detailed_analysis(analysis)

    def _display_detailed_analysis(self, analysis: Dict):
        """Display detailed analysis for a signal"""
        from rich.text import Text

        message = Text()
        message.append(f"\n{'='*60}\n", style="white")
        message.append(f"Symbol: {analysis['symbol']}\n", style="bold cyan")
        message.append(f"Signal: {analysis['signal']}\n", style="bold")
        message.append(f"Confidence: {analysis['confidence']}%\n", style="bold")
        message.append(f"Timeframe Agreement: {analysis['agreement']}%\n", style="white")
        message.append(f"Trend Strength: {analysis['trend_strength']}\n", style="white")

        message.append(f"\nTimeframe Analysis:\n", style="bold white")
        for tf, tf_data in analysis['timeframe_signals'].items():
            signal = tf_data['signal_type'].value
            score = tf_data['score']
            message.append(f"  {tf}: {signal} (score: {score:.2f})\n", style="white")

        message.append(f"\nReasons:\n", style="bold white")
        for reason in analysis['reasons']:
            message.append(f"  • {reason}\n", style="white")

        message.append(f"{'='*60}\n", style="white")

        panel = Panel(message, border_style="cyan")
        self.console.print(panel)

    def run(self, once: bool = False):
        """Run the bot"""
        if once:
            self.run_once()
        else:
            self.run_continuous()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Crypto Signal Bot PRO - Multi-Timeframe Analysis"
    )

    parser.add_argument('--config', '-c', default='config.yaml', help='Config file')
    parser.add_argument('--symbols', '-s', nargs='+', help='Symbols to monitor')
    parser.add_argument('--once', '-o', action='store_true', help='Run once')
    parser.add_argument('--demo', '-d', action='store_true', help='Demo mode')

    args = parser.parse_args()

    # Initialize bot
    bot = CryptoSignalBotPro(config_path=args.config, demo_mode=args.demo)

    # Override symbols
    if args.symbols:
        symbols = [f"{s}USDT" if not s.endswith('USDT') else s for s in args.symbols]
        bot.config['symbols'] = symbols
        bot.market_monitor.symbols = symbols

    # Run
    try:
        bot.run(once=args.once)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
