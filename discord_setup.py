#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manual Discord Setup - Edit config and test
"""

import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def show_instructions():
    print("\n" + "="*70)
    print("🔔 Discord Setup - Manual Instructions")
    print("="*70 + "\n")

    print("STEP 1: Create Discord Webhook")
    print("-"*70)
    print("1. Open Discord → Your Server")
    print("2. Click ⚙️ Settings (next to server name)")
    print("3. Integrations → Webhooks → New Webhook")
    print("4. Name: Crypto Signal Bot")
    print("5. Choose channel")
    print("6. Copy Webhook URL\n")

    print("Your URL will look like:")
    print("https://discord.com/api/webhooks/1234567890/AbCdEfGhIjKlMnOpQrStUvWxYz\n")

    print("="*70)
    print("STEP 2: Edit config.yaml")
    print("="*70 + "\n")

    print("Find this section in config.yaml:\n")
    print("  discord:")
    print("    enabled: false")
    print("    webhook_url: \"\"\n")

    print("Change it to:\n")
    print("  discord:")
    print("    enabled: true")
    print("    webhook_url: \"https://discord.com/api/webhooks/YOUR_URL_HERE\"\n")

    print("="*70)
    print("STEP 3: Test")
    print("="*70 + "\n")

    print("Run the test script:")
    print("  python test_discord.py\n")

    print("Or run the bot (will send alerts automatically):")
    print("  python main_ultimate.py --once --demo\n")

    print("="*70)
    print("Need the setup guide?")
    print("="*70 + "\n")

    print("See: DISCORD_QUICK_SETUP.md\n")


if __name__ == "__main__":
    show_instructions()
