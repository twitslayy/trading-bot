"""Free public crypto price feeds — no API key required.

Primary: Kraken. Automatic fallback: Coinbase -> CoinGecko.
Also provides free OHLC candles (Kraken) for the backtester.
"""
import requests

KRAKEN_MAP = {"BTC/USD": "XXBTZUSD", "ETH/USD": "XETHZUSD", "SOL/USD": "SOLUSD"}
COINBASE_MAP = {"BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD", "SOL/USD": "SOL-USD"}
COINGECKO_MAP = {"BTC/USD": "bitcoin", "ETH/USD": "ethereum", "SOL/USD": "solana"}


class PriceFeed:
    def __init__(self, primary="kraken", timeout=25):
        self.primary = primary
        self.timeout = timeout
        self._order = [primary] + [f for f in ("kraken", "coinbase", "coingecko") if f != primary]

    def get_prices(self, symbols):
        """Return {symbol: price}. Raises RuntimeError if every feed fails."""
        last_err = None
        for name in self._order:
            try:
                return getattr(self, "_fetch_" + name)(symbols)
            except Exception as e:  # try next feed
                last_err = e
        raise RuntimeError(f"all price feeds failed: {last_err}")

    def _fetch_kraken(self, symbols):
        pairs = ",".join(KRAKEN_MAP[s] for s in symbols)
        r = requests.get("https://api.kraken.com/0/public/Ticker",
                         params={"pair": pairs}, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        return {s: float(data["result"][KRAKEN_MAP[s]]["c"][0]) for s in symbols}

    def _fetch_coinbase(self, symbols):
        out = {}
        for s in symbols:
            r = requests.get(f"https://api.coinbase.com/v2/prices/{COINBASE_MAP[s]}/spot",
                             timeout=self.timeout)
            r.raise_for_status()
            out[s] = float(r.json()["data"]["amount"])
        return out

    def _fetch_coingecko(self, symbols):
        ids = ",".join(COINGECKO_MAP[s] for s in symbols)
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids": ids, "vs_currencies": "usd"}, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return {s: float(data[COINGECKO_MAP[s]]["usd"]) for s in symbols}

    def get_ohlc(self, symbol, interval_minutes=60, limit=720):
        """Free OHLC candles from Kraken, oldest-first.
        Each candle: {t, o, h, l, c, v}."""
        pair = KRAKEN_MAP[symbol]
        r = requests.get("https://api.kraken.com/0/public/OHLC",
                         params={"pair": pair, "interval": interval_minutes},
                         timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise RuntimeError(data["error"])
        key = [k for k in data["result"].keys() if k != "last"][0]
        rows = data["result"][key][-limit:]
        return [{"t": int(x[0]), "o": float(x[1]), "h": float(x[2]),
                 "l": float(x[3]), "c": float(x[4]), "v": float(x[6])} for x in rows]
