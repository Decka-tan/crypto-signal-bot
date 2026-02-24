from main_ultimate import CryptoSignalBotUltimate
import yaml

# Load config
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize bot
bot = CryptoSignalBotUltimate(demo_mode=False)

# Refresh active markets first!
print('Refreshing active markets from Unhedged...')
bot.refresh_active_markets()
print('Done!')
print()

# Test analyze_symbol_proper
print('Testing prediction market signal analysis...')
print('=' * 60)

signal = bot.analyze_symbol_proper('CCUSDT')

if 'error' in signal:
    print(f"ERROR: {signal['error']}")
    print(f"Reason: {signal.get('reason', 'Unknown')}")
else:
    print(f"Symbol: {signal['symbol']}")
    print(f"Signal: {signal['signal']}")
    print(f"Confidence: {signal['confidence']:.1f}%")
    print(f"Edge: {signal['edge']*100:+.2f}%")
    print(f"Current: ${signal['current_price']:.6f}")
    print(f"Strike: ${signal.get('strike_price', 'N/A')}")
    print(f"Distance: {signal.get('distance_to_strike', 0):+.2f}%")
    print(f"Bettable: {signal['is_bettable']}")
    print(f"Reasons:")
    for r in signal.get('reasons', []):
        print(f"  - {r}")

print('=' * 60)
