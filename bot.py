#!/usr/bin/env python3
"""Free crypto trading bot — runs 24/7 with plain Python, no AI needed at runtime.

Usage:
    ./venv/bin/python bot.py --config config.yaml

Create an empty file named KILL in this directory to stop the bot gracefully.
"""
import argparse
import logging
import os
import signal
import sys
import time

import requests
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pricefeed import PriceFeed
from broker import PaperBroker
from risk import RiskManager
from dashboard_state import build_state

COMMAND_URL = ("https://raw.githubusercontent.com/twitslayy/trading-bot"
               "/main/dashboard/data/command.json")


def fetch_command():
    """Read start/stop command set from the web dashboard (via Vercel API)."""
    try:
        r = requests.get(COMMAND_URL, timeout=10)
        if r.status_code == 200:
            return r.json().get("action")
    except Exception:
        pass
    return None
from strategies.grid import GridStrategy
from strategies.momentum import MomentumStrategy
from strategies.scanner import DivergenceScanner

stop = False


def _handle_sig(signum, frame):
    global stop
    stop = True


signal.signal(signal.SIGTERM, _handle_sig)
signal.signal(signal.SIGINT, _handle_sig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler("logs/bot.log"),
                                  logging.StreamHandler()])
    log = logging.getLogger("bot").info

    feed = PriceFeed(primary=cfg.get("price_feed", "kraken"))
    mode = cfg.get("mode", "paper")
    if mode == "paper":
        broker = PaperBroker(cfg.get("paper_start_balance_usd", 1000.0),
                             cfg.get("fee_pct", 0.1))
    elif mode in ("testnet", "live"):
        from broker import CcxtBroker
        broker = CcxtBroker(testnet=(mode == "testnet"))
    else:
        raise SystemExit(f"unknown mode: {mode}")

    risk = RiskManager(cfg, broker.equity_usd)

    strat_name = cfg.get("strategy", "grid")
    if strat_name == "grid":
        strat = GridStrategy(broker, cfg)
        symbols = sorted(set(cfg.get("symbols", []) + [cfg["grid"]["symbol"]]))
    elif strat_name == "momentum":
        strat = MomentumStrategy(broker, feed, cfg)
        symbols = sorted(set(cfg.get("symbols", []) + cfg["momentum"]["symbols"]))
    else:
        raise SystemExit(f"unknown strategy: {strat_name}")

    scanner = DivergenceScanner(feed)
    poll = int(cfg.get("poll_seconds", 20))

    log(f"=== bot starting: mode={mode} strategy={strat_name} symbols={symbols} ===")
    log(f"starting equity: ${broker.equity_usd():.2f}")

    # web-dashboard remote control: start paused if the dashboard says stop
    paused = (fetch_command() == "stop")
    if paused:
        log("dashboard command: starting PAUSED")

    loop_n = 0
    while not stop:
        if os.path.exists("KILL"):
            log("KILL file found — stopping gracefully")
            break
        try:
            prices = feed.get_prices(symbols)
            broker.update_prices(prices)

            ok, reason = risk.check()
            if not ok:
                log(f"RISK HALT: {reason} (equity ${broker.equity_usd():.2f})")
                time.sleep(poll)
                continue

            if paused:
                pass  # remote-paused from dashboard: monitor only, no orders
            elif strat_name == "grid":
                strat.on_tick(prices[strat.symbol], log)
            else:
                strat.on_tick(prices, log)
            scanner.maybe_scan(log)

            # publish web-dashboard state every loop (~20s)
            loop_n += 1
            try:
                # remote start/stop from the dashboard (checked ~every minute)
                if loop_n % 3 == 0:
                    cmd = fetch_command()
                    if cmd == "stop" and not paused:
                        paused = True
                        log("dashboard command: PAUSED trading")
                    elif cmd == "start" and paused:
                        paused = False
                        log("dashboard command: RESUMED trading")
                eq = broker.equity_usd()
                base = risk.day_start_equity or eq
                day_pnl = (eq - base) / base * 100.0 if base else 0.0
                build_state(cfg, broker, strat, strat_name, prices, day_pnl,
                            paused=paused)
            except Exception as e:
                log(f"dashboard publish failed: {e}")
        except Exception as e:
            log(f"loop error (will retry): {e}")
        time.sleep(poll)

    log(f"=== bot stopped. final equity: ${broker.equity_usd():.2f} ===")


if __name__ == "__main__":
    main()
