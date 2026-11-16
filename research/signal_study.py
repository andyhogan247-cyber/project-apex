"""Gold signal study: which Telegram signals actually win, and can rules known AT SIGNAL TIME
pick the better ones? (Hypothesis 1 in "Trading Edge Hypotheses - Who Pays Me?")

Inputs (both exported by you, nothing is downloaded):
  1. Telegram Desktop -> the channel -> ... -> Export chat history -> format JSON
     -> result.json  (ALL messages, so we see every signal, not just the celebrated ones)
  2. XAUUSD M1 history as CSV covering the same dates. MT4: Tools -> History Center ->
     XAUUSD -> 1 Minute -> Export  (rows: 2025.05.01,10:12,open,high,low,close,volume).
     MT4 times are broker SERVER time; --server-tz nyclose (default) = New York time + 7h,
     the usual GMT+2/GMT+3 broker clock. Use --server-offset 0 if your CSV is already UTC.

What it does:
  * parses every message that looks like a signal (tolerant formats) and lists the misses
  * grades each signal on the M1 prices exactly like the gold desk: BUY fills at the TOP of
    the zone (SELL at the bottom) within 4 h; first of stop / TP1 (TP2 if reached first);
    24 h time limit; spread deducted; result in R (multiples of the risk)
  * features known at signal time: session, hour, weekday, direction, H1 trend (EMA50),
    4 h move, how far price already ran past the zone, stop size vs H1 ATR
  * win rate / expectancy by feature, then a fair filter test: pick at most 3 rules on the
    first 70% of signals, judge them on the last 30% against 2,000 random subsets
Writes research/out/signals.csv (one row per signal) and prints the report.

Usage:  py -m research.signal_study --telegram C:\\path\\result.json --prices C:\\path\\XAUUSD1.csv
"""

import argparse
import csv
import json
import math
import random
import re
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from desk.gold_desk import simulate

OUT = Path(__file__).resolve().parent / "out"
NY = ZoneInfo("America/New_York")
NUM = r"(\d{3,5}(?:\.\d+)?)"


# ------------------------------------------------------------------ Telegram
def message_text(m):
    t = m.get("text", "")
    if isinstance(t, list):
        t = "".join(x if isinstance(x, str) else x.get("text", "") for x in t)
    return t or ""


def parse(text):
    """Tolerant signal parser -> dict or None. Needs a direction, an entry, a stop and TP1."""
    u = text.upper().replace(",", "")
    if not re.search(r"\b(BUY|SELL)\b", u) or not re.search(r"\bSL\b|STOP\s*LOSS", u):
        return None
    direction = "BUY" if re.search(r"\bBUY\b", u) and not re.search(r"\bSELL\b", u) else (
        "SELL" if re.search(r"\bSELL\b", u) and not re.search(r"\bBUY\b", u) else None)
    if not direction:
        return None
    zone = (re.search(rf"@\s*{NUM}\s*[/\-]\s*{NUM}", u) or re.search(rf"(?:BUY|SELL)[^\d\n]*{NUM}\s*[/\-]\s*{NUM}", u))
    if zone:
        a, b = float(zone.group(1)), float(zone.group(2))
    else:
        one = re.search(rf"(?:BUY|SELL|@)[^\d\n]*{NUM}", u)
        if not one:
            return None
        a = b = float(one.group(1))
    sl = re.search(rf"(?:\bSL\b|STOP\s*LOSS)\s*[:=@]?\s*{NUM}", u)
    tps = [float(x) for x in re.findall(rf"\bTP\d?\s*[:=@]?\s*{NUM}", u)]
    if not sl or not tps:
        return None
    s = {"direction": direction, "entry_high": max(a, b), "entry_low": min(a, b),
         "stop_loss": float(sl.group(1)), "tp1": tps[0], "tp2": tps[1] if len(tps) > 1 else tps[0]}
    # sanity: stop and target on the right sides of the zone
    if direction == "BUY" and not (s["stop_loss"] < s["entry_low"] and s["tp1"] > s["entry_high"]):
        return None
    if direction == "SELL" and not (s["stop_loss"] > s["entry_high"] and s["tp1"] < s["entry_low"]):
        return None
    return s


HTML_MSG = re.compile(r'<div class="message default[^"]*"(.*?)(?=<div class="message (?:default|service)|\Z)', re.S)
HTML_DATE = re.compile(r'class="pull_right date details" title="(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d):(\d\d)'
                       r'(?: UTC([+-]\d\d):(\d\d))?"')
HTML_TEXT = re.compile(r'<div class="text">(.*?)</div>', re.S)


def html_messages(path, utc_offset_hours=0.0):
    """Telegram Desktop HTML export (messages.html, messages2.html, ...) -> JSON-export-like dicts."""
    import html as _html
    p = Path(path)
    files = sorted(p.glob("messages*.html"), key=lambda f: int(re.sub(r"\D", "", f.stem) or 1)) if p.is_dir() else [p]
    out = []
    for f in files:
        for block in HTML_MSG.findall(f.read_text(encoding="utf-8")):
            d, t = HTML_DATE.search(block), HTML_TEXT.search(block)
            if not d or not t:
                continue
            dd, mm, yy, hh, mi, ss_, oh, om = d.groups()
            off = (int(oh) + (1 if int(oh) >= 0 else -1) * int(om) / 60) if oh else utc_offset_hours
            when = datetime(int(yy), int(mm), int(dd), int(hh), int(mi), int(ss_), tzinfo=timezone.utc) - timedelta(hours=off)
            text = re.sub(r"<br\s*/?>", "\n", t.group(1))
            text = _html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
            out.append({"type": "message", "date_unixtime": str(int(when.timestamp())), "text": text, "id": len(out)})
    return out


def load_signals(path, html_utc_offset=0.0):
    """JSON export (result.json) or HTML export (messages*.html file or its folder)."""
    p = Path(path)
    if p.is_dir() or p.suffix.lower() in (".html", ".htm"):
        msgs = html_messages(p, html_utc_offset)
    else:
        msgs = json.loads(p.read_text(encoding="utf-8")).get("messages", [])
    sigs, misses = [], []
    for m in msgs:
        if m.get("type") != "message":
            continue
        text = message_text(m)
        when = (datetime.fromtimestamp(int(m["date_unixtime"]), timezone.utc) if m.get("date_unixtime")
                else datetime.fromisoformat(m["date"]).replace(tzinfo=timezone.utc))
        s = parse(text)
        if s:
            s.update(id=m.get("id"), time=when, text=text[:200])
            sigs.append(s)
        elif re.search(r"\b(BUY|SELL)\b", text.upper()) and re.search(r"\bSL\b|\bTP", text.upper()):
            misses.append(text[:160].replace("\n", " | "))
    return sigs, misses


# ------------------------------------------------------------------ prices
def server_to_utc(dt, mode, offset):
    if mode == "nyclose":                   # broker clock = New York + 7 h (GMT+2 winter / GMT+3 summer)
        ny = (dt - timedelta(hours=7)).replace(tzinfo=NY)
        return ny.astimezone(timezone.utc)
    return (dt - timedelta(hours=offset)).replace(tzinfo=timezone.utc)


def load_prices(path, mode="nyclose", offset=0.0):
    """MT4 export (date,time,o,h,l,c,v) or a header CSV with time/open/high/low/close. -> sorted M1 bars (UTC)."""
    bars = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.reader(f):
            if not row or not row[0][:1].isdigit():
                continue
            try:
                if len(row) >= 6 and ":" in row[1]:
                    dt = datetime.strptime(f"{row[0]} {row[1]}", "%Y.%m.%d %H:%M")
                    o, h, l, c = map(float, row[2:6])
                else:
                    dt = datetime.fromisoformat(row[0].replace("Z", "").replace(".", "-", 2)[:19])
                    o, h, l, c = map(float, row[1:5])
            except ValueError:
                continue
            t = server_to_utc(dt, mode, offset)
            bars.append({"t": t, "o": o, "h": h, "l": l, "c": c})
    bars.sort(key=lambda b: b["t"])
    return bars


def h1_series(bars):
    """Hourly closes + ATR14 + EMA50 keyed by the hour's START (UTC)."""
    hours = {}
    for b in bars:
        k = b["t"].replace(minute=0, second=0, microsecond=0)
        x = hours.setdefault(k, {"o": b["o"], "h": b["h"], "l": b["l"], "c": b["c"]})
        x["h"], x["l"], x["c"] = max(x["h"], b["h"]), min(x["l"], b["l"]), b["c"]
    keys = sorted(hours)
    ema, atr, prev_c, out = None, None, None, {}
    for k in keys:
        x = hours[k]
        tr = x["h"] - x["l"] if prev_c is None else max(x["h"] - x["l"], abs(x["h"] - prev_c), abs(x["l"] - prev_c))
        atr = tr if atr is None else (atr * 13 + tr) / 14
        ema = x["c"] if ema is None else ema + (x["c"] - ema) * 2 / 51
        out[k] = {"c": x["c"], "atr": atr, "ema": ema}
        prev_c = x["c"]
    return keys, out


# ------------------------------------------------------------------ features + grading
def session(hour):
    return ("Asia" if hour < 7 else "London" if hour < 12 else "London/NY" if hour < 16
            else "NY" if hour < 21 else "Late")


def study(signals, bars, spread=0.30):
    import bisect
    times = [b["t"] for b in bars]
    hkeys, h1 = h1_series(bars)
    rows = []
    for s in signals:
        i = bisect.bisect_left(times, s["time"])
        if i == 0 or i >= len(bars):
            continue
        price = bars[i - 1]["c"]
        k = bisect.bisect_left(hkeys, s["time"].replace(minute=0, second=0, microsecond=0)) - 1
        if k < 50:
            continue
        h = h1[hkeys[k]]
        h4 = h1[hkeys[k - 4]]["c"]
        buy = s["direction"] == "BUY"
        entry = s["entry_high"] if buy else s["entry_low"]
        risk = abs(entry - s["stop_loss"])
        future = [{"timestamp": b["t"].replace(tzinfo=None).isoformat(), "m1_high": b["h"], "m1_low": b["l"],
                   "mid": b["c"]} for b in bars[i:i + 60 * 30]]
        outcome, r = simulate(s, future, spread)
        sign = 1 if buy else -1
        rows.append({
            "time": s["time"].isoformat(timespec="minutes"), "direction": s["direction"],
            "entry": entry, "stop": s["stop_loss"], "tp1": s["tp1"], "outcome": outcome, "r": r,
            "hour": s["time"].hour, "session": session(s["time"].hour), "weekday": s["time"].strftime("%a"),
            "trend": "with" if sign * (h["c"] - h["ema"]) > 0 else "against",
            "move_4h_atr": round(sign * (h["c"] - h4) / h["atr"], 2) if h["atr"] else 0,
            "run_past_zone_r": round(sign * (price - entry) / risk, 2) if risk else 0,
            "stop_atr": round(risk / h["atr"], 2) if h["atr"] else 0,
            "tp1_r": round(abs(s["tp1"] - entry) / risk, 2) if risk else 0,
        })
    return rows


def finished(rows):
    return [r for r in rows if r["outcome"] in ("STOP", "TP1", "TP2", "TIME")]


def stats(rows):
    f = finished(rows)
    if not f:
        return {"n": 0}
    rs = [r["r"] for r in f]
    return {"n": len(f), "win": sum(r["outcome"] in ("TP1", "TP2") for r in f) / len(f),
            "avg_r": statistics.mean(rs), "total_r": sum(rs),
            "t": statistics.mean(rs) / (statistics.stdev(rs) / math.sqrt(len(rs))) if len(rs) > 2 and statistics.stdev(rs) else 0}


def bucket(v, edges):
    for e in edges:
        if v <= e:
            return f"<={e}"
    return f">{edges[-1]}"


RULES = {
    "direction": lambda r: r["direction"],
    "session": lambda r: r["session"],
    "weekday": lambda r: r["weekday"],
    "trend": lambda r: r["trend"],
    "move_4h_atr": lambda r: bucket(r["move_4h_atr"], [-2, -0.5, 0.5, 2]),
    "run_past_zone_r": lambda r: bucket(r["run_past_zone_r"], [-0.5, 0, 0.5]),
    "stop_atr": lambda r: bucket(r["stop_atr"], [0.5, 1, 2]),
    "tp1_r": lambda r: bucket(r["tp1_r"], [0.5, 1, 1.5]),
}


def filter_test(rows, max_rules=3, min_n=25, trials=2000, seed=7):
    """Choose up to 3 'keep only X' rules on the first 70%, judge on the last 30% vs random subsets."""
    f = sorted(finished(rows), key=lambda r: r["time"])
    cut = int(len(f) * 0.7)
    ins, oos = f[:cut], f[cut:]
    cands = []
    for name, fn in RULES.items():
        for val in sorted({fn(r) for r in ins}):
            sub = [r for r in ins if fn(r) == val]
            if len(sub) >= min_n:
                cands.append((statistics.mean(r["r"] for r in sub), name, val, len(sub)))
    cands.sort(reverse=True)
    chosen, keep = [], ins
    for avg, name, val, n in cands:
        if len(chosen) >= max_rules:
            break
        nxt = [r for r in keep if RULES[name](r) == val]
        if len(nxt) >= min_n and statistics.mean(r["r"] for r in nxt) > statistics.mean(r["r"] for r in keep):
            chosen.append((name, val))
            keep = nxt
    picked = [r for r in oos if all(RULES[n](r) == v for n, v in chosen)]
    base, got = stats(oos), stats(picked)
    rnd = random.Random(seed)
    beat = 0
    if picked and len(picked) < len(oos):
        for _ in range(trials):
            sample = rnd.sample(oos, len(picked))
            beat += statistics.mean(r["r"] for r in sample) < got["avg_r"]
        pct = beat / trials
    else:
        pct = None
    return {"chosen": chosen, "in_sample": stats(keep), "oos_all": base, "oos_filtered": got,
            "beats_random_pct": pct, "split": f[cut]["time"] if cut < len(f) else None}


# ------------------------------------------------------------------ report
def fmt(s):
    if not s.get("n"):
        return "n=0"
    return f"n={s['n']:>4}  win {s['win']:>4.0%}  avg {s['avg_r']:+.2f}R  total {s['total_r']:+7.1f}R  t {s['t']:+.2f}"


def report(rows, misses, n_signals):
    print(f"Signals parsed: {n_signals}  graded: {len(rows)}  "
          f"(not filled within 4h: {sum(r['outcome'] == 'NO_FILL' for r in rows)}, "
          f"still open at data end: {sum(r['outcome'] == 'OPEN' for r in rows)})")
    if misses:
        print(f"Messages that looked like signals but did not parse: {len(misses)} - first 5:")
        for m in misses[:5]:
            print("   ", m)
    print("\nALL SIGNALS (enter at top of zone, exit TP1/TP2 or stop, spread deducted):")
    print("  ", fmt(stats(rows)))
    for name, fn in RULES.items():
        print(f"\nBy {name}:")
        for val in sorted({fn(r) for r in finished(rows)}):
            print(f"   {str(val):>10}  {fmt(stats([r for r in rows if fn(r) == val]))}")
    ft = filter_test(rows)
    print("\nFILTER TEST (rules chosen on the first 70%, judged on the last 30%):")
    print("  rules chosen:", " AND ".join(f"{n} = {v}" for n, v in ft["chosen"]) or "none beat 'take everything'")
    print("  in-sample with rules:   ", fmt(ft["in_sample"]))
    print(f"  out-of-sample, all      ({ft['split']} on): {fmt(ft['oos_all'])}")
    print("  out-of-sample, filtered:", fmt(ft["oos_filtered"]))
    if ft["beats_random_pct"] is not None:
        print(f"  filtered beats {ft['beats_random_pct']:.0%} of random subsets of the same size (need >= 95%)")
    print("\nVERDICT RULE: the filter is real only if out-of-sample avg R is positive after spread AND it beats"
          " >= 95% of random subsets. Otherwise the channel has no edge we can isolate.")
    return ft


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--telegram", required=True, help="result.json, or the HTML export folder / messages.html")
    ap.add_argument("--html-utc-offset", type=float, default=0.0,
                    help="only for old HTML exports without 'UTC+hh:mm' in the date: your PC's UTC offset then")
    ap.add_argument("--prices", required=True)
    ap.add_argument("--server-tz", choices=["nyclose", "fixed"], default="nyclose")
    ap.add_argument("--server-offset", type=float, default=0.0, help="hours ahead of UTC when --server-tz fixed")
    ap.add_argument("--spread", type=float, default=0.30)
    a = ap.parse_args()
    sigs, misses = load_signals(a.telegram, a.html_utc_offset)
    bars = load_prices(a.prices, a.server_tz, a.server_offset)
    print(f"Prices: {len(bars):,} M1 bars {bars[0]['t']:%Y-%m-%d} to {bars[-1]['t']:%Y-%m-%d} (UTC)" if bars
          else "No price rows read - check the CSV format")
    rows = study(sigs, bars, a.spread)
    report(rows, misses, len(sigs))
    OUT.mkdir(exist_ok=True)
    if rows:
        with open(OUT / "signals.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\nEvery signal with its features and result: {OUT / 'signals.csv'}")


if __name__ == "__main__":
    main()
