# NonKYC Bot

A standalone trading bot framework for NonKYC exchanges. This repository provides a complete, independent project structure including exchange client integrations, trading engine components, strategy implementations, and a command-line interface.

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
