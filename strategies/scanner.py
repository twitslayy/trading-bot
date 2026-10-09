"""Divergence scanner — INFORMATIONAL ONLY, never trades.

Logs the strongest/weakest tracked pairs vs BTC once an hour so you can
see what the market is doing. It does not open positions by itself.
"""
import time
import requests


class DivergenceScanner:
    def __init__(self, feed):
        self.feed = feed
        self.last = 0.0

    def maybe_scan(self, log):
        if time.time() - self.last < 3600:
            return
        self.last = time.time()
        try:
            r = requests.get("https://api.kraken.com/0/public/Ticker",
                             params={"pair": "XXBTZUSD,XETHZUSD,SOLUSD"},
                             timeout=10)
            r.raise_for_status()
            data = r.json()["result"]
            changes = {}
            for name, pair in (("BTC/USD", "XXBTZUSD"), ("ETH/USD", "XETHZUSD"),
                               ("SOL/USD", "SOLUSD")):
                t = data[pair]
                last, open_ = float(t["c"][0]), float(t["o"])
                changes[name] = (last - open_) / open_ * 100.0
            btc = changes.pop("BTC/USD")
            ranked = sorted(changes.items(), key=lambda kv: kv[1] - btc, reverse=True)
            line = ", ".join(f"{s} {c:+.2f}% (vs BTC {c - btc:+.2f}pp)" for s, c in ranked)
            log(f"[scanner] 24h vs BTC: {line}")
        except Exception as e:
            log(f"[scanner] failed: {e}")
