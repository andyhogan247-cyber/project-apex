"""APEX gold desk: the veto-only Grok committee on Telegram gold signals (paper).

Same design as the stock desk and Triple Seven:
  * The SIGNAL comes from the Telegram channel (saved to the `signals` table by
    collector/telegram_listener.py, or by anything else that writes there).
  * News (web + X search: data releases, Fed, DXY/yields) -> Skeptic -> Desk Lead
    can only VETO it. Code accepts a signal only if News != RED_FLAG, Skeptic != SKIP
    and Lead = APPROVE. Any failure = VETO (fail closed).
  * Every signal is graded on the MT4 M1 prices the collector records - VETOED ones
    too - so the dashboard shows whether the committee saves money or costs it.

Grading (paper, conservative, after the committee decided):
  fill    BUY at the TOP of the entry zone (SELL at the bottom) once price trades there,
          within FILL_HOURS - otherwise NO_FILL
  exit    first of stop / TP1 on the M1 bars (stop first if both in one bar); TP2 noted
          if it came before the stop; TIME after MAX_HOURS at the last price
  R       (exit - entry) / (entry - stop), minus the spread at entry

Run:  python -m desk.gold_desk          (loop: every 60 s review new signals, grade, dashboard)
      python -m desk.gold_desk --once
Dashboard: reports/gold_committee.html
"""

import argparse
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from desk import veto

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "apex.db"
PROMPTS = Path(__file__).with_name("gold_prompts.json")
LOG = ROOT / "logs" / "gold_committee_chat.log"
HTML = ROOT / "reports" / "gold_committee.html"
MARKET = "GOLD"
MAX_SIGNAL_AGE_MIN = 30   # older signals are stale: not reviewed, not traded
FILL_HOURS = 4
MAX_HOURS = 24


def _load_env():
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def _iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _epoch(text):
    return datetime.fromisoformat(text[:19]).replace(tzinfo=timezone.utc).timestamp()


def connect(db=None):
    con = sqlite3.connect(db or DB)
    con.row_factory = sqlite3.Row
    return con


def committee(db=None, post=None):
    _load_env()
    return veto.Committee(db or DB, MARKET, PROMPTS, LOG, model=os.getenv("GROK_MODEL", "grok-4.3"),
                          skeptic_model=os.getenv("SKEPTIC_MODEL"), search_roles=("news",),
                          timeout=150, post=post, enabled=os.getenv("COMMITTEE", "true").lower() != "false")


def market_context(con, now):
    """Latest price and recent change from the MT4 observations; channel BUY share."""
    def mid_at(ts):
        r = con.execute("SELECT mid FROM market_observations WHERE symbol='XAUUSD' AND timestamp<=? "
                        "ORDER BY timestamp DESC LIMIT 1", (_iso(ts),)).fetchone()
        return r["mid"] if r else None
    last = con.execute("SELECT * FROM market_observations WHERE symbol='XAUUSD' AND timestamp<=? "
                       "ORDER BY timestamp DESC LIMIT 1", (_iso(now),)).fetchone()
    ctx = {}
    if last:
        ctx = {"price_now": round(last["mid"], 2), "spread": round(last["spread"], 2),
               "price_time_utc": last["timestamp"]}
        for label, sec in (("chg_1h", 3600), ("chg_4h", 4 * 3600), ("chg_24h", 86400)):
            m = mid_at(now - sec)
            if m:
                ctx[label] = round(last["mid"] - m, 2)
    recent = [r["direction"] for r in con.execute("SELECT direction FROM signals ORDER BY timestamp DESC LIMIT 30")]
    if recent:
        ctx["channel_last30_buy_share"] = f"{recent.count('BUY') / len(recent):.0%}"
    return ctx


def review_pending(db=None, post=None, now=None):
    """Committee on every fresh signal with no decision yet. -> {signal_id: APPROVE/VETO}"""
    now = now or time.time()
    with connect(db) as con:
        con.executescript(veto.SCHEMA)
        done = {r["ref"] for r in con.execute("SELECT ref FROM veto_decisions WHERE market=?", (MARKET,))}
        fresh = [dict(r) for r in con.execute("SELECT * FROM signals WHERE timestamp>=? ORDER BY timestamp",
                                              (_iso(now - MAX_SIGNAL_AGE_MIN * 60),))
                 if r["signal_id"] not in done]
        if not fresh:
            return {}
        ctx = market_context(con, now)
    items = []
    for s in fresh:
        top, bottom = max(s["entry_high"], s["entry_low"]), min(s["entry_high"], s["entry_low"])
        entry = top if s["direction"] == "BUY" else bottom
        risk = abs(entry - s["stop_loss"])
        items.append({"ref": s["signal_id"], "symbol": s["symbol"], "direction": s["direction"],
                      "entry": f"{bottom}-{top}", "stop": s["stop_loss"], "target": s["tp1"],
                      "facts": {**ctx, "tp2": s["tp2"], "tp3": s["tp3"], "risk_points": round(risk, 2),
                                "tp1_reward_R": round(abs(s["tp1"] - entry) / risk, 2) if risk else None,
                                "signal_time_utc": s["timestamp"], "source": s["source"]}})
    context = ("Gold (XAUUSD) CFD, prices in USD per ounce. 'entry' is the signal's zone; the desk fills BUYs at "
               "the top of the zone and SELLs at the bottom.")
    return committee(db, post).review(items, context, ts=now)


def simulate(signal, bars, spread=0.0, slip=0.0):
    """-> (outcome, R). bars = M1 rows (timestamp, m1_high, m1_low, mid) AFTER the decision.

    Trade management as the channel runs it: half the position closes at TP1, the stop on
    the other half moves to break-even, and that half runs to TP2 (or break-even / time limit).
      STOP  stopped before TP1                       ~ -1R
      TP1   half at TP1, other half out at break-even
      TP2   half at TP1, half at TP2
      TIME  time limit (open part marked at the last price)
    `spread` (points) is paid once on entry; `slip` (points) worsens the entry and every stop fill.
    Same-bar ambiguity is resolved against us (stop first; TP2 only from the bar after TP1)."""
    d = 1 if signal["direction"] == "BUY" else -1
    top, bottom = max(signal["entry_high"], signal["entry_low"]), min(signal["entry_high"], signal["entry_low"])
    edge, stop, tp1, tp2 = (top if d > 0 else bottom), signal["stop_loss"], signal["tp1"], signal["tp2"]
    entry = edge + d * slip
    risk = d * (entry - stop)
    if not bars or risk <= 0 or d * (tp1 - entry) <= 0:
        return "OPEN", None
    if d * (tp2 - tp1) <= 0:          # missing / mistyped TP2: everything closes at TP1
        tp2 = None
    cost = spread / risk
    r_at = lambda px: d * (px - entry) / risk
    t0 = _epoch(bars[0]["timestamp"])
    filled_at = half = None
    for b in bars:
        t = _epoch(b["timestamp"])
        hi, lo = b["m1_high"], b["m1_low"]
        if filled_at is None:
            if t - t0 > FILL_HOURS * 3600:
                return "NO_FILL", None
            if (d > 0 and lo <= top) or (d < 0 and hi >= bottom):
                filled_at = t
            else:
                continue
        if half is None:                                   # full position
            if (lo <= stop) if d > 0 else (hi >= stop):
                return "STOP", round(r_at(stop - d * slip) - cost, 3)
            if (hi >= tp1) if d > 0 else (lo <= tp1):
                half = 0.5 * r_at(tp1)
                if tp2 is None:
                    return "TP1", round(2 * half - cost, 3)
                continue                                   # second half from the next bar
            if t - filled_at > MAX_HOURS * 3600:
                return "TIME", round(r_at(b["mid"]) - cost, 3)
        else:                                              # half left, stop at break-even
            if (lo <= entry) if d > 0 else (hi >= entry):
                return "TP1", round(half + 0.5 * r_at(entry - d * slip) - cost, 3)
            if (hi >= tp2) if d > 0 else (lo <= tp2):
                return "TP2", round(half + 0.5 * r_at(tp2) - cost, 3)
            if t - filled_at > MAX_HOURS * 3600:
                return "TIME", round(half + 0.5 * r_at(b["mid"]) - cost, 3)
    return "OPEN", None


def grade(db=None):
    n = 0
    with connect(db) as con:
        for d in veto.ungraded(db or DB, MARKET):
            s = con.execute("SELECT * FROM signals WHERE signal_id=?", (d["ref"],)).fetchone()
            if not s:
                continue
            bars = [dict(r) for r in con.execute(
                "SELECT timestamp, m1_high, m1_low, mid, spread FROM market_observations WHERE symbol='XAUUSD' "
                "AND timestamp>=? ORDER BY timestamp", (_iso(d["ts"]),))]
            outcome, r = simulate(dict(s), bars, bars[0]["spread"] if bars else 0.0)
            if outcome != "OPEN" or bars:
                veto.set_outcome(db or DB, MARKET, d["ref"], outcome, r)
                n += outcome != "OPEN"
    return n


def write_dashboard(db=None, out=None):
    out = out or HTML
    try:
        with connect(db) as con:
            sig = [dict(r) for r in con.execute("SELECT * FROM signals ORDER BY timestamp DESC LIMIT 20")]
            last = con.execute("SELECT * FROM market_observations ORDER BY timestamp DESC LIMIT 1").fetchone()
        e = veto._e
        rows = [[e(s["timestamp"]), e(s["direction"]), f"{s['entry_low']}-{s['entry_high']}", s["stop_loss"],
                 f"{s['tp1']} / {s['tp2']} / {s['tp3']}", e(s["source"])] for s in sig]
        feed = (f"<p>MT4 price feed: last {e(last['timestamp'])} UTC, mid {last['mid']:.2f}, spread {last['spread']}</p>"
                if last else "<p class='no'>No MT4 prices recorded - start the collector or nothing can be graded.</p>")
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(veto.dashboard_html(
            db or DB, [MARKET], "APEX GOLD DESK (veto-only Grok committee on Telegram signals)",
            [("Latest Telegram signals", feed + veto.table_html(
                ["Time (UTC)", "Side", "Entry zone", "Stop", "TP1 / TP2 / TP3", "Source"], rows))],
            refresh_s=60), encoding="utf-8")
    except Exception as exc:   # the dashboard must never stop the desk
        print(f"dashboard not written: {exc}")


def sweep(db=None, post=None, now=None):
    dec = review_pending(db, post, now)
    for ref, v in dec.items():
        print(f"{datetime.now(timezone.utc):%H:%M:%S} COMMITTEE {v} signal {ref[:8]}")
    grade(db)
    write_dashboard(db)
    return dec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    with connect() as con:
        con.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
        con.executescript(veto.SCHEMA)
    c = committee()
    print(f"APEX gold desk - committee {c.status}. Dashboard: {HTML}")
    while True:
        try:
            sweep()
        except Exception as exc:
            print(f"sweep failed: {type(exc).__name__}: {exc}")
        if a.once:
            return
        time.sleep(60)


if __name__ == "__main__":
    main()
