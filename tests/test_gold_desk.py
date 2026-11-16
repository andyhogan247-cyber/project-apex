"""APEX gold desk: Telegram signal -> committee veto -> graded on MT4 M1 prices.  python -m pytest tests"""
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from collector import telegram_listener as tl
from desk import gold_desk, veto

ROOT = Path(__file__).resolve().parents[1]
MSG = "XAUUSD BUY @ 2650/2647\nSL 2640\nTP 2655\nTP 2660\nTP 2670\nTP OPEN"
T0 = datetime(2026, 11, 16, 14, 0, tzinfo=timezone.utc)


def grok(lead="APPROVE", news="CLEAR", vote="WAIT", calls=None):
    def post(url, body, headers, timeout):
        system, chat = body["input"][0]["content"], body["input"][1]["content"]
        if calls is not None:
            calls.append(body)
        refs = re.findall(r"^(\S+:\d+) \|", chat, re.M)
        blk = ({"news": [{"ref": r, "label": news} for r in refs]} if '"news"' in system else
               {"votes": [{"ref": r, "vote": vote} for r in refs]} if '"votes"' in system else
               {"decisions": [{"ref": r, "decision": lead, "reason": "t"} for r in refs]})
        text = f"CPI at 13:30 https://example.com/cal\nBEGIN_JSON\n{json.dumps(blk)}\nEND_JSON"
        return {"output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
    return post


@pytest.fixture
def db(tmp_path, monkeypatch):
    p = tmp_path / "apex.db"
    with sqlite3.connect(p) as con:
        con.executescript((ROOT / "database" / "schema.sql").read_text(encoding="utf-8"))
    monkeypatch.setattr(gold_desk, "HTML", tmp_path / "gold.html")
    monkeypatch.setattr(gold_desk, "LOG", tmp_path / "chat.log")
    monkeypatch.setenv("XAI_API_KEY", "xk")
    monkeypatch.setenv("COMMITTEE", "true")
    return p


def bars(db, start, rows):
    """rows: list of (high, low) per minute from `start`."""
    with sqlite3.connect(db) as con:
        for i, (h, l) in enumerate(rows):
            t = (start + timedelta(minutes=i)).replace(tzinfo=None).isoformat(timespec="seconds")
            m = (h + l) / 2
            con.execute("INSERT INTO market_observations (timestamp, symbol, bid, ask, mid, spread, m1_open, "
                        "m1_high, m1_low, m1_close, tick_volume, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (t, "XAUUSD", m - 0.15, m + 0.15, m, 0.3, m, h, l, m, 100, "MT4"))


def decisions(db):
    with veto.connect(db) as con:
        return {r["ref"]: dict(r) for r in con.execute("SELECT * FROM veto_decisions")}


def test_signal_approved_then_graded_tp1(db, monkeypatch):
    monkeypatch.setattr(gold_desk.time, "time", lambda: T0.timestamp() + 30)
    bars(db, T0 - timedelta(hours=5), [(2652, 2650)] * 3)
    calls = []
    assert tl.handle_text(MSG, T0, "goldchan", db, grok(calls=calls)) == "APPROVE"
    assert len(calls) == 3 and calls[0].get("tools") and "tools" not in calls[1], "only News searches (speed)"
    assert "price_now" in calls[0]["input"][1]["content"] and "channel_last30_buy_share" in calls[0]["input"][1]["content"]
    assert tl.handle_text(MSG, T0, "goldchan", db, grok(calls=calls)) is None and len(calls) == 3, "no duplicates"
    assert tl.handle_text("Great week team! +350 pips", T0, "goldchan", db, grok()) is None
    # price: dips into the zone (fill at 2650), then reaches TP1 2655 but not TP2 before the stop
    bars(db, T0 + timedelta(minutes=1), [(2651, 2649), (2653, 2650), (2656, 2652), (2650, 2639)])
    gold_desk.grade(db)
    d = decisions(db)["goldchan:%d" % T0.timestamp()]
    # half at TP1 (+0.5R) = +0.25R, other half back to break-even (0), minus spread 0.03R
    assert d["decision"] == "APPROVE" and d["outcome"] == "TP1" and d["outcome_r"] == pytest.approx(0.22, abs=0.01)
    gold_desk.write_dashboard(db)
    page = gold_desk.HTML.read_text(encoding="utf-8")
    assert "TP1" in page and 'href="https://example.com/cal"' in page and "Latest Telegram signals" in page


def test_red_flag_vetoes_and_veto_is_still_graded(db, monkeypatch):
    monkeypatch.setattr(gold_desk.time, "time", lambda: T0.timestamp() + 30)
    assert tl.handle_text(MSG, T0, "goldchan", db, grok(news="RED_FLAG")) == "VETO"
    bars(db, T0 + timedelta(minutes=1), [(2650, 2648), (2645, 2639)])
    gold_desk.grade(db)
    d = list(decisions(db).values())[0]
    assert d["reason"].startswith("RED_FLAG") and d["outcome"] == "STOP" and d["outcome_r"] < -1
    assert any("VETO" in line for line in veto.grade_text(db, "GOLD"))


def test_fail_closed_and_stale_signals(db, monkeypatch):
    def down(url, body, headers, timeout):
        raise ConnectionError("xAI down")
    monkeypatch.setattr(gold_desk.time, "time", lambda: T0.timestamp() + 30)
    assert tl.handle_text(MSG, T0, "goldchan", db, down) == "VETO"
    monkeypatch.setattr(gold_desk.time, "time", lambda: T0.timestamp() + 3 * 3600)
    late = T0 + timedelta(minutes=5)
    calls = []
    assert tl.handle_text(MSG, late, "goldchan", db, grok(calls=calls)) is None and not calls, "stale: never reviewed"


def test_simulate_sell_no_fill_and_tp2():
    sig = {"direction": "SELL", "entry_high": 2650, "entry_low": 2647, "stop_loss": 2657, "tp1": 2640, "tp2": 2630}
    t = lambda i: (T0 + timedelta(minutes=i)).replace(tzinfo=None).isoformat()
    row = lambda i, h, l: {"timestamp": t(i), "m1_high": h, "m1_low": l, "mid": (h + l) / 2}
    assert gold_desk.simulate(sig, [row(0, 2640, 2635)] + [row(300, 2640, 2635)])[0] == "NO_FILL"
    out, r = gold_desk.simulate(sig, [row(0, 2648, 2646), row(1, 2645, 2638), row(2, 2635, 2629)])
    assert out == "TP2" and r == pytest.approx(0.5 * 0.7 + 0.5 * 1.7), "half at TP1, half at TP2"
    bad = dict(sig, direction="BUY", entry_high=3894, entry_low=3890, stop_loss=3884, tp1=3897, tp2=3400)
    trow = lambda i, h, l: {"timestamp": t(i), "m1_high": h, "m1_low": l, "mid": (h + l) / 2}
    out, r = gold_desk.simulate(bad, [trow(0, 3895, 3893), trow(1, 3898, 3895)])
    assert out == "TP1" and r == pytest.approx(0.3), "a mistyped TP2 below a BUY entry is ignored, never a +49R win"
    out, r = gold_desk.simulate(sig, [row(0, 2648, 2646), row(1, 2659, 2650)], slip=0.5)
    assert out == "STOP" and r == pytest.approx(-(2657.5 - 2646.5) / (2657 - 2646.5), abs=1e-3), "slippage on entry and stop"
