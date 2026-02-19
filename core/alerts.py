"""
Alerts Module - Handles notifications for trading signals
"""

import sys
import winsound
import platform
from typing import Dict, Optional
from datetime import datetime


class AlertManager:
    """Manage alerts for trading signals"""

    def __init__(self, config: Dict):
        """
        Initialize alert manager

        Args:
            config: Configuration dictionary with alert settings
        """
        self.config = config
        self.alert_config = config.get('alerts', {})
        self.sound_enabled = bool(self.alert_config.get('sound'))
        self.console_enabled = self.alert_config.get('console', True)
        self.telegram_enabled = self.alert_config.get('telegram', {}).get('enabled', False)
        self.discord_enabled = self.alert_config.get('discord', {}).get('enabled', False)

    def send_alert(self, signal_analysis: Dict):
        """
        Send alert through all enabled channels

        Args:
            signal_analysis: Signal analysis dictionary
        """
        # Console alert (always enabled by default)
        if self.console_enabled:
            self._console_alert(signal_analysis)

        # Sound alert
        if self.sound_enabled:
            self._sound_alert()

        # Telegram alert (optional)
        if self.telegram_enabled:
            self._telegram_alert(signal_analysis)

        # Discord alert (optional)
        if self.discord_enabled:
            self._discord_alert(signal_analysis)

    def _console_alert(self, signal_analysis: Dict):
        """
        Print alert to console with formatting

        Args:
            signal_analysis: Signal analysis dictionary
        """
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        # Create colored text based on signal
        signal = signal_analysis['signal']
        confidence = signal_analysis['confidence']

        if 'STRONG YES' in signal or 'YES' in signal:
            color = "green"
        elif 'STRONG NO' in signal or 'NO' in signal:
            color = "red"
        else:
            color = "yellow"

        # Build message
        symbol = signal_analysis['symbol']
        message = Text()
        message.append(f"\n🚨 SIGNAL ALERT: {symbol}\n", style="bold white")
        message.append(f"Signal: ", style="white")
        message.append(f"{signal}", style=f"bold {color}")
        message.append(f" (Confidence: {confidence}%)\n", style="white")

        advice = signal_analysis.get('prediction_advice', {})
        if advice.get('action'):
            message.append(f"\n💡 Action: {advice['action']}\n", style="bold cyan")

            if advice.get('target_price'):
                message.append(f"   Target: {advice['target_direction']} ${advice['target_price']}\n", style="cyan")
                message.append(f"   Timeframe: {advice['timeframe']}\n", style="cyan")
                message.append(f"   Risk: {advice['risk_level']}\n", style="cyan")

        message.append(f"\n📈 Reasons:\n", style="white")
        for i, reason in enumerate(signal_analysis.get('reasons', []), 1):
            message.append(f"   {i}. {reason}\n", style="white")

        message.append(f"\n⏰ {signal_analysis['timestamp']}\n", style="dim white")

        # Create panel
        panel = Panel(
            message,
            title=f"[bold]{symbol} Trading Signal[/bold]",
            border_style=color,
            padding=(1, 2)
        )

        console.print(panel)

    def _sound_alert(self):
        """Play sound alert"""
        try:
            sound_file = self.alert_config.get('sound')

            if platform.system() == "Windows":
                if sound_file:
                    # Play custom sound file
                    winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                else:
                    # Play default Windows beep
                    winsound.Beep(1000, 500)  # 1000Hz for 500ms
            elif platform.system() == "Darwin":  # macOS
                import os
                os.system('afplay /System/Library/Sounds/Glass.aiff')
            elif platform.system() == "Linux":
                import os
                # Try to play a system sound
                os.system('paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || '
                         'aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null')

        except Exception as e:
            # Silently fail if sound doesn't work
            pass

    def _telegram_alert(self, signal_analysis: Dict):
        """
        Send alert via Telegram bot

        Args:
            signal_analysis: Signal analysis dictionary
        """
        try:
            import requests

            telegram_config = self.alert_config.get('telegram', {})
            bot_token = telegram_config.get('bot_token')
            chat_id = telegram_config.get('chat_id')

            if not bot_token or not chat_id:
                print("⚠️ Telegram not configured: Missing bot_token or chat_id")
                return

            # Format message
            message = self._format_telegram_message(signal_analysis)

            # Send message
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

        except Exception as e:
            print(f"⚠️ Failed to send Telegram alert: {e}")

    def _format_telegram_message(self, signal_analysis: Dict) -> str:
        """
        Format signal analysis for Telegram message

        Args:
            signal_analysis: Signal analysis dictionary

        Returns:
            Formatted message string for Telegram
        """
        symbol = signal_analysis['symbol']
        signal = signal_analysis['signal']
        confidence = signal_analysis['confidence']
        advice = signal_analysis.get('prediction_advice', {})

        # Determine emoji based on signal
        if 'STRONG YES' in signal:
            emoji = "🟢"
        elif 'YES' in signal:
            emoji = "🟡"
        elif 'STRONG NO' in signal:
            emoji = "🔴"
        elif 'NO' in signal:
            emoji = "🟠"
        else:
            emoji = "⚪"

        lines = [
            f"{emoji} <b>SIGNAL ALERT: {symbol}</b>",
            "",
            f"📊 <b>Signal:</b> {signal}",
            f"📈 <b>Confidence:</b> {confidence}%",
            ""
        ]

        if advice.get('action'):
            lines.extend([
                f"💡 <b>Action:</b> {advice['action']}",
            ])

            if advice.get('target_price'):
                lines.extend([
                    f"   <b>Target:</b> {advice['target_direction']} ${advice['target_price']}",
                    f"   <b>Timeframe:</b> {advice['timeframe']}",
                    f"   <b>Risk:</b> {advice['risk_level']}",
                ])

        lines.append("")
        lines.append("📈 <b>Technical Reasons:</b>")
        for i, reason in enumerate(signal_analysis.get('reasons', []), 1):
            lines.append(f"   {i}. {reason}")

        lines.append("")
        lines.append(f"⏰ {signal_analysis['timestamp']}")

        return "\n".join(lines)

    def _discord_alert(self, signal_analysis: Dict):
        """
        Send alert via Discord webhook

        Args:
            signal_analysis: Signal analysis dictionary
        """
        try:
            import requests

            discord_config = self.alert_config.get('discord', {})
            webhook_url = discord_config.get('webhook_url')

            if not webhook_url:
                print("⚠️ Discord not configured: Missing webhook_url")
                return

            # Format message with embed
            embed = self._format_discord_embed(signal_analysis)

            # Send message
            data = {
                'embeds': [embed],
                'username': 'Crypto Signal Bot',
                'avatar_url': 'https://i.imgur.com/zxBaQ8k.png'  # Default avatar
            }

            response = requests.post(webhook_url, json=data, timeout=10)
            response.raise_for_status()

        except Exception as e:
            print(f"⚠️ Failed to send Discord alert: {e}")

    def _format_discord_embed(self, signal_analysis: Dict) -> Dict:
        """
        Format signal analysis as Discord embed

        Args:
            signal_analysis: Signal analysis dictionary

        Returns:
            Discord embed dictionary
        """
        symbol = signal_analysis['symbol']
        signal = signal_analysis['signal']
        confidence = signal_analysis['confidence']
        advice = signal_analysis.get('prediction_advice', {})
        indicators = signal_analysis.get('indicators', {})

        # Determine color based on signal
        if 'STRONG YES' in signal or 'YES' in signal:
            color = 5763719  # Green
            emoji = "🟢"
        elif 'STRONG NO' in signal or 'NO' in signal:
            color = 15548997  # Red
            emoji = "🔴"
        else:
            color = 16776960  # Yellow
            emoji = "⚪"

        # Build description
        description = f"**{emoji} Signal:** {signal}\n"
        description += f"**📈 Confidence:** {confidence}%\n\n"

        if advice.get('action'):
            description += f"**💡 Action:** {advice['action']}\n"

            if advice.get('target_price'):
                description += f"**🎯 Target:** {advice['target_direction']} `${advice['target_price']}`\n"
                description += f"**⏱️ Timeframe:** {advice['timeframe']}\n"
                description += f"**⚠️ Risk:** {advice['risk_level']}\n"

        # Build fields
        fields = []

        # Technical reasons
        reasons = signal_analysis.get('reasons', [])
        if reasons:
            reasons_text = "\n".join([f"{i}. {r}" for i, r in enumerate(reasons, 1)])
            fields.append({
                'name': '📊 Technical Reasons',
                'value': reasons_text,
                'inline': False
            })

        # Key indicators
        indicator_lines = []

        if 'rsi' in indicators:
            rsi = indicators['rsi']
            rsi_status = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
            indicator_lines.append(f"**RSI:** {rsi:.1f} ({rsi_status})")

        if 'macd_trend' in indicators:
            indicator_lines.append(f"**MACD:** {indicators['macd_trend'].upper()}")

        if 'ema_cross' in indicators:
            indicator_lines.append(f"**EMA Cross:** {indicators['ema_cross'].upper()}")

        if 'bb_percent' in indicators:
            bb = indicators['bb_percent']
            bb_status = "Upper Band" if bb > 80 else "Lower Band" if bb < 20 else "Middle"
            indicator_lines.append(f"**Bollinger:** {bb:.1f}% ({bb_status})")

        if 'volume_ratio' in indicators:
            vol = indicators['volume_ratio']
            indicator_lines.append(f"**Volume:** {vol:.0f}% of avg")

        if indicator_lines:
            fields.append({
                'name': '📈 Key Indicators',
                'value': "\n".join(indicator_lines),
                'inline': True
            })

        # Support/Resistance
        if 'support' in indicators and 'resistance' in indicators:
            current = indicators.get('current', indicators.get('close', 0))
            fields.append({
                'name': '🎯 Levels',
                'value': f"**Support:** `${indicators['support']:,.4f}`\n"
                        f"**Current:** `${current:,.4f}`\n"
                        f"**Resistance:** `${indicators['resistance']:,.4f}`",
                'inline': True
            })

        # Create embed
        embed = {
            'title': f"🚨 Signal Alert: {symbol}",
            'description': description,
            'color': color,
            'fields': fields,
            'footer': {
                'text': f"⏰ {signal_analysis['timestamp']} | Crypto Signal Bot v1.0"
            },
            'thumbnail': {
                'url': self._get_coin_image(symbol)
            }
        }

        return embed

    def _get_coin_image(self, symbol: str) -> str:
        """Get coin image URL for Discord embed"""
        # Map symbols to coin images
        images = {
            'BTCUSDT': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png',
            'ETHUSDT': 'https://cryptologos.cc/logos/ethereum-eth-logo.png',
            'SOLUSDT': 'https://cryptologos.cc/logos/solana-sol-logo.png',
            'BNBUSDT': 'https://cryptologos.cc/logos/binance-coin-bnb-logo.png',
            'ADAUSDT': 'https://cryptologos.cc/logos/cardano-ada-logo.png',
            'AVAXUSDT': 'https://cryptologos.cc/logos/avalanche-avax-logo.png',
            'MATICUSDT': 'https://cryptologos.cc/logos/polygon-matic-logo.png',
            'DOTUSDT': 'https://cryptologos.cc/logos/polkadot-new-dot-logo.png',
        }
        return images.get(symbol, 'https://cryptologos.cc/logos/bitcoin-btc-logo.png')

    def log_signal(self, signal_analysis: Dict):
        """
        Log signal to file for historical analysis

        Args:
            signal_analysis: Signal analysis dictionary
        """
        try:
            import os
            from pathlib import Path

            # Create logs directory
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            # Log file with today's date
            log_file = logs_dir / f"signals_{datetime.now().strftime('%Y%m%d')}.log"

            # Format log entry
            log_entry = (
                f"[{signal_analysis['timestamp']}] "
                f"{signal_analysis['symbol']} | "
                f"Signal: {signal_analysis['signal']} | "
                f"Confidence: {signal_analysis['confidence']}% | "
                f"Reasons: {', '.join(signal_analysis['reasons'])}\n"
            )

            # Append to log file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"⚠️ Failed to log signal: {e}")
