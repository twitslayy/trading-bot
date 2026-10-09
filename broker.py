"""Brokers: PaperBroker (simulated money, default) and CcxtBroker (Binance testnet/live).

API keys are NEVER stored in files — live mode reads them from the
BINANCE_API_KEY / BINANCE_API_SECRET environment variables only.
"""
import csv
import json
import os
from datetime import datetime, timezone


class PaperBroker:
    def __init__(self, start_usd=1000.0, fee_pct=0.1,
                 state_path="state.json", log_path="logs/trades.csv"):
        self.fee_rate = fee_pct / 100.0
        self.state_path = state_path
        self.log_path = log_path
        self.balances = {"USD": float(start_usd)}
        self.prices = {}
        self._load()

    # ---- state ----
    def _load(self):
        try:
            with open(self.state_path) as f:
                s = json.load(f)
                self.balances = s.get("balances", self.balances)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"balances": self.balances,
                       "saved_at": datetime.now(timezone.utc).isoformat()}, f)
        os.replace(tmp, self.state_path)

    # ---- market data ----
    def update_prices(self, prices):
        self.prices.update(prices)

    def price(self, symbol):
        return self.prices[symbol]

    # ---- balances ----
    @staticmethod
    def base_asset(symbol):
        return symbol.split("/")[0]

    def balance(self, asset):
        return self.balances.get(asset, 0.0)

    def equity_usd(self):
        total = self.balance("USD")
        for sym, px in self.prices.items():
            total += self.balance(self.base_asset(sym)) * px
        return total

    # ---- orders (instant fill at current price, fee deducted) ----
    def market_buy(self, symbol, quote_usd):
        price = self.price(symbol)
        if self.balance("USD") < quote_usd:
            raise RuntimeError(f"insufficient USD for {symbol} buy")
        fee = quote_usd * self.fee_rate
        qty = (quote_usd - fee) / price
        self.balances["USD"] -= quote_usd
        base = self.base_asset(symbol)
        self.balances[base] = self.balance(base) + qty
        self._record("BUY", symbol, qty, price, quote_usd)
        return qty

    def market_sell(self, symbol, base_qty):
        price = self.price(symbol)
        base = self.base_asset(symbol)
        if self.balance(base) < base_qty:
            raise RuntimeError(f"insufficient {base} for sell")
        proceeds = base_qty * price
        fee = proceeds * self.fee_rate
        self.balances[base] -= base_qty
        self.balances["USD"] = self.balance("USD") + proceeds - fee
        self._record("SELL", symbol, base_qty, price, proceeds - fee)
        return proceeds - fee

    def _record(self, side, symbol, qty, price, usd_value):
        self._save()
        new = not os.path.exists(self.log_path)
        with open(self.log_path, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["time_utc", "side", "symbol", "qty", "price", "usd_value"])
            w.writerow([datetime.now(timezone.utc).isoformat(), side, symbol,
                        f"{qty:.8f}", f"{price:.2f}", f"{usd_value:.2f}"])


class CcxtBroker:
    """Binance via ccxt. testnet=True uses the free Binance spot testnet."""

    def __init__(self, testnet=True):
        import ccxt  # lazy: paper mode never needs it
        key = os.environ.get("BINANCE_API_KEY")
        secret = os.environ.get("BINANCE_API_SECRET")
        if not key or not secret:
            raise RuntimeError("live mode needs BINANCE_API_KEY and "
                               "BINANCE_API_SECRET environment variables")
        self.ex = ccxt.binance({"apiKey": key, "secret": secret,
                                "enableRateLimit": True})
        if testnet:
            self.ex.set_sandbox_mode(True)
        self.ex.load_markets()
        # Binance uses USDT quote; map our "BTC/USD" style symbols.
        self._live_symbol = {}

    def _sym(self, symbol):
        if symbol not in self._live_symbol:
            base = symbol.split("/")[0]
            self._live_symbol[symbol] = f"{base}/USDT"
        return self._live_symbol[symbol]

    def update_prices(self, prices):
        pass  # live prices come from the exchange itself

    def price(self, symbol):
        return float(self.ex.fetch_ticker(self._sym(symbol))["last"])

    def balance(self, asset):
        bal = self.ex.fetch_balance()
        return float(bal.get(asset, {}).get("free", 0.0) or 0.0)

    def equity_usd(self):
        total = 0.0
        for asset, amt in (self.ex.fetch_balance().get("total") or {}).items():
            if not amt:
                continue
            if asset in ("USDT", "USD", "BUSD"):
                total += amt
            else:
                try:
                    total += amt * float(self.ex.fetch_ticker(f"{asset}/USDT")["last"])
                except Exception:
                    pass
        return total

    def market_buy(self, symbol, quote_usd):
        order = self.ex.create_market_buy_order_with_cost(self._sym(symbol), quote_usd)
        return float(order.get("filled") or 0.0)

    def market_sell(self, symbol, base_qty):
        order = self.ex.create_market_sell_order(self._sym(symbol), base_qty)
        return float(order.get("cost") or 0.0)
