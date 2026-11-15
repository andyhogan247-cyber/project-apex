"""Veto-only Grok committee - the same design as Triple Seven's, shared by every desk.

The CODE picks the trades (a backtested rule). The committee can only VETO them:

    News Checker (web + X search)  ->  Skeptic (web + X search)  ->  Desk Lead

Code accepts a trade only if News != RED_FLAG, Skeptic != SKIP and Desk Lead == APPROVE.
Anything malformed, missing or failed = VETO (fail closed). The bots never add trades,
size them or move stops. Every decision is stored with the trade plan, so the desk can
later grade what the VETOED trades did against the APPROVED ones (is the committee
saving money or costing it?).

This file is deliberately self-contained (requests + sqlite3 only) so the same module
runs the US/UK stock desk and the APEX gold desk.

Prompts: a JSON file {"news": ..., "skeptic": ..., "lead": ...}, reloaded every meeting.
"""

import html
import json
import os
import re
import sqlite3
import time
from pathlib import Path

XAI_URL = "https://api.x.ai/v1/responses"
BEGIN, END = "BEGIN_JSON", "END_JSON"
SEARCH = [{"type": "web_search"}, {"type": "x_search"}]

SCHEMA = """
CREATE TABLE IF NOT EXISTS veto_meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, market TEXT, n INTEGER, status TEXT, transcript TEXT
);
CREATE TABLE IF NOT EXISTS veto_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, day TEXT, market TEXT, ref TEXT, symbol TEXT,
    direction TEXT, entry REAL, stop REAL, target REAL, facts TEXT,
    news TEXT, vote TEXT, lead TEXT, decision TEXT, reason TEXT, meeting_id INTEGER,
    outcome TEXT, outcome_r REAL, graded_ts REAL,
    UNIQUE (market, ref)
);
"""

STRUCT = {
    "news": ('{"news": [{"ref": "REF", "label": "CLEAR"}]}', "label: CLEAR, CAUTION or RED_FLAG"),
    "skeptic": ('{"votes": [{"ref": "REF", "vote": "WAIT"}]}', "vote: BUY, WAIT or SKIP"),
    "lead": ('{"decisions": [{"ref": "REF", "decision": "APPROVE", "reason": "short"}]}',
             "decision: APPROVE or VETO"),
}
VALID = {"news": {"CLEAR", "CAUTION", "RED_FLAG"}, "skeptic": {"BUY", "WAIT", "SKIP"},
         "lead": {"APPROVE", "VETO"}}
LIST_KEY = {"news": ("news", "label"), "skeptic": ("votes", "vote"), "lead": ("decisions", "decision")}


class CommitteeError(RuntimeError):
    pass


def connect(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def load_prompts(path) -> dict:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    for role, (example, rule) in STRUCT.items():
        p[role] += (f"\n\nAfter your report, end with exactly one block:\n{BEGIN}\n{example}\n{END}\n"
                    f"Valid JSON only, one entry per trade, keyed by its exact REF; {rule}.")
    return p


def parse_block(text: str, role: str) -> dict:
    """{ref: (VALUE, reason)} from a bot's JSON block. Malformed -> {} (missing counts as VETO)."""
    list_key, field = LIST_KEY[role]
    try:
        raw = text[text.index(BEGIN) + len(BEGIN): text.index(END)].strip().strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        out = {}
        for item in json.loads(raw).get(list_key, []):
            v = str(item.get(field, "")).upper().strip()
            if item.get("ref") and v in VALID[role]:
                out[str(item["ref"])] = (v, str(item.get("reason", ""))[:200])
        return out
    except (ValueError, AttributeError, TypeError):
        return {}


def _default_post(url, body, headers, timeout):
    import requests
    r = requests.post(url, json=body, headers=headers, timeout=(20, timeout))
    r.raise_for_status()
    return r.json()


class Committee:
    """review(items) -> {ref: 'APPROVE'|'VETO'}.  item = {ref, symbol, direction, entry, stop, target, facts}"""

    def __init__(self, db_path, market, prompts_path, log_path=None, key=None, model=None,
                 skeptic_model=None, search_roles=("news", "skeptic"), timeout=240,
                 max_output_tokens=3000, post=None, enabled=True):
        self.db_path, self.market = db_path, market
        self.prompts_path, self.log_path = prompts_path, log_path
        self.key = (key or os.getenv("XAI_API_KEY", "")).strip()
        self.model = model or os.getenv("GROK_MODEL", "grok-4.3")
        self.skeptic_model = skeptic_model or os.getenv("SKEPTIC_MODEL", self.model)
        self.search_roles, self.timeout, self.max_tokens = set(search_roles), timeout, max_output_tokens
        self.post = post or _default_post
        self.enabled = enabled and bool(self.key)
        self.status = "ON" if self.enabled else ("OFF (no XAI_API_KEY)" if enabled else "OFF")
        with connect(db_path):
            pass

    # ---------------------------------------------------------------- Grok
    def ask(self, system, chat, role):
        body = {"model": self.skeptic_model if role == "skeptic" else self.model,
                "input": [{"role": "system", "content": system}, {"role": "user", "content": chat}],
                "max_output_tokens": self.max_tokens}
        if role in self.search_roles:
            body["tools"] = SEARCH
        r = self.post(XAI_URL, body, {"Authorization": f"Bearer {self.key}",
                                      "Content-Type": "application/json"}, self.timeout)
        text = "\n".join(p.get("text", "") for it in (r or {}).get("output", []) if it.get("type") == "message"
                         for p in it.get("content", []) if p.get("type") == "output_text").strip()
        if not text:
            raise CommitteeError("Grok returned no text")
        return text

    def _log(self, transcript):
        if not self.log_path:
            return
        try:
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'=' * 80}\n{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} "
                        f"[{self.market}]\n{transcript}\n")
        except OSError:
            pass

    @staticmethod
    def table(items):
        lines = ["ref | symbol | direction | entry | stop | target | facts"]
        for it in items:
            facts = "; ".join(f"{k}={v}" for k, v in (it.get("facts") or {}).items())
            lines.append(f"{it['ref']} | {it['symbol']} | {it.get('direction', 'LONG')} | {it.get('entry')} | "
                         f"{it.get('stop')} | {it.get('target')} | {facts}")
        return "\n".join(lines)

    # ---------------------------------------------------------------- meeting
    def review(self, items, context="", ts=None) -> dict:
        ts = ts or time.time()
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        with connect(self.db_path) as con:
            done = {r["ref"]: r["decision"] for r in con.execute(
                "SELECT ref, decision FROM veto_decisions WHERE market=?", (self.market,))}
        todo = [it for it in items if it["ref"] not in done]
        out = {it["ref"]: done[it["ref"]] for it in items if it["ref"] in done}
        if not todo:
            return out
        chat = (f"UTC time {time.strftime('%Y-%m-%d %H:%M', time.gmtime(ts))}. Market: {self.market}. "
                f"{context}\nTrades the coded, backtested system wants to take:\n\n{self.table(todo)}")
        news = votes = lead = {}
        status = "OK"
        if not self.enabled:
            status = f"COMMITTEE {self.status} - all vetoed (fail closed)"
        else:
            try:
                P = load_prompts(self.prompts_path)
                msg = self.ask(P["news"], chat, "news")
                chat += f"\n\n[NEWS]\n{msg}"
                news = parse_block(msg, "news")
                msg = self.ask(P["skeptic"], chat, "skeptic")
                chat += f"\n\n[SKEPTIC]\n{msg}"
                votes = parse_block(msg, "skeptic")
                msg = self.ask(P["lead"], chat, "lead")
                chat += f"\n\n[DESK LEAD]\n{msg}"
                lead = parse_block(msg, "lead")
            except Exception as e:  # network, HTTP, bad prompts file: fail closed
                status = f"FAILED ({type(e).__name__}: {str(e)[:120]}) - all vetoed (fail closed)"
        self._log(chat + f"\n[SYSTEM] {status}")
        with connect(self.db_path) as con:
            mid = con.execute("INSERT INTO veto_meetings(ts, market, n, status, transcript) VALUES(?,?,?,?,?)",
                              (ts, self.market, len(todo), status, chat[:60000])).lastrowid
            for it in todo:
                ref = it["ref"]
                n, v, ld = news.get(ref, ("?", ""))[0], votes.get(ref, ("?", ""))[0], lead.get(ref, ("?", ""))
                ok = status == "OK" and n in {"CLEAR", "CAUTION"} and v in {"BUY", "WAIT"} and ld[0] == "APPROVE"
                why = ("approved" if ok else "meeting failed" if status != "OK" else
                       "RED_FLAG from News" if n == "RED_FLAG" else "Skeptic voted SKIP" if v == "SKIP" else
                       "Desk Lead VETO" if ld[0] == "VETO" else "missing/unreadable answer")
                out[ref] = "APPROVE" if ok else "VETO"
                con.execute(
                    "INSERT OR IGNORE INTO veto_decisions(ts, day, market, ref, symbol, direction, entry, stop, "
                    "target, facts, news, vote, lead, decision, reason, meeting_id) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ts, day, self.market, ref, it["symbol"], it.get("direction", "LONG"), it.get("entry"),
                     it.get("stop"), it.get("target"), json.dumps(it.get("facts") or {}, default=str),
                     n, v, ld[0], out[ref], f"{why}: {ld[1]}"[:240], mid))
        return out


# -------------------------------------------------------------------- grading
def ungraded(db_path, market):
    with connect(db_path) as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM veto_decisions WHERE market=? AND (outcome IS NULL OR outcome='OPEN')", (market,))]


def set_outcome(db_path, market, ref, outcome, r_multiple=None):
    with connect(db_path) as con:
        con.execute("UPDATE veto_decisions SET outcome=?, outcome_r=?, graded_ts=? WHERE market=? AND ref=?",
                    (outcome, r_multiple, time.time(), market, ref))


def grade_text(db_path, market) -> list:
    """APPROVE vs VETO on finished trades. A GOOD committee: VETO group loses more / wins less."""
    with connect(db_path) as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM veto_decisions WHERE market=?", (market,))]
    lines = [f"{market} COMMITTEE (veto-only): {len(rows)} decisions, "
             f"{sum(r['decision'] == 'APPROVE' for r in rows)} approved / {sum(r['decision'] == 'VETO' for r in rows)} vetoed",
             f"  {'group':8} {'finished':>8} {'stopped':>8} {'target':>7} {'avg R':>7}   (what each trade did, "
             f"vetoed ones included)"]
    for g in ("APPROVE", "VETO"):
        fin = [r for r in rows if r["decision"] == g and r["outcome"] not in (None, "OPEN", "NO_FILL")]
        if not fin:
            lines.append(f"  {g:8} {0:>8}   nothing finished yet")
            continue
        stop = sum(r["outcome"] == "STOP" for r in fin) / len(fin)
        tgt = sum(r["outcome"] in ("TARGET", "TP1", "TP2") for r in fin) / len(fin)
        avg = sum(r["outcome_r"] or 0 for r in fin) / len(fin)
        lines.append(f"  {g:8} {len(fin):>8} {stop:>8.0%} {tgt:>7.0%} {avg:>+7.2f}")
    reasons = {}
    for r in rows:
        if r["decision"] == "VETO":
            k = (r["reason"] or "").split(":")[0]
            reasons[k] = reasons.get(k, 0) + 1
    if reasons:
        lines.append("  veto reasons: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    lines.append("  GOOD committee = the VETO group's avg R is BELOW the APPROVE group's. Judge after ~20 finished each.")
    return lines


# -------------------------------------------------------------------- dashboard
STYLE = """body{font-family:Segoe UI,Arial,sans-serif;margin:20px;background:#0f1419;color:#e6e6e6}
h1{font-size:20px} h2{font-size:16px;margin-top:28px;color:#9ecbff} a{color:#9ecbff}
table{border-collapse:collapse;width:100%;font-size:12px} th,td{border-bottom:1px solid #2a3340;padding:4px 6px;text-align:left;vertical-align:top}
th{color:#9aa5b1} .k{display:inline-block;margin-right:28px} .k b{font-size:20px;display:block}
.ok{color:#5fd38d;font-weight:600} .no{color:#ff7b72;font-weight:600} .mid{color:#e3b341}
pre{white-space:pre-wrap;background:#161b22;padding:10px;border-radius:4px;font-size:12px;line-height:1.45}
details{margin:6px 0;border:1px solid #2a3340;border-radius:4px;padding:6px 10px} summary{cursor:pointer}
.role{color:#9ecbff;font-weight:700}"""
TAG = {"APPROVE": "ok", "VETO": "no", "RED_FLAG": "no", "CLEAR": "ok", "CAUTION": "mid", "BUY": "ok",
       "WAIT": "mid", "SKIP": "no", "STOP": "no", "TARGET": "ok", "TP1": "ok", "TP2": "ok", "OPEN": "mid"}


def _e(x):
    return html.escape(str(x if x is not None else ""))


def _badge(v):
    return f'<span class="{TAG.get(v, "")}">{_e(v or "-")}</span>'


def _t(ts):
    return time.strftime("%m-%d %H:%M", time.gmtime(ts)) if ts else "-"


def table_html(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>" if rows else "<p>none yet</p>"


def chat_html(text):
    """Escape first (bot text comes from the web), then highlight roles and make links clickable."""
    s = _e(text)
    s = re.sub(r"\[(NEWS|SKEPTIC|DESK LEAD|SYSTEM)\]", r'<span class="role">[\1]</span>', s)
    return re.sub(r"(https?://[^\s<>&()\[\]]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)


def dashboard_html(db_path, markets, title, sections=(), refresh_s=300):
    """Full page for one desk. `sections` = extra (heading, html) blocks, e.g. the paper book."""
    with connect(db_path) as con:
        q = ",".join("?" * len(markets))
        dec = [dict(r) for r in con.execute(
            f"SELECT * FROM veto_decisions WHERE market IN ({q}) ORDER BY id DESC LIMIT 200", markets)]
        meets = [dict(r) for r in con.execute(
            f"SELECT * FROM veto_meetings WHERE market IN ({q}) ORDER BY id DESC LIMIT 30", markets)]
    kpis = "".join(
        f'<span class="k">{_e(m)} approved<b class="ok">{sum(d["decision"] == "APPROVE" for d in dec if d["market"] == m)}</b></span>'
        f'<span class="k">{_e(m)} vetoed<b class="no">{sum(d["decision"] == "VETO" for d in dec if d["market"] == m)}</b></span>'
        for m in markets)
    last = meets[0] if meets else None
    last_txt = (f"{_t(last['ts'])} UTC - {_e(last['market'])} - "
                + ('<span class="ok">OK</span>' if (last["status"] or "").startswith("OK") else _badge("VETO") + " " + _e(last["status"]))
                if last else "no meeting yet")
    rows = [[_t(d["ts"]), _e(d["market"]), _e(d["symbol"]), _e(d["direction"]),
             f"{_e(d['entry'])} / {_e(d['stop'])} / {_e(d['target'])}", _badge(d["news"]), _badge(d["vote"]),
             _badge(d["lead"]), _badge(d["decision"]), _e(d["reason"]),
             (_badge(d["outcome"]) + (f" {d['outcome_r']:+.2f}R" if d["outcome_r"] is not None else "")) if d["outcome"] else "-"]
            for d in dec]
    chats = "".join(
        f"<details><summary>{_t(m['ts'])} UTC &middot; {_e(m['market'])} &middot; {m['n']} trade(s) &middot; "
        f"{'OK' if (m['status'] or '').startswith('OK') else _e(m['status'])}</summary><pre>{chat_html(m['transcript'])}</pre>"
        f"</details>" for m in meets) or "<p>no meetings yet</p>"
    grade = _e("\n".join(line for m in markets for line in grade_text(db_path, m)))
    extra = "".join(f"<h2>{_e(h)}</h2>{body}" for h, body in sections)
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="{refresh_s}">
<title>{_e(title)}</title><style>{STYLE}</style></head><body>
<h1>{_e(title)} &mdash; {_t(time.time())} UTC</h1>
<div>{kpis}</div><p>Last meeting: {last_txt}</p>
<p style="color:#9aa5b1">Code accepts a trade only if News &ne; RED_FLAG, Skeptic &ne; SKIP and Desk Lead = APPROVE.
Any failure = VETO. The bots cannot add trades, size them or move stops.</p>
{extra}
<h2>Decisions and what each trade did (vetoed ones too)</h2>
{table_html(["Time", "Market", "Symbol", "Side", "Entry / stop / target", "News", "Skeptic", "Lead", "Decision", "Reason", "Outcome"], rows)}
<h2>Grading</h2><pre>{grade}</pre>
<h2>Meeting chats (newest first - click to open)</h2>{chats}
<p style="color:#9aa5b1">Paper trading research. Not financial advice.</p></body></html>"""
