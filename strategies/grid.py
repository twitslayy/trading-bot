"""Spot grid strategy.

Anchors a grid around the current price: N buy levels below, each filled
level paired with a sell one spacing above. Profits from ranging markets;
loses in strong trends (honest limitation — see README).
"""


class GridStrategy:
    def __init__(self, broker, cfg):
        g = cfg["grid"]
        self.broker = broker
        self.symbol = g["symbol"]
        self.levels = int(g["levels"])
        self.spacing = float(g["spacing_pct"]) / 100.0
        self.order_usd = float(g["order_usd"])
        self.anchor = None
        self.buy_lines = []
        self.filled = set()          # indices of buy lines already filled
        self.pending_sells = []      # [{qty, target}]

    def _setup(self, price, log):
        self.anchor = price
        self.buy_lines = [price * (1 - (i + 1) * self.spacing) for i in range(self.levels)]
        self.filled = set()
        self.pending_sells = []
        log(f"[grid] anchored at {price:.2f}, {self.levels} levels, "
            f"spacing {self.spacing * 100:.2f}%")

    def on_tick(self, price, log):
        if self.anchor is None:
            self._setup(price, log)
            return
        # Re-anchor if price escaped far beyond the grid.
        lo = self.buy_lines[-1]
        hi = self.anchor * (1 + self.levels * self.spacing)
        if price < lo * 0.98 or price > hi * 1.02:
            log(f"[grid] price {price:.2f} escaped grid, re-anchoring")
            self._setup(price, log)
            return

        # Fill buy levels crossed downward.
        for i, line in enumerate(self.buy_lines):
            if i in self.filled or price > line:
                continue
            if self.broker.balance("USD") < self.order_usd:
                log("[grid] insufficient USD, skipping buy level")
                break
            try:
                qty = self.broker.market_buy(self.symbol, self.order_usd)
            except Exception as e:
                log(f"[grid] buy failed: {e}")
                break
            self.filled.add(i)
            target = line * (1 + self.spacing)
            self.pending_sells.append({"qty": qty, "target": target})
            log(f"[grid] BUY level {i + 1} @ {price:.2f}, sell target {target:.2f}")

        # Sell filled levels whose target is reached.
        base = self.broker.base_asset(self.symbol)
        for ps in list(self.pending_sells):
            if price >= ps["target"]:
                qty = min(ps["qty"], self.broker.balance(base))
                if qty <= 0:
                    self.pending_sells.remove(ps)
                    continue
                try:
                    self.broker.market_sell(self.symbol, qty)
                except Exception as e:
                    log(f"[grid] sell failed: {e}")
                    continue
                self.pending_sells.remove(ps)
                log(f"[grid] SELL @ {price:.2f} (target {ps['target']:.2f})")
