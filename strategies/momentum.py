"""Trend-following momentum strategy (spot, long-only).

Entry: EMA(fast) crosses above EMA(slow) while RSI < rsi_max.
Exit: stop-loss, take-profit, or EMA cross back down.
"""
import time
from .common import ema, rsi


class MomentumStrategy:
    def __init__(self, broker, feed, cfg):
        m = cfg["momentum"]
        self.broker = broker
        self.feed = feed
        self.symbols = list(m["symbols"])
        self.tf = int(m.get("timeframe_minutes", 60))
        self.ef_p = int(m["ema_fast"])
        self.es_p = int(m["ema_slow"])
        self.rsi_p = int(m["rsi_period"])
        self.rsi_max = float(m["rsi_max"])
        self.sl = float(m["stop_loss_pct"]) / 100.0
        self.tp = float(m["take_profit_pct"]) / 100.0
        self.order_usd = float(m["order_usd"])
        self.max_pos = int(cfg["risk"]["max_open_positions"])
        self.signal_every = int(m.get("signal_minutes", 15)) * 60
        self.positions = {}   # symbol -> {qty, entry, sl, tp}
        self.last_signal = 0.0

    def _signal(self, symbol):
        candles = self.feed.get_ohlc(symbol, interval_minutes=self.tf)
        closes = [c["c"] for c in candles]
        ef = ema(closes, self.ef_p)
        es = ema(closes, self.es_p)
        rr = rsi(closes, self.rsi_p)
        cross_up = ef[-2] <= es[-2] and ef[-1] > es[-1]
        cross_dn = ef[-2] >= es[-2] and ef[-1] < es[-1]
        return cross_up, cross_dn, rr[-1]

    def on_tick(self, prices, log):
        # 1) manage open positions
        for sym, pos in list(self.positions.items()):
            px = prices.get(sym)
            if px is None:
                continue
            reason = None
            if px <= pos["sl"]:
                reason = "STOP-LOSS"
            elif px >= pos["tp"]:
                reason = "TAKE-PROFIT"
            if reason:
                try:
                    self.broker.market_sell(sym, pos["qty"])
                    pnl = (px - pos["entry"]) / pos["entry"] * 100
                    log(f"[momentum] {reason} {sym} @ {px:.2f} ({pnl:+.2f}%)")
                except Exception as e:
                    log(f"[momentum] exit failed for {sym}: {e}")
                finally:
                    del self.positions[sym]

        # 2) entry/exit signals on a slower cadence
        if time.time() - self.last_signal < self.signal_every:
            return
        self.last_signal = time.time()
        for sym in self.symbols:
            px = prices.get(sym)
            if px is None:
                continue
            try:
                cross_up, cross_dn, r = self._signal(sym)
            except Exception as e:
                log(f"[momentum] signal fetch failed for {sym}: {e}")
                continue
            if sym in self.positions:
                if cross_dn:
                    try:
                        self.broker.market_sell(sym, self.positions[sym]["qty"])
                        log(f"[momentum] TREND-EXIT {sym} @ {px:.2f}")
                    except Exception as e:
                        log(f"[momentum] exit failed for {sym}: {e}")
                    finally:
                        del self.positions[sym]
            elif cross_up and r < self.rsi_max:
                if len(self.positions) >= self.max_pos:
                    log("[momentum] position cap reached")
                    break
                if self.broker.balance("USD") < self.order_usd:
                    log("[momentum] insufficient USD")
                    continue
                try:
                    qty = self.broker.market_buy(sym, self.order_usd)
                except Exception as e:
                    log(f"[momentum] entry failed for {sym}: {e}")
                    continue
                self.positions[sym] = {"qty": qty, "entry": px,
                                       "sl": px * (1 - self.sl), "tp": px * (1 + self.tp)}
                log(f"[momentum] BUY {sym} @ {px:.2f} (RSI {r:.1f})")
