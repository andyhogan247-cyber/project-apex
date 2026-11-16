"""Gold signal study on synthetic data: parsing, grading, features, and the filter test."""
import json
from datetime import datetime, timedelta, timezone

from research import signal_study as ss


def test_tolerant_parser():
    p = ss.parse("XAUUSD BUY @ 2650/2647\nSL 2640\nTP 2655\nTP 2660")
    assert p["direction"] == "BUY" and p["entry_high"] == 2650 and p["stop_loss"] == 2640 and p["tp2"] == 2660
    p = ss.parse("GOLD SELL NOW 2,701 - 2,704\nSL: 2712\nTP1: 2695\nTP2: 2690")
    assert p["direction"] == "SELL" and p["entry_low"] == 2701 and p["tp1"] == 2695
    assert ss.parse("Great week! +500 pips BUY BUY BUY") is None
    assert ss.parse("BUY @ 2650/2647 SL 2660 TP 2655") is None, "stop on the wrong side -> rejected"


def make_world(n_days=60):
    """Gold drifts sideways; London BUY signals reach TP1, Asia BUY signals hit the stop."""
    t0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    bars, msgs, price = [], [], 2600.0
    minute = 0
    for d in range(n_days):
        day = t0 + timedelta(days=d)
        for h in range(24):
            for m in range(60):
                t = day + timedelta(hours=h, minutes=m)
                bars.append({"t": t, "o": price, "h": price + 0.2, "l": price - 0.2, "c": price})
        # Asia signal at 03:00 (loses), London signal at 09:00 (wins)
        for hour, win in ((3, False), (9, True)):
            st = day + timedelta(hours=hour)
            msgs.append({"id": len(msgs), "type": "message", "date_unixtime": str(int(st.timestamp())),
                         "text": f"XAUUSD BUY @ {price:.0f}/{price - 3:.0f}\nSL {price - 10:.0f}\nTP {price + 5:.0f}\nTP {price + 10:.0f}"})
            i0 = int((st - bars[0]["t"]).total_seconds() // 60) + 30
            for j in range(i0, i0 + 20):
                b = bars[j]
                if win:
                    b["h"] = price + 6
                else:
                    b["l"] = price - 11
    return bars, {"messages": msgs}


def test_study_finds_the_session_effect_and_beats_random(tmp_path):
    bars, tg = make_world()
    f = tmp_path / "result.json"
    f.write_text(json.dumps(tg))
    sigs, misses = ss.load_signals(f)
    assert len(sigs) == 120 and not misses
    rows = ss.study(sigs, bars)
    by = {s: ss.stats([r for r in rows if r["session"] == s]) for s in ("Asia", "London")}
    assert by["London"]["win"] == 1 and by["Asia"]["win"] == 0
    ft = ss.filter_test(rows, min_n=10)
    assert ("session", "London") in ft["chosen"]
    assert ft["oos_filtered"]["avg_r"] > 0 > ft["oos_all"]["avg_r"] or ft["oos_filtered"]["avg_r"] > ft["oos_all"]["avg_r"]
    assert ft["beats_random_pct"] >= 0.95


def test_mt4_csv_and_server_clock(tmp_path):
    p = tmp_path / "XAUUSD1.csv"
    p.write_text("2026.01.05,10:00,2600.1,2600.5,2599.9,2600.2,10\n2026.01.05,10:01,2600.2,2600.6,2600.0,2600.3,12\n")
    bars = ss.load_prices(p)                     # server 10:00 in January = 08:00 UTC (GMT+2)
    assert bars[0]["t"] == datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc) and bars[1]["c"] == 2600.3
    summer = tmp_path / "s.csv"
    summer.write_text("2026.07.06,10:00,1,1,1,1,1\n")
    assert ss.load_prices(summer)[0]["t"].hour == 7, "GMT+3 while US summer time is on"
    assert ss.load_prices(p, "fixed", 0)[0]["t"].hour == 10


def test_html_export(tmp_path):
    page = """<div class="message service" id="message-1"><div class="body details">16 November 2026</div></div>
<div class="message default clearfix" id="message2"><div class="body">
<div class="pull_right date details" title="16.11.2026 09:15:00 UTC+01:00">09:15</div>
<div class="from_name">Gold VIP</div>
<div class="text">XAUUSD BUY @ 2650/2647<br>SL 2640<br>TP 2655<br>TP 2660</div></div></div>
<div class="message default clearfix joined" id="message3"><div class="body">
<div class="pull_right date details" title="16.11.2026 10:00:00 UTC+01:00">10:00</div>
<div class="text">TP1 hit &#43;50 pips &amp; running</div></div></div>"""
    (tmp_path / "messages.html").write_text(page, encoding="utf-8")
    (tmp_path / "messages2.html").write_text(page.replace("09:15:00", "11:15:00"), encoding="utf-8")
    sigs, misses = ss.load_signals(tmp_path)
    assert len(sigs) == 2 and sigs[0]["time"] == datetime(2026, 11, 16, 8, 15, tzinfo=timezone.utc)
    assert sigs[0]["stop_loss"] == 2640 and sigs[1]["time"].hour == 10
