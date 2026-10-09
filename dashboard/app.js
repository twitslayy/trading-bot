/* Trading Bot Dashboard — static, fetches live state from GitHub.
   After the repo is created, set OWNER/REPO below (or leave the
   twitslayy/trading-bot placeholders — the deploy step fills them in). */
const OWNER = "twitslayy";
const REPO = "trading-bot";
const BRANCH = "main";
const DATA_URL = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/dashboard/data/state.json`;
/* Filled in at deploy time — authorises the Start/Stop buttons. */
const CONTROL_KEY = "__CONTROL_KEY__";

const $ = (id) => document.getElementById(id);

function ctrlMsg(t, ok = true) {
  const el = $("ctrl-msg");
  el.textContent = t;
  el.style.color = ok ? "var(--dim)" : "var(--red)";
  if (t) setTimeout(() => { el.textContent = ""; }, 4000);
}

async function sendCommand(action) {
  const btn = action === "start" ? $("btn-start") : $("btn-stop");
  btn.disabled = true;
  ctrlMsg(`${action === "start" ? "Starting" : "Stopping"}…`);
  try {
    const r = await fetch("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-control-key": CONTROL_KEY },
      body: JSON.stringify({ action }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || ("http " + r.status));
    ctrlMsg(action === "start"
      ? "Start sent — bot resumes within ~1 min."
      : "Stop sent — bot pauses within ~1 min.");
    setTimeout(refresh, 1500);
  } catch (e) {
    ctrlMsg("Failed: " + e.message, false);
  } finally {
    btn.disabled = false;
  }
}

function bindControls() {
  $("btn-refresh").addEventListener("click", async () => {
    const b = $("btn-refresh");
    b.disabled = true;
    b.textContent = "↻ Updating…";
    await refresh();
    b.textContent = "↻ Refresh";
    b.disabled = false;
  });
  $("btn-start").addEventListener("click", () => sendCommand("start"));
  $("btn-stop").addEventListener("click", () => sendCommand("stop"));
}

function ago(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${Math.floor(s)}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

async function refresh() {
  try {
    const r = await fetch(DATA_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) throw new Error("http " + r.status);
    const d = await r.json();
    render(d);
  } catch (e) {
    $("status-pill").className = "pill unknown";
    $("status-pill").textContent = "OFFLINE";
  }
}

function render(d) {
  const pill = $("status-pill");
  const live = (d.status || "LIVE") === "LIVE";
  pill.className = "pill " + (live ? "live" : "unknown");
  pill.textContent = live
    ? `● LIVE · ${d.mode.toUpperCase()} · ${d.strategy.toUpperCase()}`
    : `⏸ PAUSED · ${d.mode.toUpperCase()} · ${d.strategy.toUpperCase()}`;

  $("equity").textContent = "$" + d.equity_usd.toLocaleString("en-US",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pnl = $("pnl");
  pnl.textContent = `${d.day_pnl_pct >= 0 ? "+" : ""}${d.day_pnl_pct.toFixed(2)}% today`;
  pnl.className = "sub " + (d.day_pnl_pct >= 0 ? "up" : "down");
  $("updated").textContent = "updated " + ago(d.updated_at);

  $("prices").innerHTML = Object.entries(d.prices).map(([s, p]) =>
    `<div class="px"><b>${s}</b><span>$${Number(p).toLocaleString("en-US",
      { maximumFractionDigits: 2 })}</span></div>`).join("");

  $("positions").innerHTML = d.positions.length
    ? d.positions.map(p =>
      `<div class="pos"><span>${p.label}</span><span>${p.detail}</span></div>`).join("")
    : `<div class="empty">No open positions — waiting for a setup.</div>`;

  $("trades").innerHTML = d.recent_trades.length
    ? d.recent_trades.slice().reverse().map(t => {
        const dt = new Date(t.time_utc);
        const hh = String(dt.getHours()).padStart(2, "0"),
              mm = String(dt.getMinutes()).padStart(2, "0");
        return `<tr><td>${hh}:${mm}</td>` +
          `<td class="${t.side.toLowerCase()}">${t.side}</td>` +
          `<td>${t.symbol}</td><td>$${Number(t.price).toLocaleString("en-US",
            { maximumFractionDigits: 2 })}</td><td>$${t.usd_value}</td></tr>`;
      }).join("")
    : `<tr><td colspan="5" class="empty">No trades yet.</td></tr>`;

  $("log").textContent = (d.log_tail || []).join("\n") || "—";
}

refresh();
bindControls();
setInterval(refresh, 30000);
