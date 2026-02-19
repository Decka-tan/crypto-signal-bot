#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Setup Wizard - Easy webhook configuration
"""

import sys
import io
import yaml
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def setup_discord():
    """Setup Discord webhook"""

    print("\n" + "="*60)
    print("🔔 Discord Alert Setup")
    print("="*60 + "\n")

    print("Step 1: Create a Discord Webhook")
    print("-" * 60)
    print("1. Open your Discord server")
    print("2. Click ⚙️ Settings next to server name")
    print("3. Go to Integrations → Webhooks")
    print("4. Click 'New Webhook'")
    print("5. Name it 'Crypto Signal Bot'")
    print("6. Choose the channel for alerts")
    print("7. Click 'Copy Webhook URL'")
    print()

    webhook_url = input("📋 Paste your webhook URL here (or press Enter to cancel): ").strip()

    if not webhook_url:
        print("\n❌ Setup cancelled. No webhook URL provided.")
        return False

    # Validate URL format
    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("\n⚠️  Warning: URL doesn't look like a Discord webhook.")
        print("   Expected format: https://discord.com/api/webhooks/.../...")
        proceed = input("   Continue anyway? (y/n): ").strip().lower()
        if proceed != 'y':
            print("\n❌ Setup cancelled.")
            return False

    # Load config
    config_path = Path("config.yaml")

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except:
        print(f"\n❌ Error: Cannot read config.yaml")
        return False

    # Update config
    config['alerts']['discord'] = {
        'enabled': True,
        'webhook_url': webhook_url
    }

    # Save config
    try:
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"\n✅ Configuration saved to config.yaml!")

        # Test the webhook
        print("\n" + "="*60)
        print("Step 2: Test the Webhook")
        print("-" * 60)

        test = input("🧪 Send a test alert to Discord? (y/n): ").strip().lower()

        if test == 'y':
            return test_webhook(webhook_url)
        else:
            print("\n✅ Setup complete! Discord alerts are enabled.")
            print("   Run the bot with: python main_ultimate.py --demo")
            return True

    except Exception as e:
        print(f"\n❌ Error saving config: {e}")
        return False


def test_webhook(webhook_url):
    """Test Discord webhook"""
    import requests

    print("\n📡 Sending test alert...")

    # Create test alert
    test_data = {
        'embeds': [{
            'title': '🧪 Test Alert - Crypto Signal Bot',
            'description': '**Your Discord webhook is working!** 🎉\n\nYou will now receive trading signals here.',
            'color': 5763719,  # Green
            'fields': [
                {
                    'name': '✅ Status',
                    'value': 'Discord alerts successfully configured',
                    'inline': True
                },
                {
                    'name': '🚀 Next Step',
                    'value': 'Run the bot: `python main_ultimate.py --demo`',
                    'inline': True
                }
            ],
            'footer': {
                'text': 'Crypto Signal Bot ULTIMATE • Testing Mode'
            },
            'timestamp': '2026-02-19T12:00:00'
        }],
        'username': 'Crypto Signal Bot',
        'avatar_url': 'https://i.imgur.com/zxBaQ8k.png'
    }

    try:
        response = requests.post(webhook_url, json=test_data, timeout=10)
        response.raise_for_status()

        print("\n✅ Test alert sent successfully!")
        print("   Check your Discord channel - you should see a test message.")
        print("\n🎉 Setup complete! Your bot will now send alerts to Discord.")
        print("\n📝 To run the bot:")
        print("   python main_ultimate.py --demo")
        return True

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Failed to send test alert: {e}")
        print("\nTroubleshooting:")
        print("• Check that the webhook URL is correct")
        print("• Make sure the webhook wasn't deleted")
        print("• Try creating a new webhook")
        return False


if __name__ == "__main__":
    success = setup_discord()

    if success:
        print("\n" + "="*60)
        print("✅ Discord Setup Complete!")
        print("="*60)
        print("\nYour bot will now send trading signals to Discord.")
        print("\nCommands:")
        print("  • Run once:     python main_ultimate.py --once --demo")
        print("  • Continuous:   python main_ultimate.py --demo")
        print("  • Compare modes: python test_all_modes.py")
        sys.exit(0)
    else:
        print("\nSetup cancelled or failed. Try again when ready.")
        sys.exit(1)
