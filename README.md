# freqtrade-bot

Algorithmic trading bot built on Freqtrade. This is a full rebuild started June 2026 
after a post-mortem on the original May 2026 version. The old project is archived 
locally as read-only reference.

The rebuild rules and risk model are in [METHODOLOGY.md](METHODOLOGY.md). 
Every experiment and result is logged in [RESEARCH_LOG.md](RESEARCH_LOG.md).

## Status

- Phase 0 (scaffold): done. Fresh config, clean compose setup, alerting wired.
- Phase 1 (methodology): in review.
- Phase 2 (strategies): not started. No strategy is active yet so docker compose up 
  will not work until a candidate strategy is set in config.json.

## Setup

1. Telegram alerts: follow .env.example, fill .env, set FREQTRADE__TELEGRAM__ENABLED=true.
   The old bot died silently and nobody noticed for 3 weeks. Set this up first.

2. Laptop power settings: set sleep to Never while plugged in. A sleeping laptop means 
   data gaps and missed entries and exits.

3. Uptime heartbeat: create a free check at healthchecks.io then schedule a ping every 
   5 minutes via Task Scheduler:
   
   `powershell -Command "if (docker ps -q -f name=freqtrade) { curl.exe -fsS -m 10 https://hc-ping.com/<your-uuid> | Out-Null }"`

## Daily use

```powershell
docker compose up -d
docker compose logs -f --tail 50 freqtrade
docker compose down
```

FreqUI runs at http://127.0.0.1:8080.

## Hard rules

- Strategy selection only via config.json, never via --strategy flag in docker-compose.
- After any hyperopt run, check the generated JSON against what you intended. The JSON 
  silently overrides .py defaults and has caused bad exits before.
- Every stoploss and ROI number is a leveraged stake ratio, not a price move. Check the 
  risk model in METHODOLOGY.md before touching any of them.
- Check Binance delisting announcements monthly. Static pairlists rot.
