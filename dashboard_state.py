"""Publishes bot state for the web dashboard.

Writes dashboard/data/state.json (atomic) — the static dashboard on Vercel
fetches this file from GitHub raw, so no rebuild is needed for live data.
Contains no secrets: paper balances and public trade history only.
"""
import csv
import json
import os
from datetime import datetime, timezone

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "dashboard", "data", "state.json")


def _tail(path, n):
    try:
        with open(path) as f:
            lines = f.read().strip().split("\n")
        return [l for l in lines if l][-n:]
    except (FileNotFoundError, OSError):
        return []


def _recent_trades(n=20):
    rows = _tail("logs/trades.csv", n + 1)
    out = []
    for r in rows:
        if r.startswith("time_utc"):
            continue
        parts = r.split(",")
        if len(parts) >= 6:
            out.append({"time_utc": parts[0], "side": parts[1], "symbol": parts[2],
                        "qty": parts[3], "price": parts[4], "usd_value": parts[5]})
    return out[-n:]


def build_state(cfg, broker, strategy, strat_name, prices, day_pnl_pct=0.0):
    positions = []
    if strat_name == "grid":
        for ps in getattr(strategy, "pending_sells", []):
            positions.append({
                "label": f"Grid sell {strategy.symbol}",
                "detail": f"{ps['qty']:.6f} → target ${ps['target']:,.2f}",
            })
        if getattr(strategy, "filled", None):
            positions.append({
                "label": "Grid levels filled",
                "detail": f"{len(strategy.filled)}/{strategy.levels}",
            })
    elif strat_name == "momentum":
        for sym, pos in strategy.positions.items():
            positions.append({
                "label": f"Long {sym}",
                "detail": f"{pos['qty']:.6f} @ ${pos['entry']:,.2f}",
            })

    state = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": cfg.get("mode", "paper"),
        "strategy": strat_name,
        "symbols": sorted(prices.keys()),
        "prices": {s: round(p, 2) for s, p in prices.items()},
        "equity_usd": round(broker.equity_usd(), 2),
        "day_pnl_pct": round(day_pnl_pct, 3),
        "balances": {k: round(v, 8) for k, v in broker.balances.items()} if hasattr(broker, "balances") else {},
        "positions": positions,
        "recent_trades": _recent_trades(20),
        "log_tail": _tail("logs/bot.log", 12),
    }
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    tmp = DATA_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, DATA_PATH)
    return state
