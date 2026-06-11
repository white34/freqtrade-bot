# freqtrade-bot v2

Full from-scratch rebuild (started 2026-06-11) of the original May-2026 freqtrade project.
The old project lives untouched in `_archive/` (gitignored) as read-only reference —
its post-mortem and the rules for this rebuild are in [METHODOLOGY.md](METHODOLOGY.md),
and every experiment is recorded in [RESEARCH_LOG.md](RESEARCH_LOG.md).

## Status

- **Phase 0 (scaffold): done** — fresh config (new secrets), compose without the
  `--strategy` footgun, git, alerting wiring.
- **Phase 1 (methodology): awaiting user review** of METHODOLOGY.md.
- **Phase 2 (strategies): not started.** No strategy exists yet, so `docker compose up`
  will not work until Candidate L lands and `"strategy"` is set in `user_data/config.json`.

## One-time setup

1. **Telegram alerting** (do this — the old bot died silently and nobody noticed for 3 weeks):
   follow the steps in `.env.example`, fill `.env`, set `FREQTRADE__TELEGRAM__ENABLED=true`.
2. **Laptop power settings**: Settings → System → Power → set "Make my device sleep" to
   **Never** while plugged in. A sleeping laptop = data gaps = missed entries/exits
   (the old bot logged 274 outdated-history events).
3. **Uptime heartbeat**: create a free check at https://healthchecks.io, then schedule a
   ping (Task Scheduler, every 5 min) that only fires while the container runs:
   `powershell -Command "if (docker ps -q -f name=freqtrade) { curl.exe -fsS -m 10 https://hc-ping.com/<your-uuid> | Out-Null }"`
   You get an email when pings stop = bot/laptop is down.

## Daily operation

```powershell
docker compose up -d          # start
docker compose logs -f --tail 50 freqtrade   # watch
docker compose down           # stop
```

FreqUI: http://127.0.0.1:8080 (credentials in `user_data/config.json`).

## Rules carried over from the old project (hard-won)

- Strategy selection ONLY via `config.json` — never add `--strategy` to docker-compose.
- After any hyperopt, diff the generated `user_data/strategies/<Name>.json` against what
  you intended — the JSON silently overrides the `.py` defaults (this bit us: "broken exits").
- Every stoploss/ROI number is a **leveraged stake ratio**, not a price move. See the
  risk-model table in METHODOLOGY.md before touching any of them.
- Static pairlist rots: check Binance delisting announcements monthly (MKR died mid-run last time).
