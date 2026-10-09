/* Vercel serverless function: remote Start/Stop for the trading bot.
   Writes dashboard/data/command.json in the GitHub repo; the bot polls it.
   Auth: request must carry the x-control-key header matching DASHBOARD_KEY.
   GitHub writes use GITHUB_TOKEN (repo Contents: read+write). */
const OWNER = "twitslayy";
const REPO = "trading-bot";
const CMD_PATH = "dashboard/data/command.json";
const GH = "https://api.github.com";

function ghHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "User-Agent": "trading-bot-dashboard",
    "Content-Type": "application/json",
  };
}

async function readCommand(token) {
  const r = await fetch(`${GH}/repos/${OWNER}/${REPO}/contents/${CMD_PATH}`, {
    headers: ghHeaders(token),
  });
  if (r.status === 404) return { file: null };
  if (!r.ok) throw new Error("github read failed: " + r.status);
  const j = await r.json();
  return {
    file: j,
    command: JSON.parse(Buffer.from(j.content, "base64").toString()),
  };
}

export default async function handler(req, res) {
  if (req.headers["x-control-key"] !== process.env.DASHBOARD_KEY) {
    return res.status(401).json({ error: "unauthorized" });
  }
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    return res.status(503).json({ error: "control not configured yet" });
  }
  try {
    if (req.method === "GET") {
      const { command } = await readCommand(token);
      return res.status(200).json(command || { action: "start" });
    }
    if (req.method === "POST") {
      const action = (req.body && req.body.action) || "";
      if (!["start", "stop"].includes(action)) {
        return res.status(400).json({ error: "action must be start or stop" });
      }
      const { file } = await readCommand(token);
      const content = Buffer.from(
        JSON.stringify({ action, at: new Date().toISOString(), by: "dashboard" })
      ).toString("base64");
      const body = { message: `dashboard command: ${action}`, content };
      if (file) body.sha = file.sha;
      const put = await fetch(
        `${GH}/repos/${OWNER}/${REPO}/contents/${CMD_PATH}`,
        { method: "PUT", headers: ghHeaders(token), body: JSON.stringify(body) }
      );
      if (!put.ok) throw new Error("github write failed: " + put.status);
      return res.status(200).json({ ok: true, action });
    }
    return res.status(405).json({ error: "method not allowed" });
  } catch (e) {
    return res.status(502).json({ error: String(e.message || e) });
  }
}
