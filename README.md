# NonKYC Bot

A standalone scaffold for a NonKYC trading bot. This repository is independent of Hummingbot and provides a minimal project structure for client integrations, trading engine components, strategies, and a CLI entry point.

## Structure

- `src/nonkyc_client`: REST/WebSocket client scaffolding and auth helpers.
- `src/engine`: Order management, balances, state handling, and risk controls.
- `src/strategies`: Strategy placeholders.
- `src/cli`: Command-line entry point.
- `tests`: Placeholder unit tests.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
