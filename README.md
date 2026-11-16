# project-apex

Project APEX - gold (XAUUSD) market intelligence and trading research.

## Gold desk: veto-only Grok committee on Telegram signals (paper)

Same design as the stock desk and Triple Seven. The Telegram channel supplies the trade;
a three-bot Grok committee can only **veto** it:

    News Checker (web + X search: US data due, Fed, DXY, yields)  ->  Skeptic  ->  Desk Lead

Code accepts a signal only if News != RED_FLAG, Skeptic != SKIP and Lead = APPROVE.
Any failure = VETO (fail closed). Signals older than 30 minutes are never reviewed.

Every signal is then **graded on the MT4 M1 prices** the collector records - vetoed ones
too - so `reports/gold_committee.html` shows whether the committee saves money:
BUY fills at the top of the entry zone (SELL at the bottom) within 4 hours, exit at the
first of stop / TP1 (TP2 noted if it came before the stop), spread deducted, R-multiples.

### Setup (Windows VPS)
```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # fill in XAI_API_KEY, TG_API_ID, TG_API_HASH, TG_CHANNELS
py -m pytest -q
```

### Run (three windows, from the project folder)
```
py -m collector.run_collector         # 1. MT4 prices every minute (needed for grading)
py -m collector.telegram_listener     # 2. signals -> committee (first run: phone + code login)
start reports\gold_committee.html     # 3. the dashboard (refreshes every minute)
```
`py -m desk.gold_desk` reviews/grades from the database without Telegram (any other feeder
that writes to the `signals` table works too).

Files: `desk/gold_prompts.json` (prompts, edit freely), `logs/gold_committee_chat.log`
(full chats), `database/apex.db`. Never commit `.env` or `apex_listener.session`.
