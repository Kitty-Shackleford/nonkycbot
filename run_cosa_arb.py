#!/usr/bin/env python
"""PIRATE/BTC/COSA Triangular Arbitrage Bot - Starting with PIRATE"""

import sys
import os
import time
import yaml
from decimal import Decimal
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from nonkyc_client.rest import RestClient
from nonkyc_client.auth import ApiCredentials
from nonkyc_client.models import OrderRequest
from strategies.triangular_arb import find_profitable_cycle, evaluate_cycle


def load_config(config_file):
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


def get_price(client, pair):
    """Fetch current market price for a trading pair."""
    try:
        ticker = client.get_market_data(pair)
        price = Decimal(ticker.last_price)
        print(f"  {pair}: {price}")
        return price
    except Exception as e:
        print(f"  ERROR fetching {pair}: {e}")
        return None


def calculate_conversion_rates(config, prices):
    """Calculate conversion rates for the triangular cycle."""
    # PIRATE → BTC → COSA → PIRATE
    pair_ab = config['pair_ab']  # PIRATE/BTC
    pair_bc = config['pair_bc']  # COSA/BTC
    pair_ac = config['pair_ac']  # COSA/PIRATE

    # For each step, calculate how much we get
    # Step 1: PIRATE → BTC (sell PIRATE for BTC)
    # PIRATE/BTC means price in BTC, so that's how much BTC per PIRATE
    pirate_btc_rate = prices[pair_ab]  # How much BTC per PIRATE

    # Step 2: BTC → COSA (buy COSA with BTC)
    # COSA/BTC means price in BTC, so we need to invert
    cosa_btc_price = prices[pair_bc]  # BTC per COSA
    btc_cosa_rate = Decimal("1") / cosa_btc_price  # COSA per BTC

    # Step 3: COSA → PIRATE (sell COSA for PIRATE)
    # COSA/PIRATE means price in PIRATE, so that's PIRATE per COSA
    cosa_pirate_rate = prices[pair_ac]  # PIRATE per COSA

    return {
        'step1': pirate_btc_rate,    # PIRATE → BTC
        'step2': btc_cosa_rate,      # BTC → COSA
        'step3': cosa_pirate_rate,   # COSA → PIRATE
    }


def execute_arbitrage(client, config, prices):
    """Execute the arbitrage cycle."""
    start_amount = Decimal(str(config['trade_amount_a']))

    print(f"\n🔄 EXECUTING ARBITRAGE CYCLE")
    print(f"Starting amount: {start_amount} PIRATE")

    try:
        # Step 1: Sell PIRATE for BTC
        print(f"\nStep 1: Selling PIRATE for BTC...")
        order1 = OrderRequest(
            symbol=config['pair_ab'],
            side="sell",
            order_type=config['order_type'],
            quantity=str(start_amount)
        )
        response1 = client.place_order(order1)
        print(f"  Order ID: {response1.order_id}, Status: {response1.status}")

        # TODO: Wait for order to fill and get actual BTC amount received
        # For now, estimate based on price
        btc_amount = start_amount * prices[config['pair_ab']]
        btc_amount = btc_amount * (Decimal("1") - Decimal(str(config['fee_rate'])))
        print(f"  Received: ~{btc_amount} BTC")

        time.sleep(2)  # Brief pause between orders

        # Step 2: Buy COSA with BTC
        print(f"\nStep 2: Buying COSA with BTC...")
        cosa_amount = btc_amount / prices[config['pair_bc']]
        order2 = OrderRequest(
            symbol=config['pair_bc'],
            side="buy",
            order_type=config['order_type'],
            quantity=str(cosa_amount)
        )
        response2 = client.place_order(order2)
        print(f"  Order ID: {response2.order_id}, Status: {response2.status}")

        cosa_amount = cosa_amount * (Decimal("1") - Decimal(str(config['fee_rate'])))
        print(f"  Received: ~{cosa_amount} COSA")

        time.sleep(2)

        # Step 3: Sell COSA for PIRATE
        print(f"\nStep 3: Selling COSA for PIRATE...")
        order3 = OrderRequest(
            symbol=config['pair_ac'],
            side="sell",
            order_type=config['order_type'],
            quantity=str(cosa_amount)
        )
        response3 = client.place_order(order3)
        print(f"  Order ID: {response3.order_id}, Status: {response3.status}")

        final_pirate = cosa_amount * prices[config['pair_ac']]
        final_pirate = final_pirate * (Decimal("1") - Decimal(str(config['fee_rate'])))
        print(f"  Received: ~{final_pirate} PIRATE")

        profit = final_pirate - start_amount
        profit_pct = (profit / start_amount) * 100

        print(f"\n✅ CYCLE COMPLETE!")
        print(f"Started with: {start_amount} PIRATE")
        print(f"Ended with: {final_pirate} PIRATE")
        print(f"Profit: {profit} PIRATE ({profit_pct:.2f}%)")

        return True

    except Exception as e:
        print(f"\n❌ ERROR during execution: {e}")
        return False


def run_arbitrage_bot(config_file):
    """Main bot loop."""
    print("=" * 80)
    print("PIRATE/BTC/COSA Triangular Arbitrage Bot")
    print("=" * 80)

    # Load config
    config = load_config(config_file)
    print(f"\n📋 Configuration:")
    print(f"  Triangle: {config['asset_a']} → {config['asset_b']} → {config['asset_c']} → {config['asset_a']}")
    print(f"  Trade amount: {config['trade_amount_a']} {config['asset_a']}")
    print(f"  Min profitability: {float(config['min_profitability'])*100}%")
    print(f"  Fee rate: {float(config['fee_rate'])*100}%")
    print(f"  Refresh time: {config['refresh_time']}s")

    # Setup client
    creds = ApiCredentials(
        api_key=config['api_key'],
        api_secret=config['api_secret']
    )
    client = RestClient(base_url="https://api.nonkyc.io", credentials=creds)

    print("\n✅ Connected to NonKYC API")

    cycle_count = 0

    try:
        while True:
            cycle_count += 1
            print(f"\n{'=' * 80}")
            print(f"Cycle #{cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'=' * 80}")

            # Fetch current prices
            print("\n📊 Fetching prices...")
            prices = {}

            for pair in [config['pair_ab'], config['pair_bc'], config['pair_ac']]:
                price = get_price(client, pair)
                if price is None:
                    print(f"⚠️  Skipping cycle - failed to fetch price for {pair}")
                    time.sleep(config['refresh_time'])
                    continue
                prices[pair] = price

            if len(prices) != 3:
                continue

            # Calculate conversion rates
            rates = calculate_conversion_rates(config, prices)

            # Calculate expected profit
            start_amount = Decimal(str(config['trade_amount_a']))
            fee_rate = Decimal(str(config['fee_rate']))

            # Simulate the cycle
            amount = start_amount
            amount = amount * rates['step1']  # COSA → BTC
            amount = amount * (Decimal("1") - fee_rate)  # Fee

            amount = amount * rates['step2']  # BTC → PIRATE
            amount = amount * (Decimal("1") - fee_rate)  # Fee

            amount = amount * rates['step3']  # PIRATE → COSA
            amount = amount * (Decimal("1") - fee_rate)  # Fee

            profit = amount - start_amount
            profit_ratio = profit / start_amount
            profit_pct = profit_ratio * 100

            print(f"\n💰 Profit Analysis:")
            print(f"  Start: {start_amount} PIRATE")
            print(f"  End: {amount:.8f} PIRATE")
            print(f"  Profit: {profit:.8f} PIRATE ({profit_pct:.4f}%)")
            print(f"  Threshold: {float(config['min_profitability'])*100}%")

            # Check if profitable
            min_profit = Decimal(str(config['min_profitability']))

            if profit_ratio >= min_profit:
                print(f"\n🚀 OPPORTUNITY FOUND! Profit: {profit_pct:.4f}%")

                # Ask for confirmation
                response = input("\nExecute arbitrage? (yes/no): ")
                if response.lower() in ['yes', 'y']:
                    execute_arbitrage(client, config, prices)
                else:
                    print("Skipped by user.")
            else:
                print(f"\n⏸️  No opportunity - profit {profit_pct:.4f}% below threshold")

            # Wait before next cycle
            print(f"\n⏰ Waiting {config['refresh_time']} seconds...")
            time.sleep(config['refresh_time'])

    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
        print(f"Total cycles run: {cycle_count}")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_cosa_arb.py <config_file>")
        print("Example: python run_cosa_arb.py pirate_arb_config.yml")
        sys.exit(1)

    config_file = sys.argv[1]

    if not os.path.exists(config_file):
        print(f"Error: Config file '{config_file}' not found!")
        sys.exit(1)

    run_arbitrage_bot(config_file)
