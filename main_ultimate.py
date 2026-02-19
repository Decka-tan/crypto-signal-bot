#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Signal Bot - ULTIMATE Mode
Institutional-grade analysis combining:
- Multi-timeframe technical analysis
- Machine learning predictions
- Sentiment analysis
- Correlation analysis
- Funding rates
"""

import sys
import io
import time
import argparse
import yaml
import traceback

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from core.market_monitor import MarketMonitor
from core.ultimate_signals import UltimateSignalGenerator
from core.alerts import AlertManager


class CryptoSignalBotUltimate:
    """Ultimate version with all analysis methods"""

    def __init__(self, config_path: str = "config.yaml", demo_mode: bool = False):
        """Initialize ultimate bot"""
        self.config = self._load_config(config_path)
        self.console = Console()

        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
        timeframe = self.config.get('timeframe', '15m')

        exchange = self.config.get('exchange', 'auto')
        self.market_monitor = MarketMonitor(symbols, timeframe, demo_mode=demo_mode, exchange=exchange)
        self.signal_generator = UltimateSignalGenerator(self.config, self.market_monitor)
        self.alert_manager = AlertManager(self.config)

        self.running = False
        self.last_alerts = {}

    def _load_config(self, config_path: str):
        """Load configuration"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except:
            return self._default_config()

    def _default_config(self):
        """Default configuration"""
        return {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
            'timeframe': '15m',
            'thresholds': {'min_confidence': 75},
            'alerts': {'console': True, 'discord': {'enabled': False}},
            'display': {'update_interval': 60}
        }

    def analyze_symbol(self, symbol: str):
        """Analyze symbol with ultimate method"""
        return self.signal_generator.generate_ultimate_signal(symbol)

    def check_and_alert(self, signal_analysis):
        """Check and send alert"""
        if not signal_analysis or signal_analysis.get('error'):
            return

        symbol = signal_analysis['symbol']
        confidence = signal_analysis['confidence']
        min_conf = self.config.get('thresholds', {}).get('min_confidence', 75)

        from core.ultimate_signals import SignalType

        if signal_analysis['signal_type'] != SignalType.HOLD and confidence >= min_conf:
            last_time = self.last_alerts.get(symbol, 0)
            if time.time() - last_time > 120:  # 2 min cooldown
                self.alert_manager.send_alert(signal_analysis)
                self.last_alerts[symbol] = time.time()

    def create_summary_table(self, all_signals):
        """Create ultimate summary table"""
        table = Table(
            title="[bold magenta]ULTIMATE Crypto Signal Bot[/bold magenta] 🚀\n[dim]All-Mode Analysis: Technical + ML + Sentiment + Correlation + Funding[/dim]",
            box=box.DOUBLE_EDGE
        )

        table.add_column("Symbol", style="cyan bold", width=10)
        table.add_column("Signal", style="bold", width=15)
        table.add_column("Confidence", width=10)
        table.add_column("Tech", width=8)
        table.add_column("ML", width=8)
        table.add_column("Sentiment", width=10)
        table.add_column("Funding", width=10)

        for symbol, analysis in all_signals.items():
            if not analysis or analysis.get('error'):
                table.add_row(symbol, "[dim]No data[/dim]", "-", "-", "-", "-", "-")
                continue

            signal = analysis['signal']
            if 'ULTIMATE YES' in signal:
                signal_style = "[bold bright_magenta]ULTIMATE YES[/bold bright_magenta]"
            elif 'STRONG YES' in signal:
                signal_style = "[bold green]STRONG YES[/bold green]"
            elif 'YES' in signal:
                signal_style = "[green]YES[/green]"
            elif 'ULTIMATE NO' in signal:
                signal_style = "[bold bright_red]ULTIMATE NO[/bold bright_red]"
            elif 'STRONG NO' in signal:
                signal_style = "[bold red]STRONG NO[/bold red]"
            elif 'NO' in signal:
                signal_style = "[red]NO[/red]"
            else:
                signal_style = "[yellow]HOLD[/yellow]"

            conf = analysis['confidence']

            # Module scores
            combined = analysis.get('combined_scores', {})
            signals = combined.get('module_signals', {})

            tech_score = "✓" if signals.get('technical', 0.5) > 0.6 else ("×" if signals.get('technical', 0.5) < 0.4 else "≈")
            ml_score = "✓" if signals.get('ml', 0.5) > 0.6 else ("×" if signals.get('ml', 0.5) < 0.4 else "≈")
            sent_score = "✓" if signals.get('sentiment', 0.5) > 0.6 else ("×" if signals.get('sentiment', 0.5) < 0.4 else "≈")
            fund_score = "✓" if signals.get('funding', 0.5) > 0.6 else ("×" if signals.get('funding', 0.5) < 0.4 else "≈")

            table.add_row(
                symbol,
                signal_style,
                f"{conf}%",
                tech_score,
                ml_score,
                sent_score,
                fund_score
            )

        return table

    def display_detailed_analysis(self, analysis):
        """Display detailed ultimate analysis"""
        if not analysis or analysis.get('error'):
            return

        symbol = analysis['symbol']
        signal = analysis['signal']
        confidence = analysis['confidence']

        # Build detailed panel
        lines = []
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")
        lines.append(f"[bold white]ULTIMATE ANALYSIS: {symbol}[/bold white]")
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")
        lines.append("")
        lines.append(f"[bold {self._get_signal_color(signal)}]SIGNAL: {signal}[/bold {self._get_signal_color(signal)}]")
        lines.append(f"[bold white]CONFIDENCE: {confidence}%[/bold white]")
        lines.append("")

        # Module breakdown
        analyses = analysis.get('analyses', {})

        lines.append("[bold yellow]📊 Module Breakdown:[/bold yellow]")

        # Technical
        tech = analyses.get('technical', {})
        if tech and 'error' not in tech:
            lines.append(f"  🔬 Technical: {tech.get('signal', 'N/A')} ({tech.get('confidence', 0)}%)")
            lines.append(f"     Trend: {tech.get('trend_strength', 'N/A')}")

        # ML
        ml = analyses.get('ml', {})
        if ml and 'error' not in ml:
            lines.append(f"  🤖 ML: {ml.get('prediction', 'N/A')} ({ml.get('ml_confidence', 0)}%)")
            patterns = ml.get('patterns_detected', [])
            if patterns:
                lines.append(f"     Patterns: {', '.join(patterns)}")

        # Sentiment
        sent = analyses.get('sentiment', {})
        if sent and 'error' not in sent:
            lines.append(f"  😊 Sentiment: {sent.get('signal', 'N/A')} (FG: {sent.get('fear_greed', 'N/A')})")

        # Correlation
        corr = analyses.get('correlation', {})
        if corr and 'error' not in corr:
            btc_inf = corr.get('btc_influence', {})
            lines.append(f"  🔗 BTC: {btc_inf.get('trading_implication', 'N/A')}")

        # Funding
        fund = analyses.get('funding', {})
        if fund and 'error' not in fund:
            lines.append(f"  💰 Funding: {fund.get('funding_sentiment', 'N/A')} ({fund.get('funding_rate', 0):.4f})")

        lines.append("")

        # Reasons
        reasons = analysis.get('reasons', [])[:5]
        if reasons:
            lines.append("[bold yellow]📋 Key Reasons:[/bold yellow]")
            for reason in reasons:
                lines.append(f"  • {reason}")

        lines.append("")

        # Actionable advice
        advice = analysis.get('actionable_advice', {})
        if advice:
            lines.append("[bold green]💡 Trading Advice:[/bold green]")
            lines.append(f"  Action: {advice.get('action', 'N/A')}")
            lines.append(f"  Position Size: {advice.get('position_size', 'N/A')}")
            if advice.get('risk_warning'):
                lines.append(f"  [bold red]⚠️  Risk: {'; '.join(advice['risk_warning'])}[/bold red]")

        lines.append("")
        lines.append(f"[bold cyan]{'='*60}[/bold cyan]")

        panel_text = "\n".join(lines)
        panel = Panel(panel_text, border_style="magenta")
        self.console.print(panel)

    def _get_signal_color(self, signal):
        """Get color for signal"""
        if 'YES' in signal:
            return "green"
        elif 'NO' in signal:
            return "red"
        else:
            return "yellow"

    def run_once(self):
        """Run analysis once"""
        self.console.print("\n[bold bright_magenta]ULTIMATE Mode - Full Analysis[/bold bright_magenta] 🚀\n")

        self.console.print("📡 Fetching data and running all analysis modules...")

        all_signals = {}
        for symbol in self.market_monitor.symbols:
            self.console.print(f"   [cyan]{symbol}[/cyan]...", end="\r")
            signal = self.analyze_symbol(symbol)
            all_signals[symbol] = signal

        self.console.print("")  # New line after progress

        # Show summary table
        table = self.create_summary_table(all_signals)
        self.console.print(table)

        # Show detailed for high confidence
        self.console.print("\n[bold]📨 Detailed Analysis (Confidence ≥ 75%):[/bold]\n")

        for symbol, analysis in all_signals.items():
            if analysis and analysis.get('confidence', 0) >= 75:
                self.display_detailed_analysis(analysis)
                self.check_and_alert(analysis)

    def run_continuous(self):
        """Run continuous monitoring"""
        self.console.print("\n[bold bright_magenta]ULTIMATE Mode - Live Monitoring[/bold bright_magenta] 🚀")
        self.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        self.running = True
        interval = self.config.get('display', {}).get('update_interval', 900)
        smart_timing = self.config.get('prediction_market', {}).get('use_smart_timing', True)

        try:
            while self.running:
                self.console.clear()

                self.console.print(
                    f"[bold bright_magenta]ULTIMATE[/bold bright_magenta] 🚀 | "
                    f"[dim]{time.strftime('%H:%M:%S')}[/dim] | "
                    f"[dim]Update every {interval}s ({interval//60} min)[/dim]\n"
                )

                all_signals = {}
                for symbol in self.market_monitor.symbols:
                    signal = self.analyze_symbol(symbol)
                    all_signals[symbol] = signal
                    self.check_and_alert(signal)

                table = self.create_summary_table(all_signals)
                self.console.print(table)

                if smart_timing:
                    current_min = time.localtime().tm_min
                    min_to_next = 15 - (current_min % 15)
                    self.console.print(f"\n[dim]⏰ Next analysis: {min_to_next} min (at XX:{'00' if (current_min // 15 + 1) * 15 < 10 else ''}{(current_min // 15 + 1) * 15:00})[/dim]")

                time.sleep(interval)

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]⏸️  Bot stopped[/yellow]")
            self.running = False

    def run(self, once=False):
        """Run the bot"""
        if once:
            self.run_once()
        else:
            self.run_continuous()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Crypto Signal Bot - ULTIMATE Mode")

    parser.add_argument('--config', '-c', default='config.yaml')
    parser.add_argument('--symbols', '-s', nargs='+')
    parser.add_argument('--once', '-o', action='store_true')
    parser.add_argument('--demo', '-d', action='store_true')

    args = parser.parse_args()

    bot = CryptoSignalBotUltimate(config_path=args.config, demo_mode=args.demo)

    if args.symbols:
        symbols = [f"{s}USDT" if not s.endswith('USDT') else s for s in args.symbols]
        bot.config['symbols'] = symbols
        bot.market_monitor.symbols = symbols

    try:
        bot.run(once=args.once)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n--- Full Traceback ---")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
