#!/usr/bin/env python3
"""Quick test to find the correct symbol format for COSA/PIRATE on NonKYC."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from nonkyc_client.auth import ApiCredentials, AuthSigner
from nonkyc_client.rest import RestClient

# Get credentials from environment
api_key = os.getenv("NONKYC_API_KEY")
api_secret = os.getenv("NONKYC_API_SECRET")

# Validate credentials are provided
if not api_key or not api_secret:
    print("=" * 80)
    print("ERROR: Missing API Credentials")
    print("=" * 80)
    print("\n❌ No credentials found in environment variables.")
    print("\nTo run this test, set your credentials:")
    print("  export NONKYC_API_KEY='your_key_here'")
    print("  export NONKYC_API_SECRET='your_secret_here'")
    print("  python test_symbol_formats.py")
    print("\nAlternatively, pass them as arguments:")
    print("  python test_symbol_formats.py YOUR_API_KEY YOUR_API_SECRET")

    if len(sys.argv) == 3:
        api_key = sys.argv[1]
        api_secret = sys.argv[2]
        print("\n✓ Using credentials from command line arguments\n")
    else:
        sys.exit(1)

credentials = ApiCredentials(api_key=api_key, api_secret=api_secret)

# Create AuthSigner with 13-digit nonce (CRITICAL for NonKYC!)
signer = AuthSigner(
    nonce_multiplier=1e3,  # 13 digits - REQUIRED
    sort_params=False,
    sort_body=False,
)

# Create RestClient with CORRECT authentication parameters
# This MUST match the working bots (run_infinity_grid.py, debug_auth.py)
client = RestClient(
    base_url="https://api.nonkyc.io/api/v2",  # Correct base URL with /api/v2
    credentials=credentials,
    signer=signer,
    sign_absolute_url=True,  # CRITICAL - sign full URL, not just path
    timeout=10.0,
    max_retries=3,
    backoff_factor=0.5,
)

# Different symbol formats to test
test_formats = [
    # Slash separator
    "COSA/USDT",
    "COSA/BTC",
    "PIRATE/USDT",
    "PIRATE/BTC",
    # Dash separator
    "COSA-USDT",
    "COSA-BTC",
    "PIRATE-USDT",
    "PIRATE-BTC",
    # Underscore separator
    "COSA_USDT",
    "COSA_BTC",
    "PIRATE_USDT",
    "PIRATE_BTC",
    # No separator
    "COSAUSDT",
    "COSABTC",
    "PIRATEUSDT",
    "PIRATEBTC",
    # Lowercase
    "cosa/usdt",
    "cosa/btc",
    "pirate/usdt",
    "pirate/btc",
    "cosa-usdt",
    "cosa-btc",
    "pirate-usdt",
    "pirate-btc",
]

print("=" * 80)
print("Testing Symbol Formats for COSA and PIRATE")
print("=" * 80)

working_symbols = []

for symbol in test_formats:
    try:
        ticker = client.get_market_data(symbol)
        print(f"✅ WORKS: {symbol:<20} | Last: {ticker.last_price}")
        working_symbols.append(symbol)
    except Exception as e:
        error_msg = str(e)[:50]
        print(f"❌ FAILS: {symbol:<20} | {error_msg}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if working_symbols:
    print(f"\n✅ Found {len(working_symbols)} working symbols:\n")
    for symbol in working_symbols:
        print(f"  • {symbol}")

    print("\n💡 Update your config file with these symbols:")
    print("\norderbook_pairs:")
    for symbol in working_symbols:
        print(f'  - "{symbol}"')
else:
    print("\n❌ No working symbol formats found!")
    print("\nPossible issues:")
    print("  1. COSA/PIRATE tokens don't exist on NonKYC")
    print("  2. Different token names (check NonKYC website)")
    print("  3. API authentication issue")
    print("  4. Different base URL needed")

print("\n" + "=" * 80)
