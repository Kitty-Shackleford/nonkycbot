#!/usr/bin/env python3
"""Store API credentials for multiple exchanges in the OS keychain."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

def build_parser() -> argparse.ArgumentParser:
    from utils.credentials import (
        DEFAULT_API_KEY_ENV,
        DEFAULT_API_SECRET_ENV,
    )

    parser = argparse.ArgumentParser(
        description="Store API credentials for multiple exchanges in the OS keychain."
    )
    parser.add_argument(
        "--exchange",
        required=True,
        choices=["nonkyc", "cexswap"],
        help="The exchange to store credentials for (nonkyc or cexswap).",
    )
    parser.add_argument(
        "--api-key",
        help=f"API key (defaults to ${DEFAULT_API_KEY_ENV} or prompt).",
    )
    parser.add_argument(
        "--api-secret",
        help=f"API secret (defaults to ${DEFAULT_API_SECRET_ENV} or prompt, if applicable).",
    )
    return parser

def store_nonkyc_credentials(service_name: str, api_key: str, api_secret: str):
    from utils.credentials import store_api_credentials
    # Store NonKYC credentials, both API key and API secret
    store_api_credentials(service_name, api_key, api_secret)

def store_cexswap_credentials(service_name: str, api_key: str, api_secret: str):
    from utils.credentials import store_api_credentials
    # Store CexSwap credentials (both API key and API secret)
    store_api_credentials(service_name, api_key, api_secret)

def main() -> int:
    from utils.credentials import (
        DEFAULT_API_KEY_ENV,
        DEFAULT_API_SECRET_ENV,
    )

    parser = build_parser()
    args = parser.parse_args()
    
    api_key = args.api_key or os.getenv(DEFAULT_API_KEY_ENV)
    api_secret = args.api_secret or os.getenv(DEFAULT_API_SECRET_ENV)

    if args.exchange == "nonkyc":
        # For NonKYC, store under 'nonkyc-bot'
        service_name = "nonkyc-bot"
        # Ask for both API key and secret if not provided
        if not api_key:
            api_key = getpass.getpass("Enter NonKYC API key: ")
        if not api_secret:
            api_secret = getpass.getpass("Enter NonKYC API secret: ")
        store_nonkyc_credentials(service_name, api_key, api_secret)
        print(f"✅ Stored credentials in keychain for NonKYC service '{service_name}'.")

    elif args.exchange == "cexswap":
        # For CexSwap, store under 'cexswap-bot'
        service_name = "cexswap-bot"
        # Ask for both API key and secret if not provided
        if not api_key:
            api_key = getpass.getpass("Enter CexSwap API key: ")
        if not api_secret:
            api_secret = getpass.getpass("Enter CexSwap API secret: ")
        store_cexswap_credentials(service_name, api_key, api_secret)
        print(f"✅ Stored credentials in keychain for CexSwap service '{service_name}'.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())

