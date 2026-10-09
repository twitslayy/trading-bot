"""Tiny pure-python indicators (no pandas needed)."""


def ema(values, period):
    k = 2.0 / (period + 1)
    out = []
    e = values[0]
    for v in values:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def rsi(closes, period=14):
    n = len(closes)
    if n < period + 2:
        return [50.0] * n
    gains, losses = [], []
    for i in range(1, n):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    out = [50.0] * period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        rs = ag / al if al > 0 else float("inf")
        out.append(100.0 - 100.0 / (1.0 + rs))
    return [50.0] + out  # align to len(closes)
