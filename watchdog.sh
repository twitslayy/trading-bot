#!/usr/bin/env bash
# Watchdog: restart the paper trading bot if it died (unless KILL file = user stopped it).
cd "$HOME/workspace/trading-bot" || exit 1
[ -f KILL ] && exit 0
if pgrep -f "bot.py --config config.yaml" > /dev/null 2>&1; then
  exit 0
fi
setsid nohup ./venv/bin/python bot.py --config config.yaml >> /tmp/bot-live.log 2>&1 < /dev/null &
echo "restarted (appended to /tmp/bot-live.log)"
