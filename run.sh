#!/usr/bin/env bash
# Start the bot (paper mode by default). No AI / no Claude Code needed at runtime.
cd "$(dirname "$0")"
./venv/bin/python bot.py --config "${1:-config.yaml}"
