# Free Crypto Trading Bot

A real, working crypto trading bot built only from free and open-source parts.
Runs 24/7 with plain Python — **no Claude Code, no paid APIs, no subscriptions**
needed at any point. (Claude Code is just a coding assistant; the finished bot
is ordinary Python and runs with `python3 bot.py`.)

## First, the honest part (read this before adding money)

That X post about a 19-year-old turning $68 into $750,000 with a bot that
"spots price errors before humans notice" is **engagement bait**. Red flags:

- "Comment 'Claude' and I'll DM you the setup" — the product is your
  engagement, not a trading system. There is no verifiable proof of any trade.
- $68 → $750,000 in days implies turning every trade into ~11,000x. No
  strategy does this. If it existed, its author would trade it, not farm
  comments.
- Real "price error / arbitrage" edges are fought over in **milliseconds** by
  firms with servers sitting next to the exchange. A free bot polling prices
  every 20 seconds cannot compete there — anyone telling you otherwise is
  selling something.

What this bot **actually** is: two legitimate, well-understood strategies
(grid trading and EMA/RSI momentum) with risk guardrails, running on free
public price data. They can make money in the right markets and **will lose
money** in the wrong ones. There is no strategy, free or paid, that guarantees
profit. Treat every rupee you put in as money you are prepared to lose.

## What's inside

| File | What it does |
|---|---|
| `bot.py` | Main 24/7 loop: prices → risk check → strategy → repeat |
| `pricefeed.py` | Free prices, no key: Kraken → Coinbase → CoinGecko fallback |
| `broker.py` | `PaperBroker` (fake money, default) / `CcxtBroker` (Binance testnet or live) |
| `risk.py` | Daily-loss kill switch + position cap |
| `strategies/grid.py` | Buys dips on a grid, sells each fill one level higher |
| `strategies/momentum.py` | EMA-cross + RSI trend entries with stop-loss / take-profit |
| `strategies/scanner.py` | Hourly market note (info only, never trades) |
| `backtest.py` | Tests momentum on real historical data — free |
| `config.yaml` | All settings |

## Quickstart (2 minutes, zero risk)

```bash
cd ~/workspace/trading-bot
./run.sh            # paper mode: $1,000 fake money, real live prices
```

Watch it work:

```bash
tail -f logs/bot.log      # what it's doing
cat logs/trades.csv       # every simulated trade
```

Stop it: `touch KILL` in this folder (it exits gracefully), or Ctrl+C.

## Test a strategy on history first

```bash
./venv/bin/python backtest.py BTC/USD 60    # momentum, 1h candles, ~30 days
./venv/bin/python backtest.py ETH/USD 240   # 4h candles, ~120 days
```

If the backtest loses money, **do not trade that strategy live**. Compare
against the "buy & hold" line it prints.

## Going further (in this order — don't skip steps)

1. **Paper trade for 2–4 weeks.** Free, real prices, fake money.
2. **Binance testnet** (`mode: testnet` in config): real exchange mechanics,
   still fake money. Get free testnet funds at testnet.binance.vision.
3. **Live, tiny.** `mode: live` + set `BINANCE_API_KEY` / `BINANCE_API_SECRET`
   as environment variables (never in files). Start with an amount whose total
   loss wouldn't hurt you. Keep `max_daily_loss_pct` small.

## Web dashboard (phone-friendly)

A live dashboard shows equity, prices, positions, trades and the bot log —
built as a plain static site in `dashboard/` (no server needed):

- The bot writes `dashboard/data/state.json` every ~20s (`dashboard_state.py`).
- `dashboard/app.js` fetches that file from GitHub raw and refreshes every 30s.
- Hosted on Vercel (free): static files + a tiny `api/control.js` function.
- **Controls on the page:** ↻ Refresh (fetch now), ▶ Start and ⏸ Stop —
  they write `dashboard/data/command.json` via the API, which the bot polls
  about every minute. Stop pauses trading (no orders); the bot keeps
  publishing state. Needs `GITHUB_TOKEN` (repo Contents: read+write) and
  `DASHBOARD_KEY` env vars on Vercel.

## Keep it running 24/7

On any Linux machine / cheap VPS:

```bash
mkdir -p ~/.config/systemd/user
cp trading-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now trading-bot.service
```

Note: this workspace VM can restart, so for true 24/7 run it on a machine
that stays on (your PC, a Raspberry Pi, or a ~$5/month VPS).

## Costs

Everything here is free: Python, `ccxt`, `pyyaml`, `requests`, Kraken/Coinbase/
CoinGecko public data, Binance testnet. The only money involved is what **you**
choose to deposit for live trading — plus tiny exchange fees (~0.1%/trade,
already simulated in paper mode).

## Risk rules baked in

- Paper mode is the default; live requires deliberate config + key setup.
- Daily loss limit halts trading for the day (default 3%).
- Position cap, fixed per-trade size, stop-losses on momentum.
- No leverage, no futures — spot only, so you can't get liquidated.

*This is software, not financial advice. Backtest, paper trade, start tiny.*
