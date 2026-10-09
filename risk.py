"""Risk guardrails: daily loss kill-switch and position caps."""
from datetime import date


class RiskManager:
    def __init__(self, cfg, equity_fn):
        self.max_daily_loss_pct = float(cfg["risk"]["max_daily_loss_pct"])
        self.max_open_positions = int(cfg["risk"]["max_open_positions"])
        self._equity = equity_fn
        self.day = None
        self.day_start_equity = None

    def check(self):
        """Returns (ok: bool, reason: str). Halts trading for the day on breach."""
        today = date.today()
        eq = self._equity()
        if self.day != today or not self.day_start_equity:
            self.day = today
            self.day_start_equity = eq
            return True, "new day, baseline set"
        dd = (self.day_start_equity - eq) / self.day_start_equity * 100.0
        if dd >= self.max_daily_loss_pct:
            return False, (f"daily loss limit hit: -{dd:.2f}% "
                           f"(limit {self.max_daily_loss_pct}%)")
        return True, "ok"

    def can_open(self, open_count):
        return open_count < self.max_open_positions
