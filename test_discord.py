#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Discord webhook - Sends a sample alert to your Discord
"""

import sys
import io

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def test_discord_webhook(webhook_url: str):
    """Send a test alert to Discord"""

    # Sample signal data
    test_signal = {
        'symbol': 'ETHUSDT',
        'signal': 'NO',
        'signal_type': 'SELL',
        'confidence': 73.8,
        'reasons': [
            'RSI neutral (45.3)',
            'MACD bearish (hist: -0.3514)',
            'EMA bearish cross',
            'Volume spike (178% of avg)',
            'Near resistance (1.00% away)'
        ],
        'timestamp': '2026-02-19 11:02:19',
        'indicators': {
            'rsi': 45.3,
            'macd_trend': 'bearish',
            'ema_cross': 'bearish',
            'bb_percent': 35.2,
            'volume_ratio': 178.5,
            'support': 2200.50,
            'resistance': 2250.75,
            'current': 2231.57
        },
        'prediction_advice': {
            'action': 'Bet NO',
            'target_direction': 'BELOW',
            'target_price': 2204.34,
            'timeframe': '15m',
            'risk_level': 'Low'
        }
    }

    # Import alerts module
    from core.alerts import AlertManager

    # Create minimal config
    config = {
        'alerts': {
            'discord': {
                'enabled': True,
                'webhook_url': webhook_url
            }
        }
    }

    # Send alert
    alert_manager = AlertManager(config)
    alert_manager._discord_alert(test_signal)

    print("✅ Test alert sent to Discord!")
    print(f"Check your Discord channel for the alert.")
    print(f"\nTest signal details:")
    print(f"  Symbol: {test_signal['symbol']}")
    print(f"  Signal: {test_signal['signal']}")
    print(f"  Confidence: {test_signal['confidence']}%")


if __name__ == "__main__":
    print("=" * 60)
    print("Discord Webhook Test")
    print("=" * 60)
    print("\nPaste your Discord webhook URL below:")
    print("(Press Enter with empty URL to cancel)\n")

    webhook_url = input("Webhook URL: ").strip()

    if not webhook_url:
        print("\n❌ No webhook URL provided. Test cancelled.")
        sys.exit(0)

    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("\n⚠️  Warning: URL doesn't look like a Discord webhook.")
        print("   Expected format: https://discord.com/api/webhooks/...")

    print("\nSending test alert...")
    test_discord_webhook(webhook_url)
